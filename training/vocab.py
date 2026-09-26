"""Vocabulary for synthetic CV generation (Vietnamese + English)."""

VN_FAMILY = ["Nguyễn"] * 8 + ["Trần"] * 3 + ["Lê"] * 3 + ["Phạm"] * 2 + [
    "Hoàng", "Huỳnh", "Phan", "Vũ", "Võ", "Đặng", "Bùi", "Đỗ", "Hồ", "Ngô", "Dương", "Lý",
    "Đinh", "Trịnh", "Đoàn", "Lâm", "Mai", "Trương", "Cao", "Tạ", "Lương", "Hà", "Quách",
]
VN_MIDDLE_M = ["Văn", "Hữu", "Đức", "Minh", "Quốc", "Thành", "Công", "Xuân", "Anh", "Hoàng", "Gia", "Trọng", "Duy", "Tuấn", "Ngọc"]
VN_MIDDLE_F = ["Thị", "Ngọc", "Thu", "Thanh", "Minh", "Hồng", "Phương", "Mai", "Bảo", "Khánh", "Kim", "Diệu", "Hoài"]
VN_GIVEN_M = ["An", "Bình", "Cường", "Dũng", "Đạt", "Hải", "Hiếu", "Hùng", "Huy", "Khang", "Khoa", "Long",
              "Minh", "Nam", "Nghĩa", "Phong", "Phúc", "Quân", "Sơn", "Tâm", "Thắng", "Thịnh", "Trung",
              "Tuấn", "Việt", "Vinh", "Quang", "Toàn", "Kiên", "Lâm", "Đông", "Hoàng"]
VN_GIVEN_F = ["Anh", "Chi", "Dung", "Giang", "Hà", "Hạnh", "Hằng", "Hoa", "Hương", "Lan", "Linh", "Loan",
              "Mai", "My", "Nga", "Ngân", "Nhung", "Oanh", "Phương", "Quyên", "Thảo", "Trang", "Trâm",
              "Uyên", "Vân", "Vy", "Yến", "Ngọc", "Thủy", "Tuyết", "Hiền"]

VN_CITIES = {
    "Hà Nội": ["Quận Ba Đình", "Quận Cầu Giấy", "Quận Đống Đa", "Quận Hai Bà Trưng", "Quận Hoàng Mai",
               "Quận Thanh Xuân", "Quận Long Biên", "Quận Nam Từ Liêm", "Quận Hà Đông", "Quận Tây Hồ"],
    "TP. Hồ Chí Minh": ["Quận 1", "Quận 3", "Quận 7", "Quận 10", "Quận Bình Thạnh", "Quận Phú Nhuận",
                        "Quận Tân Bình", "Quận Gò Vấp", "TP. Thủ Đức", "Quận Bình Tân"],
    "Đà Nẵng": ["Quận Hải Châu", "Quận Thanh Khê", "Quận Sơn Trà", "Quận Ngũ Hành Sơn", "Quận Liên Chiểu"],
    "Hải Phòng": ["Quận Lê Chân", "Quận Ngô Quyền", "Quận Hồng Bàng"],
    "Cần Thơ": ["Quận Ninh Kiều", "Quận Cái Răng"],
    "Bình Dương": ["TP. Thủ Dầu Một", "TP. Dĩ An", "TP. Thuận An"],
    "Đồng Nai": ["TP. Biên Hòa", "Huyện Long Thành"],
    "Khánh Hòa": ["TP. Nha Trang"],
    "Thừa Thiên Huế": ["TP. Huế"],
    "Nghệ An": ["TP. Vinh"],
    "Quảng Ninh": ["TP. Hạ Long"],
    "Bắc Ninh": ["TP. Bắc Ninh", "TP. Từ Sơn"],
}
VN_PROVINCES_BIRTH = list(VN_CITIES) + ["Thái Bình", "Nam Định", "Thanh Hóa", "Hà Tĩnh", "Quảng Nam",
                                        "Bình Định", "Long An", "Tiền Giang", "An Giang", "Hưng Yên"]
