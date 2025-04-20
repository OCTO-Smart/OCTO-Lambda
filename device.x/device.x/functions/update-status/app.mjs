import { S3Client, PutObjectCommand } from "@aws-sdk/client-s3";
import pkg from 'pg';
const { Client } = pkg;

import * as fs from 'fs'; 
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Start log
console.log("App installed (app.mjs file).");

const REGION = "eu-central-1";
const BUCKET_NAME = "ivocdevices";

const DB_HOST = "ivocdev.cxiqcy2uo0c3.eu-central-1.rds.amazonaws.com";
const DB_NAME = "ivocdev";
const DB_USER = "ivoc";
const DB_PASSWORD = "ivocDevDB!";

// Create S3 client
const s3 = new S3Client({ region: REGION });

export const lambdaHandler = async (event, context) => {
  console.log("Lambda started .");

  try {
    console.log("Incoming event:", JSON.stringify(event));

    const data = event.body ? JSON.parse(event.body) : event;
    console.log("JSON parsed:", data);

    const deviceName = data.dn;
    if (!deviceName) throw new Error("Device name (dn) not found in JSON");
    console.log("Device name :", deviceName);

    const pemPath = path.join(__dirname, 'eu-central-1-bundle.pem');
    console.log("PEM way:", pemPath);
    console.log("Is there a PEM file:", fs.existsSync(pemPath) ? "Yes " : "No ");

    // Temporary test connection instead of PEM
    const client = new Client({
      host: DB_HOST,
      database: DB_NAME,
      user: DB_USER,
      password: DB_PASSWORD,
      port: 5432,
      ssl: {
        rejectUnauthorized: false // <-- PEM disabled for testing
      }
    });

    console.log("Connecting to database...");
    await client.connect();
    console.log("DB connection successful.");

    const res = await client.query(
      "SELECT id FROM device WHERE name = $1",
      [deviceName]
    );

    const deviceId = res.rows[0]?.id;
    console.log("Found device_id: ", deviceId);

    if (!deviceId) throw new Error(`Device '${deviceName}' not found in devices table`);

    await client.query(
      "UPDATE device_status SET status = $1, updated_at = NOW() WHERE device_id = $2",
      [JSON.stringify(data), deviceId]
    );

    console.log("Status has been updated. ");
    await client.end();

    const fileName = `${deviceName}-${Date.now()}.json`;
    const uploadParams = {
      Bucket: BUCKET_NAME,
      Key: fileName,
      Body: JSON.stringify(data),
      ContentType: "application/json"
    };

    console.log("Writing to S3: ", fileName);
    await s3.send(new PutObjectCommand(uploadParams));
    console.log("Successfully written to S3. ");

    return {
      statusCode: 200,
      body: JSON.stringify({
        message: "Data was successfully written to S3 and PostgreSQL.",
        fileName: fileName
      }),
      headers: {
        "Content-Type": "application/json"
      }
    };

  } catch (error) {
    console.error("ERROR:", error);
    return {
      statusCode: 500,
      body: JSON.stringify({ error: error.message }),
      headers: {
        "Content-Type": "application/json"
      }
    };
  }
};
