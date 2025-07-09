import os
import pandas as pd
from ..models import Duty, DutyType, Member, MemberDuty, CommonFound, MembershipPeriod, Category
import re
from datetime import datetime

def run():
    if not os.path.exists("alreadyDeleted.txt"):
        MemberDuty.objects.all().delete()
        Duty.objects.all().delete()
        DutyType.objects.all().delete()
        Category.objects.all().delete()
        CommonFound.objects.all().delete()

        DutyTypes = ["temporary", "permanent"]

        for element in DutyTypes:
            DutyType.objects.create(
                name=element
            )
        with open("alreadyDeleted.txt", "w") as f:
            f.write("Deleted")

    df = pd.read_excel('./LST_duties_2025.xlsx', header=1)

    for row in df.itertuples(index=False):
        name_col = row[0] if not pd.isna(row[0]) else row[1]
        if not isinstance(row[1], float) and not pd.isna(row[1]):
            if '.' not in row[1]:
                category = row[1]
                category, created = Category.objects.get_or_create(
                    name=category
                )

        duty_name = row[2] if not pd.isna(row[2]) else row[3]
        description = row[8] if not pd.isna(row[8]) else ''
        duration = row[4]
        max_members = int(row[5]) if not pd.isna(row[5]) else None

        if pd.isna(name_col) or pd.isna(duty_name) or pd.isna(duration) or pd.isna(max_members):
            continue
        
        duty_type = DutyType.objects.get(name='permanent') if duration == 'long' else DutyType.objects.get(name='temporary')
        duty, created = Duty.objects.get_or_create(
            name=duty_name,
            category=category,
            description=description,
            duty_type=duty_type,
            maximum_members=max_members
        )
        print('---------- '+duty.name+' ------------')
        
    if not CommonFound.objects.all().exists():   
        CF_IDS = [
            149, 144, 65, 298, 113, 428, 533, 448, 551, 562, 1, 73, 534, 493, 535, 544, 536, 545,
            210, 278, 558, 413, 6, 12, 532, 2, 3, 5, 7, 8, 10, 11, 13, 14, 15, 487, 16, 18, 19, 23,
            24, 25, 26, 27, 28, 29, 30, 33, 34, 36, 37, 38, 39, 41, 42, 43, 48, 49, 51, 52, 54, 55,
            57, 58, 59, 60, 61, 62, 64, 66, 67, 68, 69, 71, 74, 75, 76, 77, 79, 80, 81, 82, 85, 86,
            87, 88, 89, 90, 97, 98, 101, 92, 100, 35, 108, 109, 111, 112, 116, 118, 119, 120, 126,
            128, 130, 132, 134, 138, 140, 146, 147, 152, 156, 157, 161, 162, 163, 164, 165, 166,
            169, 172, 178, 179, 180, 181, 182, 183, 184, 185, 186, 115, 145, 117, 123, 104, 154,
            187, 188, 189, 190, 192, 194, 195, 197, 199, 200, 202, 203, 204, 205, 207, 209, 211,
            212, 213, 214, 216, 218, 221, 222, 223, 224, 225, 226, 227, 228, 229, 230, 231, 233,
            234, 235, 237, 238, 240, 242, 243, 244, 245, 247, 248, 249, 250, 251, 252, 253, 254,
            255, 256, 257, 258, 259, 262, 265, 266, 267, 268, 269, 270, 273, 274, 275, 276, 279,
            281, 282, 283, 284, 285, 286, 287, 288, 290, 291, 292, 293, 294, 295, 296, 297, 299,
            300, 301, 302, 303, 304, 305, 306, 307, 308, 309, 310, 311, 312, 313, 314, 316, 317,
            318, 320, 322, 323, 324, 325, 327, 328, 331, 332, 333, 336, 337, 338, 339, 340, 342,
            343, 346, 347, 348, 349, 350, 352, 353, 280, 354, 355, 356, 357, 358, 360, 361, 362,
            363, 364, 365, 367, 368, 369, 370, 372, 373, 375, 376, 377, 379, 382, 383, 384, 385,
            386, 388, 389, 390, 391, 392, 393, 394, 396, 397, 398, 399, 400, 403, 405, 407, 408,
            409, 415, 416, 417, 419, 420, 422, 423, 425, 426, 429, 431, 435, 436, 437, 438, 439,
            440, 441, 442, 443, 444, 445, 449, 450, 451, 453, 454, 456, 457, 458, 459, 460, 462,
            463, 467, 468, 469, 471, 472, 473, 475, 476, 477, 479, 480, 481, 484, 485, 486, 488,
            489, 490, 492, 494, 497, 499, 500, 501, 502, 503, 504, 505, 506, 507, 509, 510, 511,
            512, 514, 515, 516, 519, 520, 521, 522, 523, 495, 491, 466, 455, 524, 526, 527, 525
        ]

        for id in CF_IDS:
            member = Member.objects.get(pk=id)
            try:
                start = MembershipPeriod.objects.get(member=member, end_date__isnull=True).start_date
            except MembershipPeriod.DoesNotExist:
                start = datetime(year=2018, month=1, day=1)
            CommonFound.objects.create(
                member = member,
                start_date = start
            )
