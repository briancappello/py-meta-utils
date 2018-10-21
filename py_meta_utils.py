from collections import namedtuple
from typing import *


_missing = type('_missing', (), {'__bool__': lambda x: False})()

ABSTRACT_ATTR = '__abstract__'
META_OPTIONS_FACTORY_CLASS_ATTR_NAME = '_meta_options_factory_class'


McsInitArgs = namedtuple('McsInitArgs', ('cls', 'name', 'bases', 'clsdict'))


class McsArgs:
    """
    Data holder for the parameters to ``type.__new__()``::

        class Metaclass(type):
            def __new__(mcs, name, bases, clsdict):
                mcs_args = McsArgs(mcs, name, bases, clsdict)
                # do stuff
                return super().__new__(*mcs_args)

        # or in short-hand:

        class Metaclass(type):
            def __new__(mcs, *args):
                mcs_args = McsArgs(mcs, *args)
                # do stuff
                return super().__new__(*mcs_args)
    """
    def __init__(self,
                 mcs: type,
                 name: str,
                 bases: Tuple[Type[object], ...],
                 clsdict: Dict[str, Any]):
        self.mcs = mcs
        self.name = name
        self.bases = bases
        self.clsdict = clsdict

    def getattr(self, name, default: Any = _missing):
        """
        Convenience method equivalent to
        ``deep_getattr(mcs_args.clsdict, mcs_args.bases, 'attr_name'[, default])``
        """
        return deep_getattr(self.clsdict, self.bases, name, default)

    @property
    def module(self) -> Union[str, None]:
        """
        Returns the module of the class-under-construction, or ``None``.
        """
        return self.clsdict.get('__module__')

    @property
    def qualname(self) -> str:
        """
        Returns the fully qualified name of the class-under-construction, if possible,
        otherwise just the class name.
        """
        if self.module:
            return self.module + '.' + self.name
        return self.name

    @property
    def Meta(self) -> Type[object]:
        """
        Returns the class ``Meta`` from the class-under-construction.

        Raises ``KeyError`` if it's not present.
        """
        return self.clsdict['Meta']

    @property
    def is_abstract(self) -> bool:
        """
        Whether or not the class-under-construction was declared as abstract (**NOTE:**
        this property is usable even *before* the :class:`MetaOptionsFactory` has run)
        """
        meta_value = getattr(self.clsdict.get('Meta'), 'abstract', False)
        return self.clsdict.get(ABSTRACT_ATTR, meta_value) is True

    # we implement __iter__() to allow using the *args unpacking syntax
    def __iter__(self):
        return iter([self.mcs, self.name, self.bases, self.clsdict])

    def __repr__(self):
        return '<McsArgs class={qualname!r}>'.format(qualname=self.qualname)


class MetaOption:
    """
    Base class for custom meta options.
    """
    def __init__(self, name: str, default: Any = None, inherit: bool = False):
        self.name = name
        """
        The attribute name of the option on class ``Meta`` objects.
        """

        self.default = default
        """
        The default value for this meta option.
        """

        self.inherit = inherit
        """
        Whether or not this option's value should be inherited from the class ``Meta``
        of any base classes.
        """

    def get_value(self, Meta: Type[object], base_classes_meta, mcs_args: McsArgs) -> Any:
        """
        Returns the value for ``self.name`` given the class-under-construction's class
        ``Meta``. If it's not found there, and ``self.inherit == True`` and there is a
        base class that has a class ``Meta``, use that value, otherwise ``self.default``.

        :param Meta: the class ``Meta`` (if any) from the class-under-construction
                     (**NOTE:** this will be an ``object`` or ``None``, NOT an instance
                     of :class:`MetaOptionsFactory`)
        :param base_classes_meta: the :class:`MetaOptionsFactory` instance (if any) from
                                  the base class of the class-under-construction
        :param mcs_args: the :class:`McsArgs` for the class-under-construction
        """
        value = self.default
        if self.inherit and base_classes_meta is not None:
            value = getattr(base_classes_meta, self.name, value)
        if Meta is not None:
            value = getattr(Meta, self.name, value)
        return value

    def check_value(self, value: Any, mcs_args: McsArgs):
        """
        Optional callback to verify the user provided a valid value.

        Your implementation should assert/raise with an error message if invalid.
        """
        pass

    def contribute_to_class(self, mcs_args: McsArgs, value: Any):
        """
        Optional callback to modify the :class:`McsArgs` of the class-under-construction.
        """
        pass

    def __repr__(self):
        return '{cls}(name={name!r}, default={default!r}, inherit={inherit})'.format(
            cls=self.__class__.__name__,
            name=self.name,
            default=self.default,
            inherit=self.inherit)


