"""
PPI STRING 接口测试。

全部 mock 外部依赖（STRING API、trembl BLAST 表），不访问真实数据库或网络。
"""
from unittest import mock

from django.test import TestCase
from rest_framework.test import APIClient

from CottonOGD.views import ppi_string as _view_module
from CottonOGD import views as _views_pkg  # noqa: F401  (ensure import path)


URL = '/CottonOGD_api/ppi/string/'


class PpiStringTestBase(TestCase):
    def setUp(self):
        self.client = APIClient()

    def _mock_service(self, resolve_taxon='3635', mapping=None, unmapped=None,
                      edges=None, raise_cls=None):
        """统一 mock string_service 的关键函数。"""
        if mapping is None:
            mapping = {
                'geneA': {'taxid': '3635', 'string_id': '3635.A1', 'preferred_name': 'GeneA', 'pid': 95.0},
                'geneB': {'taxid': '3635', 'string_id': '3635.B1', 'preferred_name': 'GeneB', 'pid': 92.0},
                'geneC': {'taxid': '3635', 'string_id': '3635.C1', 'preferred_name': 'GeneC', 'pid': 90.0},
            }
        if unmapped is None:
            unmapped = []
        if edges is None:
            edges = [
                {'stringId_A': '3635.A1', 'stringId_B': '3635.B1', 'score': 0.85},
                {'stringId_A': '3635.B1', 'stringId_B': '3635.C1', 'score': 0.72},
            ]

        patchers = []
        p = mock.patch.object(_view_module.string_service, 'resolve_taxon',
                              return_value=resolve_taxon)
        p.start(); patchers.append(p)

        if raise_cls is not None:
            p = mock.patch.object(_view_module.string_service, 'map_genes_to_string',
                                  side_effect=raise_cls('boom'))
        else:
            p = mock.patch.object(_view_module.string_service, 'map_genes_to_string',
                                  return_value=(mapping, unmapped))
        p.start(); patchers.append(p)

        p = mock.patch.object(_view_module.string_service, 'fetch_interactions',
                              return_value=edges)
        p.start(); patchers.append(p)

        self._patchers = patchers
        return mapping, unmapped, edges

    def tearDown(self):
        for p in getattr(self, '_patchers', []):
            p.stop()


class TestNormalNetwork(PpiStringTestBase):
    def test_normal_network(self):
        self._mock_service()
        resp = self.client.post(URL, {
            'gene_ids': ['geneA', 'geneB', 'geneC'],
            'genome_id': 'G.hirsutumAD1_TM-1_HAU_v1.1',
        }, format='json')
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body['code'], 0)
        self.assertEqual(len(body['data']['elements']['nodes']), 3)
        self.assertEqual(len(body['data']['elements']['edges']), 2)
        self.assertEqual(body['data']['stats']['mapped_genes'], 3)
        self.assertEqual(body['data']['stats']['edges'], 2)


class TestPartialMapping(PpiStringTestBase):
    def test_partial_unmapped_reported(self):
        mapping = {
            'geneA': {'taxid': '3635', 'string_id': '3635.A1', 'preferred_name': 'GeneA', 'pid': 95.0},
            'geneB': {'taxid': '3635', 'string_id': '3635.B1', 'preferred_name': 'GeneB', 'pid': 92.0},
            'geneC': {'taxid': '3635', 'string_id': '3635.C1', 'preferred_name': 'GeneC', 'pid': 90.0},
        }
        self._mock_service(mapping=mapping, unmapped=['geneD', 'geneE'])
        resp = self.client.post(URL, {
            'gene_ids': ['geneA', 'geneB', 'geneC', 'geneD', 'geneE'],
            'genome_id': 'G.hirsutumAD1_TM-1_HAU_v1.1',
        }, format='json')
        body = resp.json()
        self.assertEqual(body['code'], 0)
        self.assertEqual(len(body['data']['elements']['nodes']), 3)
        self.assertEqual(body['data']['stats']['unmapped_genes'], 2)
        self.assertIn('geneD', body['message'])


class TestAllUnmapped(PpiStringTestBase):
    def test_all_unmapped(self):
        self._mock_service(mapping={}, unmapped=['geneA', 'geneB'])
        resp = self.client.post(URL, {
            'gene_ids': ['geneA', 'geneB'],
            'genome_id': 'G.hirsutumAD1_TM-1_HAU_v1.1',
        }, format='json')
        self.assertEqual(resp.status_code, 422)
        self.assertEqual(resp.json()['code'], 4)


class TestNoEdges(PpiStringTestBase):
    def test_no_interactions(self):
        self._mock_service(edges=[])
        resp = self.client.post(URL, {
            'gene_ids': ['geneA', 'geneB'],
            'genome_id': 'G.hirsutumAD1_TM-1_HAU_v1.1',
        }, format='json')
        body = resp.json()
        self.assertEqual(body['code'], 0)
        self.assertGreater(len(body['data']['elements']['nodes']), 0)
        self.assertEqual(len(body['data']['elements']['edges']), 0)


