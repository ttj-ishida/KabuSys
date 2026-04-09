# KabuSys

日本株向けの自動売買・リサーチ・監視システムのライブラリ群です。  
このリポジトリはアルゴリズムトレードのポートフォリオ構築、ポジションサイジング、ファクターリサーチ、ニュースのNLPスコアリング、実行エンジンの補助モジュール、監視ダッシュボードなどの機能を含みます。

---

## プロジェクト概要

KabuSys は以下の要件を想定して設計されています。

- DuckDB を用いた履歴データの解析（価格・財務データなど）
- OpenAI（LLM）を利用したニュース・マクロセンチメント評価（AI による補助的スコアリング）
- 実アカウント接続（kabuステーション相当）の抽象化（ブローカー API プロトコル）
- 発注管理（OrderManager / ExecutionEngine）、再起動後のリコンシリエーション
- 監視（System / Trade / Risk）と LINE を用いたアラート通知
- 監視データの永続化（SQLite）
- 研究用ユーティリティ（ファクター計算／IC計算等）は外部 API を呼ばず DuckDB のみで完結

設計上の特徴:
- 多くの関数は副作用を持たず純粋関数として実装（テスト容易）
- DB 操作や外部 API 呼び出し箇所を明確に分離
- ルックアヘッドバイアス対策（target_date を明示的に渡す設計）
- フェイルセーフ設計（API失敗時はフォールバックする等）

---

## 主な機能一覧

- 設定管理
  - 環境変数 / .env(.env.local) からの自動読み込み（プロジェクトルート検出）
  - 必須環境変数チェック（Settings クラス）
- ポートフォリオ構築（kabusys.portfolio）
  - 候補選定（select_candidates）
  - 等金額配分 / スコア加重配分（calc_equal_weights, calc_score_weights）
  - セクター集中制限（apply_sector_cap）
  - レジームに応じた投下乗数（calc_regime_multiplier）
  - ポジションサイズ算出（calc_position_sizes）
- リサーチ（kabusys.research）
  - Momentum / Volatility / Value のファクター計算（duckdb 接続を受け取る）
  - 将来リターン計算、IC（スピアマンランク相関）、統計サマリ
- AI（kabusys.ai）
  - ニュースのセンチメントスコアリング（OpenAI を利用、ai_scores へ書込）
  - 市場レジーム判定（ETF MA とマクロセンチメントを合成）
- 実行関連（kabusys.execution）
  - Broker API 抽象化（Protocol・データモデル・例外）
  - OrderManager（注文状態管理・送信・同期）
  - Reconciler（再起動時の自動復旧）
  - ExecutionEngine（シグナル読み取りと発注ロジック、push drain）
- 監視（kabusys.monitoring）
  - MonitoringDB（SQLiteでの永続化層）
  - System / Trade / Risk Monitor とアラート送信（LINE）
  - KillSwitch（ファイルフラグでの安全停止）
  - Streamlit ベースの監視ダッシュボード

---

## セットアップ手順

前提:
- Python 3.10 以上を推奨（PEP 604 の union 型（A | B）を使用）
- Git（プロジェクトルート検出用）、および pip が利用可能

1. リポジトリをクローン / 配布パッケージを展開
   ```
   git clone <this-repo-url>
   cd <repo>
   ```

2. 仮想環境作成（任意）
   ```
   python -m venv .venv
   source .venv/bin/activate  # Unix/macOS
   .venv\Scripts\activate     # Windows
   ```

3. 依存パッケージをインストール
   代表的な依存:
   - duckdb
   - openai (OpenAI Python SDK)
   - requests
   - psutil
   - streamlit (ダッシュボード用)
   ```
   pip install duckdb openai requests psutil streamlit
   ```

   （実行環境によって追加のパッケージが必要になる場合があります）

4. 環境変数設定
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env` を置くと自動読み込みされます。
   - 自動ロードを無効にする場合:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```
   - 実行前に必須の環境変数を設定してください（下に一覧を記載）。

5. Monitoring DB 初期化（SQLite）
   監視 DB を初期化するには Python から init_monitoring_db を呼ぶか、モジュールを利用する CLI を用意してください。例:
   ```python
   import sqlite3
   from kabusys.monitoring.monitoring_db import init_monitoring_db

   conn = sqlite3.connect("data/monitoring.db")
   init_monitoring_db(conn)
   ```

---

## 必要な環境変数（主なもの）

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants API 用リフレッシュトークン
- KABU_API_PASSWORD (必須) — kabu ステーション API のパスワード
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY — OpenAI API キー（ai.news_nlp / ai.regime_detector で使用）
- LINE_CHANNEL_ACCESS_TOKEN — LINE Messaging API 用トークン（監視アラート）
- LINE_USER_ID — 通知先ユーザ ID（監視アラート）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite パス（デフォルト: data/monitoring.db）
- PAPER_FILL_MODE — Paper Trading の挙動（instant|partial|never|reject、デフォルト: instant）
- PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- PID_FILE_PATH — PID ファイルパス（デフォルト: data/execution.pid）
- KILL_FLAG_PATH — kill フラグファイルパス（デフォルト: data/kill.flag）
- KILL_FLAG_CLEAR_ON_START — 起動時に既存 kill.flag を自動クリアする場合は "1"
- KABUSYS_ENV — "development" | "paper_trading" | "live"（デフォルト: development）
- LOG_LEVEL — "DEBUG" | "INFO" | "WARNING" | "ERROR" | "CRITICAL"（デフォルト: INFO）

