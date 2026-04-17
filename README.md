# KabuSys

KabuSys は日本株の自動売買システム（プロトタイプ）を構成する Python パッケージです。戦略のポートフォリオ構築、発注エンジン、監視（モニタリング）、研究用ファクター計算、AI を使ったニュースセンチメント評価などのコンポーネントで構成されています。

以下はこのリポジトリの概要・セットアップ・使い方・ディレクトリ構成のまとめです。

---

## プロジェクト概要

- 目的: 日本株の自動売買システム実装のためのライブラリ群と起動スクリプト群を提供する。
- 主な機能群:
  - ExecutionEngine（発注エンジン、ブローカー抽象化、リスク管理、オーダー管理、リコンシリエーション）
  - Monitoring（システム状態・注文状態・リスク監視、アラート送信、kill switch）
  - Portfolio construction（候補選定、重み計算、ポジションサイズ決定、セクター制限）
  - Research（DuckDB を使ったファクター計算、将来リターン・IC 計算）
  - AI（OpenAI を使ったニュースセンチメント評価、レジーム判定）
  - ツール（Paper Trading の検証レポート、Streamlit ダッシュボード）

---

## 主な機能一覧

- 発注・注文管理
  - OrderManager / OrderRepository による注文ライフサイクル管理
  - BrokerClientFactory による本番／Paper Trading 切替（paper_trading モード時は MockBrokerClient を利用）
  - Reconciler による起動時の自動復旧（OrderSent の照合、ポジション差分検出）

- 監視（Monitoring）
  - SystemMonitor: CPU/メモリ/ディスク、実行プロセス PID、データ鮮度（DuckDB の最終価格日）を監視
  - TradeMonitor: 滞留注文・約定異常価格検出
  - RiskMonitor: ドローダウン・ポジション上限監視、dashboard のハイウォーターマーク管理
  - KillSwitch: 一定条件で data/kill.flag を書き込んで ExecutionEngine を安全に停止
  - AlertManager: LINE Messaging API による通知（クールダウン管理）
  - MonitoringEngine: これらを束ねるポーリングループ
  - Streamlit ダッシュボード: 監視 DB を可視化

- ポートフォリオ構築
  - 候補選定（スコア順ソート）
  - 等分／スコア加重の重み付け
  - セクター上限の適用（apply_sector_cap）
  - ポジションサイズ決定（risk_based / equal / score、単元株丸め、集約上限）

- 研究（Research）
  - DuckDB 接続を通じたファクター計算（Momentum / Volatility / Value）
  - 将来リターンの計算、IC（Information Coefficient）や統計サマリ

- AI
  - ニュースを LLM（gpt-4o-mini）でセンチメント評価し ai_scores テーブルへ書き込み（score_news）
  - レジーム判定（ETF 1321 の MA200 乖離とマクロニュースセンチメントを組合せる）

- ツール
  - Paper Trading 検証レポート生成ツール（paper_verification_report）
  - Streamlit ダッシュボード（monitoring DB を参照）

---

## セットアップ手順

前提
- 推奨 Python バージョン: 3.10 以上（型アノテーションに | を使用しているため）
- OS: Linux / macOS / Windows いずれでも動作するよう設計されていますが、一部機能（CPU affinity 等）は OS に依存します。

1. リポジトリをクローン
   - git clone ... （省略）

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存ライブラリをインストール
   - 代表的な依存: duckdb, psutil, requests, openai, streamlit
   - 例:
     - pip install duckdb psutil requests openai streamlit

   ※requirements.txt がない場合は上記パッケージを手動でインストールしてください。

4. パッケージを開発モードでインストール（任意だが推奨）
   - プロジェクトルートに pyproject.toml がある想定:
     - pip install -e .

   これにより python -m kabusys.xxx 形式でモジュールを実行しやすくなります。

5. 環境変数設定 (.env)
   - プロジェクトルートに .env または .env.local を置くと自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
   - 主な環境変数（最低限必須）
     - JQUANTS_REFRESH_TOKEN: （必須）J-Quants API 用
     - KABU_API_PASSWORD: （必須）kabuステーション API のパスワード
   - 追加の設定（任意／推奨）
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - SQLTITE_PATH: デフォルト data/monitoring.db
     - DUCKDB_PATH: デフォルト data/kabusys.duckdb
     - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（paper_trading 時に使用）
     - OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合）
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: AlertManager（LINE）用
     - PAPER_FILL_MODE: instant | partial | never | reject（paper_trading の約定挙動）
     - MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト 60）
     - PID_FILE_PATH / KILL_FLAG_PATH など（デフォルトは data/ 以下）

6. data ディレクトリ作成
   - 一部プロセスは data/ 以下に PID や flag を書き込みます。
   - mkdir -p data

---

## 使い方（起動 / 各ツールの実行例）

実行方法は「パッケージをインストールした」 or 「PYTHONPATH に src を通す」どちらかをとります。開発時はプロジェクトルートで以下を実行するか、PYTHONPATH=src を付けてください。

- ExecutionEngine（発注エンジン）起動
  - 環境変数 KABUSYS_ENV により本番 / paper_trading を切替
  - 例（インストール済みの場合）:
    - python -m kabusys.run_execution
  - 例（src を使う場合）:
    - PYTHONPATH=src python -m kabusys.run_execution
  - 動作:
    - paper_trading モードでは MockBrokerClient を使用し、DB は PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に分離される
    - 起動時に data/stop_requested.flag を検知していれば起動しない

- Monitoring（監視）起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を変更可能（デフォルト 60）
  - 注意: Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を参照して監視 DB を操作します

