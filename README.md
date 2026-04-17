# KabuSys

日本株向け自動売買 / 研究プラットフォームの軽量実装（モジュール群の抜粋）。  
本リポジトリは、以下を主に含みます：取引実行エンジンの起動スクリプト、監視サブシステム、ポートフォリオ構築・ポジションサイジング、ファクター計算・リサーチユーティリティ、AI（OpenAI）を用いたニュースセンチメント評価ツールなど。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買に関わる以下の責務を分離して実装したモジュール群です。

- ExecutionEngine（発注・リスク管理・約定整合）
- Monitoring（システム稼働性、データ鮮度、注文監視、Kill Switch）
- Portfolio（候補選定、重み計算、ポジションサイズ決定、セクター制限）
- Research（DuckDB を用いたファクター計算・特徴量解析）
- AI（OpenAI を使ったニュースのセンチメントスコアリング、市場レジーム判定）
- CLI ツール（.env ウィザード、設定検証、Paper Trading レポート作成 等）

設計上の主な方針：
- 環境変数 / .env を中心とした設定管理
- 本番用設定とペーパートレード用 DB を明確に分離
- DuckDB を分析用 DB、SQLite を監視・履歴用 DB に使用
- AI 呼び出しはフェイルセーフ（失敗時はフォールバック）で実装

---

## 機能一覧

主要機能（抜粋）：

- 実行系
  - run_execution: ExecutionEngine を起動（本番 / paper_trading 判別）
  - BrokerClientFactory による本物／モックブローカー切替
  - リスク管理（ポジション制限、最大投下率、サーキットブレーカー等）
- 監視系
  - run_monitoring: SystemMonitor のポーリングループ起動（MONITOR_POLL_INTERVAL）
  - SystemMonitor / TradeMonitor / RiskMonitor / MonitoringEngine
  - MonitoringDB: system_status / trade_logs / positions / risk_logs / dashboard テーブル
  - KillSwitch: 条件により data/kill.flag を書き込んで ExecutionEngine を停止
  - AlertManager: LINE Messaging API での通知（トークン未設定時はログ出力）
- ポートフォリオ構築
  - 候補選定、等重／スコア重み、セクターキャップ、レジーム乗数
  - ポジションサイズ計算（lot 単位で丸め、aggregate cap のスケーリング）
- リサーチ
  - Momentum / Volatility / Value ファクター計算（DuckDB 上の prices_daily/raw_financials）
  - 将来リターン、IC（スピアマン）計算、ファクター統計サマリ
- AI（OpenAI）
  - news_nlp.score_news: ニュースを集約して OpenAI でセンチメント推計、ai_scores に書き込み
  - regime_detector.score_regime: ETF MA とマクロニュースの LLM スコアを合成して市場レジーム判定
  - リトライ・バックオフ、レスポンス検証、出力クリップ等の保護実装
