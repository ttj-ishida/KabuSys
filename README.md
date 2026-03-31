# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ群です。  
ETL（J-Quants からのデータ取得）、データ品質チェック、ニュースの NLP スコアリング（OpenAI）、市場レジーム判定、研究用ファクター計算、監査ログなどを含みます。

---

## プロジェクト概要

KabuSys は以下の目的で設計されています。

- J-Quants API からの株価・財務・カレンダー等の差分 ETL を安定的に実行
- DuckDB を用いたローカルデータ格納と冪等保存
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- RSS ニュース収集 → OpenAI（gpt-4o-mini）を用いた銘柄固有のニュースセンチメント算出
- マクロニュース + ETF（1321）200日移動平均乖離を合成した市場レジーム判定
- 研究用途のファクター計算 / 将来リターン計算 / IC 計測
- 発注→約定まで追跡可能な監査ログスキーマ（DuckDB）

設計上の特徴：
- ルックアヘッドバイアスを避ける実装（datetime.now / today を直接参照しない箇所が多い）
- API 呼び出しに対するリトライ / バックオフ、レートリミット制御を実装
- フェイルセーフ方針：外部 API 失敗時は例外ではなくフォールバック（ゼロスコア等）で継続する箇所がある

---

## 主な機能一覧

- 環境変数 / .env 自動ロード（project root を探索）
- J-Quants クライアント（fetch / save / token refresh / pagination / rate limit）
- ETL パイプライン（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
- データ品質チェック（missing / spike / duplicates / date consistency）
- ニュース収集（RSS → raw_news 保存、SSRF/サイズ制限 等の防御機構）
- ニュース NLP（gpt-4o-mini を用いたバッチ解析、JSON mode 利用）
- 市場レジーム判定（ETF 1321 の MA200 乖離 + マクロニュースセンチメント）
- 研究モジュール（モメンタム、バリュー、ボラティリティ、forward returns、IC、Zscore）
- 監査ログ（signal_events / order_requests / executions の初期化・DB ヘルパー）
- DuckDB を前提とした冪等的保存ロジック

---

## セットアップ手順

前提：
- Python 3.10+（typing | match features を想定）
- ネットワークアクセス（J-Quants / OpenAI / RSS）

1. レポジトリをクローンし、パッケージをインストール（開発編集可能インストール例）:

   ```bash
   git clone <repo-url>
   cd <repo-root>
   python -m pip install -e ".[dev]"  # もし pyproject / extras が用意されていれば
   ```

   依存主要パッケージ（最低限）:
   - duckdb
   - openai
   - defusedxml

   明示的にインストールする場合:

   ```bash
   python -m pip install duckdb openai defusedxml
   ```

2. 環境変数 / .env の準備

   プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（パッケージ配布後も __file__ を基準に探索します）。自動読み込みを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   主要な環境変数（例）:
   - JQUANTS_REFRESH_TOKEN (必須) — J-Quants リフレッシュトークン
   - OPENAI_API_KEY — OpenAI API キー（score_news / regime で使用）
   - KABU_API_PASSWORD — kabuステーション API パスワード
   - KABU_API_BASE_URL — kabuステーションのベース URL（省略時ローカル）
   - SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
   - SLACK_CHANNEL_ID — Slack チャンネル ID
   - DUCKDB_PATH — デフォルトの DuckDB ファイルパス（例: data/kabusys.duckdb）
   - SQLITE_PATH — 監視等に使う SQLite パス（例: data/monitoring.db）
   - KABUSYS_ENV — environment（development / paper_trading / live）
   - LOG_LEVEL — ログレベル（DEBUG/INFO/...）

   例（.env）:
   ```
   JQUANTS_REFRESH_TOKEN=xxxxx
   OPENAI_API_KEY=sk-xxxx
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   ```

3. DuckDB データベース/監査 DB の初期化（任意）

   監査ログ用 DB を初期化する例:

   ```py
   from kabusys.data.audit import init_audit_db
   conn = init_audit_db("data/audit.duckdb")  # ":memory:" も可能
   ```

   ETL / データ用の DB は、run_daily_etl 等で接続を渡して使用します。スキーマ初期化はプロジェクトに付属する schema 初期化ユーティリティを利用してください（リポジトリにある schema モジュール等）。

