# KabuSys

KabuSys は日本株の自動売買／研究／監視を目的とした Python ライブラリ群です。  
ポートフォリオ構築、ポジションサイジング、ファクター計算、ニュース NLP によるセンチメント評価、市場レジーム判定、監視エンジン、発注エンジン（ExecutionEngine）などを含みます。

---

## 主な特徴（機能一覧）

- 環境変数 / .env の自動読み込みと Settings ラッパー
  - プロジェクトルートの `.env` / `.env.local` を自動読み込み（必要に応じて無効化可）
- ポートフォリオ構築
  - シグナル選定（スコア降順で上位選定）
  - 等比率・スコア加重の重み計算
  - セクター集中制限（セクターキャップ）
  - レジームに応じた投下資金乗数
  - 株数決定（risk-based / equal / score）・単元株丸め・資金スケーリング
- リサーチ / ファクター計算
  - Momentum（1M/3M/6M/MA200乖離）
  - Volatility（20日 ATR / 出来高関連）
  - Value（PER / ROE）
  - 将来リターン計算、IC（情報係数）計算、ファクター統計サマリー
- AI（OpenAI）を用いた解析
  - ニュースのセンチメント評価（銘柄別 ai_score を DuckDB に書き込み）
  - マクロニュース + ETF MA を用いた市場レジーム判定（bull/neutral/bear）
  - OpenAI 呼び出しはリトライ・バリデーション・フェイルセーフ実装
- 実行（Execution）
  - OrderManager / OrderRepository / Reconciler / ExecutionEngine による発注ワークフロー
  - ブローカー API 抽象化（Protocol）と例外モデル
  - 起動時リコンシリエーション自動化
  - Gate チェック（シグナル / 実行 / ドローダウン）
- 監視（Monitoring）
  - SQLite ベースの監視 DB（system_status, trade_logs, positions, risk_logs, dashboard）
  - SystemMonitor / TradeMonitor / RiskMonitor / KillSwitch / AlertManager
  - LINE Push によるアラート送信（クールダウン管理）
  - Streamlit ダッシュボード（read-only 接続で監視表示）
- テストしやすい設計
  - DuckDB/SQLite を外部依存とし、外部 API 呼び出しは差し替え可能（テスト用フックあり）

---

## 前提・依存関係

- Python 3.10 以上（| 型アノテーション、match などの近年の構文を想定）
- 外部パッケージ（代表例）:
  - duckdb
  - openai
  - requests
  - psutil
  - streamlit (ダッシュボードを使う場合)
- 標準モジュール: sqlite3, logging, pathlib, datetime など

requirements.txt（例）
```
duckdb
openai
requests
psutil
streamlit
```
※ 実行環境に応じてバージョン固定を推奨します。

---

## セットアップ手順

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo-dir>
   ```

2. 仮想環境作成（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

3. 依存パッケージをインストール
   ```
   pip install -r requirements.txt
   ```
   または開発インストール:
   ```
   pip install -e .
   ```

4. 環境変数（.env）を用意  
   プロジェクトルート（.git や pyproject.toml がある場所）に `.env` を置くと自動的に読み込まれます。
   自動ロードを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   .env に設定する主なキー（例）
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
   PAPER_FILL_MODE=instant
   PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
   LOG_LEVEL=INFO
   KABUSYS_ENV=development
   ```

5. 監視用 SQLite DB の初期化（Monitoring）
   ```
   python -c "import sqlite3; from kabusys.monitoring.monitoring_db import init_monitoring_db; conn=sqlite3.connect('data/monitoring.db'); init_monitoring_db(conn); conn.close()"
   ```

6. DuckDB（データ）について  
   DuckDB 内に prices_daily / raw_financials / raw_news / news_symbols / ai_scores / market_regime / signals / portfolio_targets 等のテーブルが必要です。データロード・スキーマはプロジェクトのデータパイプライン実装に従って作成してください（本 README ではスキーマ定義は含めません）。

---

## 使い方（主要な例）

- Settings を使う（環境変数のラッパー）
  ```python
  from kabusys.config import settings
  print(settings.duckdb_path)  # Path オブジェクト
  print(settings.is_live)
  ```

- ファクター計算（DuckDB 接続が必要）
  ```python
  import duckdb
  from datetime import date
  from kabusys.research import calc_momentum, calc_value, calc_volatility

  conn = duckdb.connect("data/kabusys.duckdb")
  t = date(2026, 3, 20)
  mom = calc_momentum(conn, t)
  vol = calc_volatility(conn, t)
  val = calc_value(conn, t)
  ```

