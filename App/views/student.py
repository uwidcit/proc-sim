from flask import Blueprint, flash, request, redirect, render_template, url_for, send_file
import io
from sqlalchemy import and_
from functools import wraps
from flask_jwt_extended import jwt_required, current_user
from App.models import *
from App.controllers import *
from App.utils import format_timestamp, get_current_student_group, get_lot_owner_group_id, validate_pdf_upload


def student_required(f):
    @wraps(f)
    @jwt_required()
    def decorated_function(*args, **kwargs):
        if not current_user.is_student():
            flash("You are logged in as an admin and therefore cannot access student page", "failed")
            return redirect(url_for('index_views.index_page'))
        return f(*args, **kwargs)
    return decorated_function


def group_status_check(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        exists = check_studentGroup(current_user.id)

        if not exists:
            flash("You either have not created a group yet or your group has been reject or removed, create a new one", "info")
            return redirect(url_for('student_views.student_create_group_page'))

        group = get_group(exists.groupID)

        if group.status == "requested":
            flash("Your group has not been approved yet", "info")
            return redirect(url_for('student_views.student_group_details_page'))

        return f(*args, **kwargs)
    return decorated_function


student_views = Blueprint('student_views', __name__, template_folder='../templates')


@student_views.route('/student', methods=['GET'])
@student_required
def student_home_page():
    exists = check_studentGroup(current_user.id)
    if not exists:
        return redirect(url_for('student_views.student_create_group_page'))
    return redirect(url_for('student_views.student_group_details_page'))


@student_views.route('/student/create-group', methods=['GET', 'POST'])
@student_required
def student_create_group_page():
    exists = check_studentGroup(current_user.id)

    if exists:
        flash("You are already in a group", "failed")
        return redirect(url_for('student_views.student_group_details_page'))

    min_size, max_size = get_group_size_range()

    if request.method == 'POST':
        name = request.form.get('group_name')
        members = request.form.getlist('members')

        members.append(str(current_user.id))

        duplicates = []

        year = get_current_year()
        for member in members:
            existing = db.session.scalars(
                db.select(StudentGroup)
                .join(Group, Group.id == StudentGroup.groupID)
                .filter(
                    StudentGroup.studentID == int(member),
                    Group.academic_year == year,
                )
            ).first()

            if existing:
                duplicates.append(int(member))

        if duplicates:
            students = []
            you = False

            for ID in duplicates:
                if ID == current_user.id:
                    you = True
                    continue

                student = get_student(ID)

                if student:
                    students.append(student)

            if you:
                strings = []
                for student in students:
                    string = f"{student.name}, "
                    strings.append(string)

                if not strings:
                    flash("You are already in a group", "failed")
                    return redirect(url_for('student_views.student_create_group_page'))

                if len(strings) >= 2:
                    strings[-2] = f"{students[-2].name} and "
                    strings[-1] = f"{students[-1].name}"

                    flash(f"You are already in a group and {''.join(strings)} are already in groups", "failed")
                    return redirect(url_for('student_views.student_create_group_page'))
                else:
                    strings[0] = f"{students[0].name}"

                    flash(f"You are already in a group and {''.join(strings)} is already in a group", "failed")
                    return redirect(url_for('student_views.student_create_group_page'))
            else:
                strings = []
                for student in students:
                    string = f"{student.name}, "
                    strings.append(string)

                if len(strings) >= 2:
                    strings[-2] = f"{students[-2].name} and "
                    strings[-1] = f"{students[-1].name}"

                    flash(f"{''.join(strings)} are already in groups", "failed")
                    return redirect(url_for('student_views.student_create_group_page'))
                else:
                    strings[0] = f"{students[0].name}"

                    flash(f"{''.join(strings)} is already in a group", "failed")
                    return redirect(url_for('student_views.student_create_group_page'))

        if name == "":
            flash("You must enter a group name", "failed")
            return redirect(url_for('student_views.student_create_group_page'))

        if len(members) < min_size or len(members) > max_size:
            flash(
                f"Group size must be between {min_size} and {max_size} members (including you)",
                "failed",
            )
            return redirect(url_for('student_views.student_create_group_page'))

        group = create_group(name)

        for member in members:
            add_studentGroup(int(member), group.id)

        flash(f"Group '{name}' created successfully!", "success")
        return redirect(url_for('student_views.student_group_details_page'))

    taken_ids = students_in_groups_for_year()
    student_query = db.select(Student)
    if taken_ids:
        student_query = student_query.where(~Student.id.in_(taken_ids))
    students = db.session.scalars(student_query).all()

    candidates = []

    for student in students:
        if student.id == current_user.id:
            continue

        candidate = {}
        candidate["id"] = student.id
        candidate["name"] = student.name
        candidate["student_id"] = student.username
        candidate["selected"] = False

        candidates.append(candidate)

    return render_template(
        'student/create_group.html',
        active_page='create-group',
        title='Create Group',
        candidates=candidates,
        min_size=min_size,
        max_size=max_size,
        others_needed_min=max(0, min_size - 1),
        others_needed_max=max(0, max_size - 1),
    )


@student_views.route('/student/group-details', methods=['GET'])
@student_required
def student_group_details_page():
    exists = check_studentGroup(current_user.id)

    if not exists:
        flash("You either have not created a group yet or your group has been reject or removed, create a new one", "info")
        return redirect(url_for('student_views.student_create_group_page'))

    current_group = get_group(exists.groupID)

    if current_group.status == "requested":
        status = "Pending Confirmation"
    else:
        status = "Confirmed"

    members = db.session.scalars(
        db.select(Student)
        .join(StudentGroup, Student.id == StudentGroup.studentID)
        .filter(StudentGroup.groupID == current_group.id)
    ).all()

    return render_template(
        'student/group_details.html',
        active_page='group-details',
        title='Group Details',
        status=status,
        group=current_group,
        members=members
    )


@student_views.route('/student/lots', methods=['GET', 'POST'])
@student_required
@group_status_check
def student_lots_page():
    yourGroup = get_current_student_group(current_user.id)

    if request.method == 'POST':
        action = request.form.get('action')
        lot_id = int(request.form.get('lot_id'))

        ownership = db.session.scalars(
            db.select(LotGroup).filter_by(lotID=lot_id, groupID=yourGroup.id)
        ).first()
        if not ownership:
            flash("That lot is not assigned to your group", "failed")
            return redirect(url_for('student_views.student_lots_page'))

        specs = dict(
            deviceType=request.form.get('deviceType'),
            resolution=request.form.get('screen'),
            os=request.form.get('os'),
            cpu=request.form.get('cpu'),
            ram=request.form.get('ram'),
            drive=request.form.get('storage'),
            gpu=request.form.get('graphics'),
            peripherals=request.form.get('peripherals'),
            features=request.form.get('features'),
            io=request.form.get('io'),
        )

        # Keep lot catalog copy in sync for display convenience
        edit_lotRFP_details(id=lot_id, **specs)

        if action == 'submit':
            rfp, err = submit_rfp(yourGroup.id, lot_id, **specs)
            if err:
                flash(err, "info")
            else:
                flash(f"RFP for Lot {lot_id} has been submitted and is now visible in the gallery!", "success")
        else:
            rfp, err = save_rfp_draft(yourGroup.id, lot_id, **specs)
            if err:
                flash(err, "info")
            else:
                flash(f"Draft for Lot {lot_id} saved successfully.", "info")

        return redirect(url_for('student_views.student_lots_page', selected_lot=lot_id))

    entries = db.session.scalars(
        db.select(LotGroup).filter_by(groupID=yourGroup.id)
    ).all()

    lotIDs = sorted([entry.lotID for entry in entries])

    if not lotIDs:
        flash("Your group has no assigned lots yet", "info")
        return redirect(url_for('student_views.student_group_details_page'))

    selected_lot_id = request.args.get('selected_lot', str(lotIDs[0]))

    lots = db.session.scalars(
        db.select(Lot).where(Lot.id.in_(lotIDs))
    ).all()

    current_lot = next((lot for lot in lots if lot.id == int(selected_lot_id)), lots[0])

    existing_rfp = get_rfp(yourGroup.id, int(selected_lot_id))

    # Prefer RFP draft field values for the form when present
    if existing_rfp:
        for field in ('deviceType', 'resolution', 'os', 'cpu', 'ram', 'drive', 'gpu', 'peripherals', 'features', 'io'):
            val = getattr(existing_rfp, field, None)
            if val:
                setattr(current_lot, field, val)

    return render_template(
        'student/client_lots.html',
        active_page='lots',
        title='Assigned Lots & RFPs',
        lots=lots,
        current_lot=current_lot,
        existing_rfp=existing_rfp,
        rfp_locked=bool(existing_rfp and existing_rfp.status == 'submitted'),
    )


@student_views.route('/student/client-view-bids', methods=['GET'])
@student_required
@group_status_check
def student_view_bids_page():
    ASSIGNED_LOTS = []

    yourGroup = get_current_student_group(current_user.id)

    yourLots = db.session.scalars(
        db.select(Lot)
        .join(LotGroup, LotGroup.lotID == Lot.id)
        .filter(LotGroup.groupID == yourGroup.id)
        .order_by(Lot.id)
    ).all()

    if not yourLots:
        flash("Your group has no assigned lots yet", "info")
        return redirect(url_for('student_views.student_group_details_page'))

    for lot in yourLots:
        data = {
            "id": lot.id,
            "lab_type": lot.labType,
            "budget": lot.budget,
            "lab_size": lot.labSize,
            "num_machines": lot.numMachines,
            "description": f"{lot.labSize} · {lot.numMachines} machines",
        }
        ASSIGNED_LOTS.append(data)

    selected_lot_id = request.args.get('selected_lot', ASSIGNED_LOTS[0]["id"])
    current_lot_obj = get_lot(selected_lot_id)

    current_lot = {
        "id": current_lot_obj.id,
        "lab_type": current_lot_obj.labType,
        "budget": current_lot_obj.budget,
        "lab_size": current_lot_obj.labSize,
        "num_machines": current_lot_obj.numMachines,
        "description": f"{current_lot_obj.labSize} · {current_lot_obj.numMachines} machines",
    }

    bids_for_lot = []
    bidsReceived = db.session.scalars(
        db.select(Bid).filter(
            and_(Bid.lotID == current_lot["id"], Bid.recipientGroupID == yourGroup.id)
        )
    ).all()

    for bid in bidsReceived:
        sourceGroup = get_group(bid.sourceGroupID)
        bids_for_lot.append({
            "bid_id": bid.id,
            "lot_id": bid.lotID,
            "vendor_name": sourceGroup.groupName,
            "total_price": bid.quotationAmount,
            "timestamp": format_timestamp(bid.timestamp),
        })

    return render_template(
        'student/client_viewbid.html',
        active_page='view-bids',
        title='Received Bids',
        lots=ASSIGNED_LOTS,
        current_lot=current_lot,
        bids=bids_for_lot
    )


@student_views.route('/student/client-bid-details/<int:bid_id>', methods=['GET', 'POST'])
@student_required
@group_status_check
def student_bid_details_page(bid_id):
    technical_specs = [
        ('deviceType', 'Device Type'),
        ('resolution', 'Screen Size & Resolution'),
        ('os', 'Operating System(s)'),
        ('cpu', 'CPU'),
        ('ram', 'Memory (RAM)'),
        ('drive', 'Hard Drive'),
        ('gpu', 'Graphics'),
        ('peripherals', 'External Peripherals'),
        ('features', 'Features'),
        ('io', 'I/O')
    ]

    yourGroup = get_current_student_group(current_user.id)
    bidObj = get_bid(bid_id)

    if not bidObj or bidObj.recipientGroupID != yourGroup.id:
        flash("You do not have access to that bid", "failed")
        return redirect(url_for('student_views.student_view_bids_page'))

    sourceGroup = get_group(bidObj.sourceGroupID)
    bid = {
        "bid_id": bidObj.id,
        "lot_id": bidObj.lotID,
        "vendor_name": sourceGroup.groupName,
        "total_price": bidObj.quotationAmount,
        "timestamp": format_timestamp(bidObj.timestamp),
        "pdf": bidObj.bidDocument,
        "filename": bidObj.bidDocumentName,
    }

    lotObj = get_lot(bidObj.lotID)
    lot = {
        "id": lotObj.id,
        "lab_type": lotObj.labType,
        "budget": lotObj.budget,
        "description": f"{lotObj.labSize} · {lotObj.numMachines} machines",
    }

    if request.method == 'POST':
        specsMet = request.form.getlist("specs_selected")
        professionalism = int(request.form.get("professionalism_stars"))
        presentation = int(request.form.get("presentation_stars"))
        budget = int(request.form.get("budget_stars"))

        deviceType = request.form.get("comment_deviceType")
        resolution = request.form.get("comment_resolution")
        os = request.form.get("comment_os")
        cpu = request.form.get("comment_cpu")
        ram = request.form.get("comment_ram")
        drive = request.form.get("comment_drive")
        gpu = request.form.get("comment_gpu")
        peripherals = request.form.get("comment_peripherals")
        features = request.form.get("comment_features")
        io = request.form.get("comment_io")

        sourceGroupID = bidObj.recipientGroupID
        recipientGroupID = bidObj.sourceGroupID
        lotID = bidObj.lotID

        existing = db.session.scalars(
            db.select(Evaluation).filter_by(bidID=bid_id)
        ).first()

        if existing:
            edit_evaluation(
                existing.id, len(specsMet), presentation, professionalism, budget,
                deviceType=deviceType, resolution=resolution, os=os, cpu=cpu, ram=ram,
                drive=drive, gpu=gpu, peripherals=peripherals, features=features, io=io,
                specsSelected=','.join(specsMet),
            )
            flash("Evaluation updated successfully", "success")
            return redirect(url_for('student_views.student_bid_details_page', bid_id=bid_id))

        evaluation = create_evaluation(
            sourceGroupID, recipientGroupID, bid_id, lotID,
            len(specsMet), presentation, professionalism, budget,
        )
        edit_evaluation(
            evaluation.id, len(specsMet), presentation, professionalism, budget,
            deviceType=deviceType, resolution=resolution, os=os, cpu=cpu, ram=ram,
            drive=drive, gpu=gpu, peripherals=peripherals, features=features, io=io,
            specsSelected=','.join(specsMet),
        )

        flash("Evaluation created successfully", "success")
        return redirect(url_for('student_views.student_bid_details_page', bid_id=bid_id))

    existing = db.session.scalars(
        db.select(Evaluation).filter_by(bidID=bid_id)
    ).first()

    lot_bids = db.session.scalars(
        db.select(Bid)
        .filter_by(lotID=bidObj.lotID, recipientGroupID=yourGroup.id)
        .order_by(Bid.timestamp, Bid.id)
    ).all()

    lot_bid_nav = []
    for peer in lot_bids:
        vendor = get_group(peer.sourceGroupID)
        lot_bid_nav.append({
            "id": peer.id,
            "vendor_name": vendor.groupName if vendor else "—",
            "quotation": peer.quotationAmount,
            "filename": peer.bidDocumentName,
        })
    peer_index = next(
        (i for i, peer in enumerate(lot_bid_nav) if peer["id"] == bidObj.id),
        0,
    )
    total = len(lot_bid_nav)
    prev_bid_id = lot_bid_nav[(peer_index - 1) % total]["id"] if total > 1 else None
    next_bid_id = lot_bid_nav[(peer_index + 1) % total]["id"] if total > 1 else None

    return render_template(
        'student/client_bid_details.html',
        active_page='view-bids',
        title=f"Bid Analysis: {bid['vendor_name']}",
        bid=bid,
        lot=lot,
        technical_specs=technical_specs,
        existing=existing,
        lot_bid_nav=lot_bid_nav,
        peer_index=peer_index,
        prev_bid_id=prev_bid_id,
        next_bid_id=next_bid_id,
    )


@student_views.route('/student/client-evaluation', methods=['GET', 'POST'])
@student_required
@group_status_check
def student_client_evaluation_page():
    yourGroup = get_current_student_group(current_user.id)

    yourLots = db.session.scalars(
        db.select(Lot)
        .join(LotGroup, LotGroup.lotID == Lot.id)
        .filter(LotGroup.groupID == yourGroup.id)
        .order_by(Lot.id)
    ).all()

    if not yourLots:
        flash("Your group has no assigned lots yet", "info")
        return redirect(url_for('student_views.student_group_details_page'))

    selected_lot_id = request.args.get('selected_lot', yourLots[0].id)

    if request.method == "POST":
        evaluationID = int(request.form.get("evaluationID"))
        evaluation = get_evaluation(evaluationID)

        if not evaluation or evaluation.sourceGroupID != yourGroup.id:
            flash("You do not have access to that evaluation", "failed")
            return redirect(request.referrer or url_for('student_views.student_client_evaluation_page'))

        selected = db.session.scalars(
            db.select(Evaluation).filter(
                and_(
                    Evaluation.sourceGroupID == yourGroup.id,
                    Evaluation.lotID == selected_lot_id,
                    Evaluation.status == "selected",
                )
            )
        ).first()

        if selected:
            flash("You have already selected an evaluation for this lot. Your choice is permanent unless the admin removes the evaluation", "failed")
            return redirect(request.referrer)

        select_evaluation(evaluationID)
        flash("You have successfully selected an evaluation", "success")
        return redirect(request.referrer)

    filtered_evals = []
    yourEvaluations = db.session.scalars(
        db.select(Evaluation).filter(
            and_(Evaluation.sourceGroupID == yourGroup.id, Evaluation.lotID == selected_lot_id)
        )
    ).all()

    for evaluation in yourEvaluations:
        receipientGroup = get_group(evaluation.recipientGroupID)
        evaluatedBid = get_bid(evaluation.bidID)
        filtered_evals.append({
            "id": evaluation.id,
            "bid_id": evaluation.bidID,
            "lot_id": evaluation.lotID,
            "group_name": receipientGroup.groupName,
            "cost": evaluatedBid.quotationAmount,
            "specs_met": f"{evaluation.specsMet}/10",
            "rating": evaluation.overallScore,
            "is_selected": evaluation.status != "draft",
        })

    lots_list = [{"id": lot.id, "lab_type": lot.labType} for lot in yourLots]

    return render_template(
        'student/client_eval.html',
        active_page='client-evaluation',
        title='Bid Evaluations',
        evaluations=filtered_evals,
        lots=lots_list,
        selected_lot=selected_lot_id
    )


@student_views.route('/student/rfp-gallery', methods=['GET', 'POST'])
@student_required
@group_status_check
def rfp_gallery_page():
    yourGroup = get_current_student_group(current_user.id)

    if request.method == "POST":
        pdf = request.files.get('pdf')
        ok, err = validate_pdf_upload(pdf)
        if not ok:
            flash(err, "failed")
            return redirect(url_for('student_views.rfp_gallery_page'))

        lotID = int(request.form.get("lotID"))
        amount = float(request.form.get("amount"))

        owner_id = get_lot_owner_group_id(lotID)
        if not owner_id:
            flash("That lot has no owning group", "failed")
            return redirect(url_for('student_views.rfp_gallery_page'))

        if owner_id == yourGroup.id:
            lot = get_lot(lotID)
            flash(f"Lot {lotID} ({lot.labType}) is assigned to your group, you cannot place a bid on your own lot", "failed")
            return redirect(url_for('student_views.rfp_gallery_page'))

        rfp = get_rfp(owner_id, lotID)
        if not rfp or rfp.status != "submitted":
            flash("That RFP is not available for bidding", "failed")
            return redirect(url_for('student_views.rfp_gallery_page'))

        duplicate = db.session.scalars(
            db.select(Bid).filter(
                and_(Bid.lotID == lotID, Bid.sourceGroupID == yourGroup.id)
            )
        ).first()

        if duplicate:
            lot = get_lot(lotID)
            flash(f"You have already placed a bid on Lot {lotID} ({lot.labType}), you can only place 1 bid on each lot", "failed")
            return redirect(url_for('student_views.rfp_gallery_page'))

        lot = get_lot(lotID)
        create_bid(lotID, yourGroup.id, owner_id, pdf.read(), pdf.filename, amount)
        flash(f"Bid successfully placed on Lot {lotID} ({lot.labType})", "success")
        return redirect(url_for('student_views.rfp_gallery_page'))

    your_lot_ids = {
        e.lotID for e in db.session.scalars(
            db.select(LotGroup).filter_by(groupID=yourGroup.id)
        ).all()
    }

    year = get_current_year()
    rfp_gallery = db.session.scalars(
        db.select(RFP)
        .join(Lot, Lot.id == RFP.lotID)
        .filter(Lot.academic_year == year, RFP.status == "submitted")
    ).all()

    available_rfps = []
    for rfp in rfp_gallery:
        if rfp.lotID in your_lot_ids or rfp.groupID == yourGroup.id:
            continue

        lot = get_lot(rfp.lotID)
        group = get_group(rfp.groupID)
        available_rfps.append({
            "groupID": rfp.groupID,
            "lotID": rfp.lotID,
            "title": lot.labType,
            "client": group.groupName,
            "timestamp": format_timestamp(rfp.timestamp),
            "status": rfp.status,
            "description": f"{lot.labSize} · {lot.numMachines} machines",
            "deviceType": rfp.deviceType,
            "resolution": rfp.resolution,
            "os": rfp.os,
            "cpu": rfp.cpu,
            "ram": rfp.ram,
            "drive": rfp.drive,
            "gpu": rfp.gpu,
            "io": rfp.io,
            "peripherals": rfp.peripherals,
            "features": rfp.features,
        })

    return render_template(
        'student/vendor_rfp_gallery.html',
        title='RFP Gallery',
        active_page='rfp-gallery',
        rfps=available_rfps,
        sourceGroupID=yourGroup.id
    )


@student_views.route('/student/vendor-bids', methods=['GET'])
@student_required
@group_status_check
def submitted_bids_page():
    submitted_bids = []
    accepted = 0
    pending = 0
    rejected = 0

    yourGroup = get_current_student_group(current_user.id)

    yourBids = db.session.scalars(
        db.select(Bid).filter_by(sourceGroupID=yourGroup.id)
    ).all()

    for bid in yourBids:
        lot = get_lot(bid.lotID)
        group = get_group(bid.recipientGroupID)
        data = {
            "bid_id": bid.id,
            "rfp_title": lot.labType,
            "target_group": group.groupName,
            "submitted_at": bid.timestamp,
            "bidDocument": bid.bidDocument,
            "bidDocumentName": bid.bidDocumentName,
        }

        selected = db.session.scalars(
            db.select(Evaluation).filter(
                Evaluation.lotID == bid.lotID, Evaluation.status == "selected"
            )
        ).first()

        if selected:
            if selected.bidID == bid.id:
                data["status"] = "Accepted"
                accepted += 1
            else:
                data["status"] = "Rejected"
                rejected += 1
        else:
            data["status"] = "Pending"
            pending += 1

        submitted_bids.append(data)

    return render_template(
        'student/vendor_bids.html',
        active_page='vendor-bids',
        bids=submitted_bids,
        title='My Submitted Bids',
        accepted=accepted,
        pending=pending,
        rejected=rejected
    )


@student_views.route('/student/bid-document/<int:bid_id>')
@student_required
def serve_bid_document(bid_id):
    yourGroup = get_current_student_group(current_user.id)
    bid = get_bid(bid_id)
    if not bid:
        return "Not found", 404
    if not yourGroup or (
        bid.recipientGroupID != yourGroup.id and bid.sourceGroupID != yourGroup.id
    ):
        flash("You do not have access to that document", "failed")
        return redirect(url_for('student_views.student_home_page'))
    return send_file(
        io.BytesIO(bid.bidDocument),
        mimetype='application/pdf',
        download_name=bid.bidDocumentName
    )
