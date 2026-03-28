# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ群です。  
ETL、ニュースセンチメント（LLM）、市場レジーム判定、ファクター計算、データ品質チェック、監査ログなど、取引システムで必要となる基盤機能を含みます。

---

## プロジェクト概要

KabuSys は以下を目的としたモジュール群です。

- J-Quants API を使った株価・財務・カレンダーの差分 ETL と DuckDB への保存
- RSS 処理によるニュース収集とニュースセンチメント（OpenAI）による銘柄別スコア付与
- マクロニュースと ETF（1321）の MA200 乖離を合成した市場レジーム判定
- 研究用（ファクター計算・将来リターン・IC 等）のユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付整合性）
- 監査ログ（signal → order_request → execution）用の DuckDB スキーマと初期化ユーティリティ
- 設定は環境変数（.env/.env.local）で管理、パッケージ起動時に自動読み込み

設計上、ルックアヘッドバイアスを避けるために `date` / `target_date` を明示して処理を行い、外部 API 呼び出しはリトライ・フォールバックを備えています。

---

## 主な機能一覧

- データ取得・保存
  - J-Quants からの株価（daily_quotes）、財務（statements）、上場情報、マーケットカレンダー取得・DuckDB 保存（冪等）
  - ETL パイプライン（差分取得・バックフィル・品質チェック）
- ニュース関連
  - RSS フィード収集（SSRF 対策・トラッキング除去）
  - OpenAI を使ったニュースの銘柄別センチメント付与（バッチ・JSON Mode）
- AI / レジーム判定
  - 銘柄ニュースに基づく ai_score 書込み（ai_scores テーブル）
  - ETF（1321）MA200 乖離 + マクロニュースセンチメントで市場レジーム（bull/neutral/bear）を判定・書込み
- 研究用ユーティリティ
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - 将来リターン計算、IC（Spearman）、統計要約、Zスコア正規化
- データ品質チェック
  - 欠損、スパイク、重複、日付不整合の検出（QualityIssue オブジェクト）
- 監査ログ
  - signal_events / order_requests / executions 等のテーブル定義と初期化関数

---

## 必須 / 推奨要件

- Python 3.10+
  - （PEP 604 の型記法（`X | None`）を使用しているため）
- 主要依存ライブラリ（例）
  - duckdb
  - openai
  - defusedxml
  - （標準ライブラリのみで実装されている部分も多いですが、上記は主要機能で必要です）

インストール例（プロジェクトを pip 編集可能インストールする場合）:

```bash
python -m pip install -e .[all]   # setup extras があれば
# または個別に
python -m pip install duckdb openai defusedxml
```

※ packaging の仕組みは本リポジトリ外のため、requirements ファイルがあればそれを使ってください。

---

## 環境変数（.env）

config モジュールはプロジェクトルート（.git または pyproject.toml を探索）を基準に `.env` および `.env.local` を自動読み込みします。優先順位:

OS 環境 > .env.local > .env

自動読み込みを無効にする場合:
KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト用途など）。

主な環境変数:

- JQUANTS_REFRESH_TOKEN (必須)  
  J-Quants のリフレッシュトークン（get_id_token に使用）
- OPENAI_API_KEY (必須 for AI 関連)  
  OpenAI API キー（ai モジュールを直接呼ぶ場合）
- KABU_API_PASSWORD (必須)  
  kabuステーション API のパスワード（使用する場合）
