# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ群です。  
ETL（J-Quants からのデータ取得）、ニュース収集・NLP（OpenAI 使用）、リサーチ（ファクター計算・特徴量解析）、監査ログ（約定トレーサビリティ）などを含みます。

この README ではプロジェクト概要、機能一覧、セットアップ手順、基本的な使い方、ディレクトリ構成を日本語でまとめます。

---

## プロジェクト概要

KabuSys は日本株の自動売買システムに必要なデータ基盤・研究・AI スコアリング・監査ログなどを提供する Python パッケージ群です。  
主な設計方針は以下の通りです：

- Look-ahead バイアス防止（内部で datetime.today() を不用意に参照しない等）
- DuckDB を用いた高速なローカルデータ保存とクエリ
- J-Quants API の差分取得と冪等保存（ON CONFLICT / DO UPDATE）
- OpenAI（gpt-4o-mini 等）を用いたニュースセンチメント評価（JSON モード）
- ETL、品質チェック、監査（監査テーブルの初期化・トレース）機能を提供

---

## 主な機能一覧

- data/
  - ETL（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - J-Quants API クライアント（トークン取得・レート制限・リトライ含む）
  - market calendar 管理（営業日判定、next/prev_trading_day など）
  - news_collector（RSS 収集、SSRF 対策、前処理）
  - quality（欠損・スパイク・重複・日付不整合チェック）
  - audit（監査テーブルの初期化・監査DB管理）
  - stats（zscore_normalize 等の統計ユーティリティ）
- ai/
  - news_nlp.score_news: ニュースを銘柄ごとにまとめ、OpenAI でセンチメントを評価して ai_scores に保存
  - regime_detector.score_regime: ETF（1321）200日MA 乖離とマクロニュース（LLM）を合成して市場レジームを判定し market_regime に保存
- research/
  - factor_research: momentum / value / volatility などファクター計算
  - feature_exploration: 将来リターン計算、IC 計算、統計サマリー
- config.py
  - 環境変数読み込み（.env/.env.local 自動読み込み、無効化フラグあり）、主要設定を提供

---

## 必要条件（依存パッケージ）

少なくとも以下が必要です（プロジェクトの packaging によるが、これらは本コードから推定されます）：

- Python 3.10+
- duckdb
- openai
- defusedxml

インストール例（必要に応じて仮想環境を作成してください）:

```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb openai defusedxml
# その他、プロジェクトに合わせた依存があれば requirements.txt を参照
```

---

## 環境変数 / 設定

config.Settings を通じて以下の環境変数が参照されます。`.env` / `.env.local` をプロジェクトルート（.git または pyproject.toml が検出される位置）に置くと自動で読み込まれます（自動読み込みを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定）。

主な環境変数:

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants リフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API パスワード
- KABU_API_BASE_URL (省略可) — デフォルト "http://localhost:18080/kabusapi"
- SLACK_BOT_TOKEN (必須) — Slack 通知用トークン
- SLACK_CHANNEL_ID (必須) — Slack チャネル ID
- OPENAI_API_KEY — OpenAI API キー（ai.score_news / regime_detector の引数 api_key を省略した場合に参照）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト "data/kabusys.duckdb"）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト "data/monitoring.db"）
- KABUSYS_ENV — "development" / "paper_trading" / "live"（default: development）
- LOG_LEVEL — "DEBUG" / "INFO" / "WARNING" / "ERROR" / "CRITICAL"（default: INFO）

config は `.env.example` を参考に `.env` を作成してください（config._require が未設定時に ValueError を投げます）。

---

## セットアップ手順（簡易）

1. リポジトリをクローン / コピー
2. 仮想環境を作成してアクティベート
3. 必要パッケージをインストール（上記参照）
4. プロジェクトルートに `.env` を作成して必須値を設定
5. DuckDB の初期化（監査DB 等が必要なら初期化関数を呼ぶ）

例:

```bash
git clone <repo-url>
cd <repo>
python -m venv .venv
source .venv/bin/activate
pip install duckdb openai defusedxml
# .env をプロジェクトルートに作成
```

---

## 使い方（代表的な例）

以下は Python からの基本的な呼び出し例です。各関数は DuckDB の接続オブジェクト（duckdb.connect() が返す接続）を受け取ります。

