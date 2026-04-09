# KabuSys

KabuSys は日本株の自動売買・リサーチ・監視を目的とした軽量なライブラリ群です。ポートフォリオ構築、ポジションサイズ計算、マーケットレジーム判定、ニュースの NLP スコアリング、注文実行エンジンや監視ダッシュボードなど、トレーディング運用に必要な主要コンポーネントを収めています。

---

## プロジェクト概要

- 設計方針は「安全性とフェイルセーフ」を重視：ルックアヘッドバイアスを避ける設計、API 失敗時はフォールバックを行う、部分失敗で既存データを保護するなど。
- DB 層には DuckDB（時系列・ファクター計算用）と SQLite（監視ログ・注文 DB 等）を想定。
- OpenAI（gpt-4o-mini）を用いたニュース／マクロセンチメント評価機能を提供。
- 実行エンジン（ExecutionEngine）はシグナル処理・push ドレイン・リコンシリエーション・kill switch に対応。
- ほとんどの計算ロジックは副作用を持たない純粋関数として実装されており、ユニットテストやリサーチに適しています。

---

## 主な機能一覧

- 設定管理
  - .env / 環境変数の自動読み込み（プロジェクトルートの検出あり）
  - 必須変数未設定時の検出

- ポートフォリオ構築（kabusys.portfolio）
  - 候補選定 (select_candidates)
  - 等金額配分 / スコア配分 (calc_equal_weights / calc_score_weights)
  - ポジションサイズ決定（risk-based / equal / score）
  - セクター比率制限・レジーム乗数適用

- リサーチ（kabusys.research）
  - モメンタム/ボラティリティ/バリュー等のファクター計算（DuckDB を直接クエリ）
  - 将来リターンの計算、IC（スピアマンランク相関）、統計サマリ

- AI（kabusys.ai）
  - ニュース記事のセンチメントスコア付与（OpenAI）
  - 市場レジーム判定（ETF ma200 + マクロニュース LLM 評価の合成）

- 監視（kabusys.monitoring）
  - SQLite ベースの永続化（MonitoringDB, init_monitoring_db）
  - System / Trade / Risk の監視ロジック
  - KillSwitch（フラグファイルで ExecutionEngine 停止）
  - LINE push によるアラート送信（AlertManager）
  - Streamlit ダッシュボード（streamlit_dashboard.py）

- 実行（kabusys.execution）
  - Broker API の抽象（Protocol / データモデル / 例外）
  - OrderManager（注文状態遷移・send/cancel/sync）
  - Reconciler（起動時のリコンシリエーション）
  - ExecutionEngine（シグナルループ + push ドレイン、kill flag 管理）

---

## 必要条件（主な依存パッケージ）

- Python 3.10+
- duckdb
- openai
- requests
- psutil
- streamlit（ダッシュボードを使う場合）
- sqlite3 は標準ライブラリで利用可

（プロジェクトで実際に使うパッケージは requirements.txt / pyproject.toml に合わせてください）

---

## セットアップ手順（ローカル）

1. リポジトリをクローン
   - git clone <repo_url>

2. 仮想環境の作成（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install duckdb openai requests psutil streamlit

   （実際はプロジェクトの requirements.txt / pyproject.toml を使ってください）

4. 環境変数設定
   - プロジェクトルート（.git または pyproject.toml のある場所）を基準に自動で `.env` と `.env.local` を読み込みます。
   - 自動読み込みを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。
   - `.env` の例は .env.example（存在する場合）を参照のこと。

5. 監視 DB 初期化（SQLite）
   - Python で MonitoringDB を使う場合は init_monitoring_db(conn) を呼んでテーブルを作成してください。

---

## 環境変数（主なもの）

KabuSys の Settings クラスで参照される主要な環境変数：

- JQUANTS_REFRESH_TOKEN — J-Quants API（必須）
- KABU_API_PASSWORD — kabu ステーション API パスワード（必須）
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY — OpenAI API キー（ai モジュールで使用）
- LINE_CHANNEL_ACCESS_TOKEN — LINE Push 用トークン（AlertManager）
- LINE_USER_ID — LINE ユーザー ID（AlertManager）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite ファイルパス（デフォルト: data/monitoring.db）
- PAPER_FILL_MODE — Paper Trading の fill モード（instant/partial/never/reject）
- PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- PID_FILE_PATH — PID ファイルパス（デフォルト: data/execution.pid）
- KILL_FLAG_PATH — kill.flag のパス（デフォルト: data/kill.flag）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動削除するか（"1" で有効）
- CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT — 監視閾値
- KABUSYS_ENV — development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — DEBUG/INFO/WARNING/ERROR/CRITICAL

