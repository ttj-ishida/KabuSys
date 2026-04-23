# KabuSys

日本株自動売買システムのコードベース README（日本語）

概要、機能、セットアップ手順、使い方、ディレクトリ構成をまとめます。

---

## プロジェクト概要

KabuSys は日本株の自動売買プラットフォームのコアライブラリ群です。以下の主要機能を持ち、実運用（live）・ペーパートレード（paper_trading）・開発（development）に対応します。

- 発注実行エンジン（ExecutionEngine）とブローカー抽象化（本番/モック切替）
- 監視（Monitoring）: システム稼働・データ鮮度・注文状況・リスクチェックと Kill Switch
- ポートフォリオ構築: 候補選定、重み計算、ポジションサイズ算出（ロット丸め等）
- リサーチ: ファクター計算（モメンタム/ボラティリティ/バリュー）・特徴量解析（IC 等）
- AI 支援機能: ニュースの NLP（OpenAI）によるセンチメントスコア、レジーム判定
- ユーティリティ: ロギング設定、プロセス優先度制御、設定ウィザード・検証ツール
- 検証ツール: Paper Trading 検証レポート生成

設計方針として、DB 層は duckdb（分析用）・sqlite（監視/ペーパートレード永続化）に分離し、LLM 呼び出しは明確に独立しています。

---

## 主な機能一覧

- Execution
  - ExecutionEngine による注文発行フロー
  - BrokerClientFactory で本番/モックを切替（KABUSYS_ENV=paper_trading で MockBrokerClient を利用）
  - RiskManager / OrderManager / Reconciler による堅牢な注文管理
- Monitoring
  - SystemMonitor: CPU/メモリ/ディスク、プロセス生存確認、データ鮮度チェック
  - TradeMonitor: 注文滞留・約定異常検出（ファイル trade_logs 等に記録）
  - RiskMonitor: ドローダウン・ポジション上限監視、kill.flag の発行
  - MonitoringEngine: ポーリングループ、アラート発行
- Portfolio
  - 候補選定（select_candidates）
  - 重み算出（等分配、スコア加重）
  - ポジションサイズ計算（risk_based / equal / score、単元株丸め、aggregate cap）
  - セクターキャップ適用、レジーム乗数算出
- Research
  - ファクター計算：momentum / volatility / value
  - 将来リターン、IC（スピアマンランク相関）、統計サマリー
- AI
  - news_nlp.score_news: OpenAI を用いたニュースセンチメント集約・書き込み
  - regime_detector.score_regime: ETF MA とマクロセンチメント合成による市場レジーム判定
- ツール
  - 環境設定ウィザード: python -m kabusys.config_setup
  - 設定検証: python -m kabusys.validate_config
  - Paper Trading 検証レポート: python -m kabusys.tools.paper_verification_report

---

## セットアップ手順

前提:
- Python 3.10 以上を推奨（型ヒントで | を使用しているため）
- OS: Linux / macOS / Windows（ただし一部プロセス優先度・CPU affinity は OS に依存）

1. リポジトリをクローン／配置する
   - プロジェクトルートには `src/` 以下にパッケージが存在します。

2. 必要パッケージをインストール
   - 代表的な依存例:
     - duckdb
     - psutil
     - openai
     - PyYAML（設定検証の YAML パース用）
   - 例:
     - pip install duckdb psutil openai PyYAML

   ※ requirements.txt がある場合はそれを使用してください（本リポジトリ提供状況に依存）。

3. 環境変数設定（.env）
   - 対話式ウィザードで初期 .env を作成:
     - python -m kabusys.config_setup
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - AI 機能を利用する場合は:
     - OPENAI_API_KEY を設定（score_news / score_regime が必要とする）
   - その他代表的な環境変数（デフォルトあり）:
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）
     - LOG_LEVEL（デフォルト: INFO）
     - PAPER_FILL_MODE（paper_trading 用: instant|partial|never|reject）
     - MONITOR_POLL_INTERVAL（監視ループの秒間隔、run_monitoring で使用）
     - KILL_FLAG_CLEAR_ON_START（起動時に kill.flag をクリアするか: 0/1）

4. 設定検証（任意だが推奨）
   - python -m kabusys.validate_config
   - Strict モード（警告も失敗として扱う）:
     - python -m kabusys.validate_config --strict

5. ログディレクトリ
   - デフォルトで `logs/` にログファイルを日次ローテート（30日保持）で書き出します。
   - LOG_DIR を設定することで変更可能。

---

## 使い方（主要スクリプト）