---

## 使い方（簡単な例）

以下は Python REPL / スクリプトから主要 API を呼ぶ例です。

- 環境設定取得

```py
from kabusys.config import settings

print(settings.jquants_refresh_token)  # J-Quants のリフレッシュトークン（未設定時は例外）
print(settings.duckdb_path)            # Path オブジェクト
print(settings.is_dev)                 # environment 判定
```

- ETL を実行する（DuckDB 接続を渡す）

```py
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニューススコアリング（score_news）

```py
from kabusys.ai.news_nlp import score_news
from datetime import date

# API キーは環境変数 OPENAI_API_KEY を使うか、api_key 引数で渡す
n = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
print(f"scored {n} codes")
```

- 市場レジーム判定（score_regime）

```py
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

- 監査ログスキーマ初期化

```py
from kabusys.data.audit import init_audit_schema
init_audit_schema(conn, transactional=True)
```

- カレンダー・ユーティリティ例

```py
from kabusys.data.calendar_management import is_trading_day, next_trading_day
from datetime import date

d = date(2026, 3, 20)
print(is_trading_day(conn, d))
print(next_trading_day(conn, d))
```

- ニュース RSS フェッチ（低レベル）

```py
from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES

articles = fetch_rss(DEFAULT_RSS_SOURCES["yahoo_finance"], source="yahoo_finance")
for a in articles:
    print(a["id"], a["datetime"], a["title"])
```

注意点:
- score_news / score_regime は OpenAI API へ課金リスクがあります。テスト時はモック（unittest.mock.patch）で _call_openai_api 等を差し替えてください。
- ETL や保存は DuckDB のスキーマに依存します。事前にスキーマ作成（DDL）を行ってください。

---

## ディレクトリ構成

（主要ファイルのみ抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py                         — 環境変数 / .env ロード・設定アクセス
    - ai/
      - __init__.py
      - news_nlp.py                     — ニュース NLP（score_news）
      - regime_detector.py              — 市場レジーム判定（score_regime）
    - data/
      - __init__.py
      - jquants_client.py               — J-Quants API クライアント（fetch/save）
      - pipeline.py                     — ETL パイプライン（run_daily_etl 等）
      - etl.py                          — ETLResult 型の再エクスポート
      - news_collector.py               — RSS ニュース収集
      - calendar_management.py          — 市場カレンダー管理 / 営業日判定
      - quality.py                      — データ品質チェック
      - stats.py                        — 汎用統計（zscore_normalize）
      - audit.py                        — 監査ログスキーマ初期化 / init_audit_db
    - research/
      - __init__.py
      - factor_research.py              — モメンタム / バリュー / ボラティリティ等
      - feature_exploration.py          — forward returns / IC / summary / rank
    - (その他: strategy, execution, monitoring モジュールがエクスポート対象に含まれますが、
       本リストでは上記がメイン実装ファイルです)

---

## 注意事項 / 運用上のヒント

- 開発中は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動 .env ロードを無効にできます（ユニットテストで便利）。
- OpenAI 呼び出しはコスト・レイテンシに依存するため、本番ではバッチ処理（夜間）での実行やキャッシュを推奨します。
- J-Quants のレート制限（120 req/min）を守るため、jquants_client は内部で RateLimiter を実装しています。大量取得時は適切なバックオフ設定を利用してください。
- DuckDB への executemany に空リストを渡すと問題になるバージョンがあるため、ライブラリ側で空チェックが入っています。運用スクリプトでも注意してください。
- 監査ログ（audit）を用いることで、シグナル→発注→約定のトレーサビリティが確保できます。実際の発注処理と組み合わせる際は order_request_id を冪等キーとして利用してください。

---

必要であれば、README に以下を追加できます：
- インストール済みパッケージ一覧（requirements.txt 相当）
- 詳細なスキーマ定義 / 初期化手順
- CI / テスト実行手順（モック設定例）
- デプロイ / 本番運用チェックリスト

追加や修正したい箇所があれば教えてください。