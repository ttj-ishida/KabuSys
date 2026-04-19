# KabuSys

日本株向け自動売買システムのリポジトリ（小規模コアライブラリ）。  
このドキュメントはコードベースの主要コンポーネント、セットアップ方法、基本的な使い方、ディレクトリ構成をまとめたものです。

注意: 本リポジトリには実際の API トークンやパスワードを含めないでください。`.env` は決して Git にコミットしないでください。

---

## プロジェクト概要

KabuSys は日本株の自動売買に関わる以下の機能群を提供するモジュール群です。

- シグナル生成 / ポートフォリオ構築（portfolio）
- ポジションサイズ計算・注文ロジック（execution 用の補助関数）
- 監視（Monitoring）・アラート・Kill Switch
- リサーチ用ファクター計算（DuckDB ベース）
- News NLP / 市場レジーム判定（OpenAI を用いたスコアリング）
- ユーティリティ（ログ、プロセス優先度設定、設定管理など）
- 開発者向け CLI（.env ウィザード、設定検証、ペーパートレード検証レポート）

設計上の特徴:
- DuckDB をデータ分析（prices_daily 等）に利用
- SQLite を監視・発注ログ用に利用（paper_trading は別 DB に分離）
- 設定は `.env` / 環境変数経由。`Settings` クラスで抽象化
- OpenAI 呼び出しはリトライ・バリデーションを組み込んだ実装

---

## 主な機能一覧

- 実行スクリプト
  - run_execution: ExecutionEngine の起動（KABUSYS_ENV による paper/live 切替）
  - run_monitoring: SystemMonitor を定期実行するポーリングループ（MONITOR_POLL_INTERVAL）

- 設定管理
  - config_setup: 対話式ウィザードで `.env` を生成/更新
  - validate_config: 起動前に環境変数 / 設定ファイルの検証

- リサーチ / ファクター
  - research.calc_momentum / calc_volatility / calc_value
  - feature_exploration: forward return / IC / 統計サマリ

- ポートフォリオ構築
  - select_candidates, calc_equal_weights, calc_score_weights
  - calc_position_sizes（risk_based 等のアルゴリズム）
  - apply_sector_cap, calc_regime_multiplier（セクター制約・レジーム調整）

- AI（OpenAI 経由）
  - ai.news_nlp.score_news: ニュース記事に基づく銘柄センチメントスコア生成（ai_scores テーブル書込）
  - ai.regime_detector.score_regime: マクロ + ma200 による日次レジーム判定

- 監視
  - monitoring.MonitoringEngine: System / Trade / Risk を束ねてループ実行
  - monitoring.system_monitor, trade_monitor, risk_monitor
  - monitoring.kill_switch: kill.flag を書き込んで ExecutionEngine を安全に停止させる
  - monitoring.monitoring_db: SQLite のスキーマ初期化と永続化 API

- ツール
  - tools.paper_verification_report: ペーパートレード DB から統合的検証レポートを生成

---

## セットアップ手順（ローカル開発向け）

