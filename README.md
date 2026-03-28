# KabuSys — 日本株自動売買基盤（ドキュメント）

KabuSys は日本株向けのデータパイプライン、解析（研究）ツール、AI ベースのニュース解析、
監査ログ機能を備えた自動売買プラットフォームのコアライブラリ群です。
このリポジトリは「データ取得・品質管理・ファクター計算・ニュース NLP・市場レジーム判定・監査ログ」などを提供します。

主な目的
- J-Quants API からの株価・財務・カレンダー取得および DuckDB へ保存（ETL）
- ニュース（RSS）収集と OpenAI を使った銘柄別センチメント算出
- ファクター（モメンタム/ボラティリティ/バリュー等）計算と研究ユーティリティ
- 市場レジーム判定（ETF MA とマクロニュースの組合せ）
- 発注・約定に関する監査ログ（DuckDB ベース）整備
- データ品質チェック（欠損・重複・スパイク・日付整合性）

---

## 機能一覧（概要）

- 環境設定
  - .env / .env.local からの自動読み込み（`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可）
  - 必須環境変数を Settings オブジェクト経由で取得
- データ ETL（kabusys.data.pipeline）
  - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl
  - J-Quants API クライアント（kabusys.data.jquants_client）: 取得・ページネーション・保存（冪等）
- ニュース収集（kabusys.data.news_collector）
  - RSS フィード収集、URL 正規化、SSRF 対策、前処理、raw_news への冪等保存想定
- 品質チェック（kabusys.data.quality）
  - 欠損、スパイク、重複、日付不整合を検出し QualityIssue を返す
- 監査ログ（kabusys.data.audit）
  - signal_events / order_requests / executions 等のテーブル作成・初期化ユーティリティ
  - init_audit_db / init_audit_schema：DuckDB で監査 DB を初期化
- AI（kabusys.ai）
  - score_news: OpenAI を用いた銘柄別ニュースセンチメント算出 → ai_scores へ保存
  - score_regime: ETF（1321）の MA200 乖離とマクロニュース LLM スコアを合成し market_regime へ保存
- 研究（kabusys.research）
  - calc_momentum / calc_value / calc_volatility
  - calc_forward_returns / calc_ic / factor_summary / rank
- 汎用統計（kabusys.data.stats）
  - zscore_normalize（クロスセクション Z スコア正規化）

---

## 前提・依存（主なもの）

- Python 3.10 以上（型注釈の | None などを使用）
  - 推奨: Python 3.11
- ライブラリ（最低限、プロジェクトで使用されるもの）
  - duckdb
  - openai (OpenAI Python SDK; gpt-4o-mini 等を呼ぶため)
  - defusedxml
  - （標準ライブラリで urllib, json, datetime, logging 等を使用）
- 外部サービス
  - J-Quants API（取得用リフレッシュトークン）
  - OpenAI API（OPENAI_API_KEY）
  - kabuステーション 等（発注周りを使う場合）
  - Slack（通知連携に利用する場合。SLACK_BOT_TOKEN 等）

注意: ここに挙げたパッケージ名は最小限です。プロジェクトの packaging / requirements.txt がある場合はそちらを優先してください。

---

## 必須環境変数（主なもの）

- JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン
- OPENAI_API_KEY — OpenAI の API キー（score_news / score_regime 実行時に引数で渡すことも可）
- KABU_API_PASSWORD — kabuステーション API パスワード（発注連携で必要）
- SLACK_BOT_TOKEN — Slack 通知用トークン（通知を行う場合）
- SLACK_CHANNEL_ID — Slack 通知先チャンネル ID

その他オプション:
- KABUSYS_ENV — "development" / "paper_trading" / "live"（デフォルト: development）
- LOG_LEVEL — "DEBUG" / "INFO" / ...（デフォルト: INFO）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite パス（モニタリング等で使用）

.env 自動読み込み:
- プロジェクトルート（.git または pyproject.toml がある位置）から `.env` と `.env.local` を自動読み込みします。
- 自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## セットアップ手順（例）

1. リポジトリをクローン
   - git clone ...

2. Python 仮想環境を作成して有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール（最小例）
   - pip install --upgrade pip
   - pip install duckdb openai defusedxml

   （プロジェクトに requirements.txt / pyproject.toml がある場合はそちらを利用してください:
   pip install -r requirements.txt または pip install .）

4. 環境変数を設定
   - プロジェクトルートに `.env` を作成（例）
     JQUANTS_REFRESH_TOKEN=あなたの_jquants_refresh_token
     OPENAI_API_KEY=sk-...
     KABU_API_PASSWORD=...
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567

   - または CI / デプロイ環境で環境変数としてセット。

5. DuckDB ファイル用ディレクトリを作成（必要に応じて）
   - mkdir -p data

6. 監査 DB 初期化（任意）
   - Python REPL / スクリプトで:
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")  # ":memory:" でも可

---

## 使い方（簡単なコード例）

以下はライブラリの主要機能を呼び出す最小例です。実運用ではロギング設定や例外処理、
トークン管理を適切に行ってください。

- DuckDB に接続して ETL を実行する（日次 ETL）

```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメントをスコアして ai_scores に保存する

