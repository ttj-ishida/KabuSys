# KabuSys

日本株向けのデータプラットフォームと自動売買／リサーチ基盤ライブラリです。  
ETL（J-Quants 経由の株価・財務・カレンダー収集）、データ品質チェック、監査ログ、ファクター計算、ニュースNLP（LLM）によるセンチメント評価、マーケットレジーム判定などを含むモジュール群を提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は日本株を対象にした次の機能群を持つ Python パッケージです。

- J-Quants API を用いたデータ取得（株価日足、財務、JPX カレンダー、上場情報）
- DuckDB をデータレイヤーに用いた ETL パイプライン（差分取得、バックフィル、品質チェック）
- ニュース収集（RSS）と LLM（OpenAI）ベースのニュースセンチメント算出（ai.score_news）
- ETF とマクロニュースを組み合わせた市場レジーム判定（ai.score_regime）
- ファクター計算・特徴量探索（momentum / volatility / value / forward returns / IC 等）
- 監査ログテーブル（signal → order_request → execution のトレーサビリティ）初期化ユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付不整合検出）
- 環境変数ベースの設定管理（.env 自動読み込み、設定アクセスは kabusys.config.settings）

設計方針の要点:
- ルックアヘッドバイアスを避ける（内部で date.today()/datetime.today() を直接参照しないなど）
- 冪等性（DB 保存時に ON CONFLICT / DELETE→INSERT 等で上書き）
- フェイルセーフ（外部API失敗時は例外で全体を破壊しない維持動作）
- テスト容易性（API呼び出し箇所の差し替えがしやすい実装）

---

## 主な機能一覧

- データ取得 / ETL
  - run_daily_etl: 日次ETL（market calendar / prices / financials / 品質チェック）
  - jquants_client.fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - jquants_client.save_*: DuckDB への冪等保存
- データ品質
  - quality.run_all_checks: 欠損、スパイク、重複、日付不整合検出
- ニュース & AI
  - data.news_collector.fetch_rss: RSS 取得と前処理（SSRF対策・サイズチェック等）
  - ai.news_nlp.score_news: 銘柄ごとのニュースセンチメント算出（OpenAI）
  - ai.regime_detector.score_regime: ETF MA200 とマクロニュースセンチメントを合成した市場レジーム判定
- リサーチ
  - research.factor_research.calc_momentum / calc_volatility / calc_value
  - research.feature_exploration.calc_forward_returns / calc_ic / factor_summary / rank
  - data.stats.zscore_normalize
- 監査ログ
  - data.audit.init_audit_db / init_audit_schema: 監査ログ（signals / order_requests / executions）初期化
- 設定管理
  - kabusys.config.settings: 環境変数からの設定取得（自動 .env 読込あり）

---

## セットアップ手順

前提:
- Python 3.10 以上（| 型記法や __future__ annotations を使用）
- DuckDB, OpenAI クライアント等を使用します

1. リポジトリをクローン／パッケージをインストール
   - 開発環境であれば editable install:
     - pip install -e .

   - または requirements.txt がある場合:
     - pip install -r requirements.txt

   必要なパッケージ（一例）:
   - duckdb
   - openai
   - defusedxml

2. 環境変数の設定
   - プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（kabusys.config が .git または pyproject.toml を基準に検索）。
   - 自動読み込みを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します（主にテスト用）。

   代表的な環境変数:
   - JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
   - KABU_API_PASSWORD: kabu API パスワード（必須）
   - SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（必須）
   - SLACK_CHANNEL_ID: Slack チャンネルID（必須）
   - OPENAI_API_KEY: OpenAI API キー（ai.score_news / ai.score_regime で必要）
   - DUCKDB_PATH: DuckDB ファイルパス（既定: data/kabusys.duckdb）
   - SQLITE_PATH: SQLite パス（監視用、既定: data/monitoring.db）
   - KABUSYS_ENV: development | paper_trading | live（既定: development）
   - LOG_LEVEL: DEBUG/INFO/...（既定: INFO）

   サンプル .env（例）
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxx
   OPENAI_API_KEY=sk-...
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   ```

3. データベース初期化（監査ログなど）
   - 監査ログ用 DB を初期化する例:
     ```python
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")
     ```

4. OpenAI / J-Quants の API キーを準備
   - ai モジュールを実行するには `OPENAI_API_KEY` が必要です（関数引数でキーを直接渡すことも可能）。
   - J-Quants は `JQUANTS_REFRESH_TOKEN` を用いて id token を取得します。

---

## 使い方（簡易ガイド）

いくつかの代表的な使い方例を示します。

- 日次 ETL を実行する
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメント（ai.news_nlp.score_news）
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  # OPENAI_API_KEY が環境変数に設定されている前提
  written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"書き込み銘柄数: {written}")
  ```

