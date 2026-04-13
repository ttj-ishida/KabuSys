# KabuSys

KabuSys は日本株の自動売買システムを想定したリポジトリです。取引実行・監視・ポートフォリオ構築・リサーチ・AI を使ったニュース解析などの主要機能をモジュールごとに提供します。本 README はコードベース（src/kabusys 以下）を元に作成しています。

---

## プロジェクト概要

- 目的：日本株自動売買の実装例（ExecutionEngine、Monitoring、Portfolio Construction、Research、AI ニューススコアリング等）。
- 永続化：
  - 監視ログ等は SQLite（デフォルト: `data/monitoring.db`）。
  - ファクター計算や時系列データは DuckDB（デフォルト: `data/kabusys.duckdb`）。
- 環境切替：
  - `KABUSYS_ENV` により `development` / `paper_trading` / `live` を切替可能。
  - `paper_trading` 時は MockBroker を使用し、DB は `data/paper_trading.db` に分離されます（本番データと完全分離）。
- プロセス優先度設定：起動スクリプトは最初にプロセス優先度を "high" に試みます（プラットフォーム依存）。

---

## 主な機能一覧

- Execution（発注実行）
  - 起動スクリプト: `kabusys.run_execution`
  - BrokerFactory による実行環境に合わせた Broker クライアント生成
  - OrderManager, OrderRepository, RiskManager, Reconciler を組み合わせた実行フロー
  - 冪等な監視テーブル初期化（`init_monitoring_db`）

- Monitoring（監視）
  - 起動スクリプト: `kabusys.run_monitoring`
  - SystemMonitor：CPU/メモリ/ディスク/データ鮮度/実行プロセス監視
  - TradeMonitor：滞留注文・約定異常検出
  - RiskMonitor：ドローダウン・ポジション上限監視とダッシュボード更新
  - KillSwitch：監視ルールで `data/kill.flag` を書いて Execution を停止
  - AlertManager：LINE Push によるアラート送信
  - Streamlit ベースの監視ダッシュボード（`streamlit_dashboard.py`）

- Portfolio（銘柄選定・配分・サイズ決定）
  - 候補選定（スコア順／signal_rank ブレーク）
  - 等配分／スコア加重配分
  - セクター集中上限適用
  - ポジションサイズ計算（リスクベース／等配分等）、単元株丸め、aggregate cap

- Research（因子計算・探索）
  - モメンタム / ボラティリティ / バリュー等のファクター計算（DuckDB 接続で SQL を利用）
  - 将来リターン計算、IC（Spearman）算出、統計サマリーなど

- AI（OpenAI を用いた処理）
  - ニュースセンチメントの銘柄別スコアリング（`kabusys.ai.news_nlp.score_news`）
  - マクロニュース + ETF MA200 に基づく市場レジーム判定（`kabusys.ai.regime_detector.score_regime`）
  - OpenAI の呼出はリトライ/バックオフ・レスポンス検証を備える

- ツール
  - Paper Trading の検証レポート生成スクリプト（`kabusys.tools.paper_verification_report`）

---

## セットアップ手順

前提
- Python 3.10 以上（typing の一部機能を利用）
- SQLite は標準ライブラリ
- 推奨パッケージ：duckdb, psutil, requests, openai, streamlit

1. 仮想環境を作成・有効化（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - pip install duckdb psutil requests openai streamlit

   （プロジェクトに requirements.txt があればそちらを利用してください）

3. データディレクトリ作成（必要に応じて）
   - mkdir -p data

4. 環境変数設定
   - .env または環境変数で設定可能（config.py が自動で .env, .env.local を読み込みます）
   - 自動読み込みを無効にする場合：
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

主な環境変数（代表例）
- KABUSYS_ENV: development | paper_trading | live  （デフォルト: development）
- SQLITE_PATH: SQLite（監視）ファイルパス（デフォルト: data/monitoring.db）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
- MONITOR_POLL_INTERVAL: 監視ポーリング秒数（デフォルト: 60）
- PID_FILE_PATH: ExecutionEngine の PID ファイルパス（デフォルト: data/execution.pid）
- KILL_FLAG_PATH: kill.flag のパス（デフォルト: data/kill.flag）
- OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合必須）
- JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD: 外部 API を使う場合に必要

注意: config.py は OS 環境変数 > .env.local > .env の順で読み込みを行います。`.env.local` の方が優先で上書きされます。ただし OS 環境変数は保護され上書きされません。

---

## 使い方

基本的な起動例（プロジェクトルートから実行）

- 監視ループを起動（監視用 SQLite に接続して SystemMonitor の定期チェックを行う）
  - MONITOR_POLL_INTERVAL を指定（秒）
  - 実行:
    - python -m kabusys.run_monitoring
  - 動作:
    - プロセス優先度を high に設定し、SQLite / DuckDB に接続してポーリングループを回します。