VN_STREETS = ["Nguyễn Trãi", "Lê Lợi", "Trần Hưng Đạo", "Hai Bà Trưng", "Lý Thường Kiệt", "Cầu Giấy",
              "Xuân Thủy", "Nguyễn Văn Linh", "Điện Biên Phủ", "Võ Văn Tần", "Lê Văn Sỹ", "Phạm Văn Đồng",
              "Hoàng Quốc Việt", "Nguyễn Chí Thanh", "Kim Mã", "Láng Hạ", "Tôn Đức Thắng", "Pasteur",
              "Nam Kỳ Khởi Nghĩa", "Cách Mạng Tháng Tám", "Nguyễn Thị Minh Khai", "Bạch Đằng"]
VN_WARDS = ["Phường Dịch Vọng", "Phường Láng Thượng", "Phường Bến Nghé", "Phường Tân Định", "Phường 12",
            "Phường Tân Phong", "Phường Thạc Gián", "Phường Mỹ An", "Phường Trung Hòa", "Phường 7"]

VN_COMPANIES = [
    "Công ty Cổ phần FPT", "FPT Software", "Tập đoàn Viettel", "Viettel Solutions", "VNG Corporation",
    "Tập đoàn Vingroup", "VinFast", "Ngân hàng TMCP Kỹ Thương Việt Nam (Techcombank)",
    "Ngân hàng TMCP Ngoại thương Việt Nam (Vietcombank)", "Ngân hàng TMCP Quân đội (MB Bank)",
    "Ngân hàng TMCP Á Châu (ACB)", "VPBank", "Công ty TNHH Samsung Electronics Việt Nam",
    "Công ty TNHH LG Electronics Việt Nam", "Tiki Corporation", "Công ty Cổ phần Thế Giới Di Động",
    "Công ty Cổ phần Sữa Việt Nam (Vinamilk)", "Masan Group", "Công ty TNHH Unilever Việt Nam",
    "Tổng Công ty Bưu điện Việt Nam", "Công ty Cổ phần Giao Hàng Tiết Kiệm", "MoMo (M_Service)",
    "Công ty TNHH KPMG Việt Nam", "Deloitte Việt Nam", "PwC Việt Nam", "Công ty CP Tập đoàn Hòa Phát",
    "Công ty TNHH Bosch Việt Nam", "NashTech Vietnam", "KMS Technology", "TMA Solutions",
    "Công ty Cổ phần Tập đoàn Masan", "Vietjet Air", "Vietnam Airlines", "Công ty TNHH Grab Việt Nam",
    "Shopee Việt Nam", "Lazada Việt Nam", "Công ty Cổ phần Bất động sản Novaland", "Sun Group",
    "Công ty TNHH Nestlé Việt Nam", "Công ty CP Dược Hậu Giang", "Bệnh viện Đa khoa Quốc tế Vinmec",
    "Trường THPT Chuyên Hà Nội - Amsterdam", "Khách sạn Sheraton Sài Gòn", "InterContinental Hanoi Westlake",
    "Công ty TNHH Logistics Gemadept", "Công ty CP Xây dựng Coteccons", "Công ty TNHH Hoàng Minh",
    "Công ty TNHH Thương mại Dịch vụ An Phát", "Công ty CP Công nghệ Sao Việt",
]
VN_UNIVERSITIES = [
    "Đại học Bách khoa Hà Nội", "Trường Đại học Bách khoa - ĐHQG TP.HCM", "Đại học Quốc gia Hà Nội",
    "Trường Đại học Kinh tế Quốc dân", "Trường Đại học Ngoại thương", "Trường Đại học Kinh tế TP.HCM",
    "Học viện Công nghệ Bưu chính Viễn thông", "Trường Đại học Công nghệ - ĐHQGHN",
    "Trường Đại học Khoa học Tự nhiên - ĐHQG TP.HCM", "Trường Đại học FPT", "Học viện Tài chính",
    "Học viện Ngân hàng", "Trường Đại học Thương mại", "Trường Đại học Sư phạm Hà Nội",
    "Trường Đại học Y Hà Nội", "Trường Đại học Đà Nẵng", "Trường Đại học Cần Thơ",
    "Trường Đại học Tôn Đức Thắng", "Trường Đại học RMIT Việt Nam", "Trường Đại học Luật Hà Nội",
    "Trường Đại học Xây dựng Hà Nội", "Trường Đại học Giao thông Vận tải", "Trường Đại học Hà Nội",
    "Trường Đại học Mở TP.HCM", "Trường Đại học Công nghiệp TP.HCM", "Trường Đại học Văn Lang",
    "Hanoi University of Science and Technology", "Foreign Trade University",
    "National Economics University", "University of Economics Ho Chi Minh City",
]
VN_COLLEGES = ["Trường Cao đẳng FPT Polytechnic", "Trường Cao đẳng Kinh tế Đối ngoại",
               "Trường Cao đẳng Du lịch Hà Nội", "Trường Cao đẳng Kỹ thuật Cao Thắng"]
