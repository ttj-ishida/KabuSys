# KabuSys

日本株自動売買システムのリポジトリ用 README（日本語）

この README はリポジトリ内の主要スクリプト・設定フロー・ディレクトリ構成や利用方法を簡潔にまとめたものです。

---

## プロジェクト概要

KabuSys は日本株向けの自動売買システム向けユーティリティ群です。  
主な機能は次の通りです：

- 実行エンジン（ExecutionEngine）による注文管理（本番 / ペーパートレード対応）
- 監視（Monitoring）: システム状態、注文ログ、リスク監視と Kill Switch
- ポートフォリオ構築（候補選定、重み計算、ポジションサイズ計算、セクター制限など）
- リサーチ（ファクター計算、特徴量解析、IC 計算）
- AI 補助機能（ニュースの NLP スコアリング、レジーム判定）
- 運用・検証ツール（例: Paper Trading 検証レポートの生成）
- 環境設定ウィザード・設定検証 CLI

設計上の特徴：
- DuckDB / SQLite を用いたデータ保持（分析用と監視/注文用で分離）
- 環境変数 / .env による設定管理（config_setup.py, validate_config.py）
- 本番とペーパーを明確に分離（PAPER_TRADING 用 DB を使用）
- OpenAI を利用した NLP 処理（必要に応じて API キーを設定）

---

## 機能一覧（主要コンポーネント）

- 実行関連
  - run_execution.py: ExecutionEngine の起動スクリプト。KABUSYS_ENV により本番 or paper_trading を切替
  - BrokerClientFactory を通じたブローカー抽象化
  - OrderManager / OrderRepository / RiskManager / Reconciler など

- 監視関連
  - run_monitoring.py: SystemMonitor をポーリングする起動スクリプト（MONITOR_POLL_INTERVAL で間隔指定可）
  - MonitoringDB: SQLite を用いた監視ログ永続化
  - SystemMonitor / TradeMonitor / RiskMonitor / KillSwitch / AlertManager / MonitoringEngine

- ポートフォリオ構築
  - portfolio_builder: 候補選定・スコア順ソート
  - position_sizing: 株数決定（risk_based / equal / score）・lot 単位丸め・aggregate cap
  - risk_adjustment: セクター制限・レジーム乗数

- リサーチ
  - factor_research: Momentum / Value / Volatility 等のファクター計算（DuckDB 接続を受け取る）
  - feature_exploration: 将来リターン、IC、統計サマリ

- AI 関連
  - news_nlp: raw_news を OpenAI でセンチメント評価し ai_scores に保存
  - regime_detector: ETF の MA200 + マクロニュース（LLM）による市場レジーム判定

- ツール
  - config_setup.py: 対話式 .env 作成ウィザード
  - validate_config.py: 起動前の設定検証 CLI
  - tools/paper_verification_report.py: ペーパートレード検証レポート生成

---

## セットアップ手順（開発 / ローカル実行向け）

以下は基本的なローカルセットアップ例です。プロダクション環境向けに細かく調整してください。

1. リポジトリをクローン
   ```bash
   git clone <repo-url>
   cd <repo-dir>
   ```

2. Python 仮想環境を作成して有効化（推奨）
   ```bash
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 必要なパッケージをインストール  
   （requirements.txt がある場合はそれを使ってください。なければ主要な依存を個別にインストール）
   ```bash
   pip install duckdb openai psutil
   # その他プロジェクトが必要とするパッケージがあれば追記してください
   ```

4. .env の初期作成（ウィザード）
   ```bash
   python -m kabusys.config_setup
   ```
   ウィザードに従って J-Quants トークン、kabu API パスワード、DB パス、KABUSYS_ENV などを設定します。
   - 主要な必須環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - OpenAI を利用する場合:
     - OPENAI_API_KEY（news_nlp や regime_detector で使用）

5. 設定を検証
   ```bash
   python -m kabusys.validate_config
   # --strict を付けると警告もエラー扱いになります
   ```

6. データディレクトリ / ログディレクトリ
   - デフォルトの DB / ログパス:
     - DuckDB: data/kabusys.duckdb
     - SQLite(監視): data/monitoring.db
     - Paper Trading SQLite: data/paper_trading.db
     - ログ: logs/
   - スクリプト実行時にディレクトリが自動作成されますが、権限等は事前に確認してください。

---

## 使い方（主要コマンド）

- 環境設定ウィザード
  ```bash
  python -m kabusys.config_setup
  ```

- 設定検証
  ```bash
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- 実行エンジン起動（Execution）
  ```bash
  python -m kabusys.run_execution
  ```
  補足:
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し paper_sqlite_path（デフォルト data/paper_trading.db）へ記録します。本番 DB と分離されます。
  - 起動時に data/stop_requested.flag が存在すると起動を行わず終了します（停止フラグ）。

