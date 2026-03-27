# KabuSys

日本株向けのデータ基盤・リサーチ・自動売買補助ライブラリ群です。  
DuckDB をデータ層に、J-Quants / OpenAI 等の外部 API を組み合わせ、ETL・品質チェック・ニュース NLP・市場レジーム判定・ファクター計算・監査ログ基盤を提供します。

---

## 主な特徴（機能一覧）

- 環境・設定読み込み（.env / 環境変数）
- J-Quants API クライアント
  - 日次株価（OHLCV）取得（ページネーション・リトライ・レート制御）
  - 財務データ・上場銘柄情報・JPX カレンダー取得
  - DuckDB へ冪等保存（ON CONFLICT DO UPDATE）
- ETL パイプライン（差分取得・バックフィル・品質チェック）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- ニュース収集（RSS 取得・前処理・SSRF 対策）
- ニュース NLP（OpenAI を使った銘柄ごとのセンチメントスコア化）
- 市場レジーム判定（ETF MA とマクロニュースの LLM センチメント合成）
- 研究用ユーティリティ（ファクター計算・将来リターン・IC・統計サマリ）
- 監査ログ基盤（signal → order_request → execution をトレースするテーブル群）
- DuckDB ベースの監査 DB 初期化ユーティリティ

---

## 必要条件 / 依存関係

- Python 3.9+
- 必須（runtime）パッケージ例:
  - duckdb
  - openai
  - defusedxml

（プロジェクトで使う他パッケージは実際の packaging / requirements に従ってください）

---

## セットアップ手順

1. リポジトリをクローン／プロジェクトディレクトリへ移動

2. 仮想環境を作成（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .\.venv\Scripts\activate   # Windows
   ```

3. 必要パッケージをインストール（例）
   ```
   pip install duckdb openai defusedxml
   ```
   ※ 実プロジェクトでは requirements.txt / pyproject.toml に従ってください。

4. .env を用意（ルートに `.env` または `.env.local` を置くと自動読み込みされます）
   - 自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   サンプル（.env.example）:
   ```
   # J-Quants
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here

   # OpenAI
   OPENAI_API_KEY=your_openai_api_key_here

   # kabu ステーション（必要なら）
   KABU_API_PASSWORD=your_kabu_password
   KABU_API_BASE_URL=http://localhost:18080/kabusapi

   # Slack 通知（モニタリング用）
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567

   # DB パス（省略時は data/kabusys.duckdb 等）
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db

   # 実行環境
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

5. DuckDB データベースの準備
   - デフォルトは `data/kabusys.duckdb`（settings.duckdb_path）
   - 監査ログ専用 DB を別ファイルに作る場合は `kabusys.data.audit.init_audit_db(...)` を使用します。

---

## 使い方（主要なユースケース）

以下は Python REPL / スクリプトでの利用例です。

- 環境設定オブジェクト
  ```python
  from kabusys.config import settings
  print(settings.duckdb_path)  # Path オブジェクト
  print(settings.is_live)      # env に応じたフラグ
  ```

- DuckDB 接続して日次 ETL を実行
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- J-Quants の id_token を直接取得
  ```python
  from kabusys.data.jquants_client import get_id_token
  token = get_id_token()  # settings.jquants_refresh_token を使用
  ```

- ニュースのセンチメントスコアを作成（OpenAI 必須）
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect(str(settings.duckdb_path))
  written = score_news(conn, target_date=date(2026,3,20))
  print(f"書き込んだ銘柄数: {written}")
  ```

- 市場レジーム判定（ETF 1321 の ma200 とマクロニュース）
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect(str(settings.duckdb_path))
  score_regime(conn, target_date=date(2026,3,20))
  ```

- 監査ログ DB を初期化（監査テーブル作成）
  ```python
  from kabusys.data.audit import init_audit_db
  conn_audit = init_audit_db("data/audit.duckdb")  # :memory: も可
  ```

- RSS フィード取得（ニュース収集の一部）
  ```python
  from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES
  articles = fetch_rss(DEFAULT_RSS_SOURCES["yahoo_finance"], "yahoo_finance")
  for a in articles[:5]:
      print(a["id"], a["datetime"], a["title"])
  ```

※ 上記の各関数は内部でトランザクションやリトライ、フェイルセーフ処理を持ちます。実行時に必要な環境変数（OpenAI / J-Quants 等）が未設定だと例外を投げます。

---

## 環境変数（主要なもの）

- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須 for J-Quants）
- OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector が必要とする）
- KABU_API_PASSWORD: kabu ステーション API パスワード
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN / SLACK_CHANNEL_ID: Slack 通知に使用
- DUCKDB_PATH: データ用 DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト data/monitoring.db）
- KABUSYS_ENV: one of development / paper_trading / live
- LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 を設定すると .env 自動読み込みを無効化

---

## ディレクトリ構成（抜粋）

プロジェクトの主要なファイルとモジュール構成（src 以下）:

- src/kabusys/
  - __init__.py
  - config.py                    # 環境変数・設定読み込み
  - ai/
    - __init__.py
    - news_nlp.py                # ニュースセンチメント（銘柄単位）
    - regime_detector.py         # 市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py          # J-Quants API クライアント & DuckDB 保存
    - pipeline.py                # ETL パイプライン（run_daily_etl 等）
    - etl.py                     # ETLResult の再公開
    - news_collector.py          # RSS 収集・前処理
    - calendar_management.py     # 市場カレンダー管理（営業日判定等）
    - quality.py                 # データ品質チェック
    - stats.py                   # 汎用統計（zscore_normalize）
    - audit.py                   # 監査ログテーブル初期化 / init_audit_db
  - research/
    - __init__.py
    - factor_research.py         # ファクター計算（momentum/value/volatility）
    - feature_exploration.py     # 将来リターン / IC / 統計サマリ
  - (strategy/, execution/, monitoring/ 等の高位モジュールは別途実装される想定)

---

## 開発 / テスト時の注意

- 自動で .env を読み込む機能はプロジェクトルート（.git もしくは pyproject.toml のある親）を基準に動作します。テスト時に自動読み込みを抑止したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- OpenAI への呼び出しなど外部 API を利用する箇所はテスト時にモック可能な設計（内部呼び出し関数を patch する想定）になっています。
- DuckDB の executemany に関する挙動や SQL の互換性に注意（コード中に互換性対策あり）。

---

## 貢献・ライセンス

- この README にはライセンス情報を含めていません。実プロジェクトでは LICENSE ファイルを用意してください。
- バグ報告・機能提案は Issue、Pull Request を歓迎します。

---

必要であれば README に具体的な例（.env.example の完全版、requirements.txt の想定、CI 実行手順、Docker イメージ化など）を追記します。どの部分を充実させたいか教えてください。