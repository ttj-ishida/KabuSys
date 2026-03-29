# KabuSys

日本株向けの自動売買・データプラットフォーム用ライブラリ群です。  
データ取得（J-Quants）、ETL、データ品質チェック、ニュース収集、ニュース/NLP スコアリング（OpenAI）、
市場レジーム判定、研究用ファクター計算、監査ログ（発注→約定のトレーサビリティ）などを含みます。

バージョン: 0.1.0

---

## 概要

KabuSys は以下の目的を持つモジュール群で構成されています。

- J-Quants API からの株価 / 財務 / 市場カレンダー取得と DuckDB への永続化（差分取得・冪等保存）
- ETL パイプライン（run_daily_etl）で日次データ取得と品質チェックを自動化
- RSS からのニュース収集と銘柄紐付け
- OpenAI（gpt-4o-mini）を使ったニュースセンチメント / マクロセンチメント評価
- 市場レジーム判定（ETF + マクロセンチメントの合成）
- 研究用ファクター計算（モメンタム、バリュー、ボラティリティ等）と統計ユーティリティ
- 発注・約定の監査ログ用スキーマ初期化ユーティリティ（監査トレーサビリティ）

設計方針の要点:
- ルックアヘッドバイアスを避ける（内部で date.today() を無闇に参照しない等）
- 冪等性 / フェイルセーフ（API失敗は基本的に局所的に処理して継続）
- DuckDB を主要なローカルデータストアとして利用
- OpenAI 呼び出しはリトライやレスポンス検証を行う

---

## 主な機能一覧

- data/
  - jquants_client: J-Quants API クライアント（取得・保存関数、レート制御、トークンリフレッシュ）
  - pipeline: 日次 ETL（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - quality: データ品質チェック（欠損・スパイク・重複・日付不整合）
  - news_collector: RSS 取得・前処理・raw_news 保存
  - calendar_management: 営業日判定、next/prev_trading_day、calendar 更新ジョブ
  - audit: 監査ログ（signal_events / order_requests / executions）スキーマ初期化
  - stats: 汎用統計ユーティリティ（zscore_normalize）
- ai/
  - news_nlp.score_news: 銘柄ごとのニュースセンチメントを OpenAI で評価して ai_scores に保存
  - regime_detector.score_regime: ETF（1321）MA とマクロセンチメントを合成して market_regime に保存
- research/
  - factor_research: calc_momentum, calc_value, calc_volatility（ファクター計算）
  - feature_exploration: calc_forward_returns, calc_ic, factor_summary, rank

その他: config モジュールによる .env 自動読込 / 設定管理（.env, .env.local, OS 環境変数の優先順）  

---

## セットアップ手順

1. リポジトリをクローンし、仮想環境を作成・有効化

   ```
   git clone <repo-url>
   cd <repo>
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

2. 必要パッケージをインストール

   最低限必要な外部依存:
   - duckdb
   - openai
   - defusedxml

   例（pip）:

   ```
   pip install duckdb openai defusedxml
   ```

   （プロジェクトに setup.py/pyproject.toml があれば `pip install -e .` で開発インストールします）

3. 環境変数 (.env) の用意

   プロジェクトルート（.git や pyproject.toml があるディレクトリ）に `.env` / `.env.local` を配置すると自動で読み込まれます（自動読込を無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。

   必須っぽい環境変数（使用する機能に応じて）:

   - JQUANTS_REFRESH_TOKEN=...
   - KABU_API_PASSWORD=...
   - SLACK_BOT_TOKEN=...
   - SLACK_CHANNEL_ID=...
   - OPENAI_API_KEY=...
   - DUCKDB_PATH (例: data/kabusys.duckdb) — デフォルトは data/kabusys.duckdb
   - SQLITE_PATH (監視用) — デフォルトは data/monitoring.db
   - KABUSYS_ENV (development|paper_trading|live) — デフォルト development
   - LOG_LEVEL (DEBUG|INFO|...) — デフォルト INFO

   .env 形式の例:

   ```
   JQUANTS_REFRESH_TOKEN=xxxxx
   OPENAI_API_KEY=sk-xxxx
   SLACK_BOT_TOKEN=xoxb-xxxx
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=DEBUG
   ```

4. DuckDB 初期スキーマ（必要に応じて）  
   - 監査ログ専用 DB を初期化する例:

   ```python
   from kabusys.data.audit import init_audit_db
   conn = init_audit_db("data/audit.duckdb")
   ```

   - ETL 用のスキーマ初期化はプロジェクト内に別のスキーマ初期化関数があればそれを使ってください（このコードベースは audit の初期化ユーティリティを提供しています）。

---

## 使い方（簡単な例）

以下は代表的なユースケースの Python 例です。実行前に環境変数と DuckDB のパスなどを正しく設定してください。

- 日次 ETL 実行（株価・財務・カレンダー取得 + 品質チェック）

```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースのセンチメントスコア付与（OpenAI 必須）

