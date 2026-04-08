# Earthquake Detector for USGS

## Deliverables

Submit the following in the Canvas assignment:

1. **Your Data Application Plot URL** — the public `http://` URL to your `plot.png` served from your S3 website bucket (e.g., `http://your-bucket-name.s3-website-us-east-1.amazonaws.com/plot.png`). The plot must represent at least 72 hours / 72 entries of data. Paste the URL directly — if the image does not load it will not be graded.

2. **Your Data Application Repo URL** — the public GitHub URL to your pipeline code. The repository must include the Python script, a `Dockerfile`, and a `requirements.txt`.

3. **Canvas Quiz** — answer the short-answer questions posted in Canvas. These will ask you to reflect on what you built, including:
    - Which data source you chose and why.
    - What you observe in the data — any patterns, spikes, or surprises over the 72-hour window.
    - How Kubernetes Secrets differ from plain environment variables and why that distinction matters.
    - How your CronJob pods gain permission to read/write to AWS services without credentials appearing in any file.
    - One thing you would do differently if you were building this pipeline for a real production system.

### Graduate Students

In addition to the above, submit a short written response (one paragraph each) to the following:

1. In the ISS sample application, data is persisted in DynamoDB. If this were a much higher-frequency application (hundreds of writes per minute), what changes would you make to the persistence strategy and why?
2. The ISS tracker detects orbital burns by comparing consecutive altitude readings. Describe at least one way this detection logic could produce a false positive, and how you would make it more robust.
3. How does each `CronJob` pod get AWS permissions without credentials being passed into the container?
4. Notice the structure of the `iss-tracking` table in DynamoDB. What is the partition key and what is the sort key? Why do these work well in this example, but may not work for other solutions?
