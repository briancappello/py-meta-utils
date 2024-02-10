import pytest

from py_meta_utils import (
    AbstractMetaOption,
    EnsureProtectedMembers,
    McsArgs,
    MetaOption,
    MetaOptionsFactory,
    Singleton,
    deep_getattr,
)


class TestMcsArgs:
    def test_module_and_qualname_properties(self):
        mcs_args = McsArgs(type, "Test", (), {})
        assert mcs_args.module is None
        assert mcs_args.qualname == "Test"
        assert repr(mcs_args) == "<McsArgs class='Test'>"

        mcs_args = McsArgs(type, "Test", (), {"__module__": "it.works"})
        assert mcs_args.module == "it.works"
        assert mcs_args.qualname == "it.works.Test"
        assert repr(mcs_args) == "<McsArgs class='it.works.Test'>"

    def test_meta(self):
        mcs_args = McsArgs(type, "Test", (), {})
        with pytest.raises(KeyError):
            fail = mcs_args.Meta

        meta = object()
        mcs_args = McsArgs(type, "Test", (), {"Meta": meta})
        assert mcs_args.Meta == meta

    def test_is_abstract(self):
        assert McsArgs(type, "", (), {"__abstract__": True}).is_abstract is True
        assert McsArgs(type, "", (), {"__abstract__": False}).is_abstract is False
        assert McsArgs(type, "", (), {"__abstract__": "garbage"}).is_abstract is False

        true_meta = type("Meta", (), {"abstract": True})()
        assert McsArgs(type, "", (), {"Meta": true_meta}).is_abstract is True
        false_meta = type("Meta", (), {"abstract": False})()
        assert McsArgs(type, "", (), {"Meta": false_meta}).is_abstract is False
        garbage_meta = type("Meta", (), {"abstract": "garbage"})()
        assert McsArgs(type, "", (), {"Meta": garbage_meta}).is_abstract is False

    def test_iter(self):
        mcs_args = McsArgs(1, 2, 3, 4)
        assert list(iter(mcs_args)) == [1, 2, 3, 4]


class TestMetaOption:
    def test_get_value(self):
        mcs_args = McsArgs(type, "Test", (), {})
        option = MetaOption("testing", default="the.default")

        # test we get the default with no user-supplied Meta class
        assert option.get_value(None, None, mcs_args) == "the.default"

        # test we get the user-supplied value when it's present
        meta_with_value = type("Meta", (), {"testing": "not.default"})()
        assert option.get_value(meta_with_value, None, mcs_args) == "not.default"

        # test we don't inherit a customized value
        meta_with_value = type("Meta", (), {"testing": "not.default"})()
        assert option.get_value(None, meta_with_value, mcs_args) == "the.default"

    def test_get_value_with_inheritance(self):
        mcs_args = McsArgs(type, "Test", (), {})
        option = MetaOption("testing", default="the.default", inherit=True)
        meta_with_value = type("Meta", (), {"testing": "not.default"})()
        assert option.get_value(None, meta_with_value, mcs_args) == "not.default"


class TestAbstractMetaOption:
    def test_check_value(self):
        option = AbstractMetaOption()
        mcs_args = McsArgs(type, "", (), {})

        option.check_value(True, mcs_args)
        option.check_value(False, mcs_args)
        with pytest.raises(TypeError):
            option.check_value("garbage", mcs_args)

    def test_get_value(self):
        option = AbstractMetaOption()

        mcs_args = McsArgs(type, "", (), {"__abstract__": True})
        assert option.get_value(None, None, mcs_args) is True

        mcs_args = McsArgs(type, "", (), {"__abstract__": False})
        assert option.get_value(None, None, mcs_args) is False

    def test_contribute_to_class_when_abstract(self):
        option = AbstractMetaOption()
        mcs_args = McsArgs(type, "", (), {})
        option.contribute_to_class(mcs_args, True)
        assert mcs_args.clsdict["__abstract__"] is True

    def test_contribute_to_class_when_not_abstract(self):
        option = AbstractMetaOption()
        mcs_args = McsArgs(type, "", (), {})
        option.contribute_to_class(mcs_args, False)
        assert mcs_args.clsdict["__abstract__"] is False


