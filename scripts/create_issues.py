import json
import time
import urllib.request
import urllib.error

TOKEN = "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"
REPO = "ttj-ishida/KabuSys"
API = f"https://api.github.com/repos/{REPO}/issues"

HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json",
    "Accept": "application/vnd.github+json",
}

issues = [
    # Phase 1: Data Platform
    {
        "title": "【Phase 1】J-Quants APIクライアント実装",
        "labels": ["enhancement", "data-integration", "phase-1"],
        "body": """## 概要
`src/data/jquants_client.py` を実装し、J-Quants APIからの株価・財務・ニュースデータ取得を実現する。

## タスク
- [ ] 株価日足データ(OHLCV)の取得
- [ ] 財務データ(四半期BS/PL)の取得
- [ ] JPXカレンダー(祝日・半日・SQ)の取得
- [ ] APIレート制限(120req/min)の厳守とリトライロジック

## 関連ドキュメント
- `documents/01_Data/DataPlatform.md`
- `documents/01_Data/DataSchema.md`""",
    },
    {
        "title": "【Phase 1】データ取得・ETLパイプライン実装",
        "labels": ["enhancement", "data-integration", "phase-1"],
        "body": """## 概要
`src/data/data_loader.py` を実装し、Raw/Processed層のETLを実現する。

## タスク
- [ ] データ取得スケジューリング(差分更新)
- [ ] 欠損補完・重複除去
- [ ] 日付整形・銘柄コード統一
- [ ] Idempotency(冪等性)チェック

## 関連ドキュメント
- `documents/01_Data/DataPlatform.md` Section 4, 5, 6""",
    },
    {
        "title": "【Phase 1】ニュース収集・スクレイピング実装",
        "labels": ["enhancement", "data-integration", "phase-1"],
        "body": """## 概要
`src/data/news_collector.py` を実装し、外部ニュースソースからの記事収集を実現する。

## タスク
- [ ] RSS/Web APIの定期取得
- [ ] テキスト前処理(言語判定、リンク除去)
- [ ] データベース保存(重複チェック含む)

## 関連ドキュメント
- `documents/01_Data/DataPlatform.md` Section 3.1""",
    },
    {
        "title": "【Phase 1】マーケットカレンダー管理実装",
        "labels": ["enhancement", "data-integration", "phase-1"],
        "body": """## 概要
JPXカレンダー(祝日・半日取引・SQ日)の管理機能を実装する。

## タスク
- [ ] `calendar_update_job` による夜間バッチ更新
- [ ] `market_calendar` テーブル管理
- [ ] 営業日判定ロジック

## 関連ドキュメント
- `documents/01_Data/DataPlatform.md` Section 4.2""",
    },
    {
        "title": "【Phase 1】DuckDB/Parquetスキーマ設計と初期化",
        "labels": ["infrastructure", "database", "phase-1"],
        "body": """## 概要
DuckDB + Parquetを用いたデータベース構造を構築する。

## タスク
- [ ] Raw層テーブル定義: `raw_prices`, `raw_financials`, `raw_news`, `raw_executions`
- [ ] Processed層テーブル定義: `prices_daily`, `financials_clean`, `news_clean`
- [ ] Feature層テーブル定義: `feature_snapshot`, `ai_scores`
- [ ] Primary Key・Unique Constraintの設定

## 関連ドキュメント
- `documents/01_Data/DataSchema.md`""",
    },
    {
        "title": "【Phase 1】トレーサビリティ・監査ログテーブル構築",
        "labels": ["infrastructure", "database", "phase-1"],
        "body": """## 概要
Look-ahead Bias防止とシグナル追跡のための監査ログ構造を実装する。

## タスク
- [ ] `signal_events`: シグナル生成ログ
- [ ] `order_requests`: 発注要求ログ(冪等キー付き)
- [ ] `executions`: 約定ログ
- [ ] UUID連鎖によるトレーサビリティ確保

## 関連ドキュメント
- `documents/01_Data/DataPlatform.md` Section 8""",
    },
    {
        "title": "【Phase 1】データ品質チェック機能実装",
        "labels": ["testing", "data-quality", "phase-1"],
        "body": """## 概要
データ取得後の品質管理を実装する。

## タスク
- [ ] 欠損データ検出
- [ ] 異常値検出(スパイク判定)
- [ ] 重複チェック
- [ ] 日付不整合検出

## 関連ドキュメント
- `documents/01_Data/DataPlatform.md` Section 9""",
    },
    {
        "title": "【Phase 1】データパイプラインの単体テスト実装",
        "labels": ["testing", "phase-1"],
        "body": """## 概要
`tests/test_data_pipeline.py` を実装し、データパイプラインを検証する。

## タスク
- [ ] J-Quants APIクライアントのモック
- [ ] ETL処理の冪等性確認
- [ ] スキーマ整合性チェック""",
    },
    # Phase 2: Research Environment
    {
        "title": "【Phase 2】Jupyter Notebook研究環境のセットアップ",
        "labels": ["enhancement", "research", "phase-2"],
        "body": """## 概要
`notebooks/` 配下に研究用Jupyter Notebookテンプレートを作成する。

## タスク
- [ ] `research_factor.ipynb`: ファクター分析
- [ ] `data_analysis.ipynb`: 市場データ探索
- [ ] `backtest_experiment.ipynb`: バックテスト実験管理

## 関連ドキュメント
- `documents/07_Research/ResearchEnvironment.md`""",
    },
    {
        "title": "【Phase 2】ファクター探索ユーティリティ実装",
        "labels": ["enhancement", "research", "phase-2"],
        "body": """## 概要
`src/research/factor_research.py` と `feature_exploration.py` を実装する。

## タスク
- [ ] 基本ファクター計算(モメンタム、ボラティリティ等)
- [ ] 相関分析・統計検定
- [ ] ファクター効果の可視化

## 関連ドキュメント
- `documents/02_Strategy/StrategyModel.md` Section 3""",
    },
    {
        "title": "【Phase 2】Research環境の分離テスト",
        "labels": ["testing", "research", "phase-2"],
        "body": """## 概要
Research環境が実取引APIにアクセスしないことを検証する。

## タスク
- [ ] 実取引禁止フラグの確認
- [ ] 本番データベースアクセス遮断
- [ ] テストDB分離""",
    },
    # Phase 3: Strategy Engine
    {
        "title": "【Phase 3】Universe定義・銘柄フィルタリング実装",
        "labels": ["enhancement", "strategy", "phase-3"],
        "body": """## 概要
`src/strategy/universe_manager.py` を実装し、投資ユニバースの構築を実現する。

## タスク
- [ ] 市場フィルタ(プライム・スタンダード限定)
- [ ] 流動性フィルタ(最低売買代金5億円、最低株価300円)
- [ ] データ品質フィルタ(過去250営業日データ存在)
- [ ] セクター情報管理・企業名マッピング
- [ ] ユニバース更新(月次推奨)

## 関連ドキュメント
- `documents/02_Strategy/UniverseDefinition.md`""",
    },
    {
        "title": "【Phase 3】特徴量生成エンジン実装",
        "labels": ["enhancement", "strategy", "phase-3"],
        "body": """## 概要
`src/strategy/feature_engineering.py` を実装し、以下の特徴量を計算する。

## タスク
- [ ] モメンタム: 1ヶ月・3ヶ月・6ヶ月リターン、200日移動平均乖離率
- [ ] バリュー: PER, PBR, 配当利回り
- [ ] ボラティリティ: 20日ATR, 出来高変化率
- [ ] 正規化・Zスコア化処理
- [ ] バックテスト・本番で同じロジック使用

## 関連ドキュメント
- `documents/02_Strategy/StrategyModel.md` Section 3""",
    },
    {
        "title": "【Phase 3】売買シグナル生成ロジック実装",
        "labels": ["enhancement", "strategy", "phase-3"],
        "body": """## 概要
`src/strategy/signal_generator.py` を実装し、シグナル生成を実現する。

## タスク
- [ ] 複合ファクタースコア統合(Momentum 40%, Value 20%, Vol 15%, Liquidity 15%, News 10%)
- [ ] AI調整スコア統合(最大影響度10%制限)
- [ ] レジームフィルタ(Bear時は買いエントリー遮断)
- [ ] Entry条件: スコア閾値超過、市場リジーム確認
- [ ] Exit条件: ストップロス(-8%またはATR×2), トレーリングストップ(-10%), 時間決済(60営業日)
- [ ] Signal Queueへの書き込み(Pull型実行用)

## 関連ドキュメント
- `documents/02_Strategy/StrategyModel.md`""",
    },
    {
        "title": "【Phase 3】市場レジーム判定エンジン実装",
        "labels": ["enhancement", "strategy", "phase-3"],
        "body": """## 概要
`src/strategy/regime_detector.py` を実装し、市場レジーム(Bull/Neutral/Bear)を判定する。

## タスク
- [ ] テクニカル指標ベースのレジーム判定(TOPIX 200日移動平均等)
- [ ] AIモデルによるレジーム補正(最大影響度10%)
- [ ] レジーム別の戦略パラメータ切替

## 関連ドキュメント
- `documents/03_AI_Model/AIModel.md`
- `documents/02_Strategy/StrategyModel.md` Section 5""",
    },
    {
        "title": "【Phase 3】ニュースNLPスコアリングエンジン実装 [CRITICAL]",
        "labels": ["enhancement", "ai", "phase-3", "critical"],
        "body": """## 概要
`src/ai/news_nlp.py` を実装し、ニュース記事のセンチメント分析を行う。

## タスク
- [ ] 日本語NLPモデルの選定・統合
- [ ] 銘柄名・ティッカー紐付け
- [ ] センチメントスコア算出(+1.0〜-1.0)
- [ ] AIスコアの影響度上限(全体の10%)適用

## 注意事項
> **CLAUDE.mdアーキテクチャ制約 #2**: AIやLLMはあくまでセンチメント分析などのスコア生成に留め、最終的な取引判断は`Strategy`層を経由し、ルールベースにマッピングされた上で執行されること。

## 関連ドキュメント
- `documents/03_AI_Model/AIModel.md`""",
    },
    {
        "title": "【Phase 3】特徴量計算ロジックの単体テスト",
        "labels": ["testing", "strategy", "phase-3"],
        "body": """## 概要
`tests/test_feature_engineering.py` を実装する。

## タスク
- [ ] モメンタム計算の正確性
- [ ] 正規化処理の確認
- [ ] エッジケース(上場直後銘柄等)への対応""",
    },
    {
        "title": "【Phase 3】シグナル生成ロジックの単体テスト",
        "labels": ["testing", "strategy", "phase-3"],
        "body": """## 概要
`tests/test_signal_generator.py` を実装する。

## タスク
- [ ] スコア統合計算の検証
- [ ] レジームフィルタの動作確認
- [ ] Entry/Exit条件の正確性""",
    },
    # Phase 4: Backtest
    {
        "title": "【Phase 4】バックテストエンジンの実装",
        "labels": ["enhancement", "backtest", "phase-4"],
        "body": """## 概要
`src/backtest/engine.py` を実装し、時系列シミュレーションを実現する。

## タスク
- [ ] イベント駆動型バックテストエンジン
- [ ] Simulated Time注入機構(Look-ahead Bias防止)
- [ ] 日足OHLC間の価格補間
- [ ] スリッページモデリング(指値は始値で約定、成行は実際の乖離)
- [ ] 売買手数料・税金の適用

## 関連ドキュメント
- `documents/05_Backtest/BacktestFramework.md` Section 4""",
    },
    {
        "title": "【Phase 4】バックテストシミュレータ実装",
        "labels": ["enhancement", "backtest", "phase-4"],
        "body": """## 概要
`src/backtest/simulator.py` を実装する。

## タスク
- [ ] ポートフォリオ状態管理(保有株・現金・評価額)
- [ ] ドローダウン計算
- [ ] 約定管理・ポジション更新
- [ ] 手数料・税金の自動計算

## 関連ドキュメント
- `documents/05_Backtest/BacktestFramework.md`""",
    },
    {
        "title": "【Phase 4】バックテストメトリクス計算実装",
        "labels": ["enhancement", "backtest", "phase-4"],
        "body": """## 概要
`src/backtest/metrics.py` を実装し、評価指標を計算する。

## タスク
- [ ] CAGR(年平均成長率)
- [ ] Sharpe Ratio (最低1.0以上、理想1.5程度)
- [ ] Max Drawdown
- [ ] Win Rate / Payoff Ratio

## 関連ドキュメント
- `documents/05_Backtest/BacktestFramework.md` Section 3""",
    },
    {
        "title": "【Phase 4】Look-ahead Bias防止機構の実装 [CRITICAL]",
        "labels": ["enhancement", "backtest", "phase-4", "critical"],
        "body": """## 概要
バックテスト時のLook-ahead Biasを物理的に防止する。**最重要タスク。**

## タスク
- [ ] `Current Simulated Time` インターフェース設計
- [ ] 財務データ・ニュースの反映タイミング管理(翌営業日以降のみ)
- [ ] バックテスト用クロック(`datetime.now()`の上書き)

## 注意事項
> **CLAUDE.mdアーキテクチャ制約 #1**: バックテストと本番システムはロジックを共通化し、分析時において「未来のデータ」を誤って参照しないよう、現在時刻（Simulated Time）の注入機構を設けること。

## 関連ドキュメント
- `documents/05_Backtest/BacktestFramework.md` Section 4""",
    },
    {
        "title": "【Phase 4】バックテスト検証テスト実装",
        "labels": ["testing", "backtest", "phase-4"],
        "body": """## 概要
`tests/test_backtest_framework.py` を実装する。

## タスク
- [ ] 既知の戦略での期待値検証
- [ ] Look-ahead Biasの不存在確認
- [ ] スリッページ・手数料の正確な適用確認""",
    },
    # Phase 5: Portfolio Construction
    {
        "title": "【Phase 5】ポートフォリオビルダー実装",
        "labels": ["enhancement", "portfolio", "phase-5"],
        "body": """## 概要
`src/portfolio/portfolio_builder.py` を実装する。

## タスク
- [ ] シグナルからのランキング生成
- [ ] 上位銘柄選定(推奨10銘柄、最大15銘柄)
- [ ] スコア加重配分 / 等金額配分 / ボラティリティ調整配分

## 関連ドキュメント
- `documents/02_Strategy/PortfolioConstruction.md` Section 4-8""",
    },
    {
        "title": "【Phase 5】ポジションサイジングエンジン実装 [CRITICAL]",
        "labels": ["enhancement", "portfolio", "phase-5", "critical"],
        "body": """## 概要
`src/portfolio/position_sizing.py` を実装する。リスク管理ベースのポジション決定。

## タスク
- [ ] 許容リスク計算(総資産の0.5〜1.0%)
- [ ] 1銘柄最大投資比率(10%)チェック
- [ ] 全ポジション投下資金上限(70%)確認
- [ ] 単元株単位への丸め処理

## 関連ドキュメント
- `documents/02_Strategy/StrategyModel.md` Section 6
- `documents/06_RiskManagement/RiskManagement.md`""",
    },
    {
        "title": "【Phase 5】リスク調整・セクター制御実装",
        "labels": ["enhancement", "portfolio", "phase-5"],
        "body": """## 概要
`src/portfolio/risk_adjustment.py` を実装する。

## タスク
- [ ] セクター集中制限(同一セクター最大30%)
- [ ] 市場レジーム別の投資比率調整(Bull 100%, Neutral 70%, Bear 30%)
- [ ] ポートフォリオ監視メトリクス(銘柄数・セクター分散等)

## 関連ドキュメント
- `documents/02_Strategy/PortfolioConstruction.md` Section 8-9""",
    },
    {
        "title": "【Phase 5】ポートフォリオ構築ロジックのテスト",
        "labels": ["testing", "portfolio", "phase-5"],
        "body": """## 概要
`tests/test_portfolio_construction.py` を実装する。

## タスク
- [ ] ランキング生成の正確性
- [ ] ポジションサイジング計算の検証
- [ ] リスク上限の遵守確認""",
    },
    # Phase 6: Execution Engine
    {
        "title": "【Phase 6】kabuステーションAPIクライアント実装 [CRITICAL]",
        "labels": ["enhancement", "execution", "phase-6", "critical"],
        "body": """## 概要
`src/execution/broker_api.py` を実装し、kabuステーションAPIへのアクセスを実現する。

## タスク
- [ ] REST API発注処理
- [ ] WebSocket約定PUSH受信
- [ ] 注文照会API(リコンシリエーション用)
- [ ] 残高照会API
- [ ] エラーハンドリング・リトライロジック

## 関連ドキュメント
- `documents/04_Execution/ExecutionSystem.md`""",
    },
    {
        "title": "【Phase 6】Order State Machine実装 [CRITICAL]",
        "labels": ["enhancement", "execution", "phase-6", "critical"],
        "body": """## 概要
`src/execution/order_manager.py` を実装する。冪等な注文管理。

## タスク
- [ ] 注文状態遷移管理(Signal → OrderCreated → OrderSent → OrderAccepted → PartialFill/Filled → Closed)
- [ ] UUID/client_order_idによる冪等キー付与
- [ ] 二重発注防止
- [ ] 状態不確実性時の注文照会API連携(リコンシリエーション)
- [ ] DB永続化

## 注意事項
> **CLAUDE.mdアーキテクチャ制約 #3**: `signal_queue`を利用したPull型の実行アーキテクチャを遵守し、クラッシュ復旧時などに同じ発注が重複して実行される事故（二重発注）を確実に防ぐこと。

## 関連ドキュメント
- `documents/04_Execution/ExecutionSystem.md` Section 2""",
    },
    {
        "title": "【Phase 6】Execution Engineメインループ実装 [CRITICAL]",
        "labels": ["enhancement", "execution", "phase-6", "critical"],
        "body": """## 概要
`src/execution/execution_engine.py` を実装する。Signal QueueのPull型処理。

## タスク
- [ ] Signal Queueからのペンディング取得
- [ ] 3段階ガード(Signal/Execution/Metrics)によるリスク管理
- [ ] API送信とレート制限(毎秒5回以内)
- [ ] PUSH約定受信と状態更新
- [ ] ポジション管理

## 関連ドキュメント
- `documents/04_Execution/ExecutionSystem.md` Section 3""",
    },
    {
        "title": "【Phase 6】リスク管理3段階ガード実装 [CRITICAL]",
        "labels": ["enhancement", "execution", "phase-6", "critical"],
        "body": """## 概要
3段階のリスク検査を実装する。

## タスク
- [ ] 第1関門(Signal検証): 余力・重複・ポジション上限チェック
- [ ] 第2関門(Execution制限): APIレート制限・サーキットブレーカー
- [ ] 第3関門(Metrics監視): ドローダウン超過時のキルスイッチ

## 関連ドキュメント
- `documents/04_Execution/ExecutionSystem.md` Section 3
- `documents/06_RiskManagement/RiskManagement.md`""",
    },
    {
        "title": "【Phase 6】自動復旧・リコンシリエーション実装 [CRITICAL]",
        "labels": ["enhancement", "execution", "phase-6", "critical"],
        "body": """## 概要
システム再起動時の自動復旧機構を実装する。

## タスク
- [ ] OrderSent状態の検出と照会
- [ ] ローカルDBと証券口座の差分検出・同期
- [ ] 安全隔離・再開処理

## 関連ドキュメント
- `documents/04_Execution/ExecutionSystem.md` Section 4
- `documents/08_Operations/FailureRecovery.md`""",
    },
    {
        "title": "【Phase 6】Order State Machineの単体テスト",
        "labels": ["testing", "execution", "phase-6"],
        "body": """## 概要
`tests/test_order_management.py` を実装する。

## タスク
- [ ] 状態遷移の正確性
- [ ] 冪等キーの機能確認
- [ ] 二重発注防止""",
    },
    {
        "title": "【Phase 6】Execution Engineのシミュレーションテスト",
        "labels": ["testing", "execution", "phase-6"],
        "body": """## 概要
`tests/test_execution_engine.py` を実装する。

## タスク
- [ ] Signal Queueからの取得・処理
- [ ] APIレート制限の遵守
- [ ] リスク管理ガードの動作確認""",
    },
    # Phase 7: Monitoring
    {
        "title": "【Phase 7】Streamlit監視ダッシュボード実装",
        "labels": ["enhancement", "monitoring", "phase-7"],
        "body": """## 概要
`src/monitoring/streamlit_dashboard.py` を実装する。軽量な監視UI。

## タスク
- [ ] リアルタイムEquity推移グラフ
- [ ] 現在ポジション表示
- [ ] ドローダウン監視
- [ ] 未約定注文表示
- [ ] APIエラーログ表示

## 関連ドキュメント
- `documents/08_Operations/Monitoring.md` Section 10""",
    },
    {
        "title": "【Phase 7】SQLite監視ログDB実装",
        "labels": ["infrastructure", "monitoring", "phase-7"],
        "body": """## 概要
`src/monitoring/monitoring_db.py` を実装する。監視ログ管理。

## タスク
- [ ] `system_status` テーブル(CPU・メモリ・プロセス状態)
- [ ] `trade_logs` テーブル(発注・約定・ポジション)
- [ ] `risk_logs` テーブル(DD・ポジション上限・セクター集中)
- [ ] `dashboard` テーブル(ダッシュボード集計データ)

## 関連ドキュメント
- `documents/08_Operations/Monitoring.md` Section 3, 13""",
    },
    {
        "title": "【Phase 7】システム・データ監視エンジン実装",
        "labels": ["enhancement", "monitoring", "phase-7"],
        "body": """## 概要
`src/monitoring/system_monitor.py` を実装する。

## タスク
- [ ] CPU使用率・メモリ監視
- [ ] プロセス生存監視(Executionプロセス)
- [ ] データ更新状況監視(株価・ニュース・特徴量)
- [ ] AIスコア生成監視
- [ ] ETL失敗検出

## 関連ドキュメント
- `documents/08_Operations/Monitoring.md` Section 3-5""",
    },
    {
        "title": "【Phase 7】取引・リスク監視エンジン実装",
        "labels": ["enhancement", "monitoring", "phase-7"],
        "body": """## 概要
`src/monitoring/trade_monitor.py` と `risk_monitor.py` を実装する。

## タスク
- [ ] シグナル生成監視(異常値検出・銘柄数異常)
- [ ] 注文状態監視(未約定長時間滞留)
- [ ] 約定異常価格検出
- [ ] ドローダウン監視
- [ ] ポジション上限・セクター集中監視

## 関連ドキュメント
- `documents/08_Operations/Monitoring.md` Section 6-7""",
    },
    {
        "title": "【Phase 7】Slackアラート機能実装",
        "labels": ["enhancement", "monitoring", "phase-7"],
        "body": """## 概要
`src/monitoring/alert_manager.py` を実装する。

## タスク
- [ ] Slack API連携
- [ ] 異常検知時の通知(発注失敗・DD超過・Execution停止等)
- [ ] 重大度レベル別通知制御

## 関連ドキュメント
- `documents/08_Operations/Monitoring.md` Section 9""",
    },
    {
        "title": "【Phase 7】Kill Switch実装 [CRITICAL]",
        "labels": ["enhancement", "monitoring", "phase-7", "critical"],
        "body": """## 概要
`src/monitoring/kill_switch.py` を実装する。重大障害時の自動停止。

## タスク
- [ ] トリガー条件: DD超過・API接続断・Execution停止・異常注文
- [ ] 新規発注停止
- [ ] Executionプロセス停止
- [ ] 全ポジション成行売却検討
- [ ] Slack通知

## 関連ドキュメント
- `documents/08_Operations/Monitoring.md` Section 9
- `documents/06_RiskManagement/RiskManagement.md` Section 9""",
    },
    {
        "title": "【Phase 7】監視機能のユニットテスト",
        "labels": ["testing", "monitoring", "phase-7"],
        "body": """## 概要
`tests/test_monitoring.py` を実装する。

## タスク
- [ ] 各監視エンジンのアラート生成確認
- [ ] Slack通知の正確性
- [ ] ログDB書き込み確認""",
    },
    # Phase 8: Paper Trading
    {
        "title": "【Phase 8】Paper Trading環境構築",
        "labels": ["enhancement", "testing", "phase-8"],
        "body": """## 概要
Paper Trading環境を実装する(2〜4週間運用)。

## タスク
- [ ] 実時間シグナル生成
- [ ] 模擬ポジション追跡
- [ ] 本番と同じExecution Systemロジック
- [ ] Streamlitダッシュボード統合

## 関連ドキュメント
- `documents/05_Backtest/BacktestFramework.md` Section 2""",
    },
    {
        "title": "【Phase 8】Execution優先度制御実装",
        "labels": ["enhancement", "execution", "phase-8"],
        "body": """## 概要
Windows OSでの優先度制御を実装する。

## タスク
- [ ] Execution / MonitoringプロセスをHigh優先度に設定
- [ ] Strategy/AIプロセスをLow/Normalに設定
- [ ] CPU・メモリ割当の最適化

## 関連ドキュメント
- `documents/00_Architecture/SystemArchitecture.md` Section 3.1""",
    },
    {
        "title": "【Phase 8】Paper Trading検証テスト",
        "labels": ["testing", "phase-8"],
        "body": """## 概要
Paper Trading期間中の検証項目。

## タスク
- [ ] システム安定性確認(24/5稼働)
- [ ] 注文成功率測定
- [ ] シグナル精度確認
- [ ] APIレイテンシ測定""",
    },
    # Phase 9: Live Trading
    {
        "title": "【Phase 9】Windows Task Schedulerスクリプト実装",
        "labels": ["infrastructure", "deployment", "phase-9"],
        "body": """## 概要
`scripts/setup_task_scheduler.ps1` を実装し、自動スケジューリングを設定する。

## タスク
- [ ] 15:30 - data_update_job
- [ ] 16:00 - feature_generation_job
- [ ] 18:00 - ai_analysis_job
- [ ] 20:00 - strategy_signal_job
- [ ] 21:00 - portfolio_construction_job
- [ ] 08:30 - execution_start
- [ ] 09:00 - monitoring_start

## 関連ドキュメント
- `documents/10_Runtime/RuntimeJobSchedule.md`
- `documents/10_Runtime/RuntimeArchitecture.md`""",
    },
    {
        "title": "【Phase 9】システム起動・停止スクリプト実装",
        "labels": ["infrastructure", "deployment", "phase-9"],
        "body": """## 概要
運用スクリプトを実装する。

## タスク
- [ ] `scripts/start_system.py`: 全プロセス起動
- [ ] `scripts/stop_system.py`: グレースフルシャットダウン
- [ ] `scripts/rebuild_features.py`: 特徴量の再生成
- [ ] `scripts/reset_signals.py`: シグナルキューのリセット

## 関連ドキュメント
- `documents/00_Architecture/RepositoryStructure.md` Section 6""",
    },
    {
        "title": "【Phase 9】日次運用Runbookの整備",
        "labels": ["documentation", "operations", "phase-9"],
        "body": """## 概要
日常的な運用手順を整備する。

## タスク
- [ ] Pre-Market Checklist(08:00)
- [ ] Market Hours監視ポイント
- [ ] アラート対応フロー
- [ ] Market Close処理(15:30)
- [ ] 夜間処理確認

## 関連ドキュメント
- `documents/08_Operations/TradingRunbook.md`""",
    },
    {
        "title": "【Phase 9】障害復旧手順の整備",
        "labels": ["documentation", "operations", "phase-9"],
        "body": """## 概要
障害時の対応手順を整備する。

## タスク
- [ ] API接続障害
- [ ] PC再起動時のリコンシリエーション
- [ ] Signal Queue破損時の再生成
- [ ] ポジション不整合時の復旧
- [ ] Kill Switch発動後の復旧

## 関連ドキュメント
- `documents/08_Operations/FailureRecovery.md`""",
    },
    # Cross-cutting
    {
        "title": "【横断】Python環境・依存関係管理",
        "labels": ["infrastructure", "setup"],
        "body": """## 概要
`requirements.txt` を作成し、依存ライブラリを管理する。

## タスク
- [ ] pandas, numpy, scikit-learn
- [ ] duckdb, pyarrow (Parquet)
- [ ] requests, websocket-client (API)
- [ ] pyyaml (設定管理)
- [ ] streamlit (監視ダッシュボード)
- [ ] pytest (テスト)

## 関連ドキュメント
- `documents/00_Architecture/RepositoryStructure.md` Section 5""",
    },
    {
        "title": "【横断】CI/CDパイプライン構築",
        "labels": ["infrastructure", "devops"],
        "body": """## 概要
Git フロー + GitHub Actions による CI/CD パイプラインを整備する。

## タスク
- [ ] ブランチ戦略設定: main / develop / feature/*
- [ ] Pre-commit Hook: Black, isort, flake8, mypy
- [ ] GitHub Actions: ユニットテスト・Lint自動実行
- [ ] PRマージ前の自動検査

## 関連ドキュメント
- CLAUDE.md (Git & Repository Workflow セクション)""",
    },
    {
        "title": "【横断】統合テスト実装",
        "labels": ["testing"],
        "body": """## 概要
`tests/test_integration.py` を実装し、各モジュール間の連携をテストする。

## タスク
- [ ] Data → Strategy → Portfolio → Executionの一連フロー
- [ ] Signal Queueの処理確認
- [ ] Monitoringの通知確認""",
    },
    {
        "title": "【横断】ストレステスト・シナリオテスト実装",
        "labels": ["testing", "risk-management"],
        "body": """## 概要
極端な市場状況でのシステム動作を検証する。

## タスク
- [ ] マーケットクラッシュシナリオ
- [ ] API接続遮断シナリオ
- [ ] 流動性枯渇シナリオ

## 関連ドキュメント
- `documents/06_RiskManagement/RiskManagement.md`""",
    },
    {
        "title": "【横断】設定ファイル・スキーマ整備",
        "labels": ["infrastructure", "configuration"],
        "body": """## 概要
`config/` 配下のYAML設定スキーマを完備する。

## タスク
- [ ] `config/system_config.yaml`
- [ ] `config/data_config.yaml`
- [ ] `config/strategy_config.yaml`
- [ ] `config/risk_config.yaml`
- [ ] `config/execution_config.yaml`
- [ ] `config/monitoring_config.yaml`

## 関連ドキュメント
- `documents/01_Data/config_schema.md`""",
    },
    {
        "title": "【横断】APIキー・認証情報管理",
        "labels": ["infrastructure", "security"],
        "body": """## 概要
安全な認証情報管理を実装する。

## タスク
- [ ] `.env` ファイルによるAPIキー管理
- [ ] 環境変数注入
- [ ] Gitで秘密情報をコミットしない仕組み(.gitignore整備)
- [ ] `.env.example` テンプレート作成""",
    },
    {
        "title": "【横断】統合ログ・トレーサビリティシステム構築",
        "labels": ["monitoring", "operations"],
        "body": """## 概要
全システムのログを一元管理する。

## タスク
- [ ] ログレベル(DEBUG/INFO/WARNING/ERROR)の設定
- [ ] ログローテーション
- [ ] シグナル→発注→約定の完全なトレース(UUID連鎖)

## 関連ドキュメント
- `documents/08_Operations/Monitoring.md` Section 11""",
    },
    {
        "title": "【横断】パフォーマンス分析・レポート機能実装",
        "labels": ["monitoring", "reporting"],
        "body": """## 概要
定期的なパフォーマンス評価機能を実装する。

## タスク
- [ ] 日次・週次・月次リターン計算
- [ ] Sharpe Ratio、Max Drawdownの自動計算
- [ ] 戦略効果測定

## 関連ドキュメント
- `documents/05_Backtest/BacktestFramework.md` Section 3""",
    },
]


def create_issue(issue):
    data = json.dumps(issue).encode("utf-8")
    req = urllib.request.Request(API, data=data, headers=HEADERS, method="POST")
    try:
        with urllib.request.urlopen(req) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            print(f"Created: #{result['number']} {result['title']}")
            return True
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8")
        print(f"Error {e.code}: {body[:200]}")
        return False


total = len(issues)
success = 0
for i, issue in enumerate(issues, 1):
    print(f"[{i}/{total}] Creating: {issue['title'][:60]}")
    if create_issue(issue):
        success += 1
    time.sleep(0.8)

print(f"\n完了: {success}/{total} 件のIssueを登録しました。")
