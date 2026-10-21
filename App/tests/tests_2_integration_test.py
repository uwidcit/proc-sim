import pytest
import unittest
from datetime import datetime
from werkzeug.security import generate_password_hash
from sqlalchemy import or_

from App.main import create_app
from App.database import db, create_db
from App.models import User, Admin, Student, Group, StudentGroup, Lot, LotGroup, Bid, Evaluation, RFP
from App.controllers import *

@pytest.fixture(autouse=True, scope="module")
def empty_db():
    app = create_app({'TESTING': True, 'SQLALCHEMY_DATABASE_URI': 'sqlite:///test.db'})
    create_db()
    yield app.test_client()
    db.drop_all()

@pytest.mark.run(order=33)
def test_authenticate():
    user = create_user("bob", "bobpass")
    assert login("bob", "bobpass") != None

class UsersIntegrationTests(unittest.TestCase):
    @pytest.mark.run(order=34)
    def test_user_children_are_users(self):
        admin = Admin("jack", "jackpass")
        db.session.add(admin)
        student = Student("cooper", "20229876", "cooperpass")
        db.session.add(student)
        db.session.commit()
        users_json = get_all_users_json()
        usernames = {u["username"] for u in users_json}
        self.assertIn("jack", usernames)
        self.assertIn("20229876", usernames)
        roles = {u["username"]: u.get("role") for u in users_json}
        self.assertEqual(roles["jack"], "admin")
        self.assertEqual(roles["20229876"], "student")

    # Tests data changes in the database
    @pytest.mark.run(order=35)
    def test_update_user(self):
        update_user(1, "pot")
        user = get_user(1)
        assert user.username == "pot"

class Workflow1IntegrationTests(unittest.TestCase):
    @pytest.mark.run(order=36)
    def test_creating_lots(self):
        db.drop_all()
        create_db()
        create_lot("GIS Lab", "Medium, capable of having 20 machines", 160000.00)
        create_lot("Government Office Lab", "Medium, capable of having 20 machines", 110000.00)
        lots_json = get_all_lots_json()
        self.assertListEqual([
        {
            'id': 1,
            'name': "Lot 1",
            'labType': "GIS Lab",
            'labSize': "Medium, capable of having 20 machines",
            'numMachines': 0,
            'budget': 160000.00,
            'academic_year': 2026,
        },
        {
            'id': 2,
            'name': "Lot 2",
            'labType': "Government Office Lab",
            'labSize': "Medium, capable of having 20 machines",
            'numMachines': 0,
            'budget': 110000.00,
            'academic_year': 2026,
        }
        ], lots_json)

    @pytest.mark.run(order=37)
    def test_edit_lots(self):
        lot = get_lot(1)
        assert lot.budget == 160000.00
        edit_lot(1, budget=170000.00)
        lot = get_lot(1)
        assert lot.budget == 170000.00

    @pytest.mark.run(order=38)
    def test_remove_lot(self):
        lot = get_lot(1)
        assert lot
        remove_lot(1)
        lot = get_lot(1)
        assert not lot