class TestMetaOptionsFactory:
    def test_it_requires_protected_attributes(self):
        with pytest.raises(NameError) as e:

            class Foo(MetaOptionsFactory):
                def fail(self):
                    pass

        assert "Foo.fail must be protected (rename to Foo._fail)" in str(e)

    def test_get_meta_options_with_classes(self):
        class One(MetaOption):
            def __init__(self):
                super().__init__("one")

        class Two(MetaOption):
            def __init__(self):
                super().__init__("two")

        class Foo(MetaOptionsFactory):
            _options = [One, Two]

        instances = Foo()._get_meta_options()
        assert isinstance(instances[0], One)
        assert isinstance(instances[1], Two)

    def test_get_meta_options_with_instances(self):
        instances = [MetaOption("foo"), MetaOption("bar")]

        class Foo(MetaOptionsFactory):
            _options = instances

        assert Foo()._get_meta_options() == instances

    def test_fill_from_meta(self):
        class Foo(MetaOptionsFactory):
            _options = [
                MetaOption("one", 1),
                MetaOption("two", 2),
                MetaOption("three", 3),
            ]

        foo = Foo()
        foo._fill_from_meta(None, None, McsArgs(type, "", (), {}))
        assert foo.one == 1
        assert foo.two == 2
        assert foo.three == 3

        foo = Foo()
        foo._fill_from_meta(
            type("Meta", (), {"one": "one", "two": "two"}),
            None,
            McsArgs(type, "", (), {}),
        )
        assert foo.one == "one"
        assert foo.two == "two"
        assert foo.three == 3

        foo = Foo()
        with pytest.raises(TypeError) as e:
            foo._fill_from_meta(
                type("Meta", (), {"fail": "fail"}),
                None,
                McsArgs(type, "Foobar", (), {}),
            )
        assert "`class Meta` for Foobar got unknown attribute(s) fail" in str(e)

    def test_contribute_to_class(self):
        class Foo(MetaOptionsFactory):
            _options = [
                MetaOption("one", 1),
                MetaOption("two", 2),
                MetaOption("three", 3),
            ]

        foo = Foo()
        mcs_args = McsArgs(type, "Foobar", (), {})
        foo._contribute_to_class(mcs_args)

        assert mcs_args.Meta == foo
        assert foo.one == 1
        assert foo.two == 2
        assert foo.three == 3


class TestEnsureProtectedMembers:
    def test_it_works(self):
        with pytest.raises(NameError) as e:

            class HasPublicMembers(metaclass=EnsureProtectedMembers):
                def should_not_be_allowed(self):
                    raise Exception

        assert "HasPublicMembers.should_not_be_allowed must be protected" in str(e)

    def test_it_allows_public_properties(self):
        class HasPublicProperties(metaclass=EnsureProtectedMembers):
            _allowed_properties = ["allowed"]

            def __init__(self):
                self._allowed = True

            @property
            def allowed(self):
                return self._allowed

            @allowed.setter
            def allowed(self, allowed):
                self._allowed = allowed

        assert HasPublicProperties().allowed is True


def test_singleton():
    class Single(metaclass=Singleton):
        pass

    class Second(Single):
        pass

    single = Single()
    assert single == Single()
    assert isinstance(single, Single) and not isinstance(single, Second)

    second = Second()
    assert second == Second()
    assert single != second
    assert isinstance(second, Second)


def test_singleton_subclassable():
    class Single(metaclass=Singleton):
        pass

    class Second(Single):
        pass

    Single.set_singleton_class(Second)

    single = Single()
    assert single == Single()
    assert isinstance(single, Second)

    second = Second()
    assert single == second == Second()

    class Third(Second):
        pass

    with pytest.warns(UserWarning) as warnings:
        Single.set_singleton_class(Third)
    assert (
        "An instance of the singleton Single has already been created! Please set "
        "Third earlier." in warnings[0].message.args[0]
    )

    with pytest.warns(UserWarning) as warnings:
        Second.set_singleton_class(Third)
    assert (
        "An instance of the singleton Second has already been created! Please set "
        "Third earlier." in warnings[0].message.args[0]
    )


def test_singleton_subclassable_without_set_is_instantiation_order_independent():
    class Single(metaclass=Singleton):
        pass

    class Second(Single):
        pass

    class Third(Second):
        pass

    third = Third()
    assert third == Third()
    assert isinstance(third, Third)

    second = Second()
    assert second == Second()
    assert isinstance(second, Second) and not isinstance(second, Third)

    single = Single()
    assert single == Single()
    assert isinstance(single, Single) and not isinstance(single, Second)


def test_singleton_subsubclassable():
    class Single(metaclass=Singleton):
        pass

    class Second(Single):
        pass

    class Third(Second):
        pass

    Second.set_singleton_class(Third)

    single = Single()
    assert isinstance(single, Third)
    assert single == Single()

    second = Second()
    assert isinstance(second, Third)
    assert single == second == Second()

    third = Third()
    assert isinstance(third, Third)
    assert single == second == third == Third()


class TestDeepGetattr:
    def test_from_clsdict(self):
        assert deep_getattr({"hi": "hello"}, (), "hi") == "hello"

    def test_from_bases(self):
        Hi = type("Hi", (), {"hi": "hello"})
        assert deep_getattr({}, (Hi,), "hi") == "hello"
        assert deep_getattr({}, (object, Hi), "hi") == "hello"

    def test_clsdict_takes_precedence_over_bases(self):
        Base = type("Base", (), {"hi": "from base"})
        assert deep_getattr({"hi": "from clsdict"}, (Base,), "hi") == "from clsdict"

    def test_default(self):
        assert deep_getattr({}, (), "nope", "default") == "default"

    def test_attribute_error(self):
        with pytest.raises(AttributeError):
            deep_getattr({}, (), "nope")
