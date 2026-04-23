# KabuSys README

このリポジトリは日本株向けの自動売買／リサーチ基盤ライブラリです。ここではプロジェクト概要、主な機能、セットアップ手順、使い方、およびディレクトリ構成をまとめます。

---

## プロジェクト概要

KabuSys は日本株の自動売買システムおよびリサーチ用ユーティリティ群を収めた Python パッケージです。以下の目的を想定しています。

- 戦略用のファクター計算・特徴量探索（DuckDB を利用）
- ポートフォリオ構築（候補選定・重み付け・ポジションサイズ算出）
- 発注エンジン（本番／ペーパートレード分離）
- システム監視とリスク監視（監視ログの永続化、Kill Switch）
- ニュース NLP（OpenAI を使ったセンチメントスコアリング）
- 運用支援ツール（.env 設定ウィザード、設定検証、ペーパートレード検証レポート）

重要な設計方針として、ルックアヘッドバイアスを避けるために日付参照や DB クエリは慎重に扱われています。また、ペーパートレード環境は本番 DB と完全に分離されます。

---

## 機能一覧（抜粋）

- 環境設定管理・ウィザード
  - .env 生成 / 更新（python -m kabusys.config_setup）
  - 設定検証 CLI（python -m kabusys.validate_config）

- 発注・実行
  - ExecutionEngine 起動スクリプト（python -m kabusys.run_execution）
  - Paper Trading モードでは MockBrokerClient を利用し、data/paper_trading.db に書き込む

- 監視
  - SystemMonitor / TradeMonitor / RiskMonitor を束ねる MonitoringEngine
  - run_monitoring スクリプト（python -m kabusys.run_monitoring）
  - Kill Switch: リスク条件により data/kill.flag を書き込み、Engine を停止させる

- ポートフォリオ構築（純粋関数）
  - 候補選定（select_candidates）
  - 等重／スコア重み（calc_equal_weights / calc_score_weights）
  - セクター制限（apply_sector_cap）
  - レジーム乗数（calc_regime_multiplier）
  - ポジションサイズ算出（calc_position_sizes）

- リサーチ
  - ファクター計算（momentum / volatility / value）
  - 将来リターン／IC 計算、統計サマリ

- AI（OpenAI）
  - ニュースセンチメントスコアリング（kabusys.ai.score_news）
  - 市場レジーム判定（ai.regime_detector.score_regime）

- 運用ツール
  - Paper Trading 検証レポート（python -m kabusys.tools.paper_verification_report）

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローンし、Python 環境を準備します（Python 3.10+ を想定）。
   - 仮想環境の作成・有効化推奨（venv / poetry / pipenv 等）

2. 必要ライブラリをインストールします（requirements.txt / pyproject.toml に従う）。
   - 例: pip install -r requirements.txt
   - 主要依存: duckdb, psutil, openai（AI 機能利用時）, PyYAML（設定検証で任意）

3. .env を作成
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - 手動で作る場合は .env.example を参考にして .env を作成してください。

4. 設定の検証（起動前に実行推奨）
   - python -m kabusys.validate_config
   - 警告も厳格にチェックする場合:
     - python -m kabusys.validate_config --strict

5. データディレクトリを作成（必要なら）
   - デフォルトの DB / PID / フラグは `data/` に置かれます。実行時に自動作成される場合もありますが、権限等の問題で事前に作るのが安全です。

---

## 主要な環境変数（主なもの）

- 必須
  - JQUANTS_REFRESH_TOKEN — J-Quants API 用
  - KABU_API_PASSWORD — kabuステーション API パスワード

- 実行環境
  - KABUSYS_ENV — development | paper_trading | live （デフォルト: development）
    - paper_trading: 発注はモック、専用 DB（PAPER_TRADING_SQLITE_PATH）に記録
    - live: 本番モード

- DB / ログ
  - DUCKDB_PATH — DuckDB ファイル（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）
  - LOG_LEVEL — ログレベル（DEBUG/INFO/…）
  - LOG_DIR — ログディレクトリ（デフォルト: logs/）

- AI
  - OPENAI_API_KEY — OpenAI API キー（ai モジュール利用時）

- その他
  - MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト 60）
  - PAPER_FILL_MODE — ペーパートレード時の約定挙動（instant | partial | never | reject）
  - KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag をクリアするか（"1" で有効、注意: 本番では危険）
  - PID_FILE_PATH / KILL_FLAG_PATH — Settings で参照

※ .env は決して Git にコミットしないでください（秘密情報が含まれます）。

---

## 使い方（ランナー・ツール）

基本的に各機能はモジュールとして使えるほか、実行スクリプトが提供されています。

