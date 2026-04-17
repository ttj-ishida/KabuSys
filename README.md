# KabuSys

日本株向けの自動売買／リサーチ／監視システムのコードベースです。本 README はプロジェクト概要、主要機能、セットアップ手順、使い方、ディレクトリ構成を日本語でまとめたものです。

注意: この README はリポジトリ内のソースコード（src/kabusys 以下）に基づいて作成しています。

---

## プロジェクト概要

KabuSys は以下の責務を持つモジュール群で構成された自動売買プラットフォームです。

- 注文管理・発注（ExecutionEngine, OrderManager, BrokerClient）
- 監視（MonitoringEngine, SystemMonitor, TradeMonitor, RiskMonitor, AlertManager）
- ポートフォリオ構築（候補選定、重み付け、ポジションサイズ計算、セクター制約）
- リサーチ（ファクター計算、特徴量探索、将来リターン・IC 計算）
- AI 支援（ニュースセンチメント、マクロレジーム判定 - OpenAI 利用）
- 運用補助ツール（Paper Trading 検証レポート、Streamlit ダッシュボード等）

設計方針として、以下が重視されています。

- 本番 DB と Paper Trading の分離
- ルックアヘッドバイアス防止（target_date の扱いに配慮）
- フェイルセーフ（API 失敗時は安全なデフォルトで継続）
- モジュール毎に純粋関数・副作用の分離（DB 書き込みは専用レイヤで管理）

---

## 主な機能一覧

- Execution
  - 注文作成・送信・同期（OrderManager、ExecutionEngine、Reconciler）
  - リコンシリエーション（再起動後の状態同期）
  - Paper Trading モード（MockBroker による完全分離、data/paper_trading.db）
- Monitoring
  - システムリソース監視（CPU/メモリ/ディスク）
  - データ鮮度チェック（DuckDB の prices_daily）
  - 注文滞留・約定異常検出
  - ドローダウン・ポジション上限監視
  - Kill Switch（閾値到達で ExecutionEngine に停止フラグを書き込み）
  - LINE への通知（AlertManager）
  - Streamlit ベースのダッシュボード表示
- Portfolio Construction
  - 候補選定（スコア/ランク基準）
  - 重み付け（等金額・スコア加重）
  - セクターキャップ適用
  - ポジションサイズ決定（risk_based / equal / score）
- Research
  - Momentum / Volatility / Value ファクター計算（DuckDB 利用）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリ
- AI
  - ニュース記事のセンチメントスコア付与（OpenAI を利用）
  - マクロニュース + ETF MA200 を用いた市場レジーム判定（OpenAI を利用）
- Tools
  - Paper Trading 検証レポート生成スクリプト
  - Streamlit ダッシュボード起動スクリプト

---

## セットアップ手順

前提:
- Python 3.9+（ソースは型アノテーション等を利用）
- SQLite（標準ライブラリで利用可能）
- 任意で DuckDB、OpenAI クライアント、psutil、streamlit 等のパッケージが必要

1. リポジトリをクローン／展開
   - ソースルートに `src` ディレクトリがあることを想定しています。

2. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージのインストール
   - 代表的な依存パッケージ:
     - duckdb
     - psutil
     - requests
     - openai
     - streamlit
   - 例:
     - pip install duckdb psutil requests openai streamlit

   （プロジェクトに requirements.txt がある場合はそちらを使用してください。）

4. データディレクトリ作成
   - デフォルトで使われるファイルは `data/` 配下に配置されます。
     - mkdir -p data

5. 環境変数（.env）を準備
   - 自動ロード機能により、プロジェクトルートの `.env` / `.env.local` が読み込まれます（OS 環境変数が優先）。
   - 重要な環境変数例:
     - JQUANTS_REFRESH_TOKEN (必須)
     - KABU_API_PASSWORD (必須)
     - OPENAI_API_KEY (AI 機能を使う場合)
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
     - PAPER_FILL_MODE (instant | partial | never | reject) — Paper Trading 用
     - PAPER_TRADING_SQLITE_PATH — Paper Trading DB パス（デフォルト data/paper_trading.db）
     - SQLITE_PATH — 監視用 SQLite（デフォルト data/monitoring.db）
     - DUCKDB_PATH — DuckDB ファイル（デフォルト data/kabusys.duckdb）
     - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — LINE 通知用
     - LOG_LEVEL — ログレベル（DEBUG/INFO/...）
   - 例の `.env` エントリ:
     - JQUANTS_REFRESH_TOKEN=...
     - KABU_API_PASSWORD=...
     - OPENAI_API_KEY=...
     - KABUSYS_ENV=development

