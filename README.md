# KabuSys

日本株向けの自動売買・データ基盤ライブラリ群です。ETL（J-Quants からのデータ取得）、データ品質チェック、ニュース収集・NLP（OpenAI を用いたセンチメント評価）、ファクター計算、監査ログスキーマ、マーケットカレンダー管理などを含みます。

---

## 主な目的（Project Overview）

KabuSys は以下を目的としたライブラリ／ツール群です。

- J-Quants API を用いた株価・財務・カレンダーの差分 ETL パイプライン
- DuckDB をデータレイクとして利用するデータモデルと保存ユーティリティ
- ニュース収集 (RSS) と OpenAI を使ったニュースセンチメントの自動スコアリング
- 市場レジーム判定（ETF の MA200 乖離 + マクロニュースセンチメント）
- 研究用ファクター計算（モメンタム、ボラティリティ、バリュー）と統計ユーティリティ
- 取引監査ログスキーマ（シグナル → 発注 → 約定までのトレース）
- データ品質チェック（欠損、スパイク、重複、日付不整合）

---

## 機能一覧（Features）

- ETL パイプライン（kabusys.data.pipeline）
  - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl
  - 差分取得、バックフィル、品質チェック
- J-Quants クライアント（kabusys.data.jquants_client）
  - get_id_token / fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - DuckDB へ冪等保存（ON CONFLICT DO UPDATE）
  - レートリミッティング・リトライ・トークン自動更新対応
- ニュース収集（kabusys.data.news_collector）
  - RSS 取得、URL 正規化、SSRF 対策、前処理、raw_news への保存想定
- ニュース NLP（kabusys.ai.news_nlp）
  - OpenAI（gpt-4o-mini）で銘柄ごとにセンチメントを算出し ai_scores へ保存
  - バッチ・トリム・リトライ・レスポンス検証
- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF(1321) の MA200 乖離とマクロニュースセンチメントを合成して daily market_regime を生成
- 研究用モジュール（kabusys.research）
  - calc_momentum / calc_volatility / calc_value / calc_forward_returns / calc_ic / factor_summary / rank
  - zscore_normalize（kabusys.data.stats）
- データ品質チェック（kabusys.data.quality）
  - 欠損、スパイク、重複、将来日付・非営業日データ検出
- 監査ログスキーマ初期化（kabusys.data.audit）
  - init_audit_schema / init_audit_db（DuckDB に監査用テーブル/インデックスを作成）

---

## セットアップ手順（Setup）

1. 推奨 Python バージョン
   - Python 3.9+（ソース内の型注釈・標準ライブラリ利用を想定）

2. 仮想環境を作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate (macOS / Linux)
   - .venv\Scripts\activate (Windows)

3. 依存パッケージ（例）
   - pip install duckdb openai defusedxml

   （プロジェクト配布で requirements.txt があればそれを使用してください。）

4. パッケージのインストール（開発時）
   - pip install -e .

5. 環境変数の設定
   - プロジェクトルート（.git または pyproject.toml がある場所）に `.env` または `.env.local` を置くと、自動的に読み込まれます（自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1）。
   - 主に使用する環境変数（Settings で参照）:

     - 必須 / 認証
       - JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
       - KABU_API_PASSWORD: kabuステーション API パスワード（必須）
       - OPENAI_API_KEY: OpenAI API キー（score_news/score_regime 実行時に利用可能）
     - 任意（デフォルト値あり）
       - KABU_API_BASE_URL: デフォルト "http://localhost:18080/kabusapi"
       - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID
       - DUCKDB_PATH: デフォルト "data/kabusys.duckdb"
       - SQLITE_PATH: デフォルト "data/monitoring.db"
       - PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START
       - CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
       - KABUSYS_ENV: one of "development", "paper_trading", "live" (default "development")
       - LOG_LEVEL: "DEBUG","INFO","WARNING","ERROR","CRITICAL"（default "INFO"）

   - 設定は kabusys.config.settings 経由で取得できます。必須項目が未設定だと ValueError を送出します。

---

## 使い方（Usage）

基本的な利用例を示します。実行の前に必ず環境変数（JQUANTS_REFRESH_TOKEN, OPENAI_API_KEY など）を設定してください。

- DuckDB 接続を作り ETL を実行する（日次 ETL の例）:

```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")  # settings.duckdb_path と合わせる
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- ニュースセンチメントをスコアリングして ai_scores に保存する:

```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
# api_key を明示的に渡すか、環境変数 OPENAI_API_KEY を設定
count = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
print(f"scored {count} codes")
```

- 市場レジーム判定を実行する:

```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

- 監査ログ用 DB を初期化する:

```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# conn は DuckDB 接続。テーブルが作成されます。
```

