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






<!-- mondoDB install -->

### mongoDB install
(youtube - reference)[https://www.youtube.com/watch?v=8gUQL2zlpvI]

- If mongo already installed the use the below command to run the server
```shell
sudo mongod --dbpath=/Users/alpitg/data/db
```


1. Install mongo db service & compass
2. copy the mondoDB service folder into the root directory
   1. mv <MONGODB_FOLDER_NAME> <PATH_TO_ROOT>
   2. then go to root folder & check folder is present or not

```shell
pwd # to check current directory
ls -al
touch .zshrc
open .zshrc
```

3. copy the below text in the file and save it.
 
```shell
export PATH=${PATH}:/Users/alpitg/mongodb-macos-aarch64-8.0.12/bin
```
4. Run below command
```shell
source .zshrc
```
5. You will get below error -
```json
{"error":"NonExistentPath: Data directory /data/db not found. Create the missing directory or specify another path using (1) the --dbpath command line option, or (2) by adding the 'storage.dbPath' option in the configuration file."}}
```
 - to resolve this use below command 
```shell
sudo mkdir -p data/db
sudo mongod --dbpath=/Users/alpitg/data/db

```




<!-- prompts -->

```shell

For my client which owns a shop, I am building app where I need to manage the 1. store bills and 2. the items get sold or the items which are customised its costing and discounts additionally 3. need to manage inventory 

suggest me api required to get started with
```


```shell
Below are the master tables we need bring the data from the mongoDB

1. frame-types
2. glass-types
3. misc-charges
4. mount-types
5. order-status

prepare the industry best practice schema in mongo
```



  
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