6. 権限・プラットフォーム注意
   - プロセス優先度を上げる処理（psutil.nice など）は管理者権限を要求する場合があります。失敗した場合はログにワーニングが出て処理は継続します。

---

## 使い方

以下は主要な実行手順とコマンド例です。プロジェクトルートで実行することを想定しています（`src` がパッケージとしてパスにあるか、`python -m` を利用）。

1. 監視ループの起動（Monitoring）
   - モジュール実行:
     - python -m kabusys.run_monitoring
   - 環境変数:
     - MONITOR_POLL_INTERVAL: ポーリング間隔（秒、デフォルト 60）。1 未満や不正値はデフォルトにフォールバック。
   - 停止:
     - プロジェクトルートの `data/stop_requested.flag` を作成すると次回ループで検出して終了します（スクリプト内に STOP_FLAG が定義されています）。

2. Execution エンジンの起動（発注エンジン）
   - モジュール実行:
     - python -m kabusys.run_execution
   - 動作モード:
     - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を用い、Paper Trading 用の専用 SQLite（PAPER_TRADING_SQLITE_PATH、デフォルト data/paper_trading.db）に記録して本番 DB と完全分離します。
   - 停止:
     - `data/stop_requested.flag` を作成すると、実行スレッドが検知して停止を試みます。
   - PID ファイル:
     - 実行時に PID を data/execution.pid に書く設計になっています（Settings.pid_file_path を参照）。

3. Streamlit ダッシュボード（監視表示）
   - 起動コマンド例:
     - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
   - read-only で SQLite を開いてダッシュボードを表示します（MonitoringEngine が書き込むことが前提）。
   - DB が見つからない／読み込みできない場合はエラーメッセージが表示されます。

4. Paper Trading 検証レポート（ツール）
   - コマンド:
     - python -m kabusys.tools.paper_verification_report
     - 期間指定例:
       - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
     - DB 指定:
       - --db PATH で SQLite ファイルを指定（環境変数 PAPER_TRADING_SQLITE_PATH が優先されます）。
   - 出力:
     - 稼働率、注文成功率、送信率、レイテンシ（P95 など）を計算して PASS/FAIL 判定を行います。

5. AI 関連（プログラムから利用）
   - ニューススコア付与:
     - kabusys.ai.score_news(conn, target_date, api_key=None)
     - conn は DuckDB 接続（duckdb.connect(...) の返り値）
     - api_key 未指定時は環境変数 OPENAI_API_KEY を参照
   - 市場レジーム判定:
     - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
   - 注意:
     - OpenAI API 呼び出しには API キーが必要。レスポンスの種類によってはリトライやフォールバックが行われます（エラー時のフェイルセーフが実装されています）。

6. プログラム的に各モジュールを利用する
   - パッケージから直接インポートして利用できます（例: kabusys.portfolio.calc_position_sizes など）。
   - DuckDB 接続を渡してリサーチ関数を実行する設計です。

---

## 設定（Settings）概観

設定は `kabusys.config.Settings` で取得します。自動的にプロジェクトルートの `.env` / `.env.local` をロードします（OS 環境変数が優先）。自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

主要な環境変数（抜粋）:

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- OPENAI_API_KEY (AI 機能を使う場合)
- KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
- LOG_LEVEL (DEBUG|INFO|...)
- SQLITE_PATH (監視 DB, デフォルト data/monitoring.db)
- DUCKDB_PATH (duckdb ファイル, デフォルト data/kabusys.duckdb)
- PAPER_FILL_MODE (instant|partial|never|reject)
- PAPER_TRADING_SQLITE_PATH (Paper Trading 用 DB パス)
- PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START など

Settings クラスはプロパティメソッドとして値検証やデフォルト解決を行います。

---

## 停止・フェイル操作

- stop_requested.flag
  - run_monitoring.py / run_execution.py はプロジェクトルートの `data/stop_requested.flag` を監視しており、存在を検出すると安全に停止処理を行います（起動前に存在する場合は run_execution は起動を避けます）。
- kill.flag
  - KillSwitch（監視側）によって条件に合致すると `data/kill.flag` に理由を書き込み、ExecutionEngine 側は Settings.kill_flag_path を参照して停止する設計を想定できます。
  - KillSwitch は冪等に書き込みを行い、存在する場合は再書き込みを行いません。
