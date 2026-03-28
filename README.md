# KabuSys

日本株のデータプラットフォームと自動売買支援ライブラリ（KabuSys）のリポジトリ向け README。  
本ドキュメントはコードベース（src/kabusys 以下）を参照して、導入・実行方法や主な機能を日本語でまとめたものです。

---

## プロジェクト概要

KabuSys は日本株向けのデータ ETL、ニュース収集・NLP、リサーチ（ファクター計算）、監査ログ（発注／約定トレーサビリティ）、および市場レジーム判定・AI スコアリングを含むユーティリティ群を提供する Python パッケージです。

設計方針の要点：
- DuckDB をメインの分析ストレージとして利用（ローカルファイルまたはメモリ）。
- J-Quants API から差分取得する ETL パイプライン（レート制限・リトライ・トークン自動更新対応）。
- ニュースは RSS から収集し前処理を行い、OpenAI（gpt-4o-mini）で銘柄別センチメント評価を実施。
- 市場カレンダーや営業日判定、品質チェック、監査ログ（signal → order_request → execution）のスキーマ管理を提供。
- ルックアヘッドバイアスを避ける実装方針（日時の明示的扱い／DBクエリでの排他条件等）。

---

## 主な機能一覧

- 環境設定管理
  - .env / .env.local の自動読み込み（プロジェクトルート検出）
  - 必須環境変数チェック（Settings オブジェクト）

- データ ETL（kabusys.data.pipeline）
  - 日次 ETL（prices / financials / calendar）の差分更新
  - 品質チェック（欠損・スパイク・重複・日付不整合）

- J-Quants API クライアント（kabusys.data.jquants_client）
  - 株価日足、財務データ、マーケットカレンダー等の取得と DuckDB への冪等保存
  - レートリミット、トークンリフレッシュ、リトライ実装

- ニュース収集（kabusys.data.news_collector）
  - RSS 取得（SSRF 対策・gzip 対応・追跡パラメータ除去）
  - raw_news / news_symbols への冪等保存想定

- ニュース NLP（kabusys.ai.news_nlp）
  - 指定ウィンドウ内の銘柄ごとのニュースをまとめ、OpenAI でセンチメント（-1.0〜1.0）を取得して ai_scores に保存
  - バッチ化・トークン肥大化対策・リトライ・レスポンス検証

- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF 1321 の 200 日移動平均乖離（70%）とマクロニュースセンチメント（30%）を組み合わせて日次レジーム判定（bull/neutral/bear）

- リサーチ（kabusys.research）
  - ファクター計算（momentum / value / volatility）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー、Z-score 正規化ユーティリティ

- カレンダー管理（kabusys.data.calendar_management）
  - JPX カレンダーの取得・保存・営業日判定・next/prev_trading_day 等

- 監査ログ（kabusys.data.audit）
  - signal_events, order_requests, executions の DDL 定義・初期化ユーティリティ
  - 監査 DB 初期化（init_audit_db）で UTC タイムゾーン固定

---

## セットアップ手順

前提：Python 3.9+（type hint に union などを用いているため）と pip が利用可能であること。

1. リポジトリをクローン／チェックアウト:
   - git clone ...（リポジトリ URL）

2. 仮想環境を作成して有効化（推奨）:
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージのインストール（代表例）:
   - pip install duckdb openai defusedxml

   （パッケージセットは用途により追加で必要：例 urllib など標準ライブラリ、logging は標準）

   プロジェクトに setup.cfg / pyproject.toml がある場合:
   - pip install -e .

