from collections import namedtuple
from typing import *


_missing = type('_missing', (), {'__bool__': lambda x: False})()

ABSTRACT_ATTR = '__abstract__'
META_OPTIONS_FACTORY_CLASS_ATTR_NAME = '_meta_options_factory_class'

McsInitArgs = namedtuple('McsInitArgs', ('cls', 'name', 'bases', 'clsdict'))


class McsArgs:
    def __init__(self,
                 mcs: type,
                 name: str,
                 bases: Tuple[Type[object], ...],
                 clsdict: Dict[str, Any]):
        self.mcs = mcs
        self.name = name
        self.bases = bases
        self.clsdict = clsdict

    @property
    def module(self) -> Union[str, None]:
        return self.clsdict.get('__module__')

    @property
    def qualname(self) -> str:
        if self.module:
            return f'{self.module}.{self.name}'
        return self.name

    @property
    def Meta(self) -> object:
        return self.clsdict['Meta']

    @property
    def is_abstract(self) -> bool:
        """
        Whether or not the class-under-construction was declared as abstract (NOTE: this
        property is usable even *before* the :class:`MetaOptionsFactory` has run)
        """
        meta_value = getattr(self.clsdict.get('Meta'), 'abstract', False)
        return self.clsdict.get(ABSTRACT_ATTR, meta_value) is True

    def __iter__(self):
        return iter([self.mcs, self.name, self.bases, self.clsdict])

    def __repr__(self):
        return f'<McsArgs class={self.qualname}>'


class MetaOption:
    def __init__(self, name: str, default: Any = None, inherit: bool = False):
        self.name = name
        self.default = default
        self.inherit = inherit

    def get_value(self, Meta: object, base_classes_meta, mcs_args: McsArgs):
        """
        :param Meta: the class Meta (if any) from the class (NOTE: this will
                     be a plain object, NOT an instance of MetaOptionsFactory)
        :param base_classes_meta: the MetaOptionsFactory (if any) from the
                                  base class of the class
        :param mcs_args: the McsArgs for the class
        """
        value = self.default
        if self.inherit and base_classes_meta is not None:
            value = getattr(base_classes_meta, self.name, value)
        if Meta is not None:
            value = getattr(Meta, self.name, value)
        return value

    def check_value(self, value: Any, mcs_args: McsArgs):
        pass

    def contribute_to_class(self, mcs_args: McsArgs, value: Any):
        pass

    def __repr__(self):
        return f'<{self.__class__.__name__} name={self.name!r}, ' \
               f'default={self.default!r}, inherit={self.inherit}>'


class AbstractMetaOption(MetaOption):
    def __init__(self):
        super().__init__(name='abstract', default=False, inherit=False)

    def get_value(self, Meta: object, base_classes_meta, mcs_args: McsArgs):
        if ABSTRACT_ATTR in mcs_args.clsdict:
            return True
        return super().get_value(Meta, base_classes_meta, mcs_args)

    def contribute_to_class(self, mcs_args: McsArgs, is_abstract):
        if is_abstract:
            mcs_args.clsdict[ABSTRACT_ATTR] = True


