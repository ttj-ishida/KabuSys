# KabuSys

日本株向けのデータプラットフォーム兼自動売買補助ライブラリ。  
ETL・データ品質チェック・ニュース収集・LLM によるニュースセンチメント評価・市場レジーム判定・監査ログ（トレーサビリティ）など、マーケットデータの取得から研究・監視・実行支援に必要な機能群を提供します。

---

## 目次
- プロジェクト概要
- 主な機能
- 必要条件 / インストール
- 環境変数（設定）
- セットアップ手順
- 使い方（簡単なコード例）
- ディレクトリ構成
- 注意点 / 設計方針
- トラブルシューティング

---

## プロジェクト概要
KabuSys は日本株向けのデータ収集・整備・解析基盤と、AI を使ったニュース評価や市場レジーム判定を行うためのライブラリ群です。J-Quants API からの株価／財務／カレンダー取得、RSS ベースのニュース収集、OpenAI（gpt-4o-mini）を用いたニュースセンチメント評価、DuckDB を用いた永続化・ETL、品質チェック、監査ログ（発注→約定のトレース）などを提供します。

設計上の特徴:
- DuckDB をデータベースに利用（軽量・ローカルで高速）
- J-Quants API へのレートリミット制御・リトライ・トークン自動リフレッシュを実装
- OpenAI 呼び出しはリトライ・応答検証・JSON モードを前提に堅牢化
- ルックアヘッドバイアスを防ぐ設計（関数は date を引数で受け、内部で date.today() に依存しない）
- データ品質チェックを明示的に実行可能

---

## 主な機能一覧
- データ取得 / ETL
  - J-Quants から株価（OHLCV）、財務、上場情報、JPX カレンダーを差分取得・保存（jquants_client / data.pipeline）
  - 日次 ETL（run_daily_etl）と個別 ETL（run_prices_etl / run_financials_etl / run_calendar_etl）
- データ品質チェック（data.quality）
  - 欠損、スパイク、重複、日付不整合の検出
- ニュース収集（data.news_collector）
  - RSS フィード取得・前処理・raw_news への冪等保存補助
  - SSRF / gzip / XML 系のセーフガードを備える
- AI（kabusys.ai）
  - ニュースセンチメント: news_nlp.score_news（銘柄ごとのスコアを ai_scores テーブルへ書き込み）
  - 市場レジーム判定: regime_detector.score_regime（ETF 1321 の MA とマクロニュースを合成して daily market_regime テーブルへ書込）
  - OpenAI 呼び出しのリトライ / パース・検証ロジック実装
- 研究用ユーティリティ（kabusys.research）
  - ファクター計算（モメンタム / バリュー / ボラティリティ等）
  - 将来リターン計算 / IC 計算 / 統計サマリー・正規化
- 監査ログ（data.audit）
  - signal_events / order_requests / executions 等のテーブル定義 + 初期化関数（init_audit_schema / init_audit_db）
- 設定管理（config）
  - .env / .env.local / 環境変数からの自動読み込み（プロジェクトルート検出）と settings オブジェクト

---

## 必要条件 / 推奨環境
- Python 3.10+
  - 型注釈（X | Y 形式）に依存しているため Python 3.10 以降を推奨
- 必要ライブラリ（主なもの）
  - duckdb
  - openai
  - defusedxml
  - （標準ライブラリ多数）
- ネットワーク接続（J-Quants / OpenAI / RSS 取得用）

※実運用では secrets（API トークン等）を安全に管理してください。

---

## 環境変数（主な設定）
KabuSys は .env / .env.local を自動で読み込む（プロジェクトルートに .git または pyproject.toml がある場合）。自動読み込みを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

必須（実行による）:
- JQUANTS_REFRESH_TOKEN : J-Quants リフレッシュトークン
- KABU_API_PASSWORD     : kabuステーション API パスワード（発注連携で使用）
- SLACK_BOT_TOKEN       : Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID      : Slack 通知先チャンネル ID
- OPENAI_API_KEY        : OpenAI 呼び出しに使用（news / regime 判定時。関数引数で上書き可能）

任意 / デフォルトあり:
- KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
- LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL) — デフォルト: INFO
- DUCKDB_PATH — デフォルト: data/kabusys.duckdb
- SQLITE_PATH — デフォルト: data/monitoring.db
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env 読み込みを無効化するフラグ（"1" 等）

サンプル .env:
KABUSYS_ENV=development
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-xxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb

---

## セットアップ手順（開発環境の例）
1. リポジトリをクローン
2. Python 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール（プロジェクトに requirements.txt / pyproject.toml がある想定）
   - pip install -r requirements.txt
   - または pip install duckdb openai defusedxml