- PID ファイル
  - ExecutionEngine は PID ファイルを利用してプロセスの存在を確認する仕組み（stale PID の検出・削除）があります。

---

## ディレクトリ構成（主要ファイル）

以下は `src/kabusys` 以下の主要ファイルと機能の簡潔な説明です。

- kabusys/
  - __init__.py — パッケージメタ情報（__version__ 等）
  - config.py — 環境変数 / .env 読み込みと Settings クラス
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py — ExecutionEngine 起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成 CLI
  - utils/
    - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ
  - monitoring/
    - monitoring_db.py — SQLite ベースの監視ログ永続化（テーブル初期化・CRUD）
    - monitoring_engine.py — 各 Monitor を束ねるポーリング Engine
    - system_monitor.py — システムリソース & データ鮮度監視
    - trade_monitor.py — 注文滞留・約定異常検出
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - alert_manager.py — LINE 通知
    - kill_switch.py — 停止フラグの生成/管理
    - streamlit_dashboard.py — Streamlit ベースの監視ダッシュボード
  - execution/
    - reconciler.py — 起動時自動復旧・照合ロジック
    - order_manager.py — 注文作成・発注フロー管理（State Machine）
    - order_repository.py — Orders DB 操作（ファイル内に存在）
    - order_record.py — OrderRecord / OrderState 定義
    - execution_engine.py — 実行エンジン（スケジューリング・セッション管理）
    - broker_factory.py / broker_api.py — ブローカークライアント関連
    - risk_manager.py — リスク管理ロジック
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py — 株数決定・スケールダウンロジック
    - risk_adjustment.py — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py — モメンタム/ボラティリティ/バリュー計算
    - feature_exploration.py — 将来リターン・IC・統計サマリ
  - ai/
    - news_nlp.py — ニュース NLP（OpenAI）による銘柄別センチメント評価
    - regime_detector.py — マクロ + ETF MA200 を合成したレジーム判定
  - data/ (実行時に生成される想定)
    - monitoring.db (デフォルト)
    - paper_trading.db (Paper Trading 用)
    - kabusys.duckdb (DuckDB ファイル)
    - execution.pid, stop_requested.flag, kill.flag など

---

## 開発・運用時の注意点

- データ鮮度:
  - SystemMonitor は DuckDB の prices_daily テーブルの最終日付を見てデータ鮮度を判定します。価格データが欠けているとアラート対象になります。
- DB マイグレーション:
  - monitoring_db.init_monitoring_db は冪等でテーブルを作成し、既存スキーマに列が足りない場合の簡単なマイグレーションを行います（例: dashboard.peak_value, trade_logs.latency_ms）。
- Paper Trading:
  - Paper Trading は本番 DB と完全に分離された SQLite を使うように設計されています（PAPER_TRADING_SQLITE_PATH / KABUSYS_ENV）。
- OpenAI 利用:
  - API レート制限、429、ネットワークエラー、5xx などに対するエクスポネンシャルバックオフやフォールバックが実装されていますが、API キーの管理とコストに注意してください。
- 権限:
  - process priority / cpu affinity の設定は OS と権限に依存します。許可がない場合はログに警告が出て処理は継続します。

---

## トラブルシュート（よくある課題と確認箇所）

- モジュールが .env を読み込まない:
  - Settings の自動読み込みはプロジェクトルート検出（.git または pyproject.toml）に依存します。CI やテストで意図的に自動読み込みを無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- DuckDB / SQLite のファイルが見つからない:
  - デフォルトパスは `data/kabusys.duckdb`、`data/monitoring.db`、`data/paper_trading.db` です。必要に応じて環境変数で上書きしてください。
- OpenAI のレスポンスパースエラー:
  - news_nlp/regime_detector は JSON モードを使いつつガード処理を行いますが、想定外のレスポンスが返る場合はログを確認してください。
- LINE 通知が届かない:
  - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID が正しく設定されているか、API のレスポンスコード（非2xx）をログで確認してください。

---

以上が README の要点です。実際に導入・運用する際は、環境変数やデータベースのバックアップ、OpenAI 利用料の監視、監視アラートの受信確認などを踏まえた運用設計を推奨します。

追加で以下のいずれかが必要でしたら対応します:
- .env.example のテンプレート作成
- requirements.txt の候補リスト生成
- 起動スクリプトの systemd ユニット例（Ubuntu 等）
- 詳細な API や内部データ構造のドキュメント（個別ファイルごと）