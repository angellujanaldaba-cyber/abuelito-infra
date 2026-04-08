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
    aws_ecr_assets as ecr_assets,
)

class AbuelitoInfraStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        app_path = self.node.try_get_context("app_path")
        container_port = int(self.node.try_get_context("container_port") or 3000)
        cpu = int(self.node.try_get_context("cpu") or 256)
        memory_mib = int(self.node.try_get_context("memory_mib") or 512)
        desired_count = int(self.node.try_get_context("desired_count") or 1)

        vpc = ec2.Vpc(
            self,
            "AbuelitoVpc",
            max_azs=2,
            nat_gateways=0
        )

        cluster = ecs.Cluster(
            self,
            "AbuelitoCluster",
            vpc=vpc
        )

        log_group = logs.LogGroup(
            self,
            "AbuelitoLogGroup",
            retention=logs.RetentionDays.ONE_WEEK,
            removal_policy=RemovalPolicy.DESTROY
        )

        image_asset = ecr_assets.DockerImageAsset(
            self,
            "AbuelitoDockerImage",
            directory=app_path
        )

        service = ecs_patterns.ApplicationLoadBalancedFargateService(
            self,
            "AbuelitoService",
            cluster=cluster,
            public_load_balancer=True,
            desired_count=desired_count,
            cpu=cpu,
            memory_limit_mib=memory_mib,
            assign_public_ip=True,
            runtime_platform=ecs.RuntimePlatform(
                cpu_architecture=ecs.CpuArchitecture.ARM64,
                operating_system_family=ecs.OperatingSystemFamily.LINUX
            ),
            task_image_options=ecs_patterns.ApplicationLoadBalancedTaskImageOptions(
                image=ecs.ContainerImage.from_docker_image_asset(image_asset),
                container_port=container_port,
                enable_logging=True,
                log_driver=ecs.LogDrivers.aws_logs(
                    stream_prefix="abuelito",
                    log_group=log_group
                )
            )
        )

        service.target_group.configure_health_check(
            path="/",
            healthy_http_codes="200-399",
            interval=Duration.seconds(30),
            timeout=Duration.seconds(5),
            healthy_threshold_count=2,
            unhealthy_threshold_count=3
        )

        service.service.health_check_grace_period = Duration.seconds(60)
        service.service.enable_execute_command = True

        CfnOutput(
            self,
            "LoadBalancerURL",
            value=f"http://{service.load_balancer.load_balancer_dns_name}"
        )