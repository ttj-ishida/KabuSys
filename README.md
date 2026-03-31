# KabuSys

日本株向けのデータプラットフォームと研究・自動売買支援ライブラリです。  
DuckDB を中心にデータを蓄積・品質チェック・ETL を行い、ニュース NLP / LLM ベースの銘柄スコアリング、マーケットレジーム判定、研究用ファクター計算、監査ログ（発注〜約定トレーサビリティ）などを提供します。

主な設計方針としては「バックテストでのルックアヘッドバイアス防止」「ETL の冪等性」「外部 API 呼び出しの堅牢なリトライ/レート制御」を重視しています。

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方（コード例）
- 環境変数（.env 例）
- ディレクトリ構成

---

## プロジェクト概要

KabuSys は日本株向けに次を提供する Python モジュール群です。

- J-Quants からの株価・財務・カレンダー ETL と保存（DuckDB）
- RSS ニュース収集と前処理（SSRF対策・トラッキング除去）
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント判定（銘柄別・マクロ）
- ETF（1321）200日移動平均乖離とマクロセンチメントを合成する市場レジーム判定
- 研究用ファクター計算（モメンタム・バリュー・ボラティリティ等）と特徴量解析ユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（signal -> order_request -> execution）テーブル定義と初期化ユーティリティ
- 環境設定の自動読み込み（プロジェクトルートの .env / .env.local）

設計上、内部処理はバックテストでのルックアヘッドを避けるように日付指定ベースで動作します。

---

## 機能一覧

- data
  - jquants_client: J-Quants API クライアント（レートリミット・リトライ・トークンリフレッシュ）
  - pipeline / etl: 日次 ETL （prices, financials, calendar）と ETL 結果オブジェクト（ETLResult）
  - news_collector: RSS 収集・前処理・記事ID生成（SSRF / Gzip / XML 対策あり）
  - quality: データ品質チェック（欠損・スパイク・重複・日付不整合）
  - calendar_management: 市場カレンダー管理と営業日ユーティリティ
  - audit: 監査ログスキーマ生成・初期化（DuckDB）
  - stats: z-score 正規化などの汎用統計ユーティリティ
- ai
  - news_nlp.score_news: 銘柄別ニュースセンチメントを OpenAI で評価し ai_scores に保存
  - regime_detector.score_regime: ETF の MA200 乖離とマクロニュース LLM を合成して market_regime に記録
- research
  - factor_research: モメンタム・ボラティリティ・バリュー等のファクター計算
  - feature_exploration: 将来リターン計算、IC（Information Coefficient）、統計サマリー、ランク付け
- config: 環境変数読み込み・Settings オブジェクト（自動 .env ロード、必須キーチェック）

---

## セットアップ手順

1. Python 環境（推奨: 3.10+）を用意します。
2. 仮想環境を作成・有効化します（任意）。
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要なパッケージをインストールします（例）:

   pip install duckdb openai defusedxml

   ※ プロジェクトの requirements.txt は含まれていないため、用途に合わせて追加してください（例: requests, slack-sdk など）。

4. プロジェクトルートに .env（または .env.local）ファイルを作成します。config モジュールはプロジェクトルート（.git または pyproject.toml の存在）を基に自動で .env を読み込みます。テスト等で自動読み込みを無効にする場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

5. DuckDB データベースの保存先（デフォルト: data/kabusys.duckdb）や監視用 SQLite（デフォルト: data/monitoring.db）は Settings から取得できます。ディレクトリが存在しない場合は作成してください。

---

## 環境変数（.env 例）

以下は主要な必須/推奨環境変数の例 (.env):

JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=your_openai_api_key
KABU_API_PASSWORD=your_kabu_station_password
SLACK_BOT_TOKEN=xoxb-your-slack-bot-token
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
KABUSYS_ENV=development
LOG_LEVEL=INFO

Notes:
- .env.local は .env を上書き（優先）します。
- 自動ロードを無効にしたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。
- KABUSYS_ENV の有効値: development / paper_trading / live
- LOG_LEVEL は DEBUG/INFO/WARNING/ERROR/CRITICAL のいずれか

---

## 使い方（簡単なコード例）

以下は主要なユースケースの簡単なコード例です。いずれも Python スクリプト / REPL で実行できます。

- 設定取得

```python
from kabusys.config import settings

print(settings.duckdb_path)
print(settings.is_live)
```

- DuckDB 接続を作って日次 ETL を実行（run_daily_etl）