- 市場レジーム判定（ai.regime_detector.score_regime）
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログスキーマ初期化（既存接続に対して）
  ```python
  from kabusys.data.audit import init_audit_schema
  import duckdb

  conn = duckdb.connect("data/kabusys.duckdb")
  init_audit_schema(conn, transactional=True)
  ```

- J-Quants から株価を直接フェッチ（ページネーション対応）
  ```python
  from kabusys.data.jquants_client import fetch_daily_quotes
  from datetime import date

  records = fetch_daily_quotes(date_from=date(2026, 3, 1), date_to=date(2026, 3, 20))
  print(len(records))
  ```

注意点:
- ai.score_news / score_regime は OpenAI API を呼び出します。APIキーやコスト管理に注意してください。
- 多くの関数は DuckDB 接続を受け取り、DB 内のテーブル（raw_prices, raw_news, ai_scores, prices_daily, market_calendar など）を参照/更新します。事前にスキーマ作成・ETL 実行が必要です。

---

## ディレクトリ構成

主要なファイル・モジュールを示します（抜粋）。

- src/kabusys/
  - __init__.py
  - config.py                      — 環境変数 / .env 自動読込 / settings
  - ai/
    - __init__.py                   — score_news をエクスポート
    - news_nlp.py                   — ニュースNLPスコアリング（OpenAI）
    - regime_detector.py            — 市場レジーム判定（ETF MA + マクロニュース）
  - data/
    - __init__.py
    - jquants_client.py             — J-Quants API クライアント & 保存ロジック
    - pipeline.py                   — ETL パイプライン（run_daily_etl 等）
    - etl.py                        — ETL 公開インターフェース（ETLResult 再エクスポート）
    - calendar_management.py        — 市場カレンダー管理、営業日判定
    - news_collector.py             — RSS 収集・前処理・保存支援
    - quality.py                    — データ品質チェック
    - stats.py                      — zscore_normalize 等の統計ユーティリティ
    - audit.py                      — 監査ログテーブル定義と初期化
  - research/
    - __init__.py
    - factor_research.py            — momentum/value/volatility 等
    - feature_exploration.py        — forward returns, IC, summary, rank
  - research/... （補助ファイル）
  - その他（strategy, execution, monitoring 等パッケージ参照可能）

プロジェクトルートには .env や pyproject.toml / setup.cfg 等が想定されます（自動 .env 検出は .git または pyproject.toml を起点に行います）。

---

## 設定（settings）と自動 .env ロードについて

- kabusys.config は起動時にプロジェクトルートを探索し、.env → .env.local の順に読み込みます。
- 読み込み優先度は OS 環境変数 > .env.local > .env です。
- 自動読み込みを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テストで便利です）。
- settings オブジェクトから設定を直接取得できます：
  ```python
  from kabusys.config import settings
  token = settings.jquants_refresh_token
  ```

---

## テスト・開発ヒント

- OpenAI や HTTP 周りの呼び出しは内部で分離されており、テスト時にモック差替えしやすい設計です（例: news_nlp._call_openai_api を patch）。
- 自動 .env 読込を無効化して、テスト固有の環境を構築してください。
- DuckDB を使った単体テストでは ":memory:" を DB パスに指定してインメモリ DB を利用できます（data.audit.init_audit_db 等が対応）。

---

## ライセンス / 貢献

（ここでは README にライセンス／貢献規約を記載してください。必要であれば LICENSE ファイルを用意してください）

---

この README はコードベース（src/kabusys 以下）から主要機能を抜粋して作成しています。具体的なエンドツーエンドのセットアップや運用手順（監視、Slack 通知、kabu API 連携、実際の発注フロー）は別途運用ドキュメントにまとめることを推奨します。必要であれば README に追記しますので、追加で記載したい情報（例えば具体的な .env.example、docker-compose、CI セットアップ等）を教えてください。