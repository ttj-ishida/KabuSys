# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリセットです。  
ETL（J-Quants からの市場データ取得）・データ品質チェック・ニュース収集・LLM を用いたニュースセンチメント解析・市場レジーム判定・研究用ファクター計算・監査ログ（トレーサビリティ）などを提供します。

バージョン: 0.1.0

---

## 概要

主な目的は次の通りです。

- J-Quants API から株価・財務・マーケットカレンダー等を差分取得して DuckDB に保存する ETL パイプライン
- raw_news（RSS）収集・銘柄紐付け・LLM を用いたニュースセンチメント算出（ai_scores テーブルへの保存）
- ETF の移動平均乖離等とマクロニュースの LLM センチメントを合成した市場レジーム判定
- ファクター（モメンタム、ボラティリティ、バリュー等）の計算・探索用ユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 発注〜約定までをトレースできる監査ログスキーマ（DuckDB）
- セキュリティ・耐障害性を考慮した実装（SSRF 対策、API リトライ、レートリミット、フェイルセーフ）

---

## 機能一覧

- ETL
  - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl（kabusys.data.pipeline）
  - J-Quants クライアント：fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar（kabusys.data.jquants_client）
- データ品質
  - 欠損、スパイク、重複、日付不整合チェック（kabusys.data.quality）
- ニュース
  - RSS 収集（fetch_rss）・前処理・保存の骨組み（kabusys.data.news_collector）
- AI（LLM）
  - 銘柄別ニュースのセンチメント算出（score_news, kabusys.ai.news_nlp）
  - 市場レジーム判定（score_regime, kabusys.ai.regime_detector）
  - 両方とも OpenAI Chat API（gpt-4o-mini 等）を利用（JSON Mode の利用を想定）
- 研究用（Research）
  - ファクター計算（calc_momentum, calc_value, calc_volatility）
  - 将来リターン計算、IC、統計サマリー等（kabusys.research）
- カレンダー管理
  - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, calendar_update_job（kabusys.data.calendar_management）
- 監査ログ（Audit）
  - 監査用テーブルの初期化・インデックス定義（kabusys.data.audit.init_audit_db / init_audit_schema）
- 設定管理
  - .env 自動読み込み（プロジェクトルート検出）と Settings API（kabusys.config）

---

## 前提・依存関係

- Python 3.10 以上（typing の | 記法などを使用）
- 主な Python パッケージ（例）:
  - duckdb
  - openai
  - defusedxml
- その他標準ライブラリ多数（urllib, json, datetime, logging 等）

実際のインストール時はプロジェクトに同梱の requirements.txt / pyproject.toml を参照してください（本コード断片には含まれていません）。

---

## 環境変数（主要）

設定は .env または環境変数で行います。パッケージは自動的にプロジェクトルート（.git または pyproject.toml のあるディレクトリ）を探索して `.env` と `.env.local` を読み込みます（OS環境変数は上書きされません）。自動読み込みを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

必須／推奨の環境変数（README 用の代表例）:

- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD — kabuステーション API のパスワード（必須）
- SLACK_BOT_TOKEN — Slack 通知用ボットトークン（必須）
- SLACK_CHANNEL_ID — Slack 送信先チャンネルID（必須）
- OPENAI_API_KEY — OpenAI API キー（AI 関数呼び出し時に必要）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用途などの SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 環境: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — ログレベル: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）

kabusys.config.Settings でこれらを参照できます（例: from kabusys.config import settings; settings.jquants_refresh_token）。

---

## セットアップ手順（例）

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo-root>
   ```

2. Python 仮想環境作成・有効化
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS/Linux
   .venv\Scripts\activate      # Windows
   ```

3. 必要パッケージをインストール
   （プロジェクトに pyproject.toml や requirements.txt があればそれを使う）
   ```
   pip install duckdb openai defusedxml
   # またはパッケージを編集可能モードでインストール
   pip install -e .
   ```