注意: Settings クラスは必要な変数が未設定の場合に ValueError を発生させます。`.env.example` を参考に `.env` を用意してください（本リポジトリ内に example ファイルがない場合は同等の内容で作成してください）。

---

## 使い方（代表例）

いくつかの良く使う呼び出し例を示します。

- Settings の利用
  ```python
  from kabusys.config import settings
  token = settings.jquants_refresh_token
  ```

- ポートフォリオ候補選定・重み算出
  ```python
  from kabusys.portfolio import select_candidates, calc_score_weights, calc_equal_weights

  signals = [{"code": "7203", "score": 1.2, "signal_rank": 1}, {"code": "9984", "score": 0.8, "signal_rank": 2}]
  candidates = select_candidates(signals, max_positions=5)
  weights = calc_score_weights(candidates)
  ```

- ポジションサイズ計算
  ```python
  from kabusys.portfolio import calc_position_sizes
  shares = calc_position_sizes(weights, candidates, portfolio_value=10_000_000, available_cash=7_000_000,
                               current_positions={}, open_prices={"7203": 2500.0}, allocation_method="score")
  ```

- DuckDB を使ったファクター計算
  ```python
  import duckdb
  from datetime import date
  from kabusys.research import calc_momentum, calc_volatility, calc_value

  conn = duckdb.connect("data/kabusys.duckdb")
  results = calc_momentum(conn, date(2026, 3, 20))
  ```

- ニュース NLP によるスコア付け（AI）
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  score_count = score_news(conn, date(2026, 3, 20), api_key="sk-...")
  ```

- 市場レジーム判定
  ```python
  from kabusys.ai.regime_detector import score_regime
  score_regime(conn, date(2026, 3, 20), api_key="sk-...")
  ```

- 監視ダッシュボード（Streamlit）
  ```
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```

- Monitoring DB の初期化（例）
  ```python
  import sqlite3
  from kabusys.monitoring.monitoring_db import init_monitoring_db
  conn = sqlite3.connect("data/monitoring.db")
  init_monitoring_db(conn)
  ```

実運用では ExecutionEngine / OrderManager / BrokerAPI の具象実装を組み合わせて起動します。ExecutionEngine は PID ファイル管理、kill.flag による安全停止、リコンシリエーション等を含むため、起動スクリプトの実装が必要です。

---

## ディレクトリ構成

（src/kabusys 配下を抜粋）

- src/kabusys/
  - __init__.py
  - config.py                    — 環境変数/設定管理
  - portfolio/
    - __init__.py
    - portfolio_builder.py       — 候補選定・重み計算
    - position_sizing.py         — 発注株数計算・資金制限処理
    - risk_adjustment.py         — セクター制限・レジーム乗数
  - research/
    - __init__.py
    - factor_research.py         — Momentum / Volatility / Value 等
    - feature_exploration.py     — forward returns, IC, summary
  - ai/
    - __init__.py
    - news_nlp.py                — ニュースセンチメント（OpenAI 呼び出し）
    - regime_detector.py         — レジーム判定（MA + マクロセンチメント）
  - monitoring/
    - __init__.py
    - monitoring_db.py           — SQLite 永続化層
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py
    - monitoring_engine.py
    - streamlit_dashboard.py
  - execution/
    - broker_api.py              — Broker API 型・Protocol・例外
    - order_manager.py
    - order_repository.py        — (DB 層、別ファイル群が想定される)
    - order_record.py
    - reconciler.py
    - execution_engine.py
    - risk_manager.py            — (参照されるが未列挙の実装がある想定)
  - monitoring/ ... (上記)
  - その他: data パス、DB ファイル等はプロジェクトルートの data/ を想定

---

## 注意事項 / 補足

- 自動 .env 読み込み:
  - 実行時にプロジェクトルート（.git または pyproject.toml を基準）を探索し、`.env` → `.env.local` を読み込みます。
  - 環境変数の優先順位: OS 環境変数 > .env.local > .env
  - 自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト時に便利）。

- OpenAI 呼び出し:
  - news_nlp と regime_detector は OpenAI を利用します。API キー未設定時はそれぞれ ValueError を送出します（呼び出し側で捕捉してください）。
  - API エラー時は可能な限りフェイルセーフ（0.0 にフォールバック、ログ出力）となる設計です。

- DB スキーマ:
  - monitoring_db.init_monitoring_db による初期化で監視用テーブルは作成されますが、DuckDB の prices_daily/raw_financials/raw_news 等のテーブルは外部データ投入プロセスが必要です（ETL は別途実装を想定）。

- テスト:
  - 多くのコア関数は副作用がなく単体テストしやすい構造です。外部依存（OpenAI・ブローカー）部分はモック可能な設計になっています（例: _call_openai_api をパッチする等）。

---

もし README にサンプルの .env.example、起動スクリプト、または DB 初期化スクリプトのテンプレートを含めたい場合は指定してください。用途（研究用 / ペーパートレード / 実運用）に応じた設定例も用意できます。