- ツール
  - config_setup: 対話式 .env ウィザード（初期作成・更新）
  - validate_config: .env と config/*.yaml の簡易検証
  - tools.paper_verification_report: Paper Trading DB から検証レポートを生成

---

## セットアップ手順

前提：
- Python 3.9+（typing 機能を利用）
- システムに sqlite3 は標準で含まれます

1. リポジトリをクローン／展開して、プロジェクトルートから作業する（src 配下がパッケージ実装場所）。
2. 仮想環境を作成・有効化（推奨）：
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）
3. 必要パッケージをインストール（最低限）：
   - pip install duckdb psutil openai requests
   - （YAML 検証を使う場合）pip install pyyaml
   - ※ requirements.txt は本コードに含まれていないため、上記を参考に追加してください。
4. .env を用意する
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - または手動で .env を作成（プロジェクトルート）：
     - 主要な環境変数（例）:
       - JQUANTS_REFRESH_TOKEN=your_token
       - KABU_API_PASSWORD=your_password
       - KABUSYS_ENV=development|paper_trading|live
       - DUCKDB_PATH=data/kabusys.duckdb
       - SQLITE_PATH=data/monitoring.db
       - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
       - OPENAI_API_KEY=sk-...
       - LINE_CHANNEL_ACCESS_TOKEN=...
       - LINE_USER_ID=...
       - LOG_LEVEL=INFO
       - KILL_FLAG_CLEAR_ON_START=0
5. DB／データディレクトリ
   - デフォルトでは data/ 以下に sqlite/duckdb/flag/pid ファイルが作られます。存在しない親ディレクトリは起動時に自動作成される場合がありますが、必要に応じて手動で作成してください。

注意点:
- KABUSYS_ENV=paper_trading の場合、run_execution は MockBrokerClient を使用し、paper_trading 専用 SQLite（PAPER_TRADING_SQLITE_PATH）に記録します。本番 DB との完全分離が担保されています。
- OpenAI を利用する機能は OPENAI_API_KEY が必須です（引数で渡すことも可能）。

---

## 使い方

主要な CLI / スクリプト:

- 環境設定ウィザード（.env 作成 / 更新）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告も FAIL 扱い（exit 1）

- 実行エンジン起動（ExecutionEngine）
  - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading の場合はモックブローカーを使用し、PAPER_TRADING_SQLITE_PATH に記録
    - data/execution.pid を作成して PID 管理
    - 停止は data/stop_requested.flag を作成することで実行中スレッドに通知（run_execution と run_monitoring はこのフラグを監視）
    - kill スイッチは data/kill.flag を書き込むことで ExecutionEngine を強制停止させる仕組み（Monitoring が判定して書き込む）

- 監視ループ起動（SystemMonitor のポーリング）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を変更可能（デフォルト 60）
  - Monitoring は KABUSYS_ENV に関わらず本番 sqlite_path を使用（監視データは共通の監視 DB に保存）
  - system_status 等のログは monitoring DB（デフォルト data/monitoring.db）に保存

- Paper Trading 検証レポート（SQLite DB 参照）
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db で DB パスを指定可能（環境変数 PAPER_TRADING_SQLITE_PATH より優先）

- AI 関連（Python API 呼び出し）
  - ニュース評価:
    - from kabusys.ai.news_nlp import score_news
    - score_news(conn, target_date, api_key=None)
    - DuckDB 接続を渡し、target_date を指定して ai_scores テーブルへ書き込み
  - レジーム判定:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(conn, target_date, api_key=None)
  - いずれも OPENAI_API_KEY が必要（api_key 引数で代替可能）

プロセス優先度:
- run_execution / run_monitoring は起動時に set_process_priority("high") を呼び出し、一部 OS で優先度を上げます（psutil を使用）。権限や OS により失敗する場合はログに警告が出ます。

停止フラグ:
- data/stop_requested.flag — run_execution / run_monitoring が起動時とループ中に参照して停止判定に使用
- data/kill.flag — KillSwitch が条件成立時に書き込む（ExecutionEngine の停止トリガー）

ログ:
- 標準の logging モジュールを使用。LOG_LEVEL 環境変数で制御可能（INFO デフォルト）。

---

## 重要な環境変数（抜粋・デフォルト値）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
- DUCKDB_PATH — デフォルト: data/kabusys.duckdb
- SQLITE_PATH — デフォルト: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH — デフォルト: data/paper_trading.db
- OPENAI_API_KEY — OpenAI を使う機能で必須
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — AlertManager 用（任意）
- LOG_LEVEL — DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START — 本番での自動クリア防止（0 推奨）

.env は .git にコミットしないでください（秘匿情報を含みます）。

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 以下の主要モジュールとファイル（抜粋）です。

- src/
  - kabusys/
    - __init__.py
    - config.py                        — 環境変数 / .env の自動ロードと Settings クラス
    - config_setup.py                  — .env 対話式ウィザード（CLI）
    - validate_config.py               — 起動前設定検証 CLI
    - run_execution.py                 — ExecutionEngine 起動スクリプト
    - run_monitoring.py                — SystemMonitor ポーリングループ起動スクリプト
    - tools/
      - __init__.py
      - paper_verification_report.py   — Paper Trading レポート生成スクリプト
    - execution/                        — Execution エンジン関連（OrderManager 等）
      - (複数ファイル: broker_factory, execution_engine, order_manager, order_repository, reconciler, risk_manager, order_record など)
    - monitoring/
      - monitoring_db.py               — SQLite のテーブル作成・永続化 API
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
      - __init__.py
    - research/
      - factor_research.py
      - feature_exploration.py
      - __init__.py
    - ai/
      - news_nlp.py                     — ニュースセンチメント（OpenAI）
      - regime_detector.py              — マーケットレジーム判定（OpenAI）
      - __init__.py
    - monitoring/                       — （監視関連、一部重複上記）
    - utils/
      - process_priority.py             — プロセス優先度・CPU affinity ユーティリティ
      - __init__.py

（実際のファイルは上記以外にも存在します。README は主要な設計と実行方法のガイドです。）

---

## 追加のメモ・運用上の注意

- 本番運用時（KABUSYS_ENV=live）は設定ミスが重大な影響を及ぼします。validate_config を必ず実行して警告／エラーを確認してください。
- OpenAI を使う処理は外部 API 呼び出しのため、レート制限や費用が発生します。API キーおよび呼び出し頻度には注意してください。
- データ鮮度チェック: SystemMonitor は DuckDB の prices_daily の最終日付を参照し、最大許容差（現在実装: 3 日）を超えると警告します。
- ログや監視 DB のローテーション／バックアップ戦略は運用側で用意してください（本実装ではローテーション機能は含みません）。
- 単体テストや CI の設定は本コード抜粋には含まれていません。ユニットテストを書く際は外部 API（OpenAI 等）をモックしてください（既に _call_openai_api を patch しやすい設計になっています）。

---

もし README に追記してほしい具体項目（例：詳しい .env のテンプレート、実行例のログ、API のシーケンス図、開発フロー、テスト方法など）があれば教えてください。必要に応じてサンプル .env やコマンド例を追加します。