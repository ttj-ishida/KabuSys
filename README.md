# KabuSys

日本株のデータ収集・解析・自動売買プラットフォームのコアライブラリ（KabuSys）。  
このリポジトリは、J-Quants / JPX などのデータソースからの ETL、ニュース収集・NLP（OpenAI）、リサーチ用ファクター計算、監査ログ（取引トレース）などの機能を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株向けのバックエンドライブラリ群です。主な目的は以下の通りです。

- J-Quants API から株価・財務・市場カレンダーを差分取得して DuckDB に保存する ETL パイプライン
- RSS ベースのニュース収集と前処理、銘柄との紐付け
- OpenAI を使ったニュースセンチメント評価（銘柄別 ai_score、マクロセンチメント）
- 研究（research）用のファクター計算・特徴量探索ユーティリティ
- 監査ログ（signal → order_request → execution）のスキーマ初期化・管理
- データ品質チェック（欠損・スパイク・重複・日付不整合）

設計方針の特徴:
- ルックアヘッドバイアスに配慮（内部処理で date.today() を不用意に使わない）
- DuckDB を主要なローカル DB として使用（軽量・高速）
- 外部 API 呼び出しに対して堅牢なリトライ/バックオフ・フェイルセーフ実装
- 冪等性を重視した DB 保存ロジック

---

## 機能一覧

- data/
  - ETL パイプライン（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - J-Quants クライアント（認証・ページネーション・保存用ユーティリティ）
  - 市場カレンダー管理（営業日判定・next/prev_trading_day）
  - ニュース収集（RSS の取得／正規化／SSRF 対策）
  - データ品質チェック（欠損・スパイク・重複・日付不整合）
  - 監査ログスキーマ初期化 / 監査 DB 初期化ユーティリティ
  - 汎用統計関数（zscore 正規化）
- ai/
  - news_nlp.score_news: 銘柄ごとのニュースセンチメントを OpenAI に問い合わせて ai_scores に書き込む
  - regime_detector.score_regime: ETF（1321）の MA とマクロセンチメントを合成して市場レジームを判定・保存
- research/
  - ファクター計算（momentum, value, volatility）
  - 特徴量探索（forward returns, IC, summary, rank）
- config.py
  - 環境変数の自動読み込み（.env / .env.local をプロジェクトルートから読み込み）
  - settings オブジェクト経由で設定を参照

---

## 必要条件 / 推奨環境

- Python 3.10 以上（型ヒントで `|` 演算子を使用）
- DuckDB
- OpenAI Python SDK（gpt-4o-mini 等を利用する場合）
- defusedxml（RSS パースの安全対策）

主要な Python パッケージ（例）:
- duckdb
- openai
- defusedxml

（プロジェクトには requirements.txt が存在しない場合があります。必要に応じて上記パッケージをインストールしてください。）

---

## セットアップ手順

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo-root>
   ```

2. Python 仮想環境作成（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 必要パッケージをインストール
   例:
   ```
   pip install duckdb openai defusedxml
   ```
   開発・テスト用に editable install を行う場合:
   ```
   pip install -e .
   ```

4. 環境変数を設定
   プロジェクトルートに `.env` または `.env.local` を配置すると自動で読み込まれます（自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。

   主要な環境変数（一部必須）:
   - JQUANTS_REFRESH_TOKEN (必須): J-Quants のリフレッシュトークン
   - OPENAI_API_KEY (必須 for AI functions): OpenAI API キー
   - KABU_API_PASSWORD: kabuステーション API パスワード（発注機能を使う場合）
   - KABU_API_BASE_URL: kabu API のベースURL（デフォルト: http://localhost:18080/kabusapi）
   - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID: Slack 通知を利用する場合
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH: SQLite（監視用）パス（デフォルト: data/monitoring.db）
   - KABUSYS_ENV: development / paper_trading / live
   - LOG_LEVEL: DEBUG/INFO/...

   .env 例:
   ```
   JQUANTS_REFRESH_TOKEN=xxxx
   OPENAI_API_KEY=sk-xxxx
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   ```

---

## 使い方（簡易ガイド）

以下は Python インタプリタ / スクリプトからの利用例です。各例は基本的な呼び出し方を示しています。

- DuckDB 接続作成
  ```python
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL を実行（市場カレンダー・株価・財務の差分取得 + 品質チェック）
  ```python
  from kabusys.data.pipeline import run_daily_etl

  result = run_daily_etl(conn)  # target_date を与えなければ今日
  print(result.to_dict())
  ```

