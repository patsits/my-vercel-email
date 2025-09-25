// api/send-email.js
const nodemailer = require("nodemailer");

module.exports = async (req, res) => {
  // μόνο POST επιτρέπεται
  if (req.method !== "POST") {
    res.setHeader("Allow", "POST");
    return res.status(405).json({ error: "Method Not Allowed" });
  }

  try {
    // Προαιρετικός έλεγχος "secret" για να μην μπορεί οποιοσδήποτε να καλέσει το webhook
    const expectedSecret = process.env.WEBHOOK_SECRET || null;
    const incomingSecret = req.headers["x-webhook-secret"] || req.query.secret || (req.body && req.body.secret);

    if (expectedSecret && incomingSecret !== expectedSecret) {
      return res.status(401).json({ error: "Unauthorized (invalid secret)" });
    }

    const { to, subject, text, html } = req.body || {};

    if (!to || (!text && !html)) {
      return res.status(400).json({ error: "Missing required fields: to and (text|html)" });
    }

    // δημιουργία transporter από περιβάλλοντα μεταβλητά
    const transporter = nodemailer.createTransport({
      host: process.env.SMTP_HOST,
      port: Number(process.env.SMTP_PORT || 587),
      secure: (process.env.SMTP_SECURE === "true"), // true για 465
      auth: {
        user: process.env.SMTP_USER,
        pass: process.env.SMTP_PASS
      }
    });

    const mailOptions = {
      from: process.env.FROM_EMAIL || process.env.SMTP_USER,
      to,
      subject: subject || "(no subject)",
      text: text || undefined,
      html: html || undefined
    };

    const info = await transporter.sendMail(mailOptions);

    return res.status(200).json({ success: true, messageId: info.messageId });
  } catch (err) {
    console.error("send-email error:", err);
    return res.status(500).json({ error: String(err) });
  }
};
