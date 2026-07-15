def merge_entities(results):

    priority = {

        "ADDRESS": 100,
        "PERSON_NAME": 100,
        "ID_NUMBER": 100,
        "FINANCIAL": 100,
        "PHONE_NUMBER": 100,

        "PERSON": 50,
        "LOCATION": 40
    }


    results = sorted(
        results,
        key=lambda x: (
            x.start,
            -(x.end - x.start)
        )
    )


    final_results = []


    for current in results:

        keep = True


        for existing in final_results:


            # check overlap
            overlap = (
                current.start < existing.end
                and current.end > existing.start
            )


            if overlap:


                current_length = current.end - current.start
                existing_length = existing.end - existing.start


                current_priority = priority.get(
                    current.entity_type,
                    0
                )

                existing_priority = priority.get(
                    existing.entity_type,
                    0
                )


                # Current entity is better
                if (
                    current_priority > existing_priority
                    or
                    (
                        current_priority == existing_priority
                        and current_length > existing_length
                    )
                ):

                    final_results.remove(existing)
                    break


                else:
                    keep = False
                    break



        if keep:
            final_results.append(current)


    return final_results