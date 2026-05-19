"""SMTP email service for order confirmations and test messages."""
from __future__ import annotations

import smtplib
import ssl
import traceback
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Iterable

from config import load_config
from models.customer import CustomerModel
from models.order import OrderItemModel, OrderModel


def _build_html(order: OrderModel, customer: CustomerModel, items: Iterable[OrderItemModel],
                store_name: str) -> str:
    rows_html = []
    for it in items:
        opt_html = ""
        if it.options:
            opt_names = ", ".join(o.option_name for o in it.options)
            opt_html = f"<div style='font-size:11px;color:#666'>{opt_names}</div>"
        rows_html.append(
            f"<tr>"
            f"<td style='padding:6px;border-bottom:1px solid #eee'>{it.product_name}{opt_html}</td>"
            f"<td style='padding:6px;border-bottom:1px solid #eee;text-align:center'>{it.quantity}</td>"
            f"<td style='padding:6px;border-bottom:1px solid #eee;text-align:right'>₱{it.unit_price:,.2f}</td>"
            f"<td style='padding:6px;border-bottom:1px solid #eee;text-align:right'>₱{it.subtotal:,.2f}</td>"
            f"</tr>"
        )

    rows_str = "".join(rows_html)
    return f"""
    <html><body style="font-family:Arial,sans-serif;color:#333">
      <div style="max-width:600px;margin:auto;border:1px solid #eee;border-radius:8px;overflow:hidden">
        <div style="background:#1A56DB;color:#fff;padding:18px 24px">
          <h2 style="margin:0">{store_name}</h2>
        </div>
        <div style="padding:20px 24px">
          <h3>Thank you for your order, {customer.first_name}!</h3>
          <p>Your order <b>#{order.order_id}</b> has been placed successfully.</p>
          <p>
            <b>Order Date:</b> {order.order_date.strftime('%Y-%m-%d %H:%M')}<br/>
            <b>Order Type:</b> {order.order_type}<br/>
            <b>Payment Method:</b> {order.payment_method or '—'}
          </p>
          <table style="width:100%;border-collapse:collapse;margin-top:14px">
            <thead>
              <tr style="background:#f5f7fb">
                <th style="text-align:left;padding:6px">Item</th>
                <th style="padding:6px">Qty</th>
                <th style="text-align:right;padding:6px">Unit</th>
                <th style="text-align:right;padding:6px">Subtotal</th>
              </tr>
            </thead>
            <tbody>{rows_str}</tbody>
          </table>
          <div style="margin-top:14px;text-align:right">
            <div>Subtotal: <b>₱{order.subtotal:,.2f}</b></div>
            <div>Discount: <b>-₱{order.discount_amount:,.2f}</b></div>
            <div style="font-size:18px;margin-top:6px">Total: <b>₱{order.total_amount:,.2f}</b></div>
          </div>
          <p style="margin-top:24px;color:#666">
            We will update you as your order moves through processing. If you have questions, reply to this email.
          </p>
        </div>
        <div style="background:#f5f7fb;padding:12px 24px;font-size:12px;color:#666;text-align:center">
          {store_name} · Order Confirmation
        </div>
      </div>
    </body></html>
    """


def send_order_confirmation(
    order: OrderModel, customer: CustomerModel, items: Iterable[OrderItemModel]
) -> tuple[bool, str]:
    """
    Returns (success, message). Logs errors but does not raise.
    """
    cfg = load_config()
    smtp_cfg = cfg.get("smtp", {})
    store_name = cfg.get("store", {}).get("name", "Store")

    if not customer.email:
        return False, "Customer has no email address; skipping."
    if not smtp_cfg.get("host") or not smtp_cfg.get("username"):
        return False, "SMTP not configured. Skipped sending."

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"Order Confirmation - Order #{order.order_id}"
    from_name = smtp_cfg.get("from_name") or store_name
    msg["From"] = f"{from_name} <{smtp_cfg['username']}>"
    msg["To"] = customer.email

    html = _build_html(order, customer, items, store_name)
    msg.attach(MIMEText(f"Thank you for your order #{order.order_id}.", "plain"))
    msg.attach(MIMEText(html, "html"))

    try:
        port = int(smtp_cfg.get("port", 587))
        if smtp_cfg.get("use_tls", True):
            with smtplib.SMTP(smtp_cfg["host"], port, timeout=15) as srv:
                srv.ehlo()
                srv.starttls(context=ssl.create_default_context())
                srv.login(smtp_cfg["username"], smtp_cfg.get("password", ""))
                srv.send_message(msg)
        else:
            with smtplib.SMTP_SSL(smtp_cfg["host"], port, timeout=15) as srv:
                srv.login(smtp_cfg["username"], smtp_cfg.get("password", ""))
                srv.send_message(msg)
        return True, f"Email sent to {customer.email}"
    except Exception as e:
        traceback.print_exc()
        return False, f"Email failed: {e}"


