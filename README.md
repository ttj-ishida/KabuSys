# KabuSys

日本株向けの自動売買システム（ライブラリ／起動スクリプト群）の README です。  
このドキュメントはリポジトリ内の主要スクリプトとモジュール（実行・監視・研究・ポートフォリオ構築・AI連携等）を使うための概要と手順をまとめています。

---

## プロジェクト概要

KabuSys は以下の機能群を備えた日本株自動売買向けフレームワークです。

- 注文実行エンジン（ExecutionEngine）とブローカー抽象化（paper/live 切替）
- システム監視（SystemMonitor / MonitoringEngine）と Kill Switch（危険時の自動停止）
- リスク監視（ドローダウン・ポジション数監視）
- ポートフォリオ構築（候補選定・重み計算・ポジションサイズ計算等）
- 研究用モジュール（ファクター計算、将来リターン、IC、統計サマリ）
- AI 連携（OpenAI を用いたニュースのセンチメント評価、レジーム判定）
- 運用支援ツール（対話式 .env ウィザード、設定検証、ペーパートレード検証レポート）

主要スクリプト（起動ポイント）
- run_execution.py — ExecutionEngine 起動（本番 / ペーパー切替）
- run_monitoring.py — 監視用ポーリングループ起動
- config_setup.py — .env 対話ウィザード（初期設定）
- validate_config.py — 設定検証 CLI
- tools/paper_verification_report.py — ペーパートレード検証レポート生成

---

## 機能一覧（主要）

- 環境設定読み込み（.env、自動ロード機能）
- DB：SQLite（監視 / ペーパートレード）・DuckDB（分析）
- Logging：統一的なログ設定（コンソール + 日次ローテーションファイル）
- プロセス優先度設定・CPU affinity 操作ユーティリティ
- 監視機能：
  - システム状態（CPU/MEM/DISK/プロセス生存）とデータ鮮度の監視
  - トレードログ監視（滞留注文、異常約定等）
  - リスク監視（ドローダウン / ポジション上限）
  - Kill Switch（data/kill.flag）による ExecutionEngine 停止
- ポートフォリオ構築：候補選定、等スコア/スコア加重、リスクベースの発注量算定、セクター制約、レジーム乗数
- 研究用：Momentum/Value/Volatility 等のファクター計算、IC・統計量計算
- AI：OpenAI（gpt-4o-mini）を使ったニュースセンチメント、レジーム判定（フェイルセーフ設計）
- 運用ツール：環境設定ウィザード、設定検証、ペーパートレード検証レポート

注意点：
- run_monitoring は KABUSYS_ENV にかかわらず「本番用の sqlite_path」を使用して監視 DB に接続します（設計上の仕様）。
- run_execution は KABUSYS_ENV=paper_trading の際に MockBrokerClient を使用し、ペーパー用 DB（data/paper_trading.db）に記録します（本番 DB と分離）。

---

## セットアップ手順

前提
- Python 3.10 以上（コード内で `X | None` 型等を使用）
- Git、端末操作の基本知識

1. リポジトリをクローン
   - git clone ...

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージをインストール
   - 代表的な依存ライブラリ（requirements.txt がない場合の例）:
     - duckdb
     - psutil
     - openai
     - PyYAML（任意。validate_config の YAML 検証に使用）
   - インストール例：
     - pip install duckdb psutil openai pyyaml

4. データ / ログ ディレクトリの準備（自動生成されることもありますが手動で作ると権限トラブルを避けられます）
   - mkdir -p data logs

5. .env の準備
   - 対話式ウィザードを使う（推奨）:
     - python -m kabusys.config_setup
   - あるいは .env を手動で作成（後述の環境変数参照）

6. 設定検証（起動前確認）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります

7. DB 初期化
   - run_execution / run_monitoring 起動時に必要テーブルは自動で作成されます（init_monitoring_db）。

---

## 環境変数（主要）

必須
- JQUANTS_REFRESH_TOKEN — J-Quants API リフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード

主要（任意／デフォルトあり）
- KABUSYS_ENV — 実行環境: development / paper_trading / live（デフォルト: development）
- DUCKDB_PATH — DuckDB ファイル（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL — ログレベル（例: INFO）
- LOG_DIR — ログ保存ディレクトリ（デフォルト: logs/）
- OPENAI_API_KEY — OpenAI API キー（AI 機能を使う際に必要）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — LINE 通知（任意）
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト 60）
- PAPER_FILL_MODE — ペーパートレードの約定挙動（instant/partial/never/reject）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアする (0/1、本番では 0 推奨)

