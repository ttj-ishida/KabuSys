# KabuSys

日本株向けの自動売買システム（ライブラリ / 実行スクリプト群）。  
バックテストや研究用のファクター計算、ポートフォリオ構築、発注・リスク管理、監視・アラート、AI を用いたニュースセンチメント評価などの機能を備えています。

バージョン: 0.1.0

---

## 概要

KabuSys は以下の責務を持つモジュール群から構成されています。

- 実行エンジン（ExecutionEngine）: ブローカークライアントを介した発注処理・注文管理・リスク管理
- 監視（Monitoring）: システム状態、注文推移、リスク（ドローダウン・ポジション数）をポーリング監視し、Kill Switch を発動
- ポートフォリオ構築: 候補選定・重み計算・ポジションサイズ算出・セクター上限適用
- リサーチ: DuckDB 上の時系列データを用いたファクター計算・特徴量解析
- AI サービス: ニュースの NLP（OpenAI）を用いた銘柄センチメント評価、マクロセンチメントを併用したレジーム判定
- ユーティリティ: 設定読み込み（.env）、ログ設定、プロセス優先度設定など
- CLI ツール: .env ウィザード、設定検証、Paper Trading 検証レポート生成 など

---

## 主な機能一覧

- 設定管理（kabusys.config）
  - .env 自動読み込み（プロジェクトルート基準）
  - Settings クラスから環境変数を型付きで取得
- 起動ヘルパー
  - config_setup: 対話式 .env ウィザード（python -m kabusys.config_setup）
  - validate_config: 起動前チェック（python -m kabusys.validate_config）
- Execution
  - 本番 / Paper Trading 切り替え（KABUSYS_ENV）
  - Paper Trading 時は MockBrokerClient を使用し、専用 DB（data/paper_trading.db）に分離
  - PID ファイル、停止フラグ連携
- Monitoring
  - SystemMonitor / TradeMonitor / RiskMonitor を統合した MonitoringEngine
  - SQLite に監視ログを永続化（data/monitoring.db）
  - Kill Switch（条件に応じて data/kill.flag を書き込み）
  - ポーリング間隔は環境変数で上書き可能
- Portfolio モジュール（純粋関数）
  - 候補選定、等金額/スコア加重、リスクベースのポジション決定、セクター制限、レジーム乗数
- Research（DuckDB ベース）
  - モメンタム・ボラティリティ・バリュー系ファクター、IC 計算、統計サマリ
- AI（OpenAI）
  - ニュースの銘柄別センチメントを LLM で算出し ai_scores に保存
  - マクロニュース + ETF MA200 を組み合わせて市場レジーム判定
- ツール
  - paper_verification_report: Paper Trading の稼働・約定・レイテンシ等の検証レポート生成

---

## 要件 (推奨)

- Python >= 3.10（typing の | 演算子を使用）
- 推奨パッケージ（pip でインストール）
  - duckdb
  - psutil
  - openai
  - PyYAML（config YAML の内容検証に任意で使用）
- 他: sqlite3 標準モジュール、logging など標準ライブラリ

requirements.txt がない場合は手動インストール例:
pip install duckdb psutil openai PyYAML

---

## セットアップ手順

1. リポジトリをクローン / 展開
2. Python 仮想環境を作成して有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール
   - pip install duckdb psutil openai PyYAML
4. 対話式で .env を作成
   - python -m kabusys.config_setup
   - 主要な環境変数（例）:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - KABUSYS_ENV: development / paper_trading / live
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
     - OPENAI_API_KEY（AI 機能を使う場合）
5. 設定検証（任意）
   - python -m kabusys.validate_config
   - 警告をエラー扱いにする場合: python -m kabusys.validate_config --strict
6. データディレクトリや logs ディレクトリは自動作成されますが、手動で用意しても構いません。

注意: 自動 .env ロードを無効化したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト時など）。

---

## 実行方法（使い方）

基本的に Python モジュールとして実行します。実行中のログは stdout と logs/<app>.log（デフォルト）に出力されます。

- ExecutionEngine を起動
  - python -m kabusys.run_execution
  - 備考:
    - KABUSYS_ENV=paper_trading のときは MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH に記録します（本番 DB と分離）。
    - 起動時に data/stop_requested.flag が存在すると起動を行わず終了します。
    - 起動中に同ファイルが作成されると安全に停止します。
    - 実行時の PID ファイル: data/execution.pid（設定で上書き可能）

