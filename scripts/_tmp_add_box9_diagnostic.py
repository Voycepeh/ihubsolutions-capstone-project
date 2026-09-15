import json
from pathlib import Path
import nbformat

nb_path = Path('notebooks/Inital EDA v2.ipynb')
nb = nbformat.read(nb_path, as_version=4)

remove_ids = {'box9-question-heading','box9-question-table','box9-question-note'}
nb.cells = [c for c in nb.cells if c.get('id') not in remove_ids]

insert_at = None
for i, cell in enumerate(nb.cells):
    if cell.cell_type == 'markdown' and cell.get('id') == 'util-gt6-insight':
        insert_at = i + 1
        break
if insert_at is None:
    for i, cell in enumerate(nb.cells):
        if cell.cell_type == 'markdown' and '## 8.' in ''.join(cell.source):
            insert_at = i
            break
if insert_at is None:
    raise RuntimeError('Could not locate insertion point after section 7')

heading = nbformat.v4.new_markdown_cell(
    '### Box9 orders above the 70% threshold\n\n'
    'The table below lists **all Box9 cases where the reference output reports `UsedSpace > 70%`**. '
    'It includes the exact `OrderId`, total physical item quantity, raw Box9 `UsedSpace`, and the raw input `ItemsList` JSON from `data_samples_v2.json`. '
    'This is included so the cases can be sent directly to iHub for clarification.'
)
heading['id'] = 'box9-question-heading'

code = nbformat.v4.new_code_cell('''box9_over_70 = []\nfor rec in raw:\n    order_id = rec["input"]["OrderId"]\n    raw_items = rec["input"]["Items"]["ItemsList"]\n    physical_items = sum(item["Quantity"] for item in raw_items)\n    for packed_bin in rec["output"]["Data"]["BinsPacked"]:\n        if packed_bin["Code"] == "Box9" and float(packed_bin["UsedSpace"]) > 70:\n            box9_over_70.append({\n                "OrderId": order_id,\n                "physical_items": physical_items,\n                "Box9_UsedSpace_raw": packed_bin["UsedSpace"],\n                "Raw_ItemsList": json.dumps(raw_items, ensure_ascii=False, separators=(",", ":")),\n            })\n\nbox9_over_70_df = pd.DataFrame(box9_over_70).sort_values(["Box9_UsedSpace_raw", "OrderId"], ascending=[False, True]).reset_index(drop=True)\nprint(f"Box9 orders above 70%: {len(box9_over_70_df):,} unique orders")\ndisplay(box9_over_70_df)''')
code['id'] = 'box9-question-table'

note = nbformat.v4.new_markdown_cell(
    '**Question for iHub.** The supplied v2 parameters indicate a 70% maximum fill check once the item-count threshold is exceeded, '
    'yet these Box9 reference outputs are above 70%. Is Box9 intentionally exempt from `BinMaxFillPct`, or is there additional Box9-specific '
    'logic in the current service that is not represented in the supplied request parameters?'
)
note['id'] = 'box9-question-note'

nb.cells[insert_at:insert_at] = [heading, code, note]
nbformat.write(nb, nb_path)
