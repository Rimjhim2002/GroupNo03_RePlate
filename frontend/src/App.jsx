import { useEffect, useMemo, useState } from 'react'

const API_URL = 'http://127.0.0.1:8000'

const initialForm = {
  food_name: '',
  quantity: '',
  category: '',
  expiry_time: '',
  original_price: '',
  discounted_price: '',
  pickup_location: '',
  restaurant_id: 'restaurant_001',
  status: 'available',
}

const formatDate = (value) => {
  if (!value) return 'N/A'
  return new Date(value).toLocaleString([], {
    dateStyle: 'medium',
    timeStyle: 'short',
  })
}

const recommendationStyles = {
  'Donate now': 'bg-red-100 text-red-700 border-red-200',
  'Sell at discount': 'bg-amber-100 text-amber-700 border-amber-200',
  'Keep for normal sale': 'bg-emerald-100 text-emerald-700 border-emerald-200',
  'Review listing': 'bg-slate-100 text-slate-700 border-slate-200',
}

function App() {
  const [activeTab, setActiveTab] = useState('restaurant')
  const [formData, setFormData] = useState(initialForm)
  const [loading, setLoading] = useState(false)
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')
  const [listings, setListings] = useState([])
  const [notifications, setNotifications] = useState([])
  const [searchLocation, setSearchLocation] = useState('')
  const [selectedCategory, setSelectedCategory] = useState('All')
  const [loadingListings, setLoadingListings] = useState(false)
  const [loadingNotifications, setLoadingNotifications] = useState(false)
  const [reservingId, setReservingId] = useState(null)
  const [reservationMessage, setReservationMessage] = useState('')

  const fetchListings = async () => {
    try {
      setLoadingListings(true)
      const response = await fetch(`${API_URL}/listings/`)
      const data = await response.json()
      if (!response.ok) {
        throw new Error(data.detail || 'Failed to load listings')
      }
      setListings(Array.isArray(data) ? data : [])
    } catch (err) {
      setError(err.message)
    } finally {
      setLoadingListings(false)
    }
  }

  const fetchNotifications = async () => {
    try {
      setLoadingNotifications(true)
      const response = await fetch(`${API_URL}/listings/notifications`)
      const data = await response.json()
      if (!response.ok) {
        throw new Error(data.detail || 'Failed to load notifications')
      }
      setNotifications(Array.isArray(data) ? data : [])
    } catch (err) {
      setError(err.message)
    } finally {
      setLoadingNotifications(false)
    }
  }

  useEffect(() => {
    fetchListings()
    fetchNotifications()
  }, [])

  const filteredListings = useMemo(() => {
    return listings.filter((listing) => {
      const matchesLocation =
        !searchLocation ||
        listing.pickup_location?.toLowerCase().includes(searchLocation.toLowerCase())
      const matchesCategory =
        selectedCategory === 'All' || listing.category === selectedCategory
      return matchesLocation && matchesCategory
    })
  }, [listings, searchLocation, selectedCategory])

  const categories = ['All', ...new Set(listings.map((listing) => listing.category).filter(Boolean))]

  const handleChange = (event) => {
    const { name, value } = event.target
    setFormData((prev) => ({ ...prev, [name]: value }))
  }

  const handleSubmit = async (event) => {
    event.preventDefault()
    setLoading(true)
    setError('')
    setMessage('')

    const payload = {
      ...formData,
      quantity: Number(formData.quantity),
      original_price: Number(formData.original_price),
      discounted_price: Number(formData.discounted_price),
      expiry_time: formData.expiry_time ? new Date(formData.expiry_time).toISOString() : '',
    }

    try {
      const response = await fetch(`${API_URL}/listings/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload),
      })

      const result = await response.json()

      if (!response.ok) {
        throw new Error(result.detail || 'Failed to create listing')
      }

      setMessage('Food listing created successfully!')
      setFormData(initialForm)
      setActiveTab('discover')
      await Promise.all([fetchListings(), fetchNotifications()])
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const handleReserve = async (listingId) => {
    setReservingId(listingId)
    setReservationMessage('')
    setError('')

    try {
      const response = await fetch(`${API_URL}/listings/${listingId}/reserve`, {
        method: 'POST',
      })
      const result = await response.json()

      if (!response.ok) {
        throw new Error(result.detail || 'Could not reserve the listing')
      }

      setReservationMessage(`Reserved successfully: ${result.reservation.id}`)
      await Promise.all([fetchListings(), fetchNotifications()])
    } catch (err) {
      setError(err.message)
    } finally {
      setReservingId(null)
    }
  }

  return (
    <div className="min-h-screen bg-[radial-gradient(circle_at_top_left,_rgba(74,222,128,0.18),_transparent_28%),radial-gradient(circle_at_bottom_right,_rgba(59,130,246,0.12),_transparent_20%),linear-gradient(135deg,_#f0fdf4_0%,_#f8fafc_36%,_#eef2ff_100%)] text-slate-800">
      <header className="relative overflow-hidden border-b border-emerald-200/70 bg-gradient-to-r from-emerald-700 via-green-700 to-teal-700 text-white shadow-[0_18px_40px_rgba(6,78,59,0.2)]">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_left,_rgba(255,255,255,0.18),_transparent_35%),radial-gradient(circle_at_bottom_right,_rgba(16,185,129,0.25),_transparent_25%)]" />

        <div className="relative mx-auto flex max-w-6xl items-center justify-between gap-4 px-4 py-6 sm:px-6 lg:px-8">
          <div className="flex items-center gap-4">
            <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-white/15 shadow-inner ring-1 ring-white/30 backdrop-blur-sm">
              <span className="text-2xl">🍽️</span>
            </div>
            <div>
              <h1 className="text-2xl font-black tracking-tight sm:text-3xl">RePlate</h1>
              <p className="text-sm text-emerald-50/90">Smart Food Lifecycle Management</p>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-2 rounded-full border border-white/20 bg-white/10 p-1.5 shadow-lg shadow-emerald-950/10 backdrop-blur-md">
            <button
              type="button"
              onClick={() => setActiveTab('restaurant')}
              className={`rounded-full px-4 py-2 text-sm font-semibold transition-all ${
                activeTab === 'restaurant'
                  ? 'bg-white text-emerald-700 shadow-md'
                  : 'text-white/90 hover:bg-white/10'
              }`}
            >
              Restaurant
            </button>
            <button
              type="button"
              onClick={() => setActiveTab('discover')}
              className={`rounded-full px-4 py-2 text-sm font-semibold transition-all ${
                activeTab === 'discover'
                  ? 'bg-white text-emerald-700 shadow-md'
                  : 'text-white/90 hover:bg-white/10'
              }`}
            >
              Nearby Food
            </button>
            <button
              type="button"
              onClick={() => setActiveTab('notifications')}
              className={`rounded-full px-4 py-2 text-sm font-semibold transition-all ${
                activeTab === 'notifications'
                  ? 'bg-white text-emerald-700 shadow-md'
                  : 'text-white/90 hover:bg-white/10'
              }`}
            >
              Notifications
            </button>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-6xl px-4 py-8 sm:px-6 lg:px-8 lg:py-10">
        {activeTab === 'restaurant' && (
          <div className="rounded-[30px] border border-white/70 bg-white/80 p-6 shadow-[0_20px_60px_rgba(15,23,42,0.08)] backdrop-blur-xl md:p-8">
            <div className="mb-8 flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
              <div>
                <span className="inline-flex rounded-full bg-emerald-100 px-3 py-1 text-xs font-bold uppercase tracking-[0.18em] text-emerald-700">
                  Restaurant Hub
                </span>
                <h2 className="mt-4 text-3xl font-black tracking-tight text-slate-800">Add Surplus Food</h2>
              </div>
              <p className="max-w-xl text-sm text-slate-500 md:text-right">
                Turn leftovers into impact by publishing a fresh listing for nearby consumers and NGOs.
              </p>
            </div>

            {message && (
              <div className="mb-5 rounded-2xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm font-medium text-emerald-700 shadow-sm">
                {message}
              </div>
            )}

            {error && (
              <div className="mb-5 rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm font-medium text-red-700 shadow-sm">
                {error}
              </div>
            )}

            <form className="space-y-6" onSubmit={handleSubmit}>
              <div className="rounded-2xl border border-slate-200 bg-slate-50/80 p-4 md:p-5">
                <label className="mb-2 block text-sm font-semibold text-slate-700">Food Name</label>
                <input
                  type="text"
                  name="food_name"
                  value={formData.food_name}
                  onChange={handleChange}
                  placeholder="e.g. Chicken Burger"
                  className="w-full rounded-xl border border-slate-200 bg-white px-4 py-3 text-slate-800 shadow-sm transition focus:border-emerald-400 focus:outline-none focus:ring-4 focus:ring-emerald-100"
                  required
                />
              </div>

              <div className="grid gap-6 md:grid-cols-2">
                <div className="rounded-2xl border border-slate-200 bg-slate-50/80 p-4 md:p-5">
                  <label className="mb-2 block text-sm font-semibold text-slate-700">Quantity</label>
                  <input
                    type="number"
                    name="quantity"
                    min="1"
                    value={formData.quantity}
                    onChange={handleChange}
                    placeholder="e.g. 10"
                    className="w-full rounded-xl border border-slate-200 bg-white px-4 py-3 text-slate-800 shadow-sm transition focus:border-emerald-400 focus:outline-none focus:ring-4 focus:ring-emerald-100"
                    required
                  />
                </div>

                <div className="rounded-2xl border border-slate-200 bg-slate-50/80 p-4 md:p-5">
                  <label className="mb-2 block text-sm font-semibold text-slate-700">Category</label>
                  <select
                    name="category"
                    value={formData.category}
                    onChange={handleChange}
                    className="w-full rounded-xl border border-slate-200 bg-white px-4 py-3 text-slate-800 shadow-sm transition focus:border-emerald-400 focus:outline-none focus:ring-4 focus:ring-emerald-100"
                    required
                  >
                    <option value="">Select category</option>
                    <option value="Fast Food">Fast Food</option>
                    <option value="Rice">Rice & Meals</option>
                    <option value="Bakery">Bakery</option>
                    <option value="Dessert">Dessert</option>
                    <option value="Drinks">Drinks</option>
                    <option value="Other">Other</option>
                  </select>
                </div>
              </div>

              <div className="rounded-2xl border border-slate-200 bg-slate-50/80 p-4 md:p-5">
                <label className="mb-2 block text-sm font-semibold text-slate-700">Expiry Time</label>
                <input
                  type="datetime-local"
                  name="expiry_time"
                  value={formData.expiry_time}
                  onChange={handleChange}
                  className="w-full rounded-xl border border-slate-200 bg-white px-4 py-3 text-slate-800 shadow-sm transition focus:border-emerald-400 focus:outline-none focus:ring-4 focus:ring-emerald-100"
                  required
                />
              </div>

              <div className="grid gap-6 md:grid-cols-2">
                <div className="rounded-2xl border border-slate-200 bg-slate-50/80 p-4 md:p-5">
                  <label className="mb-2 block text-sm font-semibold text-slate-700">Original Price (৳)</label>
                  <input
                    type="number"
                    name="original_price"
                    min="0"
                    value={formData.original_price}
                    onChange={handleChange}
                    placeholder="250"
                    className="w-full rounded-xl border border-slate-200 bg-white px-4 py-3 text-slate-800 shadow-sm transition focus:border-emerald-400 focus:outline-none focus:ring-4 focus:ring-emerald-100"
                    required
                  />
                </div>

                <div className="rounded-2xl border border-slate-200 bg-slate-50/80 p-4 md:p-5">
                  <label className="mb-2 block text-sm font-semibold text-slate-700">Discounted Price (৳)</label>
                  <input
                    type="number"
                    name="discounted_price"
                    min="0"
                    value={formData.discounted_price}
                    onChange={handleChange}
                    placeholder="150"
                    className="w-full rounded-xl border border-slate-200 bg-white px-4 py-3 text-slate-800 shadow-sm transition focus:border-emerald-400 focus:outline-none focus:ring-4 focus:ring-emerald-100"
                    required
                  />
                </div>
              </div>

              <div className="rounded-2xl border border-slate-200 bg-slate-50/80 p-4 md:p-5">
                <label className="mb-2 block text-sm font-semibold text-slate-700">Pickup Location</label>
                <input
                  type="text"
                  name="pickup_location"
                  value={formData.pickup_location}
                  onChange={handleChange}
                  placeholder="e.g. BRAC University"
                  className="w-full rounded-xl border border-slate-200 bg-white px-4 py-3 text-slate-800 shadow-sm transition focus:border-emerald-400 focus:outline-none focus:ring-4 focus:ring-emerald-100"
                  required
                />
              </div>

              <button
                type="submit"
                disabled={loading}
                className="w-full rounded-2xl bg-gradient-to-r from-emerald-600 via-green-600 to-teal-600 px-5 py-3.5 text-base font-bold text-white shadow-[0_16px_32px_rgba(22,163,74,0.24)] transition hover:scale-[1.01] hover:shadow-[0_18px_34px_rgba(22,163,74,0.28)] disabled:cursor-not-allowed disabled:from-emerald-400 disabled:to-green-400"
              >
                {loading ? 'Creating...' : 'Create Food Listing'}
              </button>
            </form>
          </div>
        )}

        {activeTab === 'discover' && (
          <div className="rounded-[30px] border border-white/70 bg-white/80 p-6 shadow-[0_20px_60px_rgba(15,23,42,0.08)] backdrop-blur-xl md:p-8">
            <div className="mb-6 flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
              <div>
                <span className="inline-flex rounded-full bg-amber-100 px-3 py-1 text-xs font-bold uppercase tracking-[0.18em] text-amber-700">
                  Discover
                </span>
                <h2 className="mt-4 text-3xl font-black tracking-tight text-slate-800">Nearby Food Discovery</h2>
              </div>

              <button
                type="button"
                onClick={fetchListings}
                className="rounded-xl border border-slate-200 bg-white px-4 py-2 text-sm font-semibold text-slate-700 shadow-sm transition hover:border-emerald-300 hover:text-emerald-700"
              >
                Refresh
              </button>
            </div>

            <div className="mb-6 grid gap-4 md:grid-cols-2">
              <div className="rounded-2xl border border-slate-200 bg-slate-50/80 p-4">
                <label className="mb-2 block text-sm font-semibold text-slate-700">Search by pickup location</label>
                <input
                  type="text"
                  value={searchLocation}
                  onChange={(event) => setSearchLocation(event.target.value)}
                  placeholder="e.g. BRAC University"
                  className="w-full rounded-xl border border-slate-200 bg-white px-4 py-3 text-slate-800 shadow-sm transition focus:border-emerald-400 focus:outline-none focus:ring-4 focus:ring-emerald-100"
                />
              </div>

              <div className="rounded-2xl border border-slate-200 bg-slate-50/80 p-4">
                <label className="mb-2 block text-sm font-semibold text-slate-700">Category</label>
                <select
                  value={selectedCategory}
                  onChange={(event) => setSelectedCategory(event.target.value)}
                  className="w-full rounded-xl border border-slate-200 bg-white px-4 py-3 text-slate-800 shadow-sm transition focus:border-emerald-400 focus:outline-none focus:ring-4 focus:ring-emerald-100"
                >
                  {categories.map((category) => (
                    <option key={category} value={category}>
                      {category}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            {reservationMessage && (
              <div className="mb-5 rounded-2xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm font-medium text-emerald-700 shadow-sm">
                {reservationMessage}
              </div>
            )}

            {loadingListings ? (
              <div className="rounded-2xl border border-dashed border-slate-300 bg-slate-50 p-8 text-center text-slate-600">
                Loading food listings...
              </div>
            ) : filteredListings.length === 0 ? (
              <div className="rounded-2xl border border-dashed border-slate-300 bg-slate-50 p-8 text-center text-slate-600">
                No food listings match your search right now.
              </div>
            ) : (
              <div className="grid gap-5 md:grid-cols-2 xl:grid-cols-3">
                {filteredListings.map((listing) => (
                  <div key={listing.id} className="group rounded-[26px] border border-slate-200 bg-gradient-to-br from-white to-emerald-50/70 p-5 shadow-[0_12px_30px_rgba(15,23,42,0.06)] transition hover:-translate-y-1 hover:shadow-[0_18px_40px_rgba(15,23,42,0.08)]">
                    <div className="mb-4 flex items-start justify-between gap-3">
                      <div>
                        <h3 className="text-xl font-bold text-slate-800">{listing.food_name}</h3>
                        <p className="mt-1 text-sm text-slate-500">{listing.category}</p>
                      </div>
                      <span className={`rounded-full border px-2.5 py-1 text-[10px] font-bold uppercase tracking-[0.12em] ${recommendationStyles[listing.recommendation] || 'bg-slate-100 text-slate-700 border-slate-200'}`}>
                        {listing.recommendation || 'Review listing'}
                      </span>
                    </div>

                    <div className="mb-4 rounded-2xl border border-emerald-100 bg-white/80 px-3 py-2 text-xs leading-relaxed text-slate-700">
                      <span className="font-bold text-slate-800">Smart recommendation:</span> {listing.recommendation_reason || 'No recommendation available yet.'}
                    </div>

                    <div className="space-y-2 text-sm text-slate-700">
                      <p><span className="font-semibold text-slate-800">Quantity:</span> {listing.quantity}</p>
                      <p><span className="font-semibold text-slate-800">Pickup:</span> {listing.pickup_location}</p>
                      <p><span className="font-semibold text-slate-800">Expiry:</span> {formatDate(listing.expiry_time)}</p>
                    </div>

                    <div className="mt-5 flex items-end justify-between border-t border-slate-200 pt-4">
                      <div>
                        <p className="text-xs font-medium text-slate-400 line-through">৳{listing.original_price}</p>
                        <p className="text-2xl font-black text-emerald-700">৳{listing.discounted_price}</p>
                      </div>

                      <button
                        type="button"
                        onClick={() => handleReserve(listing.id)}
                        disabled={reservingId === listing.id}
                        className="rounded-xl bg-gradient-to-r from-emerald-600 to-green-600 px-4 py-2.5 text-sm font-bold text-white shadow-[0_12px_25px_rgba(22,163,74,0.22)] transition hover:from-emerald-500 hover:to-green-500 disabled:cursor-not-allowed disabled:from-emerald-300 disabled:to-green-300"
                      >
                        {reservingId === listing.id ? 'Reserving...' : 'Reserve'}
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {activeTab === 'notifications' && (
          <div className="rounded-[30px] border border-white/70 bg-white/80 p-6 shadow-[0_20px_60px_rgba(15,23,42,0.08)] backdrop-blur-xl md:p-8">
            <div className="mb-6 flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
              <div>
                <span className="inline-flex rounded-full bg-sky-100 px-3 py-1 text-xs font-bold uppercase tracking-[0.18em] text-sky-700">
                  Alerts
                </span>
                <h2 className="mt-4 text-3xl font-black tracking-tight text-slate-800">Smart Notifications</h2>
              </div>

              <button
                type="button"
                onClick={fetchNotifications}
                className="rounded-xl border border-slate-200 bg-white px-4 py-2 text-sm font-semibold text-slate-700 shadow-sm transition hover:border-sky-300 hover:text-sky-700"
              >
                Refresh alerts
              </button>
            </div>

            {loadingNotifications ? (
              <div className="rounded-2xl border border-dashed border-slate-300 bg-slate-50 p-8 text-center text-slate-600">
                Loading notifications...
              </div>
            ) : notifications.length === 0 ? (
              <div className="rounded-2xl border border-dashed border-slate-300 bg-slate-50 p-8 text-center text-slate-600">
                No notifications at the moment.
              </div>
            ) : (
              <div className="space-y-4">
                {notifications.map((item) => (
                  <div key={item.id} className="rounded-[24px] border border-slate-200 bg-gradient-to-r from-slate-50 via-white to-emerald-50 p-5 shadow-[0_10px_25px_rgba(15,23,42,0.04)]">
                    <div className="mb-2 flex items-center justify-between gap-3">
                      <h3 className="text-lg font-bold text-slate-800">{item.title}</h3>
                      <span className={`rounded-full border px-2.5 py-1 text-[10px] font-bold uppercase tracking-[0.12em] ${
                        item.type === 'donation' ? 'border-red-200 bg-red-100 text-red-700' :
                        item.type === 'discount' ? 'border-amber-200 bg-amber-100 text-amber-700' :
                        'border-emerald-200 bg-emerald-100 text-emerald-700'
                      }`}>
                        {item.type}
                      </span>
                    </div>
                    <p className="text-sm leading-6 text-slate-700">{item.message}</p>
                    <p className="mt-3 text-xs font-medium text-slate-500">{formatDate(item.created_at)}</p>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </main>
    </div>
  )
}

export default App
