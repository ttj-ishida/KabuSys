# KabuSys — README

このリポジトリは日本株向け自動売買システム KabuSys の一部実装です。
以下はコードベース（src/kabusys 以下）に基づく README です。

- 対応 Python: >= 3.10（型ヒントに `X | Y` を使用）
- 主要依存ライブラリ（抜粋）: duckdb, psutil, requests, openai, streamlit

---

## プロジェクト概要

KabuSys は日本株の自動売買を想定したシステム群です。本コードベースには以下の主要機能が含まれます。

- Execution エンジン起動スクリプト（本番 / paper trading 切替）
- 監視（Monitoring）コンポーネント（システム状態・注文監視・リスク判定・Kill Switch）
- ポートフォリオ構築（候補選定、重み付け、ポジションサイズ計算、セクター制約）
- リサーチ用ファクター計算（モメンタム / ボラティリティ / バリュー）
- ニュース NLP（OpenAI を使った銘柄別センチメント化）
- レジーム検出（ETF + マクロセンチメントを合成）
- 各種ツール（Paper Trading 検証レポート、Streamlit ダッシュボード など）

設計上のポイント:
- DuckDB / SQLite を使ったローカルデータ操作
- テスト / paper_trading 環境向けに本番 DB と分離する仕組み
- LLM（OpenAI）呼び出しは失敗時に安全にフォールバック（フェイルセーフ）
- アプリ設定は環境変数 / .env ファイルから読み込み（Settings クラス）

---

## 機能一覧（抜粋）

- 起動スクリプト
  - run_execution.py: ExecutionEngine 起動（KABUSYS_ENV による paper/live 切替）
  - run_monitoring.py: SystemMonitor のポーリングループ起動（MONITOR_POLL_INTERVAL 対応）
- 監視
  - system_monitor: CPU/メモリ/ディスク/プロセス PID/データ鮮度監視
  - trade_monitor: 注文滞留・約定異常価格の検出
  - risk_monitor: ドローダウン・ポジション上限監視とダッシュボード更新
  - kill_switch: フラグファイルで ExecutionEngine 停止指示（data/kill.flag）
  - alert_manager: LINE Push による通知（クールダウン管理）
  - streamlit_dashboard: Streamlit で監視ダッシュボードを表示
- Execution 側
  - Reconciler: 再起動時の注文・ポジション照合
  - OrderManager / OrderRepository: 注文状態管理、DB 永続化
- ポートフォリオ構築
  - 候補選定、等金額／スコア重み付け、リスク調整、position sizing（単元丸め、aggregate cap）
- リサーチ
  - factor_research: momentum / volatility / value のファクター計算（DuckDB 経由）
  - feature_exploration: 将来リターン、IC、統計サマリー
- AI（LLM）
  - news_nlp.score_news: raw_news を LLM で銘柄別にセンチメント化して ai_scores に書き込み
  - regime_detector.score_regime: ETF の MA とマクロニュースで市場レジーム判定
- ツール
  - tools.paper_verification_report: Paper Trading 用の検証レポート生成（SQLite を読み取り）

---

## セットアップ手順（開発 / 実行環境）

1. リポジトリをクローンし、作業ディレクトリをプロジェクトルートにする。

2. Python 仮想環境を作成・有効化（例: venv）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール（代表的なパッケージ）
   - pip install duckdb psutil requests openai streamlit

   実際にはプロジェクトに requirements.txt があればそれを使用してください。

4. データディレクトリを作成（デフォルトの DB 保存先や pid ファイルを置くため）
   - mkdir -p data

5. 環境変数の設定
   - 本プロジェクトは Settings クラスが環境変数を参照します。主な環境変数:
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - JQUANTS_REFRESH_TOKEN: （必須）J-Quants API トークン
     - KABU_API_PASSWORD: （必須）kabuステーション API パスワード
     - OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合）
     - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: LINE 通知用（任意）
     - PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
     - PID_FILE_PATH, KILL_FLAG_PATH（デフォルトあり）
     - PAPER_FILL_MODE: paper trading の fill 挙動 (instant|partial|never|reject)（デフォルト: instant）
     - MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト: 60）
     - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env 自動ロードを無効化できます。

   - プロジェクトはプロジェクトルート（.git または pyproject.toml のあるディレクトリ）から `.env` / `.env.local` を自動ロードします。

---

## 使い方（主要な実行例）

※ 下記はプロジェクトルートで実行する想定です。

1. 監視プロセスの起動
   - MONITOR_POLL_INTERVAL を上書き可能（秒）
   - python -m kabusys.run_monitoring
   - あるいは環境変数を指定して:
     - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

   備考:
   - run_monitoring は Settings にかかわらず本番 sqlite_path（SQLITE_PATH）を使用して監視 DB を開きます。
   - 起動時にプロセス優先度を "high" に設定しようとします（psutil 権限に依存）。

2. Execution エンジンの起動
   - 通常: python -m kabusys.run_execution
   - Paper Trading 環境（mock broker & 別 DB）:
     - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
   - run_execution は paper_trading の場合、PAPER_TRADING_SQLITE_PATH を使い、本番 DB と分離されます。

