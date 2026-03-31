# KabuSys

日本株向けのデータプラットフォーム兼リサーチ／自動売買支援ライブラリ。  
DuckDB を用いたデータ格納・ETL、J-Quants API 経由のデータ取得、ニュースの NLP（OpenAI）によるスコアリング、研究用ファクター計算、監査ログ（発注→約定トレーサビリティ）などを提供します。

---

## 主な特徴（機能一覧）

- 環境設定読み込み
  - .env / .env.local / OS 環境変数の自動読み込み（プロジェクトルート検出）
  - 必須環境変数のラッピング（settings オブジェクト）

- データ ETL / Data Platform
  - J-Quants API クライアント（株価日足、財務、マーケットカレンダー取得）
  - 差分 ETL / バックフィル対応（DuckDB へ冪等保存）
  - データ品質チェック（欠損・重複・スパイク・日付不整合）

- ニュース収集・NLP
  - RSS 収集（SSRF 対策、サイズ制限、トラッキングパラメータ除去）
  - OpenAI（gpt-4o-mini）を使ったニュースセンチメント解析（銘柄ごと、チャンクバッチ処理）
  - マクロニュースを使った市場レジーム判定（ETF 1321 の MA200 と LLM を合成）

- リサーチ / ファクター分析
  - モメンタム、バリュー、ボラティリティ等のファクター計算
  - 将来リターン計算、IC（Information Coefficient）、Zスコア正規化、統計サマリ

- 監査ログ（Audit）
  - シグナル → 発注要求 → 約定 を追跡する監査テーブル定義・初期化ユーティリティ
  - DuckDB での監査 DB 初期化関数を提供

---

## セットアップ手順

前提
- Python 3.10+（型ヒントに union 型等を利用）
- ネットワーク環境（J-Quants / OpenAI へのアクセス）
- 必要なライブラリ（例: duckdb, openai, defusedxml）

推奨手順（開発環境の例）:

1. リポジトリをクローンし、仮想環境を作成
   ```
   git clone <repo-url>
   cd <repo-dir>
   python -m venv .venv
   source .venv/bin/activate
   ```

2. 必要パッケージをインストール
   ※ pyproject.toml / requirements.txt があればそれに従ってください。最低限:
   ```
   pip install duckdb openai defusedxml
   ```

3. パッケージを編集可能インストール（任意）
   ```
   pip install -e .
   ```

4. 環境変数を設定
   - 推奨はリポジトリルートの `.env` / `.env.local` を作成する方法（自動読み込み）
   - 自動読み込みは、.git または pyproject.toml の親ディレクトリをプロジェクトルートとして探索します
   - 自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定

   例（.env）
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   KABU_API_PASSWORD=your_kabu_api_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   OPENAI_API_KEY=sk-...
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

   注意: 必須環境変数は settings オブジェクト経由で参照され、未設定時はエラーになります（例: JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, KABU_API_PASSWORD）。

---

## 使い方（例）

以下は代表的なユースケースの簡易サンプルです。実行前に環境変数を設定してください。

- DuckDB 接続を作って日次 ETL を実行する
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースの AI スコアリング（銘柄ごと ai_scores へ書き込む）
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # api_key None -> OPENAI_API_KEY を参照
  print("written:", written)
  ```

- 市場レジーム判定（ma200 + macro sentiment）
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査 DB を初期化する
  ```python
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  ```

- RSS フィードを取得する（ニュースコレクタの低レベル関数）
  ```python
  from kabusys.data.news_collector import fetch_rss
  articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
  for a in articles:
      print(a["id"], a["title"])
  ```

注意点:
- OpenAI 呼び出しは rate-limit とエラー時のリトライを実装していますが、API キー・コストに注意してください。
- DuckDB の executemany は空リストを受け付けないバージョンがあるため、ライブラリ内でハンドリングされています。
- すべての関数はルックアヘッドバイアスを避けるために内部で date.today() を盲目的に参照しない設計になっています（引数で日付を渡すことが基本）。

---

## 主要モジュール / ディレクトリ構成

（概要、代表的なファイルのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py
    - settings: 環境変数ラッパー（J-Quants トークン、Kabu API、Slack、DB パス、環境モード等）
  - ai/
    - __init__.py (score_news を公開)
    - news_nlp.py -- ニュースを銘柄ごとに集約して LLM でスコアリングする主要ロジック
    - regime_detector.py -- ETF 1321 の MA200 とマクロニュース LLM を合成して市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py -- J-Quants API クライアント（取得・保存ロジック、レート制御、リトライ）
    - pipeline.py -- ETL のエントリポイント（run_daily_etl 等）
    - etl.py -- ETL 結果型の再エクスポート
    - calendar_management.py -- マーケットカレンダー管理（営業日判定・更新ジョブ）
    - news_collector.py -- RSS 収集、前処理、保存ユーティリティ
    - quality.py -- データ品質チェック（欠損・重複・スパイク・日付不整合）
    - stats.py -- zscore_normalize 等の共通統計ユーティリティ
    - audit.py -- 監査ログ（テーブル定義・初期化）
  - research/
    - __init__.py
    - factor_research.py -- momentum / value / volatility 等のファクター計算
    - feature_exploration.py -- 将来リターン計算、IC、統計サマリ、rank ユーティリティ
  - others...
  
各モジュールは DuckDB 接続（duckdb.DuckDBPyConnection）を想定しており、外部副作用（発注 API 呼び出しなど）を含まない研究用関数群と、ETL/保存を行う関数群に分かれています。

---

## 環境変数（主なもの）

- JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API ベース URL（デフォルト http://localhost:18080/kabusapi）
- OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector で使用）
- SLACK_BOT_TOKEN, SLACK_CHANNEL_ID: Slack 通知用
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用途の SQLite（デフォルト data/monitoring.db）
- KABUSYS_ENV: 環境 "development" / "paper_trading" / "live"（デフォルト development）
- LOG_LEVEL: "DEBUG" / "INFO" / "WARNING" / "ERROR" / "CRITICAL"

settings オブジェクトから安全にアクセスできます（kabusys.config.settings）。

---

## テスト・開発時のヒント

- .env の自動読み込みを無効化する:
  ```
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  ```
- OpenAI / J-Quants の呼び出しはモックしやすく設計されています。内部の API 呼び出し箇所はユニットテストでパッチ可能（例: kabusys.ai.news_nlp._call_openai_api のパッチ）。
- DuckDB はインメモリ（":memory:"）での接続も可能。テスト時にファイル IO を避けられます。

---

## ライセンス・貢献

（ここにプロジェクトのライセンスや貢献ルール、コントリビュート方法を追記してください）

---

この README はコードベースの主要機能と利用方法の概要をまとめたものです。各モジュールの詳細な API（関数の引数・戻り値・例外等）はソース内のドキュメント文字列（docstring）を参照してください。