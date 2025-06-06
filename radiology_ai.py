import requests
import json
import re
from typing import List, Dict, Any
import time
from datetime import datetime

class RadiologyClinicalAI:
    def __init__(self):
        # API Keys
        self.tavily_api_key = "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"
        self.cohere_api_key = "BuMAz7ljs4KRZqT680W8zZVaIzFekAcGi3ECzHod"
        self.groq_api_key = "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"
        
        # API URLs
        self.tavily_url = "https://api.tavily.com/search"
        self.cohere_url = "https://api.cohere.ai/v1/generate"
        self.groq_url = "https://api.groq.com/openai/v1/chat/completions"
        
        # Priority search terms for guidelines
        self.priority_sources = [
            "NICE guidelines",
            "NHS England",
            "Royal College of Radiologists",
            "British Society",
            "European Society",
            "American College of Radiology",
            "Cochrane review",
            "systematic review",
            "meta-analysis",
            "clinical guidelines"
        ]

    def extract_key_findings(self, report_text: str) -> List[str]:
        """Extract key clinical findings from radiology report using Groq as backup"""
        # First try Cohere, if fails use Groq
        findings = self._extract_with_cohere(report_text)
        if not findings:
            print("Cohere failed, trying with Groq...")
            findings = self._extract_with_groq(report_text)
        
        return findings
    
    def _extract_with_cohere(self, report_text: str) -> List[str]:
        """Extract findings using Cohere API"""
        try:
            prompt = f"""Analyze this radiology report and extract key positive clinical findings that require management:

Report: {report_text}

List only significant findings as numbered points:"""

            headers = {
                'Authorization': f'Bearer {self.cohere_api_key}',
                'Content-Type': 'application/json'
            }

            data = {
                'model': 'command',
                'prompt': prompt,
                'max_tokens': 200,
                'temperature': 0.1
            }

            response = requests.post(self.cohere_url, headers=headers, json=data)
            
            if response.status_code == 200:
                result = response.json()
                findings_text = result['generations'][0]['text'].strip()
                return self._parse_findings(findings_text)
            else:
                print(f"Cohere API error: {response.status_code} - {response.text}")
                return []
                
        except Exception as e:
            print(f"Cohere error: {str(e)}")
            return []
    
    def _extract_with_groq(self, report_text: str) -> List[str]:
        """Extract findings using Groq API as backup"""
        try:
            prompt = f"""Analyze this radiology report and extract key positive clinical findings that require management or follow-up:

Report: {report_text}

Provide a numbered list of significant findings only:"""

            headers = {
                'Authorization': f'Bearer {self.groq_api_key}',
                'Content-Type': 'application/json'
            }

            data = {
                'model': 'deepseek-r1-distill-llama-70b',
                'messages': [
                    {
                        'role': 'user',
                        'content': prompt
                    }
                ],
                'max_tokens': 200,
                'temperature': 0.1
            }

            response = requests.post(self.groq_url, headers=headers, json=data)
            
            if response.status_code == 200:
                result = response.json()
                findings_text = result['choices'][0]['message']['content']
                return self._parse_findings(findings_text)
            else:
                print(f"Groq API error: {response.status_code}")
                # Fallback to manual extraction
                return self._manual_extraction(report_text)
                
        except Exception as e:
            print(f"Groq error: {str(e)}")
            return self._manual_extraction(report_text)
    
    def _parse_findings(self, findings_text: str) -> List[str]:
        """Parse AI response into list of findings"""
        findings = []
        lines = findings_text.split('\n')
        for line in lines:
            line = line.strip()
            if re.match(r'^\d+\.', line):
                finding = re.sub(r'^\d+\.\s*', '', line)
                if finding and len(finding) > 10:
                    findings.append(finding)
        return findings
    
    def _manual_extraction(self, report_text: str) -> List[str]:
        """Manual extraction as last resort"""
        print("Using manual extraction as fallback...")
        
        # Keywords that indicate significant findings
        significant_terms = [
            'tear', 'fracture', 'mass', 'lesion', 'stenosis', 'occlusion',
            'thrombus', 'embolism', 'hemorrhage', 'hematoma', 'abscess',
            'tumor', 'malignancy', 'metastasis', 'displacement', 'rupture',
            'perforation', 'obstruction', 'dilatation', 'effusion',
            'fluid collection', 'abnormal signal', 'enhancement', 'nodule'
        ]
        
        findings = []
        sentences = re.split(r'[.!?]', report_text.lower())
        
        for sentence in sentences:
            sentence = sentence.strip()
            if any(term in sentence for term in significant_terms):
                # Clean up and capitalize
                clean_sentence = sentence.strip().capitalize()
                if len(clean_sentence) > 15:
                    findings.append(clean_sentence)
        
        return findings[:5]  # Limit to 5 findings

    def search_clinical_evidence(self, finding: str) -> Dict[str, Any]:
        """Search for comprehensive clinical evidence using Tavily API"""
        try:
            # Create comprehensive search queries targeting multiple guideline sources
            queries = [
                # UK Guidelines
                f"{finding} NICE guidelines management",
                f"{finding} NHS England clinical guidelines",
                f"{finding} Royal College Radiologists RCR guidelines",
                f"{finding} SIGN Scottish guidelines",
                f"{finding} British Orthopaedic Association guidelines",
                f"{finding} British Society Skeletal Radiology guidelines",
                
                # European Guidelines
                f"{finding} European Society Radiology ESR guidelines",
                f"{finding} European League Against Rheumatism EULAR guidelines",
                f"{finding} European Society Musculoskeletal Radiology ESSR",
                f"{finding} European Orthopaedic Research Society guidelines",
                
                # American Guidelines
                f"{finding} American College Radiology ACR appropriateness criteria",
                f"{finding} American Academy Orthopaedic Surgeons AAOS guidelines",
                f"{finding} American Orthopaedic Society Sports Medicine guidelines",
                f"{finding} Radiological Society North America RSNA guidelines",
                
                # International/Evidence-based
                f"{finding} Cochrane systematic review",
                f"{finding} WHO World Health Organization guidelines",
                f"{finding} International Skeletal Society guidelines",
                f"{finding} consensus statement management",
                f"{finding} clinical practice guidelines",
                f"{finding} evidence based management systematic review"
            ]
            
            all_results = []
            
            for i, query in enumerate(queries):
                print(f"Searching query {i+1}/{len(queries)}: {query[:50]}...")
                
                headers = {
                    'Content-Type': 'application/json'
                }
                
                data = {
                    'api_key': self.tavily_api_key,
                    'query': query,
                    'search_depth': 'advanced',
                    'include_answer': True,
                    'include_raw_content': True,
                    'max_results': 8,
                    'include_domains': [
                        # UK Sources
                        'nice.org.uk',
                        'nhs.uk', 
                        'rcr.ac.uk',
                        'sign.ac.uk',
                        'boa.ac.uk',
                        'bssr.org.uk',
                        'nhsengland.nhs.uk',
                        'gov.uk',
                        
                        # European Sources
                        'myesr.org',
                        'eular.org',
                        'essr.org',
                        'esska.org',
                        'eurospine.org',
                        
                        # American Sources
                        'acr.org',
                        'aaos.org',
                        'aossm.org',
                        'rsna.org',
                        'ajronline.org',
                        
                        # International/Evidence Sources
                        'cochranelibrary.com',
                        'who.int',
                        'pubmed.ncbi.nlm.nih.gov',
                        'ncbi.nlm.nih.gov',
                        'bmj.com',
                        'thelancet.com',
                        'nejm.org',
                        'nature.com',
                        'springer.com',
                        'wiley.com',
                        'elsevier.com',
                        'journals.lww.com',
                        'academic.oup.com'
                    ]
                }
                
                try:
                    response = requests.post(self.tavily_url, headers=headers, json=data)
                    
                    if response.status_code == 200:
                        results = response.json()
                        if 'results' in results:
                            # Filter out duplicates by URL
                            new_results = []
                            existing_urls = {r.get('url', '') for r in all_results}
                            for result in results['results']:
                                if result.get('url', '') not in existing_urls:
                                    new_results.append(result)
                            all_results.extend(new_results)
                    else:
                        print(f"Search failed for query: {response.status_code}")
                        
                except Exception as query_error:
                    print(f"Error with query {i+1}: {str(query_error)}")
                    continue
                
                time.sleep(0.3)  # Rate limiting
            
            print(f"Total unique sources found: {len(all_results)}")
            
            # Prioritize results by source reliability
            prioritized_results = self.prioritize_sources(all_results)
            
            return {
                'finding': finding,
                'results': prioritized_results,
                'total_sources': len(prioritized_results)
            }
            
        except Exception as e:
            print(f"Error searching for {finding}: {str(e)}")
            return {'finding': finding, 'results': [], 'total_sources': 0}

    def prioritize_sources(self, results: List[Dict]) -> List[Dict]:
        """Prioritize search results based on source reliability and authority"""
        priority_domains = {
            # Tier 1: UK National Guidelines (Highest Priority)
            'nice.org.uk': 100,
            'nhs.uk': 95,
            'nhsengland.nhs.uk': 90,
            'sign.ac.uk': 85,  # Scottish Intercollegiate Guidelines Network
            'gov.uk': 80,
            
            # Tier 2: UK Professional Bodies
            'rcr.ac.uk': 75,  # Royal College of Radiologists
            'boa.ac.uk': 70,  # British Orthopaedic Association
            'bssr.org.uk': 65,  # British Society of Skeletal Radiology
            
            # Tier 3: European Guidelines
            'eular.org': 60,  # European League Against Rheumatism
            'myesr.org': 58,  # European Society of Radiology
            'essr.org': 55,   # European Society of Musculoskeletal Radiology
            'esska.org': 52,  # European Society of Sports, Knee & Arthroscopy
            'eurospine.org': 50,
            
            # Tier 4: American Guidelines
            'acr.org': 48,    # American College of Radiology
            'aaos.org': 45,   # American Academy of Orthopaedic Surgeons
            'aossm.org': 42,  # American Orthopaedic Society for Sports Medicine
            'rsna.org': 40,   # Radiological Society of North America
            'ajronline.org': 38,
            
            # Tier 5: International Evidence-Based Sources
            'cochranelibrary.com': 35,
            'who.int': 32,
            
            # Tier 6: High-Impact Journals
            'bmj.com': 30,
            'thelancet.com': 28,
            'nejm.org': 26,
            'nature.com': 24,
            
            # Tier 7: PubMed and Other Academic Sources
            'pubmed.ncbi.nlm.nih.gov': 20,
            'ncbi.nlm.nih.gov': 18,
            'academic.oup.com': 16,
            'springer.com': 14,
            'wiley.com': 12,
            'elsevier.com': 10,
            'journals.lww.com': 8
        }
        
        def get_priority(result):
            url = result.get('url', '').lower()
            for domain, priority in priority_domains.items():
                if domain in url:
                    return priority
            return 1
        
        # Sort by priority score, then by relevance score if available
        def sort_key(result):
            priority = get_priority(result)
            relevance = result.get('score', 0.5)  # Default relevance if not provided
            return (priority, relevance)
        
        return sorted(results, key=sort_key, reverse=True)

    def generate_recommendations(self, finding: str, search_results: List[Dict]) -> str:
        """Generate clinical recommendations using Groq"""
        try:
            # Prepare evidence summary
            evidence_text = ""
            for i, result in enumerate(search_results[:5]):  # Top 5 results
                evidence_text += f"\nSource {i+1}: {result.get('title', 'N/A')}\n"
                evidence_text += f"URL: {result.get('url', 'N/A')}\n"
                evidence_text += f"Content: {result.get('content', 'N/A')[:500]}...\n"
                evidence_text += "-" * 50 + "\n"

            prompt = f"""
            As an NHS consultant radiologist, provide evidence-based clinical recommendations for the following finding:

            FINDING: {finding}

            AVAILABLE EVIDENCE:
            {evidence_text}

            Please provide:
            1. IMMEDIATE MANAGEMENT (if urgent)
            2. INVESTIGATION RECOMMENDATIONS
            3. FOLLOW-UP REQUIREMENTS
            4. REFERRAL RECOMMENDATIONS
            5. PATIENT INFORMATION NEEDS

            For each recommendation, specify:
            - Strength of evidence (Strong/Moderate/Weak/Expert Opinion)
            - Time frame for action
            - Source of recommendation

            Format as clear, actionable clinical recommendations suitable for NHS practice.
            """

            headers = {
                'Authorization': f'Bearer {self.groq_api_key}',
                'Content-Type': 'application/json'
            }

            data = {
                'model': 'deepseek-r1-distill-llama-70b',
                'messages': [
                    {
                        'role': 'system',
                        'content': 'You are an expert NHS consultant radiologist providing evidence-based clinical recommendations.'
                    },
                    {
                        'role': 'user',
                        'content': prompt
                    }
                ],
                'max_tokens': 800,
                'temperature': 0.1
            }

            response = requests.post(self.groq_url, headers=headers, json=data)
            
            if response.status_code == 200:
                result = response.json()
                return result['choices'][0]['message']['content']
            else:
                print(f"Groq API error: {response.status_code}")
                return "Unable to generate recommendations due to API error."
                
        except Exception as e:
            print(f"Error generating recommendations: {str(e)}")
            return "Unable to generate recommendations due to system error."

    def format_evidence_strength(self, sources: List[Dict]) -> str:
        """Determine evidence strength based on source types and quality"""
        if not sources:
            return "INSUFFICIENT (No reliable sources found)"
        
        # Count different types of high-quality sources
        nice_count = sum(1 for s in sources if 'nice.org.uk' in s.get('url', '').lower())
        nhs_count = sum(1 for s in sources if any(domain in s.get('url', '').lower() 
                                                for domain in ['nhs.uk', 'nhsengland.nhs.uk']))
        uk_guidelines = sum(1 for s in sources if any(domain in s.get('url', '').lower() 
                                                    for domain in ['sign.ac.uk', 'rcr.ac.uk', 'boa.ac.uk']))
        
        cochrane_count = sum(1 for s in sources if 'cochrane' in s.get('url', '').lower())
        
        european_guidelines = sum(1 for s in sources if any(domain in s.get('url', '').lower() 
                                                          for domain in ['eular.org', 'myesr.org', 'essr.org']))
        
        american_guidelines = sum(1 for s in sources if any(domain in s.get('url', '').lower() 
                                                          for domain in ['acr.org', 'aaos.org', 'aossm.org']))
        
        systematic_review_count = sum(1 for s in sources if any(term in s.get('content', '').lower() 
                                                              for term in ['systematic review', 'meta-analysis', 'consensus statement']))
        
        high_impact_journals = sum(1 for s in sources if any(domain in s.get('url', '').lower() 
                                                           for domain in ['bmj.com', 'thelancet.com', 'nejm.org']))
        
        total_authoritative = nice_count + nhs_count + uk_guidelines + cochrane_count + european_guidelines + american_guidelines
        
        # Determine strength based on source quality and quantity
        if nice_count >= 2 or (nice_count >= 1 and nhs_count >= 1):
            return f"VERY STRONG (NICE Guidelines: {nice_count}, NHS: {nhs_count})"
        elif nice_count >= 1 or cochrane_count >= 1:
            return f"STRONG (NICE: {nice_count}, Cochrane: {cochrane_count})"
        elif total_authoritative >= 3:
            return f"STRONG (Multiple Guidelines: UK:{uk_guidelines}, EU:{european_guidelines}, US:{american_guidelines})"
        elif total_authoritative >= 2 or systematic_review_count >= 2:
            return f"MODERATE (Guidelines: {total_authoritative}, Systematic Reviews: {systematic_review_count})"
        elif total_authoritative >= 1 or high_impact_journals >= 2:
            return f"MODERATE (Authoritative Sources: {total_authoritative}, High-Impact Journals: {high_impact_journals})"
        elif len(sources) >= 5:
            return f"WEAK (Multiple Sources: {len(sources)}, but limited authoritative guidelines)"
        elif len(sources) >= 1:
            return f"WEAK (Limited Sources: {len(sources)})"
        else:
            return "INSUFFICIENT (No reliable sources found)"

    def generate_report(self, radiology_report: str) -> str:
        """Generate complete clinical analysis report"""
        print("🔍 Analyzing radiology report...")
        print("=" * 60)
        
        # Step 1: Extract key findings
        print("📋 Extracting key clinical findings...")
        findings = self.extract_key_findings(radiology_report)
        
        if not findings:
            return "No significant clinical findings requiring management identified."
        
        print(f"✅ Found {len(findings)} key clinical findings")
        
        # Step 2: Search for evidence for each finding
        all_evidence = []
        for i, finding in enumerate(findings, 1):
            print(f"🔬 Searching evidence for finding {i}/{len(findings)}: {finding[:50]}...")
            evidence = self.search_clinical_evidence(finding)
            all_evidence.append(evidence)
        
        # Step 3: Generate comprehensive report
        report = f"""
NHS RADIOLOGY REPORT CLINICAL ANALYSIS
Generated: {datetime.now().strftime('%d/%m/%Y %H:%M')}
{'=' * 60}

ORIGINAL REPORT SUMMARY:
{radiology_report[:300]}...

KEY CLINICAL FINDINGS IDENTIFIED: {len(findings)}
{'=' * 60}
"""
        
        for i, (finding, evidence) in enumerate(zip(findings, all_evidence), 1):
            print(f"📝 Generating recommendations for finding {i}...")
            
            recommendations = self.generate_recommendations(finding, evidence['results'])
            evidence_strength = self.format_evidence_strength(evidence['results'])
            
            report += f"""
FINDING {i}: {finding}
{'-' * 50}

EVIDENCE STRENGTH: {evidence_strength}
SOURCES FOUND: {evidence['total_sources']}

CLINICAL RECOMMENDATIONS:
{recommendations}

KEY EVIDENCE SOURCES:
"""
            
            # Add top 3 sources with links
            for j, source in enumerate(evidence['results'][:3], 1):
                report += f"""
{j}. {source.get('title', 'Unknown Title')}
   URL: {source.get('url', 'No URL available')}
   Source Type: {self.identify_source_type(source.get('url', ''))}
"""
            
            report += "\n" + "=" * 60 + "\n"
        
        report += f"""
SUMMARY:
- Total findings analyzed: {len(findings)}
- Evidence-based recommendations provided for each finding
- Sources prioritized: NICE > NHS > Royal Colleges > Cochrane > Peer-reviewed journals
- All recommendations based on current UK clinical guidelines where available

DISCLAIMER: This AI analysis is for clinical decision support only. 
Always use clinical judgment and consult colleagues when appropriate.
All recommendations should be considered within the full clinical context.
"""
        
        return report

    def identify_source_type(self, url: str) -> str:
        """Identify the type and authority level of clinical source"""
        url_lower = url.lower()
        
        # UK National Guidelines
        if 'nice.org.uk' in url_lower:
            return 'NICE Guideline (UK National)'
        elif 'nhs.uk' in url_lower or 'nhsengland.nhs.uk' in url_lower:
            return 'NHS Guidance (UK National)'
        elif 'sign.ac.uk' in url_lower:
            return 'SIGN Guideline (Scottish)'
        elif 'gov.uk' in url_lower:
            return 'UK Government Guidance'
            
        # UK Professional Bodies
        elif 'rcr.ac.uk' in url_lower:
            return 'Royal College of Radiologists (UK)'
        elif 'boa.ac.uk' in url_lower:
            return 'British Orthopaedic Association'
        elif 'bssr.org.uk' in url_lower:
            return 'British Society of Skeletal Radiology'
            
        # European Guidelines
        elif 'eular.org' in url_lower:
            return 'EULAR Guidelines (European)'
        elif 'myesr.org' in url_lower:
            return 'European Society of Radiology'
        elif 'essr.org' in url_lower:
            return 'European Society of MSK Radiology'
        elif 'esska.org' in url_lower:
            return 'European Society Sports/Knee/Arthroscopy'
            
        # American Guidelines
        elif 'acr.org' in url_lower:
            return 'American College of Radiology'
        elif 'aaos.org' in url_lower:
            return 'American Academy Orthopaedic Surgeons'
        elif 'aossm.org' in url_lower:
            return 'American Orthopaedic Society Sports Med'
        elif 'rsna.org' in url_lower:
            return 'Radiological Society North America'
            
        # International Evidence Sources
        elif 'cochrane' in url_lower:
            return 'Cochrane Systematic Review'
        elif 'who.int' in url_lower:
            return 'World Health Organization'
            
        # High-Impact Journals
        elif 'bmj.com' in url_lower:
            return 'British Medical Journal'
        elif 'thelancet.com' in url_lower:
            return 'The Lancet'
        elif 'nejm.org' in url_lower:
            return 'New England Journal of Medicine'
        elif 'nature.com' in url_lower:
            return 'Nature Journal'
            
        # Research Databases
        elif 'pubmed' in url_lower or 'ncbi.nlm.nih.gov' in url_lower:
            return 'PubMed Research Database'
        elif 'academic.oup.com' in url_lower:
            return 'Oxford Academic'
        elif 'springer.com' in url_lower:
            return 'Springer Academic'
        elif 'wiley.com' in url_lower:
            return 'Wiley Academic'
        elif 'elsevier.com' in url_lower:
            return 'Elsevier Academic'
            
        else:
            return 'Clinical Source'