class TestInvalidInput(PpiStringTestBase):
    def test_gene_ids_not_list(self):
        resp = self.client.post(URL, {
            'gene_ids': 'geneA',
            'genome_id': 'G.hirsutumAD1_TM-1_HAU_v1.1',
        }, format='json')
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json()['code'], 1)

    def test_gene_ids_empty(self):
        resp = self.client.post(URL, {
            'gene_ids': [],
            'genome_id': 'G.hirsutumAD1_TM-1_HAU_v1.1',
        }, format='json')
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json()['code'], 1)

    def test_gene_ids_non_string_elem(self):
        resp = self.client.post(URL, {
            'gene_ids': ['geneA', 123],
            'genome_id': 'G.hirsutumAD1_TM-1_HAU_v1.1',
        }, format='json')
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json()['code'], 1)

    def test_missing_genome_id(self):
        resp = self.client.post(URL, {
            'gene_ids': ['geneA'],
        }, format='json')
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json()['code'], 1)

    def test_empty_genome_id(self):
        resp = self.client.post(URL, {
            'gene_ids': ['geneA'],
            'genome_id': '   ',
        }, format='json')
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json()['code'], 1)

    def test_too_many_genes(self):
        resp = self.client.post(URL, {
            'gene_ids': [f'gene{i}' for i in range(301)],
            'genome_id': 'G.hirsutumAD1_TM-1_HAU_v1.1',
        }, format='json')
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json()['code'], 1)

    def test_score_threshold_out_of_range(self):
        self._mock_service()
        resp = self.client.post(URL, {
            'gene_ids': ['geneA', 'geneB'],
            'genome_id': 'G.hirsutumAD1_TM-1_HAU_v1.1',
            'score_threshold': 50,
        }, format='json')
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json()['code'], 1)


class TestUnsupportedGenome(PpiStringTestBase):
    def test_unmapped_genome(self):
        self._mock_service(resolve_taxon=None)
        resp = self.client.post(URL, {
            'gene_ids': ['geneA'],
            'genome_id': 'UnknownGenome_XYZ',
        }, format='json')
        self.assertEqual(resp.status_code, 422)
        self.assertEqual(resp.json()['code'], 2)

    def test_no_blast_table(self):
        self._mock_service(
            raise_cls=RuntimeError)
        resp = self.client.post(URL, {
            'gene_ids': ['geneA'],
            'genome_id': 'G.hirsutumAD1_TM-1_HAU_v1.1',
        }, format='json')
        self.assertEqual(resp.status_code, 422)
        self.assertEqual(resp.json()['code'], 3)


class TestStringFailure(PpiStringTestBase):
    def test_string_timeout(self):
        self._mock_service()
        with mock.patch.object(_view_module.string_service, 'fetch_interactions',
                               side_effect=__import__('requests').Timeout):
            resp = self.client.post(URL, {
                'gene_ids': ['geneA', 'geneB'],
                'genome_id': 'G.hirsutumAD1_TM-1_HAU_v1.1',
            }, format='json')
        self.assertEqual(resp.status_code, 504)
        self.assertEqual(resp.json()['code'], 5)

    def test_string_connection_error(self):
        self._mock_service()
        with mock.patch.object(_view_module.string_service, 'fetch_interactions',
                               side_effect=__import__('requests').ConnectionError):
            resp = self.client.post(URL, {
                'gene_ids': ['geneA', 'geneB'],
                'genome_id': 'G.hirsutumAD1_TM-1_HAU_v1.1',
            }, format='json')
        self.assertEqual(resp.status_code, 502)
        self.assertEqual(resp.json()['code'], 6)


class TestCytoscapeStructure(PpiStringTestBase):
    def test_structure_constraints(self):
        self._mock_service()
        resp = self.client.post(URL, {
            'gene_ids': ['geneA', 'geneB', 'geneC'],
            'genome_id': 'G.hirsutumAD1_TM-1_HAU_v1.1',
        }, format='json')
        data = resp.json()['data']
        nodes = data['elements']['nodes']
        edges = data['elements']['edges']

        # 节点 id 唯一
        node_ids = [n['data']['id'] for n in nodes]
        self.assertEqual(len(node_ids), len(set(node_ids)))

        # 边 id 唯一
        edge_ids = [e['data']['id'] for e in edges]
        self.assertEqual(len(edge_ids), len(set(edge_ids)))

        # 边 source/target 引用已返回节点
        node_set = set(node_ids)
        for e in edges:
            self.assertIn(e['data']['source'], node_set)
            self.assertIn(e['data']['target'], node_set)
            # score 为 0-1000 整数
            self.assertIsInstance(e['data']['score'], int)
            self.assertGreaterEqual(e['data']['score'], 0)
            self.assertLessEqual(e['data']['score'], 1000)

        # 节点含 id 与 label
        for n in nodes:
            self.assertIn('id', n['data'])
            self.assertIn('label', n['data'])
