import unittest
import theano.tensor as tt
import pymc3 as pm
from pymc3.distributions import HalfCauchy, Normal
from pymc3 import Potential, Deterministic


class NewModel(pm.Model):
    def __init__(self, name='', model=None):
        super(NewModel, self).__init__(name, model)
        assert pm.modelcontext(None) is self
        # 1) init variables with Var method
        self.Var('v1', pm.Normal.dist())
        self.v2 = pm.Normal('v2', mu=0, sd=1)
        # 2) Potentials and Deterministic variables with method too
        # be sure that names will not overlap with other same models
        pm.Deterministic('d', tt.constant(1))
        pm.Potential('p', tt.constant(1))


class DocstringModel(pm.Model):
    def __init__(self, mean=0, sd=1, name='', model=None):
        super(DocstringModel, self).__init__(name, model)
        self.Var('v1', Normal.dist(mu=mean, sd=sd))
        Normal('v2', mu=mean, sd=sd)
        Normal('v3', mu=mean, sd=HalfCauchy('sd', beta=10, testval=1.))
        Deterministic('v3_sq', self.v3 ** 2)
        Potential('p1', tt.constant(1))


class TestBaseModel(unittest.TestCase):
    def test_setattr_properly_works(self):
        with pm.Model() as model:
            pm.Normal('v1')
            self.assertEqual(len(model.vars), 1)
            with pm.Model('sub') as submodel:
                submodel.Var('v1', pm.Normal.dist())
                self.assertTrue(hasattr(submodel, 'v1'))
                self.assertEqual(len(submodel.vars), 1)
            self.assertEqual(len(model.vars), 2)
            with submodel:
                submodel.Var('v2', pm.Normal.dist())
                self.assertTrue(hasattr(submodel, 'v2'))
                self.assertEqual(len(submodel.vars), 2)
            self.assertEqual(len(model.vars), 3)

    def test_context_passes_vars_to_parent_model(self):
        with pm.Model() as model:
            # a set of variables is created
            NewModel()
            # another set of variables are created but with prefix 'another'
            usermodel2 = NewModel(name='another')
            # you can enter in a context with submodel
            with usermodel2:
                usermodel2.Var('v3', pm.Normal.dist())
                pm.Normal('v4')
                # this variable is created in parent model too
        self.assertIn('another_v2', model.named_vars)
        self.assertIn('another_v3', model.named_vars)
        self.assertIn('another_v3', usermodel2.named_vars)
        self.assertIn('another_v4', model.named_vars)
        self.assertIn('another_v4', usermodel2.named_vars)
        self.assertTrue(hasattr(usermodel2, 'v3'))
        self.assertTrue(hasattr(usermodel2, 'v2'))
        self.assertTrue(hasattr(usermodel2, 'v4'))
        # When you create a class based model you should follow some rules
        with model:
            m = NewModel('one_more')
        self.assertTrue(m.d is model['one_more_d'])
        self.assertTrue(m['d'] is model['one_more_d'])
        self.assertTrue(m['one_more_d'] is model['one_more_d'])


class TestNested(unittest.TestCase):
    def test_nest_context_works(self):
        with pm.Model() as m:
            new = NewModel()
            with new:
                self.assertTrue(
                    pm.modelcontext(None) is new
                )
            self.assertTrue(
                pm.modelcontext(None) is m
            )
        self.assertIn('v1', m.named_vars)
        self.assertIn('v2', m.named_vars)

    def test_named_context(self):
        with pm.Model() as m:
            NewModel(name='new')
        self.assertIn('new_v1', m.named_vars)
        self.assertIn('new_v2', m.named_vars)

    def test_docstring_example1(self):
        usage1 = DocstringModel()
        self.assertIn('v1', usage1.named_vars)
        self.assertIn('v2', usage1.named_vars)
        self.assertIn('v3', usage1.named_vars)
        self.assertIn('v3_sq', usage1.named_vars)
        self.assertTrue(len(usage1.potentials), 1)

    def test_docstring_example2(self):
        with pm.Model() as model:
            DocstringModel(name='prefix')
        self.assertIn('prefix_v1', model.named_vars)
        self.assertIn('prefix_v2', model.named_vars)
        self.assertIn('prefix_v3', model.named_vars)
        self.assertIn('prefix_v3_sq', model.named_vars)
        self.assertTrue(len(model.potentials), 1)

    def test_duplicates_detection(self):
        with pm.Model():
            DocstringModel(name='prefix')
            self.assertRaises(ValueError, DocstringModel, name='prefix')

    def test_model_root(self):
        with pm.Model() as model:
            self.assertTrue(model is model.root)
            with pm.Model() as sub:
                self.assertTrue(model is sub.root)