簡単な .env の最小例（例示。実運用ではシークレットは必ず保護してください）
- KABUSYS_ENV=development
- JQUANTS_REFRESH_TOKEN=your_jquants_token_here
- KABU_API_PASSWORD=your_kabu_password_here
- OPENAI_API_KEY=your_openai_key_here
- DUCKDB_PATH=data/kabusys.duckdb
- SQLITE_PATH=data/monitoring.db
- LOG_LEVEL=INFO
- KILL_FLAG_CLEAR_ON_START=0

---

## 使い方（起動 / 運用）

基本的にパッケージモジュールとして実行します（プロジェクトルートから）:

- 環境ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳格モード: python -m kabusys.validate_config --strict

- 監視（Monitoring）起動
  - python -m kabusys.run_monitoring
  - 環境変数でポーリング間隔を調整: MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - 監視は KABUSYS_ENV にかかわらず sqlite_path を参照します（monitoring 用 DB）

  停止手順:
  - プロセスを Ctrl+C するか、プロジェクトルート/data/stop_requested.flag を作成するとループが検知して終了します。

- 実行エンジン（ExecutionEngine）起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使い、データは PAPER_TRADING_SQLITE_PATH に記録されます
  - 起動前に data/stop_requested.flag が存在すると起動をスキップします
  - 実行中に停止させたい場合は data/stop_requested.flag を作成（run_execution が検知して engine.stop() を呼びます）

- ペーパートレード検証レポート生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB を明示する場合: python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- AI 関連（ニューススコアリング / レジーム判定）
  - 必要に応じて OPENAI_API_KEY を設定して利用します
  - ニューススコアリング関数: kabusys.ai.score_news（ライブラリ API）
  - レジーム判定関数: kabusys.ai.regime_detector.score_regime

ログ
- デフォルトでは logs/<app_name>.log に日次ローテーション保存されます（30世代保持）
- コンソールにも出力されます（stdout を使用）

停止フラグと Kill Switch
- 運用中に重大リスク（ドローダウン / ポジション上限など）が検出されると、KillSwitch が data/kill.flag を書き込み、ExecutionEngine の停止を促します
- KILL_FLAG_CLEAR_ON_START=1 を使うと起動時に自動クリアできますが、本番では推奨されません

---

## ディレクトリ構成（主なファイル/モジュール）

リポジトリ構成（src/kabusys 以下を抜粋）

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数読み込み・Settings
  - config_setup.py           — .env 対話式ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — 監視ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート
  - ai/
    - news_nlp.py             — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py      — レジーム判定（MA + マクロセンチメント）
  - monitoring/
    - monitoring_db.py        — SQLite 監視テーブル操作
    - system_monitor.py       — システム・データ鮮度監視
    - trade_monitor.py        — （トレード監視ロジック）
    - risk_monitor.py         — ドローダウン・ポジション監視
    - kill_switch.py          — Kill Switch 実装（kill.flag 書込み）
    - monitoring_engine.py    — 各モニタを束ねるエンジン
    - alert_manager.py        — （通知管理。LINE など）
  - execution/
    - execution_engine.py     — ExecutionEngine 本体
    - broker_factory.py       — BrokerClient 抽象 / Mock 切替
    - order_manager.py
    - order_repository.py
    - risk_manager.py
    - reconciler.py
  - portfolio/
    - portfolio_builder.py    — 候補選定・重み計算
    - position_sizing.py      — 発注株数・スケーリング
    - risk_adjustment.py      — セクター制約・レジーム乗数
  - research/
    - factor_research.py      — Momentum/Value/Volatility 等
    - feature_exploration.py  — 将来リターン / IC / 統計サマリ
  - utils/
    - logging_setup.py        — 統一ロギング設定
    - process_priority.py     — プロセス優先度・CPU affinity
  - data/                     — 実行時生成 DB / フラグファイル（README 参照）
  - config/                   — 各種 YAML 設定ファイル（生成/配置想定）

---

## 開発・運用上の注意

- シークレット情報（APIキー・パスワード）は .env を使って管理し、決してリポジトリにコミットしないでください。
- 本番環境（KABUSYS_ENV=live）では KILL_FLAG_CLEAR_ON_START=0 を推奨します（誤って Kill Switch を無効化するのを防ぐため）。
- AI 呼び出しには OpenAI のレート制限やエラーが発生するため、各モジュールはリトライ・フォールバックを組み込んでいますが、API キー・料金・利用制限に注意してください。
- DuckDB / SQLite のファイルパスは env で上書き可能です。バックアップやアクセス権管理に注意してください。
- run_monitoring は監視用 DB（SQLITE_PATH）へ接続します。監視処理は監視テーブルを初期化（冪等）します。

---

ご不明点や README に追加してほしい内容（例：コマンドのより詳細な実行例、各設定ファイルの説明、設計ドキュメントへの参照）は教えてください。必要に応じてサンプル .env のテンプレートや運用手順（systemd / Supervisor 起動例）も追記できます。