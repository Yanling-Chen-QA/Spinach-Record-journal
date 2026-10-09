from train_data import create_training_data
from searchr1_grpo import SearchR1GRPO
from searchr1_config import searchr1_config
config = searchr1_config()

def main():
    """主训练循环"""
    print("初始化 Search-R1 GRPO (Token-level) 训练器...")
    trainer = SearchR1GRPO()

    # 创建训练数据
    queries, ground_truths = create_training_data()

    print("开始训练...")
    num_epochs = config.num_epochs
    batch_size = config.batch_size
    save_interval = config.save_interval

    for epoch in range(num_epochs):
        epoch_loss = 0.0
        epoch_kl_div = 0.0
        epoch_avg_reward = 0.0
        batch_count = 0
        
        # 新增：按batch_size遍历批次
        for i in range(0, len(queries), batch_size):
            # 新增：截取当前批次的queries和ground_truths
            batch_queries = queries[i:i+batch_size]
            batch_ground_truths = ground_truths[i:i+batch_size]
            
            # 调整：传入批次数据而非全量数据
            metrics = trainer.train_step(batch_queries, batch_ground_truths)
            
            # 新增：累加批次指标
            epoch_loss += metrics['loss']
            epoch_kl_div += metrics['kl_div']
            epoch_avg_reward += metrics['avg_reward']
            batch_count += 1

        # 新增：计算epoch平均指标（避免单批次波动）
        avg_loss = epoch_loss / batch_count if batch_count > 0 else 0.0
        avg_kl = epoch_kl_div / batch_count if batch_count > 0 else 0.0
        avg_reward = epoch_avg_reward / batch_count if batch_count > 0 else 0.0

        print(f"\n{'=' * 80}")
        print(f"Epoch {epoch + 1}/{num_epochs}")
        print(f"{'=' * 80}")

        # 打印每个样本生成的 tokens
        trajectories = metrics.get("trajectories", [])
        for i, traj in enumerate(trajectories):
            print(f"\n[Sample {i + 1}] Query: {traj.query}")
            print(f"Generated Text: {traj.generated_text}")
            print(f"Final Answer: {traj.final_answer}")
            print(f"Reward: {traj.reward:.2f}")
            # print(f"Num Tokens: {len(traj.token_steps)}")

        # 打印训练指标（调整：使用epoch平均指标）
        print(f"\n{'─' * 80}")
        print(f"Training Metrics:")
        print(f"  Loss: {avg_loss:.4f}")
        print(f"  KL Div: {avg_kl:.4f}")
        print(f"  Avg Reward: {avg_reward:.4f}")
        print(f"  Avg Tokens: {metrics['avg_tokens']:.1f}")
        print(f"  Search Rate: {metrics['search_trajectories']:.2f}")
        print(f"  Beta: {metrics['beta']:.4f}")
        print(f"{'=' * 80}\n")

        if (epoch + 1) % save_interval == 0:
            save_dir = f"./output_model/epoch_{epoch + 1}"
            trainer.save_model(save_dir)
            print(f"\n第 {epoch + 1} 个epoch完成，模型保存到 {save_dir}")

    trainer.save_model("./output_model/final")
    print("\n训练全部完成，最终模型保存完成！")

if __name__ == "__main__":
    main()