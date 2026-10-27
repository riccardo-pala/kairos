"""Fictional bilingual examples, independent of private user conversations."""


def examples(language: str) -> list[dict]:
    italian = language == 'it'
    texts = [
        ('museum', 'Una visita al museo', 'A museum visit', [
            ('Domani voglio visitare un museo a Roma', 'Tomorrow I want to visit a museum in Rome',
             {'title': 'Visitare un museo a Roma' if italian else 'Visit a museum in Rome', 'day_offset': 1}),
            ('Alle 11:30 al museo in centro a Roma', 'At 11:30 at the city-centre museum in Rome',
             {'start_time': '11:30', 'location': 'Museo del centro, Roma' if italian else 'City-centre museum, Rome'}),
            ('Vorrei un promemoria 45 minuti prima', 'I would like a reminder 45 minutes before', {'reminders': [{'minutes_before': 45}]}),
            ('Prima della visita al museo devo acquistare i biglietti',
             'Before visiting the museum I need to buy tickets',
             {'task': 'Acquistare i biglietti' if italian else 'Buy tickets', 'timing': 'before'}),
            ('Togli l’attività prima della visita', 'Remove the activity before the visit', {'remove': True}),
        ]),
        ('dinner', 'Una cena a Londra', 'Dinner in London', [
            ('Domani sera ho una cena a Londra', 'Tomorrow evening I have dinner in London',
             {'title': 'Cena a Londra' if italian else 'Dinner in London', 'day_offset': 1}),
            ('Alle 19:00 al ristorante in centro a Londra', 'At 19:00 at the city-centre restaurant in London',
             {'start_time': '19:00', 'location': 'Ristorante del centro, Londra' if italian else 'City-centre restaurant, London'}),
            ('La cena dura 90 minuti', 'Dinner lasts 90 minutes', {'duration_minutes': 90}),
            ('Nessun promemoria', 'No reminders', {'reminders': []}),
        ]),
        ('picnic', 'Un picnic a New York', 'A picnic in New York', [
            ('Dopodomani organizzo un picnic a New York', 'The day after tomorrow I am organizing a picnic in New York',
             {'title': 'Picnic a New York' if italian else 'Picnic in New York', 'day_offset': 2}),
            ('Comincia alle 12:00 e dura 2 ore', 'It starts at 12:00 and lasts 2 hours',
             {'start_time': '12:00', 'duration_minutes': 120}),
            ('Dopo il picnic voglio fare una passeggiata nel parco', 'After the picnic I want to take a walk in the park',
             {'task': 'Fare una passeggiata nel parco' if italian else 'Take a walk in the park', 'timing': 'after'}),
            ('Aggiungi un promemoria 1 giorno prima', 'Add a reminder 1 day before', {'reminders': [{'minutes_before': 1440}]}),
        ]),
    ]
    return [
        {'id': key, 'label': it_label if italian else en_label,
         'steps': [{'message': it_message if italian else en_message, 'proposal': proposal}
                   for it_message, en_message, proposal in steps]}
        for key, it_label, en_label, steps in texts
    ]