- Streamlit ダッシュボード（監視 DB の可視化）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - または、インストール済みなら:
    - streamlit run $(python -c "import kabusys; import pathlib; print(pathlib.Path(kabusys.__file__).parents[1] / 'monitoring' / 'streamlit_dashboard.py')") -- --db data/monitoring.db

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - オプション --db で SQLite ファイルを指定可能（デフォルト: data/paper_trading.db）

- AI 機能
  - kabusys.ai.score_news(conn, target_date, api_key=...) — raw_news を AI に送って ai_scores に書く
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=...) — 市場レジーム判定して market_regime に書く
  - 実行には OPENAI_API_KEY が必要（引数で渡すことも可能）

- Kill Switch / 停止制御
  - data/kill.flag が存在すると ExecutionEngine 起動時に停止シグナルとして扱われます
  - Monitoring の KillSwitch が条件を満たすと kill.flag を生成します
  - data/stop_requested.flag は run_monitoring.py / run_execution.py が監視している停止フラグ（外部から停止を要求する場合に使用）

---

## 主要な環境変数（まとめ）

- KABUSYS_ENV: development | paper_trading | live（default: development）
- JQUANTS_REFRESH_TOKEN: （必須）J-Quants API トークン
- KABU_API_PASSWORD: （必須）kabuステーション API パスワード
- OPENAI_API_KEY: OpenAI API キー（AI 機能）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: AlertManager（LINE 通知）
- DUCKDB_PATH: data/kabusys.duckdb（デフォルト）
- SQLITE_PATH: data/monitoring.db（デフォルト）
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（paper_trading 用）
- PAPER_FILL_MODE: instant | partial | never | reject（paper_trading 約定挙動）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト 60）
- PID_FILE_PATH, KILL_FLAG_PATH：監視・制御用パス
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1：.env 自動ロードを無効にする

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 以下の主要なファイル・モジュールの一覧（リポジトリに含まれるファイルに基づく）：

- src/kabusys/
  - __init__.py
  - config.py               — 環境変数 / 設定管理 (.env 自動ロード含む)
  - run_monitoring.py       — SystemMonitor のポーリングループ起動スクリプト
  - run_execution.py        — ExecutionEngine 起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py — Paper Trading 検証レポート生成ツール
  - utils/
    - __init__.py
    - process_priority.py    — プロセス優先度 / CPU affinity ユーティリティ
  - portfolio/
    - __init__.py
    - portfolio_builder.py   — 候補選定・重み計算
    - position_sizing.py     — 株数決定・リスク制限・単元丸め
    - risk_adjustment.py     — セクター制限・レジーム乗数
  - research/
    - __init__.py
    - factor_research.py     — Momentum/Volatility/Value ファクター計算
    - feature_exploration.py — 将来リターン・IC・統計サマリ
  - ai/
    - __init__.py
    - news_nlp.py            — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py     — 市場レジーム判定（MA200 + マクロセンチメント）
  - monitoring/
    - __init__.py
    - monitoring_db.py       — SQLite 監視 DB レイヤー（テーブル初期化 / CRUD）
    - system_monitor.py      — システム・データ鮮度監視
    - trade_monitor.py       — 注文滞留・約定異常監視
    - risk_monitor.py        — ドローダウン・ポジション上限監視
    - monitoring_engine.py   — 各モニタを束ねるエンジン
    - alert_manager.py       — LINE 通知ラッパー
    - kill_switch.py         — kill.flag の管理
    - streamlit_dashboard.py — Streamlit ベースの可視化ダッシュボード
  - execution/
    - order_manager.py      — 発注 API の外向き API
    - reconciler.py         — 起動時のリコンシリエーション（同期処理）
    - ... (その他 OrderRepository / broker などのモジュールが存在)
  - data/                    — 実行時に使われる DB・PID・flag（リポジトリに含まれることを想定）
    - monitoring.db (デフォルト)
    - kabusys.duckdb (デフォルト)
    - paper_trading.db (paper_trading 時)
    - execution.pid
    - kill.flag / stop_requested.flag

---

## 運用上の注意点

- データベース分離:
  - paper_trading（KABUSYS_ENV=paper_trading）時は paper_sqlite_path（デフォルト data/paper_trading.db）を使用し、本番 DB と完全分離する設計です。
  - Monitoring は設計上、本番 sqlite_path を参照します（監視は環境に依らず本番 DB を見る仕様の箇所あり）。

- プロセス制御:
  - run_monitoring / run_execution は data/stop_requested.flag を監視して終了します。kill.flag は ExecutionEngine の停止要求用です。
  - set_process_priority により起動時にプロセス優先度を上げます（権限により失敗することがあります）。

- AI（OpenAI）:
  - OpenAI API 呼び出しは外部サービスに依存します。API failures はリトライやフォールバック（0.0）で安全に扱う設計になっていますが、API キーが必須です。

- .env の自動読み込み:
  - config.py はプロジェクトルート（.git または pyproject.toml）を検出し、.env / .env.local を自動読み込みします。必要に応じて KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して無効化してください。

---

## よくある操作例（まとめ）

- 仮想環境を作る、依存を入れる:
  - python -m venv .venv && source .venv/bin/activate
  - pip install duckdb psutil requests openai streamlit
  - pip install -e .

- 監視を起動（デフォルト 60 秒間隔）:
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- 発注エンジン（Execution）を起動:
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution

- Paper Trading 検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - または --db path/to/paper_trading.db

- Streamlit ダッシュボード:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

---

この README はコードベースの主要な振る舞いと実行方法を要約したものです。詳しい内部ロジックや API のパラメータ仕様、DB スキーマの説明は各モジュール（monitoring/*.py, ai/*.py, research/*.py, execution/*.py, portfolio/*.py）内の docstring を参照してください。必要であれば各モジュール向けの詳細ドキュメント（設計ノート、図、API リファレンス）を別途作成できます。