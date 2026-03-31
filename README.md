# KabuSys

日本株向け自動売買・データ基盤ライブラリ & ユーティリティ集

---

## プロジェクト概要

KabuSys は日本株のデータ収集（J-Quants）、データ品質チェック、ETL パイプライン、ニュースの NLP によるセンチメント評価、研究用ファクター計算、監査ログ（トレーサビリティ）、および市場レジーム判定などを提供する Python モジュール群です。バックテストや自動売買システムの基盤処理（データ取得・保存・スコアリング・監査）を安全かつ冪等に実行できるよう設計されています。

設計上の特徴：
- Look-ahead bias を防ぐ（内部で datetime.today() を直接参照しない設計の関数群）
- DuckDB を利用したローカル DB（ETL / 監査用）
- J-Quants API 用の堅牢なクライアント（レート制御・リトライ・トークン自動リフレッシュ）
- OpenAI（gpt-4o-mini）を使ったニュース/マクロセンチメント解析（JSON mode を利用）
- ニュース収集時の SSRF / XML 脆弱性対策（URL 検証・defusedxml 使用）
- ETL/品質チェックは部分失敗に耐える設計（問題を集約して呼び出し元へ返す）

---

## 主な機能一覧

- 環境設定管理
  - .env 自動読み込み（プロジェクトルート検出：.git または pyproject.toml）
  - 必須値取得時のバリデーション（settings オブジェクト）

- データ ETL / Data Platform
  - J-Quants API クライアント（株価・財務・カレンダー）
  - 差分 ETL・バックフィル・ページネーション対応
  - DuckDB への冪等保存（ON CONFLICT DO UPDATE）
  - データ品質チェック（欠損、スパイク、重複、日付不整合）
  - 市場カレンダー管理（営業日判定、next/prev_trading_day 等）
  - ニュース収集（RSS）と銘柄紐付け

- AI / NLP
  - ニュース単位の銘柄センチメント算出（news_nlp.score_news）
  - マクロニュース + ETF MA200 乖離を用いた市場レジーム判定（regime_detector.score_regime）

- 研究ユーティリティ
  - モメンタム、ボラティリティ、バリュー等のファクター計算
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー
  - z-score 正規化ユーティリティ

- 監査（トレーサビリティ）
  - signal_events / order_requests / executions を含む監査テーブルの初期化（init_audit_schema / init_audit_db）
  - UUID ベースの冪等キー設計

---

## セットアップ手順

前提
- Python 3.10 以上を推奨（型ヒントに | 型が多用されているため）
- DuckDB, OpenAI SDK, defusedxml などの依存が必要

例（venv を使用したセットアップ）:

```bash
# 仮想環境作成・有効化
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

# 必要パッケージのインストール（例）
pip install duckdb openai defusedxml
# その他、プロジェクトに合わせて追加依存がある場合は requirements.txt を使用
```

環境変数 / .env
- プロジェクトルート（.git または pyproject.toml を含むディレクトリ）に `.env` / `.env.local` を置くと自動で読み込まれます。
- テスト等で自動ロードを無効にする場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

主な環境変数（README 用の例）:

```
# J-Quants
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token

# kabu API
KABU_API_PASSWORD=your_kabu_password
KABU_API_BASE_URL=http://localhost:18080/kabusapi

# Slack (通知等)
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567

# DB パス
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db

# OpenAI
OPENAI_API_KEY=sk-...

# 実行環境
KABUSYS_ENV=development     # development | paper_trading | live
LOG_LEVEL=INFO
```

注意点:
- `config.Settings` は必須変数未設定時に ValueError を投げます（例: JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN など）。
- `.env.local` は `.env` よりも優先して上書きされる（OS 環境変数は保護される）。

---

## 使い方（主なユースケース）

以下は簡単な使用例です。実行前に必要な環境変数を設定してください。

1) DuckDB 接続を作成して日次 ETL を実行する

```python
from datetime import date
import duckdb
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

# settings.duckdb_path でデフォルト DB パスを参照可能
conn = duckdb.connect(str(settings.duckdb_path))

# 今日の ETL を実行（id_token を個別に渡す必要は通常なし）
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

2) ニュースのセンチメントスコアを計算して ai_scores に書き込む

```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
# 必要に応じて API キーを引数で渡す（None の場合は OPENAI_API_KEY 環境変数を使用）
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
print(f"書き込み銘柄数: {n_written}")
```

3) 市場レジーム（マクロ + MA200）を判定する

```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20))  # OpenAI API キーは環境変数から取得
```

4) 監査用 DB の初期化

```python
from kabusys.data.audit import init_audit_db