def test_with_sample_report():
    """Test function with the knee MRI report"""
    sample_report = """There is horizontal tear of the medial meniscal posterior horn with displaced flap within the medial knee gutter. Heterogenous signal of the ACL, likely partial tear. Moderate medial tibiofemoral chondropathy, 1.5cm width, partial thickness. Small joint effusion. No other significant findings."""
    
    print("🧪 Testing with sample knee MRI report...")
    ai_system = RadiologyClinicalAI()
    
    # Test finding extraction
    print("Testing finding extraction...")
    findings = ai_system.extract_key_findings(sample_report)
    print(f"Found {len(findings)} findings:")
    for i, finding in enumerate(findings, 1):
        print(f"{i}. {finding}")
    
    if findings:
        # Test evidence search for first finding
        print(f"\nTesting evidence search for: {findings[0][:50]}...")
        evidence = ai_system.search_clinical_evidence(findings[0])
        print(f"Found {evidence['total_sources']} sources")
        
        if evidence['results']:
            print("Top source:", evidence['results'][0].get('title', 'No title'))
    
    return findings

def main():
    """Main function to run the radiology AI system"""
    print("🏥 NHS Radiology Report Clinical AI System")
    print("=" * 50)
    
    # Initialize the AI system
    ai_system = RadiologyClinicalAI()
    
    while True:
        print("\nOptions:")
        print("1. Analyze a new radiology report")
        print("2. Test with sample knee MRI report")
        print("3. Exit")
        
        choice = input("\nEnter your choice (1, 2, or 3): ").strip()
        
        if choice == '1':
            print("\n📄 Please enter your radiology report:")
            print("(Type your report and press Enter twice when finished)")
            
            report_lines = []
            empty_lines = 0
            
            while empty_lines < 2:
                line = input()
                if line.strip() == '':
                    empty_lines += 1
                else:
                    empty_lines = 0
                report_lines.append(line)
            
            radiology_report = '\n'.join(report_lines).strip()
            
            if len(radiology_report) < 50:
                print("⚠️  Report seems too short. Please provide a complete radiology report.")
                continue
            
            print("\n🔄 Processing your report... This may take a few minutes.")
            
            try:
                # Generate the clinical analysis
                analysis = ai_system.generate_report(radiology_report)
                
                print("\n" + "=" * 60)
                print("📊 CLINICAL ANALYSIS COMPLETE")
                print("=" * 60)
                
                # Display the analysis
                print(analysis)
                
                # Option to save to file
                save_choice = input("\n💾 Save this analysis to a file? (y/n): ").strip().lower()
                if save_choice == 'y':
                    filename = f"radiology_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
                    try:
                        with open(filename, 'w', encoding='utf-8') as f:
                            f.write(analysis)
                        print(f"✅ Analysis saved to {filename}")
                    except Exception as e:
                        print(f"❌ Error saving file: {str(e)}")
                
            except Exception as e:
                print(f"❌ Error processing report: {str(e)}")
                print("Please check your internet connection and API keys.")
        
        elif choice == '2':
            try:
                findings = test_with_sample_report()
                if findings:
                    proceed = input("\n▶️ Run full analysis on this sample? (y/n): ").strip().lower()
                    if proceed == 'y':
                        sample_report = """There is horizontal tear of the medial meniscal posterior horn with displaced flap within the medial knee gutter. Heterogenous signal of the ACL, likely partial tear. Moderate medial tibiofemoral chondropathy, 1.5cm width, partial thickness. Small joint effusion. No other significant findings."""
                        analysis = ai_system.generate_report(sample_report)
                        print("\n" + "=" * 60)
                        print("📊 SAMPLE ANALYSIS COMPLETE")
                        print("=" * 60)
                        print(analysis)
            except Exception as e:
                print(f"❌ Test failed: {str(e)}")
        
        elif choice == '3':
            print("👋 Thank you for using the NHS Radiology Clinical AI System!")
            break
        
        else:
            print("❌ Invalid choice. Please enter 1, 2, or 3.")

if __name__ == "__main__":
    main()