# GroupNo03_RePlate# GroupNo03_RePlate

## Database setup

RePlate stores accounts and application data in MongoDB. The `MONGO_URI` value is
machine-specific, so a local URI such as `mongodb://localhost:27017` creates a
separate database on every computer. Accounts registered on one computer will
not exist on another computer using a different local MongoDB server.

For multiple computers to share accounts:

1. Create a MongoDB Atlas cluster (the free tier is sufficient for development),
	create a database user, and allow the computers running the app in the
	cluster's network access list.
2. Copy `.env.example` to `.env` on every computer.
3. Set the same Atlas connection string in `MONGO_URI` on every `.env` file and
	keep `MONGO_DB_NAME` set to `replate`.
4. Start the app from the project directory with:

	```powershell
	uvicorn app.main:app --reload
	```

The real `.env` file is ignored by Git because it contains database credentials.
Never commit the Atlas password or connection string.