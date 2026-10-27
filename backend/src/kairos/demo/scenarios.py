"""Explicit bilingual example conversations, not a natural-language parser."""


def examples(language: str) -> list[dict]:
    italian = language == 'it'
    texts = [
        ('mechanic', 'Dal meccanico', 'At the mechanic', [
            ('Domani devo portare la moto dal meccanico', 'Tomorrow I need to take my motorbike to the mechanic',
             {'title': 'Portare la moto dal meccanico' if italian else 'Take motorbike to the mechanic', 'day_offset': 1}),
            ('Alle 15:00 da Yamaha Motorsprint a Porto di Mare', 'At 15:00 at Yamaha Motorsprint in Porto di Mare',
             {'start_time': '15:00', 'location': 'Yamaha Motorsprint, Porto di Mare'}),
            ('Ricordamelo 2 ore prima', 'Remind me 2 hours before', {'reminders': [{'minutes_before': 120}]}),
            ('Prima di andare dal meccanico devo ritirare i documenti della moto',
             'Before going to the mechanic I need to collect the motorbike documents',
             {'task': 'Ritirare i documenti della moto' if italian else 'Collect the motorbike documents', 'timing': 'before'}),
            ('Togli l’attività prima dell’appuntamento', 'Remove the activity before the appointment', {'remove': True}),
        ]),
        ('dinner', 'Una cena', 'Dinner with friends', [
            ('Domani sera ceno con gli amici', 'Tomorrow evening I am having dinner with friends',
             {'title': 'Cena con gli amici' if italian else 'Dinner with friends', 'day_offset': 1}),
            ('Alle 20:30 al ristorante in via roma 12, milano', 'At 20:30 at the restaurant in via roma 12, milano',
             {'start_time': '20:30', 'location': 'Ristorante, Via Roma 12, Milano'}),
            ('La cena dura 2 ore', 'Dinner lasts 2 hours', {'duration_minutes': 120}),
            ('Nessun promemoria', 'No reminders', {'reminders': []}),
        ]),
        ('study', 'Una sessione di studio', 'A study session', [
            ('Dopodomani voglio studiare Python', 'The day after tomorrow I want to study Python',
             {'title': 'Studiare Python' if italian else 'Study Python', 'day_offset': 2}),
            ('Comincio alle 10:00 e studio per 90 minuti', 'I start at 10:00 and study for 90 minutes',
             {'start_time': '10:00', 'duration_minutes': 90}),
            ('Dopo lo studio voglio fare una passeggiata', 'After studying I want to take a walk',
             {'task': 'Fare una passeggiata' if italian else 'Take a walk', 'timing': 'after'}),
            ('Aggiungi un promemoria 1 giorno prima', 'Add a reminder 1 day before', {'reminders': [{'minutes_before': 1440}]}),
        ]),
    ]
    return [
        {'id': key, 'label': it_label if italian else en_label,
         'steps': [{'message': it_message if italian else en_message, 'proposal': proposal}
                   for it_message, en_message, proposal in steps]}
        for key, it_label, en_label, steps in texts
    ]
