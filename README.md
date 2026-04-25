# KabuSys

日本株向け自動売買システムのリファレンス実装（ライブラリ + 起動スクリプト群）。  
本リポジトリは戦略の研究/検証、ペーパートレード、本番運用を想定した以下のコンポーネントを含みます。

- データ処理 / DuckDB を用いたファクタ計算（research）
- ポートフォリオ構築（portfolio）
- 発注エンジン（execution） — 本番 / ペーパートレード切替対応
- 監視コンポーネント（monitoring） — システム状態・注文ログ・リスク監視・Kill Switch
- AI モジュール（ai） — ニュース NLP / レジーム判定（OpenAI 利用）
- 運用補助ツール（tools）

---

## 機能一覧

- 環境設定ウィザード（.env 作成 / 更新）: python -m kabusys.config_setup
- 設定検証 CLI: python -m kabusys.validate_config
- ExecutionEngine 起動スクリプト（本番 / paper_trading 切替）: python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、data/paper_trading.db に記録
- SystemMonitor（監視ループ）起動スクリプト: python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）
- 監視 DB（SQLite）操作ユーティリティ（monitoring_db）
- Kill Switch（data/kill.flag）による ExecutionEngine の安全停止
- リスク監視（ドローダウン・ポジション上限）とアラート連携
- Paper Trading 検証レポート生成ツール: python -m kabusys.tools.paper_verification_report
- DuckDB を使ったファクター計算・研究用ユーティリティ（research）
- ニュースを LLM でスコア化する AI モジュール（OpenAI／gpt-4o-mini を使用）
- ロギングの統一設定（stdout + 日次ローテートファイル）

---

## セットアップ手順（ローカルでの基本手順）

前提: Python 3.9+ を想定（duckdb / openai / psutil 等に依存）。

1. リポジトリをクローン
   - git clone <repo-url>
   - cd <repo>

2. 仮想環境を作成・有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   - （プロジェクトに requirements.txt がない場合）最低限のパッケージ:
     - pip install duckdb psutil openai
     - PyYAML を使いたい場合: pip install PyYAML
   - または開発用にまとめて:
     - pip install duckdb psutil openai PyYAML

   注: SQLite は標準ライブラリで利用可能です。

4. ディレクトリを作成
   - mkdir -p data logs

5. .env の初期作成
   - python -m kabusys.config_setup
   - ウィザードに従って .env を作成します（.env は絶対に Git にコミットしないでください）。

6. 設定検証
   - python -m kabusys.validate_config
   - 必須項目が揃っているかをチェックします。
   - --strict を付けると警告も失敗扱いになります。

7. （OpenAI を使用する場合）
   - 環境変数 OPENAI_API_KEY を設定するか、AI を呼ぶ箇所で api_key を渡してください。

---

## 使い方（主要なコマンド）

- 環境設定ウィザード
  - python -m kabusys.config_setup
    - .env の対話式作成／更新。生成後、python -m kabusys.validate_config で検証を推奨。