VN_DEGREES = {
    "bachelor": ["Cử nhân", "Kỹ sư", "Cử nhân chính quy", "Bằng Cử nhân"],
    "master": ["Thạc sĩ", "Thạc sĩ Quản trị Kinh doanh (MBA)"],
    "phd": ["Tiến sĩ"],
    "college": ["Cao đẳng", "Cao đẳng chính quy"],
}
VN_GRADES = ["Giỏi", "Khá", "Xuất sắc", "Trung bình khá", "Loại Giỏi", "Loại Khá"]

EN_UNIVERSITIES = [
    "University of California, Berkeley", "University of Michigan", "Boston University",
    "National University of Singapore", "Nanyang Technological University", "University of Melbourne",
    "University of Toronto", "University of Manchester", "King's College London", "Monash University",
    "University of Texas at Austin", "Georgia Institute of Technology", "Arizona State University",
    "University of Washington", "Indian Institute of Technology Bombay", "University of Sydney",
    "RMIT University", "University of Leeds", "Pennsylvania State University", "Purdue University",
]
EN_DEGREES = {
    "bachelor": ["Bachelor of Science", "Bachelor of Arts", "B.S.", "B.A.", "Bachelor of Engineering",
                 "BBA", "Bachelor of Commerce"],
    "master": ["Master of Science", "MBA", "M.S.", "Master of Arts", "Master of Engineering"],
    "phd": ["Ph.D.", "Doctor of Philosophy"],
    "college": ["Associate Degree", "Diploma"],
}
EN_GRADES = ["3.8/4.0", "3.5/4.0", "3.62/4.0", "First Class Honours", "Magna Cum Laude", "Distinction",
             "Upper Second Class", "8.2/10", "3.2/4.0"]

LANGUAGES = {
    "vi": [("Tiếng Anh", ["IELTS 6.5", "IELTS 7.0", "TOEIC 750", "TOEIC 850", "Thành thạo", "Khá",
                          "Giao tiếp tốt", "Trung cấp", "Cao cấp", "B2", "C1"]),
           ("Tiếng Nhật", ["JLPT N2", "JLPT N3", "N4", "Cơ bản", "Trung cấp"]),
           ("Tiếng Hàn", ["TOPIK 4", "TOPIK 3", "Cơ bản", "Giao tiếp"]),
           ("Tiếng Trung", ["HSK 4", "HSK 5", "Cơ bản", "Khá"]),
           ("Tiếng Pháp", ["DELF B1", "Cơ bản"]),
           ("Tiếng Việt", ["Bản ngữ", "Tiếng mẹ đẻ"])],
    "en": [("English", ["Native", "Fluent", "Professional working proficiency", "IELTS 7.5", "C1",
                        "Business fluent", "Advanced"]),
           ("Vietnamese", ["Native", "Mother tongue"]),
           ("Japanese", ["JLPT N2", "Intermediate", "Basic", "Conversational"]),
           ("Korean", ["TOPIK 4", "Basic"]),
           ("Mandarin", ["HSK 5", "Conversational", "Intermediate"]),
           ("French", ["B1", "Intermediate", "Basic"]),
           ("Spanish", ["Conversational", "B2", "Elementary"]),
           ("German", ["A2", "B1", "Basic"])],
}

