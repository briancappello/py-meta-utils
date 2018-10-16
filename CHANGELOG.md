# CHANGELOG

## 0.6.1 (2018/10/16)

- add more tests for `Singleton`, fix bugs in implementation

## 0.6.0 (2018/10/16)

- add `McsArgs.getattr(name[, default])` convenience method
- refactor `Singleton` to support specifying the class to use, drop `SubclassableSingleton`

## 0.5.1 (2018/10/14)

- fix markdown readme on PyPI

## 0.5.0 (2018/10/14)

- clean up the documentation a bit
- update type hints for `Meta` to reflect that we pass around class objects, not instances
- rename `EnsureProtected` to `EnsureProtectedMembers`
- rename `apply_factory_meta_options` to `process_factory_meta_options`

## 0.4.1 (2018/10/13)

- add unit tests

## 0.4.0 (2018/10/13)

- make `__abstract__` a constant
- add type hints
- rename `McsArgs.repr` to `McsArgs.qualname`
- add `McsArgs.is_abstract` property
- make compatible with Python 3.5
- ensure `abstract` meta option is always a boolean
- rename `MetaOptionsFactory.options` to `MetaOptionsFactory._options`
- add a metaclass on `MetaOptionsFactory` to ensure subclasses can only add protected attributes and/or methods
- remove the `Singleton._instance` property
- add documentation

## 0.3.0 (2018/09/30)

- rename `McsArgs.meta` to `McsArgs.Meta`
- add the `apply_factory_meta_options` function for consumer metaclasses
- previously we popped the user's `Meta` class and renamed it to `_meta` after applying the factory options. Now we keep it named as `Meta` (although we replace the user's `Meta` class with the meta options factory instance)

## 0.2.0 (2018/09/28)

- add missing `OptionalClass` and `OptionalMetaclass` classes
- rename `McsArgs.model_repr` to `McsArgs.repr`
- rename `McsArgs.model_meta` to `McsArgs.meta`
- rename the `base_model_meta` argument to `MetaOption.get_value` to `base_classes_meta`

## 0.1.0 (2018/09/24)

- rename `Singleton.instance` to `Singleton._instance`
- add `SubclassableSingleton` class

## 0.0.1 (2018/09/24)
 
- initial release
