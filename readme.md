```shell

python3 -m venv venv
source venv/bin/activate

pip3 install -r requirements.txt

```

my-crm-app/
├── backend/
│ ├── app/
│ │ ├── models/
│ │ │ └── user.py
│ │ ├── schemas/
│ │ │ └── user.py
│ │ ├── routes/
│ │ │ └── user.py
│ │ ├── db/
│ │ │ └── mongo.py
│ │ └── core/
│ │ └── config.py
│ ├──── main.py
│ └── requirements.txt
├── frontend/ (React app)
│ └── ...
└── docker-compose.yml (optional for deployment)


| Original Name | Recommended Collection Name |
| ------------- | --------------------------- |
| frame-types   | `master_frame_types`        |
| glass-types   | `master_glass_types`        |
| misc-charges  | `master_misc_charges`       |
| mount-types   | `master_mount_types`        |
| order-status  | `master_order_status`       |




  
```js
// customers

{
  _id: ObjectId,
  name: String,
  contact: { phone: String, email: String },
  billingAddress: { street: String, city: String, state: String, postcode: String, country: String },
  // ...
}
```

<!-- orders -->
```js
{
  _id: ObjectId,
  customerId: ObjectId,
  createdAt: ISODate,
  status: "pending" | "fulfilled" | "partial" | "cancelled",
  items: [
    {
      productId: ObjectId,
      description: String,
      quantity: Number,
      unitPrice: Number,

      discountedQuantity: Number?,       // items that got discount
      discountAmount: Number,            // total discount value on this line
      discountPercentage: Number,        // discount percent applied

      cancelledQty: Number,              // if partially cancelled
      netQuantity: Number,               // billable qty = quantity - cancelledQty

      amountBeforeDiscount: Number,
      amountAfterDiscount: Number        // unitPrice * netQuantity − discountAmount
    }
  ],
  subtotal: Number,
  totalDiscountAmount: Number,           // sum of all line discounts
  totalAmount: Number,                   // subtotal - totalDiscountAmount
  cancelledAmount: Number,
  note: String
}
```

<!-- invoices -->
```js
{
  _id: ObjectId,
  customerId: ObjectId,
  orderIds: [ObjectId],
  createdAt: ISODate,
  status: "draft" | "issued" | "paid",
  items: [
    {
      orderId: ObjectId,
      productId: ObjectId,
      description: String,
      quantity: Number,
      unitPrice: Number,

      discountAmount: Number,
      discountPercentage: Number,

      amountBeforeDiscount: Number,
      amountAfterDiscount: Number
    }
  ],
  subtotal: Number,
  totalDiscountAmount: Number,
  totalAmount: Number,           // subtotal - totalDiscountAmount
  paidAmount: Number,
  balanceAmount: Number,
  paymentMethod: String,
  paymentStatus: String
}

```