前提:
- Python 3.10+（コードは型注釈で Union 型などを使用）
- SQLite（Python 標準ライブラリに含む）
- DuckDB（pip で導入）
- psutil（プロセス優先度・CPU情報）
- openai（AI 機能を使う場合）
- PyYAML（validate_config による config/*.yaml 検証を使う場合）

1. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 必要パッケージをインストール
   - pip install duckdb psutil openai
   - PyYAML は任意: pip install pyyaml

   （プロジェクトに requirements.txt がない場合は上記を手動インストール）

3. ディレクトリ作成（ログ / DB 用）
   - mkdir -p data logs

   起動時に自動作成される箇所もありますが、手動で作っておくと権限周りで安全です。

4. .env を作成
   - 対話式ウィザードで生成: python -m kabusys.config_setup
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - AI 機能を使う場合:
     - OPENAI_API_KEY

   自動ロード:
   - プロジェクトルートの `.env` / `.env.local` は起動時に自動的に読み込まれます（テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。

5. 設定検証
   - python -m kabusys.validate_config
   - 警告もエラー扱いにする場合: python -m kabusys.validate_config --strict

---

## 使い方（主要なコマンド）

- 実行エンジン（ExecutionEngine）起動
  - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用して data/paper_trading.db を利用（本番 DB と分離）
    - 起動時に data/stop_requested.flag が存在する場合は起動せず終了
    - 実行中は data/execution.pid が使用されます

- 監視（SystemMonitor）起動
  - python -m kabusys.run_monitoring
  - 環境変数:
    - MONITOR_POLL_INTERVAL: ポーリング間隔（秒）を上書き（デフォルト 60）
  - 監視は常に本番 sqlite_path を使う（環境にかかわらず）
  - 停止:
    - プロジェクトルート/data/stop_requested.flag を作成すると監視ループが検出して終了します

- ログ
  - デフォルト: logs/<app_name>.log（TimedRotatingFileHandler による日次ローテーション、30日保持）
  - LOG_DIR 環境変数で変更可能
  - LOG_LEVEL 環境変数（DEBUG/INFO/...）でログレベルを制御

- 設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict により警告も失敗扱いにできます

- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD
    - --to YYYY-MM-DD
    - --db PATH （PAPER_TRADING_SQLITE_PATH 環境変数の代替）

---

## 主要な環境変数（抜粋）

- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - paper_trading: 発注は MockBroker、DB は data/paper_trading.db
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE（paper_trading 時の約定挙動: instant | partial | never | reject。デフォルト instant）
- MONITOR_POLL_INTERVAL（run_monitoring ポーリング間隔秒）
- LOG_LEVEL（ログレベル。デフォルト INFO）
- LOG_DIR（ログ保存先）
- OPENAI_API_KEY（AI 機能利用時に必要）
- KILL_FLAG_CLEAR_ON_START（起動時に kill.flag を自動クリアするか。0/1。production では 0 推奨）

---

## 注意点 / 運用メモ

- データベースマイグレーション:
  - monitoring_db.init_monitoring_db() は起動時に冪等にテーブルを作成し、簡易的なカラム追加を行います。
- Kill Switch:
  - monitoring.kill_switch はリスク閾値を検出すると data/kill.flag を書き込み、ExecutionEngine に停止シグナルを送ります（ExecutionEngine は kill.flag を見て停止処理を行います）。
  - 本番では KILL_FLAG_CLEAR_ON_START=0 を推奨（起動時に kill flag を自動で消すと危険）。
- OpenAI 呼び出し:
  - rate limit / 一時エラーを踏まえて指数バックオフでリトライします。API キーは OPENAI_API_KEY を想定。
  - レスポンスの JSON バリデーションを厳密に行い、失敗時はフェイルセーフ（0 やスキップ）で継続します。
- プロセス優先度:
  - 起動時に set_process_priority("high") を呼び出します。psutil による操作が失敗してもログに警告を出して継続します。
- 自動 .env 読み込み:
  - プロジェクトルートの `.env` と `.env.local` を自動ロードします（OS 環境変数が優先）。自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1。

---

## ディレクトリ構成（抜粋）

以下は重要ファイル / モジュールの概観です（トップは src/kabusys）:

- src/kabusys/
  - __init__.py (バージョン)
  - config.py (Settings クラス、.env 自動ロードロジック)
  - config_setup.py (.env 対話式ウィザード)
  - validate_config.py (設定検証 CLI)
  - run_execution.py (ExecutionEngine 起動スクリプト)
  - run_monitoring.py (SystemMonitor ポーリング起動スクリプト)
  - tools/
    - paper_verification_report.py (ペーパートレード検証レポート)
  - portfolio/
    - portfolio_builder.py (候補選定・重み)
    - position_sizing.py (株数決定・資金配分)
    - risk_adjustment.py (セクターキャップ・レジーム乗数)
  - research/
    - factor_research.py (momentum/value/volatility 計算)
    - feature_exploration.py (forward returns, IC, summary)
  - ai/
    - news_nlp.py (ニュース → センチメントスコア)
    - regime_detector.py (ma200 + macro sentiment → market regime)
  - monitoring/
    - monitoring_db.py (SQLite テーブル定義 + MonitoringDB API)
    - monitoring_engine.py (複数 Monitor を束ねる)
    - system_monitor.py (プロセス・データ鮮度監視)
    - risk_monitor.py (ドローダウン・ポジション上限監視)
    - kill_switch.py (kill.flag の作成/確認)
    - alert_manager.py (アラート管理)  ※コードベース内参照あり
    - trade_monitor.py (発注ログ等の監視) ※コードベース内参照あり
  - utils/
    - logging_setup.py (統一的ログ設定)
    - process_priority.py (プロセス優先度 / CPU affine 設定)
  - portfolio, execution, monitoring 内にさらに実行ロジックやリポジトリが存在

---

## 開発者向けヒント

- テスト時に環境変数自動ロードを無効化:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して import 時の自動読み込みを回避できます。
- OpenAI 呼出しをモックする:
  - news_nlp._call_openai_api や regime_detector._call_openai_api を unittest.mock でパッチしてユニットテストを実行してください。
- DuckDB 接続:
  - research / ai モジュールは DuckDB 接続を受け取る設計（外部の DB コネクションを注入してテスト可能）。

---

以上がこのコードベースの概要と基本的な使い方です。  
追加で「実行エンジンの挙動」「監視のアラート設定」「データベーススキーマの詳細」など特定トピックのドキュメントが必要であれば、その旨を教えてください。