class MetaOptionsFactory:
    options = []

    def __init__(self):
        self._mcs_args: McsArgs = None

    def _get_meta_options(self) -> List[MetaOption]:
        return [option if isinstance(option, MetaOption) else option()
                for option in self.options]

    def _contribute_to_class(self, mcs_args: McsArgs):
        self._mcs_args = mcs_args

        Meta = mcs_args.clsdict.pop('Meta', None)
        base_classes_meta = deep_getattr(
            mcs_args.clsdict, mcs_args.bases, 'Meta', None)

        mcs_args.clsdict['Meta'] = self

        options = self._get_meta_options()

        self._fill_from_meta(Meta, base_classes_meta, mcs_args)
        for option in options:
            option_value = getattr(self, option.name, None)
            option.contribute_to_class(mcs_args, option_value)

    def _fill_from_meta(self, Meta: object, base_classes_meta, mcs_args: McsArgs):
        # Exclude private/protected fields from the Meta
        meta_attrs = {} if not Meta else {k: v for k, v in vars(Meta).items()
                                          if not k.startswith('_')}

        for option in self._get_meta_options():
            assert not hasattr(self, option.name), \
                f"Can't override field {option.name}."
            value = option.get_value(Meta, base_classes_meta, mcs_args)
            option.check_value(value, mcs_args)
            meta_attrs.pop(option.name, None)
            if option.name != '_':
                setattr(self, option.name, value)

        if meta_attrs:
            # Some attributes in the Meta aren't allowed here
            raise TypeError(
                f"'class Meta' for {self._mcs_args.name!r} got unknown "
                f"attribute(s) {','.join(sorted(meta_attrs.keys()))}")

    def __repr__(self):
        return '<{cls} meta_options={attrs!r}>'.format(
            cls=self.__class__.__name__,
            attrs={option.name: getattr(self, option.name, None)
                   for option in self._get_meta_options()})


def apply_factory_meta_options(
        mcs_args: McsArgs,
        default_factory_class: Type[MetaOptionsFactory] = MetaOptionsFactory,
        factory_attr_name: Optional[str] = None) -> MetaOptionsFactory:
    factory_cls = deep_getattr(
        mcs_args.clsdict, mcs_args.bases,
        factory_attr_name or META_OPTIONS_FACTORY_CLASS_ATTR_NAME,
        default_factory_class)
    options_factory = factory_cls()
    options_factory._contribute_to_class(mcs_args)
    return options_factory


class Singleton(type):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super().__call__(*args, **kwargs)
        return cls._instances[cls]

    @property
    def _instance(cls):
        return cls._instances[cls] if cls in cls._instances else None


class SubclassableSingleton(Singleton):
    def __call__(cls, *args, **kwargs):
        while cls.__subclasses__():
            cls = cls.__subclasses__()[0]
        return super().__call__(*args, **kwargs)


def deep_getattr(clsdict: Dict[str, Any],
                 bases: Tuple[Type[object], ...],
                 name: str,
                 default: Any = _missing) -> Any:
    """
    Acts just like getattr would on a constructed class object, except this operates
    on the pre-class-construction class dictionary and base classes. In other words,
    first we look for the attribute in the class dictionary, and then we search all the
    base classes (in method resolution order), finally returning the default value if
    the attribute was not found in any of the class dictionary or base classes.
    """
    value = clsdict.get(name, _missing)
    if value != _missing:
        return value
    for base in bases:
        value = getattr(base, name, _missing)
        if value != _missing:
            return value
    if default != _missing:
        return default
    raise AttributeError(name)


class OptionalMetaclass(type):
    """
    Use this as a generic base metaclass if you need to subclass a metaclass from
    an optional package.
    """

    __optional_class = None

    def __new__(mcs, name, bases, clsdict):
        if mcs.__optional_class is None:
            mcs.__optional_class = super().__new__(mcs, name, bases, clsdict)
        return mcs.__optional_class

    def __getattr__(self, item):
        return self.__optional_class

    def __setattr__(self, key, value):
        pass

    def __call__(self, *args, **kwargs):
        return self.__optional_class

    def __getitem__(self, item):
        return self.__optional_class

    def __setitem__(self, key, value):
        pass


class OptionalClass(metaclass=OptionalMetaclass):
    """
    Use this as a generic base class if you have classes that depend on an
    optional package. For example, if you want to define a serializer but not
    depend on flask_api_bundle, you should do something like this::

        try:
            from flask_api_bundle import ma
        except ImportError:
            from flask_unchained import OptionalClass as ma

        class MySerializer(ma.ModelSerializer):
            class Meta:
                model = 'MyModel'
    """
    def __init__(self, *args, **kwargs):
        pass
