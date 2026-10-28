import os
import uuid
from pathlib import Path
from werkzeug.utils import secure_filename
from flask import current_app, abort, send_from_directory
from flask_login import current_user
from app.extensions import db
from app.models.provider import ProviderDocument, ProviderProfile


class KYCService:
    """Service handling secure file validation, storage, and access control for provider documents."""

    @staticmethod
    def allowed_file(filename: str, content_type: str = None) -> bool:
        """Validates file extension against allowed whitelist."""
        if not filename or '.' not in filename:
            return False
        ext = filename.rsplit('.', 1)[1].lower()
        allowed_ext = current_app.config.get('ALLOWED_EXTENSIONS', {'pdf', 'png', 'jpg', 'jpeg'})
        if ext not in allowed_ext:
            return False
        if content_type:
            allowed_mime = current_app.config.get('ALLOWED_MIME_TYPES', {'application/pdf', 'image/png', 'image/jpeg'})
            if content_type.lower() not in allowed_mime:
                return False
        return True

    @staticmethod
    def save_provider_document(provider_profile: ProviderProfile, document_type: str, file_storage) -> ProviderDocument:
        """
        Validates, randomizes filename, stores document outside public static directory,
        and saves database metadata.
        """
        if not file_storage or not file_storage.filename:
            raise ValueError("No file uploaded.")

        filename = secure_filename(file_storage.filename)
        content_type = file_storage.content_type

        if not KYCService.allowed_file(filename, content_type):
            raise ValueError(f"Invalid file format: '{filename}'. Only PDF, PNG, JPG, and JPEG files are allowed.")

        # Check file size (max 5 MB)
        file_storage.seek(0, os.SEEK_END)
        file_size = file_storage.tell()
        file_storage.seek(0)
        
        max_size = current_app.config.get('MAX_CONTENT_LENGTH', 5 * 1024 * 1024)
        if file_size > max_size:
            raise ValueError(f"File size exceeds maximum allowed limit of {max_size // (1024 * 1024)} MB.")
        if file_size == 0:
            raise ValueError("Uploaded file is empty.")

        ext = filename.rsplit('.', 1)[1].lower()
        stored_filename = f"{uuid.uuid4().hex}_{document_type.lower()}.{ext}"

        docs_folder = current_app.config.get('DOCUMENTS_FOLDER')
        os.makedirs(docs_folder, exist_ok=True)
        dest_path = os.path.join(docs_folder, stored_filename)
        file_storage.save(dest_path)

        # Check if a document of this type already exists for the provider and replace it
        existing_doc = ProviderDocument.query.filter_by(
            provider_profile_id=provider_profile.id,
            document_type=document_type
        ).first()

        if existing_doc:
            old_file = os.path.join(docs_folder, existing_doc.stored_filename)
            if os.path.exists(old_file):
                try:
                    os.remove(old_file)
                except OSError:
                    pass
            existing_doc.original_filename = filename
            existing_doc.stored_filename = stored_filename
            existing_doc.mime_type = content_type
            existing_doc.file_size = file_size
            doc = existing_doc
        else:
            doc = ProviderDocument(
                provider_profile_id=provider_profile.id,
                document_type=document_type,
                original_filename=filename,
                stored_filename=stored_filename,
                mime_type=content_type,
                file_size=file_size
            )
            db.session.add(doc)

        # Reset verification status to PENDING whenever new documents are submitted
        provider_profile.verification_status = 'PENDING'
        provider_profile.rejection_reason = None
        db.session.commit()
        return doc

    @staticmethod
    def serve_document(document_id: int):
        """
        Serves an uploaded document ONLY to authorized callers:
        1. An Administrator.
        2. The Provider who owns the document.
        """
        doc = db.session.get(ProviderDocument, document_id)
        if not doc:
            abort(404)

        # Ownership and authorization enforcement
        is_owner = (current_user.is_authenticated and 
                    current_user.is_provider and 
                    current_user.provider_profile and 
                    current_user.provider_profile.id == doc.provider_profile_id)
        is_admin = (current_user.is_authenticated and current_user.is_admin)

        if not (is_owner or is_admin):
            abort(403)

        docs_folder = current_app.config.get('DOCUMENTS_FOLDER')
        file_path = os.path.join(docs_folder, doc.stored_filename)
        if not os.path.exists(file_path):
            abort(404)

        return send_from_directory(
            docs_folder,
            doc.stored_filename,
            mimetype=doc.mime_type,
            as_attachment=False,
            download_name=doc.original_filename
        )
