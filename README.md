# Py Meta Utils

## Useful Links

* [Official Documentation on Read The Docs](http://py-meta-utils.readthedocs.io/)
* [Source Code on GitHub](https://github.com/briancappello/py-meta-utils)
* [PyPI](https://pypi.org/project/Py-Meta-Utils/)

## The Meta Options Factory Pattern as a library, and related metaclass utilities

OK, but just what is the Meta options factory pattern? Perhaps the easiest way to explain it is to start with an example. Let's say you wanted your end users to be able to optionally enable logging of the actions of a class from a library you're writing:

```python
class EndUserClass(YourLoggableService):
    class Meta:
        debug: bool = True
        verbosity: int = 2
        log_destination: str = '/tmp/end-user-class.log'
```

The first step is to define your custom [MetaOption](https://py-meta-utils.readthedocs.io/en/latest/api.html#py_meta_utils.MetaOption) subclasses:

- All that's absolutely required to implement is the constructor and its `name` argument. That said, it's recommended to also specify the `default` and `inherit` arguments for the sake of being explicit.
- The `check_value` method is optional, but useful for making sure your users aren't giving you garbage.
- The `get_value` method has a default implementation that normally you shouldn't need to override, unless your default value is mutable or you have advanced logic.
- There's also a `contribute_to_class` method that we'll cover later on.

```python
import os
import sys

# first we have to import what we need from py_meta_utils
from py_meta_utils import (McsArgs, MetaOption, MetaOptionsFactory,
                           process_factory_meta_options, _missing)

# then we have to declare the meta options the meta options factory should support
class DebugMetaOption(MetaOption):
    def __init__(self):
        super().__init__(name='debug', default=False, inherit=True)

    def check_value(self, value, mcs_args: McsArgs):
        if not isinstance(value, bool):
            raise TypeError(f'The {self.name} Meta option must be a bool')


class VerbosityMetaOption(MetaOption):
    def __init__(self):
        super().__init__(name='verbosity', default=1, inherit=True)

    def check_value(self, value, mcs_args: McsArgs):
        if value not in {1, 2, 3}:
            raise ValueError(f'The {self.name} Meta option must either 1, 2, or 3')


class LogDestinationMetaOption(MetaOption):
    def __init__(self):
        super().__init__(name='log_destination', default=_missing, inherit=True)

    # this pattern is useful if you need a mutable default value like [] or {}
    def get_value(self, Meta, base_classes_meta, mcs_args: McsArgs):
        value = super().get_value(Meta, base_classes_meta, mcs_args)
        return value if value != _missing else 'stdout'

    def check_value(self, value, mcs_args: McsArgs):
        if value in {'stdout', 'stderr'}:
            return

        try:
            valid_dir = os.path.exists(os.path.dirname(value))
        except Exception:
            valid_dir = False

        if not valid_dir:
            raise ValueError(f'The {self.name} Meta option must be one of `stdout`, '
                             '`stderr`, or a valid filepath')
```

The next step is to subclass [MetaOptionsFactory](https://py-meta-utils.readthedocs.io/en/latest/api.html#py_meta_utils.MetaOptionsFactory) and specify the [MetaOption](https://py-meta-utils.readthedocs.io/en/latest/api.html#py_meta_utils.MetaOption) subclasses you want:

```python
class LoggingMetaOptionsFactory(MetaOptionsFactory):
    _options = [
        DebugMetaOption,
        VerbosityMetaOption,
        LogDestinationMetaOption,
    ]
```

Then you need a metaclass to actually apply the factory options:

```python
class LoggingMetaclass(type):
    def __new__(mcs, name, bases, clsdict):
        mcs_args = McsArgs(mcs, name, bases, clsdict)
        factory_cls = mcs_args.getattr('_meta_options_factory_class',
                                       LoggingMetaOptionsFactory)
        options_factory = factory_cls()
        options_factory._contribute_to_class(mcs_args)
        # the above three lines can be replaced by:
        # process_factory_meta_options(mcs_args, LoggingMetaOptionsFactory)
        return super().__new__(*mcs_args)
```

And lastly, create the public class, using the metaclass just defined:

```python
class YourLoggableService(metaclass=LoggingMetaclass):
    def do_important_stuff(self):
        if self.Meta.verbosity < 3:
            self._log('doing important stuff')
        else:
            self._log('doing really detailed important stuff like so')

    def _log(self, msg):
        if not self.Meta.debug:
            return

        if self.Meta.log_destination == 'stdout':
            print(msg)
        elif self.Meta.log_destination == 'stderr':
            sys.stderr.write(msg)
            sys.stderr.flush()
        else:
            with open(self.Meta.log_destination, 'a') as f:
                f.write(msg)
```

The options factory automatically adds the `Meta` attribute to the class-under-construction (in this example, `YourLoggableService`). (In this case the `Meta` attribute will be populated with the default values as supplied by the [MetaOption](https://py-meta-utils.readthedocs.io/en/latest/api.html#py_meta_utils.MetaOption) subclasses specified by the factory.) In the case where the class-under-construction has a partial `Meta` class, the missing meta options will be added to it.(*)

(*) In effect that's what happens, and for all practical purposes is probably how you should think about it, but technically speaking, the class-under-construction's `Meta` attribute actually gets replaced with a populated instance of the specified [MetaOptionsFactory](https://py-meta-utils.readthedocs.io/en/latest/api.html#py_meta_utils.MetaOptionsFactory) subclass.

The one thing we didn't cover is `MetaOption.contribute_to_class`. This is an optional callback hook that allows `MetaOption` subclasses to, well, contribute something to the class-under-construction. Most likely it adds/removes attributes to/from the class, or perhaps it wraps some method(s) with a decorator or something else entirely. 

A good simple example can be found in the source code for the included [AbstractMetaOption](https://py-meta-utils.readthedocs.io/en/latest/api.html#py_meta_utils.AbstractMetaOption):

```python
ABSTRACT_ATTR = '__abstract__'


class AbstractMetaOption(MetaOption):
    def __init__(self):
        super().__init__(name='abstract', default=False, inherit=False)

    def get_value(self, Meta, base_classes_meta, mcs_args: McsArgs):
        # class attributes take precedence over the class Meta's value
        if mcs_args.clsdict.get(ABSTRACT_ATTR, False) is True:
            return True
        return super().get_value(Meta, base_classes_meta, mcs_args) is True

    def contribute_to_class(self, mcs_args: McsArgs, value):
        if value is True:
            mcs_args.clsdict[ABSTRACT_ATTR] = True
        else:
            mcs_args.clsdict[ABSTRACT_ATTR] = False
```

A number of libraries use the `__abstract__` class attribute to determine whether or not the class-under-construction should be considered concrete or not, but they won't understand class `Meta` options. Therefore, we implement `MetaOption.contribute_to_class` to set the `__abstract__` class attribute to the appropriate value for backwards compatibility with such libraries.

## Included Metaclass Utilities

### Singleton

[Singleton](http://localhost:8000/api.html#singleton) is an included metaclass that makes any class utilizing it a singleton:

```python
from py_meta_utils import Singleton


class YourSingleton(metaclass=Singleton):
    pass


instance = YourSingleton()
assert instance == YourSingleton()
```

Classes using [Singleton](http://localhost:8000/api.html#singleton) can be subclassed, however, you must inform the base class of your subclass:

```python
from py_meta_utils import Singleton

class BaseSingleton(metaclass=Singleton):
    pass

class Extended(BaseSingleton):
    pass

BaseSingleton.set_singleton_class(Extended)
base_instance = BaseSingleton()
extended_instance = Extended()
assert base_instance == extended_instance == BaseSingleton() == Extended()
```

### deep_getattr

```python
deep_getattr(clsdict, bases, 'attr_name', [default])
```

`deep_getattr` acts just like `getattr` would on a constructed class object, except this operates on the pre-class-construction class dictionary and base classes. In other words, first we look for the attribute in the class dictionary, and then we search all the base classes (in method resolution order), finally returning the default value if the attribute was not found in any of the class dictionary or base classes (or it raises `AttributeError` if `default` not given).


### OptionalMetaclass and OptionalClass

```python
try:
    from optional_dependency import SomeClass
except ImportError:
    from py_meta_utils import OptionalClass as SomeClass


class Optional(SomeClass):
    pass
```

## License

MIT