- ニュースセンチメントスコアを生成（ai_scores テーブルへ）
  ```python
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  # OpenAI APIキーは環境変数 OPENAI_API_KEY または api_key 引数で指定
  n_written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"wrote scores for {n_written} codes")
  ```

- 市場レジーム判定（market_regime テーブルへ）
  ```python
  from kabusys.ai.regime_detector import score_regime
  from datetime import date

  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 研究用ファクター計算
  ```python
  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
  from datetime import date

  momentum = calc_momentum(conn, date(2026, 3, 20))
  volatility = calc_volatility(conn, date(2026, 3, 20))
  value = calc_value(conn, date(2026, 3, 20))
  ```

- 監査ログ用 DB 初期化
  ```python
  from kabusys.data.audit import init_audit_db

  audit_conn = init_audit_db("data/audit.duckdb")
  # init_audit_db はテーブル作成まで行い、接続を返します
  ```

- ニュース RSS を取得（単体）
  ```python
  from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES

  articles = fetch_rss(DEFAULT_RSS_SOURCES["yahoo_finance"], source="yahoo_finance")
  for a in articles:
      print(a["id"], a["datetime"], a["title"])
  ```

注意:
- OpenAI 呼び出しは料金がかかるため、本番環境では適切な API キー・レート管理・コスト管理を行ってください。
- J-Quants API の呼び出しはレート制限に注意していますが、実運用ではさらに運用上の配慮が必要です。

---

## 開発・テストに関するメモ

- config.py はプロジェクトルート（.git または pyproject.toml のある場所）を基準に .env を自動読み込みします。テスト時に自動ロードしたくない場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- AI モジュール（news_nlp, regime_detector）では OpenAI 呼び出し部分を内部関数として定義しており、ユニットテストではこれらをモックする設計になっています（例: unittest.mock.patch で _call_openai_api を差し替え）。
- DuckDB を利用した SQL は executemany を前提にしている箇所があり、空リストでの executemany を避けるチェックが入っています。テスト時にも空リストの扱いに注意してください。

---

## ディレクトリ構成

以下はコードベースの主要なディレクトリ/ファイル構成（抜粋）です。

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
    - pipeline.py
    - etl.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - research/__init__.py
- src/kabusys/__init__.py

各モジュールの責務（簡単に）
- config.py: 環境変数の読み込み・settings オブジェクト
- data/jquants_client.py: J-Quants API の取得・保存ロジック（ETL の低レベル）
- data/pipeline.py: 日次 ETL の Orchestrator（run_daily_etl 等）
- data/news_collector.py: RSS 取得と前処理、raw_news への保存ロジック
- data/quality.py: データ品質チェック
- data/audit.py: 監査ログ用テーブル定義・初期化
- ai/news_nlp.py: ニュースの銘柄別センチメント取得（OpenAI）
- ai/regime_detector.py: マクロセンチメント + ETF MA で市場レジーム判定
- research/*: ファクター計算・評価用ユーティリティ

---

## 追加情報 / 注意点

- 本ライブラリはデータ収集・解析基盤のコアを提供しますが、実際の売買発注（ブローカー API 経由の約定処理等）を組み込む場合は別途実装と安全設計（リスク管理、二重発注防止、監査）を行ってください。kabuステーション API 用のパスワード変数などは config で扱われていますが、発注ロジックはこのコードベースの範囲外です。
- OpenAI を使う箇所はレスポンスの堅牢なパース・リトライ・フェイルセーフを実装していますが、モデルの振る舞いや API 仕様変更には注意してください。
- テストを書く際は外部 API 呼び出し（OpenAI, J-Quants, RSS）を必ずモックしてください。

---

README に載せてほしいサンプルや、環境変数の .env.example を生成してほしい等があれば教えてください。必要に応じて README を補足・改善します。