class AbstractMetaOption(MetaOption):
    """
    A meta option that allows designating a class as abstract, using either::

        class SomeAbstractBase(metaclass=MetaclassWithAnOptionsFactory):
            __abstract__ = True

        # or

        class SomeAbstractBase(metaclass=MetaclassWithAnOptionsFactory):
            class Meta:
                abstract = True

    In the latter case, we make sure to set the ``__abstract__`` class attribute
    for backwards compatibility with libraries that do not understand ``Meta`` options.
    """
    def __init__(self):
        super().__init__(name='abstract', default=False, inherit=False)

    def get_value(self, Meta, base_classes_meta, mcs_args: McsArgs):
        # class attributes take precedence over the class Meta's value
        if mcs_args.clsdict.get(ABSTRACT_ATTR, False) is True:
            return True
        return super().get_value(Meta, base_classes_meta, mcs_args) is True

    def check_value(self, value: Any, mcs_args: McsArgs):
        if not isinstance(value, bool):
            raise TypeError('The abstract Meta option must be either True or False')

    def contribute_to_class(self, mcs_args: McsArgs, value):
        mcs_args.clsdict[ABSTRACT_ATTR] = True if value is True else False


class EnsureProtectedMembers(type):
    """
    Metaclass to ensure that all members (attributes and method names) of consumer classes
    are protected (ie, prefixed with an ``_``).

    Raises ``NameError`` if any public members are found.
    """
    def __init__(cls, name, bases, clsdict):
        for attr in clsdict:
            if not attr.startswith('_'):
                raise NameError('{cls}.{attr} must be protected '
                                '(rename to {cls}._{attr})'.format(cls=name,
                                                                   attr=attr))
        super().__init__(name, bases, clsdict)


class MetaOptionsFactory(metaclass=EnsureProtectedMembers):
    """
    Base class for meta options factory classes. Subclasses should either set
    :attr:`_options` to a list of :class:`MetaOption` subclasses (or instances)::

        class MyMetaOptionsFactory(MetaOptionsFactory):
            _options = [AbstractMetaOption]

    Or override :meth:`_get_meta_options` to return a list of :class:`MetaOption`
    *instances*::

        class MyMetaOptionsFactory(MetaOptionsFactory):
            def _get_meta_options(self):
                return [AbstractMetaOption()]

    **IMPORTANT:** If you add any attributes and/or methods to your factory subclass,
    they *must* be protected (ie, prefixed with an ``_`` character).
    """

    _options = []
    """
    A list of :class:`MetaOption` subclasses (or instances) that this factory supports.
    """

    def __init__(self):
        self._mcs_args = None

    def _get_meta_options(self) -> List[MetaOption]:
        """
        Returns a list of :class:`MetaOption` instances that this factory supports.
        """
        return [option if isinstance(option, MetaOption) else option()
                for option in self._options]

    def _contribute_to_class(self, mcs_args: McsArgs):
        """
        Where the magic happens. Takes one parameter, the :class:`McsArgs` of the
        class-under-construction, and processes the declared ``class Meta`` from
        it (if any). We fill ourself with the declared meta options' name/value pairs,
        give the declared meta options a chance to also contribute to the class-under-
        construction, and finally replace the class-under-construction's ``class Meta``
        with this populated factory instance (aka ``self``).
        """
        self._mcs_args = mcs_args

        Meta = mcs_args.clsdict.pop('Meta', None)  # type: Type[object]
        base_classes_meta = mcs_args.getattr('Meta', None)  # type: MetaOptionsFactory

        mcs_args.clsdict['Meta'] = self  # must come before _fill_from_meta, because
                                         # some meta options may depend upon having
                                         # access to the values of earlier meta options
        self._fill_from_meta(Meta, base_classes_meta, mcs_args)

        for option in self._get_meta_options():
            option_value = getattr(self, option.name, None)
            option.contribute_to_class(mcs_args, option_value)

    def _fill_from_meta(self, Meta: Type[object], base_classes_meta, mcs_args: McsArgs):
        """
        Iterate over our supported meta options, and set attributes on the factory
        instance (self) for each meta option's name/value. Raises ``TypeError`` if
        we discover any unsupported meta options on the class-under-construction's
        ``class Meta``.
        """
        # Exclude private/protected fields from the Meta
        meta_attrs = {} if not Meta else {k: v for k, v in vars(Meta).items()
                                          if not k.startswith('_')}

        for option in self._get_meta_options():
            assert not hasattr(self, option.name), \
                "Can't override field {name}.".format(name=option.name)
            value = option.get_value(Meta, base_classes_meta, mcs_args)
            option.check_value(value, mcs_args)
            meta_attrs.pop(option.name, None)
            if option.name != '_':
                setattr(self, option.name, value)

        if meta_attrs:
            # Only allow attributes on the Meta that have a respective MetaOption
            raise TypeError(
                '`class Meta` for {cls} got unknown attribute(s) {attrs}'.format(
                    cls=mcs_args.name,
                    attrs=', '.join(sorted(meta_attrs.keys()))))

    def __repr__(self):
        return '{cls}(options={attrs!r})'.format(
            cls=self.__class__.__name__,
            attrs={option.name: getattr(self, option.name, None)
                   for option in self._get_meta_options()})