- KABU_API_BASE_URL (任意, default: http://localhost:18080/kabusapi)  
- SLACK_BOT_TOKEN (必須 if Slack notifications used)
- SLACK_CHANNEL_ID (必須 if Slack notifications used)
- DUCKDB_PATH (任意, default: data/kabusys.duckdb)  
- SQLITE_PATH (任意, default: data/monitoring.db)  
- KABUSYS_ENV (任意, default: development) 値: development / paper_trading / live
- LOG_LEVEL (任意, default: INFO)

例 `.env`（最低限の例）:

```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
OPENAI_API_KEY=sk-...
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=CXXXXXXX
KABU_API_PASSWORD=your_kabu_password
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=DEBUG
```

---

## セットアップ手順（ローカル）

1. リポジトリをクローン
2. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate (Windows: .venv\Scripts\activate)
3. 依存ライブラリをインストール
   - pip install duckdb openai defusedxml
4. 必要な環境変数を .env または OS 環境に設定（上記参照）
5. データディレクトリ作成（必要であれば）
   - mkdir -p data
6. DuckDB ファイルは自動生成されます（初回 ETL 実行時など）

---

## 使い方（主要 API の例）

以下は Python REPL やスクリプトから呼び出す例です。すべての関数は `duckdb.connect()` で得られる接続オブジェクトを受け取ります。

注意: AI 関連関数を使うには OpenAI API キー（環境変数または api_key 引数）が必要です。

- ETL を日次で実行する（pipeline.run_daily_etl）:

```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメントをスコアリングして ai_scores に書き込む:

```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
num_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # api_key None: OPENAI_API_KEY を参照
print(f"written {num_written} scores")
```

- 市場レジームを判定して market_regime に書き込む:

```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ用の DuckDB を初期化する:

```python
from kabusys.data.audit import init_audit_db
conn_audit = init_audit_db("data/audit.duckdb")  # 親ディレクトリは自動作成されます
```

- 研究用ファクター計算の呼び出し例:

```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum

conn = duckdb.connect("data/kabusys.duckdb")
recs = calc_momentum(conn, target_date=date(2026,3,20))
# recs は [{"date":..., "code":"XXXX", "mom_1m":..., ...}, ...]
```

---

## 実装上のポイント / 注意事項

- ルックアヘッドバイアス対策:
  - 日時の算出に `date.today()` を暗黙に参照せず、呼び出し側が `target_date` を明示して使う設計です。
  - prices_daily などのクエリは `date < target_date`（排他）や `date = ?` などで将来データを参照しないよう注意しています。
- OpenAI 呼び出し:
  - gpt-4o-mini を前提とした JSON モードで呼び出します。API の失敗はフェイルセーフ（スコア 0 など）として扱うことが多いです。
- .env 自動読み込み:
  - パッケージ import 時に `.env`/.env.local を読み込みます（プロジェクトルートを .git または pyproject.toml で探索）。
  - テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で抑制できます。
- DuckDB の executemany と空リスト:
  - DuckDB のバージョン依存で executemany に空リストを渡すと失敗するケースがあるため、空チェックを実装しています。
- RSS 収集:
  - SSRF 対策（リダイレクト検査・ホストプライベート判定）や XML 攻撃対策（defusedxml）を実装しています。
- J-Quants API:
  - レートリミット（120 req/min）を守るため固定間隔スロットリングを実装しています。401 は自動リフレッシュし 1 回リトライします。

---

## ディレクトリ構成

以下は主なファイル・モジュールの概要（src/kabusys 配下）:

- __init__.py
  - パッケージ定義、version

- config.py
  - 環境変数 / .env 自動読み込み、Settings クラス

- ai/
  - news_nlp.py: ニュースを銘柄別にまとめて OpenAI へ送り ai_scores に書込む
  - regime_detector.py: ETF (1321) の MA200 乖離 + マクロニュースで市場レジーム判定
  - __init__.py: score_news を公開

- data/
  - pipeline.py: ETL のエントリポイント（run_daily_etl 他）
  - jquants_client.py: J-Quants API 呼び出し & DuckDB への保存ロジック
  - news_collector.py: RSS フィード取得・前処理・raw_news 保存ロジック
  - calendar_management.py: 市場カレンダー管理・営業日判定・calendar_update_job
  - quality.py: データ品質チェック（QualityIssue）
  - stats.py: 共通統計ユーティリティ（zscore_normalize）
  - audit.py: 監査ログテーブル定義と初期化ユーティリティ
  - etl.py: ETLResult の再エクスポート
  - __init__.py

- research/
  - factor_research.py: 各種ファクター計算（momentum/value/volatility）
  - feature_exploration.py: 将来リターン, IC, summarization, rank
  - __init__.py

上記の他に strategy / execution / monitoring に関するサブパッケージ（__all__ に宣言済）を想定できます（現コードベースの一部機能が中心で、それらは将来的に追加される想定）。

---

## 開発 / 貢献

- コードは型注釈・ドキュメントストリングを含み、ユニットテストでの差し替え（mock）を想定した設計になっています。
- テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を利用し、環境依存を切り離してください。
- 外部 API の呼び出しはそれぞれモジュール単位でラップしてあるため、ネットワーク呼び出しをモックしてテストできます。

---

## ライセンス / 免責

本 README はコードベースの要約です。実際の運用（特に実口座での自動売買）を行う場合は、責任あるリスク管理・法令順守・バックテスト・十分な監査を行ってください。商用利用や外部 API 利用にはそれぞれのプロバイダの利用規約を確認してください。

---

README に含めてほしい追加の情報（例: 実行スクリプト、CI 設定、requirements.txt の具体的中身等）があれば教えてください。必要に応じてサンプル .env.example や CLI 例も作成します。