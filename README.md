# KabuSys

日本株向け自動売買フレームワーク（ミニマムプロトタイプ）。戦略の研究・ファクター計算、ポートフォリオ構築、発注エンジン、監視・アラート、LLM を使ったニュース/レジーム評価などのコンポーネントを含みます。

---

## プロジェクト概要

KabuSys は以下の用途を想定したモジュール群です。

- DuckDB に保存した時系列株価 / 財務データを用いたファクター計算・リサーチ
- ポートフォリオ構築（候補選定・重み付け・株数決定・セクター制限・レジーム乗数など）
- 発注管理（OrderManager / ExecutionEngine）とブローカー API 抽象化
- 起動時リコンシリエーション（Reconciler）で注文/ポジションの自動復旧
- ニュースセンチメントの LLM（OpenAI）による評価と市場レジーム判定
- 監視（System / Trade / Risk モニタ）と LINE 経由の通知、Streamlit ダッシュボード
- モジュールは「ビジネスロジック」と「永続化/IO」を分離する設計を志向

本 README はリポジトリ内の主要モジュール（src/kabusys）を対象にした利用ガイドです。

---

## 主な機能一覧

- 設定管理（環境変数 / .env の自動読み込み）
- ファクター計算（momentum, volatility, value 等）
- ファクター探索・IC 計算・統計サマリー
- ポートフォリオ構築：候補選定、等金額 / スコア加重、リスクベースのポジションサイズ計算
- セクター集中制限、レジームに応じた資金乗数
- ニュース NLP（OpenAI）による銘柄単位センチメントスコア生成（ai_scores へ書き込み）
- 市場レジーム判定（ETF 指標 + マクロ記事の LLM 評価の合成）
- 発注フロー：OrderManager（状態遷移を DB に永続化）、ExecutionEngine（Signal → 発注、push drain）
- Reconciler による OrderSent の自動復旧とポジション差分検出
- 監視コンポーネント：MonitoringDB（SQLite）、System/Trade/Risk Monitor、KillSwitch、AlertManager（LINE Push）
- Streamlit による監視ダッシュボード（read-only）

---

## セットアップ手順

以下は開発 / 実行のための一般的な手順例です。

1. リポジトリをクローン
   - git clone <repo-url>

2. Python 環境（仮想環境）を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - 主要な依存例（プロジェクトに requirements.txt が無い場合の参考）:
     - duckdb
     - openai
     - requests
     - psutil
     - streamlit
   - 例:
     - pip install duckdb openai requests psutil streamlit

4. 環境変数設定 / .env
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）を起点に自動で `.env` と `.env.local` を読み込みます（OS 環境変数が優先）。自動ロードはデフォルトで有効です。
   - 自動ロードを無効化する場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
   - 必須/主要な環境変数:
     - JQUANTS_REFRESH_TOKEN — J-Quants API 用（必須）
     - KABU_API_PASSWORD — Kabu ステーション API 用（必須）
     - OPENAI_API_KEY — OpenAI 呼出しが必要な機能（news/regime）で必須
     - LINE_CHANNEL_ACCESS_TOKEN — AlertManager（任意）
     - LINE_USER_ID — AlertManager（任意）
     - その他（デフォルトがあるもの）
       - KABUSYS_ENV (development | paper_trading | live) — default: development
       - LOG_LEVEL (DEBUG|INFO|...) — default: INFO
       - DUCKDB_PATH — default: data/kabusys.duckdb
       - SQLITE_PATH — default: data/monitoring.db
       - PAPER_TRADING_SQLITE_PATH — default: data/paper_trading.db
       - PID_FILE_PATH, KILL_FLAG_PATH, 等
   - .env の詳細なパース動作:
     - export KEY=val 形式をサポート
     - シングル/ダブルクォート内はエスケープを考慮
     - 非クォート値の " # " は直前が空白/タブの場合にコメントと認識
     - 自動ロード順序: OS env > .env.local > .env

5. データベース準備
   - DuckDB（価格・財務データ）ファイルを用意（デフォルト: data/kabusys.duckdb）
   - 監視用 SQLite DB を初期化:
     - Python から: 
       from sqlite3 import connect
       from kabusys.monitoring.monitoring_db import init_monitoring_db
       conn = connect("data/monitoring.db")
       init_monitoring_db(conn)

---

## 使い方（代表的な例）

- 設定の取得
  - from kabusys.config import settings
  - settings.jquants_refresh_token, settings.kabu_api_password, settings.duckdb_path など

- DuckDB / SQLite 接続の例
  - import duckdb, sqlite3
  - dconn = duckdb.connect(str(settings.duckdb_path))
  - sconn = sqlite3.connect(str(settings.sqlite_path))

- ニューススコアリング（LLM 必須）
  - from kabusys.ai.news_nlp import score_news
  - n = score_news(dconn, target_date=date(2026,3,19), api_key="sk-...")
  - api_key を指定しない場合は環境変数 OPENAI_API_KEY を参照

- 市場レジーム判定
  - from kabusys.ai.regime_detector import score_regime
  - score_regime(dconn, target_date=date(2026,3,19), api_key="sk-...")

- 監視 DB 初期化（1回）
  - from kabusys.monitoring.monitoring_db import init_monitoring_db
  - init_monitoring_db(sqlite3_conn)

