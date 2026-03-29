# KabuSys

日本株向けの自動売買・データプラットフォームライブラリです。  
ETL（J-Quants 経由の市場データ取得）、ニュース収集・NLP スコアリング、ファクター計算、研究用ユーティリティ、監査ログ（発注トレーサビリティ）などの機能を提供します。

主な設計方針：
- ルックアヘッドバイアスを避ける（内部で datetime.today()/date.today() を直接参照しない箇所が多い）
- DuckDB を主なローカルデータベースとして利用
- 外部 API 呼び出し（J-Quants / OpenAI）はリトライ・フェイルセーフを備える
- 冪等性・トレーサビリティを重視（ETL の ON CONFLICT、監査テーブル、order_request_id の冪等キーなど）

---

## 機能一覧

- data
  - ETL パイプライン（prices / financials / calendar）の差分取得と保存（jquants_client 経由）
  - 市場カレンダー管理（営業日判定、next/prev trading day 等）
  - ニュース収集（RSS）とニュース→銘柄紐付け（news_collector）
  - データ品質チェック（欠損、スパイク、重複、日付整合性）
  - 監査ログ（signal_events / order_requests / executions）テーブル初期化・管理
  - 汎用統計ユーティリティ（zscore 正規化）
  - J-Quants クライアント（rate limiting、token リフレッシュ、保存関数）
- ai
  - ニュース NLP スコアリング（gpt-4o-mini を使用。JSON Mode でレスポンス検証）
  - 市場レジーム判定（ETF 1321 の MA200 乖離 + マクロニュースの LLM センチメントを合成）
  - OpenAI 呼び出しはリトライ・フォールバック（失敗時は中立スコア）
- research
  - ファクター計算（モメンタム / ボラティリティ / バリュー）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリー
- config
  - 環境変数管理（.env / .env.local の自動ロードを提供、必要な設定をプロパティで取得）

---

## 必要な環境変数（主なもの）

アプリケーション起動 / 各機能で必須な環境変数（.env に定義しておく）:

- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD : kabu ステーション API パスワード（必須）
- SLACK_BOT_TOKEN : Slack 通知用ボットトークン（必須）
- SLACK_CHANNEL_ID : Slack チャンネルID（必須）
- OPENAI_API_KEY : OpenAI API キー（ai.score_news / ai.score_regime で使用）
- KABUSYS_ENV : 環境 (development | paper_trading | live)（省略時: development）
- LOG_LEVEL : ログレベル (DEBUG/INFO/WARNING/ERROR/CRITICAL)（省略時: INFO）
- KABU_API_BASE_URL : kabu API のベース URL（省略時: http://localhost:18080/kabusapi）
- DUCKDB_PATH : DuckDB ファイルパス（省略時: data/kabusys.duckdb）
- SQLITE_PATH : SQLite パス（監視用、デフォルト: data/monitoring.db）

自動 .env ロード
- パッケージはプロジェクトルート（.git または pyproject.toml を検出）を基に `.env` と `.env.local` を自動でロードします。
- 自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## セットアップ手順（例）

1. リポジトリをクローン
   ```
   git clone <リポジトリURL>
   cd <repo>
   ```

2. Python 仮想環境の作成（例: venv）
   ```
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   ```

3. 依存関係のインストール  
   ※ requirements ファイルがある想定。なければプロジェクトで使用している主なライブラリをインストールしてください。
   ```
   pip install -e ".[dev]"   # setup.cfg/pyproject がある場合の編集モードインストール
   # あるいは個別:
   pip install duckdb openai defusedxml
   ```

4. .env を作成  
   プロジェクトルートに `.env`（および必要なら `.env.local`）を作成し、上記必須環境変数を設定します。`.env.example` を用意している場合はそれを参考にしてください。

5. データベースディレクトリ作成（必要に応じて）
   ```
   mkdir -p data
   ```

---

## 使い方（主要なユースケース）

