# KabuSys

日本株自動売買システムのコードベース（ドキュメント版 README）。

この README はリポジトリ内のソースコードに基づき作成しています。実行前に .env を作成し、必要な依存ライブラリをインストールしてください。

---

## プロジェクト概要

KabuSys は日本株の自動売買・リサーチ・監視を目的としたモジュール群です。主な用途は以下の通りです。

- 戦略ファクター計算（research）
- ポートフォリオ構築とポジションサイジング（portfolio）
- 実際の執行エンジン（execution）と注文管理
- 監視（monitoring）：システム状態、注文滞留、リスク監視、Kill Switch
- AI 補助（ai）：ニュースのセンチメントや市場レジーム判定（OpenAI を利用）
- ペーパートレード検証ツール（tools）

設計方針の一例：
- DuckDB を分析用 DB として使用（prices_daily / raw_financials 等）
- SQLite を監視・発注ログ用に使用（monitoring.db / paper_trading.db）
- 環境依存設定は .env / 環境変数で管理
- 本番（live）・ペーパー（paper_trading）・開発（development）を環境切替可

---

## 主な機能一覧

- 環境設定ウィザード（config_setup.py）
  - 対話形式で .env を生成 / 更新
- 設定検証 CLI（validate_config.py）
  - .env と config/*.yaml の基本チェック
- 実行エンジン起動スクリプト（run_execution.py）
  - KABUSYS_ENV=paper_trading のときは MockBroker を使用し DB を分離
- 監視ループ起動スクリプト（run_monitoring.py）
  - SystemMonitor を定期ポーリングして監視ログを保存
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（デフォルト 60 秒）
- 監視コンポーネント（monitoring/）
  - SystemMonitor: CPU/メモリ/Disk、プロセス・データ鮮度
  - TradeMonitor: 注文滞留、約定価格異常
  - RiskMonitor: ドローダウン・ポジション上限監視
  - KillSwitch / AlertManager連携（Kill Flag による実行停止）
  - MonitoringDB: SQLite スキーマ初期化・読み書き
- ポートフォリオ（portfolio/）
  - 候補選定、等分/スコア重み、ポジションサイジング、セクター制限、レジーム乗数
- リサーチ（research/）
  - ファクター計算（Momentum / Volatility / Value）
  - 将来リターン・IC 計算・統計サマリー
- AI モジュール（ai/）
  - news_nlp: ニュースをまとめて OpenAI に問い合わせ、銘柄別センチメントを ai_scores に書き込み
  - regime_detector: ETF MA とマクロニュースを合成してレジーム判定
- ツール（tools/）
  - paper_verification_report: ペーパートレード DB を解析して PASS/FAIL 判定レポートを生成

---

## セットアップ手順

1. Python（3.9 以上推奨）をインストール

2. 必要パッケージをインストール
   - 本リポジトリに requirements.txt がない場合は最低下記を入れてください（実際の環境に合わせて追加）。
     - duckdb
     - psutil
     - openai
     - pyyaml（設定検証で YAML 検証を行う場合）
   - 例:
     - pip install duckdb psutil openai pyyaml

3. プロジェクトルートに移動して .env を作成
   - 対話式ウィザードを使用（推奨）:
     - python -m kabusys.config_setup
   - 手動で作成する場合は .env.example を参考にし、必要な環境変数を設定してください。

4. 主要な環境変数（例）
   - 必須:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 推奨/設定例:
     - KABUSYS_ENV=development|paper_trading|live（デフォルト development）
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
     - LOG_LEVEL=INFO
     - OPENAI_API_KEY=（AI 機能を使う場合）
     - PAPER_FILL_MODE=instant|partial|never|reject（paper_trading 時）
     - MONITOR_POLL_INTERVAL=60（監視ポーリング間隔秒）

5. DB 初期化
   - 監視用 SQLite テーブルは起動スクリプトが接続時に自動作成（init_monitoring_db）します。
   - DuckDB テーブル（prices_daily 等）はデータ投入処理 / スクリプトで準備してください。

---

## 使い方（代表的なコマンド）

- 環境設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳密モード（警告も失敗扱い）:
    - python -m kabusys.validate_config --strict

- 実行エンジン起動（ExecutionEngine）
  - python -m kabusys.run_execution
  - 注意:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し data/paper_trading.db に記録します（本番 DB と分離）。
    - 実行中に停止させるには data/stop_requested.flag を作成してください（stop フラグ検知で安全終了）。

- 監視ループ起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒で指定（デフォルト 60）
    - 0 以下や不正な値は無効でデフォルトにフォールバック
  - 監視は常に本番の sqlite_path を使用（環境に依らず監視 DB は本番パス）

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - デフォルト DB パスは PAPER_TRADING_SQLITE_PATH 環境変数または data/paper_trading.db

- AI 機能（例）
  - news_nlp.score_news / regime_detector.score_regime は DuckDB 接続と target_date、OPENAI_API_KEY を渡して実行する関数 API です。
  - OpenAI を使用するため、OPENAI_API_KEY を設定してください。API 呼び出しは失敗耐性（リトライ・フォールバック）実装あり。

---

## 重要な挙動・注意点

- .env 自動ロード
  - config.py はプロジェクトルート（.git または pyproject.toml を基準）を探索し、.env を自動で読み込みます。
  - 自動ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

- 環境（KABUSYS_ENV）
  - development / paper_trading / live のいずれかが有効値です。
  - live に設定すると本番動作になります。LINE 通知等の設定が適切かを validate_config で確認してください。

- Kill Switch / 停止フラグ
  - KillSwitch は data/kill.flag を書き込んで ExecutionEngine に停止シグナルを送ります。
  - Execution の停止や起動制御には data/stop_requested.flag などのフラグファイルを使用する仕組みがあります（スクリプト内で参照）。

- データベース
  - 監視用の SQLite スキーマは init_monitoring_db により自動作成・マイグレーションされます（冪等）。
  - ペーパートレードは paper_sqlite_path を使い本番 DB と分離。

- OpenAI の扱い
  - news_nlp / regime_detector は外部 API（OpenAI）へ接続します。API キーは環境変数 OPENAI_API_KEY、または関数引数で渡してください。
  - API 呼び出しはリトライ、バックオフ、レスポンス検証を含む実装です。失敗時は安全にフォールバックしますが、API キー未設定時は例外になります。

---

## ディレクトリ構成（主なファイル）

リポジトリの主要なディレクトリ/ファイル（src/kabusys 以下を抜粋）:

- src/kabusys/
  - __init__.py
  - config.py               — 環境・設定読み込みロジック
  - config_setup.py         — .env 対話式ウィザード
  - validate_config.py      — 設定検証 CLI
  - run_execution.py        — ExecutionEngine 起動スクリプト
  - run_monitoring.py       — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート
  - ai/
    - news_nlp.py           — ニュース NLP（OpenAI でセンチメント）
    - regime_detector.py    — 市場レジーム判定（MA + マクロ NLP）
  - monitoring/
    - monitoring_db.py      — SQLite スキーマ・CRUD（MonitoringDB）
    - monitoring_engine.py  — 各 Monitor を束ねる Engine
    - system_monitor.py     — システム状態・データ鮮度監視
    - trade_monitor.py      — 注文滞留・約定異常監視
    - risk_monitor.py       — ドローダウン・ポジション上限監視
    - kill_switch.py        — Kill Switch ロジック（flag ファイル）
    - alert_manager.py      — （アラート送信ロジック、未表示）
  - portfolio/
    - portfolio_builder.py  — 候補選定・重み計算
    - position_sizing.py    — 株数決定・リスク制限
    - risk_adjustment.py    — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py    — Momentum / Value / Volatility 計算
    - feature_exploration.py— 将来リターン・IC・統計処理
  - utils/
    - process_priority.py   — プロセス優先度 / CPU affinity ユーティリティ
  - monitoring_db, execution, その他: 発注関連や engine 実装ファイル群（参照多数）

（上記は抜粋です。詳細はソースツリーを参照してください）

---

## 開発時のヒント

- ログレベルは .env の LOG_LEVEL で制御できます。
- config.validate_config を起動前に実行して基本的な環境整合性をチェックしてください。
- 開発・テスト時は KABUSYS_ENV=paper_trading を使うと本番発注を防げます。
- OpenAI／外部 API 呼び出し部分はモックしやすいように設計されています（テストでの差し替えを推奨）。

---

## よく使うコマンドまとめ

- .env 作成: python -m kabusys.config_setup
- 設定検証: python -m kabusys.validate_config
- Execution 起動: python -m kabusys.run_execution
- Monitoring 起動: python -m kabusys.run_monitoring
- Paper 検証レポート: python -m kabusys.tools.paper_verification_report --from YYYY-MM-DD --to YYYY-MM-DD

---

README に含めるべき追加の情報（例: 実行例、詳細な API ドキュメント、サンプル .env、unit tests、CI 設定等）があれば教えてください。必要に応じて追記・整形します。