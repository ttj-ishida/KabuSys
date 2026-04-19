# KabuSys

日本株自動売買システムのコードベース README。

バージョン: 0.1.0（src/kabusys/__init__.py）

---

## 概要

KabuSys は日本株向けの自動売買・リサーチ・監視フレームワークです。  
主な役割は以下の通りです。

- 発注エンジン（ExecutionEngine）による発注・リスク管理（本番 / ペーパートレード対応）
- 監視（Monitoring）: システム状態、注文フロー、リスク指標の定期チェックとアラート／Kill Switch
- ポートフォリオ構築（候補選定、重み付け、株数決定、セクター制約）
- リサーチ（ファクター計算、特徴量探索、IC計算など）
- AI モジュール（ニュースセンチメント評価、レジーム判定） — OpenAI を利用
- ユーティリティ（ログ設定、プロセス優先度設定、設定ウィザード、設定検証、ツール類）

設計方針として、DB（DuckDB/SQLite）とファイルベースのフラグ操作を用い、テストしやすく安全な運用を重視しています。

---

## 主な機能一覧

- Execution
  - 本番 / ペーパートレード分離（PAPER_TRADING 用 DB）
  - ブローカークライアント抽象化（BrokerClientFactory）
  - 注文管理・リスク管理・約定リコンシリエーション
- Monitoring
  - SystemMonitor: CPU/メモリ/ディスク/データ鮮度 / 実行プロセス検知
  - TradeMonitor: 注文滞留・約定異常の検出（実装ファイルあり）
  - RiskMonitor: ドローダウン・ポジション上限の監視
  - KillSwitch: 条件に応じて data/kill.flag を書き込み Execution を停止
  - MonitoringDB: SQLite でログ・ダッシュボードを永続化（マイグレーション含む）
  - MonitoringEngine: 各モニタを束ねたポーリングループ
- Portfolio
  - 候補選定（スコア順）、等ウェイト・スコア加重、位置サイズ計算（リスクベース、単元丸め、aggregate cap）
  - セクター上限適用、レジーム乗数計算
- Research
  - ファクター計算（Momentum/Volatility/Value）、将来リターン、IC、統計サマリ
  - DuckDB を利用した SQL/Python 混在の計算
- AI
  - news_nlp: OpenAI を用いた銘柄別ニュースセンチメント生成（ai_scores テーブル）
  - regime_detector: ETF の MA とマクロ記事の LLM センチメントを合成して日次レジーム判定
