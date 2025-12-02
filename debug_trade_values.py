from database import SessionLocal
import models

def main():
    db = SessionLocal()

    print("=== StagingInvoiceDetail.trade ===")
    rows = db.query(models.StagingInvoiceDetail.trade).distinct().all()
    for (val,) in rows:
        print("staging trade:", repr(val))

    print("\n=== InvoiceDetail.trade ===")
    rows2 = db.query(models.InvoiceDetail.trade).distinct().all()
    for (val,) in rows2:
        print("detail trade:", repr(val))

    db.close()

if __name__ == "__main__":
    main()