- 監視ループ起動（Monitoring）
  ```bash
  python -m kabusys.run_monitoring
  ```
  補足:
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を指定可能（デフォルト 60 秒）。
  - Monitoring は環境に関係なく本番 sqlite_path を参照して監視データを記録します（監視 DB を共有したくない場合は設定を調整してください）。

- Paper Trading 検証レポート（ツール）
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # --db で別 DB を指定可能
  ```

- AI 関連（スコア算出・レジーム判定）はライブラリ関数として利用
  - news_nlp.score_news(conn, target_date, api_key=None)
  - regime_detector.score_regime(conn, target_date, api_key=None)

---

## 重要な運用ノート

- Kill Switch:
  - risk_monitor の条件を満たすと KillSwitch が data/kill.flag を書き込み、ExecutionEngine は起動中に kill.flag を検出して停止します。
  - 起動時の自動クリアは KILL_FLAG_CLEAR_ON_START 環境変数で制御（0/1）。本番では 0 を推奨。

- プロセス優先度:
  - run_execution/run_monitoring は起動時にプロセス優先度を "high" に設定する試みを行います（プラットフォーム依存で失敗する場合は警告に留まる）。

- Paper Trading:
  - PAPER_FILL_MODE（instant, partial, never, reject）でモックの約定挙動を制御可能。

- DuckDB / SQLite:
  - DuckDB は主にリサーチ・分析用。SQLite は監視ログ / 注文履歴用に利用。
  - monitoring_db.init_monitoring_db は冪等でテーブル・列のマイグレーションを行います。

- ログ:
  - ログは logs/<app_name>.log に日次ローテートで出力されます。LOG_DIR / LOG_LEVEL で挙動変更可。

---

## ディレクトリ構成（抜粋）

以下は主要なモジュールのツリー（src/kabusys 配下）と簡単な説明です。

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数/.env の読み込みと Settings
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成
  - execution/               — 発注関連（BrokerFactory, Engine, OrderManager, RiskManager, Reconciler 等）
  - monitoring/
    - monitoring_db.py       — SQLite 監視 DB レイヤ
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py            — ニュースセンチメント（OpenAI）
    - regime_detector.py     — 市場レジーム判定（MA200 + LLM）
  - utils/
    - logging_setup.py       — 統一ロギング設定
    - process_priority.py    — プロセス優先度 / CPU affinity ヘルパ
  - data/ (非コード)         — デフォルト DB / PID / フラグファイルが置かれる想定ディレクトリ

※ 上記に示した各コンポーネントは内部にさらに多くのファイルを含みます。リポジトリ全体のツリーを参照して詳細を確認してください。

---

## サンプル .env（最小構成）

.env ファイルの例（実運用ではトークン等を秘匿してください）：

KABUSYS_ENV=development
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
KABU_API_PASSWORD=your_kabu_api_password_here
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO
KILL_FLAG_CLEAR_ON_START=0
# OPENAI_API_KEY=sk-...

---

## 開発・テストのヒント

- validate_config.py は起動前に設定不備を検出するため、CI で利用できます。
- AI モジュールは外部 API に依存するため、ユニットテストでは OpenAI 呼び出し部分（_call_openai_api など）をモックしてください。
- DuckDB 接続を受け取る関数群は副作用を持たず、ローカルの DuckDB ファイルで容易に検証できます。
- run_execution/run_monitoring は stop/kill フラグファイルによる制御を行っているため、運用時は data/stop_requested.flag / data/kill.flag の管理に注意してください。

---

## ライセンス / バージョン

パッケージバージョンは src/kabusys/__init__.py 内の __version__ を参照してください。  
（必要に応じて LICENSE ファイルを追加してください）

---

README に記載されていない細かな実装や API 仕様については、各モジュールの docstring を参照してください。質問や追加のドキュメント化が必要であればお知らせください。