def send_test_email(to_email: str = "") -> tuple[bool, str]:
    cfg = load_config()
    smtp_cfg = cfg.get("smtp", {})
    if not smtp_cfg.get("host") or not smtp_cfg.get("username"):
        return False, "SMTP not configured."
    target = to_email or smtp_cfg["username"]

    msg = MIMEMultipart("alternative")
    msg["Subject"] = "Inventory App SMTP Test"
    msg["From"] = smtp_cfg["username"]
    msg["To"] = target
    msg.attach(MIMEText("This is a test email from the Inventory Management System.", "plain"))

    try:
        port = int(smtp_cfg.get("port", 587))
        if smtp_cfg.get("use_tls", True):
            with smtplib.SMTP(smtp_cfg["host"], port, timeout=15) as srv:
                srv.ehlo()
                srv.starttls(context=ssl.create_default_context())
                srv.login(smtp_cfg["username"], smtp_cfg.get("password", ""))
                srv.send_message(msg)
        else:
            with smtplib.SMTP_SSL(smtp_cfg["host"], port, timeout=15) as srv:
                srv.login(smtp_cfg["username"], smtp_cfg.get("password", ""))
                srv.send_message(msg)
        return True, f"Test email sent to {target}."
    except Exception as e:
        return False, f"Failed: {e}"


# ----------------------- Status update emails -----------------------

def _build_status_html(order: OrderModel, customer: CustomerModel,
                       store_name: str, headline: str, body_text: str) -> str:
    return f"""
    <html><body style="font-family:Arial,sans-serif;color:#333">
      <div style="max-width:600px;margin:auto;border:1px solid #eee;border-radius:8px;overflow:hidden">
        <div style="background:#1E1B4B;color:#fff;padding:18px 24px">
          <h2 style="margin:0">{store_name}</h2>
        </div>
        <div style="padding:20px 24px">
          <h3>{headline}</h3>
          <p>Hi {customer.first_name},</p>
          <p>{body_text}</p>
          <p>
            <b>Order #{order.order_id}</b><br/>
            <b>Order Type:</b> {order.order_type}<br/>
            <b>Total:</b> ₱{order.total_amount:,.2f}
          </p>
          <p style="color:#666">If you have any questions, just reply to this email.</p>
        </div>
        <div style="background:#f5f7fb;padding:12px 24px;font-size:12px;color:#666;text-align:center">
          {store_name} · Order Update
        </div>
      </div>
    </body></html>
    """


def _send_html(to_email: str, subject: str, html: str,
               plain_fallback: str) -> tuple[bool, str]:
    """Low-level send helper. Returns (success, message)."""
    cfg = load_config()
    smtp_cfg = cfg.get("smtp", {})
    if not smtp_cfg.get("host") or not smtp_cfg.get("username"):
        return False, "SMTP not configured."
    if not to_email:
        return False, "No recipient email."

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    from_name = smtp_cfg.get("from_name") or cfg.get("store", {}).get("name", "Store")
    msg["From"] = f"{from_name} <{smtp_cfg['username']}>"
    msg["To"] = to_email
    msg.attach(MIMEText(plain_fallback, "plain"))
    msg.attach(MIMEText(html, "html"))

    try:
        port = int(smtp_cfg.get("port", 587))
        if smtp_cfg.get("use_tls", True):
            with smtplib.SMTP(smtp_cfg["host"], port, timeout=15) as srv:
                srv.ehlo()
                srv.starttls(context=ssl.create_default_context())
                srv.login(smtp_cfg["username"], smtp_cfg.get("password", ""))
                srv.send_message(msg)
        else:
            with smtplib.SMTP_SSL(smtp_cfg["host"], port, timeout=15) as srv:
                srv.login(smtp_cfg["username"], smtp_cfg.get("password", ""))
                srv.send_message(msg)
        return True, f"Email sent to {to_email}"
    except Exception as e:
        traceback.print_exc()
        return False, f"Email failed: {e}"


def send_order_completed(order: OrderModel, customer: CustomerModel) -> tuple[bool, str]:
    cfg = load_config()
    store_name = cfg.get("store", {}).get("name", "Store")
    if not customer.email:
        return False, "Customer has no email; skipped."
    html = _build_status_html(
        order, customer, store_name,
        headline="Your order is complete 🎉",
        body_text="Thank you for choosing us. Your order has been completed successfully. We hope you enjoyed it!",
    )
    plain = f"Order #{order.order_id} is complete. Total: ₱{order.total_amount:,.2f}."
    return _send_html(customer.email, f"Order Complete - #{order.order_id}", html, plain)


def send_order_status_update(order: OrderModel, customer: CustomerModel,
                             new_status: str) -> tuple[bool, str]:
    cfg = load_config()
    store_name = cfg.get("store", {}).get("name", "Store")
    if not customer.email:
        return False, "Customer has no email; skipped."
    headline_map = {
        "Processing": "We're preparing your order",
        "ReadyForPickup": "Your order is ready for pickup",
        "ReadyForDelivery": "Your order is on the way",
        "Cancelled": "Your order was cancelled",
    }
    body_map = {
        "Processing": "Our kitchen has started preparing your items.",
        "ReadyForPickup": "Your order is ready! Come grab it whenever you can.",
        "ReadyForDelivery": "Our courier has picked up your order — it should arrive soon.",
        "Cancelled": "Your order has been cancelled. If you were charged, a refund has been issued.",
    }
    headline = headline_map.get(new_status, f"Order {new_status}")
    body = body_map.get(new_status, f"Your order is now {new_status}.")
    html = _build_status_html(order, customer, store_name, headline, body)
    plain = f"Order #{order.order_id}: {headline}"
    return _send_html(customer.email,
                      f"Order #{order.order_id} - {headline}",
                      html, plain)
