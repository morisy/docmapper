import csv
import folium
import geopy
from geopy.geocoders import Nominatim
from zipfile import ZipFile
import os

from documentcloud.addon import AddOn
from commonregex import CommonRegex

geolocator = Nominatim(user_agent="address_mapper")


class AddressMapper(AddOn):
    """Extracts addresses from documents, creates annotations, and generates a map with links to the annotations."""

    def __init__(self):
        super().__init__()

    def detect(self, document, page, parsed, positions):
        addresses = []
        for word in set(parsed):
            for info in positions:
                if word in info["text"]:
                    location = geolocator.geocode(word)
                    if location:
                        annotation = document.annotations.create(
                            "Address found",
                            page - 1,
                            content=word,
                            access=self.data.get("access"),
                            x1=info["x1"],
                            y1=info["y1"],
                            x2=info["x2"],
                            y2=info["y2"],
                        )
                        addresses.append(
                            {
                                "address": word,
                                "latitude": location.latitude,
                                "longitude": location.longitude,
                                "document_title": document.title,
                                "page": page,
                                "annotation_id": annotation.id,
                            }
                        )
        return addresses

    def main(self):
        all_addresses = []

        # Extract addresses and create annotations
        for document in self.get_documents():
            for page in range(1, document.pages + 1):
                text = document.get_page_text(page)
                parsed_text = CommonRegex(text)

                positions = document.get_page_text(page, positions=True)

                addresses = set(parsed_text.street_addresses) | set(parsed_text.po_boxes)
                found_addresses = self.detect(document, page, addresses, positions)
                all_addresses.extend(found_addresses)

        # Create a CSV file with the extracted addresses
        with open("addresses.csv", "w", newline="") as csvfile:
            fieldnames = ["address", "latitude", "longitude", "document_title", "page", "annotation_id"]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(all_addresses)

        # Generate a map with the extracted addresses using Stamen Toner tiles
        m = folium.Map(tiles="Stamen Toner")

        for address in all_addresses:
            folium.Marker(
                location=[address["latitude"], address["longitude"]],
                popup=f'<a href="https://www.documentcloud.org/documents/{address["annotation_id"]}/annotations/{address["annotation_id"]}.html" target="_blank">{address["address"]}</a>',
            ).add_to(m)

        m.save("map.html")

        # Zip the map HTML and CSV of exported addresses
        with ZipFile("address_map_export.zip", "w") as zipped_export:
            zipped_export.write("map.html")
            zipped_export.write("addresses.csv")

        # Upload the zip file
        with open("address_map_export.zip", "rb") as file:
            self.upload_file(file)

        # Clean up
        os.remove("map.html")
        os.remove("addresses.csv")
        os.remove("address_map_export.zip")


if __name__ == "__main__":
    AddressMapper().main()
