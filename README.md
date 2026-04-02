# KabuSys

日本株向けのデータプラットフォーム兼自動売買支援ライブラリです。DuckDB をデータレイクに用い、J-Quants API から市場データを取得して ETL → 品質チェック → 研究（ファクター計算）→ シグナル／監査ログ（発注トレース）→ 実行／監視のワークフローをサポートします。LLM（OpenAI）を使ったニュースセンチメント評価や市場レジーム判定機能も含みます。

主な対象
- データ収集 / ETL（株価・財務・市場カレンダー）
- データ品質チェック
- ニュース収集・NLP による銘柄センチメント評価
- 市場レジーム判定（ETF MA + マクロニュース）
- ファクター計算・特徴量探索（研究用途）
- 監査ログ（signal → order_request → execution のトレーサビリティ）

---

## 機能一覧

- data
  - ETL パイプライン（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - J-Quants API クライアント（認証・ページネーション・保存用ユーティリティ）
  - 市場カレンダー管理（営業日判定・next/prev/get_trading_days）
  - ニュース収集（RSS → raw_news、SSRF 対策・URL 正規化）
  - データ品質チェック（欠損・スパイク・重複・日付整合性）
  - 監査ログスキーマ初期化（init_audit_schema / init_audit_db）
  - 汎用統計ユーティリティ（zscore 正規化）

- ai
  - ニュースセンチメント分析（news_nlp.score_news）
  - 市場レジーム判定（regime_detector.score_regime）
  - OpenAI（gpt-4o-mini）を JSON-mode で呼び出す仕組み（リトライ・フォールバックあり）

- research
  - ファクター計算（momentum / value / volatility）
  - 将来リターン計算、IC（Spearman）計算、統計サマリー、ランク処理

- config
  - 環境変数読み込み（.env / .env.local の自動ロード。プロジェクトルート検出）
  - settings オブジェクト経由で設定値を安全に取得

---

## 要求環境（目安）

- Python 3.10+
- 必要なパッケージ（例）
  - duckdb
  - openai
  - defusedxml
- 標準ライブラリ（urllib, datetime, json, logging 等）

（実プロジェクトでは requirements.txt / pyproject.toml を用意して pipenv/poetry/venv を使ってインストールしてください）

---

## 環境変数

主要な環境変数（必須は明記）:

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン（ETL 用）
- OPENAI_API_KEY (必須 for AI 呼び出し) — OpenAI API キー（news_nlp / regime_detector）
- KABU_API_PASSWORD (必須) — kabuステーション API パスワード（実行/注文用）
- SLACK_BOT_TOKEN (必須) — 通知用 Slack Bot トークン
- SLACK_CHANNEL_ID (必須) — Slack チャネル ID
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視 DB パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 環境 ("development" | "paper_trading" | "live")（デフォルト: development）
- LOG_LEVEL — "DEBUG"|"INFO"|...（デフォルト: INFO）

自動 .env ロード:
- パッケージはプロジェクトルート（.git または pyproject.toml があるディレクトリ）を検出し、
  .env → .env.local の順で自動的に環境変数を読み込みます。自動ロードを無効化するには:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト用途など）。

---

## セットアップ手順（例）

1. リポジトリをクローン / ソースを用意する。
2. Python 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows は .venv\Scripts\activate)
3. 必要パッケージをインストール（例）
   - pip install duckdb openai defusedxml
   - （他に logging や標準ライブラリのみで実装されていますが、実運用で追加パッケージがある場合は pyproject.toml を参照してください）
4. .env を作成
   - プロジェクトルートに .env を作成し、上記の必須環境変数を設定してください。
   - 例:
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     OPENAI_API_KEY=sk-...
     KABU_API_PASSWORD=your_kabu_password
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     DUCKDB_PATH=data/kabusys.duckdb

5. データベースディレクトリを作成（必要に応じて）
   - mkdir -p data

---

## 使い方（簡易サンプル）

コードはライブラリとしてインポートして使用できます。以下は主要 API の例です。

- ETL を実行（日次 ETL）
```python
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=None)  # target_date を指定するとその日を対象に実行
print(result.to_dict())
```

- ニュースセンチメントをスコア付け（ai.news_nlp）
```python
from kabusys.ai.news_nlp import score_news
import duckdb
from datetime import date

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026, 3, 20))  # 書き込んだ銘柄数が返る
```

- 市場レジーム判定（ai.regime_detector）
```python
from kabusys.ai.regime_detector import score_regime
import duckdb
from datetime import date

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログスキーマ初期化
```python
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/audit.duckdb")  # :memory: も可
# 以後 conn を用いて監査テーブルへ書き込み／クエリ可能
```

- 研究用ファクター計算
```python
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
import duckdb
from datetime import date

conn = duckdb.connect("data/kabusys.duckdb")
momentums = calc_momentum(conn, target_date=date(2026,3,20))
```

注意点
- AI 呼び出しは OpenAI API キー（OPENAI_API_KEY）を必要とします。API のリトライ・フォールバックロジックがありますが、料金やレート制限に注意してください。
- DuckDB に対する書き込みは多くの関数が冪等（INSERT ... ON CONFLICT DO UPDATE）を想定して実装されています。

---

## .env の自動ロードと無効化

パッケージは実行時にプロジェクトルートを探索し、`.env` → `.env.local` の順で環境変数を読み込みます（既存の OS 環境変数は保護されます）。自動ロードを無効化したい場合は環境変数を設定してください:

- KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

## ディレクトリ構成（抜粋）

src/kabusys
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
- research/
  - __init__.py
  - factor_research.py
  - feature_exploration.py

主要モジュールの役割
- config.py: 環境変数管理と settings オブジェクト
- data/jquants_client.py: J-Quants API 取得・保存ロジック
- data/pipeline.py: 日次 ETL の Orchestrator（run_daily_etl）
- data/quality.py: データ品質チェック
- data/news_collector.py: RSS 収集・前処理
- ai/news_nlp.py: ニュースを銘柄別にまとめて LLM で評価し ai_scores へ保存
- ai/regime_detector.py: ETF MA とマクロニュースで市場レジームを判定
- research/*: ファクター計算 / 特徴量評価

---

## 開発メモ / テストについて

- OpenAI 呼び出し等は内部でラッパー関数を用いているため、ユニットテストでは該当関数を monkeypatch / unittest.mock.patch して差し替え可能です（例: kabusys.ai.news_nlp._call_openai_api）。
- .env の自動ロードはプロジェクトルート検出に依存するため、テスト実行時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定することを推奨します。
- DuckDB のバージョンや executemany の挙動に依存する箇所があるため（コード内コメント参照）、CI 上の DuckDB バージョンを固定すると再現性が高まります。

---

## 最後に

この README はコードベースの主要な使い方とアーキテクチャを概説しています。実運用では環境変数の管理、API キーの保護、OpenAI / J-Quants のレート制限や課金に十分ご注意ください。詳細な API 仕様やインストール要件はプロジェクトの pyproject.toml / requirements.txt / docs を参照して補完してください。