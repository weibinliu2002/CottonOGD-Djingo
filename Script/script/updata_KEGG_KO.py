import json
import re
import pymysql

def import_kegg_ko_data(json_file_path):
    conn = pymysql.connect(
        host='localhost',
        user='root',
        password='1234',
        db='cottonogd-ortho',
        charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor
    )
    cursor = conn.cursor()

    with open(json_file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    def collect_all_items(data, categories=[], pathways=[], ko_enzymes=[], current_category_id=None, parent_category_id=None):
        """收集所有数据，保留层级关系"""
        if not data:
            return categories, pathways, ko_enzymes

        name = data.get('name', '')
        children = data.get('children', [])

        if '[PATH:' in name:
            pathway_id = name.split()[0] if name.split() else ''
            pathway_name = ' '.join(name.split()[1:]) if name.split()[1:] else name

            ko_match = re.search(r'\[PATH:ko(\d+)\]', pathway_name)
            ko_id = f"ko{ko_match.group(1)}" if ko_match else None

            pathways.append({
                'pathway_id': pathway_id,
                'name': pathway_name.split('[')[0].strip(),
                'full_name': pathway_name,
                'ko_id': ko_id,
                'category_id': current_category_id
            })

            for enzyme_data in children:
                enzyme_name = enzyme_data.get('name', '')
                
                ko_match = re.match(r'^([^\s]+)\s+(.*)', enzyme_name)
                enzyme_ko_id = ko_match.group(1) if ko_match else enzyme_name.split()[0] if enzyme_name.split() else ''
                
                ec_match = re.search(r'\[EC:(.*?)\]', enzyme_name)
                ec_number = ec_match.group(1) if ec_match else None
                
                if ';' in enzyme_name:
                    enzyme_name_clean = enzyme_name.split(';')[1].strip()
                elif '[' in enzyme_name:
                    enzyme_name_clean = enzyme_name.split('[')[0].strip()
                else:
                    enzyme_name_clean = enzyme_name

                ko_enzymes.append({
                    'pathway_id': pathway_id,
                    'ko_id': enzyme_ko_id,
                    'name': enzyme_name_clean,
                    'ec_number': ec_number,
                    'full_name': enzyme_name
                })
        else:
            category_id = name.split()[0] if name.split() else ''
            category_name = ' '.join(name.split()[1:]) if name.split()[1:] else name

            if category_id and category_id != 'ko00001':
                categories.append({
                    'category_id': category_id,
                    'name': category_name,
                    'parent_id': parent_category_id
                })

                for child in children:
                    collect_all_items(child, categories, pathways, ko_enzymes, category_id, parent_category_id=None if parent_category_id else category_id)
            else:
                for child in children:
                    collect_all_items(child, categories, pathways, ko_enzymes, current_category_id, parent_category_id)

        return categories, pathways, ko_enzymes

    print("正在收集数据...")
    categories, pathways, ko_enzymes = collect_all_items(data)

    print("正在清空现有数据...")
    cursor.execute('SET FOREIGN_KEY_CHECKS = 0')
    cursor.execute('TRUNCATE TABLE pathway_enzyme')
    cursor.execute('TRUNCATE TABLE ko_term')
    cursor.execute('TRUNCATE TABLE metabolic_pathway')
    cursor.execute('TRUNCATE TABLE ec_number')
    cursor.execute('TRUNCATE TABLE category')
    cursor.execute('SET FOREIGN_KEY_CHECKS = 1')
    conn.commit()

    print("正在导入分类...")
    for cat in categories:
        try:
            cursor.execute("""
                INSERT INTO category (category_id, name, parent_id)
                VALUES (%s, %s, %s)
                ON DUPLICATE KEY UPDATE name = VALUES(name), parent_id = VALUES(parent_id)
            """, (cat['category_id'], cat['name'], cat['parent_id']))
        except pymysql.Error as e:
            print(f"Error inserting category {cat['category_id']}: {e}")
    conn.commit()

    print("正在导入代谢通路...")
    for pathway in pathways:
        try:
            cursor.execute("""
                INSERT INTO metabolic_pathway (pathway_id, name, full_name, ko_id, category_id)
                VALUES (%s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE name = VALUES(name), full_name = VALUES(full_name), ko_id = VALUES(ko_id), category_id = VALUES(category_id)
            """, (pathway['pathway_id'], pathway['name'], pathway['full_name'], pathway['ko_id'], pathway['category_id']))
        except pymysql.Error as e:
            print(f"Error inserting pathway {pathway['pathway_id']}: {e}")
    conn.commit()

    print("正在导入KO术语...")
    ko_set = set()
    for item in ko_enzymes:
        if item['ko_id'] and item['ko_id'] not in ko_set:
            ko_set.add(item['ko_id'])
            ec_numbers = item['ec_number'].split() if item['ec_number'] else []
            ec_number = ec_numbers[0] if ec_numbers else None
            
            try:
                cursor.execute("""
                    INSERT INTO ko_term (ko_id, name, ec_number, full_name, is_enzyme)
                    VALUES (%s, %s, %s, %s, 1)
                    ON DUPLICATE KEY UPDATE name = VALUES(name), ec_number = VALUES(ec_number), full_name = VALUES(full_name), is_enzyme = VALUES(is_enzyme)
                """, (item['ko_id'], item['name'], ec_number, item['full_name']))
            except pymysql.Error as e:
                print(f"Error inserting KO term {item['ko_id']}: {e}")
    conn.commit()

    print("正在导入EC编号...")
    ec_set = set()
    for item in ko_enzymes:
        if item['ec_number']:
            ec_numbers = [e.strip() for e in item['ec_number'].split()]
            for ec in ec_numbers:
                if ec and ec not in ec_set:
                    ec_set.add(ec)
                    try:
                        cursor.execute("""
                            INSERT INTO ec_number (ec_number, name)
                            VALUES (%s, %s)
                            ON DUPLICATE KEY UPDATE name = VALUES(name)
                        """, (ec, item['name']))
                    except pymysql.Error as e:
                        print(f"Error inserting EC number {ec}: {e}")
    conn.commit()

    print("正在导入通路-酶关联...")
    for item in ko_enzymes:
        if item['ko_id'] and item['pathway_id']:
            try:
                cursor.execute("""
                    INSERT INTO pathway_enzyme (pathway_id, enzyme_id)
                    VALUES (%s, %s)
                    ON DUPLICATE KEY UPDATE pathway_id = VALUES(pathway_id)
                """, (item['pathway_id'], item['ko_id']))
            except pymysql.Error as e:
                print(f"Error inserting pathway_enzyme {item['pathway_id']} - {item['ko_id']}: {e}")
    conn.commit()

    cursor.close()
    conn.close()
    print("KEGG KO数据导入完成！")
    print(f"导入统计：分类 {len(categories)} 条，通路 {len(pathways)} 条，KO术语 {len(ko_set)} 条，EC编号 {len(ec_set)} 条，关联 {len(ko_enzymes)} 条")

if __name__ == '__main__':
    json_file = '/data/web/CottonOGD/OGD/backend/data/go_ontology/ko00001.json'
    import_kegg_ko_data(json_file)