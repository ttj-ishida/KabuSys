# KabuSys

日本株向けの自動売買 / 研究 / 監視ユーティリティ群です。  
このリポジトリはアルゴリズム的なポートフォリオ構築、ファクター計算、ニュースのLLMによるセンチメントスコア付与、実行エンジン周りの発注ロジック、監視ダッシュボードなどを含みます。

## プロジェクト概要
- ポートフォリオ構築（銘柄選定・配分・株数決定）
- ファクター計算（モメンタム・バリュー・ボラティリティ等）
- 研究用統計ユーティリティ（IC 計算、将来リターン計算、要約統計）
- ニュースをLLMでスコアリングして ai_scores テーブルへ格納
- 市場レジーム判定（ETF とマクロニュースの組合せ）
- 実行系（OrderManager / ExecutionEngine / Broker API プロトコル）
- 起動時リコンシリエーション（Reconciler）
- 監視（System/Trade/Risk Monitor、Alert via LINE、Streamlitダッシュボード）
- 環境設定管理（.env / 環境変数の自動ロード / Settings オブジェクト）

## 主な機能一覧
- 環境変数 / .env の自動読み込み（プロジェクトルートの .env / .env.local、KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可）
- ポートフォリオ構築関数
  - select_candidates, calc_equal_weights, calc_score_weights
  - calc_position_sizes（risk_based / equal / score）
  - apply_sector_cap（セクター集中制御）
  - calc_regime_multiplier（市場レジームに基づく資金乗数）
- 研究用モジュール
  - calc_momentum, calc_volatility, calc_value（DuckDB を用いて prices_daily / raw_financials を参照）
  - calc_forward_returns, calc_ic, factor_summary, rank
- AI / ニュース関連
  - score_news（OpenAI を使ったニュースセンチメント集計→ai_scores に書込）
  - score_regime（ETF とマクロニュースから市場レジーム判定）
- 実行 / 発注
  - ExecutionEngine：シグナル処理 / push ドレイン / kill switch 発動など
  - OrderManager / Reconciler / BrokerAPIProtocol 用のデータモデルと例外設計
- 監視
  - MonitoringDB（SQLite を使った永続化層）
  - SystemMonitor / TradeMonitor / RiskMonitor / KillSwitch / AlertManager
  - Streamlit ベースの監視ダッシュボード

## セットアップ手順（開発用）
前提: Python 3.10 以上を推奨（PEP 604 の union 型等を利用しているため）。

1. リポジトリをクローンして移動
   ```
   git clone <repo-url>
   cd <repo-dir>
   ```

2. 仮想環境作成（任意）
   ```
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

3. 必要パッケージをインストール
   （プロジェクトに requirements.txt / pyproject.toml があればそちらを使ってください。以下は主な依存例）
   ```
   pip install duckdb openai psutil requests streamlit
   ```

4. データディレクトリ（例）
   ```
   mkdir -p data
   ```

5. 環境変数設定
   - プロジェクトルート（.git や pyproject.toml がある場所）に .env, .env.local を置けます。
   - 自動読み込みはデフォルトで有効。無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

   例 (.env):
   ```
   JQUANTS_REFRESH_TOKEN=...
   KABU_API_PASSWORD=...
   OPENAI_API_KEY=...
   LINE_CHANNEL_ACCESS_TOKEN=...
   LINE_USER_ID=...
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   PID_FILE_PATH=data/execution.pid
   KILL_FLAG_PATH=data/kill.flag
   KILL_FLAG_CLEAR_ON_START=0
   PAPER_FILL_MODE=instant
   ```
   使用可能な主なキーは Settings クラスのプロパティ（config.py）を参照してください。

6. 監視 DB 初期化（SQLite）
   ```python
   from kabusys.monitoring.monitoring_db import init_monitoring_db
   import sqlite3
   conn = sqlite3.connect("data/monitoring.db")
   init_monitoring_db(conn)
   conn.close()
   ```

## 使い方（例）
以下は代表的な使い方例です。実運用ではエンジンやブローカー実装、DuckDB のデータ準備などが必要です。

- 設定の参照
  ```python
  from kabusys.config import settings
  print(settings.duckdb_path)
  print(settings.is_live)
  ```

- 研究モジュール（ファクター算出）
  ```python
  import duckdb
  from datetime import date
  from kabusys.research import calc_momentum, calc_volatility, calc_value

  conn = duckdb.connect("data/kabusys.duckdb")
  target = date(2026, 3, 20)
  mom = calc_momentum(conn, target)
  vol = calc_volatility(conn, target)
  val = calc_value(conn, target)
  ```

- ニューススコアリング（OpenAI API 必要）
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  written = score_news(conn, date(2026,3,20), api_key="sk-xxxx")
  print("written scores:", written)
  ```