Python スクリプトや REPL から直接呼び出して利用できます。以下は代表的な呼び出し例です（DuckDB 接続は `duckdb.connect(path)` を想定）。

- 日次 ETL を実行（株価・財務・カレンダー取得 + 品質チェック）
  ```py
  from datetime import date
  import duckdb
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  res = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(res.to_dict())
  ```

- ニュース NLP スコアリング（OpenAI API キーが必要）
  ```py
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  count = score_news(conn, target_date=date(2026, 3, 20))
  print(f"scored {count} symbols")
  ```

- 市場レジーム判定
  ```py
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 研究用ファクター計算
  ```py
  from datetime import date
  import duckdb
  from kabusys.research import calc_momentum, calc_value, calc_volatility

  conn = duckdb.connect("data/kabusys.duckdb")
  m = calc_momentum(conn, date(2026,3,20))
  v = calc_value(conn, date(2026,3,20))
  vol = calc_volatility(conn, date(2026,3,20))
  ```

- 監査ログ DB 初期化（監査専用 DB）
  ```py
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  ```

- J-Quants の ID トークンを取得
  ```py
  from kabusys.data.jquants_client import get_id_token
  token = get_id_token()  # 環境変数 JQUANTS_REFRESH_TOKEN を参照
  ```

注意点：
- OpenAI 呼び出しは JSON Mode を利用し、レスポンスのバリデーションを行います。テストでは内部の `_call_openai_api` 関数をモックして置き換えることが想定されています。
- DuckDB の executemany に空リストを渡すと失敗するバージョンがあるため、ライブラリは空チェックを行っています。
- ETL / API 呼び出しは多くがリトライ・バックオフを実装しています。

---

## ディレクトリ構成（主要ファイル）

リポジトリは src 配下にパッケージを配置する構成を想定しています。主要モジュールを抜粋します。

- src/kabusys/
  - __init__.py
  - config.py                     — 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py                  — ニュース NLP（score_news）
    - regime_detector.py           — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py            — J-Quants API クライアント（fetch / save）
    - pipeline.py                  — ETL パイプライン（run_daily_etl 等）
    - etl.py                       — ETL の公開インターフェース（ETLResult）
    - news_collector.py            — RSS ニュース収集
    - calendar_management.py       — 市場カレンダー管理（is_trading_day 等）
    - quality.py                   — データ品質チェック
    - stats.py                     — 統計ユーティリティ（zscore）
    - audit.py                     — 監査ログテーブル初期化
  - research/
    - __init__.py
    - factor_research.py           — モメンタム/ボラティリティ/バリュー計算
    - feature_exploration.py       — 将来リターン/IC/統計サマリー
  - research/...                    — 研究用ユーティリティ
  - ... その他モジュール（strategy / execution / monitoring 等は __all__ に定義）

実際のファイルは src/kabusys 以下に多数の実装ファイルが含まれます（上記は主要なものの抜粋です）。

---

## 開発・テストに関する補足

- 自動 .env 読み込みはプロジェクトルート判定（.git or pyproject.toml）を行います。パッケージ化後やテスト時に挙動が不要であれば `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して無効化してください。
- OpenAI の呼び出しはモックしやすく設計されています（内部 `_call_openai_api` を unittest.mock.patch などで差し替える）。
- J-Quants API は rate limit（120 req/min）を守るために内部でレートリミッタを使用しています。

---

## ライセンス / 注意事項

- この README では実装の概要と利用手順を示しています。実稼働環境での利用（特に発注関連）は十分に検証を行い、paper_trading 環境での確認を経てから live に切り替えてください。
- 外部 API キーやトークンの管理には十分注意してください。.env は秘匿情報を含むためバージョン管理に含めないでください。

---

必要であれば README にサンプル .env.example のテンプレートや、主要な SQL スキーマ（監査テーブル DDL）抜粋、よくあるトラブルシュートのセクションも追加できます。どの情報を追加したいか教えてください。