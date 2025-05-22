import json
import base64

# Read the notebook
with open('notebook.ipynb', 'r') as f:
    notebook_content = json.load(f)

# Find the cell with the workflow image
for cell in notebook_content['cells']:
    if cell['cell_type'] == 'code' and 'outputs' in cell:
        for output in cell['outputs']:
            if 'data' in output and 'image/png' in output['data']:
                # Extract the base64 encoded image
                image_data = output['data']['image/png']
                # Decode the base64 image
                image_bytes = base64.b64decode(image_data)
                # Save the image
                with open('agent_workflow.png', 'wb') as img_file:
                    img_file.write(image_bytes)
                    print("Workflow image extracted and saved as agent_workflow.png")
                    exit(0)

print("No workflow image found in the notebook.") 