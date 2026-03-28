import pkg from 'whatsapp-web.js';
const { Client, LocalAuth } = pkg;
import qrcode from 'qrcode-terminal';
import readlineSync from 'readline-sync';

const log = (message, type = 'INFO') => {
    const timestamp = new Date().toLocaleTimeString();
    console.log(`[${timestamp}] [${type}] ${message}`);
};

// --- UPDATED SMART NUMBER FORMATTER ---
function formatPhoneNumber(numberStr) {
    // Strip all non-digits (removes the '+' or any spaces/dashes)
    let digits = String(numberStr).replace(/\D/g, '');
    
    // If the API gave exactly 10 digits, append the 91
    if (digits.length === 10) {
        digits = '91' + digits;
    }
    
    // Safety check
    if (!digits || digits.length < 10 || digits.length > 15) return null;
    
    return `${digits}@c.us`;
}

async function main() {
    log('=== Voyage 2k26 Notification Worker ===');
    
    const apiBaseUrl = readlineSync.question('Enter API Base URL: ');
    const profileBaseUrl = readlineSync.question('Enter Profile Base URL: ');
    const apiPassword = readlineSync.question('Enter API Password: ', { hideEchoBack: true });

    if (!apiBaseUrl || !apiPassword || !profileBaseUrl) {
        log('All fields required.', 'ERROR');
        process.exit(1);
    }

    const client = new Client({
        authStrategy: new LocalAuth({ clientId: 'voyage-worker' }),
        puppeteer: { 
            headless: true, 
            args:['--no-sandbox', '--disable-setuid-sandbox'] 
        }
    });

    client.on('qr', qr => {
        log('Scan this QR code:');
        qrcode.generate(qr, { small: true });
    });

    client.on('ready', () => {
        log('✅ WhatsApp ready!');
        pollQueue(apiBaseUrl, apiPassword, profileBaseUrl, client);
    });

    client.on('auth_failure', msg => log(`Auth failure: ${msg}`, 'ERROR'));

    client.initialize();
}

async function pollQueue(baseUrl, password, profileUrl, client) {
    try {
        const response = await fetch(`${baseUrl}/api/notifications/next`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ password })
        });

        if (response.ok) {
            const job = await response.json();

            if (job.data) {
                const { name, phone, student_id } = job.data;
                log(`Job for ${name} (${student_id}). ${job.pending_count} left.`, 'WORK');
                
                // --- FIXED: Pass the raw phone number to our smart formatter ---
                const chatId = formatPhoneNumber(phone); 
                
                const profileLink = `${profileUrl}/${student_id}`;
                const message = `Hi ${name}!\n\nYour registration for Voyage 2k26 has been confirmed. Check out your profile at ${profileLink}.\n\nRegards,\nFinance, Voyage 2k26\n\n_This is an automated message._`;

                if (!chatId) {
                    log(`Invalid phone for ${name}: ${phone}`, 'ERROR');
                } else {
                    try {
                        log(`Checking if ${chatId.replace('@c.us', '')} is registered on WhatsApp...`);
                        
                        // Check if number exists on WA
                        const registeredUser = await client.getNumberId(chatId);
                        
                        if (!registeredUser) {
                            log(`Number is not registered on WhatsApp: ${phone}`, 'ERROR');
                            
                            // Let the API know so it doesn't get stuck in an endless loop
                            await fetch(`${baseUrl}/api/notifications/confirm`, {
                                method: 'POST',
                                headers: { 'Content-Type': 'application/json' },
                                body: JSON.stringify({ password, student_id, status: 'invalid_number' })
                            });
                        } else {
                            // Send to the verified, serialized ID
                            await client.sendMessage(registeredUser._serialized, message);
                            log(`Message sent to ${name}.`);
                            
                            // Confirm job success
                            await fetch(`${baseUrl}/api/notifications/confirm`, {
                                method: 'POST',
                                headers: { 'Content-Type': 'application/json' },
                                body: JSON.stringify({ password, student_id, status: 'success' })
                            });
                            log(`Confirmed job for ${student_id}.`);
                        }
                    } catch (sendErr) {
                        log(`Failed to send to ${name}: ${sendErr}`, 'ERROR');
                    }
                }
            }
        }
    } catch (error) {
        log(`Loop Error: ${error.stack || error}`, 'ERROR');
    }

    setTimeout(() => pollQueue(baseUrl, password, profileUrl, client), 10000);
}

main();