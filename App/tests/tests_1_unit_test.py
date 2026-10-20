import pytest
import unittest
from datetime import datetime
from werkzeug.security import generate_password_hash

from App.main import create_app
from App.database import db, create_db
from App.models import User, Admin, Student, Group, StudentGroup, Lot, LotGroup, Bid, Evaluation, RFP


class AdminUnitTests(unittest.TestCase):
    @pytest.mark.run(order=1)
    def test_new_admin(self):
        admin = Admin("alice", "alicepass")
        assert admin.username == "alice"

    @pytest.mark.run(order=2)
    def test_admin_get_json(self):
        admin = Admin("alice", "alicepass")
        admin_json = admin.get_json()
        assert admin_json["username"] == "alice"
        assert admin_json["role"] == "admin"

    @pytest.mark.run(order=3)
    def test_admin_hashed_password(self):
        admin = Admin("alice", "alicepass")
        assert admin.password != "alicepass"

    @pytest.mark.run(order=4)
    def test_admin_check_password(self):
        admin = Admin("alice", "alicepass")
        assert admin.check_password("alicepass")

    @pytest.mark.run(order=5)
    def test_admin_is_admin(self):
        admin = Admin("alice", "alicepass")
        assert admin.is_admin()

    @pytest.mark.run(order=6)
    def test_admin_is_not_student(self):
        admin = Admin("alice", "alicepass")
        assert not admin.is_student()

class StudentUnitTests(unittest.TestCase):
    @pytest.mark.run(order=7)
    def test_new_student(self):
        student = Student("bob", "20231245", "bobpass")
        assert student.username == "20231245"

    @pytest.mark.run(order=8)
    def test_student_get_json(self):
        student = Student("bob", "20240123", "bobpass")
        student_json = student.get_json()
        assert student_json["username"] == "20240123"
        assert student_json["role"] == "student"

    @pytest.mark.run(order=9)
    def test_student_hashed_password(self):
        student = Student("bob", "20240123", "bobpass")
        assert student.password != "bobpass"

    @pytest.mark.run(order=10)
    def test_student_check_password(self):
        student = Student("bob", "20240123", "bobpass")
        assert student.check_password("bobpass")

    @pytest.mark.run(order=11)
    def test_student_is_student(self):
        student = Student("bob", "20240123", "bobpass")
        assert student.is_student()

    @pytest.mark.run(order=12)
    def test_student_is_not_admin(self):
        student = Student("bob", "20240123", "bobpass")
        assert not student.is_admin()

class GroupUnitTests(unittest.TestCase):
    @pytest.mark.run(order=13)
    def test_new_group(self):
        group = Group("Algorithms")
        assert group.groupName == "Algorithms"

    @pytest.mark.run(order=14)
    def test_group_get_json(self):
        group = Group("Algorithms")
        group_json = group.get_json()
        assert group_json["groupName"] == "Algorithms"
        assert group_json["academic_year"] == 2025


class StudentGroupUnitTests(unittest.TestCase):
    @pytest.mark.run(order=15)
    def test_new_student_group(self):
        student_group = StudentGroup(1, 2)
        assert student_group.studentID == 1
        assert student_group.groupID == 2

    @pytest.mark.run(order=16)
    def test_student_group_get_json(self):
        student_group = StudentGroup(1, 2)
        sg_json = student_group.get_json()
        self.assertDictEqual(sg_json, {"studentID": 1, "groupID": 2})


class LotUnitTests(unittest.TestCase):
    @pytest.mark.run(order=17)
    def test_new_lot(self):
        lot = Lot("Biology", "Medium", 5000.00, numMachines=20)
        assert lot.labType == "Biology"

    @pytest.mark.run(order=18)
    def test_lot_lab_size(self):
        lot = Lot("Biology", "Medium", 5000.00, numMachines=20)
        assert lot.labSize == "Medium"
        assert lot.numMachines == 20

    @pytest.mark.run(order=19)
    def test_lot_budget(self):
        lot = Lot("Biology", "Medium", 5000.00, numMachines=20)
        assert lot.budget == 5000.00

    @pytest.mark.run(order=20)
    def test_lot_get_json(self):
        lot = Lot("Biology", "Medium", 5000.00, numMachines=20)
        lot_json = lot.get_json()
        self.assertDictEqual(lot_json, {
            "id": None,
            "name": None,
            "labType": "Biology",
            "labSize": "Medium",
            "numMachines": 20,
            "budget": 5000.00,
            "academic_year": 2025,
        })

    @pytest.mark.run(order=21)
    def test_lot_budget_comparison(self):
        lot = Lot("Biology", "Medium", 5000.00, numMachines=20)
        assert 4999.99 < lot.budget
        assert 5000.01 > lot.budget