- 設定検証
  - python -m kabusys.validate_config [--strict]
    - 必須環境変数、パス、config/*.yaml の存在（および PyYAML があればパース）をチェック。

- ExecutionEngine を起動
  - python -m kabusys.run_execution
    - KABUSYS_ENV により動作モードが切り替わる:
      - development: 発注なし（開発用）
      - paper_trading: MockBroker を使用、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）へ記録
      - live: 本番ブローカークライアントを使用（要 KABU_API_PASSWORD 等の設定）
    - 起動時にプロセス優先度を "high" に設定します。
    - 停止は data/stop_requested.flag にフラグファイルを置くか、Ctrl+C。

- SystemMonitor（監視ループ）を起動
  - python -m kabusys.run_monitoring
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可能（デフォルト 60）
    - 監視用 SQLite は Settings.sqlite_path（デフォルト data/monitoring.db）を使用（monitoring は環境にかかわらず本番 sqlite_path を参照）
    - 停止は data/stop_requested.flag の作成または Ctrl+C。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
    - PAPER_TRADING_SQLITE_PATH 環境変数を優先、未指定なら data/paper_trading.db。

- AI / レジーム判定・ニューススコアリング（プログラム的に利用）
  - kabusys.ai.score_news（DuckDB 接続と target_date を渡す）
  - kabusys.ai.regime_detector.score_regime（DuckDB 接続と target_date を渡す）
  - どちらも OPENAI_API_KEY が必要（または引数で API キーを渡す）。

---

## 主な環境変数（抜粋）

- 必須（validate_config でチェック）
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD

- 実行環境
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）

- DB / ログ
  - DUCKDB_PATH: DuckDB ファイル（デフォルト data/kabusys.duckdb）
  - SQLITE_PATH: 監視 DB（デフォルト data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（デフォルト data/paper_trading.db）
  - LOG_DIR: ログ出力先（デフォルト logs/）
  - LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）

- その他
  - OPENAI_API_KEY: OpenAI API キー（ai モジュール利用時）
  - PAPER_FILL_MODE: ペーパートレードの約定動作（instant | partial | never | reject、デフォルト: instant）
  - MONITOR_POLL_INTERVAL: run_monitoring でのポーリング間隔（秒、デフォルト: 60）

- Kill Switch / PID
  - PID_FILE_PATH: ExecutionEngine の pid ファイル（デフォルト data/execution.pid）
  - KILL_FLAG_PATH: kill.flag のパス（デフォルト data/kill.flag）
  - KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（0/1、デフォルト 0）

例（.env に記述する主要項目の例）
JQUANTS_REFRESH_TOKEN=your_token_here
KABU_API_PASSWORD=your_password_here
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
OPENAI_API_KEY=sk-...
LOG_LEVEL=INFO
KILL_FLAG_CLEAR_ON_START=0

---

## 運用上の注意

- .env は機密情報を含むため、絶対にリポジトリにコミットしないでください。
- 本番 (KABUSYS_ENV=live) では LINE 通知設定や Kill Switch の取り扱いを十分に確認してください（validate_config に警告があります）。
- monitoring は常に Settings.sqlite_path（監視 DB）を使用します。paper_trading 時でも監視 DB は本番と同じパスを参照するよう設計されています。
- run_execution は KABUSYS_ENV=paper_trading 時に paper_trading DB（PAPER_TRADING_SQLITE_PATH）へ記録し、本番 DB と分離します。
- AI モジュールは外部 API（OpenAI）を呼び出します。API 失敗時はフェイルオープン（スコア0.0 等）となるよう実装されていますが、API コストやレート制限に注意してください。
- ロギングは kabusys.utils.logging_setup.setup_logging を通じて統一されています。logs/ ディレクトリに日次ローテートでログが出力されます。

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py                  — 環境変数 / 設定管理
- config_setup.py            — .env 対話ウィザード
- validate_config.py         — 設定検証 CLI
- run_execution.py           — ExecutionEngine 起動スクリプト
- run_monitoring.py          — SystemMonitor 起動スクリプト

- execution/                 — 発注エンジン関連コンポーネント（Engine, BrokerFactory, OrderManager 等）
- monitoring/
  - monitoring_db.py         — SQLite 永続化層（system_status / trade_logs / positions / risk_logs / dashboard）
  - system_monitor.py
  - trade_monitor.py
  - risk_monitor.py
  - kill_switch.py
  - monitoring_engine.py
  - alert_manager.py
- portfolio/
  - portfolio_builder.py      — 候補選定、等ウェイト/スコアウェイト
  - position_sizing.py        — 発注数量算出（リスクベース等）
  - risk_adjustment.py        — セクター制限、レジーム乗数
- research/
  - factor_research.py        — momentum / volatility / value ファクター計算（DuckDB）
  - feature_exploration.py    — 将来リターン・IC 等の統計解析
- ai/
  - news_nlp.py               — ニュース NLP（OpenAI 呼び出し・結果検証・ai_scores へ書込）
  - regime_detector.py        — 市場レジーム判定（ma200 + マクロセンチメント合成）
- tools/
  - paper_verification_report.py — Paper Trading 検証レポート生成
- utils/
  - logging_setup.py          — 共通ログ設定
  - process_priority.py       — プロセス優先度 / CPU affinity 設定

data/                         — デフォルトで使用する DB / フラグ / pid ファイル配置想定
logs/                         — ログ出力先（デフォルト）

---

## 開発 / テストに関するヒント

- 個別関数（research.calc_momentum など）は DuckDB の接続を受け取る純粋関数として設計されています。テスト時はメモリ上の DuckDB を使ってテストできます。
- AI 呼び出し部（kabusys.ai.news_nlp._call_openai_api など）はユニットテストでパッチしやすいよう分離されています。外部 API 呼び出しはモックしてテストしてください。
- monitoring_db.init_monitoring_db は冪等であり、既存 DB への簡単なマイグレーション（カラム追加）を行います。

---

README は以上です。追加で「運用手順（systemd / Supervisor の service ファイル例）」「テスト手順」「詳細な API ドキュメント」などが必要であれば目的に合わせて追記します。