class Workflow2IntegrationTests(unittest.TestCase):
    @pytest.mark.run(order=39)
    def test_create_groupRequest(self):
        remove_lot(2)
        create_lot("GIS Lab", "Medium, capable of having 20 machines", 160000.00)
        create_lot("Government Office Lab", "Medium, capable of having 20 machines", 110000.00)
        create_lot("University Computer Lab", "Medium, capable of having 20 machines", 250000.00)
        create_lot("Data Center", "Medium, capable of having 20 machines", 25000000.00)

        create_student("jack", "20240123", "jackpass")
        create_student("cooper", "20231245", "cooperpass")
        create_student("john", "20229876", "johnpass")
        create_student("tony", "20235678", "tonypass")

        create_student("peper", "20246789", "peperpass")
        create_student("steve", "20242345", "stevepass")
        create_student("clint", "20238901", "clintpass")
        create_student("bruce", "20238902", "brucepass")

        groupName = "TechNova Solution"
        members = [1,2,3,4]

        group = create_group(groupName)
        
        self.assertDictEqual({
            'id': 1,
            'groupName': "G1 TechNova Solution",
            'status': "requested",
            'academic_year': 2026,
        }, group.get_json())

        for member in members:
            add_studentGroup(member, group.id)

        self.assertListEqual([
            {
                'studentID': 1,
                'groupID': 1
            },
            {
                'studentID': 2,
                'groupID': 1
            },
            {
                'studentID': 3,
                'groupID': 1
            },
            {
                'studentID': 4,
                'groupID': 1
            },
        ], get_all_studentGroups_json())

    @pytest.mark.run(order=40)
    def test_trying_to_create_group_request_with_a_duplicate_member(self):
        groupName = "ANK Productions"
        members = [1,2,3,4]

        duplicates = []

        for member in members:
            existing = db.session.scalars(
                db.select(StudentGroup)
                .filter_by(studentID = member)
            ).first()

            if existing:
                duplicates.append(member)
        
        assert duplicates == [1,2,3,4]

        members = [5,6,7,8]
        group = create_group(groupName)

        for member in members:
            add_studentGroup(member, group.id)

class Workflow3IntegrationTests(unittest.TestCase):
    @pytest.mark.run(order=41)
    def test_approving_groupReuests(self):
        ok, err = assign_exclusive_lots(1, count=2)
        assert ok, err

        self.assertListEqual([
            {
                'lotID': 1,
                'groupID': 1
            },
            {
                'lotID': 2,
                'groupID': 1
            }
        ], get_all_lotGroups_json())

        group = get_group(1)
        assert group.status == "approved"

    @pytest.mark.run(order=42)
    def test_rejecting_a_group_request(self):
        groupID = 2

        removed = remove_group(groupID)
        assert removed

class Workflow4IntegrationTests(unittest.TestCase):
    @pytest.mark.run(order=43)
    def test_remove_group(self):
        groupID = 1

        removed = remove_group(groupID)
        assert removed

        groupName = "TechNova Solution"
        members = [1,2,3,4]
        Lot1ID = 1
        Lot2ID = 2

        group = create_group(groupName)

        for member in members:
            add_studentGroup(member, group.id)

        add_lotGroup(Lot1ID, group.id)
        add_lotGroup(Lot2ID, group.id)

        approve_group(group.id)

        groupName = "ANK Productions"
        members = [5,6,7,8]
        Lot1ID = 3
        Lot2ID = 4

        group = create_group(groupName)
        
        for member in members:
            add_studentGroup(member, group.id)

        add_lotGroup(Lot1ID, group.id)
        add_lotGroup(Lot2ID, group.id)

        approve_group(group.id)