class LotGroupUnitTests(unittest.TestCase):
    @pytest.mark.run(order=22)
    def test_new_lot_group(self):
        lot_group = LotGroup(1, 2)
        assert lot_group.lotID == 1
        assert lot_group.groupID == 2

    @pytest.mark.run(order=23)
    def test_lot_group_get_json(self):
        lot_group = LotGroup(1, 2)
        lg_json = lot_group.get_json()
        self.assertDictEqual(lg_json, {"lotID": 1, "groupID": 2})


class RFPUnitTests(unittest.TestCase):
    @pytest.mark.run(order=24)
    def test_new_RFP(self):
        rfp = RFP(1, 10)
        assert rfp
        assert rfp.groupID == 1
        assert rfp.lotID == 10

    @pytest.mark.run(order=25)
    def test_RFP_get_json(self):
        rfp = RFP(1, 10)
        assert rfp
        self.assertEqual(rfp.status, "draft")
        data = rfp.get_json()
        self.assertEqual(data['groupID'], 1)
        self.assertEqual(data['lotID'], 10)
        self.assertEqual(data['status'], "draft")


class BidUnitTests(unittest.TestCase):
    @pytest.mark.run(order=26)
    def test_new_bid(self):
        bid = Bid(1, 2, 3, b'fake pdf content', 'test.pdf', 14000.0)
        assert bid.lotID == 1
        assert bid.sourceGroupID == 2
        assert bid.recipientGroupID == 3

    @pytest.mark.run(order=27)
    def test_bid_document_link(self):
        bid = Bid(1, 2, 3, b'fake pdf content', 'test.pdf', 14000.0)
        assert bid.bidDocumentName == 'test.pdf'

    @pytest.mark.run(order=28)
    def test_bid_timestamp_auto_set(self):
        bid = Bid(1, 2, 3, b'fake pdf content', 'test.pdf', 14000.0)
        assert isinstance(bid.timestamp, datetime)

    @pytest.mark.run(order=29)
    def test_bid_timestamp_is_recent(self):
        bid = Bid(1, 2, 3, b'fake pdf content', 'test.pdf', 14000.0)
        delta = datetime.now() - bid.timestamp
        assert delta.seconds < 5

    @pytest.mark.run(order=30)
    def test_bid_get_json(self):
        bid = Bid(1, 2, 3, b'fake pdf content', 'test.pdf', 14000.0)
        bid_json = bid.get_json()
        assert bid_json["lotID"] == 1
        assert bid_json["sourceGroupID"] == 2
        assert bid_json["recipientGroupID"] == 3
        assert bid_json["bidDocumentName"] == 'test.pdf'
        assert "timestamp" in bid_json


class EvaluationUnitTests(unittest.TestCase):
    @pytest.mark.run(order=31)
    def test_new_evaluation(self):
        sourceGroupID = 1
        recipientGroupID = 2
        bidID = 2
        lotID = 1
        specsMet = 5
        presentation = 3
        professionalism = 2
        budget = 4

        evaluation = Evaluation(sourceGroupID, recipientGroupID, bidID, lotID, specsMet, presentation, professionalism, budget)
        assert evaluation
        assert evaluation.overallScore == 5.6

    @pytest.mark.run(order=32)
    def test_evaluation_get_json(self):
        sourceGroupID = 1
        recipientGroupID = 2
        bidID = 2
        lotID = 1
        specsMet = 5
        presentation = 3
        professionalism = 2
        budget = 4

        evaluation = Evaluation(sourceGroupID, recipientGroupID, bidID, lotID, specsMet, presentation, professionalism, budget)
        self.assertDictEqual({
            'id': None,
            'sourceGroupID': 1,
            'recipientGroupID': 2,
            'bidID': 2,
            'lotID': 1,
            'overallScore': 5.6
        }, evaluation.get_json())