- ExecutionEngine を起動（実取引 or paper_trading）
  - Paper トレードにする:
    - export KABUSYS_ENV=paper_trading
  - 実行:
    - python -m kabusys.run_execution
  - 動作:
    - Broker クライアントを環境に応じて生成（paper_trading では MockBroker を利用）
    - OrderRepository, OrderManager, RiskManager, Reconciler を組み立て ExecutionEngine を開始

- Streamlit ダッシュボード（監視 UI）
  - 起動:
    - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - read-only 接続で SQLite を開き、ダッシュボードを表示します。

- Paper Trading 検証レポート（コマンドライン）
  - 実行:
    - python -m kabusys.tools.paper_verification_report
    - オプション: --from YYYY-MM-DD --to YYYY-MM-DD --db PATH
  - デフォルト DB は `data/paper_trading.db`（環境変数 `PAPER_TRADING_SQLITE_PATH` で上書き可）

- AI 機能（スクリプト / プログラム内呼び出し）
  - ニューススコアリング:
    - from kabusys.ai.news_nlp import score_news
    - score_news(conn, target_date, api_key=...)
  - レジーム判定:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(conn, target_date, api_key=...)

- 設定確認
  - アプリケーションからは `kabusys.config.Settings` を通じて設定値を取得します。利用可能なプロパティは `config.py` の docstring /プロパティ一覧を参照してください。

---

## 実装上の重要ポイント・注意点

- Monitoring 用テーブル初期化:
  - `init_monitoring_db(conn)` は冪等に監視用テーブルを作成し、マイグレーション（列追加）も内包します。
- PID / Kill Flag:
  - ExecutionEngine は PID ファイル（`PID_FILE_PATH`）を書き、監視側はこれを使ってプロセス存在をチェックします。
  - KillSwitch は `KILL_FLAG_PATH` にフラグを書き、ExecutionEngine 起動時にその存在を確認して停止できます。
- Paper Trading の分離:
  - `KABUSYS_ENV=paper_trading` の場合、発注 DB は `PAPER_TRADING_SQLITE_PATH` を参照し、本番の monitoring DB とは分離されます。
- OpenAI 呼び出し:
  - API 呼び出しはリトライ・バックオフを実装。失敗時はフェイルセーフで中立値やスキップを選択する設計。
- .env パース:
  - `config._parse_env_line` は複雑なクォート／コメント処理を行いますが、想定外フォーマットには注意してください。
- 依存権限:
  - プロセス優先度設定や CPU affinity はプラットフォーム・権限によって失敗する場合があり、失敗時は警告ログを出してスキップします。

---

## ディレクトリ構成（主要ファイル）

（src/kabusys 以下を抜粋）

- src/kabusys/
  - __init__.py
  - config.py                     — 環境変数 / 設定管理
  - run_monitoring.py             — SystemMonitor をポーリング起動するスクリプト
  - run_execution.py              — ExecutionEngine 起動スクリプト
  - utils/
    - __init__.py
    - process_priority.py         — プロセス優先度 / CPU affinity ユーティリティ
  - monitoring/
    - __init__.py
    - monitoring_db.py            — SQLite 永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - alert_manager.py
    - kill_switch.py
    - streamlit_dashboard.py
  - execution/
    - order_manager.py
    - order_repository.py
    - order_record.py
    - reconciler.py
    - execution_engine.py         — (ファイル抜粋は README に全部含まれていませんがメイン構成)
    - broker_factory.py
    - broker_api.py
    - ... （実装の詳細は該当ファイル参照）
  - portfolio/
    - __init__.py
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - ai/
    - __init__.py
    - news_nlp.py                  — ニュースを OpenAI でスコアリング
    - regime_detector.py           — マクロ + ETF MA200 によるレジーム判定
  - tools/
    - __init__.py
    - paper_verification_report.py — Paper Trading 検証レポート生成ツール

---

## 追加情報・運用メモ

- ログレベルは `LOG_LEVEL` 環境変数で制御（Settings.log_level）。
- Monitoring のポーリング間隔は `MONITOR_POLL_INTERVAL`（秒）で上書き可能。1 未満や非数値は無視されデフォルト 60 秒が使われます。
- DuckDB は大規模時系列データやファクター計算用に使用する想定です。接続先は `DUCKDB_PATH` で設定可能。
- DB のバックアップ / ローテーション、データ保持期間等の運用ルールは実装に含まれていません。運用環境に合わせて外部ツールで対処してください。

---

必要であれば、README に「インストール可能な requirements.txt の例」「簡易デプロイ手順（systemd 例）」「よくあるトラブルシューティング（OpenAI のタイムアウトや psutil の権限問題）」などを追記できます。どの情報を優先して追加しますか？