# KabuSys — README

このリポジトリは「KabuSys」（日本株自動売買システム）のコードベースです。本 README ではプロジェクトの概要、主な機能、セットアップ手順、使い方、ディレクトリ構成を日本語で説明します。

注意: 実行には外部 API キー（例: J-Quants / kabuステーション / OpenAI など）やネイティブライブラリ（duckdb 等）が必要なコンポーネントがあります。サンプル・デフォルト設定はローカル開発用に安全に分離されています（Paper Trading 等）。

---

目次
- プロジェクト概要
- 機能一覧
- 前提・依存関係
- セットアップ手順
- 環境変数（主なもの）
- 使い方（実行コマンド・ユーティリティ）
- データファイル / フラグファイルの説明
- ディレクトリ構成（主要ファイルの説明）

---

## プロジェクト概要

KabuSys は日本株向けの自動売買フレームワークで、主に以下を提供します。

- シグナル → ポートフォリオ構築 → 注文発注（ExecutionEngine）を実行する実行系コンポーネント
- システム / 注文 / リスクの監視（MonitoringEngine）
- Paper Trading（検証用）と本番（live）を環境変数で切り替え可能
- DuckDB を用いた研究（ファクター計算・特徴量探索）
- OpenAI を用いたニュース NLP / レジーム検出モジュール
- Streamlit ベースの監視ダッシュボード、Paper Trading 検証レポート生成スクリプト

設計方針として、可能な限り「副作用なしの純粋関数」「DB 書き込みは永続層に集約」「ルックアヘッドバイアス防止」等を意識しています。

---

## 機能一覧

- 実行系（execution）
  - 注文作成・管理（OrderManager, OrderRepository）
  - ブローカー抽象化（BrokerClientFactory / MockBrokerClient を含む）
  - 起動時のリコンシリエーション（Reconciler）
  - リスク管理（RiskManager）

- 監視（monitoring）
  - SystemMonitor: CPU/メモリ/ディスク/プロセスの健全性・データ鮮度を監視
  - TradeMonitor: 注文滞留（stale orders）・約定異常価格を検出
  - RiskMonitor: ドローダウン・ポジション上限を監視、ダッシュボード更新
  - KillSwitch: 条件により ExecutionEngine を停止させるためのフラグファイル出力
  - AlertManager: LINE Messaging API による通知（オプション）
  - Streamlit ダッシュボード（read-only モードで監視 DB を可視化）

- Portfolio（portfolio）
  - 候補選定、等重/スコア重み計算、セクターキャップ適用、ポジションサイズ計算

- Research（research）
  - DuckDB を使ったファクター計算（モメンタム / ボラティリティ / バリュー）
  - 将来リターン計算、IC（Information Coefficient）、ファクター統計サマリ

- AI（ai）
  - news_nlp: raw_news を OpenAI に投げて銘柄別センチメントを ai_scores に保存
  - regime_detector: ETF（1321）MA200 とマクロニュースの LLM センチメントを合成して市場レジーム判定

- ツール（tools）
  - paper_verification_report: Paper Trading の検証レポート生成スクリプト

---

## 前提・依存関係

主な Python ライブラリ（例）
- duckdb
- psutil
- requests
- openai
- streamlit （ダッシュボード起動時）
- sqlite3（標準ライブラリ）
- その他、用途に応じて（開発環境に合わせて pip install してください）

推奨: 仮想環境（venv / poetry / pipenv 等）を使用してください。

例（pip）:
pip install duckdb psutil requests openai streamlit

※ 実行環境によってはネイティブビルドや追加ライブラリが必要になる場合があります。

---

## セットアップ手順

1. リポジトリをクローン / 取得
2. 仮想環境を作成して有効化
3. 依存ライブラリをインストール
   - 例: pip install -r requirements.txt（requirements.txt がある場合）
   - 最低限: duckdb, psutil, requests, openai, streamlit
4. データディレクトリの作成
   - デフォルトでは data/ に各 DB /フラグが作られます
     mkdir -p data
5. 環境変数を設定（.env を使用する場合）
   - .env/.env.local をプロジェクトルートに置くと自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）
   - 必須例:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - OpenAI を使う場合:
     - OPENAI_API_KEY
   - 監視通知に LINE を使う場合:
     - LINE_CHANNEL_ACCESS_TOKEN
     - LINE_USER_ID

.env の例（プロジェクトルートに .env を作る）:
JQUANTS_REFRESH_TOKEN=your_jquants_token
KABU_API_PASSWORD=your_kabu_password
OPENAI_API_KEY=your_openai_key
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
PAPER_FILL_MODE=instant

---

## 環境変数（主なもの）

- KABUSYS_ENV: 起動環境を指定（development / paper_trading / live）
  - paper_trading: MockBroker を用い、paper_trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）に記録して本番 DB と分離
- MONITOR_POLL_INTERVAL: Monitoring のポーリング間隔（秒、既定 60）
- SQLITE_PATH: 監視 DB（デフォルト data/monitoring.db）
- DUCKDB_PATH: DuckDB ファイル（デフォルト data/kabusys.duckdb）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト data/paper_trading.db）
- PAPER_FILL_MODE: paper_trading 時の約定挙動（instant / partial / never / reject）
- OPENAI_API_KEY: OpenAI API キー（ai モジュールで必要）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: AlertManager（LINE）用
- PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START 等（Settings クラス参照）

Settings クラスは .env/.env.local を自動ロードします（ただし OS 環境変数が優先）。