```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- ニューススコアリング（score_news）を実行して ai_scores に保存

```python
import duckdb
from datetime import date
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect(str(settings.duckdb_path))
written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # env の OPENAI_API_KEY を使用
print(f"書き込み銘柄数: {written}")
```

- マーケットレジーム判定（score_regime）

```python
from kabusys.ai.regime_detector import score_regime
import duckdb
from datetime import date

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

- 監査ログ用 DuckDB を初期化（監査スキーマ作成）

```python
from kabusys.data.audit import init_audit_db

# ファイル DB を作る場合
conn = init_audit_db("data/audit.duckdb")

# :memory: でメモリ DB
# conn = init_audit_db(":memory:")
```

- 研究用ファクター計算（例: モメンタム）

```python
from kabusys.research.factor_research import calc_momentum
from datetime import date
import duckdb

conn = duckdb.connect(str(settings.duckdb_path))
records = calc_momentum(conn, target_date=date(2026, 3, 20))
print(len(records))
```

注意点:
- OpenAI を使用する関数（score_news, score_regime）は OPENAI_API_KEY を参照します。引数 api_key に文字列を渡すことも可能です。
- J-Quants の API は JQUANTS_REFRESH_TOKEN を設定しておく必要があります（get_id_token 内で使用）。
- ETL / API 呼び出しは外部ネットワークに依存するため、実行時のネットワーク・API レート制限に注意してください。

---

## 主要 API の説明（抜粋）

- kabusys.config.settings
  - settings.jquants_refresh_token / settings.duckdb_path / settings.env / settings.log_level などをプロパティとして取得できます。必須キーが未設定の場合は ValueError を発生させます。

- kabusys.data.pipeline.run_daily_etl(conn, target_date, ...)
  - 日次 ETL を実行し ETLResult を返します。個別ジョブ（run_prices_etl, run_financials_etl, run_calendar_etl）も単独で実行可能。

- kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)
  - 指定ウィンドウのニュースを銘柄ごとに集約して LLM に送信、ai_scores テーブルへ書き込みます。返り値は書き込んだ銘柄数。

- kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - 1321 の MA200 乖離とマクロニュースの LLM センチメントを合成して market_regime テーブルへ保存します。

- kabusys.data.audit.init_audit_db(db_path)
  - 監査用 DB を作成しスキーマを初期化します。

---

## ディレクトリ構成

リポジトリの主要なファイル・モジュール構成（src/kabusys 以下）:

- kabusys/
  - __init__.py
  - config.py                      — 環境変数読み込み / Settings
  - ai/
    - __init__.py
    - news_nlp.py                   — 銘柄別ニューススコアリング（OpenAI）
    - regime_detector.py            — 市場レジーム判定（ETF + マクロLLM）
  - data/
    - __init__.py
    - jquants_client.py             — J-Quants API クライアント（fetch/save）
    - pipeline.py                   — ETL パイプライン（run_daily_etl 等）
    - etl.py                        — ETLResult の公開
    - news_collector.py             — RSS フィード収集・前処理
    - calendar_management.py        — 市場カレンダー / 営業日ユーティリティ
    - quality.py                    — データ品質チェック
    - stats.py                      — 統計ユーティリティ（zscore_normalize）
    - audit.py                      — 監査ログスキーマ定義 / 初期化
  - research/
    - __init__.py
    - factor_research.py            — モメンタム/バリュー/ボラティリティ等
    - feature_exploration.py        — 将来リターン / IC / summary / rank
  - research/...                     — ファクター研究用ユーティリティ群

各モジュールはドキュメント文字列（docstring）と詳細なロジック注釈が付与されています。実運用では DuckDB のテーブルスキーマが必要（raw_prices / raw_financials / market_calendar / ai_scores / market_regime / audit テーブル等）。ETL とスキーマ初期化ロジックはプロジェクトの別箇所で管理してください（このコードベースは主に処理ロジックを提供します）。

---

## 補足・留意点

- 本ライブラリは外部 API（J-Quants, OpenAI）やネットワークリソースに依存します。API キーやトークンの取り扱いには注意してください。
- 設計上、バックテスト等でのルックアヘッドを防ぐため「target_date を明示的に渡す」スタイルを採っています。内部で datetime.today() を意図的に参照しない関数が多くあります。バックテスト時は取得済みの過去データを事前に DB に保存してから利用してください。
- news_collector は SSRF 対策・レスポンスサイズ制限・XML パース安全化（defusedxml）などを実装しています。外部 RSS を収集する際も運用ポリシーに従ってください。

---

必要に応じて README を拡張します。特に「テーブルスキーマ」「具体的な初期化手順（DDL）」「CI / デプロイ手順」など追記をご希望であれば教えてください。