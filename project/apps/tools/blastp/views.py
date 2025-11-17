from django.views import View
from django.shortcuts import render, HttpResponse
from django.db import connection
import tempfile
import os
import json 
import subprocess
import shutil
import time
from collections import defaultdict
from Bio import SeqIO
from Bio.Seq import Seq
from Bio.SeqRecord import SeqRecord
from Bio.Blast import NCBIXML

class BlastpView(View):
    template_name = 'tools/blastp/blastp.html'
    results_template = 'tools/blastp/blastp_results.html'
    
    def get(self, request):
        """显示BLASTP搜索表单"""
        return render(request, self.template_name)
    
    def post(self, request):
        """处理BLASTP搜索请求"""
        sequence = request.POST.get('sequence', '').strip()
        evalue = request.POST.get('evalue', '0.01')
        max_target_seqs = request.POST.get('max_target_seqs', '30')
        
        if not sequence:
            return render(request, self.template_name, {
                'error': 'Please provide a protein sequence'
            })
        
        temp_dir = tempfile.mkdtemp()
        
        try:
            # 1. 准备查询序列文件
            query_file = os.path.join(temp_dir, 'query.fasta')
            self._create_query_file(query_file, sequence)
            
            # 2. 创建BLAST数据库
            db_file = os.path.join(temp_dir, 'db.fasta')
            db_name = os.path.join(temp_dir, 'blast_db')
            self._create_blast_database(db_file, db_name)
            
            # 3. 执行BLASTP搜索
            output_file = os.path.join(temp_dir, 'results.xml')
            start_time = time.time()
            self._run_blastp(
                query_file=query_file,
                db_path=db_name,
                evalue=evalue,
                max_target_seqs=max_target_seqs,
                output_file=output_file
            )
            
            # 4. 解析结果
            blast_data = self._parse_blast_results(output_file)
            
            chord_data = {
                'query': 'Query_Protein',
                'queryLength': blast_data['query_length'],
                'proteins': [{'id': pid, 'length': blast_data['protein_lengths'][pid]} 
                           for pid in blast_data['protein_lengths']],
                'hits': [{
                    'query': 'Query_Protein',
                    'target': hit['protein_id'],
                    'evalue': str(hit['evalue']),
                    'score': hit['score'],
                    'identity': hit['identity'],
                    'qStart': hit['qStart'],
                    'qEnd': hit['qEnd'],
                } for hit in blast_data['hits']]
            }

            return render(request, self.results_template, {
                'query_sequence': sequence,
                'hits': blast_data['hits'],
                'execution_time': round(time.time() - start_time, 2),
                'evalue': evalue,
                'max_target_seqs': max_target_seqs,
                'chord_data_json': chord_data
            })
            
        except subprocess.CalledProcessError as e:
            return render(request, self.template_name, {
                'error': f"BLAST执行失败: {e.stderr.decode('utf-8') if e.stderr else str(e)}"
            })
            
        except Exception as e:
            return render(request, self.template_name, {
                'error': f"系统错误: {str(e)}"
            })
            
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
    
    def _create_query_file(self, path, sequence):
        """创建查询序列文件"""
        with open(path, 'w') as f:
            f.write(f">query\n{sequence}")
    
    def _create_blast_database(self, fasta_path, db_name):
        """从MySQL数据创建BLAST数据库"""
        records = []
        id_counter = defaultdict(int)
        
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT 
                    protein_id, 
                    REGEXP_REPLACE(UPPER(sequence), '[^ACDEFGHIKLMNPQRSTVWY]', '') as clean_sequence
                FROM blastp
                WHERE LENGTH(sequence) > 0
            """)
            
            for protein_id, sequence in cursor.fetchall():
                base_id = protein_id.replace("@", "_").strip()[:45]
                id_counter[base_id] += 1
                clean_id = base_id if id_counter[base_id] == 1 else f"{base_id}_dup{id_counter[base_id]}"
                
                records.append(SeqRecord(
                    Seq(sequence),
                    id=clean_id,
                    description=""
                ))
        
        if not records:
            raise ValueError("数据库中没有有效序列！")
        
        SeqIO.write(records, fasta_path, "fasta")
        
        cmd = [
            'makeblastdb',
            '-in', fasta_path,
            '-dbtype', 'prot',
            '-out', db_name,
            '-parse_seqids',
            '-hash_index'
        ]
        
        subprocess.run(cmd, check=True)
    
    def _run_blastp(self, query_file, db_path, evalue, max_target_seqs, output_file):
        """执行BLASTP搜索"""
        cmd = [
            'blastp',
            '-query', query_file,
            '-db', db_path,
            '-evalue', evalue,
            '-outfmt', '5',
            '-out', output_file,
            '-num_threads', '4',
            '-max_target_seqs', max_target_seqs,
            '-seg', 'yes'
        ]
        
        subprocess.run(cmd, check=True)
    
    def _parse_blast_results(self, xml_path):
        """解析BLAST结果"""
        with open(xml_path, 'r') as f:
            blast_records = NCBIXML.parse(f)
            
            hits = []
            proteins = set()
            query_length = 0
            
            for blast_record in blast_records:
                query_length = blast_record.query_length
                for alignment in blast_record.alignments:
                    protein_id = alignment.hit_id.split('|')[0]
                    proteins.add(protein_id)
                    for hsp in alignment.hsps:
                        identity_percent = (hsp.identities / hsp.align_length) * 100
                        
                        hits.append({
                            'protein_id': protein_id,
                            'identity': round(identity_percent, 2),
                            'score': hsp.score,
                            'evalue': hsp.expect,
                            'qStart': hsp.query_start,
                            'qEnd': hsp.query_end,
                            'length': alignment.length,
                        })
            
            protein_lengths = self._get_protein_lengths(list(proteins))
            for hit in hits:
                if hit['protein_id'] not in protein_lengths:
                    protein_lengths[hit['protein_id']] = hit['length']
            
            return {
                'hits': hits,
                'query_length': query_length,
                'protein_lengths': protein_lengths,
            }
    
    def _get_protein_lengths(self, protein_ids):
        """从数据库获取蛋白质长度"""
        if not protein_ids:
            return {}

        with connection.cursor() as cursor:
            unique_ids = list(set(protein_ids))
            placeholders = ','.join(['%s'] * len(unique_ids))
            
            query = f"""
                SELECT protein_id, LENGTH(sequence) as length
                FROM blastp 
                WHERE protein_id IN ({placeholders})
            """
            
            cursor.execute(query, tuple(unique_ids))
            results = cursor.fetchall()
            
            return {row[0]: row[1] for row in results}


class ProteinDetailView(View):
    """蛋白质详情视图"""
    template_name = 'tools/protein_detail.html'
    
    def get(self, request, protein_id):
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT 
                    protein_id, 
                    gene_id, 
                    description, 
                    sequence, 
                    file_source, 
                    created_at
                FROM blastp 
                WHERE protein_id = %s
            """, [protein_id])
            columns = [col[0] for col in cursor.description]
            protein = dict(zip(columns, cursor.fetchone())) if cursor.rowcount > 0 else None
        
        if not protein:
            return HttpResponse("Protein not found", status=404)
        
        return render(request, self.template_name, {'protein': protein})


class DownloadSequenceView(View):
    """序列下载视图"""
    def get(self, request, protein_id):
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT sequence 
                FROM blastp 
                WHERE protein_id = %s
            """, [protein_id])
            row = cursor.fetchone()
        
        if not row:
            return HttpResponse("Protein not found", status=404)
        
        response = HttpResponse(row[0], content_type='text/plain')
        response['Content-Disposition'] = f'attachment; filename="{protein_id}.fasta"'
        return response