# domain -> dict with titles (en/vi), majors (en/vi), bullets (en/vi), certs, courses
DOMAINS = {
    "it": {
        "titles_en": ["Software Engineer", "Senior Software Engineer", "Backend Developer", "Frontend Developer",
                      "Full-stack Developer", "Data Engineer", "DevOps Engineer", "QA Engineer", "Tech Lead",
                      "Mobile Developer", "Data Analyst", "Solution Architect", "Intern Developer", "Project Manager"],
        "titles_vi": ["Lập trình viên", "Kỹ sư phần mềm", "Chuyên viên phân tích dữ liệu", "Trưởng nhóm kỹ thuật",
                      "Kỹ sư kiểm thử phần mềm", "Thực tập sinh lập trình", "Chuyên viên IT", "Quản trị hệ thống"],
        "majors_en": ["Computer Science", "Information Technology", "Software Engineering", "Data Science",
                      "Computer Engineering", "Information Systems"],
        "majors_vi": ["Công nghệ thông tin", "Khoa học máy tính", "Kỹ thuật phần mềm", "Hệ thống thông tin",
                      "Khoa học dữ liệu", "Mạng máy tính và truyền thông"],
        "bullets_en": ["Developed REST APIs with {tech} serving {n}K requests per day",
                       "Migrated legacy monolith to microservices on {cloud}",
                       "Reduced page load time by {p}% through caching and query optimization",
                       "Led a team of {k} engineers delivering {product}",
                       "Built CI/CD pipelines with GitLab CI and Docker",
                       "Designed database schema and optimized PostgreSQL queries",
                       "Wrote unit and integration tests, raising coverage to {p}%",
                       "Collaborated with product owners to define requirements for {product}"],
        "bullets_vi": ["Phát triển API cho hệ thống {product} sử dụng {tech}",
                       "Tối ưu truy vấn cơ sở dữ liệu, giảm {p}% thời gian phản hồi",
                       "Quản lý nhóm {k} lập trình viên",
                       "Xây dựng quy trình CI/CD với Jenkins và Docker",
                       "Phân tích yêu cầu và thiết kế hệ thống cho khách hàng Nhật Bản",
                       "Bảo trì và nâng cấp hệ thống {product}",
                       "Viết tài liệu kỹ thuật và hướng dẫn thành viên mới"],
        "certs": [("AWS Certified Solutions Architect – Associate", "Amazon Web Services"),
                  ("Certified Kubernetes Administrator (CKA)", "The Linux Foundation"),
                  ("Oracle Certified Professional, Java SE 11 Developer", "Oracle"),
                  ("Microsoft Certified: Azure Fundamentals", "Microsoft"),
                  ("Google Professional Data Engineer", "Google Cloud"),
                  ("ISTQB Certified Tester Foundation Level", "ISTQB"),
                  ("PMP", "PMI"), ("Scrum Master (PSM I)", "Scrum.org")],
        "courses": [("Machine Learning", "Coursera"), ("Docker & Kubernetes: The Practical Guide", "Udemy"),
                    ("Khóa học lập trình Java nâng cao", "FUNiX"), ("Data Engineering Bootcamp", "DataCamp")],
    },
    "finance": {
        "titles_en": ["Accountant", "Senior Accountant", "Financial Analyst", "Auditor", "Chief Accountant",
                      "Credit Analyst", "Relationship Manager", "Tax Consultant", "Finance Manager"],
        "titles_vi": ["Kế toán viên", "Kế toán tổng hợp", "Kế toán trưởng", "Chuyên viên phân tích tài chính",
                      "Kiểm toán viên", "Chuyên viên tín dụng", "Giao dịch viên", "Chuyên viên quan hệ khách hàng"],
        "majors_en": ["Accounting", "Finance", "Banking and Finance", "Economics", "Auditing"],
        "majors_vi": ["Kế toán", "Tài chính - Ngân hàng", "Kiểm toán", "Kinh tế", "Tài chính doanh nghiệp"],
        "bullets_en": ["Prepared monthly and quarterly financial statements under VAS and IFRS",
                       "Managed accounts payable and receivable for {n} clients",
                       "Performed audit engagements for manufacturing and retail clients",
                       "Built financial models to support {p}% cost reduction",
                       "Coordinated tax finalization and reporting with tax authorities"],
        "bullets_vi": ["Lập báo cáo tài chính tháng, quý, năm", "Theo dõi công nợ phải thu, phải trả",
                       "Kê khai và quyết toán thuế GTGT, TNDN, TNCN",
                       "Thẩm định hồ sơ vay vốn của khách hàng doanh nghiệp",
                       "Phát triển {n} khách hàng mới, đạt {p}% chỉ tiêu doanh số"],
        "certs": [("ACCA", "ACCA"), ("CPA Việt Nam", "Bộ Tài chính"), ("CFA Level II", "CFA Institute"),
                  ("Chứng chỉ Kế toán trưởng", "Bộ Tài chính"), ("CMA", "IMA")],
        "courses": [("IFRS Fundamentals", "ICAEW"), ("Excel for Financial Modeling", "Corporate Finance Institute"),
                    ("Khóa đào tạo Kế toán thực hành", "Trung tâm Lê Ánh")],
    },
    "sales": {
        "titles_en": ["Sales Executive", "Marketing Executive", "Digital Marketing Specialist", "Brand Manager",
                      "Account Manager", "Sales Manager", "Content Marketing Lead", "Business Development Manager"],
        "titles_vi": ["Nhân viên kinh doanh", "Chuyên viên marketing", "Trưởng phòng kinh doanh",
                      "Nhân viên chăm sóc khách hàng", "Chuyên viên truyền thông", "Giám sát bán hàng"],
        "majors_en": ["Marketing", "Business Administration", "International Business", "Communications"],
        "majors_vi": ["Marketing", "Quản trị kinh doanh", "Kinh doanh quốc tế", "Quan hệ công chúng"],
        "bullets_en": ["Achieved {p}% of annual sales target", "Managed a portfolio of {n} key accounts",
                       "Planned and executed digital campaigns on Facebook and Google Ads",
                       "Grew social media followers by {p}% in 6 months",
                       "Negotiated contracts with distributors across {k} provinces"],
        "bullets_vi": ["Tìm kiếm và phát triển khách hàng mới", "Đạt {p}% chỉ tiêu doanh số năm",
                       "Lập kế hoạch và triển khai chiến dịch marketing online",
                       "Quản lý fanpage và nội dung trên các kênh mạng xã hội",
                       "Chăm sóc {n} khách hàng doanh nghiệp"],
        "certs": [("Google Ads Certification", "Google"), ("HubSpot Content Marketing", "HubSpot"),
                  ("Facebook Blueprint", "Meta")],
        "courses": [("Kỹ năng bán hàng chuyên nghiệp", "PACE"), ("Digital Marketing", "Coursera")],
    },
    "hr": {
        "titles_en": ["HR Executive", "Recruitment Specialist", "HR Business Partner", "C&B Specialist",
                      "Talent Acquisition Lead", "HR Manager", "Training Specialist"],
        "titles_vi": ["Chuyên viên tuyển dụng", "Chuyên viên nhân sự", "Trưởng phòng hành chính nhân sự",
                      "Chuyên viên C&B", "Nhân viên hành chính"],
        "majors_en": ["Human Resource Management", "Business Administration", "Psychology"],
        "majors_vi": ["Quản trị nhân lực", "Quản trị kinh doanh", "Tâm lý học"],
        "bullets_en": ["Recruited {n} staff for technical and sales positions",
                       "Managed payroll and social insurance for {n} employees",
                       "Designed onboarding program reducing turnover by {p}%",
                       "Organized training plans and performance reviews"],
        "bullets_vi": ["Tuyển dụng {n} nhân sự cho các vị trí kỹ thuật và kinh doanh",
                       "Tính lương, bảo hiểm xã hội cho {n} nhân viên", "Xây dựng quy trình đánh giá KPI",
                       "Tổ chức các hoạt động gắn kết nhân viên"],
        "certs": [("SHRM-CP", "SHRM"), ("Chứng chỉ Quản trị nhân sự", "Đại học Kinh tế Quốc dân")],
        "courses": [("HR Analytics", "Coursera"), ("Luật lao động và BHXH", "Trung tâm đào tạo Nhân Việt")],
    },
    "engineering": {
        "titles_en": ["Civil Engineer", "Mechanical Engineer", "Electrical Engineer", "Site Engineer",
                      "Production Supervisor", "QA/QC Engineer", "Maintenance Engineer"],
        "titles_vi": ["Kỹ sư xây dựng", "Kỹ sư cơ khí", "Kỹ sư điện", "Giám sát công trình",
                      "Kỹ sư QA/QC", "Trưởng ca sản xuất", "Kỹ sư bảo trì"],
        "majors_en": ["Civil Engineering", "Mechanical Engineering", "Electrical Engineering", "Automation"],
        "majors_vi": ["Kỹ thuật xây dựng", "Kỹ thuật cơ khí", "Kỹ thuật điện", "Tự động hóa"],
        "bullets_en": ["Supervised construction of a {n}-floor residential building",
                       "Implemented 5S and Kaizen improving line efficiency by {p}%",
                       "Prepared shop drawings with AutoCAD and Revit",
                       "Managed maintenance schedule for {n} machines"],
        "bullets_vi": ["Giám sát thi công dự án chung cư {n} tầng", "Lập bản vẽ thi công bằng AutoCAD",
                       "Kiểm soát chất lượng vật tư đầu vào", "Bảo trì hệ thống điện nhà máy"],
        "certs": [("Chứng chỉ hành nghề giám sát xây dựng hạng II", "Bộ Xây dựng"), ("Six Sigma Green Belt", "ASQ"),
                  ("AutoCAD Certified Professional", "Autodesk")],
        "courses": [("Lean Manufacturing", "JICA"), ("An toàn lao động", "Sở LĐ-TB&XH")],
    },
    "hospitality": {
        "titles_en": ["Front Office Manager", "Guest Relations Officer", "Chef de Partie", "Restaurant Supervisor",
                      "Tour Guide", "Receptionist", "F&B Manager"],
        "titles_vi": ["Lễ tân khách sạn", "Nhân viên phục vụ", "Bếp trưởng", "Giám sát nhà hàng",
                      "Hướng dẫn viên du lịch", "Quản lý buồng phòng"],
        "majors_en": ["Hospitality Management", "Tourism Management", "Culinary Arts"],
        "majors_vi": ["Quản trị khách sạn", "Quản trị dịch vụ du lịch và lữ hành", "Kỹ thuật chế biến món ăn"],
        "bullets_en": ["Handled check-in/check-out for {n} rooms", "Maintained guest satisfaction score of 9.{k}/10",
                       "Trained {k} new front desk staff", "Managed daily F&B operations"],
        "bullets_vi": ["Đón tiếp và làm thủ tục nhận, trả phòng cho khách", "Xử lý phản hồi của khách hàng",
                       "Đào tạo {k} nhân viên mới", "Quản lý ca làm việc của bộ phận"],
        "certs": [("Chứng chỉ nghiệp vụ lễ tân", "VTOS"), ("Food Safety Level 2", "Highfield")],
        "courses": [("Hospitality Management", "Cornell eCornell")],
    },
    "healthcare": {
        "titles_en": ["Registered Nurse", "Pharmacist", "Medical Representative", "General Practitioner",
                      "Lab Technician"],
        "titles_vi": ["Điều dưỡng viên", "Dược sĩ", "Trình dược viên", "Bác sĩ đa khoa", "Kỹ thuật viên xét nghiệm"],
        "majors_en": ["Nursing", "Pharmacy", "Medicine", "Medical Laboratory Science"],
        "majors_vi": ["Điều dưỡng", "Dược học", "Y đa khoa", "Kỹ thuật xét nghiệm y học"],
        "bullets_en": ["Provided care for {n} patients per shift", "Administered medications and monitored vital signs",
                       "Managed pharmacy inventory worth {n}K USD"],
        "bullets_vi": ["Chăm sóc {n} bệnh nhân mỗi ca trực", "Tư vấn sử dụng thuốc cho bệnh nhân",
                       "Quản lý kho thuốc của khoa"],
        "certs": [("Chứng chỉ hành nghề Dược", "Sở Y tế"), ("BLS Provider", "American Heart Association")],
        "courses": [("Kiểm soát nhiễm khuẩn", "Bệnh viện Bạch Mai")],
    },
    "logistics": {
        "titles_en": ["Logistics Coordinator", "Supply Chain Analyst", "Purchasing Executive", "Warehouse Supervisor",
                      "Import-Export Specialist"],
        "titles_vi": ["Nhân viên xuất nhập khẩu", "Chuyên viên mua hàng", "Thủ kho", "Điều phối vận tải",
                      "Chuyên viên chuỗi cung ứng"],
        "majors_en": ["Logistics and Supply Chain Management", "International Trade"],
        "majors_vi": ["Logistics và Quản lý chuỗi cung ứng", "Kinh tế đối ngoại", "Ngoại thương"],
        "bullets_en": ["Coordinated {n} import shipments per month", "Negotiated freight rates saving {p}%",
                       "Managed warehouse of {n} SKUs"],
        "bullets_vi": ["Làm thủ tục hải quan cho hàng xuất nhập khẩu", "Theo dõi {n} lô hàng mỗi tháng",
                       "Quản lý xuất nhập tồn kho"],
        "certs": [("FIATA Diploma", "FIATA"), ("Chứng chỉ nghiệp vụ khai hải quan", "Tổng cục Hải quan")],
        "courses": [("Supply Chain Fundamentals", "MITx")],
    },
}

