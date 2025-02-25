import { S3Client, PutObjectCommand } from "@aws-sdk/client-s3";
import pkg from 'pg';
const { Client } = pkg;

import * as fs from 'fs'; 
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const REGION = "eu-central-1"
const BUCKET_NAME = "ivocdevices";

const DB_HOST = "ivocdev.cxiqcy2uo0c3.eu-central-1.rds.amazonaws.com";
const DB_NAME = "ivocdev";
const DB_USER = "ivoc";
const DB_PASSWORD = "ivocDevDB!";


// S3 client oluştur
const s3 = new S3Client({ region: REGION }); 

/**
 * Sample Lambda function which mocks the operation of checking the current price of a stock.
 * For demonstration purposes this Lambda function simply returns a random integer between 0 and 100 as the stock price.
 * 
 * @param {Object} event - Input event to the Lambda function
 * @param {Object} context - Lambda Context runtime methods and attributes
 *
 * @returns {Object} object - Object containing the current price of the stock
 * 
 */
export const lambdaHandler = async (event, context) => {
    try {
        console.log("Received event:", JSON.stringify(event));

        // Event'ten 'body' kısmını al (API Gateway kullanılıyorsa body string olabilir)
        const data = event.body ? JSON.parse(event.body) : event;

        if (data.dn == "IVOC2") {
            const client = new Client({
                host: DB_HOST,
                database: DB_NAME,
                user: DB_USER,
                password: DB_PASSWORD,
                port: 5432,
                ssl: {
                    rejectUnauthorized: true, // Ensures SSL verification
                    ca: fs.readFileSync(path.join(__dirname, 'eu-central-1-bundle.pem')).toString()
                }
            });

            await client.connect();

            await client.query(
                "UPDATE device_status SET status = $1, updated_at = NOW() WHERE device_id = $2",
                [JSON.stringify(data), 2]
            );

            await client.end();
        }

        // JSON'u bir dosya olarak kaydetmek için ad oluştur
        const fileName = `${data.dn}.json`;

        // JSON'u S3'e yükle
        const uploadParams = {
            Bucket: BUCKET_NAME,
            Key: fileName,
            Body: JSON.stringify(data),
            ContentType: "application/json"
        };

        await s3.send(new PutObjectCommand(uploadParams));


        // Başarılı yanıt döndür
        return {
            statusCode: 200,
            body: JSON.stringify({
                message: "JSON data successfully saved to S3",
                fileName: fileName
            }),
            headers: {
                "Content-Type": "application/json"
            }
        };
    } catch (error) {
        console.error("Error:", error);
        return {
            statusCode: 500,
            body: JSON.stringify({ error: error.message }),
            headers: {
                "Content-Type": "application/json"
            }
        };
    }
};