# Earthquake Detector for USGS

### Deliverables

Submit the following in the Canvas assignment:

1. **Your Data Application Plot URL** — the public `http://` URL to your `plot.png` served from your S3 website bucket (e.g., `http://your-bucket-name.s3-website-us-east-1.amazonaws.com/plot.png`). The plot must represent at least 72 hours / 72 entries of data. Paste the URL directly — if the image does not load it will not be graded.

2. **Your Data Application Repo URL** — the public GitHub URL to your pipeline code. The repository must include the Python script, a `Dockerfile`, and a `requirements.txt`.

3. **Canvas Quiz** — answer the short-answer questions posted in Canvas. These will ask you to reflect on what you built, including:
    - Which data source you chose and why?
      **I chose to collect data on earthquakes because their is a real need to alert people of quakes if they are near the epicenter or have loved ones near the epicenter.**
    - What you observe in the data — any patterns, spikes, or surprises over the 72-hour window?
      **I extended my data past 72 hours due to the frequency of earthquakes. There are earthquakes every day all over Earth and there tends to be many relatively minor quakes with an also small number of moderate earthquakes. There is an infrequent number of major earthquakes which do not occur everyday.**
    - How Kubernetes Secrets differ from plain environment variables and why that distinction matters?
      **Kubernetes Secrets differ from plain text environment variables in that they're encrypted and hidden from copying that may result if they are left unguarded and open to copying. This matters in order to protect the underlying data that the API provides.**
    - How your CronJob pods gain permission to read/write to AWS services without credentials appearing in any file?
      **The EC2 instance has an AMI role assigned to it that grants certain permissions. It queries the EC2 Instance Metadata Service (IMDS) which provides credentials that are temporary and never written to the disk. This protects the underlying secrets.**
    - One thing you would do differently if you were building this pipeline for a real production system?
      **If I was building the pipeline for production I would have to account for the increase in traffic to the S3 bucket and the distributed nature of the requests I'd use a CDN like CloudFront.**

### Graduate Students

In addition to the above, submit a short written response (one paragraph each) to the following:

1. In the ISS sample application, data is persisted in DynamoDB. If this were a much higher-frequency application (hundreds of writes per minute), what changes would you make to the persistence strategy and why?
   **The underlying issue is that DynamoDB partitions cap at ~1,000 WCUs/second. All writes hitting one key will get throttled. To fix this I'd shard the partition key to ISS#0–ISS#9 (distributed by hash(timestamp) % 10), then fan-out reads across shards. You'd need a long-running Deployment or a Kinesis stream + Lambda consumer instead. Switch to batch_writer() (up to 25 items/call) and add a DynamoDB TTL attribute to bound table growth and avoid the expensive fetch_history() full-scan that runs on every execution.**
3. The ISS tracker detects orbital burns by comparing consecutive altitude readings. Describe at least one way this detection logic could produce a false positive, and how you would make it more robust?
   **An API glich could occur that triggers one bad altitude value (interpolation error, stale cache from wheretheiss.at) stores a phantom reading and triggers the label, then the next reading shows a sharp negative delta despite no burn ever occuring.**
5. How does each `CronJob` pod get AWS permissions without credentials being passed into the container?
   **The EC2 node has an IAM instance profile attached at the AWS layer; IMDS hands back temporary STS credentials (key + secret + session token) that are auto-rotated and never written to disk.**
7. Notice the structure of the `iss-tracking` table in DynamoDB. What is the partition key and what is the sort key? Why do these work well in this example, but may not work for other solutions?
   **Partition key: satellite_id (always "ISS") Sort key: timestamp (ISO 8601 string, e.g., "2024-04-09T12:34:56Z"). String timestamps prevent native numeric range arithmetic; epoch-milliseconds as a Number sort key would be more flexible.**

### Link to AWS S3 Bucket
[http://mtk9va-earthquake-detector.s3-website-us-east-1.amazonaws.com/earthquake-activity.png](http://mtk9va-earthquake-detector.s3-website-us-east-1.amazonaws.com/earthquake-activity.png)

### Package
[https://github.com/users/heywoodwt/packages/container/package/earthquake-detector](https://github.com/users/heywoodwt/packages/container/package/earthquake-detector)