- Streamlit ダッシュボード起動
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- ExecutionEngine の概略（実運用はブローカー実装が必要）
  - 必須: BrokerAPIProtocol 実装（ブローカー接続）、OrderRepository（SQLite）、RiskManager、OrderManager、Reconciler（任意）
  - 例（概念）:
    - engine = ExecutionEngine(broker, order_repo, risk_manager, order_manager, duckdb_conn, config)
    - engine.run_session()
  - ExecutionEngine は kill.flag、PID ファイル、reconciliation、WebSocket push drain 等を取り扱います。

- 監視・アラート
  - from kabusys.monitoring import AlertManager, SystemMonitor, TradeMonitor, RiskMonitor, MonitoringEngine
  - AlertManager(token, user_id) を渡して MonitoringEngine を運用できます。

---

## 主要モジュールとディレクトリ構成

（src/kabusys 以下の主要ファイル / パッケージ）

- kabusys/
  - __init__.py
  - config.py
    - 環境変数 / .env 自動読み込み、Settings クラス（アプリ設定）を提供
  - portfolio/
    - __init__.py
    - portfolio_builder.py — 候補選定、等金額/スコア加重
    - risk_adjustment.py — セクター上限・レジーム乗数
    - position_sizing.py — 株数算出・利用可能現金に基づくスケーリング
  - research/
    - __init__.py
    - factor_research.py — momentum / volatility / value ファクター計算（DuckDB 使用）
    - feature_exploration.py — 将来リターン、IC（Spearman）、統計サマリ
  - ai/
    - __init__.py
    - news_nlp.py — ニュースを集約して OpenAI へ送り、銘柄別スコアを ai_scores に書き込む
    - regime_detector.py — ETF MA とマクロニュース（LLM）を合成して market_regime を書き込む
  - monitoring/
    - __init__.py
    - monitoring_db.py — SQLite スキーマ / MonitoringDB（永続化 API）
    - system_monitor.py — CPU/Mem/Disk・データ鮮度・PID チェック
    - trade_monitor.py — 滞留注文・約定価格異常の検出
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — kill.flag による停止シグナル処理
    - alert_manager.py — LINE Push による通知
    - monitoring_engine.py — 各 Monitor を束ねて定期実行
    - streamlit_dashboard.py — Read-only Streamlit ダッシュボード（起動コマンドはファイル先頭注記参照）
  - execution/
    - broker_api.py — ブローカー API のデータモデル / Protocol / 例外定義
    - order_manager.py — Order 状態遷移とブローカー呼び出しのオーケストレーション
    - order_repository.py — （SQLite を前提とした）注文永続化レイヤ（ファイルには定義なしがあるため実装参照）
    - order_record.py — 注文の状態遷移ロジック（Enum / 日付等）
    - reconciler.py — 起動時リコンシリエーション（注文 / ポジションの突合）
    - execution_engine.py — Signal → 発注のメインエンジン（push drain を含む）
    - risk_manager.py — 発注 Gate / レート制限 / Gate 3（ポートフォリオ-level）など（ファイルはリポジトリ内実装を確認）
  - data/ (参照されるデータベースパスの既定値)
    - デフォルト DuckDB: data/kabusys.duckdb
    - 監視 SQLite: data/monitoring.db
    - Paper trading SQLite: data/paper_trading.db

---

## 実運用上の注意点 / 実装上のポイント

- 環境変数の必須チェック:
  - Settings._require は必須キーが未設定の場合 ValueError を発生させます。`.env.example` に合わせて `.env` を作成してください（リポジトリに .env.example がある想定）。
- .env 自動読み込み:
  - プロジェクトルート（.git または pyproject.toml が存在するディレクトリ）を基準に自動で .env / .env.local をロードします。OS 環境変数は上書きされません（.env.local は override=True のため .env の上書きとして扱われますが、OS 環境変数は protected されます）。
- LLM 呼び出し:
  - OpenAI API を利用する機能（news/regime）は API のレート制限や失敗に対して冗長性を設けており、失敗時はフェイルセーフ（スコア=0 など）で継続します。API キーは OPENAI_API_KEY で指定するか、各関数に api_key を渡してください。
- 発注ロジック:
  - OrderManager はクラッシュ耐性を考慮した 2 段階の永続化（OrderSent の永続化 → ブローカー呼び出し → broker_order_id の保存 → OrderAccepted）を行います。クラッシュ後は Reconciler で復旧する設計です。
- Kill Switch:
  - kill.flag を用いた安全停止を実装。KillSwitch はファイルの存在と内容で停止理由を伝えます。ExecutionEngine は起動時に kill.flag の存在を検査し、必要に応じて起動拒否または自動クリアを行います（KILL_FLAG_CLEAR_ON_START 設定）。

---

補足・開発メモ:
- 各モジュールは「DB 等の IO を受け取る / 純粋関数でロジックを実装する」方針で分離されています。単体関数は DB を直接参照しない pure 関数（例: portfolio.*）も多く、ユニットテストが書きやすい設計です。
- 実際のブローカー接続や OrderRepository 実装、RiskManager の具体化はプロダクション環境に合わせて実装/差し替えが必要です。

---

ご不明な点や README に追加したい実行例（具体的な broker 実装や OrderRepository の例、CI 用セットアップ手順等）があれば指示ください。README をその内容に合わせて拡張します。