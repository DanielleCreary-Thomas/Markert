import json
import requests
import psycopg2
import discord
from discord import SyncWebhook

# connect to db
conn = psycopg2.connect("dbname=Markert user=postgres password=notasecret")
# open cursor
cur = conn.cursor()


def new_marker_insert(response):
    for product in response["products"]:
        name = product["variants"][0]["title"]
        ccode = product["variants"][0]["sku"]
        ccode = ccode[2:-2]

        price = product["variants"][0]["price"]
        image = product["variants"][0]["featured_image"]
        availability = product["variants"][0]["available"]
        price_diff = None

        cur.execute("INSERT INTO sketch_markers (ccode, name, image, price, price_diff, availability) "
                    "VALUES (%s, %s, %s, %s, %s, %s) "
                    " ON CONFLICT DO NOTHING",
                    (ccode, name, image, price, price_diff, availability))
        conn.commit()


def price_update(response):
    cur.execute("SELECT id, ccode, price FROM sketch_markers")
    marker_data = cur.fetchall()
    marker_dict = {}
    for marker in marker_data:
        data_id = marker[0]
        data_ccode = marker[1]
        data_price = marker[2]
        marker_dict[data_ccode] = (data_id, data_price)

    for product in response["products"]:
        ccode = product["variants"][0]["sku"]
        ccode = ccode[2:-2]
        price = product["variants"][0]["price"]

        if ccode in marker_dict:
            if marker_dict[ccode][1] is None:
                price_diff = None
            else:
                price_diff = compare_price(marker_dict[ccode][1], price)
            cur.execute("UPDATE sketch_markers"
                        " SET price = %s,"
                        " price_diff = %s"
                        " WHERE id = %s", (price, price_diff, marker_dict[ccode][0]))
            conn.commit()


def compare_price(new_price, data_price):
    difference = float(new_price) - float(data_price)
    if difference > 0:
        return "-{:.2f}".format(float(difference))
    elif difference < 0:
        return "+{:.2f}".format(float(difference))
    else:
        return "0.00"


def alert_check():
    cur.execute("SELECT id, ccode, name, price, price_diff, availability FROM sketch_markers")
    marker_data = cur.fetchall()
    # might not need the marker dict
    result = "You've got a Sale!\n"
    saleCount = 0
    saleitems = False
    for marker in marker_data:
        data_id = marker[0]
        data_ccode = marker[1]
        data_name = marker[2]
        data_price = marker[3]
        data_price_diff = marker[4]
        data_availability = marker[5]

        print(f"CCode: {data_ccode}, Price {data_price}, Diff: {data_price_diff}, Avail: {data_availability}")
        if data_availability is True:
            # diff_val = data_price_diff[1:] if len(data_price_diff) > 4 else data_price_diff
            diff_val = float(data_price_diff)
            print(f"Diff Val: {diff_val}")
            if diff_val < 0.0:
                saleitems = True
                saleCount += 1
                print(f"CCode: {data_ccode}, Name: {data_name}, Price:{data_price},"
                      f" Price Diff:{data_price_diff}, Available:{data_availability}\n")
                result += "Colour code: {}, Colour Name: {}, Colour Price: {}, Colour Price Diff: {} \n".format(
                    data_ccode, data_name, data_price, data_price_diff
                )

    print(saleCount)
    result += "Buy now: https://www.deserres.ca/products/copic-sketch-marker?colour=all"
    if not saleitems:
        result = "No sales today, womp womp :("
    return result


def scan():
    response = requests.get("https://www.deserres.ca/collections/COPSK/?view=super.json&limit=12&page=1").json()
    print(response)

    ##Fields Wanted: ColourCode, Name, Price, Image,availability
    ##Marker Table: CCode, Name, Image
    ##Price Table: CCode, Price,Timestamp, availability?

    new_marker_insert(response)
    price_update(response)
    send_disc_msg(alert_check())


def send_disc_msg(message):
    webhook = SyncWebhook.from_url(
        "https://discord.com/api/webhooks/1219829534044717057/cnuI0n76o5w9cigmjnccJhMv6nZscKN2AaurkSiazJGfkdUv0qXI0Htp-jeZTV2f7xmW")
    if len(message) > 2000:
        msg_subset = ""
        lines = message.split("\n")
        i = 0
        msg_length = 0
        for line in lines:
            msg_length += len(line + "\n")
            if msg_length < 1999:
                msg_subset += line+"\n"
                i += 1
            else:
                webhook.send(msg_subset)
                msg_subset = line+"\n"
                msg_length = len(line + "\n")
        webhook.send(len(lines).__str__())

    else:
        webhook.send(message)



if __name__ == "__main__":
    scan()
    #     name = product["variants"][0]["title"]
    #     ccode = product["variants"][0]["sku"]
    #     price = product["variants"][0]["price"]
    #     image = product["variants"][0]["featured_image"]
    #     availability = product["variants"][0]["available"]
    #
    #     # ccode = ccode.lstrip("CM").rstrip("-S")
    #     # print(f"CCode: {ccode}, Name: {name}, Price:{price}, Image:{image}, Available:{availability}\n")
    #
    #     ccode = ccode[2:-2]
    #
    #     print(f"CCode: {ccode}, Name: {name}, Price:{price}, Image:{image}, Available:{availability}\n")
    #
    # cur.execute("SELECT id, ccode, price FROM sketch_markers")
    # marker_data = cur.fetchall()
    # for marker in marker_data:
    #     print(f"id:{marker[0]}, ccode:{marker[1]}, price:{marker[2]}")
    # cur.execute("INSERT INTO sketch_markers(ccode, name, image) VALUES (%s, %s, %s)", (ccode, name, image))
    # conn.commit()