def process_factory_meta_options(
        mcs_args: McsArgs,
        default_factory_class: Type[MetaOptionsFactory] = MetaOptionsFactory,
        factory_attr_name: str = META_OPTIONS_FACTORY_CLASS_ATTR_NAME) \
        -> MetaOptionsFactory:
    """
    Main entry point for consumer metaclasses. Usage::

        from py_meta_utils import (AbstractMetaOption, McsArgs, MetaOptionsFactory,
                                   process_factory_meta_options)


        class YourMetaOptionsFactory(MetaOptionsFactory):
            _options = [AbstractMetaOption]


        class YourMetaclass(type):
            def __new__(mcs, name, bases, clsdict):
                mcs_args = McsArgs(mcs, name, bases, clsdict)

                # process_factory_meta_options must come *before* super().__new__()
                process_factory_meta_options(mcs_args, YourMetaOptionsFactory)
                return super().__new__(*mcs_args)


        class YourClass(metaclass=YourMetaclass):
            pass

    Subclasses of ``YourClass`` may set their ``_meta_options_factory_class``
    attribute to a subclass of ``YourMetaOptionsFactory`` to customize
    their own supported meta options::

        from py_meta_utils import MetaOption


        class FooMetaOption(MetaOption):
            def __init__(self):
                super().__init__(name='foo', default=None, inherit=True)


        class FooMetaOptionsFactory(YourMetaOptionsFactory):
            _options = YourMetaOptionsFactory._options + [
                FooMetaOption,
            ]


        class FooClass(YourClass):
            _meta_options_factory_class = FooMetaOptionsFactory

            class Meta:
                foo = 'bar'

    :param mcs_args: The :class:`McsArgs` for the class-under-construction
    :param default_factory_class: The default MetaOptionsFactory class to use, if
                                  the ``factory_attr_name`` attribute is not set on
                                  the class-under-construction
    :param factory_attr_name: The attribute name to look for an overridden factory
                              meta options class on the class-under-construction
    :return: The populated instance of the factory class
    """
    factory_cls = mcs_args.getattr(
        factory_attr_name or META_OPTIONS_FACTORY_CLASS_ATTR_NAME,
        default_factory_class)
    options_factory = factory_cls()
    options_factory._contribute_to_class(mcs_args)
    return options_factory


class Singleton(type):
    """
    A metaclass that makes a consumer class a singleton::

        from py_meta_utils import Singleton

        class Foo(metaclass=Singleton):
            pass

        foo = Foo()
        assert foo == Foo() == Foo()  # True

    Note that if you subclass a singleton, then you must inform the base class::

        Foo.set_singleton_class(YourFooSubclass)

    This way, calling ``Foo()`` will still return the same instance of ``YourFooSubclass``
    as if calling ``YourFooSubclass()`` itself::

        foo = Foo()
        sub = YourFooSubclass()
        assert foo == sub == Foo() == YourFooSubclass()
    """

    _classes = {}
    _instances = {}

    def set_singleton_class(self, cls):
        if self in self._classes:
            from warnings import warn
            warn('An instance of this singleton has already been created! Please set '
                 'the class you wish to use earlier.', UserWarning)
            return

        for base in self.__mro__:
            self._classes[base] = cls
        self._classes[cls] = cls

    def __call__(cls, *args, **kwargs):
        if cls not in cls._classes:
            cls.set_singleton_class(cls)

        cls = cls._classes[cls]
        if cls not in cls._instances:
            cls._instances[cls] = super().__call__(*args, **kwargs)
        return cls._instances[cls]


def deep_getattr(clsdict: Dict[str, Any],
                 bases: Tuple[Type[object], ...],
                 name: str,
                 default: Any = _missing) -> Any:
    """
    Acts just like ``getattr`` would on a constructed class object, except this operates
    on the pre-construction class dictionary and base classes. In other words, first we
    look for the attribute in the class dictionary, and then we search all the base
    classes (in method resolution order), finally returning the default value if the
    attribute was not found in any of the class dictionary or base classes (or it raises
    ``AttributeError`` if no default was given).
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
    an optional package::

        try:
            from optional_dependency import SomeMetaclass
        except ImportError:
            from py_meta_utils import OptionalMetaclass as SomeMetaclass

        class Optional(metaclass=SomeMetaclass):
            pass
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

    def __call__(cls, *args, **kwargs):
        return cls.__optional_class

    def __getitem__(self, item):
        return self.__optional_class

    def __setitem__(self, key, value):
        pass

    def __bool__(self):
        return False

    def __contains__(self, item):
        return False


class OptionalClass(metaclass=OptionalMetaclass):
    """
    Use this as a generic base class if you have classes that depend on an
    optional package::

        try:
            from optional_dependency import SomeClass
        except ImportError:
            from py_meta_utils import OptionalClass as SomeClass

        class Optional(SomeClass):
            pass
    """
    def __init__(self, *args, **kwargs):
        pass