4. プロジェクトルートに `.env` を用意（上記サンプル参照）
5. DuckDB ファイルの親ディレクトリが存在しない場合、自動作成されるが事前に作る場合:
   - mkdir -p data

※テスト実行やユニットテストでは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセットして自動ロードを無効化できます。

---

## 使い方（代表的な例）

- DuckDB 接続の準備（settings を使う例）
  ```python
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL を実行する
  ```python
  from kabusys.data.pipeline import run_daily_etl
  from datetime import date

  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースの AI スコア付け（銘柄ごとに ai_scores に書き込む）
  ```python
  from kabusys.ai import score_news  # ai.__init__ は score_news をエクスポート
  from datetime import date

  n = score_news(conn, target_date=date(2026, 3, 20))  # OPENAI_API_KEY は環境変数で
  print(f"scored {n} codes")
  ```

- 市場レジーム判定
  ```python
  from kabusys.ai.regime_detector import score_regime
  from datetime import date

  score_regime(conn, target_date=date(2026, 3, 20))  # market_regime テーブルへ書込
  ```

- 監査用 DuckDB の初期化（監査ログ用 DB を作る）
  ```python
  from kabusys.data.audit import init_audit_db
  from kabusys.config import settings

  audit_conn = init_audit_db(settings.duckdb_path)  # ":memory:" も可
  ```

- J-Quants API を直接呼ぶ（例: 株価取得）
  ```python
  from kabusys.data.jquants_client import fetch_daily_quotes

  records = fetch_daily_quotes(date_from=date(2026,1,1), date_to=date(2026,3,19))
  ```

- ニュース RSS をフェッチ（news_collector）
  ```python
  from kabusys.data.news_collector import fetch_rss

  articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
  ```

注意: OpenAI 呼び出しは api_key 引数で上書き可能（関数内で api_key を優先）。未設定だと ValueError が出ます。

---

## ディレクトリ構成（抜粋）
以下はコードベース内の主要モジュールとファイル構成の要約です（root は src/kabusys）:

- kabusys/
  - __init__.py
  - config.py                      # .env 読み込み・settings
  - ai/
    - __init__.py                   # score_news をエクスポート
    - news_nlp.py                   # ニュースセンチメント（score_news）
    - regime_detector.py            # 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - calendar_management.py        # JPX カレンダー管理
    - pipeline.py                   # ETL パイプライン（run_daily_etl 他）
    - etl.py                        # ETLResult の再エクスポート
    - stats.py                      # zscore_normalize 等
    - quality.py                    # データ品質チェック
    - audit.py                      # 監査ログスキーマ初期化
    - jquants_client.py             # J-Quants API クライアント & 保存関数
    - news_collector.py             # RSS 収集・前処理
  - research/
    - __init__.py
    - factor_research.py            # ファクター計算（momentum/value/volatility）
    - feature_exploration.py        # forward returns / IC / summary / rank

---

## 注意点 / 設計方針（実運用時のポイント）
- ルックアヘッドバイアス排除:
  - AI 解析やファクター計算の関数は target_date 引数を使い、内部で date.today() に依存しない設計です。バックテスト等での誤用に注意してください。
- OpenAI 呼び出し:
  - レスポンスの JSON 検証とリトライロジックが実装されています。API の失敗時はフェイルセーフでスコアを 0.0 とするなどの挙動があります（例: score_regime）。
- J-Quants:
  - レート制限（120 req/min）を固定間隔スロットリングで厳守します。401 の場合はリフレッシュトークンで自動更新して再試行します。
- DuckDB 用の executemany は空リストを渡すと挙動が異なるバージョンがあるため各所で空チェックを行っています。
- news_collector は SSRF や XML Bomb、gzip BOM 等の防御ロジックを備えています。

---

## よくあるトラブルと対処
- ValueError: "OpenAI API キーが未設定です"
  - OPENAI_API_KEY を環境変数か関数引数で指定してください。
- .env が読み込まれない
  - プロジェクトルートの検出は .git または pyproject.toml を基準に行っています。自動ロードを無効化している場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を確認してください。
- J-Quants の API エラー / 429
  - ネットワークや API 制限のためリトライされます。rate limit に引っかかる場合は実行間隔を調整してください。
- DuckDB のスキーマがない / テーブルがない
  - ETL の初回実行や audit 初期化を行ってテーブルを作成してください（data.schema 初期化関数等がある場合はそれを利用）。

---

この README はコードベースに基づいた利用方法・設計の要約です。実際に運用する際は各関数のドキュメント文字列（docstring）を参照し、特に API トークンや DB のバックアップ・権限管理、秘密情報の扱いに注意してください。質問や補足の要望があれば、用途（開発環境・デプロイ・特定機能）を教えてください。