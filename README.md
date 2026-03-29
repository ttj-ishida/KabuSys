# KabuSys

日本株向けのデータプラットフォーム / 研究・AI評価・監査・ETL を備えた自動売買支援ライブラリです。DuckDB をデータ層として使い、J-Quants API や RSS / OpenAI を組み合わせて市場データ収集、品質チェック、ニュースNLP、レジーム判定、ファクター計算、監査ログ管理などを行います。

## 主な特徴（機能一覧）

- 環境設定管理
  - .env / .env.local 自動読み込み（プロジェクトルート検出）／無効化フラグあり
- データ取得・保存（J-Quants クライアント）
  - 株価日足（OHLCV）、財務データ、JPXマーケットカレンダーの取得・保存（ページネーション・リトライ・レート制御）
- ETL パイプライン
  - 日次 ETL（カレンダー → 株価 → 財務 → 品質チェック）、個別 ETL ジョブ
- データ品質チェック
  - 欠損、重複、スパイク（前日比）、日付不整合などの検出
- ニュース収集
  - RSS からの安全な収集（SSRF 回避、トラッキング除去、最大受信サイズ等）
- ニュース NLP / AI スコアリング
  - OpenAI（gpt-4o-mini）を用いた銘柄センチメントスコア（バッチ処理・JSON mode）
  - ニュースウィンドウ定義（JST基準）
- 市場レジーム判定
  - ETF（1321）の MA200乖離 + マクロニュースセンチメントを合成して日次で bull/neutral/bear を判定・保存
- 研究用ユーティリティ
  - ファクター計算（モメンタム / ボラティリティ / バリュー 等）、将来リターン計算、IC 計算、Zスコア正規化
- 監査ログ（トレーサビリティ）
  - signal_events / order_requests / executions 等の監査テーブルを DuckDB に冪等で初期化・管理

---

## 動作要件

- Python 3.10+
- 必要なライブラリ（代表例）
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants API、RSS フィード、OpenAI API）

（実際のパッケージ化時は requirements.txt / pyproject.toml を参照してください）

---

## セットアップ手順

1. リポジトリをクローン / パッケージを取得
   - 例: git clone <repo>

2. Python 仮想環境作成・アクティブ化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   - pip install -U pip
   - pip install duckdb openai defusedxml
   - （パッケージが pyproject.toml / requirements.txt を持つ場合はそちらを使用）

4. パッケージの開発インストール（任意）
   - pip install -e .

5. 環境変数の設定
   - プロジェクトルート（.git や pyproject.toml がある場所）に `.env` / `.env.local` を置くと自動読み込みされます。
   - 自動ロードを無効にする場合:
     - 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定
   - 読み込み優先順位: OS 環境変数 > .env.local > .env

必要な環境変数（主なもの）
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD : kabu API パスワード（必須）
- SLACK_BOT_TOKEN : Slack 通知用の Bot トークン（必須）
- SLACK_CHANNEL_ID : Slack チャンネル ID（必須）
- OPENAI_API_KEY : OpenAI API キー（news_nlp / regime_detector 実行時に必要）
- KABUSYS_ENV : 実行環境 (development / paper_trading / live)（省略時 development）
- LOG_LEVEL : ログレベル (DEBUG / INFO / WARNING / ERROR / CRITICAL)（省略時 INFO）
- DUCKDB_PATH : デフォルトの DuckDB ファイルパス（省略時 data/kabusys.duckdb）
- SQLITE_PATH : 監視用 SQLite パス（省略時 data/monitoring.db）

---

## 使い方（代表的な API・実行例）

以下はライブラリを直接インポートして使う例です。関数は DuckDB の接続オブジェクト（duckdb.connect(...) が返す接続）を受け取ります。

- DuckDB 接続の例:
  ```python
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")
  ```

