# KabuSys

日本株向けの自動売買 / データ基盤ライブラリ。  
ETL、ニュースNLP、研究用ファクター計算、監査ログ、JPXカレンダー管理、J-Quants クライアントなどを含むモジュール群で構成されています。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株のデータ収集・品質管理・特徴量計算・AI を用いたニュースセンチメント評価・市場レジーム判定・監査ログ管理を目的とした Python ライブラリ群です。  
主にバックオフィスの夜間バッチ処理・リサーチ環境・シグナル -> 発注の監査トレーサビリティに使うことを想定しています。

設計のポイント:
- DuckDB を用いたローカルデータベース中心の処理
- J-Quants API による差分ETL（レート制限・リトライ実装あり）
- OpenAI（gpt-4o-mini）を用いたニュース / マクロセンチメント評価（JSON Mode）
- ルックアヘッドバイアス対策（内部で date.today() を不用意に参照しない設計）
- フォールバックやフェイルセーフを重視（API失敗時は継続できる）

---

## 主な機能一覧

- データ取得・ETL
  - J-Quants API クライアント（株価日足、財務、上場銘柄、マーケットカレンダー）
  - 差分更新 / ページネーション / キャッシュされた id_token / レート制御
  - ETL パイプライン（run_daily_etl）と個別ジョブ（run_prices_etl / run_financials_etl / run_calendar_etl）
  - 品質チェック（欠損・スパイク・重複・日付整合性）

- ニュース処理
  - RSS 収集（fetch_rss）と前処理（URL 正規化・トラッキング除去）
  - ニュース -> 銘柄結びつけ（news_symbols を想定）
  - OpenAI による銘柄別ニュースセンチメント（score_news）

- 市場レジーム判定
  - ETF（1321）200 日 MA 乖離とマクロニュース（LLM）を合成して日次レジーム判定（score_regime）

- 研究（Research）
  - モメンタム / ボラティリティ / バリューなどのファクター計算
  - 将来リターン計算、IC（スピアマン）の算出、Z スコア正規化等

- 監査ログ（Audit）
  - signal_events / order_requests / executions 等の監査テーブル定義と初期化ユーティリティ
  - init_audit_db / init_audit_schema により DuckDB に監査スキーマを作成

- カレンダー管理
  - JPX マーケットカレンダーの取得・保存、営業日判定・前後営業日取得関数群

---

## 要件

- Python 3.10 以上（型アノテーションに `X | None` を使用）
- 必須パッケージ（例）
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants / OpenAI / RSS ソース）
- J-Quants / OpenAI の API キー（環境変数または引数で指定）

インストール例（仮）:
```
python -m venv .venv
source .venv/bin/activate
pip install -e .            # パッケージ化されている場合
pip install duckdb openai defusedxml
```

---

## 環境変数（主なもの）

KabuSys は環境変数またはプロジェクトルートの `.env` / `.env.local` から設定を自動読み込みします（自動読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。

必須:
- JQUANTS_REFRESH_TOKEN  — J-Quants リフレッシュトークン
- SLACK_BOT_TOKEN       — （通知等で使用する場合）Slack Bot Token
- SLACK_CHANNEL_ID      — Slack チャンネル ID
- KABU_API_PASSWORD     — kabuステーション API パスワード（発注系を使う場合）

任意/デフォルト:
- OPENAI_API_KEY        — OpenAI API キー（score_news / score_regime の api_key 引数で上書き可）
- KABUSYS_ENV           — development / paper_trading / live（デフォルト: development）
- LOG_LEVEL             — DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
- KABU_API_BASE_URL     — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH           — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH           — SQLite（監視用途など）のパス（デフォルト: data/monitoring.db）

.env 例（簡略）
```
JQUANTS_REFRESH_TOKEN=xxxxx
OPENAI_API_KEY=sk-xxxxxxxx
SLACK_BOT_TOKEN=xoxb-xxxx
SLACK_CHANNEL_ID=C01234567
KABU_API_PASSWORD=secret
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
```

---

## セットアップ手順（簡易）

1. リポジトリをクローンして仮想環境を作成
   ```
   git clone <repo-url>
   cd <repo>
   python -m venv .venv
   source .venv/bin/activate
   pip install -e .          # setup.py / pyproject がある場合
   pip install duckdb openai defusedxml
   ```

