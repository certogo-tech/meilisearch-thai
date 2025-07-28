# Integration Guides

This section provides comprehensive guides for integrating Thai tokenization with existing systems and workflows.

## 🔄 Integration Scenarios

### Existing MeiliSearch Users
- **[Existing MeiliSearch Integration](existing-meilisearch-integration.md)** - Complete guide for adding Thai tokenization to your current MeiliSearch setup
- **Migration strategies and best practices**
- **Zero-downtime deployment options**
- **Performance comparison and validation**

### Application Integration
- **[REST API Integration](../api/index.md)** - Integrate via REST API calls
- **[SDK Integration](../development/sdks.md)** - Use official SDKs (coming soon)
- **[Webhook Integration](webhooks.md)** - Real-time document processing (coming soon)

### Platform Integration
- **[Docker Integration](../deployment/docker.md)** - Container-based deployment
- **[Kubernetes Integration](../deployment/k8s.md)** - Kubernetes deployment
- **[Cloud Integration](../deployment/cloud.md)** - AWS, GCP, Azure deployment

## 🏗️ Architecture Patterns

### Side-by-Side Deployment
```
Your App → Load Balancer → [Existing MeiliSearch | Thai Tokenizer + MeiliSearch]
```
- **Best for**: Gradual migration, A/B testing
- **Benefits**: Zero downtime, easy rollback
- **Guide**: [Existing MeiliSearch Integration](existing-meilisearch-integration.md#option-1-side-by-side-deployment-recommended)

### Preprocessing Pipeline
```
Your App → Thai Tokenizer → Document Processing → Existing MeiliSearch
```
- **Best for**: Minimal infrastructure changes
- **Benefits**: Use existing MeiliSearch instance
- **Guide**: [Existing MeiliSearch Integration](existing-meilisearch-integration.md#option-2-preprocessing-pipeline)

### Hybrid Integration
```
Your App → Smart Router → [Thai Content → Thai Tokenizer | Non-Thai → Existing MeiliSearch]
```
- **Best for**: Multi-language applications
- **Benefits**: Language-specific optimization
- **Guide**: [Existing MeiliSearch Integration](existing-meilisearch-integration.md#option-3-hybrid-integration)

## 📊 Migration Strategies

### Blue-Green Deployment
1. **Set up new environment** (Green)
2. **Migrate data** to green environment
3. **Test thoroughly** with production data
4. **Switch traffic** gradually
5. **Decommission old** environment (Blue)

### Canary Release
1. **Route small percentage** of traffic to new system
2. **Monitor performance** and accuracy
3. **Gradually increase** traffic percentage
4. **Full migration** when confident

### Feature Flag Approach
1. **Implement feature flags** in application
2. **Enable for specific users** or queries
3. **Monitor and validate** improvements
4. **Roll out to all users** gradually

## 🔧 Integration Tools

### Smart Router
```python
# Route requests based on content language
def route_request(query):
    if contains_thai(query):
        return route_to_thai_tokenizer(query)
    else:
        return route_to_existing_system(query)
```

### Data Migration Scripts
```python
# Migrate existing Thai content
migrator = ThaiContentMigrator(
    existing_url="http://localhost:7700",
    thai_tokenizer_url="http://localhost:8001"
)
migrated_count = migrator.migrate_documents(thai_docs)
```

### Performance Monitoring
```python
# Compare search performance
results = compare_search_performance(query)
print(f"Performance improvement: {results['improvement']:.2f}%")
```

## 📋 Integration Checklist

### Pre-Integration
- [ ] **Assess current setup** - Document existing MeiliSearch configuration
- [ ] **Identify Thai content** - Analyze data to find Thai text
- [ ] **Plan migration strategy** - Choose deployment approach
- [ ] **Set up monitoring** - Prepare performance tracking
- [ ] **Create backups** - Backup existing data and configuration

### During Integration
- [ ] **Deploy Thai tokenizer** - Set up new services
- [ ] **Configure routing** - Implement smart routing logic
- [ ] **Migrate data** - Transfer Thai content with tokenization
- [ ] **Test thoroughly** - Validate search quality and performance
- [ ] **Monitor metrics** - Track performance and errors

### Post-Integration
- [ ] **Validate improvements** - Measure search quality gains
- [ ] **Optimize performance** - Tune configuration for your use case
- [ ] **Update documentation** - Document new architecture
- [ ] **Train team** - Ensure team understands new system
- [ ] **Plan maintenance** - Set up ongoing monitoring and updates

## 🎯 Success Metrics

### Technical Metrics
- **Search Accuracy**: Improved compound word matching
- **Response Time**: Maintained or improved performance
- **Availability**: 99.9%+ uptime during migration
- **Error Rate**: <0.1% error rate

### Business Metrics
- **User Satisfaction**: Better search experience
- **Search Success Rate**: Higher percentage of successful searches
- **User Engagement**: Increased interaction with search results
- **Conversion Rate**: Better search leading to more actions

## 🆘 Troubleshooting

### Common Integration Issues
- **Port conflicts** - Ensure ports don't conflict with existing services
- **API key management** - Properly configure authentication
- **Data format differences** - Handle document structure changes
- **Performance degradation** - Monitor and optimize resource usage

### Support Resources
- **[Troubleshooting Guide](../troubleshooting.md)** - Common issues and solutions
- **[Performance Guide](../deployment/PERFORMANCE_OPTIMIZATIONS.md)** - Optimization tips
- **[Community Support](https://github.com/your-repo/discussions)** - Get help from community
- **[Professional Support](mailto:support@example.com)** - Enterprise support options

## 📚 Additional Resources

### Documentation
- **[API Reference](../api/index.md)** - Complete API documentation
- **[Configuration Guide](../../config/index.md)** - All configuration options
- **[Architecture Overview](../architecture/index.md)** - System design details

### Examples and Tools
- **[Code Examples](../examples.md)** - Ready-to-use integration code
- **[Demo Scripts](../../deployment/scripts/)** - Interactive demonstrations
- **[Test Suite](../../tests/)** - Comprehensive testing examples

### Community
- **[GitHub Discussions](https://github.com/your-repo/discussions)** - Community Q&A
- **[Issue Tracker](https://github.com/your-repo/issues)** - Bug reports and feature requests
- **[Contributing Guide](../development/README.md)** - How to contribute

---

**Ready to integrate?** Start with the [Existing MeiliSearch Integration](existing-meilisearch-integration.md) guide for the most comprehensive integration approach.