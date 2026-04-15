from constructs import Construct
from aws_cdk import (
    Stack,
    Duration,
    RemovalPolicy,
    CfnOutput,
    aws_ec2 as ec2,
    aws_ecs as ecs,
    aws_ecs_patterns as ecs_patterns,
    aws_logs as logs,
    aws_ecr as ecr,
)


class AbuelitoInfraStack(Stack):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        environment_name: str,
        **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        prefix = f"abuelito-{environment_name}"

        container_port = int(self.node.try_get_context("container_port") or 3000)
        repository_name = self.node.try_get_context("repository_name") or "abuelito-web"
        image_tag = self.node.try_get_context("image_tag") or "latest"

        # Configuración por ambiente
        if environment_name == "prod":
            cpu = 512
            memory_mib = 1024
            desired_count = 2
            log_retention = logs.RetentionDays.ONE_MONTH
            log_removal_policy = RemovalPolicy.RETAIN
        else:
            cpu = 256
            memory_mib = 512
            desired_count = 1
            log_retention = logs.RetentionDays.ONE_WEEK
            log_removal_policy = RemovalPolicy.DESTROY

        vpc = ec2.Vpc(
            self,
            f"{prefix}-vpc",
            max_azs=2,
            nat_gateways=0
        )

        cluster = ecs.Cluster(
            self,
            f"{prefix}-cluster",
            vpc=vpc
        )

        log_group = logs.LogGroup(
            self,
            f"{prefix}-log-group",
            retention=log_retention,
            removal_policy=log_removal_policy
        )

        repository = ecr.Repository.from_repository_name(
            self,
            f"{prefix}-ecr-repo",
            repository_name=repository_name
        )

        service = ecs_patterns.ApplicationLoadBalancedFargateService(
            self,
            f"{prefix}-service",
            cluster=cluster,
            public_load_balancer=True,
            desired_count=desired_count,
            cpu=cpu,
            memory_limit_mib=memory_mib,
            assign_public_ip=True,
            circuit_breaker=ecs.DeploymentCircuitBreaker(
                rollback=False
            ),
            min_healthy_percent=100,
            max_healthy_percent=200,
            task_image_options=ecs_patterns.ApplicationLoadBalancedTaskImageOptions(
                image=ecs.ContainerImage.from_ecr_repository(repository, tag=image_tag),
                container_port=container_port,
                enable_logging=True,
                log_driver=ecs.LogDrivers.aws_logs(
                    stream_prefix=prefix,
                    log_group=log_group
                )
            )
        )

        service.target_group.configure_health_check(
            path="/api/health",
            healthy_http_codes="200",
            interval=Duration.seconds(30),
            timeout=Duration.seconds(5),
            healthy_threshold_count=2,
            unhealthy_threshold_count=3
        )

        service.service.health_check_grace_period = Duration.seconds(60)
        service.service.enable_execute_command = True

        CfnOutput(
            self,
            f"{prefix}-load-balancer-url",
            value=f"http://{service.load_balancer.load_balancer_dns_name}"
        )

        CfnOutput(
            self,
            f"{prefix}-cluster-name-output",
            value=cluster.cluster_name
        )

        CfnOutput(
            self,
            f"{prefix}-service-name-output",
            value=service.service.service_name
        )