- ツール
  - config_setup: .env の対話式生成ウィザード
  - validate_config: 起動前の設定検証（必須 env 変数、config/*.yaml、DB パス等）
  - paper_verification_report: ペーパートレード検証レポート生成

---

## セットアップ手順

前提:
- Python 3.10 以上（typing の `X | Y` 構文を使用）
- SQLite は標準ライブラリで同梱
- 作業ディレクトリはプロジェクトルート（pyproject.toml または .git がある場所）を想定

1. リポジトリをクローン / 展開

2. 仮想環境作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate (macOS/Linux) または .venv\Scripts\activate (Windows)

3. 必要パッケージをインストール
   - 最低推奨パッケージ:
     - duckdb
     - psutil
     - openai (AI 機能利用時)
     - PyYAML（validate_config で YAML 検証を行う場合）
   - 例:
     - pip install duckdb psutil openai PyYAML

   （requirements.txt がない場合は上記を個別にインストールしてください）

4. 初期設定 (.env) の作成
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - もしくは .env.example を参考に手動で .env を作成

5. 設定検証（任意だが推奨）
   - python -m kabusys.validate_config
   - 警告も失敗扱いにする場合は `--strict` を付ける

6. データ・ログディレクトリ
   - デフォルト:
     - DuckDB: data/kabusys.duckdb
     - SQLite (monitoring): data/monitoring.db
     - Paper Trading SQLite: data/paper_trading.db
     - ログ: logs/
   - これらは設定で上書き可能（.env の DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH / LOG_DIR）

---

## 環境変数（主要）

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

運用に重要なもの（主なもののみ）:
- KABUSYS_ENV: development | paper_trading | live (default: development)
  - paper_trading では MockBrokerClient を使用し、別 DB に記録
- DUCKDB_PATH (default: data/kabusys.duckdb)
- SQLITE_PATH (default: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (default: data/paper_trading.db)
- LOG_LEVEL (DEBUG/INFO/WARNING/ERROR/CRITICAL, default: INFO)
- OPENAI_API_KEY (AI 機能利用時)
- PAPER_FILL_MODE (paper_trading の約定挙動: instant|partial|never|reject, default: instant)
- MONITOR_POLL_INTERVAL (監視ループ間隔 秒、default: 60) — run_monitoring で参照
- KILL_FLAG_CLEAR_ON_START (0/1) — 本番での自動 kill フラグクリア設定（推奨は 0）

例（.env に書く内容の最小例）:
```
JQUANTS_REFRESH_TOKEN=your_jquants_token_here
KABU_API_PASSWORD=your_kabu_password_here
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO
```

注意: .env は Git にコミットしないでください（config_setup にも警告あり）。

---

## 実行方法（使い方）

基本的にモジュールを直接実行する形です。プロジェクトルートから実行してください。

- 設定ウィザード（.env 生成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳格モード: python -m kabusys.validate_config --strict

- ExecutionEngine を起動（本番 / paper_trading は KABUSYS_ENV による）
  - python -m kabusys.run_execution
  - 動作:
    - プロセス優先度を high に設定
    - DB 接続（paper_trading 時は PAPER_TRADING_SQLITE_PATH を使用）
    - BrokerClientFactory によるブローカークライアント生成
    - ExecutionEngine を別スレッドで起動し、data/stop_requested.flag を監視して停止

- Monitoring を起動
  - python -m kabusys.run_monitoring
  - 動作:
    - プロセス優先度を high に設定
    - monitoring 用 DB を常に（環境に関わらず）本番 sqlite_path に接続して初期化
    - SystemMonitor を起動して定期ポーリング（MONITOR_POLL_INTERVAL 秒、デフォルト 60）
    - data/stop_requested.flag 検知で終了

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db /path/to/paper_trading.db （環境変数 PAPER_TRADING_SQLITE_PATH より優先）

- AI 関連（プログラム API 呼び出し）
  - kabusys.ai.score_news(conn, target_date, api_key=None) など。OpenAI API キーが必要。

停止方法（運用）:
- 停止要求: プロセス外から `data/stop_requested.flag` を作成すると run_monitoring や run_execution のループが検知して終了・停止手順を実行します。
- Kill Switch: モニタが条件を満たすと `data/kill.flag` を書き込み、ExecutionEngine 側で検知して安全に停止します。`KILL_FLAG_CLEAR_ON_START=1` を設定すると起動時に自動でクリアされますが、本番では 0 を推奨。

ログ:
- デフォルトは logs/<app_name>.log（日次ローテーション・30日保持）およびコンソール出力。setup_logging が統一設定します。

---

## 主要モジュールの簡単説明

- src/kabusys/run_execution.py
  - ExecutionEngine の起動スクリプト。paper_trading モード時は MockBrokerClient を使い、DB は data/paper_trading.db に分離。

- src/kabusys/run_monitoring.py
  - SystemMonitor のポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL で間隔指定可。

- src/kabusys/config_setup.py
  - .env を対話式に生成・更新するウィザード。

- src/kabusys/validate_config.py
  - .env と config/*.yaml の基本チェックを行う CLI。

- src/kabusys/config.py
  - Settings クラス: 環境変数読み込み、デフォルト値、バリデーションを提供。自動的にプロジェクトルートの .env / .env.local をロードする（無効化可能）。

- src/kabusys/utils/
  - logging_setup.py: 一貫したログ設定（コンソール + 日次ファイル）
  - process_priority.py: OS に依存しないプロセス優先度・CPU affinity 設定ユーティリティ

- src/kabusys/monitoring/
  - monitoring_db.py: SQLite テーブル作成・読み書きラッパー（system_status/trade_logs/positions/risk_logs/dashboard）
  - system_monitor.py / trade_monitor.py / risk_monitor.py / monitoring_engine.py / kill_switch.py / alert_manager.py: 監視ロジック一式

- src/kabusys/execution/
  - ExecutionEngine、注文管理、リスク管理、ブローカーファクトリ等（発注ロジック）

- src/kabusys/portfolio/
  - portfolio_builder.py, position_sizing.py, risk_adjustment.py: 候補選定・重み付け・株数決定・セクター調整

- src/kabusys/research/
  - factor_research.py, feature_exploration.py: ファクター計算、将来リターン、IC、統計サマリ

- src/kabusys/ai/
  - news_nlp.py, regime_detector.py: OpenAI を用いたニュース / マクロセンチメント評価とレジーム判定

- src/kabusys/tools/
  - paper_verification_report.py: ペーパートレード検証レポート生成

---

## ディレクトリ構成（主なファイル）

（プロジェクトルート 以下、src/kabusys を抜粋）

- src/kabusys/
  - __init__.py
  - config.py
  - config_setup.py
  - validate_config.py
  - run_execution.py
  - run_monitoring.py
  - utils/
    - __init__.py
    - logging_setup.py
    - process_priority.py
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py
  - execution/
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - broker_factory.py
    - reconciler.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - ai/
    - news_nlp.py
    - regime_detector.py
    - __init__.py
  - tools/
    - paper_verification_report.py
    - __init__.py
  - data/ (実行時に生成される想定)
    - execution.pid
    - kill.flag
    - stop_requested.flag
    - monitoring.db / paper_trading.db など

---

## 運用上の注意点

- KABUSYS_ENV の値によって実際の発注が行われるかが決まります。live 環境に設定して起動する際は、すべての設定値（APIキー、LINE 通知先、Kill Switch の設定など）を慎重に確認してください。
- .env は決してリポジトリにコミットしないでください。
- OpenAI API を用いる機能は API 呼び出しに料金が発生します。API キーの保護、コール頻度の設計に注意してください。
- run_monitoring は監視ログ用に常に本番 sqlite_path（settings.sqlite_path）を使用します。監視ログが本番 DB を参照する設計意図です。
- ペーパートレード環境は本番 DB と完全に分離するよう設計されています（PAPER_TRADING_SQLITE_PATH を使用）。

---

## 参考コマンドまとめ

- .env 作成: python -m kabusys.config_setup
- 設定検証: python -m kabusys.validate_config [--strict]
- 実行エンジン起動: python -m kabusys.run_execution
- 監視プロセス起動: python -m kabusys.run_monitoring
- ペーパートレード検証レポート: python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]

---

この README はコードベースの主要点をまとめたものです。さらに詳細な仕様（StrategyModel.md / PortfolioConstruction.md など参照）や、個別モジュールの API ドキュメントは該当ソースファイルの docstring を参照してください。必要であれば、セクションごとに詳細な使い方・例を追加できます。