class Workflow5IntegrationTests(unittest.TestCase):
    @pytest.mark.run(order=44)
    def test_save_rfp_details(self):
        lotID = 1
        deviceType = "Workstation/Laptop/Tablet"
        resolution = ""
        os = "Mac/Windows/Android/IOS/Linux/Chromium"
        cpu = "Core and frequency range eg (quad-core @ 2.2 - 3.0 GHz)"
        ram = ""
        drive = ""
        gpu = ""
        peripherals = ""
        features = ""
        io = ""

        lot = edit_lotRFP_details(lotID, deviceType=deviceType, os=os, cpu=cpu)
        assert lot.deviceType == "Workstation/Laptop/Tablet"
        assert lot.resolution == ""
        assert lot.os == "Mac/Windows/Android/IOS/Linux/Chromium"
        assert lot.cpu == "Core and frequency range eg (quad-core @ 2.2 - 3.0 GHz)"
        assert lot.ram == ""
        assert lot.drive == ""
        assert lot.gpu == ""
        assert lot.peripherals == ""
        assert lot.features == ""
        assert lot.io == ""

        lotID = 2
        deviceType = ""
        resolution = ""
        os = ""
        cpu = ""
        ram = ""
        drive = "HDD/SSD, speed and capacity range, (list if secondary storage)"
        gpu = "Integrated/Dedicated with memory range"
        peripherals = ""
        features = "Touch screen, WIFI version, bluetooth, Capture Card, Integrated Speakers, Integrated Webcam, Fingerprint reader, LTE"
        io = ""

        lot = edit_lotRFP_details(lotID, drive=drive, gpu=gpu, features=features)
        assert lot.deviceType == ""
        assert lot.resolution == ""
        assert lot.os == ""
        assert lot.cpu == ""
        assert lot.ram == ""
        assert lot.drive == "HDD/SSD, speed and capacity range, (list if secondary storage)"
        assert lot.gpu == "Integrated/Dedicated with memory range"
        assert lot.peripherals == ""
        assert lot.features == "Touch screen, WIFI version, bluetooth, Capture Card, Integrated Speakers, Integrated Webcam, Fingerprint reader, LTE"
        assert lot.io == ""

    @pytest.mark.run(order=45)
    def test_submit_rfp_details(self):
        lotID = 1
        groupID = 1
        existing = get_rfp(groupID, lotID)
        if existing:
            remove_rfp(groupID, lotID)

        rfp = create_rfp(
            groupID,
            lotID,
            deviceType="Workstation/Laptop/Tablet",
            os="Mac/Windows/Android/IOS/Linux/Chromium",
            cpu="Core and frequency range eg (quad-core @ 2.2 - 3.0 GHz)",
        )

        rfp = get_rfp(groupID, lotID)
        assert rfp.deviceType == "Workstation/Laptop/Tablet"
        assert rfp.os == "Mac/Windows/Android/IOS/Linux/Chromium"
        assert rfp.cpu == "Core and frequency range eg (quad-core @ 2.2 - 3.0 GHz)"
        assert rfp.status == "draft"

    @pytest.mark.run(order=46)
    def test_submit_duplicate_rfp_details(self):
        lotID = 1
        groupID = 1

        if not get_rfp(groupID, lotID):
            create_rfp(groupID, lotID)

        rfp = get_rfp(groupID, lotID)
        assert rfp
        assert rfp.status == "draft"

        # Creating again returns the existing draft
        again = create_rfp(groupID, lotID)
        assert again.groupID == rfp.groupID
        assert again.lotID == rfp.lotID

        lotID = 2
        if get_rfp(groupID, lotID):
            remove_rfp(groupID, lotID)

        rfp = create_rfp(
            groupID,
            lotID,
            drive="HDD/SSD, speed and capacity range, (list if secondary storage)",
            gpu="Integrated/Dedicated with memory range",
            features="Touch screen, WIFI version, bluetooth, Capture Card, Integrated Speakers, Integrated Webcam, Fingerprint reader, LTE",
        )
        assert rfp

        rfp = get_rfp(groupID, lotID)
        assert rfp.drive == "HDD/SSD, speed and capacity range, (list if secondary storage)"
        assert rfp.gpu == "Integrated/Dedicated with memory range"
        assert rfp.features == "Touch screen, WIFI version, bluetooth, Capture Card, Integrated Speakers, Integrated Webcam, Fingerprint reader, LTE"
        assert rfp.status == "draft"

class Workflow6IntegrationTests(unittest.TestCase):
    @pytest.mark.run(order=47)
    def test_approve_rfp_Request(self):
        lotID = 1
        groupID = 1

        if not get_rfp(groupID, lotID):
            create_rfp(groupID, lotID)
        approve_rfp(groupID, lotID)

        rfp = get_rfp(groupID, lotID)
        assert rfp.status == "submitted"

    @pytest.mark.run(order=48)
    def test_reject_rfp_Request(self):
        groupID = 1
        lotID = 2

        if not get_rfp(groupID, lotID):
            create_rfp(groupID, lotID)
        removed = remove_rfp(groupID, lotID)
        assert removed

