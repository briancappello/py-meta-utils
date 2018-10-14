API Documentation
=================

McsArgs
-------

.. autoclass:: py_meta_utils.McsArgs
   :members:

deep_getattr
------------

.. autofunction:: py_meta_utils.deep_getattr

MetaOption
----------

.. autoclass:: py_meta_utils.MetaOption
   :members:

AbstractMetaOption
^^^^^^^^^^^^^^^^^^

.. autoclass:: py_meta_utils.AbstractMetaOption

   .. attribute:: name = 'abstract'

   The attribute name on class ``Meta`` objects is ``abstract``.

   .. attribute:: default = False

   The default value is ``False``.

   .. attribute:: inherit = False

   We do *not* inherit this value from the class ``Meta`` of base classes.

MetaOptionsFactory
------------------

.. autoclass:: py_meta_utils.MetaOptionsFactory
   :members: _options, _get_meta_options, _contribute_to_class, _fill_from_meta

process_factory_meta_options
----------------------------

.. autofunction:: py_meta_utils.process_factory_meta_options

Utility Classes
---------------

EnsureProtectedMembers
^^^^^^^^^^^^^^^^^^^^^^

.. autoclass:: py_meta_utils.EnsureProtectedMembers

Singleton
^^^^^^^^^

.. autoclass:: py_meta_utils.Singleton

SubclassableSingleton
^^^^^^^^^^^^^^^^^^^^^

.. autoclass:: py_meta_utils.SubclassableSingleton

OptionalClass
^^^^^^^^^^^^^

.. autoclass:: py_meta_utils.OptionalClass

OptionalMetaclass
^^^^^^^^^^^^^^^^^

.. autoclass:: py_meta_utils.OptionalMetaclass
