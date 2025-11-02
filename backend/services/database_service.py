    async def create_appointment_type(self, appointment_type_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new appointment type"""
        try:
            appointment_type_data["created_at"] = datetime.now(timezone.utc)
            appointment_type_data["updated_at"] = datetime.now(timezone.utc)

            result = await self.appointments_collection.insert_one(appointment_type_data)
            created_type = await self.appointments_collection.find_one(
                {"_id": result.inserted_id}
            )

            created_type["_id"] = str(created_type["_id"])
            return created_type

        except Exception as e:
            self.logger.error(f"Error creating appointment type: {e}")
            raise

    async def get_appointment_types(self) -> List[Dict[str, Any]]:
        """Get all active appointment types"""
        try:
            cursor = self.appointments_collection.find({"is_active": True})
            types = []
            async for type_doc in cursor:
                type_doc["_id"] = str(type_doc["_id"])
                types.append(type_doc)
            return types

        except Exception as e:
            self.logger.error(f"Error retrieving appointment types: {e}")
            raise

    async def create_doctor(self, doctor_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new doctor"""
        try:
            doctor_data["created_at"] = datetime.now(timezone.utc)
            doctor_data["updated_at"] = datetime.now(timezone.utc)

            result = await self.appointments_collection.insert_one(doctor_data)
            created_doctor = await self.appointments_collection.find_one(
                {"_id": result.inserted_id}
            )

            created_doctor["_id"] = str(created_doctor["_id"])
            return created_doctor

        except Exception as e:
            self.logger.error(f"Error creating doctor: {e}")
            raise

    async def get_doctors(self) -> List[Dict[str, Any]]:
        """Get all active doctors"""
        try:
            cursor = self.appointments_collection.find({"is_active": True})
            doctors = []
            async for doctor in cursor:
                doctor["_id"] = str(doctor["_id"])
                doctors.append(doctor)
            return doctors

        except Exception as e:
            self.logger.error(f"Error retrieving doctors: {e}")
            raise

    async def update_clinic_info(self, clinic_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update clinic information"""
        try:
            clinic_data["updated_at"] = datetime.now(timezone.utc)

            # Upsert clinic info (assuming single clinic document)
            result = await self.appointments_collection.update_one(
                {"type": "clinic_info"},
                {"$set": clinic_data, "$setOnInsert": {"created_at": datetime.now(timezone.utc)}},
                upsert=True
            )

            # Retrieve updated clinic info
            clinic_info = await self.appointments_collection.find_one({"type": "clinic_info"})
            if clinic_info:
                clinic_info["_id"] = str(clinic_info["_id"])
            return clinic_info

        except Exception as e:
            self.logger.error(f"Error updating clinic info: {e}")
            raise

    async def get_clinic_info(self) -> Optional[Dict[str, Any]]:
        """Get clinic information"""
        try:
            clinic_info = await self.appointments_collection.find_one({"type": "clinic_info"})
            if clinic_info:
                clinic_info["_id"] = str(clinic_info["_id"])
            return clinic_info

        except Exception as e:
            self.logger.error(f"Error retrieving clinic info: {e}")
            raise