import pymysql
import os
import sys,subprocess

def parse_obo(file_path):
    """解析GO OBO文件，返回术语列表和关系列表"""
    terms = []
    relationships = []
    current_term = {}

    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line == '[Term]':
                if current_term:
                    terms.append(current_term)
                    current_term = {}
            elif line.startswith('id:'):
                current_term['id'] = line.split(':', 1)[1].strip()
            elif line.startswith('name:'):
                current_term['name'] = line.split(':', 1)[1].strip()
            elif line.startswith('namespace:'):
                current_term['namespace'] = line.split(':', 1)[1].strip()
            elif line.startswith('def:'):
                def_str = line.split(':', 1)[1].strip()
                if def_str.startswith('"'):
                    def_str = def_str[1:]
                if '"' in def_str:
                    def_str = def_str.split('"', 1)[0]
                if '[' in def_str:
                    def_str = def_str.split('[', 1)[0].strip()
                current_term['definition'] = def_str
            elif line.startswith('is_obsolete:'):
                current_term['is_obsolete'] = True
            # 处理关系（扩展更多类型）
            elif line.startswith('is_a:'):
                relationships.append({
                    'subject_id': current_term['id'],
                    'object_id': line.split(':', 1)[1].strip(),
                    'relationship_type': 'is_a'
                })
            elif line.startswith('part_of:'):
                relationships.append({
                    'subject_id': current_term['id'],
                    'object_id': line.split(':', 1)[1].strip(),
                    'relationship_type': 'part_of'
                })
            elif line.startswith('regulates:'):
                relationships.append({
                    'subject_id': current_term['id'],
                    'object_id': line.split(':', 1)[1].strip(),
                    'relationship_type': 'regulates'
                })
            elif line.startswith('negatively_regulates:'):
                relationships.append({
                    'subject_id': current_term['id'],
                    'object_id': line.split(':', 1)[1].strip(),
                    'relationship_type': 'negatively_regulates'
                })
            elif line.startswith('positively_regulates:'):
                relationships.append({
                    'subject_id': current_term['id'],
                    'object_id': line.split(':', 1)[1].strip(),
                    'relationship_type': 'positively_regulates'
                })
            elif line.startswith('replaced_by:'):  # 新增：处理replaced_by
                relationships.append({
                    'subject_id': current_term['id'],
                    'object_id': line.split(':', 1)[1].strip(),
                    'relationship_type': 'replaced_by'
                })
            elif line.startswith('consider:'):  # 新增：处理consider
                relationships.append({
                    'subject_id': current_term['id'],
                    'object_id': line.split(':', 1)[1].strip(),
                    'relationship_type': 'consider'
                })

    if current_term:
        terms.append(current_term)

    return terms, relationships

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Usage: python import_go_obo.py <path_to_obo_file>")
        sys.exit(1)

    file_path = '../../backend/data/go_ontology/go-basic.obo'
    if not os.path.exists(file_path):
        print(f"Error: File {file_path} not found")
        sys.exit(1)

    terms, relationships = parse_obo(file_path)


    try:
        conn = pymysql.connect(
            host='localhost',
            user='root',
            password='1234',
            db='cottonogd-ortho',
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor
        )
    except pymysql.Error as e:
        print(f"Database connection error: {e}")
        sys.exit(1)

    cursor = conn.cursor()

        # 获取现有术语ID
        subprocess.run(f'mv {file_path} {file_path}_{datetime.now().strftime("%Y%m%d%H%M%S")}.backup', shell=True)
        subprocess.run(f'wget https://purl.obolibrary.org/obo/go/go-basic.obo -o {file_path}', shell=True)
        cursor.execute("SELECT id FROM go_term")
        existing_ids = {row['id'] for row in cursor.fetchall()}

        # 准备新术语数据
        terms_to_insert = []
        for term in terms:
            if term['id'] not in existing_ids:
                terms_to_insert.append((
                    term['id'],
                    term['name'],
                    term['namespace'],
                    term.get('definition', ''),
                    term.get('is_obsolete', False),
                ))

        if terms_to_insert:
            cursor.executemany(
                "INSERT INTO go_term (id, name, namespace, definition, is_obsolete, created_at, updated_at) VALUES (%s, %s, %s, %s, %s, NOW(), NOW())",
                terms_to_insert
            )
            conn.commit()
            print(f"Created {len(terms_to_insert)} new GO terms")

        # 获取所有术语ID（包括新插入的）
        cursor.execute("SELECT id FROM go_term")
        all_term_ids = {row['id'] for row in cursor.fetchall()}

        # 调试：打印关系类型
        print("Relationship types found:")
        for rel in relationships:
            print(f"- {rel['relationship_type']}")

        relationships_to_insert = []
        for rel in relationships:
            subject_id = rel['subject_id']
            object_id = rel['object_id']
            if subject_id in all_term_ids and object_id in all_term_ids:
                relationships_to_insert.append((
                    subject_id,
                    object_id,
                    rel['relationship_type']
                ))

        print(f"Available term IDs: {len(all_term_ids)}")
        print(f"Valid relationships to insert: {len(relationships_to_insert)}")

        if relationships_to_insert:
            cursor.executemany(
                "INSERT INTO go_relationship (subject_id, object_id, relationship_type) VALUES (%s, %s, %s)",
                relationships_to_insert
            )
            conn.commit()
            print(f"Created {len(relationships_to_insert)} new relationships")
        else:
            print("No valid relationships to insert (subject or object not found in go_term)")

    except pymysql.Error as e:
        print(f"Database operation error: {e}")
        conn.rollback()
    finally:
        cursor.close()
        conn.close()

    print("Import completed!")
