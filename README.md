# KabuSys

日本株向けの自動売買／リサーチ／監視フレームワーク（軽量プロトタイプ）。

このリポジトリは、戦略のシグナル生成から発注、監視、Paper Trading 検証、AI を用いたニュースセンチメントや市場レジーム判定までを含むモジュール群を提供します。DB は SQLite / DuckDB を併用し、LINE による監視通知や OpenAI を用いた NLP 機能もサポートします。

---

## 主要機能

- 発注エンジン（ExecutionEngine）
  - ブローカー抽象化（実運用／Paper Trading の切替）
  - 注文状態管理・再送／同期（Reconciler）
  - リスク管理（RiskManager）
- 監視（Monitoring）
  - システム状態（CPU/Memory/Disk）・プロセス監視
  - 注文滞留・約定異常検出
  - ドローダウン／ポジション上限監視と kill.flag による停止信号
  - LINE Push によるアラート通知
  - Streamlit ベースのダッシュボード
- Portfolio Construction（候補選定、重み算出、ポジションサイズ算出、セクター制約）
- Research（ファクター計算、将来リターン、IC 計算、統計サマリ）
- AI（OpenAI を用いたニュースセンチメント、レジーム判定）
- ユーティリティ
  - プロセス優先度 / CPU affinity 設定ユーティリティ
  - .env 自動ロード（プロジェクトルートを探索）

---

## 動作要件

- Python 3.10+
- 必須ライブラリ（例）
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit (ダッシュボード利用時)
- 標準ライブラリ: sqlite3 等

（requirements.txt がある場合はそれを利用してください。なければ上のパッケージを pip でインストールしてください。）

例:
python -m pip install duckdb psutil requests openai streamlit

---

## セットアップ手順

1. リポジトリをチェックアウト
2. 仮想環境を作成して有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）
3. 依存ライブラリをインストール
   - pip install -r requirements.txt  （存在する場合）
   - または: pip install duckdb psutil requests openai streamlit
4. 環境変数の設定
   - プロジェクトルートに `.env`（または `.env.local`）を作成できます。
   - 自動ロードはデフォルトで有効（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
5. 必須環境変数（実行に必須）
   - JQUANTS_REFRESH_TOKEN — J-Quants API 用トークン
   - KABU_API_PASSWORD — kabuステーション API 用パスワード
   - OPENAI_API_KEY — OpenAI を使用する機能のときに必要
6. データディレクトリ
   - デフォルトの DB パス:
     - DuckDB: data/kabusys.duckdb
     - SQLite（監視用）: data/monitoring.db
     - Paper Trading SQLite: data/paper_trading.db (KABUSYS_ENV=paper_trading の場合)
   - 必要に応じて環境変数で上書き可能（下記を参照）。

---

## 環境変数（主なもの）

- KABUSYS_ENV — 実行モード（development / paper_trading / live）。デフォルト: development
- JQUANTS_REFRESH_TOKEN — 必須（J-Quants API）
- KABU_API_PASSWORD — 必須（kabu API）
- OPENAI_API_KEY — AI 機能（news/regime）使用時に必要
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE — Paper Trading の約定モード（instant / partial / never / reject、デフォルト: instant）
- PID_FILE_PATH — ExecutionEngine の PID ファイル（デフォルト: data/execution.pid）
- KILL_FLAG_PATH — kill.flag（デフォルト: data/kill.flag）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag をクリアする場合は "1"
- MONITOR_POLL_INTERVAL — monitoring のポーリング間隔（秒、デフォルト: 60）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — LINE Push 通知用（未設定なら送信はスキップ）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...。デフォルト INFO）
- CPU/MEM/DISK 閾値などの監視設定（CPU_THRESHOLD_PCT 等）

※ .env 自動ロード: プロジェクトルート（.git または pyproject.toml がある階層）から `.env` と `.env.local` を読み込みます。OS の環境変数は保護され、.env.local は上書き可。

---

## 使い方（実行コマンド）

- Execution (本番 / paper_trading を切り替えて起動)
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading を設定すると Paper Trading 用クライアントが使われ、Paper DB に記録されます。
  - 起動時はプロセス優先度を "high" に設定します（権限がない場合は警告を出してスキップ）。

- Monitoring: シンプルなポーリングループ
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を変更可能（デフォルト 60）。
  - 監視は常に監視用 SQLite（Settings.sqlite_path）を使用します。

- Streamlit ダッシュボード
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - monitoring.db を読み取り専用で開き、概要・ポジション・注文・システム状態を表示します。

- Paper Trading 検証レポート（コマンドライン）
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db オプションあるいは PAPER_TRADING_SQLITE_PATH 環境変数で DB パスを指定可能。
  - 検証項目: 稼働率、注文成功率、送信率、P95 レイテンシ など。合否基準はソース内の定数で定義。

