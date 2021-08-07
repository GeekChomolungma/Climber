from strategy.FirstBuy import fb
import chomoClient.client

# Replace the uri string with your MongoDB deployment's connection string.
conn_str = "mongodb://market:admin123@localhost:27017"
bo = fb.FirstBuyPoint(conn_str)
bo.getAccountBalance("usdt")
bo.getAccountBalance("btc")
#chomoClient.client.PlaceOrder("btcusdt", "sell-limit", "0.0009", "50000.333333", "spot-api")
#chomoClient.client.CancelOrder("338263242190689")
chomoClient.client.GetOrder("338263242190689")