4. 環境変数設定
   - プロジェクトルート（.git または pyproject.toml がある親ディレクトリ）配下の `.env` / `.env.local` が自動で読み込まれます（デフォルト）。
   - 自動読み込みを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` をセットしてください。

   必須の環境変数（最低限）:
   - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
   - SLACK_BOT_TOKEN — Slack 通知用（本機能を使う場合）
   - SLACK_CHANNEL_ID — Slack チャンネル ID（本機能を使う場合）
   - KABU_API_PASSWORD — kabuステーション API のパスワード（発注等を行う場合）
   - OPENAI_API_KEY — OpenAI を利用する機能（news_nlp / regime_detector）で必要

   任意・デフォルトあり:
   - KABUSYS_ENV — development / paper_trading / live（default: development）
   - LOG_LEVEL — DEBUG/INFO/WARNING/ERROR/CRITICAL（default: INFO）
   - KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env ロードを無効化するフラグ
   - DUCKDB_PATH — (default: data/kabusys.duckdb)
   - SQLITE_PATH — (default: data/monitoring.db)
   - KABU_API_BASE_URL — kabu API の base URL（default: http://localhost:18080/kabusapi）

   .env の例:
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=sk-xxxxxxxxxxxx
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C0123456789
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

---

## 使い方（基本的な例）

以下はパッケージをインポートして主要な処理を呼ぶ最小例です。全て Python コードとして実行できます。

- 共通準備:
  ```python
  import duckdb
  from kabusys.config import settings
  ```

- DuckDB 接続を作る:
  ```python
  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL（prices/financials/calendar + 品質チェック）を実行:
  ```python
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメント（銘柄別 ai_scores）を生成:
  ```python
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  # OPENAI_API_KEY が環境変数に設定されている前提
  n_written = score_news(conn, date(2026, 3, 20))
  print("written:", n_written)
  ```

- 市場レジーム判定を実行:
  ```python
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  # OpenAI API key は環境変数 OPENAI_API_KEY を利用
  score_regime(conn, date(2026, 3, 20))
  ```

- ファクター計算（研究用途）:
  ```python
  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
  from kabusys.data.stats import zscore_normalize
  from datetime import date

  target = date(2026, 3, 20)
  mom = calc_momentum(conn, target)
  vol = calc_volatility(conn, target)
  val = calc_value(conn, target)

  mom_z = zscore_normalize(mom, ["mom_1m", "mom_3m", "mom_6m", "ma200_dev"])
  ```

- 監査ログ DB（audit）スキーマ初期化:
  ```python
  from kabusys.data.audit import init_audit_db
  # settings.duckdb_path を使うか、監査用に別ファイルを指定
  audit_conn = init_audit_db(settings.duckdb_path)
  ```

- RSS フィードを取得（ニュース収集ヘルパー）:
  ```python
  from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES

  src = DEFAULT_RSS_SOURCES["yahoo_finance"]
  articles = fetch_rss(src, "yahoo_finance")
  for a in articles[:5]:
      print(a["id"], a["datetime"], a["title"])
  ```

注意点:
- OpenAI を用いる関数は、api_key を引数で与えるか環境変数 OPENAI_API_KEY を設定してください。
- run_daily_etl などは DB 内のテーブル構造（raw_prices, raw_financials, market_calendar 等）が前提です。必要ならスキーマ初期化やマイグレーションを行ってください（本 README ではスキーマの自動生成手順は含めていませんが、data.audit.init_audit_schema 等を参照できます）。
- ETL / AI 関連は外部 API に依存するためネットワークアクセス、API キー、レート制限に注意してください。

---

## ディレクトリ構成（抜粋）

src/kabusys 以下の主要ファイル・モジュール:

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
  - stats.py
  - quality.py
  - news_collector.py
  - audit.py
  - etl.py (ETLResult 再エクスポート)
- research/
  - __init__.py
  - factor_research.py
  - feature_exploration.py
- monitoring/, strategy/, execution/ など（パッケージ __all__ に含むが本 README のコード抜粋には未掲載の可能性あり）

（上記はリポジトリに含まれる各機能ごとの主要ファイルの抜粋です。詳細なファイル一覧はリポジトリツリーをご確認ください。）

簡易ツリー例:
```
src/
  kabusys/
    __init__.py
    config.py
    ai/
      news_nlp.py
      regime_detector.py
    data/
      jquants_client.py
      pipeline.py
      news_collector.py
      calendar_management.py
      quality.py
      audit.py
      stats.py
    research/
      factor_research.py
      feature_exploration.py
    ...
```

---

## 追加のヒント・運用注意

- テスト環境:
  - 自動 .env 読み込みをテストで不要にするなら環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してからテストを実行してください。
  - OpenAI / J-Quants API 呼び出しはモック化できる設計（各モジュールで _call_openai_api などを差し替え可能）です。

- ログ:
  - settings.log_level でログレベルを制御できます（LOG_LEVEL 環境変数）。運用時は適切なログ出力先とローテーションを設定してください。

- セキュリティ:
  - news_collector は SSRF 等に配慮した実装を含みます。RSS URL の取り扱いや外部入力には十分注意してください。
  - API キーは .env に保存する場合はアクセス権限を厳格に管理してください。

---

この README はコードの概要と利用方法の手引きです。詳細な API やテーブルスキーマ、運用フロー（ジョブスケジューリング・モニタリング・リトライポリシー等）は各モジュールの docstring（ソース内のコメント）を参照してください。必要であれば README に追記したいトピック（例：スキーマ初期化 SQL、CI 設定、デプロイ手順など）を教えてください。