# KabuSys

日本株自動売買システムのコードベース（ライブラリ＋運用ユーティリティ群）の抜粋リポジトリです。  
この README はソースに含まれる主要モジュールの概要、機能一覧、セットアップ・実行方法、ディレクトリ構成を日本語でまとめたものです。

注意: 実運用前に必ず .env や環境変数・権限・APIキーの管理を行ってください。

---

## プロジェクト概要

KabuSys は日本株の自動売買システムを構成するコンポーネント群です。主に以下を提供します。

- Execution（発注ロジック、OrderManager、Reconciler 等）
- Monitoring（システム監視、注文監視、リスク監視、LINE アラート、ダッシュボード）
- Portfolio（候補選定・重み付け・ポジションサイズ計算・セクター制約）
- Research（ファクター計算・将来リターン・IC 計算等の分析ツール）
- AI ユーティリティ（ニュースのセンチメント推定、レジーム判定）
- 運用スクリプト（ExecutionEngine / Monitoring の起動、Paper Trading レポート等）

設計方針の要点：
- DuckDB / SQLite によるデータ永続化
- 環境変数 / .env による設定管理（自動ロード機能あり）
- 本番 / paper_trading の分離（paper_trading は専用 SQLite DB を使用）
- LLM 呼び出しは失敗耐性・リトライ・バリデーションを備える

---

## 主な機能一覧

- Execution
  - OrderManager: 注文作成・送信・同期ロジック（重複検知・クラッシュ安全）
  - Reconciler: 起動時リコンシリエーション（未確定注文とブローカー照合、ポジション差分検出）
  - ExecutionEngine（参照のみ）: 実際の取引セッションを回す想定

- Monitoring
  - SystemMonitor: CPU/メモリ/ディスク/プロセス生存／データ鮮度監視
  - TradeMonitor: 注文滞留（stale）・約定価格異常検出
  - RiskMonitor: ドローダウン検出・ポジション数上限監視（ハイウォーターマーク管理）
  - KillSwitch: 必要時にフラグファイルを作成して Execution を停止する仕組み
  - AlertManager: LINE Messaging API による通知（クールダウン管理）
  - MonitoringEngine: 各監視を束ねたポーリングエンジン
  - Streamlit ダッシュボード（read-only で monitoring DB を表示）

- Portfolio（純粋関数）
  - 候補選定（スコア順ソート）
  - 等分配 / スコア加重配分
  - セクター集中制限の適用
  - ポジションサイズ計算（risk_based / equal / score、単元株丸め、aggregate cap）

- Research
  - ファクター計算（Momentum / Volatility / Value）
  - 将来リターン計算、IC（Spearman）計算、統計サマリ

- AI
  - news_nlp.score_news: OpenAI（gpt-4o-mini）でニュースの銘柄別センチメントを計算して ai_scores に書き込む
  - regime_detector.score_regime: ETF 1321 の MA200 乖離とマクロニュースセンチメントを合成して market_regime を作成

- 運用ツール
  - run_monitoring.py: SystemMonitor ポーリングループ起動
  - run_execution.py: ExecutionEngine 起動（paper_trading モード時は MockBroker 使用）
  - tools/paper_verification_report.py: paper_trading DB を解析して検証レポート生成

---

## セットアップ手順（ローカル開発向け）

前提
- 推奨 Python バージョン: 3.10+
  - 型ヒントで `X | Y` を使っているため少なくとも 3.10 以上を想定しています。

必要パッケージ（代表例）
- duckdb
- psutil
- requests
- openai
- streamlit

例（pip）
1. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 必要パッケージをインストール
   - pip install duckdb psutil requests openai streamlit

（プロジェクトに requirements.txt があればそちらを使用してください）

環境変数 / .env
- プロジェクトルート（.git や pyproject.toml のある場所）に .env / .env.local を置くことで自動読み込みされます（既存の OS 環境変数は上書きされません）。自動読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。
- 主な必須/任意環境変数:
  - JQUANTS_REFRESH_TOKEN（必須）
  - KABU_API_PASSWORD（必須）
  - OPENAI_API_KEY（AI 機能を使う場合）
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - SQLITE_PATH（監視DB デフォルト: data/monitoring.db）
  - DUCKDB_PATH（DuckDB デフォルト: data/kabusys.duckdb）
  - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB デフォルト: data/paper_trading.db）
  - PAPER_FILL_MODE（paper_trading の注文約定モード: instant|partial|never|reject）（デフォルト: instant）
  - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID（AlertManager）
  - PID_FILE_PATH（デフォルト: data/execution.pid）
  - KILL_FLAG_PATH（デフォルト: data/kill.flag）
  - MONITOR_POLL_INTERVAL（run_monitoring のポーリング秒、デフォルト 60）

データディレクトリ
- デフォルトの DB 等は `data/` 下を想定しています。必要に応じ `data/` を作成しておいてください。
  - data/monitoring.db
  - data/paper_trading.db
  - data/kabusys.duckdb

注意: SQLite/DuckDB ファイルのパーミッションとプロセス間での排他に注意してください。

---

## 使い方（実行例）

基本的にパッケージ内スクリプトをモジュール実行します（プロジェクトルートから実行）。

