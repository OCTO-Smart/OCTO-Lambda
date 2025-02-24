import { S3Client, PutObjectCommand } from "@aws-sdk/client-s3";

// S3 client oluştur
const s3 = new S3Client({ region: "eu-central-1" });  // Kendi bölgeni ekle

// S3 bucket adı
const BUCKET_NAME = "ivocdevices";


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