- ニュースセンチメント（OpenAI API キーが必要）
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  written = score_news(conn, date(2026, 3, 20), api_key="sk-...")
  print(f"wrote {written} ai_scores")
  ```

- 市場レジーム判定
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, date(2026, 3, 20), api_key="sk-...")
  ```

- 監視ダッシュボード（Streamlit）
  ```
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```

- 監視 DB 初期化 / MonitoringEngine 実行（非常に簡略化した例）
  ```python
  import sqlite3, duckdb
  from kabusys.monitoring import SystemMonitor, TradeMonitor, RiskMonitor, MonitoringEngine, KillSwitch, AlertManager, MonitoringDB, init_monitoring_db
  from kabusys.execution.order_repository import OrderRepository  # 実装に依存

  # 省略: 必要な接続・リポジトリ・クライアントを初期化
  ```

- ExecutionEngine 実行（実運用ではブローカー実装・OrderRepository 等の実体が必要）
  - ExecutionEngine は以下を組み合わせて実行します:
    - BrokerAPIProtocol 実装（ブローカークライアント）
    - OrderRepository（SQLite ベース）
    - RiskManager（ルール）
    - OrderManager
    - DuckDB 接続（signals / portfolio_targets）
    - Reconciler（任意）
  - 実稼働では EngineConfig.target_date を指定して `engine.run_session()` を呼びます。

---

## 重要な設計／運用メモ

- self-contained な計算関数（portfolio、research）は DB 書き換えを行わずメモリ内の純粋関数として設計されています（テスト容易性向上）。
- AI 呼び出しはフェイルセーフ設計：API エラー時はスコアをスキップまたは 0.0 にフォールバックし、処理全体が停止しないようになっています。
- .env の自動読み込みはプロジェクトルート（.git または pyproject.toml がある場所）を基準に行います。テスト時は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化できます。
- kill.flag（Settings.kill_flag_path）を用いた外部停止シグナルをサポート。ExecutionEngine は起動時に kill.flag を検出し、設定に応じて起動を拒否または clear します。

---

## ディレクトリ構成（抜粋）

- src/kabusys/
  - __init__.py — パッケージ定義（バージョンなど）
  - config.py — 環境変数/.env の読み込みと Settings
  - portfolio/
    - __init__.py
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py — 株数決定・資金スケール
    - risk_adjustment.py — セクターキャップ・レジーム乗数
  - research/
    - __init__.py
    - factor_research.py — Momentum/Volatility/Value 計算
    - feature_exploration.py — 将来リターン / IC / 統計サマリ
  - ai/
    - __init__.py
    - news_nlp.py — ニュースセンチメント算出（OpenAI）
    - regime_detector.py — ETF MA + マクロニュースで市場レジーム判定
  - monitoring/
    - __init__.py
    - monitoring_db.py — SQLite スキーマ & MonitoringDB クラス
    - system_monitor.py — CPU/メモリ/データ鮮度監視
    - trade_monitor.py — 注文滞留 / 約定異常監視
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - alert_manager.py — LINE 通知
    - kill_switch.py — kill.flag 管理
    - monitoring_engine.py — 各 Monitor をまとめるポーリングエンジン
    - streamlit_dashboard.py — 監視ダッシュボード（Streamlit）
  - execution/
    - broker_api.py — Broker API のデータモデル / Protocol / 例外
    - order_manager.py — Order State Machine 外向け API
    - reconciler.py — 起動時の自動リコンシリエーション
    - execution_engine.py — Signal Queue Pull 型発注エンジン（メイン実行部）
    - （その他: order_repository, order_record, risk_manager などは実装ファイルが必要）
  - monitoring/、research/、portfolio/、ai/ 等はそれぞれ単体テストしやすい設計

---

## テストと拡張

- 各モジュールは外部 API 呼び出し（OpenAI, ブローカー, requests 等）を切り離して設計されています。ユニットテストでは該当関数をモック（patch）して挙動を検証してください。
- 将来的な拡張ポイント:
  - 銘柄別の lot_size（現状は一括 lot_size パラメータ）
  - 価格フォールバック（price_map の欠損時の挙動改善）
  - データロード / DuckDB スキーマ定義の自動化スクリプト

---

この README はコードベースの主要部分を要約したものです。実運用・開発時は各モジュールの docstring と型注釈、ログ出力を参照してください。必要であれば、デプロイ手順／CI 設定／DuckDB スキーマ定義の詳細 README を別途作成できます。