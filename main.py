import json
import csv
import tempfile
from commonregex import CommonRegex
from documentcloud.addon import AddOn
import folium
from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter


class AddressMap(AddOn):
    """AddressMap AddOn class"""

    def main(self):
        addresses = []

        # Extract addresses from documents
        for document in self.get_documents():
            for page in range(1, document.pages + 1):
                text = document.get_page_text(page)
                parsed_text = CommonRegex(text)
                street_addresses = set(parsed_text.street_addresses)

                for address in street_addresses:
                    # Create annotations for extracted addresses
                    annotation = document.annotations.create(
                        "Address found on this page",
                        page - 1,
                        content=address,
                        access=self.data.get("access"),
                    )

                    addresses.append(
                        {
                            "document": document.title,
                            "page": page,
                            "url": annotation.canonical_url,
                            "address": address,
                        }
                    )

        # Generate a CSV file with extracted addresses
        csv_file = tempfile.NamedTemporaryFile(mode="w+", delete=False, suffix=".csv")
        fieldnames = ["document", "page", "url", "address"]
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(addresses)
        csv_file.close()

        # Upload the CSV file
        self.upload_file(open(csv_file.name))

        # Geocode addresses
        geolocator = Nominatim(user_agent="address_mapper")
        geocode = RateLimiter(geolocator.geocode, min_delay_seconds=1)
        locations = [
            (geocode(addr["address"]), addr["document"], addr["page"], addr["url"])
            for addr in addresses
        ]

        # Remove any None values in locations
        locations = [loc for loc in locations if loc[0] is not None]

        # Create a folium map
        first_location = locations[0][0]
        map = folium.Map(location=[first_location.latitude, first_location.longitude], zoom_start=12)

        # Add markers to the map
        for location, doc_title, page, url in locations:
            folium.Marker(
                [location.latitude, location.longitude],
                popup=f"{doc_title}<br>Page: {page}<br><a href='{url}' target='_blank'>View Annotation</a>",
            ).add_to(map)

        # Save the map as an HTML file and upload
        map_file = tempfile.NamedTemporaryFile(mode="w+", delete=False, suffix=".html")
        map.save(map_file.name)
        map_file.close()

        self.upload_file(open(map_file.name), "addresses_map.html")

        self.set_message("Address extraction and map generation completed")


if __name__ == "__main__":
    AddressMap().main()