2. 環境変数を設定
   - プロジェクトルートに `.env` または `.env.local` を作成する（.gitignore で適切に除外）
   - 必須のキー（上記参照）を設定

3. ディレクトリ作成（デフォルトの保存先が存在しない場合）
   ```
   mkdir -p data
   ```

4. DuckDB スキーマの準備
   - ここに提示しているコードは監査スキーマ初期化機能（init_audit_db）を持ちますが、raw_prices / raw_financials / market_calendar 等のテーブル定義はプロジェクトの別スクリプトまたはマイグレーションで作成する想定です。
   - 監査ログだけを初期化するには次を使います（例）:

   ```python
   from kabusys.data.audit import init_audit_db
   conn = init_audit_db("data/audit.duckdb")
   ```

   - raw_prices 等のスキーマはプロジェクトのスキーマ作成スクリプトを利用してください（サンプルDDL は別途管理される想定）。

---

## 使い方（主要 API の例）

以下は Python REPL / スクリプト内での利用例です。すべての操作は DuckDB 接続を渡して行います。

- 日次 ETL（市場カレンダー・株価・財務・品質チェック）
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
# target_date を省略すると今日が使われます（内部で必要に応じて営業日に調整されます）
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメントスコア作成（score_news）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
# OPENAI_API_KEY は環境変数か、api_key 引数で指定
n_written = score_news(conn, target_date=date(2026, 3, 20))
print("scored codes:", n_written)
```

- 市場レジーム判定（score_regime）
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査 DB の初期化（監査スキーマ）
```python
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/audit.duckdb")
# conn は duckdb.DuckDBPyConnection
```

- JPX カレンダーの更新ジョブ（夜間バッチとして実行）
```python
from datetime import date
import duckdb
from kabusys.data.calendar_management import calendar_update_job

conn = duckdb.connect("data/kabusys.duckdb")
calendar_update_job(conn, lookahead_days=90)
```

- 研究用ファクター計算（例: モメンタム）
```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum

conn = duckdb.connect("data/kabusys.duckdb")
records = calc_momentum(conn, target_date=date(2026, 3, 20))
# records は [{"date": ..., "code": "...", "mom_1m": ..., ...}, ...]
```

---

## 注意点 / 運用上のヒント

- OpenAI 呼び出しは API 使用料が発生します。プロダクション運用時はレートやコストに注意してください。
- J-Quants API はレート制限があります（コード内で制御していますが、運用側でも監視してください）。
- ETL 実行前に対象 DuckDB に必要なテーブルスキーマが作成されていることを確認してください（raw_prices 等）。
- 自動環境変数読み込みはプロジェクトルート（.git または pyproject.toml の存在）から .env / .env.local を読みます。CI/テストで自動読み込みを無効にしたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- score_news / score_regime は外部 API に依存するため、テストではモックしやすいように内部呼び出しを差し替える設計になっています。

---

## ディレクトリ構成（抜粋）

（プロジェクトの src/kabusys 以下の主要ファイルを抜粋）

- src/kabusys/
  - __init__.py
  - config.py                       — 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py                    — ニュース NLU / OpenAI 呼び出し
    - regime_detector.py             — 市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py              — J-Quants API クライアント & 保存処理
    - pipeline.py                    — ETL パイプライン（run_daily_etl 等）
    - etl.py                         — ETL の公開型（ETLResult）
    - news_collector.py              — RSS 収集・前処理
    - calendar_management.py         — JPX カレンダー管理・営業日ロジック
    - quality.py                     — 品質チェック（欠損・スパイク等）
    - stats.py                       — 汎用統計ユーティリティ
    - audit.py                       — 監査ログスキーマ定義と初期化
  - research/
    - __init__.py
    - factor_research.py             — Momentum / Value / Volatility 等
    - feature_exploration.py         — forward returns, IC, summary, rank
  - ai, data, research 以下に補助モジュールが入っています

---

## 貢献 / 開発

- バグレポートや機能提案は Issue を作成してください。
- テストや CI の追加、スキーマ定義（raw_prices 等）の移動・整備は歓迎します。
- 外部 API 呼び出し箇所はモック可能な設計になっているため、ユニットテストの追加が容易です。

---

以上が README の概略です。README に追加してほしい具体的な手順（例: スキーマDDL、CI 実行方法、デプロイ手順など）があれば教えてください。必要に応じて .env.example のテンプレートやスキーマ作成 SQL 例も作成します。