# :memory: も可、またはファイルパスを指定
audit_conn = init_audit_db("data/audit.duckdb")
# 監査テーブル(signal_events, order_requests, executions) が作成される
```

5) RSS ニュースの取得（単体テストやデバッグ用）

```python
from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES

url = DEFAULT_RSS_SOURCES["yahoo_finance"]
articles = fetch_rss(url=url, source="yahoo_finance")
for a in articles[:5]:
    print(a["id"], a["datetime"], a["title"])
```

6) 研究ユーティリティ（ファクター計算）

```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

conn = duckdb.connect(str(settings.duckdb_path))
momentum = calc_momentum(conn, target_date=date(2026, 3, 20))
value = calc_value(conn, target_date=date(2026, 3, 20))
vol = calc_volatility(conn, target_date=date(2026, 3, 20))
```

---

## ディレクトリ構成

リポジトリ内の主要ファイル / モジュール構成（src/kabusys 以下）:

- kabusys/
  - __init__.py
  - config.py                       — 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py                    — ニュース NLP / スコアリング
    - regime_detector.py             — マクロ + ETF MA200 による市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py              — J-Quants API クライアント（取得 / 保存）
    - pipeline.py                    — ETL パイプライン（run_daily_etl 等）
    - etl.py                         — ETL の公開インターフェース（ETLResult 再エクスポート）
    - news_collector.py              — RSS 収集 / 前処理
    - calendar_management.py         — 市場カレンダー管理（営業日判定など）
    - quality.py                     — データ品質チェック
    - stats.py                       — 統計ユーティリティ（zscore_normalize）
    - audit.py                       — 監査ログスキーマ初期化 / init_audit_db
  - research/
    - __init__.py
    - factor_research.py             — モメンタム / ボラティリティ / バリュー等
    - feature_exploration.py         — 将来リターン / IC / 統計サマリー
  - research/...                      — 研究用ユーティリティ群

各モジュールはドメインごとに分割されており、ETL・データ品質・AI スコアリング・監査ログ・研究にそれぞれ責務が割り当てられています。

---

## 運用 / 実行に関する注意点

- OpenAI API:
  - モデルは gpt-4o-mini を想定しています（response_format={"type":"json_object"} を使用）。API レスポンスのパースに失敗した場合はフェイルセーフ（多くの箇所で 0.0 にフォールバック）となる設計です。
  - API キーは環境変数 `OPENAI_API_KEY`、または各関数に `api_key` 引数で注入可能です。

- J-Quants:
  - リフレッシュトークンは `JQUANTS_REFRESH_TOKEN` に設定してください。get_id_token が自動で idToken を生成し、ページネーション時はキャッシュを共有します。
  - API レート制限を守るため内部で RateLimiter を使用していますが、大量ループでの呼び出しは注意してください。

- DuckDB / トランザクション:
  - ETL / 保存処理は多くの箇所で BEGIN / COMMIT / ROLLBACK を利用し冪等に設計されています。
  - DuckDB の executemany は空リストを受け付けないバージョン（例: 0.10 系）向けにガードが組まれています。

- セキュリティ:
  - ニュース収集は SSRF 対策・受信サイズ制限・defusedxml による XML 脆弱性対策を実装しています。
  - .env の取り扱いに注意し、機密情報は適切に管理してください。

---

## ライセンス / 貢献

この README はコードベースの概要と使い方を簡潔に示したもので、実運用する際はさらにドキュメント（例: API レート・リソース管理、運用手順、モニタリング・アラート設計）を整備してください。貢献・バグ報告はリポジトリの Issue / Pull Request を利用してください。

---

必要であれば、README に以下の追加情報を含めます：
- requirements.txt のサンプル（pip install 用）
- より詳しい .env.example（各環境変数の説明）
- CI / テスト実行方法
- よくあるトラブルシューティング（OpenAI レスポンスパース失敗、DuckDB バージョン問題 等）

どれを追加しますか？