TECH = ["Java Spring Boot", "Python/Django", "Node.js", "Go", ".NET Core", "React", "Kotlin", "FastAPI"]
CLOUD = ["AWS", "Azure", "Google Cloud", "Kubernetes"]
PRODUCTS = ["e-commerce platform", "mobile banking app", "ERP system", "payment gateway", "CRM",
            "hệ thống quản lý kho", "ứng dụng đặt vé", "cổng thanh toán"]

AWARDS_VI = [("Nhân viên xuất sắc năm", None), ("Giải Nhất cuộc thi Hackathon", None),
             ("Học bổng khuyến khích học tập", None), ("Giấy khen của Tổng Giám đốc", None),
             ("Sinh viên 5 tốt cấp Thành phố", "Thành đoàn Hà Nội")]
AWARDS_EN = [("Employee of the Year", None), ("Best Innovation Award", None), ("Dean's List", None),
             ("Top Performer Q3", None), ("1st Prize, National Coding Contest", None)]

SKILLS = ["Microsoft Office", "Excel", "SQL", "Python", "Teamwork", "Communication", "Problem solving",
          "Tin học văn phòng", "Làm việc nhóm", "Giao tiếp", "Quản lý thời gian", "Photoshop", "SAP", "Power BI"]
HOBBIES = ["Đọc sách", "Du lịch", "Bóng đá", "Chạy bộ", "Reading", "Travelling", "Photography", "Chess", "Cooking"]

FAMILY_REL_VI = ["Bố", "Mẹ", "Vợ", "Chồng", "Anh trai", "Chị gái", "Em trai", "Em gái", "Con"]
OCCUPATIONS_VI = ["Giáo viên", "Kỹ sư", "Nội trợ", "Kinh doanh tự do", "Hưu trí", "Nhân viên văn phòng",
                  "Bác sĩ", "Học sinh", "Nông dân", "Công nhân"]