---

## 使い方（コマンド & 実行フロー）

以下は主要コンポーネントの起動方法です。プロジェクトルートから実行してください。

- Monitoring の起動（ポーリングループ）
  - デフォルトは本番 sqlite_path を使用（monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を参照）
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を変更できます（1 秒以上の整数）。
  - 実行:
    python -m kabusys.run_monitoring

  - 停止:
    - Ctrl+C（KeyboardInterrupt）
    - またはプロジェクト内 data/stop_requested.flag を作成するとループが検知して終了します。

- ExecutionEngine の起動（注文実行ループ）
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient/専用 DB を使用して本番と分離されます。
  - 実行:
    python -m kabusys.run_execution
  - 停止:
    - data/stop_requested.flag を作成して実行エンジンに停止を要求します。
    - 実行エンジンは pid ファイル（data/execution.pid）を管理し、stale PID の検出等を行います。

- Streamlit ダッシュボード（監視）
  - 起動:
    streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - read-only で監視 DB を表示します。DB が存在しない場合は監視エンジンを先に起動してください。

- Paper Trading 検証レポート
  - 実行:
    python -m kabusys.tools.paper_verification_report
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - オプション --db で PAPER_TRADING_SQLITE_PATH を上書き可能。

- AI / レジーム検出・ニューススコアリング
  - OpenAI API キーが必要です（OPENAI_API_KEY または引数で指定）。
  - 使用例（Python API）:
    from kabusys.ai.news_nlp import score_news
    # duckdb_conn は duckdb.connect(...) の接続
    score_news(duckdb_conn, target_date, api_key="...")

    from kabusys.ai.regime_detector import score_regime
    score_regime(duckdb_conn, target_date, api_key="...")

- 監視関連の一時停止・停止フラグ
  - data/kill.flag: KillSwitch が書き込むファイル（ExecutionEngine に停止シグナルを送るために使用）
  - data/stop_requested.flag: run_monitoring / run_execution が検知して安全に終了するための手動フラグ

---

## 注意点・運用メモ

- Monitoring は常に本番 sqlite_path（Settings.sqlite_path）を使用します。Paper Trading 時は run_execution が paper_sqlite_path を使って DB を分離します。
- run_monitoring/run_execution 起動直後にプロセス優先度を "high" に設定しようとします（プラットフォーム依存・権限により失敗することがあります）。
- .env の自動読み込みはプロジェクトルート（.git や pyproject.toml がある場所）から行われます。自動ロードを無効にしたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI 呼び出し部分はエラー時にフェイルセーフ（既定値で継続）するよう設計されていますが、API キーと利用量には注意してください。
- Paper Trading の挙動は Settings.paper_fill_mode で制御できます。許容される値は instant/partial/never/reject です。

---

## ディレクトリ構成（主要ファイル説明）

以下は src/kabusys 以下の主なモジュール／ファイルと簡単な説明です。

- src/kabusys/
  - __init__.py                — パッケージ初期化（バージョン等）
  - config.py                  — Settings クラス（環境変数・.env ロード・値検証）
  - run_monitoring.py          — SystemMonitor のポーリングループ起動スクリプト
  - run_execution.py           — ExecutionEngine 起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading の検証レポートジェネレータ
  - ai/
    - news_nlp.py              — ニュース NLP（OpenAI 経由で銘柄別スコア生成）
    - regime_detector.py       — 市場レジーム判定（MA200 + マクロニュース）
  - monitoring/
    - monitoring_db.py         — SQLite による監視ログ永続化層（init/CRUD）
    - system_monitor.py        — システム状態・データ鮮度監視
    - trade_monitor.py         — 注文滞留・約定異常監視
    - risk_monitor.py          — ドローダウン・ポジション上限監視
    - kill_switch.py           — kill.flag 書き込みユーティリティ
    - alert_manager.py         — LINE API によるプッシュ通知ユーティリティ
    - monitoring_engine.py     — 各 Monitor を束ねるエンジン
    - streamlit_dashboard.py   — Streamlit ダッシュボード（read-only）
  - execution/
    - order_manager.py        — 注文状態管理の外部 API
    - reconciler.py           — 再起動時のリコンシリエーション
    - (その他ブローカー・エンジン関連モジュールは実装済 / 一部省略)
  - portfolio/
    - portfolio_builder.py    — 候補選定・重み計算（等重・スコア重み）
    - position_sizing.py      — 発注株数計算（lot 単位丸め・aggregate cap）
    - risk_adjustment.py      — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py     — モメンタム/ボラティリティ/バリュー計算（DuckDB）
    - feature_exploration.py — 将来リターン/IC/統計サマリ等
  - utils/
    - process_priority.py    — プロセス優先度 / CPU affinity 設定ユーティリティ

その他、data/ 配下に DB ファイルやフラグファイルが置かれます（実行時に自動作成されます）。

---

## よく使うコマンド（まとめ）

- 監視ループ起動:
  python -m kabusys.run_monitoring

- 実行エンジン起動:
  python -m kabusys.run_execution

- Streamlit ダッシュボード:
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- Paper Trading 検証レポート:
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

## 最後に

この README はコードベースの主要コンポーネントと使い方を把握するための概要です。より詳細な設計仕様や API の使い方は各モジュールの docstring とソースコード中のコメントを参照してください。問題や不足事項があれば、実行ログ・例外トレース・実行環境情報を添えて問い合わせてください。