1) DuckDB に接続して日次 ETL を実行する

```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

2) ニュースセンチメント（ai_scores）を作成する

```python
from datetime import date
from kabusys.ai.news_nlp import score_news
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
# api_key を渡すか、環境変数 OPENAI_API_KEY を設定してください
count = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
print(f"scored {count} symbols")
```

3) 市場レジーム判定を実行する

```python
from datetime import date
from kabusys.ai.regime_detector import score_regime
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

4) 監査用 DuckDB を初期化する（監査テーブル作成）

```python
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/audit.duckdb")
# これで signal_events / order_requests / executions テーブルが作成されます
```

5) research（ファクター計算）の例

```python
from datetime import date
from kabusys.research.factor_research import calc_momentum
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
factors = calc_momentum(conn, target_date=date(2026,3,20))
# factors は各銘柄ごとの dict のリスト
```

注意点:
- OpenAI 呼び出しは JSON モードを期待しており、レスポンスのパースに失敗した場合はログ出力してフェイルセーフ（0.0 など）して進行します。
- J-Quants API 呼び出しは内部でレート制限・リトライ・401 リフレッシュなどを実施します。
- ETL 実行前に `.env` などで J-Quants のリフレッシュトークンを設定してください。

---

## 設定の自動ロードについて

`kabusys.config` はプロジェクトルート（.git または pyproject.toml を起点）を探索し、`.env` と `.env.local` を自動で読み込みます（OS 環境変数が優先）。自動ロードを無効化したい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト等で有用）。

---

## よく使う公開 API（抜粋）

- kabusys.data.pipeline.run_daily_etl(...) — 日次 ETL（calendar/prices/financials + 品質チェック）
- kabusys.data.jquants_client.fetch_daily_quotes(...) — J-Quants から株価を取得
- kabusys.data.jquants_client.save_daily_quotes(...) — DuckDB へ保存（冪等）
- kabusys.ai.news_nlp.score_news(conn, target_date, api_key) — ニュース NLP スコア作成
- kabusys.ai.regime_detector.score_regime(conn, target_date, api_key) — レジーム判定
- kabusys.data.audit.init_audit_db(path) — 監査 DB 初期化（DDL 実行）

---

## ディレクトリ構成

（src/kabusys 以下を抜粋）

- kabusys/
  - __init__.py (パッケージ定義、version)
  - config.py (環境変数・設定管理、自動 .env 読み込み)
  - ai/
    - __init__.py (score_news の公開)
    - news_nlp.py (ニュースの集約 / OpenAI を使ったセンチメント評価)
    - regime_detector.py (市場レジーム判定ロジック)
  - data/
    - __init__.py
    - calendar_management.py (市場カレンダー管理・営業日判定)
    - etl.py (ETLResult 再エクスポート)
    - pipeline.py (ETL パイプライン実装: run_daily_etl 等)
    - stats.py (zscore_normalize 等)
    - quality.py (データ品質チェック)
    - audit.py (監査テーブル DDL・初期化)
    - jquants_client.py (J-Quants API クライアント / 保存ロジック)
    - news_collector.py (RSS 収集・前処理・SSRF 対策)
  - research/
    - __init__.py (研究用関数の再エクスポート)
    - factor_research.py (モメンタム・ボラティリティ・バリュー等)
    - feature_exploration.py (将来リターン・IC・統計サマリー等)
  - monitoring, execution, strategy など（__all__ に含まれる／将来のモジュール）

---

## 運用上の注意点

- 本リポジトリのコードは実運用前にローカルで十分に検証してください（API レート制限、課金、実口座操作など）。
- OpenAI / J-Quants の API キーは厳重に管理してください（`.env` は Git 管理対象から外す）。
- ETL と AI 呼び出しは外部ネットワーク依存のため、リトライ・例外処理・ログ監視を必ず行ってください。
- DuckDB のスキーマやテーブルはプロジェクトの要件に応じて事前に作成しておく必要があります（init_audit_db は監査関連のみ作成します）。

---

必要に応じて README にサンプル .env.example、スキーマ作成 SQL、さらに詳しい使い方（cron / Airflow での ETL スケジュール、Slack通知、監査ログのクエリ例等）を追加できます。追加を希望する箇所を教えてください。