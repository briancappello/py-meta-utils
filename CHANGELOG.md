# CHANGELOG

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
