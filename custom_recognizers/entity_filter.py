def remove_address_false_positive(results, text):

    filtered = []


    address_keywords = [
        "jalan",
        "jln",
        "lorong",
        "persiaran",
        "taman",
        "no",
        "selangor",
        "kuala lumpur",
        "johor",
        "penang"
    ]

    for result in results:
        entity_text = text[
            result.start:result.end
        ].lower()

        # remove PERSON detection from address words
        if result.entity_type in [
            "PERSON",
            "PERSON_NAME"
        ]:

            if any(
                word in entity_text
                for word in address_keywords
            ):
                continue

        filtered.append(result)

    return filtered

def remove_location_inside_address(results, text):
    final = []

    addresses = [
        r for r in results
        if r.entity_type == "ADDRESS"
    ]

    for r in results:

        if r.entity_type == "LOCATION":

            inside_address = False

            for addr in addresses:

                if (
                    r.start >= addr.start
                    and r.end <= addr.end
                ):
                    inside_address = True


            if inside_address:
                continue


        final.append(r)


    return final