.env の読み込み順位:
1. OS 環境変数（最優先）
2. .env（プロジェクトルート）
3. .env.local（.env の後で上書き、OS 環境変数は保護）

注意: .env 読み込みではクォートや export 文など一般的な .env 構文をある程度サポートします。

---

## 使い方（代表的な例）

- 設定利用
  - from kabusys.config import settings
  - settings.jquants_refresh_token, settings.duckdb_path などで取得

- リサーチ系（DuckDB 接続が必要）
  - import duckdb
  - conn = duckdb.connect("data/kabusys.duckdb")
  - from kabusys.research import calc_momentum, calc_volatility, calc_value
  - records = calc_momentum(conn, target_date)

- AI（ニューススコアリング）
  - from kabusys.ai.news_nlp import score_news
  - n_written = score_news(conn, target_date, api_key="sk-...")  # api_key None の場合は OPENAI_API_KEY を参照

- レジーム判定
  - from kabusys.ai.regime_detector import score_regime
  - score_regime(conn, target_date, api_key="sk-...")

- 監視 DB 初期化
  - import sqlite3
  - conn = sqlite3.connect("data/monitoring.db")
  - from kabusys.monitoring.monitoring_db import init_monitoring_db
  - init_monitoring_db(conn)

- Streamlit ダッシュボード
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- 実行エンジン（概要）
  - ExecutionEngine は BrokerAPIProtocol 実装、OrderRepository、RiskManager、OrderManager、DuckDB 接続などを組み合わせて動作します。
  - テストや運用では run_session() を呼んでセッションを実行します（PID ファイル書き込み・kill.flag チェックを行う）。

- リコンシリエーション
  - from kabusys.execution.reconciler import Reconciler
  - rec = Reconciler(broker, repo, order_manager); result = rec.run()

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py — パッケージ情報
- config.py — 環境変数・設定管理
- ai/
  - news_nlp.py — ニュース NLP スコアリング
  - regime_detector.py — マーケットレジーム判定
  - __init__.py
- portfolio/
  - portfolio_builder.py — 候補選定・配分ロジック
  - position_sizing.py — 株数決定・スケーリング
  - risk_adjustment.py — セクターキャップ・レジーム乗数
  - __init__.py
- research/
  - factor_research.py — 各種ファクター計算（momentum/value/volatility）
  - feature_exploration.py — 将来リターン・IC・統計サマリ
  - __init__.py
- monitoring/
  - monitoring_db.py — SQLite 永続化層
  - system_monitor.py, trade_monitor.py, risk_monitor.py — 各種監視ロジック
  - kill_switch.py — フラグファイル制御
  - monitoring_engine.py — 監視の総合エンジン
  - alert_manager.py — LINE 通知
  - streamlit_dashboard.py — ダッシュボード
  - __init__.py
- execution/
  - broker_api.py — Broker API 抽象（型・例外）
  - order_manager.py — 注文状態機械（OrderManager）
  - order_repository.py — （注文 DB 操作、未列挙の実装想定）
  - reconciler.py — 起動時リコンシリエーション
  - execution_engine.py — 実行エンジン
  - ...（その他 execution 関連）
- monitoring/、research/、portfolio/…（上記のサブパッケージ群）

---

## 開発・テストのヒント

- 多くの関数は副作用が無い（pure function）ように実装されているため、DuckDB や SQLite の軽量なテストデータを用意して単体テストを書くのが簡単です。
- AI モジュールは OpenAI API 呼び出しをラップした関数を内部で使っているため、ユニットテストでは _call_openai_api をモックすることが想定されています（コメントでその旨が明記されています）。
- .env 読み込みの自動動作はテストで邪魔になることがあるため、テスト環境では環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して無効化できます。

---

## 注意事項・運用上のポイント

- AI API 呼び出しや外部ブローカー連携は課金・実取引に直結するため、ローカル実行では必ずテスト用キーやモックを使用してください。
- ExecutionEngine は kill.flag と PID ファイルを用いて外部からの停止や二重起動抑止を行います。運用時にはこれらファイルの存在・パーミッションを確認してください。
- Paper Trading 用の設定（PAPER_FILL_MODE 等）があり、動作を切り替えて実トレードと分離できます。
- セキュリティ：API キーやパスワードは .env に直接置かず、安全なシークレット管理を推奨します。

---

必要があれば README に以下を追加します：
- 具体的な .env.example のテンプレート
- 各モジュールの API 使用例（コードスニペット）
- 実行フロー図（シグナル → 発注 → push → リスク監視）
- テストコマンド / CI 設定例

どの内容を優先して追加しますか？