4. 環境変数設定
   - プロジェクトルートに `.env` を作成し必要項目を記載
   - 例（.env）:
     ```
     JQUANTS_REFRESH_TOKEN=xxxxx
     OPENAI_API_KEY=sk-xxxxx
     KABU_API_PASSWORD=your_kabu_password
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     ```
   - テスト時に自動ロードを抑止する場合:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```

5. DuckDB（および監査DB）初期化（必要に応じて）
   Python REPL で:
   ```python
   import duckdb
   from kabusys.config import settings
   from kabusys.data.audit import init_audit_db

   # メイン DB に接続している DuckDB 接続を作成する例
   conn = duckdb.connect(str(settings.duckdb_path))
   # 監査用 DB を初期化する（ファイルパスを与える）
   audit_conn = init_audit_db(settings.duckdb_path)  # 監査専用 DB を使うなら別パス指定可
   ```

---

## 使い方（代表的な呼び出し例）

- 日次 ETL を実行（J-Quants からの差分取得・保存・品質チェック）
  ```python
  from datetime import date
  import duckdb
  from kabusys.config import settings
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメント（銘柄別）を実行
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  # OPENAI_API_KEY は環境変数に設定しておくか、api_key 引数で渡す
  n_written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"Written scores: {n_written}")
  ```

- 市場レジーム判定を実行
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect(str(settings.duckdb_path))
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 研究用のファクター計算（例：モメンタム）
  ```python
  from datetime import date
  import duckdb
  from kabusys.research.factor_research import calc_momentum

  conn = duckdb.connect("data/kabusys.duckdb")
  recs = calc_momentum(conn, date(2026, 3, 20))
  # recs は [{ "date": ..., "code": "XXXX", "mom_1m": ..., ... }, ...]
  ```

- RSS フィードの取得（ニュース収集の一部）
  ```python
  from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES

  articles = fetch_rss(DEFAULT_RSS_SOURCES["yahoo_finance"], source="yahoo_finance")
  for a in articles:
      print(a["id"], a["datetime"], a["title"])
  ```

- 監査スキーマの初期化（既存 DuckDB 接続に対して）
  ```python
  from kabusys.data.audit import init_audit_schema
  conn = duckdb.connect("data/kabusys.duckdb")
  init_audit_schema(conn, transactional=True)
  ```

---

## 自動 .env 読み込みの挙動

- 自動読み込み対象ファイル（優先度低→高）: `.env` → `.env.local`
- OS 環境変数は保護され、既に設定されているキーは .env によって上書きされません（.env.local は override=True でロードされますが OS の既存キーは保護されます）。
- 自動読み込みを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- プロジェクトルートは `.git` または `pyproject.toml` の存在を基準に探索します（CWD に依存しません）。見つからない場合は自動ロードをスキップします。

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 以下の主要モジュール・ファイル構成です（抜粋）:

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
    - quality.py
    - stats.py
    - news_collector.py
    - calendar_management.py
    - audit.py
    - etl.py (再エクスポート用)
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py

（実際のディレクトリには他の補助モジュールやユーティリティも含まれます）

---

## テスト・開発時の注意点

- LLM や外部 API 呼び出し（OpenAI / J-Quants / RSS）を伴う関数はネットワーク依存のため、ユニットテストでは依存箇所をモック（patch）することを想定しています。コード内でも _call_openai_api 等を patch することでテスト可能です。
- DuckDB の executemany に空リストを渡すとエラーになるバージョンがあるため、モジュール側で空チェックを行っています。
- Look-ahead bias に注意：関数群は内部で datetime.today() を直接参照しない設計を心がけています（テスト／バックテストの再現性向上）。

---

## 最後に

この README はコードベースの抜粋から作成した概要ドキュメントです。各モジュールの詳細な仕様や API 引数、戻り値の完全な説明はモジュールの docstring（ソース内コメント）を参照してください。追加の README セクション（デプロイ、CI、運用手順、Slack 通知設定など）が必要であれば、目的に合わせて追記できます。