```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026, 3, 20))
print(f"wrote {n_written} scores")
```

- 市場レジームをスコアして market_regime に書き込む

```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査 DB 初期化（別 DB を使う場合）

```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# conn は DuckDB 接続。テーブル群が作成されていることを確認できます。
```

- Settings（環境変数読み込み）

```python
from kabusys.config import settings
print(settings.duckdb_path)        # Path オブジェクト
print(settings.is_live, settings.log_level)
```

---

## 注意点 / 実装上の考慮

- Look-ahead bias の回避
  - ai モジュール・ETL 等は内部で date の取り扱いに注意し、target_date より未来のデータを参照しない設計になっています（datetime.today() を直接使わない等）。
- 冪等性
  - J-Quants から取得して DuckDB に保存する処理は ON CONFLICT / UPSERT を使い冪等に設計されています。
- API リトライ / レート制御
  - J-Quants クライアントはレートリミット（120 req/min）を守る RateLimiter を導入しています。OpenAI 呼び出しにもリトライロジックがあります。
- セキュリティ
  - news_collector では SSRF 対策、XML の安全パース（defusedxml）、受信サイズ制限などを実装しています。

---

## ディレクトリ構成（主要ファイル）

（src 配下をベースに抜粋）

- src/kabusys/
  - __init__.py
  - config.py — 環境変数読み込み・Settings
  - ai/
    - __init__.py
    - news_nlp.py — ニュースセンチメント算出（score_news）
    - regime_detector.py — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - calendar_management.py — 市場カレンダー管理・営業日ロジック
    - etl.py — ETL 結果型再エクスポート
    - pipeline.py — ETL パイプライン（run_daily_etl 等）
    - stats.py — zscore_normalize 等統計ユーティリティ
    - quality.py — データ品質チェック
    - audit.py — 監査ログテーブル定義・初期化
    - jquants_client.py — J-Quants API クライアント（fetch / save 実装）
    - news_collector.py — RSS 取得・前処理
  - research/
    - __init__.py
    - factor_research.py — calc_momentum / calc_volatility / calc_value
    - feature_exploration.py — calc_forward_returns / calc_ic / factor_summary / rank

（上記以外にも strategy / execution / monitoring 等のトップレベルエクスポートが __all__ に定義されていますが、今回抜粋したモジュールが主要なコア機能です。）

---

## 開発時のヒント

- テスト時に .env の自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- OpenAI の呼び出しをユニットテストで差し替える際には、モジュール内の `_call_openai_api` をモックすることが想定されています（news_nlp._call_openai_api / regime_detector._call_openai_api）。
- DuckDB は軽量でファイルベースのため、CI では ":memory:" を使うことも可能です（init_audit_db(":memory:") など）。
- ロギングはモジュール単位の logger.getLogger(__name__) を使用しているため、アプリ側で logging.basicConfig()/dictConfig を設定して出力を制御してください。

---

## ライセンス・貢献

この README 内ではライセンス情報を含めていません。実際のプロジェクトルートにある LICENSE や CONTRIBUTING.md を参照してください。
貢献やバグ報告、機能追加は Pull Request / Issue を通して受け付けてください。

---

以上がこのコードベースの概要・セットアップ・使い方・構成の簡易ドキュメントです。追加で README に記載したいサンプルや、CI/デプロイ手順、requirements.txt の生成、具体的な DB スキーマ（列名一覧）などが必要であれば教えてください。