```python
import duckdb
from datetime import date
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # 環境変数 OPENAI_API_KEY を使う
print(f"written {n_written} scores")
```

- 市場レジーム判定

```python
import duckdb
from datetime import date
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

- 研究用ファクター計算

```python
import duckdb
from datetime import date
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

conn = duckdb.connect("data/kabusys.duckdb")
mom = calc_momentum(conn, date(2026, 3, 20))
val = calc_value(conn, date(2026, 3, 20))
vol = calc_volatility(conn, date(2026, 3, 20))
```

- RSS フィード取得（news_collector.fetch_rss）

```python
from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES

articles = fetch_rss(DEFAULT_RSS_SOURCES["yahoo_finance"], source="yahoo_finance")
for a in articles[:5]:
    print(a["datetime"], a["title"])
```

- 監査ログ DB 初期化（order/exec スキーマ）

```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")  # テーブルとインデックスを作成
```

注意:
- OpenAI を利用する機能（news_nlp, regime_detector）は OPENAI_API_KEY または api_key 引数を必要とします。
- J-Quants への問い合わせを行う機能は JQUANTS_REFRESH_TOKEN を必要とします（jquants_client.get_id_token が使用）。

---

## 主要な設定項目 / 環境変数

config.Settings 経由で取得される代表的なキー:

- JQUANTS_REFRESH_TOKEN: J-Quants の refresh token（必須で使用機能あり）
- KABU_API_PASSWORD: kabuステーション API パスワード
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト http://localhost:18080/kabusapi）
- OPENAI_API_KEY: OpenAI API キー
- SLACK_BOT_TOKEN, SLACK_CHANNEL_ID: Slack 通知用
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: SQLite（監視用）パス（デフォルト data/monitoring.db）
- KABUSYS_ENV: development / paper_trading / live
- LOG_LEVEL: ログレベル

.env 自動読み込み:
- プロジェクトルート（.git または pyproject.toml の所在）を基準に `.env` / `.env.local` を読み込みます。
- 自動読込を無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## ディレクトリ構成（概要）

リポジトリの主要ファイル / モジュール:

- src/kabusys/
  - __init__.py
  - config.py                      — 環境設定 / .env 読込
  - ai/
    - __init__.py
    - news_nlp.py                   — ニュースセンチメント（OpenAI）
    - regime_detector.py            — 市場レジーム判定（ETF + マクロ）
  - data/
    - __init__.py
    - jquants_client.py             — J-Quants API クライアント（取得・保存）
    - pipeline.py                   — ETL パイプライン（run_daily_etl など）
    - etl.py                        — ETLResult 再エクスポート
    - news_collector.py             — RSS 取得・前処理・保存
    - calendar_management.py        — 市場カレンダー管理・営業日ロジック
    - quality.py                    — データ品質チェック
    - audit.py                      — 監査ログスキーマ初期化
    - stats.py                      — 統計ユーティリティ（zscore_normalize）
  - research/
    - __init__.py
    - factor_research.py            — モメンタム/バリュー/ボラティリティ計算
    - feature_exploration.py        — forward returns / IC / summary / rank
  - research/*（上記）
- その他: README.md（本ファイル）

各モジュールはドキュメント文字列で設計方針・前提・処理フローが詳述されています。必要に応じて該当モジュールの docstring を参照してください。

---

## 運用上の注意

- API キー・トークン類は秘匿して管理してください（.env を git に上げない）。
- OpenAI 呼び出しにはコスト・レート制限が発生します。batch サイズやリトライ設定を考慮して運用してください。
- J-Quants API のレート制限（120 req/min）はモジュール内で最小待機時間を設けていますが、実運用では更なる制御が必要な場合があります。
- DuckDB のスキーマ設計やインデックスは一部モジュール（audit 等）で定義されます。スキーマ初期化は注意して実行してください。
- テスト実行時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動 .env 読込を無効化できます。

---

## 貢献 / 開発

- コードは各モジュールの docstring に処理フロー・設計方針が記載されています。新規機能追加や修正はそれらに沿った実装を心がけてください。
- OpenAI / ネットワーク呼び出し部分はモック化しやすいように分離されています（テストは unittest.mock.patch 等を利用）。

---

必要であれば、使用する DB スキーマ（raw_prices, raw_financials, raw_news, news_symbols, ai_scores, prices_daily, market_regime など）の DDL も README に追加できます。どの情報をさらに詳しく載せたいか教えてください。