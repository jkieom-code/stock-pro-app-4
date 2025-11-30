<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Interactive Stock Forecaster</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap" rel="stylesheet">
    <style>
        body {
            font-family: 'Inter', sans-serif;
            background-color: #f7f9fb;
            color: #1e293b;
        }
        .card {
            box-shadow: 0 0 25px -5px rgba(0, 0, 0, 0.1), 0 8px 10px -6px rgba(0, 0, 0, 0.1);
            transition: all 0.3s ease;
        }
        .header-bg {
            background: linear-gradient(90deg, #1d4ed8, #3b82f6);
        }
        .btn-primary {
            background-color: #3b82f6;
            transition: background-color 0.2s;
        }
        .btn-primary:hover {
            background-color: #2563eb;
        }
    </style>
</head>
<body class="p-4 sm:p-8 min-h-screen flex items-start justify-center">

    <div class="w-full max-w-5xl">
        
        <!-- Header Section -->
        <header class="header-bg p-6 rounded-t-xl text-white card">
            <h1 class="text-3xl font-bold">Simulated Stock Price Forecast (GBM Model)</h1>
            <p class="mt-1 opacity-90">Generate a 30-day forecast using Geometric Brownian Motion. Weekends are excluded.</p>
        </header>

        <!-- Main Content Card -->
        <div class="bg-white p-6 sm:p-8 rounded-b-xl card mb-8">
            
            <!-- Input and Generation -->
            <div class="grid grid-cols-1 md:grid-cols-5 gap-4 mb-8 items-end">
                
                <!-- Ticker Input -->
                <div class="col-span-1 md:col-span-1">
                    <label for="stockTicker" class="block text-sm font-medium text-gray-700">Ticker</label>
                    <input type="text" id="stockTicker" value="TSLA"
                           class="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 p-2 border uppercase text-center font-bold">
                </div>

                <!-- Price Input -->
                <div class="col-span-1">
                    <label for="initialPrice" class="block text-sm font-medium text-gray-700">Starting Price ($)</label>
                    <input type="number" id="initialPrice" value="200.00" step="0.01" min="1"
                           class="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 p-2 border">
                </div>
                
                <!-- Annual Return (Drift) Input -->
                <div class="col-span-1">
                    <label for="annualReturn" class="block text-sm font-medium text-gray-700">Annual Return (%)</label>
                    <input type="number" id="annualReturn" value="15" step="1"
                           class="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 p-2 border">
                </div>
                
                <!-- Annual Volatility Input -->
                <div class="col-span-1">
                    <label for="annualVolatility" class="block text-sm font-medium text-gray-700">Annual Volatility (%)</label>
                    <input type="number" id="annualVolatility" value="45" step="1"
                           class="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 p-2 border">
                </div>

                <!-- Button -->
                <button onclick="generateForecast()" class="btn-primary text-white font-semibold py-2 px-6 rounded-lg w-full shadow-md hover:shadow-lg col-span-1">
                    Run Simulation
                </button>
            </div>
            
            <!-- Fundamental Data & Forecast Results -->
            <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
                <!-- Fundamental Data Column -->
                <div id="fundamental-data-output" class="lg:col-span-1">
                    <p class="text-center text-gray-500">Fundamental data will appear here after generation.</p>
                </div>

                <!-- Forecast Table Column -->
                <div id="forecast-output" class="lg:col-span-2">
                    <p class="text-center text-gray-500">Enter parameters and run simulation to see the 30-day forecast.</p>
                </div>
            </div>

            <!-- Error/Message Box -->
            <div id="message-box" class="mt-4 p-3 bg-red-100 text-red-700 rounded-lg hidden" role="alert"></div>
        </div>

    </div>

    <script>
        // Constants for the simulation
        const TRADING_DAYS_PER_YEAR = 252;
        const TIME_STEP = 1 / TRADING_DAYS_PER_YEAR;

        // Global utility function for formatting currency
        const formatCurrency = (amount) => {
            return `$${amount.toFixed(2)}`;
        };

        // Function to display messages or errors
        const showMessage = (message, type = 'error') => {
            const box = document.getElementById('message-box');
            box.textContent = message;
            box.className = `mt-4 p-3 rounded-lg block`;
            
            if (type === 'error') {
                box.classList.add('bg-red-100', 'text-red-700');
            } else {
                box.classList.add('bg-green-100', 'text-green-700');
            }
        };
        
        // Function to clear messages
        const clearMessage = () => {
            document.getElementById('message-box').classList.add('hidden');
        };

        /**
         * Generates a Standard Normal Random Variable (Z) using the Box-Muller transform.
         * @returns {number} A random number following a normal distribution N(0, 1).
         */
        let storedGaussian = null;
        const getNormalRandom = () => {
            if (storedGaussian !== null) {
                const temp = storedGaussian;
                storedGaussian = null;
                return temp;
            }
            const u = Math.random();
            const v = Math.random();
            const z = Math.sqrt(-2.0 * Math.log(u)) * Math.cos(2.0 * Math.PI * v);
            storedGaussian = Math.sqrt(-2.0 * Math.log(u)) * Math.sin(2.0 * Math.PI * v);
            return z;
        };

        /**
         * Simulates a single day's stock price movement using Geometric Brownian Motion (GBM).
         * P_t = P_{t-1} * exp( (mu - sigma^2 / 2) * dt + sigma * sqrt(dt) * Z )
         * * @param {number} currentPrice The price from the previous trading day.
         * @param {number} mu Expected annual return (drift) as a decimal (e.g., 0.15).
         * @param {number} sigma Annual volatility as a decimal (e.g., 0.45).
         * @returns {number} The new, simulated price.
         */
        const simulateDailyPrice = (currentPrice, mu, sigma) => {
            const driftTerm = (mu - (sigma * sigma) / 2) * TIME_STEP;
            const volatilityTerm = sigma * Math.sqrt(TIME_STEP) * getNormalRandom();
            
            const exponent = driftTerm + volatilityTerm;
            const newPrice = currentPrice * Math.exp(exponent);
            
            // Ensure price is non-negative and round to 2 decimal places
            return Math.max(1, parseFloat(newPrice.toFixed(2)));
        };

        /**
         * Provides mock fundamental data based on the ticker.
         * In a real application, this would fetch data from an API.
         */
        const getFundamentalData = (ticker) => {
            switch (ticker) {
                case 'TSLA':
                    return {
                        "Sector": "Consumer Cyclical",
                        "Industry": "Auto Manufacturers",
                        "Forward P/E": "58.21",
                        "Dividend Yield": "0.00%",
                        "Beta": "2.23"
                    };
                case 'GOOGL':
                    return {
                        "Sector": "Technology",
                        "Industry": "Internet Content & Information",
                        "Forward P/E": "22.50",
                        "Dividend Yield": "0.00%",
                        "Beta": "1.05"
                    };
                case 'AAPL':
                    return {
                        "Sector": "Technology",
                        "Industry": "Consumer Electronics",
                        "Forward P/E": "28.00",
                        "Dividend Yield": "0.55%",
                        "Beta": "1.25"
                    };
                default:
                    // Defaulting to the user's requested data structure for fixing the bug
                    return {
                        "Sector": "Technology",
                        "Industry": "Consumer Electronics",
                        "Forward P/E": "33.56",
                        "Dividend Yield": "3.70%", // Fixed the 37.00% typo to 3.70% for realism
                        "Beta": "1.11"
                    };
            }
        };

        /**
         * Generates and renders the fundamental data section.
         */
        function renderFundamentalData(ticker) {
            const data = getFundamentalData(ticker);
            const outputDiv = document.getElementById('fundamental-data-output');

            const itemsHtml = Object.keys(data).map(key => `
                <div class="flex justify-between py-2 border-b border-gray-100 last:border-b-0">
                    <span class="text-sm font-medium text-gray-500">${key}</span>
                    <span class="text-sm font-semibold text-gray-800">${data[key]}</span>
                </div>
            `).join('');

            outputDiv.innerHTML = `
                <div class="p-4 bg-gray-50 rounded-lg border border-gray-200 shadow-inner">
                    <h3 class="text-xl font-bold text-gray-800 mb-3 border-b pb-2">Key Fundamental Data</h3>
                    ${itemsHtml}
                    <p class="text-xs text-gray-400 mt-3">* Data is simulated/mocked for this demonstration.</p>
                </div>
            `;
        }


        /**
         * Generates the 30-day stock price forecast using GBM.
         */
        function generateForecast() {
            clearMessage();
            const priceInput = document.getElementById('initialPrice');
            const tickerInput = document.getElementById('stockTicker');
            const returnInput = document.getElementById('annualReturn');
            const volatilityInput = document.getElementById('annualVolatility');
            
            const initialPrice = parseFloat(priceInput.value);
            const ticker = tickerInput.value.trim().toUpperCase();
            const annualReturnPercent = parseFloat(returnInput.value);
            const annualVolatilityPercent = parseFloat(volatilityInput.value);

            // Convert percentages to decimal for GBM calculation
            const mu = annualReturnPercent / 100;
            const sigma = annualVolatilityPercent / 100;

            // Input validation
            if (isNaN(initialPrice) || initialPrice <= 0) {
                showMessage("Please enter a valid starting price greater than 0.");
                return;
            }
            if (isNaN(annualReturnPercent) || isNaN(annualVolatilityPercent)) {
                 showMessage("Please enter valid numbers for Annual Return and Volatility.");
                return;
            }
            if (ticker === "") {
                showMessage("Please enter a stock ticker symbol.");
                return;
            }

            // Run the fundamental data render first
            renderFundamentalData(ticker);

            const forecastDays = 30;
            let forecastData = [];
            let currentDate = new Date();
            let currentPrice = initialPrice;
            let daysGenerated = 0;

            // Loop to generate 30 trading days
            while (daysGenerated < forecastDays) {
                // Move to the next day
                currentDate.setDate(currentDate.getDate() + 1);
                
                const dayOfWeek = currentDate.getDay();
                
                // 0 = Sunday, 6 = Saturday. Skip weekends.
                if (dayOfWeek === 0 || dayOfWeek === 6) {
                    continue; 
                }

                // Simulate the next day's price using GBM
                currentPrice = simulateDailyPrice(currentPrice, mu, sigma);

                // Format the date for display
                const dateString = currentDate.toLocaleDateString('en-US', { 
                    weekday: 'short', year: 'numeric', month: 'short', day: 'numeric' 
                });

                forecastData.push({
                    date: dateString,
                    price: currentPrice
                });

                daysGenerated++;
            }

            // Render the results
            renderForecastTable(ticker, initialPrice, forecastData);
        }

        /**
         * Renders the forecast data table into the output area.
         */
        function renderForecastTable(ticker, initialPrice, data) {
            const outputDiv = document.getElementById('forecast-output');
            
            // Generate the table header
            const headerHtml = `
                <div class="mb-4">
                    <h2 class="text-2xl font-bold text-gray-800">30-Day Simulation for ${ticker}</h2>
                    <p class="text-gray-600">Starting Price: ${formatCurrency(initialPrice)}</p>
                    <p class="text-sm text-gray-500 italic mt-1">Prices are simulated using Geometric Brownian Motion with specified parameters.</p>
                </div>
            `;

            // Generate the table rows
            const rowsHtml = data.map((item, index) => {
                // Calculate daily change relative to the *previous* trading day
                const priceChange = index === 0 ? 0 : item.price - data[index - 1].price;
                const dailyChangeClass = priceChange >= 0 ? 'text-green-600' : 'text-red-600';
                const dailyIcon = priceChange >= 0 ? '▲' : '▼';

                // Calculate total change relative to the *initial* price
                const totalChange = item.price - initialPrice;
                const totalChangeClass = totalChange >= 0 ? 'text-green-800' : 'text-red-800';

                return `
                    <tr class="${index % 2 === 0 ? 'bg-gray-50' : 'bg-white'} hover:bg-blue-50 transition duration-150">
                        <td class="p-3 text-center whitespace-nowrap text-sm font-medium text-gray-900">${index + 1}</td>
                        <td class="p-3 whitespace-nowrap text-sm text-gray-500">${item.date}</td>
                        <td class="p-3 whitespace-nowrap text-base font-semibold ${totalChangeClass}">
                            ${formatCurrency(item.price)}
                        </td>
                        <td class="p-3 whitespace-nowrap text-sm ${dailyChangeClass} font-mono">
                            ${dailyIcon} ${formatCurrency(Math.abs(priceChange))}
                        </td>
                    </tr>
                `;
            }).join('');

            // Assemble the final table structure
            outputDiv.innerHTML = `
                ${headerHtml}
                <div class="overflow-x-auto rounded-lg border border-gray-200">
                    <table class="min-w-full divide-y divide-gray-200">
                        <thead class="bg-gray-100">
                            <tr>
                                <th scope="col" class="px-3 py-2 text-center text-xs font-medium text-gray-500 uppercase tracking-wider w-1/12">Day</th>
                                <th scope="col" class="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider w-3/12">Trading Date</th>
                                <th scope="col" class="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider w-4/12">Predicted Price</th>
                                <th scope="col" class="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider w-4/12">Daily Change</th>
                            </tr>
                        </thead>
                        <tbody class="divide-y divide-gray-200">
                            ${rowsHtml}
                        </tbody>
                    </table>
                </div>
            `;
        }
        
        // Run the forecast once on page load with default values
        document.addEventListener('DOMContentLoaded', generateForecast);

    </script>
</body>
</html>
