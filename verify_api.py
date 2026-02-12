from app import create_app, db
from app.models.Mortor_inspection import TJob, InspectionResult

app = create_app('development')

with app.app_context():
    print("Verifying TJob.to_dict()...")
    # Fetch a job (if any exists, otherwise skip or mock)
    job = TJob.query.first()
    if job:
        data = job.to_dict(include_results=True)
        print(f"Job ID: {data.get('actid')}")
        print(f"Total Items: {data.get('total_items')}")
        print(f"Completed Items: {data.get('completed_items')}")
        print(f"Act Mem Name: {data.get('act_mem_name')}")
        
        if 'results' in data and data['results']:
            print("\nVerifying InspectionResult.to_dict()...")
            res = data['results'][0]
            print(f"Item ID: {res.get('item_id')}")
            print(f"Abnormal Reason: {res.get('abnormal_reason')}")
            print(f"Is Processed: {res.get('is_processed')}")
    else:
        print("No jobs found in database to verify.")