- 監視ループ起動（SystemMonitor 単体）
  - MONITOR_POLL_INTERVAL でポーリング秒を指定できます（例: 30 秒）
  - 実行:
    - python -m kabusys.run_monitoring
    - または MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- 実行エンジン起動（注文発行・リスク管理等）
  - paper_trading モードでは専用 DB を使用し MockBrokerClient を使う（環境: KABUSYS_ENV=paper_trading）
  - 実行:
    - python -m kabusys.run_execution
    - paper_trading: KABUSYS_ENV=paper_trading python -m kabusys.run_execution

- Streamlit ダッシュボード（監視用、読み取り専用）
  - 起動例:
    - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間を指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB を指定:
    - python -m kabusys.tools.paper_verification_report --db data/paper_trading.db

- AI 処理
  - ニューススコア:
    - Python から直接: from kabusys.ai.news_nlp import score_news
      - score_news(conn, target_date, api_key=None)
  - レジーム判定:
    - from kabusys.ai.regime_detector import score_regime
      - score_regime(conn, target_date, api_key=None)
  - いずれも OPENAI_API_KEY（または api_key 引数）が必要です。

ログレベル
- Settings.log_level によりログレベルを制御できます（環境変数 LOG_LEVEL）。

プロセス優先度・PID 管理
- 起動スクリプトは最初に set_process_priority("high") を呼んでプロセス優先度を上げます（psutil による権限依存）。PID ファイルは Settings.pid_file_path（デフォルト data/execution.pid）を使用します。
- KillSwitch は data/kill.flag を作成して Execution を停止させる仕組みです。クリアは KillSwitch.clear() または Execution 起動時の設定で行えます。

---

## 主要ファイル / ディレクトリ構成

（抜粋。実装全体は src/kabusys 以下を参照してください）

- src/kabusys/
  - __init__.py
  - config.py
    - Settings クラス（.env 自動ロード・必須チェック）
  - run_monitoring.py
    - SystemMonitor を使ったポーリングループのエントリポイント
  - run_execution.py
    - ExecutionEngine の起動スクリプト（paper_trading をサポート）
  - monitoring/
    - monitoring_db.py — SQLite テーブル初期化・MonitoringDB クラス（永続化層）
    - system_monitor.py — CPU/メモリ/ディスク/データ鮮度/プロセスチェック
    - trade_monitor.py — 注文滞留・約定異常検出
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — フラグファイルによる停止トリガ
    - alert_manager.py — LINE による通知（クールダウン付き）
    - monitoring_engine.py — 監視コンポーネント束ねるエンジン
    - streamlit_dashboard.py — 監視ダッシュボード（Streamlit）
  - execution/
    - order_manager.py — 注文状態遷移・送信処理
    - reconciler.py — 起動時の注文/ポジション再同期
    - （その他: broker_factory, execution_engine, order_repository など）
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py — 発注株数計算・aggregate cap
    - risk_adjustment.py — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py — Momentum/Volatility/Value の計算（DuckDB）
    - feature_exploration.py — 将来リターン・IC・統計サマリ
  - ai/
    - news_nlp.py — ニュースの LLM によるセンチメント計算と書き込み
    - regime_detector.py — MA200 と LLM を使った市場レジーム判定
  - tools/
    - paper_verification_report.py — Paper Trading の検証レポート生成

---

## 設定の主要ポイント（Settings）

- 自動読み込み
  - プロジェクトルートに .env / .env.local があれば自動でロード（OS 環境優先）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化

- 主な設定項目（代表）
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD — 外部 API 用の必須秘密情報
  - KABUSYS_ENV — 実行環境識別: development | paper_trading | live
  - PAPER_FILL_MODE — paper_trading の約定動作（instant|partial|never|reject）
  - SQLITE_PATH / PAPER_TRADING_SQLITE_PATH / DUCKDB_PATH
  - PID_FILE_PATH / KILL_FLAG_PATH
  - CPU/MEM/DISK 閾値: CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT

---

## トラブルシューティング（よくある注意点）

- DB ロック / パーミッション
  - SQLite/DuckDB ファイルへのアクセス権限を確認してください。複数プロセスからの同時書き込みは注意が必要です（特に network drive 上等）。
- OPENAI_API_KEY
  - AI 機能を利用する場合は必須。未設定だと例外を投げる箇所があります（score_news/score_regime）。
- psutil 権限
  - set_process_priority / cpu_affinity は権限やプラットフォームに依存します。失敗すると警告が出ますが処理は継続します。
- pid ファイルの整合性
  - system_monitor は PID ファイルの stale 検出と削除を行います。PID ファイルの内容が不正だと削除されることがあります。
- MONITOR_POLL_INTERVAL
  - run_monitoring のポーリング間隔は環境変数で上書き可能。無効な値の場合はデフォルト 60 秒にフォールバックされます。

---

## 開発・拡張のヒント

- DuckDB のクエリ最適化やインデックス設計はパフォーマンスに影響します。research / ai のクエリは適宜最適化してください。
- LLM 呼び出しは入出力のバリデーション・リトライが実装されていますが、モデルや API の変更に伴ってレスポンスパース処理を見直す必要がある場合があります。
- 単体テストは各純粋関数（portfolio、research、monitoring の一部）から作成しやすい設計です。DB アクセスは sqlite の in-memory を使うとテストしやすいです。

---

必要であればこの README を元にさらに「インストール手順（requirements.txt の例）」や「運用手順書（systemd/pm2 等）」、あるいは各モジュールの API ドキュメント（関数の引数/戻り値の詳細）を追加で作成できます。どの部分を詳述したいか指示してください。