- 日次 ETL を実行（市場カレンダー → 株価 → 財務 → 品質チェック）
  ```python
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースのセンチメントスコア付与（OpenAI 必須）
  ```python
  from datetime import date
  from kabusys.ai.news_nlp import score_news
  import duckdb

  conn = duckdb.connect("data/kabusys.duckdb")
  # OPENAI_API_KEY は環境変数または api_key 引数で指定
  count = score_news(conn, target_date=date(2026, 3, 20))
  print(f"scored {count} codes")
  ```

- 市場レジーム判定（1321 MA200 + マクロニュース）
  ```python
  from datetime import date
  from kabusys.ai.regime_detector import score_regime
  import duckdb

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- RSS フィード取得（ニュース収集）
  ```python
  from kabusys.data.news_collector import fetch_rss
  from datetime import datetime

  articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
  for a in articles:
      print(a["id"], a["datetime"], a["title"])
  ```

- 監査ログ用 DB 初期化（監査スキーマのみ）
  ```python
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  ```

- J-Quants の ID トークン取得
  ```python
  from kabusys.data.jquants_client import get_id_token
  token = get_id_token()  # JQUANTS_REFRESH_TOKEN を参照
  ```

注意点:
- 多くの関数は内部で特定のテーブル（raw_prices, raw_financials, raw_news, market_calendar, ai_scores, news_symbols, prices_daily, etc.）を参照・更新します。スキーマ初期化はこのリポジトリの別モジュールやデータ定義に依存します（必要に応じてスキーマ作成ルーチンを用意してください）。
- OpenAI 呼び出しや J-Quants API 呼び出しは課金/レート制限の対象です。適切な API キーと運用上の注意を行ってください。

---

## 設定（config）に関して

- モジュール: `kabusys.config.Settings` を通じて設定値へアクセスできます。
  - 例: `from kabusys.config import settings; settings.jquants_refresh_token`
- .env の自動ロード動作:
  - モジュール import 時にプロジェクトルートを探し（`.git` または `pyproject.toml`）、`.env` と `.env.local` を読み込みます。
  - 読み込み順: OS 環境 > .env.local (override=True) > .env (override=False)
  - 自動ロードを無効化したい場合: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`
- 設定の検証:
  - `KABUSYS_ENV` の値は `development` / `paper_trading` / `live` のいずれかでないと例外になります。
  - `LOG_LEVEL` は `DEBUG/INFO/WARNING/ERROR/CRITICAL` のいずれか。

---

## ディレクトリ構成（主要ファイル）

（プロジェクトの root 配下に `src/kabusys/` を配置している想定）

- src/kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py
    - regime_detector.py
  - data/
    - __init__.py
    - calendar_management.py
    - etl.py
    - pipeline.py
    - stats.py
    - quality.py
    - audit.py
    - jquants_client.py
    - news_collector.py
    - (ETLResult re-export in etl.py)
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - (そのほか strategy, execution, monitoring モジュールは __init__ の __all__ に記載あり—実装は別途)

上記ファイル群はそれぞれ
- data/* : データ取得・ETL・品質管理・監査ログ・ニュース収集
- ai/*   : OpenAI を使ったニューススコアリング・レジーム判定
- research/* : ファクター計算や探索的分析用ユーティリティ

---

## 運用上の注意 / ベストプラクティス

- DuckDB のスキーマ（テーブル定義）は本リポジトリに含まれている DDL を参考に初期化してください（例: audit.init_audit_schema）。
- OpenAI 呼び出しはレートやコストに敏感です。バッチサイズやリトライ挙動は各モジュールでパラメータ化されています。API キーの取り扱いには注意してください。
- ETL の差分ロジックは最終取得日を基に設計されています。初回ロード時は過去範囲を十分に確保してください。
- ニュース収集は外部 RSS に依存します。SSRF 対策や受信サイズチェックなどの安全機構が働きますが、社内運用時はホワイトリスト管理等を検討してください。
- 本ライブラリはバックテスト用コードや発注実行コードと切り離して利用する前提で設計されています。発注周りのコードは監査ログを使ってトレーサビリティを担保してください。

---

もし README に含めてほしい追加情報（例: schema 初期化スクリプト、requirements.txt、CI 手順、実運用での設定例など）があれば教えてください。必要に応じて追記します。