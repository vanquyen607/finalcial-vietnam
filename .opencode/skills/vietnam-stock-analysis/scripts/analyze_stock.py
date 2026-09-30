import sys
import os
# Make sure vnstock, pandas, pytz are installed manually in your environment.
# Example: pip install -r requirements.txt

from vnstock import Vnstock
import pandas as pd
from datetime import datetime, timedelta

def fetch_stock_data(symbol):
    end_date = datetime.now()
    # Fetch more data to ensure we get 200 valid candles after cleaning
    start_date = end_date - timedelta(days=200 * 1.5)

    try:
        stock = Vnstock().stock(symbol=symbol, source='VCI')
        df = stock.quote.history(start=start_date.strftime('%Y-%m-%d'), end=end_date.strftime('%Y-%m-%d'), interval='1D')

        if df.empty:
            print(f"Không lấy được dữ liệu cho mã cổ phiếu {symbol}. Vui lòng kiểm tra lại mã hoặc kết nối.")
            return None

        # Ensure correct column names
        df.rename(columns={'time': 'Date', 'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close', 'volume': 'Volume'}, inplace=True)
        df['Date'] = pd.to_datetime(df['Date'])
        df.set_index('Date', inplace=True)

        # Take last 200 candles
        df = df.tail(200)

        if len(df) < 20: # A minimal check, but AI will handle deeper analysis
            print(f"Cảnh báo: Chỉ có {len(df)} ngày dữ liệu cho mã cổ phiếu {symbol}. Cần ít nhất 20 ngày để phân tích kỹ thuật đầy đủ.")

        # Define the directory for stock data and create it if it doesn't exist
        script_dir = os.path.dirname(os.path.abspath(__file__))
        stock_data_dir = os.path.join(script_dir, os.pardir, 'stock-data') # Relative to skill root
        os.makedirs(stock_data_dir, exist_ok=True)

        # Save the raw data to a JSON file in the new directory
        json_filename = os.path.join(stock_data_dir, f"{symbol.lower()}_data.json")
        df_to_save = df.reset_index() # Reset index to include Date in JSON output
        df_to_save.to_json(json_filename, orient='records', indent=4, date_format='iso')
        print(f"Dữ liệu thô đã được lưu vào: {json_filename}")
        return json_filename

    except Exception as e:
        print(f"Lỗi xảy ra trong quá trình thu thập dữ liệu: {e}")
        print("Có thể do mã cổ phiếu không tồn tại hoặc lỗi kết nối dữ liệu.")
        return None


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Vui lòng cung cấp mã cổ phiếu (symbol) làm đối số.")
        sys.exit(1)

    stock_symbol = sys.argv[1].upper()
    fetch_stock_data(stock_symbol)