- 環境設定ウィザード
  - python -m kabusys.config_setup
  - .env を対話式に生成・更新します

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗扱いになります

- ExecutionEngine（取引実行エンジン）起動
  - python -m kabusys.run_execution
  - 起動時にプロセス優先度を "high" に設定します
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使い data/paper_trading.db に記録（本番 DB と分離）
  - 停止: プロジェクトルートの data/stop_requested.flag を作成すると安全に終了します

- Monitoring（監視）起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒数で指定可能（デフォルト 60 秒）
  - 監視は Settings の sqlite_path を常に使用（環境に依らず本番監視 DB に書き込まれる点に注意）
  - 監視は system/trade/risk をチェックし、必要に応じて Kill Switch を発動して data/kill.flag を書き込みます

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - デフォルト DB: data/paper_trading.db（PAPER_TRADING_SQLITE_PATH 環境変数で上書き可）
  - 稼働率・注文成功率・P95 レイテンシ等を算出して PASS/FAIL 判定を出力します

- AI スコアリング（プログラムから利用）
  - ニュースセンチメント: from kabusys.ai import score_news
    - score_news(conn, target_date, api_key=None)
  - レジーム判定: kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - OpenAI API キーが必要（引数で渡すか OPENAI_API_KEY 環境変数を設定）

- ロギング
  - 各起動スクリプトは共通の setup_logging を使用しており、console（stdout）出力 + 日次ローテートのファイル出力（logs/<app>.log）を行います

---

## 停止・Kill Switch の扱い

- 手動停止（実行スクリプト両方で有効）
  - プロジェクトルートの data/stop_requested.flag を作成すると、run_execution/run_monitoring は検知して終了します

- Kill Switch（自動）
  - 監視が条件を満たした場合（例: ドローダウン超過・ポジション上限超過）に monitoring モジュールが data/kill.flag を書き込みます
  - ExecutionEngine は起動時に kill フラグのクリーンアップ設定（KILL_FLAG_CLEAR_ON_START）を尊重する可能性がありますが、本番では 0 のままにすることを推奨します
  - kill.flag を取り消すには手動でファイルを削除してください（rm data/kill.flag）

---

## 開発者向けノート / 注意点

- Paper Trading は本番 DB と分離されます。paper_trading モードでは paper_sqlite_path に書き込まれるため、本番データに上書きされる心配はありません。
- ローカルで OpenAI を利用する場合は API キーに注意してください。モデルやトークン利用にはコストがかかります。
- DuckDB に依存するリサーチ機能は prices_daily / raw_financials / raw_news 等のテーブル構成に依存します。事前にデータを投入しておく必要があります。
- 監視用 SQLite（monitoring.db）は init_monitoring_db によりテーブルとマイグレーションが行われます。既存 DB への列追加処理（例: peak_value, latency_ms）も備えています。

---

## ディレクトリ構成（抜粋）

以下は main なファイルとモジュールの概観です（src/kabusys 以下）。

- kabusys/
  - __init__.py
  - config.py                 — 環境変数 / Settings 管理（.env 自動ロード）
  - config_setup.py           — .env 対話式ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — SystemMonitor ポーリング起動スクリプト
  - utils/
    - logging_setup.py        — 共通ロギング設定
    - process_priority.py     — プロセス優先度 / CPU affinity 設定
  - monitoring/
    - monitoring_db.py        — SQLite 永続化層（テーブル作成・CRUD）
    - system_monitor.py       — システム状態・データ鮮度監視
    - risk_monitor.py         — ドローダウン・ポジション上限監視
    - kill_switch.py          — kill.flag 書込みロジック
    - monitoring_engine.py    — 各 Monitor を束ねるエンジン
    - ... (alert_manager, trade_monitor 等)
  - execution/                 — 発注エンジン関連（OrderManager, BrokerFactory 等）
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py             — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py      — レジーム判定（ma200 + macro sentiment）
  - tools/
    - paper_verification_report.py

（注）上記は主要ファイルの抜粋です。細かなサブモジュールが他にも存在します。

---

## 例: よく使うコマンド集

- .env ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- 発注エンジン起動（バックグラウンド実行等は OS の方法で）
  - python -m kabusys.run_execution

- 監視プロセス起動
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- Paper Trading レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定: --db path/to/paper_trading.db

---

## 最後に

本 README はコードベースの主要な使い方／構成をまとめたものです。各モジュールには詳細な docstring が付いているため、実装や動作を詳しく確認したい場合は該当ファイルを参照してください。運用・本番導入時は必ず設定検証（validate_config）と、kill flag / PID / ログディレクトリのアクセス権限を確認してください。ご不明点があれば知りたい箇所を指定して質問してください。