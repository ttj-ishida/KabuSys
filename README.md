# KabuSys

日本株向け自動売買 / データプラットフォーム用ライブラリです。  
ETL、ニュース収集・NLP、ファクター計算、監査ログ・発注監視、J-Quants / kabu API クライアントなどを含むモジュール群を提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は日本株のデータ取得・品質管理・特徴量生成・AI ベースのニュースセンチメント評価・市場レジーム判定・監査ログ管理を行うための共有ライブラリです。  
設計上、バックテストや運用（paper/live）での使用を意識しており、ルックアヘッドバイアスにならないよう日付処理やデータ取得の取り扱いが丁寧に実装されています。

主な特徴
- J-Quants API クライアント（レート制御・リトライ・トークン自動更新）
- ETL パイプライン（差分取得・冪等保存・品質チェック）
- ニュース収集（RSS）とニュースNLP（OpenAI）による銘柄別スコアリング
- 市場レジーム判定（ETF MA + マクロニュースの合成）
- ファクター計算・特徴量探索（モメンタム、ボラティリティ、バリュー等）
- 監査（audit）テーブル／初期化ユーティリティ（発注→約定のトレーサビリティ）
- DuckDB を中心とした軽量な永続化設計

---

## 機能一覧

- data/
  - jquants_client: J-Quants API 呼び出し、DuckDB への保存（raw_prices, raw_financials, market_calendar 等）
  - pipeline: 日次 ETL（run_daily_etl）や個別 ETL ジョブ（run_prices_etl 等）
  - news_collector: RSS フィードの収集と前処理（SSRF 対策、トラッキング除去）
  - calendar_management: JPX カレンダー管理、営業日判定・前後営業日検索
  - quality: データ品質チェック（欠損・スパイク・重複・日付不整合）
  - audit: 監査ログ用スキーマ作成・初期化（signal_events, order_requests, executions）
  - stats: zscore_normalize 等の統計ユーティリティ
- ai/
  - news_nlp.score_news: 銘柄ごとにニュースからセンチメントを計算して ai_scores に書き込む
  - regime_detector.score_regime: ETF(1321)の MA200 乖離とマクロセンチメントを合成して market_regime に書き込む
- research/
  - factor_research: calc_momentum, calc_value, calc_volatility
  - feature_exploration: calc_forward_returns, calc_ic, factor_summary, rank
- config:
  - 環境変数の読み込み（プロジェクトルートの .env / .env.local を自動ロード、優先順位: OS 環境 > .env.local > .env）
  - settings オブジェクト経由の型付き設定取得（バリデーション含む）

---

## 要件

- Python 3.10+
- 必須ライブラリ（例）
  - duckdb
  - openai
  - defusedxml

（パッケージ一覧はプロジェクトの requirements.txt / pyproject.toml を参照してください。ここに無ければ上記を pip で導入してください。）

---

## セットアップ手順

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境作成（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

3. 依存パッケージをインストール
   例:
   ```
   pip install duckdb openai defusedxml
   # または
   pip install -e .
   ```

4. 環境変数設定
   プロジェクトルートに `.env`（およびローカル用に `.env.local`）を作成します。自動ロードは以下の優先順位です:
   - OS 環境変数（最優先）
   - .env.local
   - .env

   主要な環境変数:
   - JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
   - OPENAI_API_KEY: OpenAI API キー（AI モジュールで使用）
   - KABU_API_PASSWORD: kabuステーション API パスワード
   - KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
   - SLACK_BOT_TOKEN / SLACK_CHANNEL_ID: Slack 通知用（必須ではないが一部機能で使用）
   - DUCKDB_PATH / SQLITE_PATH: デフォルト DB パス（data/kabusys.duckdb, data/monitoring.db）
   - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
   - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL

   自動読み込みを無効にする場合:
   ```
   export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
   ```

---

## 使い方（簡単な例）

まず DuckDB 接続を作成してから各関数を呼び出します。

- ETL（日次）
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメントを計算して ai_scores に書き込む
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  count = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # 環境変数 OPENAI_API_KEY を使う
  print(f"scored {count} symbols")
  ```

- 市場レジーム判定
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
  ```

- 監査用 DB 初期化
  ```python
  from kabusys.data.audit import init_audit_db

  conn = init_audit_db("data/audit.duckdb")
  ```

- 研究用ファクター計算
  ```python
  import duckdb
  from datetime import date
  from kabusys.research.factor_research import calc_momentum

  conn = duckdb.connect("data/kabusys.duckdb")
  records = calc_momentum(conn, target_date=date(2026, 3, 20))
  ```

- カレンダー関数例
  ```python
  from kabusys.data.calendar_management import next_trading_day, is_trading_day
  import duckdb
  from datetime import date

  conn = duckdb.connect("data/kabusys.duckdb")
  print(is_trading_day(conn, date(2026, 3, 20)))
  print(next_trading_day(conn, date(2026, 3, 20)))
  ```

注意:
- AI モジュール（news_nlp / regime_detector）は OpenAI の API を呼び出します。API キーを渡すか、環境変数 OPENAI_API_KEY を設定してください。
- run_daily_etl などは内部で複数の ETL ジョブを呼び出します。各ステップは個別に例外処理され、結果は ETLResult にまとめられます。

---

## ディレクトリ構成

以下は主要なファイル・モジュールのツリー（src/kabusys 配下）です:

- src/kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py
    - regime_detector.py
  - data/
    - __init__.py
    - jquants_client.py
    - pipeline.py
    - etl.py
    - calendar_management.py
    - news_collector.py
    - quality.py
    - stats.py
    - audit.py
    - pipeline.py (ETLResult 再エクスポート)
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py

各モジュールの役割は上記「機能一覧」を参照してください。

---

## 注意事項 / 運用メモ

- 環境変数の自動ロードはプロジェクトルート（.git または pyproject.toml があるディレクトリ）を基準に行われます。CI やテストで自動読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。
- DuckDB に対する executemany の挙動（バージョン差）に依存する箇所があるため、DuckDB のバージョンアップ時には注意してください（コード内に互換性対策があります）。
- OpenAI や J-Quants 呼び出しにはリトライ・バックオフ・レート制御が組み込まれているものの、プロダクションでの運用では API 使用料とリクエストレートに注意してください。
- 監査ログ（audit）は削除せず蓄積する前提です。DB サイズ増大に備えて定期バックアップやアーカイブ方針を用意してください。

---

## 貢献 / 開発

- 新機能やバグ修正は PR をお願いします。コードはテスト可能であること、Look-ahead バイアスが入らないことを念頭に実装してください。
- テストでは環境変数自動ロードの影響を避けるため KABUSYS_DISABLE_AUTO_ENV_LOAD を利用し、OpenAI / J-Quants 呼び出しはモックで差し替えてください（コード内でモック可能なヘルパーが用意されています）。

---

README に含めてほしい追加情報や使用例（CI、Docker、requirements.txt など） があれば教えてください。必要に応じてサンプルスクリプトやテンプレート .env.example も作成します。