- Monitoring を起動
  - python -m kabusys.run_monitoring
  - 備考:
    - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可能（デフォルト 60 秒）。
    - 監視は常に本番 sqlite_path（Settings.sqlite_path）を使用します（環境に依らず）。
    - 停止は data/stop_requested.flag の作成で検知して終了します。

- .env 作成ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗扱い（exit 1）

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from YYYY-MM-DD --to YYYY-MM-DD
  - DB を直接指定する場合: --db PATH
  - 環境変数: PAPER_TRADING_SQLITE_PATH でデフォルト DB パスを上書き可

- AI 機能（ニュース NLP / レジーム判定）
  - OPENAI_API_KEY が必要。該当関数を呼び出す際に api_key 引数でも指定可。
  - 例: kabusys.ai.score_news を用いて指定日分のニューススコアを生成

---

## 停止・Kill Switch の仕様

- 停止フラグ（外部からの停止要求）
  - ファイル: data/stop_requested.flag
  - run_execution/run_monitoring はこのファイルの存在をチェックし、検出時に安全に停止します。

- Kill Switch（自動停止）
  - 条件（例）: ドローダウン閾値超過、ポジション数上限超過など
  - 発動時に data/kill.flag を書き込み、ExecutionEngine に対して停止シグナルを送ります（KillSwitch モジュール）。
  - kill.flag の自動クリアは KILL_FLAG_CLEAR_ON_START 環境変数で制御（0/1、デフォルト 0。本番では 0 推奨）。

---

## 主要な環境変数（抜粋）

- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）
- LOG_LEVEL（DEBUG/INFO/...、デフォルト: INFO）
- OPENAI_API_KEY（AI 機能で使用）
- MONITOR_POLL_INTERVAL（監視ポーリング間隔（秒））
- PAPER_FILL_MODE（paper_trading の約定モード: instant | partial | never | reject）

詳細は kabusys.config.Settings のプロパティを参照してください。

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 以下の主要構成です（抜粋）:

- kabusys/
  - __init__.py
  - config.py                — 環境変数/設定管理
  - config_setup.py          — .env 対話ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor 起動スクリプト
  - utils/
    - logging_setup.py       — ログ設定ユーティリティ
    - process_priority.py    — プロセス優先度 / CPU affinity
  - execution/                — 発注関連コンポーネント（Engine, BrokerFactory, OrderManager 等）
  - monitoring/
    - monitoring_db.py       — SQLite 永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
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
    - news_nlp.py             — ニュース NLP スコアリング
    - regime_detector.py      — マクロ + MA200 によるレジーム判定
  - tools/
    - paper_verification_report.py

data/ や logs/ ディレクトリは実行時に自動作成されます（パスは .env で上書き可能）。

---

## 開発・デバッグのヒント

- ログ設定は kabusys.utils.logging_setup.setup_logging() で統一されています。ログ保存先は LOG_DIR 環境変数またはデフォルト logs/。
- .env の自動読み込みはプロジェクトルート（.git または pyproject.toml を基準）を探索して行われます。テストで自動ロードを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB を使うリサーチコードは prices_daily / raw_financials / raw_news 等のテーブルを前提としています。テーブルスキーマに合うデータを用意してください。
- OpenAI 周りはネットワークやレート制限に配慮したリトライロジックを備えています。API キーは環境変数 OPENAI_API_KEY に設定してください。
- Paper Trading を検証する際は paper_verification_report を利用すると稼働率、約定成功率、レイテンシ等を簡単にチェックできます。

---

## トラブルシューティング（よくある問題）

- 「環境変数が未設定です」と出る
  - .env を作成していない、または自動ロードが無効化されている可能性があります。python -m kabusys.config_setup を実行するか、環境変数を設定してください。
- DuckDB / SQLite ファイルが見つからない
  - デフォルトは data/kabusys.duckdb、data/monitoring.db、data/paper_trading.db。設定で別パスを指定している場合はそのファイルを確認してください。
- OpenAI 呼び出しで失敗する
  - OPENAI_API_KEY が正しいか、IP/ネットワークからのアクセス制限、レート制限や API のステータスを確認してください。コード側でリトライする設計ですが、キー未設定はエラーになります。
- プロセスの優先度設定 (psutil) で権限エラー
  - 一部のシステムでは管理者権限が必要です。失敗した場合は警告ログが出て処理は継続します。

---

必要であれば README に実行例や設定例のテンプレート（.env.example）を追加します。どの情報をより詳しく載せたいか教えてください。