3. Streamlit ダッシュボード
   - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
   - dashboard は監視 DB を読み取り専用で開きます。監視ループが DB を作成/更新していることが前提です。

4. Paper Trading 検証レポート生成
   - python -m kabusys.tools.paper_verification_report
   - 期間指定:
     - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   - DB パス指定:
     - python -m kabusys.tools.paper_verification_report --db data/paper_trading.db

5. AI / レジームスコア関連（スクリプトから直接呼ぶ例）
   - news_nlp.score_news や regime_detector.score_regime は DuckDB 接続と target_date、（必要なら）api_key を受け取ります。簡易例:
     - python - <<'PY'
       import duckdb, datetime
       from kabusys.ai.news_nlp import score_news
       conn = duckdb.connect('data/kabusys.duckdb')
       print(score_news(conn, datetime.date(2026,4,1), api_key='YOUR_KEY'))
       PY__

   - 実運用ではこれらをバッチジョブやスケジューラで実行します。OpenAI の API キーは引数か環境変数 OPENAI_API_KEY で指定可能です。

---

## 設定・挙動の補足

- .env 自動読み込み:
  - プロジェクトルートが見つかると `.env`（上書きしない）→ `.env.local`（上書き）を読み込みます。
  - OS 環境変数が優先され、`.env.local` は OS 環境変数を上書きしません（保護）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化できます。

- MONITOR_POLL_INTERVAL:
  - run_monitoring 内のポーリング間隔。環境変数で整数秒を設定できます。1 未満や不正な値はデフォルト 60 秒にフォールバックします。

- Paper Trading:
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient（実装箇所に依存）を使用し、紙データベース（PAPER_TRADING_SQLITE_PATH）に記録します。

- PID / Kill Flag:
  - Execution 側は PID ファイル（Settings.pid_file_path）を作成し、監視側は PID 存在チェックを行います。
  - KillSwitch は指定された kill_flag_path（デフォルト data/kill.flag）に理由を書き込むことで Execution 停止トリガーを発生させます。

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 以下の主要ファイル・モジュールの構成（抜粋）です。

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / .env 読み込みと Settings クラス
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリングループ起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py — Paper Trading 検証レポート生成
  - monitoring/
    - __init__.py
    - monitoring_db.py        — SQLite スキーマ定義 / MonitoringDB ラッパ
    - system_monitor.py       — システム状態・データ鮮度監視
    - trade_monitor.py        — 注文滞留・約定異常検出
    - risk_monitor.py         — ドローダウン・ポジション上限監視
    - kill_switch.py          — kill.flag 管理
    - alert_manager.py        — LINE 通知ラッパ
    - monitoring_engine.py    — 各 Monitor を束ねるエンジン
    - streamlit_dashboard.py  — Streamlit ダッシュボード
  - portfolio/
    - __init__.py
    - portfolio_builder.py    — 候補選定・重み計算
    - risk_adjustment.py      — セクターキャップ・レジーム乗数
    - position_sizing.py      — 株数算出・単元丸め・aggregate cap
  - research/
    - __init__.py
    - factor_research.py      — momentum / volatility / value
    - feature_exploration.py  — 将来リターン・IC・統計サマリー
  - ai/
    - __init__.py
    - news_nlp.py             — ニュース → 銘柄別センチメント（OpenAI）
    - regime_detector.py      — ETF + マクロニュース → 市場レジーム判定
  - execution/
    - order_manager.py
    - reconciler.py
    - (その他 execution 関連モジュールはコードベースに依存)
  - utils/
    - __init__.py
    - process_priority.py     — psutil を使った優先度 / CPU affinity ユーティリティ

（上記は実装済みファイルの抜粋です。詳細な実装は各ファイルの docstring を参照してください。）

---

## 注意点 / 運用メモ

- DB マイグレーション:
  - monitoring_db.init_monitoring_db は idempotent（何度実行しても安全）で、既存 DB に必要カラムがない場合は ALTER で追加する処理を行います。
- 権限:
  - プロセス優先度設定や CPU affinity 変更は権限や OS に依存します。失敗した場合は警告ログを出しスキップします。
- OpenAI 呼び出し:
  - API のレート制限や一時エラーに対し指数バックオフでリトライします。失敗時は安全側にフォールバックして例外を上げない設計です（部分失敗で他データを保護）。
- ロギング:
  - 起動スクリプトは logging.basicConfig(level=logging.INFO) で基本ログ出力します。LOG_LEVEL 環境変数で Settings.log_level を変更可能。

---

## 開発者向け参照

- 各モジュールには詳細な docstring が付いています（処理フロー、フェイルセーフ、入力/出力の仕様など）。
- DuckDB による分析処理は SQL を多用し、結果は dict のリストで返される設計です（テストしやすい純粋関数化が多い）。

---

README の内容は現状のソースコード（src/kabusys/*）に基づいて作成しています。環境や運用要件に応じて .env の整備、DB の初期データ投入、ブローカー接続情報の設定などを行ってください。必要であれば README に追記する項目（CI/デプロイ手順や要件ファイルなど）を教えてください。