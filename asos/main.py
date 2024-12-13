import time
from concurrent.futures import ThreadPoolExecutor
import asos

def process_categories(category_ids, executor):
    futures = []
    for category_id in category_ids:
        url = f"https://www.asos.com/api/product/search/v2/categories/{category_id}?channel=desktop-web&country=US&currency=USD&keyStoreDataversion=mhabj1f-41&lang=en-US&limit=200&offset=0&rowlength=4&store=US&tstSearchSponsoredProducts=true"
        futures.append(
            executor.submit(asos.Asos(thread_id=category_id, request_type=asos.RequestType.GET_DATA, thread_url=url).run)
        )
    for future in futures:
        future.result()

def process_products(products, executor):
    print("by the look ...")
    new_product_count = 0
    futures = []

    for product in products:
        product_url = product.get("url")
        if not product_url or asos.FileManager.is_duplicate("processed_products", product_url):
            continue 

        full_url = f"https://www.asos.com/{product_url}"
        futures.append(
            executor.submit(asos.Asos(thread_id=product.get("id"), request_type=asos.RequestType.BUY_THE_LOOK, thread_url=full_url).run)
        )
        asos.FileManager.mark_as_processed("processed_products", product_url)
        new_product_count += 1  

    for future in futures:
        future.result()

    return new_product_count

def main():
    # category_ids=["7046","27108","8799","4172","9577","26091","4174","1314","5678","20753","25997","26090","3159","5034","9265","4210","4209","27110"]
    category_ids=["4209","27110"]
    with ThreadPoolExecutor(max_workers=8) as executor:
        while True:
            process_categories(category_ids, executor)

            print("Checking for new products")
            new_products = 0
            data = asos.FileManager.load_from_file("data").get("data", [])
            for category in data:
                products = category.get("products", [])
                new_products += process_products(products, executor)

            print(f"New products added: {new_products}")

            print("Waiting before the next check...")
            time.sleep(300)  

if __name__ == "__main__":
    print("Start Program")
    main()
    print("End Program")
