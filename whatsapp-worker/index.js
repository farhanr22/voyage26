const { Client, LocalAuth } = require('whatsapp-web.js');
const qrcode = require('qrcode-terminal');
const readline = require('readline-sync');

// === Helper Functions ===
const delay = ms => new Promise(res => setTimeout(res, ms));

const log = (message, type = 'INFO') => {
    const timestamp = new Date().toLocaleTimeString();
    console.log(`[${timestamp}] [${type}] ${message}`);
};

// === Main Application ===
async function main() {
    log('=== WhatsApp Notification Worker ===');
    
    // Prompt for all necessary info on startup
    const apiBaseUrl = readline.question('Enter the API Base URL (e.g., http://127.0.0.1:5000): ');
    const profileBaseUrl = readline.question('Enter the Profile Pages Base URL (e.g., https://voyage-profiles.netlify.app): ');
    const apiPassword = readline.question('Enter the API Password: ', { hideEchoBack: true });

    if (!apiBaseUrl || !apiPassword || !profileBaseUrl) {
        log('All fields (API URL, Profile URL, Password) are required. Exiting.', 'ERROR');
        return;
    }

    // Setup WhatsApp Client
    const client = new Client({
        authStrategy: new LocalAuth(),
        puppeteer: {
            headless: true,
            args: ['--no-sandbox', '--disable-setuid-sandbox']
        }
    });

    client.on('qr', qr => {
        log('QR code received. Please scan with your phone.');
        qrcode.generate(qr, { small: true });
    });

    client.on('authenticated', () => {
        log('WhatsApp client authenticated successfully.');
    });

    client.on('ready', () => {
        log('WhatsApp client is ready!');
        log('Starting notification processing loop...');
        startProcessingLoop(apiBaseUrl, apiPassword, profileBaseUrl, client);
    });

    client.on('auth_failure', msg => {
        log(`Authentication failed: ${msg}`, 'ERROR');
    });

    client.initialize();
}

// === The Processing Loop ===
async function startProcessingLoop(baseUrl, password, profileUrl, client) { // Accept the new profileUrl parameter
    setInterval(async () => {
        try {
            log('Checking for pending notifications...');
            
            // Fetch the next notification job
            const nextJobResponse = await fetch(`${baseUrl}/api/notifications/next`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ password })
            });

            if (!nextJobResponse.ok) {
                log(`API Error on /next: ${nextJobResponse.statusText}`, 'ERROR');
                return;
            }

            const job = await nextJobResponse.json();

            if (job.data) {
                const { name, phone, student_id } = job.data;
                log(`Found job for ${name} (${student_id}). ${job.pending_count} pending.`, 'WORK');
                
                const chatId = `91${phone}@c.us`;

                // Construct the profile URL
                const profileLink = `${profileUrl}/${student_id}`;

                // Fill in message template
                const message = `Hi ${name}!\n\nYour registration for Voyage 2k25 has been confirmed. Check out your profile at ${profileLink}.\n\nRegards,\nGeneral Secretary, Voyage 2k25\n\n_This is an automated message._`;

                // Send the message
                await client.sendMessage(chatId, message);
                log(`Message sent successfully to ${name}.`);
                
                // Confirm the job as done
                const confirmResponse = await fetch(`${baseUrl}/api/notifications/confirm`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ password, student_id })
                });

                if (confirmResponse.ok) {
                    log(`Confirmed job for ${student_id} as 'Done'.`);
                } else {
                    log(`Failed to confirm job for ${student_id}.`, 'ERROR');
                }
                
                await delay(5000); 

            } else {
                log('No pending notifications found.');
            }

        } catch (error) {
            log(`An error occurred in the processing loop: ${error.message}`, 'ERROR');
        }
    }, 15000);
}

main();