# KabuSys — 日本株自動売買システム

この README はリポジトリ内の主要スクリプト／モジュールに基づいて作成した日本語ドキュメントです。開発・テスト・運用のためのセットアップ手順、使い方、ディレクトリ構成などをまとめています。

---

## プロジェクト概要

KabuSys は日本株向けの自動売買システムのコードベースです。以下の機能群を含みます。

- 戦略（ファクター計算・リサーチ）とポートフォリオ構成（候補選定・重み付け・株数決定）
- 注文管理／ExecutionEngine（出力・リスク管理・reconciler 等）
- 監視サブシステム（システム状態、注文滞留、リスク監視、Kill Switch）
- Paper Trading 向けの分離された DB / モックブローカー動作
- News NLP / Regime Detector（OpenAI を使ったセンチメント評価）
- 運用支援ツール（.env ウィザード、設定検証、Paper Trading レポート生成 等）

設計方針の一部:
- DB は DuckDB（分析用）と SQLite（監視・注文ログ）を併用
- Paper Trading は本番 DB と完全分離（デフォルト: data/paper_trading.db）
- 時刻の扱いはルックアヘッドバイアスを避ける（関数は date 引数を受け取る等）
- 外部 API 失敗はフェイルセーフで扱う（フォールバックやスキップ）

---

## 主な機能一覧

- 環境設定ウィザード: python -m kabusys.config_setup
- 設定検証 CLI: python -m kabusys.validate_config [--strict]
- ExecutionEngine 起動: python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、paper_trading 用 SQLite に記録
- Monitoring 起動: python -m kabusys.run_monitoring
  - ポーリングで system / trade / risk の監視を行い、必要に応じて kill.flag を作成
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）
- Paper Trading レポート: python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD --to YYYY-MM-DD --db PATH]
- ファクター計算（research/）: momentum, volatility, value 等
- ポートフォリオ構築（portfolio/）: 候補選定・重み付け・ポジションサイズ計算・セクター制限・レジーム乗数
- AI ベース機能（ai/）:
  - news_nlp.score_news: raw_news を OpenAI にかけて銘柄別スコアを ai_scores テーブルに書き込み
  - regime_detector.score_regime: ma200 とマクロニュースを合成して market_regime を判定・保存
  - 両者は OpenAI API キー（OPENAI_API_KEY）が必要
- ユーティリティ:
  - process_priority（プロセス優先度設定）
  - monitoring_db（監視ログの永続化層）
  - config（.env 自動読み込み、Settings クラス）

---

## セットアップ手順（ローカル開発向け）

1. Python の準備
   - 推奨: Python 3.9+（ソース内に厳密なバージョン指定はありません）
2. 依存パッケージのインストール（例）
   - 必須ライブラリ（利用する機能に応じて）:
     - duckdb
     - psutil
     - openai (ai 機能を使う場合)
     - requests (AlertManager)
     - PyYAML（validate_config で YAML パース検証を行いたい場合）
   - 例:
     - pip install duckdb psutil openai requests pyyaml
3. プロジェクトルートに移動（.git または pyproject.toml が存在するディレクトリ）
4. .env を作成
   - 推奨: ウィザードで対話的に作成
     - python -m kabusys.config_setup
   - もしくは直接ファイルを作り、必要な環境変数を設定
   - 自動読み込みはデフォルトで有効。自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定
5. 設定検証
   - python -m kabusys.validate_config
   - 問題があれば表示されます。--strict を付けると警告も失敗扱いになります
6. DB の準備
   - デフォルトパス:
     - DuckDB: data/kabusys.duckdb
     - SQLite (monitoring): data/monitoring.db
     - Paper Trading SQLite (paper_trading): data/paper_trading.db
   - 初回起動時に自動でテーブル作成・簡易マイグレーションを行う箇所があります（monitoring_db.init_monitoring_db など）
7. OpenAI を利用する場合
   - 環境変数 OPENAI_API_KEY を設定（または ai 関数に api_key を渡す）

---

## 使い方（主なコマンド例）

- 環境設定ウィザード（.env 作成／更新）
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config
  - 厳密モード（警告を FAIL とする）: python -m kabusys.validate_config --strict
- ExecutionEngine 起動
  - python -m kabusys.run_execution
  - note: KABUSYS_ENV=paper_trading を設定すると paper_trading 専用 DB を使い、MockBroker を利用する（本番 DB とは完全分離）
- Monitoring (ポーリング監視) 起動
  - python -m kabusys.run_monitoring
  - ポーリング間隔を変更するには環境変数 MONITOR_POLL_INTERVAL を秒数で指定（例: MONITOR_POLL_INTERVAL=30）
- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB を別パスにしたい場合: --db path/to/paper_trading.db （環境変数 PAPER_TRADING_SQLITE_PATH でも指定可）
- AI 機能（プログラム内呼び出し）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - これらは DuckDB コネクションおよび OpenAI API キーを必要とします

停止・Kill Switch の扱い:
- 監視側がデータの不整合やドローダウン等を検知すると、Settings.kill_flag_path（デフォルト data/kill.flag）に理由を書き込んで ExecutionEngine に停止シグナルを送ります
- 実行停止フラグ（run_execution/run_monitoring で内部使用）:
  - stop_requested flag: data/stop_requested.flag によりプロセス起動ループを止める実装があります
- 起動時に kill_flag_clear_on_start を有効にすると起動時に kill.flag を自動で削除します（本番では推奨しません）

ログ出力:
- スクリプトは logging.basicConfig(level=logging.INFO) を使用しており、LOG_LEVEL 環境変数で調整可能

注意点（Paper Trading と本番の分離）:
- KABUSYS_ENV=paper_trading の場合は paper_sqlite_path（デフォルト data/paper_trading.db）を使用し、本番 sqlite_path を使いません
- Monitoring は env に依らず本番 sqlite_path を使用する箇所があるため運用時は注意（run_monitoring の docstring 参照）

---

## 環境変数（主要）

必須（少なくとも設定を検証する）:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

主なオプション:
- KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
- DUCKDB_PATH: 分析用 DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL
- OPENAI_API_KEY: OpenAI の API キー（ai 機能で必要）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: AlertManager（LINE 通知）使用時に必要
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、run_monitoring 用。デフォルト 60）
- PAPER_FILL_MODE: ペーパートレードの約定挙動（instant / partial / never / reject）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（1 で有効。注意: 本番では 0 推奨）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 を設定すると .env の自動ロードを無効化

（完全な設定項目は config_setup.py 内の _ITEMS と Settings クラスを参照してください）

---

## ディレクトリ構成（主要ファイル・概要）

- src/kabusys/
  - __init__.py — パッケージ定義、バージョン
  - config.py — 環境変数自動ロード・Settings クラス
  - config_setup.py — .env 対話式ウィザード
  - validate_config.py — 起動前の設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor のポーリング起動スクリプト
  - utils/
    - process_priority.py — プロセス優先度・CPU affinity 設定ユーティリティ
  - monitoring/
    - monitoring_db.py — SQLite 監視 DB 初期化 / 永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
    - monitoring_engine.py — 各 Monitor を束ねるエンジン（テスト用 run_once / 本番 run）
    - system_monitor.py — システム・データ鮮度監視
    - trade_monitor.py — 注文滞留・約定異常検知
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — kill.flag 書き込みロジック
    - alert_manager.py — LINE Push 通知（クールダウン管理）
  - execution/ (実装参照。ただし README 内では高レベルに言及)
    - execution_engine.py, order_manager.py, order_repository.py, reconciler.py, risk_manager.py, broker_factory など
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py — 株数計算・スケーリング・単元丸め
    - risk_adjustment.py — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py — momentum/volatility/value 等のファクター計算（DuckDB を使用）
    - feature_exploration.py — forward returns, IC, 統計サマリー
  - ai/
    - news_nlp.py — ニュースの LLM ベースセンチメント → ai_scores 書き込み
    - regime_detector.py — ma200 + マクロニュースの LLM を組合せたレジーム判定
  - tools/
    - paper_verification_report.py — Paper Trading の検証レポート生成スクリプト

付記:
- data/ 以下はランタイムで使用されるファイル群（デフォルト）:
  - data/kabusys.duckdb
  - data/monitoring.db
  - data/paper_trading.db
  - data/execution.pid
  - data/kill.flag
  - data/stop_requested.flag

---

## 運用上の注意とベストプラクティス

- 本番環境（KABUSYS_ENV=live）の場合は .env や API キーの管理に注意してください（.env を Git にコミットしないこと）。
- kill.flag / stop_requested.flag によるプロセス制御は冪等性を保つ実装ですが、誤ってフラグを残さないよう運用ルールを設定してください。
- Monitoring は本番の監視データに書き込むため、paper_trading と混在しないよう環境変数と DB パスを確認してください。
- OpenAI を使う機能は API コスト・レイテンシを考慮して運用してください。リトライやクリップ等の保護ロジックは組み込まれていますが、コストは発生します。
- validate_config を CI に組み込むことで環境変数や設定ファイルの不備を事前に検出できます。

---

この README はコードベースから自動的に要点を抽出して作成しています。追加の利用方法や API の詳細説明が必要であれば、どのモジュール／機能のドキュメントを拡充したいか教えてください。