- ExecutionEngine 起動（本番／ペーパーいずれも Settings に従う）
  - python -m kabusys.run_execution
  - 特記事項:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し paper_trading DB（PAPER_TRADING_SQLITE_PATH）に記録。
    - 起動時に data/stop_requested.flag が存在すると起動をスキップ。
    - 実行中は data/execution.pid に PID を書きます。

- Monitoring 起動（ポーリング）
  - python -m kabusys.run_monitoring
  - 環境変数:
    - MONITOR_POLL_INTERVAL: ポーリング間隔（秒、デフォルト 60）
  - 動作:
    - SystemMonitor・TradeMonitor・RiskMonitor を用いて定期チェックを実行。
    - data/stop_requested.flag が作成されるとループを終了。
    - 監視は常に本番 sqlite_path を参照（環境に依存せず監視 DB を本番 DB に格納する設計）。

- 環境設定ウィザード
  - python -m kabusys.config_setup
  - .env を対話的に生成・更新します。

- 設定検証
  - python -m kabusys.validate_config
  - --strict オプションで警告もエラー扱いにできます。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - デフォルト DB: data/paper_trading.db または環境変数 PAPER_TRADING_SQLITE_PATH

---

## 運用上のファイル / フラグ

- data/stop_requested.flag
  - run_execution / run_monitoring が停止依頼として監視するフラグ。存在するとループ終了や起動抑止を行います。

- data/execution.pid
  - Execution エンジン起動時に PID を書き込むファイル。

- data/kill.flag
  - KillSwitch が書き込み、ExecutionEngine 停止要求を発行する（主にリスク閾値超過時）。Settings.kill_flag_clear_on_start により起動時に自動クリア可能。

---

## ログ/デバッグ

- ログ設定は共通ユーティリティで行われ、標準出力（stdout）と日次ローテートのファイルに出力されます。
- デフォルトログディレクトリ: logs/
- ログレベルは環境変数 LOG_LEVEL で調整（例: DEBUG, INFO, WARNING）。

---

## 環境変数一覧（主要）

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

AI（任意）:
- OPENAI_API_KEY

運用 / DB:
- KABUSYS_ENV (development | paper_trading | live)
- DUCKDB_PATH (default: data/kabusys.duckdb)
- SQLITE_PATH (default: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (default: data/paper_trading.db)
- PAPER_FILL_MODE (instant | partial | never | reject)

監視:
- MONITOR_POLL_INTERVAL (秒、run_monitoring 用)
- KILL_FLAG_CLEAR_ON_START (0/1)

ログ:
- LOG_LEVEL
- LOG_DIR

詳細は `kabusys.config.Settings` を参照してください（コード内に各プロパティの説明あり）。

---

## ディレクトリ構成

主要ファイル / モジュールの一覧（src/kabusys 以下、抜粋）

- src/kabusys/
  - __init__.py
  - run_execution.py              — ExecutionEngine 起動スクリプト
  - run_monitoring.py             — Monitoring ポーリング起動スクリプト
  - config.py                     — 環境変数 / 設定管理
  - config_setup.py               — .env 生成ウィザード
  - validate_config.py            — 設定検証 CLI
  - utils/
    - logging_setup.py            — ログ初期化ユーティリティ
    - process_priority.py         — プロセス優先度 / CPU affinity
  - execution/
    - broker_factory.py
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
    - ...                         （発注ロジック等）
  - monitoring/
    - monitoring_db.py            — SQLite テーブル定義・永続化 API
    - monitoring_engine.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py                  — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py          — レジーム判定（MA + マクロセンチメント）
  - tools/
    - paper_verification_report.py — Paper Trading の検証レポート生成ツール

（上記は代表的なモジュール。さらに細分化された実装ファイルが含まれます）

---

## 運用上の注意 / ベストプラクティス

- 本番環境（KABUSYS_ENV=live）では .env を十分に確認し、LINE の通知設定等を適切に行ってください。validate_config の live 用ガードを活用してください。
- kill.flag の自動クリア（KILL_FLAG_CLEAR_ON_START=1）は本番では推奨されません（誤って Kill Switch を消してしまうリスク）。
- Paper Trading と本番の DB は明確に分離してください（PAPER_TRADING_SQLITE_PATH を利用）。
- OpenAI キーは適切に保護し、不要なログ出力に含めないようにしてください。
- logs/ の容量やパーミッションを運用開始前に確認してください。

---

この README はコードベースの主要点を抜粋してまとめたものです。詳細実装や API の挙動は各モジュールの docstring およびソースコードを参照してください。質問や追加のドキュメント化が必要であれば教えてください。