- 市場レジーム判定
  ```python
  from kabusys.ai.regime_detector import score_regime
  written = score_regime(conn, date(2026,3,20), api_key="sk-xxxx")
  ```

- 監視ダッシュボード（Streamlit）
  ```
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```

- ExecutionEngine の起動（実運用には Broker 実装等が必要）
  ExecutionEngine は BrokerAPIProtocol 実装、OrderRepository、RiskManager、OrderManager、DuckDB 接続などを渡して利用します。テストでは run_once / run_session の一部を呼んで制御できます。

## 環境変数・設定（要点）
- 自動 .env 読み込みの挙動:
  - 読み込み順: OS 環境変数 > .env.local > .env
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化
  - プロジェクトルートは .git または pyproject.toml を起点に探索
- 重要な環境変数（主なもの）
  - JQUANTS_REFRESH_TOKEN（必須）
  - KABU_API_PASSWORD（必須）
  - OPENAI_API_KEY（AI 機能使用時）
  - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（アラート送信）
  - DUCKDB_PATH / SQLITE_PATH（データベースパス）
  - PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START（実行管理）
  - PAPER_FILL_MODE（paper trading の挙動: instant/partial/never/reject）
  - LOG_LEVEL / KABUSYS_ENV（development / paper_trading / live）

詳細は src/kabusys/config.py の Settings クラスをご確認ください。

## ディレクトリ構成（主要ファイル・モジュール）
- src/kabusys/
  - __init__.py — パッケージ定義、バージョン
  - config.py — 環境変数 / Settings 管理（.env 自動読み込み）
  - portfolio/
    - portfolio_builder.py — 候補選定・配分（select_candidates, calc_equal_weights, calc_score_weights）
    - position_sizing.py — 株数決定（calc_position_sizes）
    - risk_adjustment.py — セクターキャップ・regime multiplier
    - __init__.py
  - research/
    - factor_research.py — momentum/value/volatility 計算（DuckDB）
    - feature_exploration.py — 将来リターン / IC / summary
    - __init__.py
  - ai/
    - news_nlp.py — ニュース → OpenAI でスコア化 → ai_scores 書込
    - regime_detector.py — ETF + マクロニュースで市場レジーム判定
    - __init__.py
  - monitoring/
    - monitoring_db.py — SQLite スキーマ & MonitoringDB クラス
    - system_monitor.py, trade_monitor.py, risk_monitor.py — 各種チェック
    - kill_switch.py — フラグファイルによる停止
    - alert_manager.py — LINE プッシュ通知
    - monitoring_engine.py — 各 Monitor を束ねるループ
    - streamlit_dashboard.py — 観測用ダッシュボード
    - __init__.py
  - execution/
    - broker_api.py — Broker API のデータモデル / Protocol / 例外
    - order_manager.py — order state machine と broker 呼び出しの統括
    - execution_engine.py — Signal Queue Pull 型発注エンジン
    - reconciler.py — 起動時リコンシリエーション（注文・ポジション同期）
    - ...（その他 OrderRepository / OrderRecord 等は別ファイルに実装されている想定）
- その他:
  - data/ — データベースファイルや kill flag、pid などを置く既定の場所（設定で変更可）

## テスト・開発時のヒント
- .env.example を元に .env を作成して下さい（リポジトリに .env.example がある場合）。
- 自動 .env 読み込みはプロジェクトルート（.git / pyproject.toml）を基準に行われます。テストで読み込みを抑制したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI 関連関数は外部APIに依存するため、ユニットテスト時は _call_openai_api 等をモックすることを想定しています（news_nlp, regime_detector 内で明記）。
- DuckDB を読み書きする関数群は「DuckDB 接続」を引数にとるため、テスト用に in-memory な接続やテスト用データを作って検証できます。

---

さらに詳しい使い方や各関数の仕様はソース中のドキュメンテーション（docstring）を参照してください。必要であれば、特定モジュールの利用例や運用手順（運用時の注意、DB マイグレーション、バックアップ方針など）について追記できます。