- RSS フィードの取得（ニュース収集ユーティリティ）:

```python
from kabusys.data.news_collector import fetch_rss

articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
for a in articles[:5]:
    print(a["id"], a["datetime"], a["title"])
```

- J-Quants の ID トークン取得（テストや直接利用時）:

```python
from kabusys.data.jquants_client import get_id_token
token = get_id_token()  # settings.jquants_refresh_token を使用
```

注意点:
- AI 関連関数（score_news / score_regime）は OpenAI API 呼び出しを含みます。API キーの管理とコストに注意してください。
- 各関数はルックアヘッドバイアス防止のため、内部で date.today() を固定的に参照しない設計になっています。必ず target_date を明示的に渡すことを推奨します。
- ETL / 保存関数は DuckDB を前提とした SQL スキーマに合わせて実装されています。実行前に適切なスキーマを用意してください（既存の DB に追記する想定）。

---

## よく使うモジュールの説明（短いリファレンス）

- kabusys.config
  - settings: 実行時設定（環境変数から読み込み、自動 .env ロードあり）
- kabusys.data.jquants_client
  - fetch_daily_quotes / save_daily_quotes
  - fetch_financial_statements / save_financial_statements
  - fetch_market_calendar / save_market_calendar
  - get_id_token
- kabusys.data.pipeline
  - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl
  - ETLResult データクラス
- kabusys.data.quality
  - run_all_checks / check_missing_data / check_spike / check_duplicates / check_date_consistency
- kabusys.data.news_collector
  - fetch_rss / preprocess_text / _make_article_id（内部ユーティリティ）
- kabusys.ai.news_nlp
  - score_news（ニュースから銘柄ごとの ai_score を作成）
- kabusys.ai.regime_detector
  - score_regime（市場レジームを判定して market_regime に書き込み）
- kabusys.data.audit
  - init_audit_schema / init_audit_db（監査ログスキーマ）

---

## ディレクトリ構成（抜粋）

プロジェクトは src/kabusys 以下にモジュール群が格納されています。主要ファイル・ディレクトリは次の通りです。

- src/
  - kabusys/
    - __init__.py
    - config.py                       (環境変数・設定管理)
    - ai/
      - __init__.py
      - news_nlp.py                   (ニュースNLP スコアリング)
      - regime_detector.py            (市場レジーム判定)
    - data/
      - __init__.py
      - jquants_client.py             (J-Quants API クライアント & DuckDB 保存)
      - pipeline.py                   (ETL パイプライン)
      - etl.py                        (ETLResult エクスポート)
      - news_collector.py             (RSS ニュース収集)
      - quality.py                    (データ品質チェック)
      - calendar_management.py        (マーケットカレンダー管理)
      - stats.py                      (統計ユーティリティ: zscore_normalize)
      - audit.py                      (監査ログスキーマ初期化)
    - research/
      - __init__.py
      - factor_research.py            (momentum/value/volatility)
      - feature_exploration.py        (forward returns, IC, summary, rank)
    - ai/ (上記)
    - research/ (上記)

（上記はコードベースから抽出した代表的ファイル群です。実際のプロジェクトには追加ファイルやテスト、ドキュメント、pyproject.toml 等が存在する可能性があります。）

---

## 運用上の注意 / ベストプラクティス

- 本リポジトリは実運用（live）およびペーパートレード（paper_trading）を想定しています。KABUSYS_ENV を正しく設定して運用モードを切り替えてください。
- OpenAI / J-Quants の API キーは機密情報です。`.env` や CI シークレットに安全に格納してください。
- DuckDB ファイルはデフォルトで data/kabusys.duckdb に作成されます。バックアップ／バージョン管理（差分）を検討してください。
- ETL は外部 API 呼び出しを伴うため、ネットワークエラーや API 制限に備えた再実行戦略を運用外側で用意してください（Cron / ジョブスケジューラなど）。
- AI 呼び出し（OpenAI）はコストが発生します。バッチサイズや呼び出し頻度を適切に調整してください。

---

## サポート / 開発に関して

- テスト時は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env 自動ロードを無効にできます。
- OpenAI 呼び出しや外部 HTTP をテストで差し替えられるように、各モジュールは呼び出し箇所をモック可能な設計になっています（例: kabusys.ai.news_nlp._call_openai_api を unittest.mock.patch で置き換え）。
- 変更を加える場合は、ETL の互換性（スキーマ、INSERT の ON CONFLICT 動作）と Look-ahead バイアスの回避ポリシーに注意してください。

---

必要であれば README の英語版や、環境変数の .env.example（テンプレート）、セットアップのための requirements.txt / pyproject.toml の例も作成します。どれを優先しますか？