- AI モジュール（プログラムから呼び出し）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
    - DuckDB 接続・target_date を渡してニュースセンチメントを ai_scores テーブルへ書き込みます。
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
    - ETF 1321 の MA200 乖離とマクロニュースを合成して market_regime テーブルへ書き込みます。
  - いずれも OPENAI_API_KEY（引数 or 環境変数）が必要です。

---

## 実行時の挙動（ポイント）

- プロセス優先度: run_monitoring / run_execution は起動時に set_process_priority("high") を試みます（psutil を使用）。権限不足時は警告が出ます。
- Monitoring DB: init_monitoring_db() は冪等でテーブル・インデックスを作成し、既存 DB に必要カラムがなければマイグレーション（列追加）を行います。
- Kill Switch: RiskMonitor が閾値を満たすと kill.flag に理由を出力し、ExecutionEngine に停止信号を送る設計。KillSwitch は冪等に書き込みを行います。
- Paper Trading: KABUSYS_ENV=paper_trading の場合、ブローカーは MockBrokerClient を使用し、Paper DB（data/paper_trading.db）に完全分離して記録します。
- .env 読み込み: OS 環境変数 > .env.local > .env の優先順位で読み込まれます。自動読み込みを無効にしたいときは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

---

## ディレクトリ構成（抜粋）

- src/kabusys/
  - __init__.py — パッケージ定義、バージョン
  - config.py — 環境変数 / Settings 管理（.env 自動ロード含む）
  - run_execution.py — ExecutionEngine 起動スクリプト（main）
  - run_monitoring.py — SystemMonitor 単体ポーリング起動スクリプト
  - utils/
    - process_priority.py — プロセス優先度 / CPU affinity ユーティリティ
  - execution/
    - order_manager.py — 発注ロジックの外向き API（状態遷移・送信フロー）
    - reconciler.py — 起動時の注文・ポジション再同期
    - (そのほか broker_factory, execution_engine, order_repository 等)
  - monitoring/
    - monitoring_db.py — 監視用 SQLite テーブル定義・CRUD
    - system_monitor.py — システム状態・データ鮮度チェック
    - trade_monitor.py — 注文滞留・約定異常チェック
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — kill.flag の書き込みロジック
    - alert_manager.py — LINE Push 通知ラッパー
    - monitoring_engine.py — 各 Monitor を束ねるポーリングエンジン
    - streamlit_dashboard.py — Streamlit ダッシュボード起動スクリプト
  - portfolio/
    - portfolio_builder.py — 候補選択・重み算出
    - position_sizing.py — 発注株数算出・スケーリング
    - risk_adjustment.py — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py — モメンタム／ボラティリティ／バリュー等のファクター計算（DuckDB）
    - feature_exploration.py — 将来リターン計算、IC、統計サマリー
  - ai/
    - news_nlp.py — ニュースを OpenAI でスコアリングして ai_scores に書き込み
    - regime_detector.py — マクロ + MA200 でレジーム判定（OpenAI 使用可）
  - tools/
    - paper_verification_report.py — Paper Trading の検証レポート生成（CLI）

---

## 開発上の注意・設計上のポイント

- データベース設計は監視 DB（SQLite）と分析 DB（DuckDB）を分離：監視ログは SQLite、分析やファクター計算は DuckDB を使用。
- ルックアヘッドバイアス防止のため、日次判定関数は内部で date.today() を直接参照しない設計。
- OpenAI 呼び出しはリトライとバリデーションを実装し、失敗時はフェイルセーフ（スコア0やスキップ）で継続する設計。
- マルチモジュール間でプライベート関数を共有せず、テスト容易性を高めるため呼び出し箇所をモック可能な実装にしている（例: _call_openai_api をパッチ差し替え）。

---

## よく使うコマンドまとめ

- 実行エンジン起動:
  - python -m kabusys.run_execution
- 監視ループ起動:
  - python -m kabusys.run_monitoring
- Streamlit ダッシュボード:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- Paper 検証レポート:
  - python -m kabusys.tools.paper_verification_report --from YYYY-MM-DD --to YYYY-MM-DD
- Python モジュールから AI 処理を呼ぶ（例）:
  - from kabusys.ai import score_news
  - score_news(duckdb_conn, target_date, api_key="...")

---

README は以上です。必要であれば以下の点について README を拡張できます：

- requirements.txt / Dockerfile のサンプル
- systemd ユニットファイル例（run_execution / run_monitoring の常駐化）
- CI / テスト実行方法（ユニットテストの方針）
- 各モジュールの API ドキュメント（関数シグネチャの詳細）

どれを追加したいか教えてください。