class Workflow7IntegrationTests(unittest.TestCase):
    @pytest.mark.run(order=49)
    def test_remove_rfp(self):
        groupID = 1
        lotID = 1

        removed = remove_rfp(groupID, lotID)
        assert removed

        rfp = create_rfp(groupID, lotID)
        approve_rfp(groupID, lotID)

        groupID = 2
        lotID = 3
        rfp = create_rfp(groupID, lotID)
        approve_rfp(groupID, lotID)

class Workflow8IntegrationTests(unittest.TestCase):
    @pytest.mark.run(order=50)
    def test_place_bid(self):
        sourceGroupID = 1
        recipientGroupID = 2
        lotID = 3
        bidDocument=b'fake pdf content'
        bidDocumentName='test.pdf'
        quotationAmount= 25000.0

        bid = create_bid(lotID, sourceGroupID, recipientGroupID, bidDocument, bidDocumentName, quotationAmount)
        
        assert bid
        assert bid.sourceGroupID == 1
        assert bidDocumentName == 'test.pdf'
        assert recipientGroupID == 2
        assert lotID == 3
        assert quotationAmount == 25000.0

class Workflow9IntegrationTests(unittest.TestCase):
    @pytest.mark.run(order=51)
    def test_remove_bid(self):
        bidID = 1

        removed = remove_bid(bidID)
        assert removed

        sourceGroupID = 1
        recipientGroupID = 2
        lotID = 3
        bidDocument=b'fake pdf content'
        bidDocumentName='test.pdf'
        quotationAmount= 25000.0

        bid = create_bid(lotID, sourceGroupID, recipientGroupID, bidDocument, bidDocumentName, quotationAmount)

        sourceGroupID = 2
        recipientGroupID = 1
        lotID = 1
        bidDocument=b'fake pdf content'
        bidDocumentName='test.pdf'
        quotationAmount= 25000.0

        bid = create_bid(lotID, sourceGroupID, recipientGroupID, bidDocument, bidDocumentName, quotationAmount)

class Workflow10IntegrationTests(unittest.TestCase):
    @pytest.mark.run(order=52)
    def test_create_evaluation(self):
        sourceGroupID = 1
        recipientGroupID = 2
        bidID = 2
        lotID = 1
        specsMet = 5
        presentation = 3
        professionalism = 2
        budget = 4

        evaluation = create_evaluation(sourceGroupID, recipientGroupID, bidID, lotID, specsMet, presentation, professionalism, budget)

        assert evaluation
        assert evaluation.status == "draft"
        assert evaluation.overallScore == 5.6

class Workflow11IntegrationTests(unittest.TestCase):
    @pytest.mark.run(order=53)
    def test_edit_evaluation(self):
        evaluationID = 1
        specsMet = 9
        presentation = 3
        professionalism = 2
        budget = 4
        deviceType = "device type comment"
        resolution = "resolution comment"
        ram = "ram comment"

        edited = edit_evaluation(evaluationID, specsMet, presentation, professionalism, budget, deviceType=deviceType, resolution=resolution, ram=ram)
        assert edited
        
        evaluation = get_evaluation(evaluationID)
        assert evaluation.overallScore == 7.2
        assert evaluation.deviceType == "device type comment"
        assert evaluation.resolution == "resolution comment"
        assert evaluation.ram == "ram comment"

    @pytest.mark.run(order=54)
    def test_select_evaluation(self):
        evaluationID = 1

        select_evaluation(evaluationID)

        evaluation = get_evaluation(evaluationID)
        assert evaluation
        assert evaluation.status == "selected"

class Workflow12IntegrationTests(unittest.TestCase):
    @pytest.mark.run(order=55)
    def test_remove_evaluation(self):
        evaluationID = 1

        removed = remove_evaluation(evaluationID)
        assert removed