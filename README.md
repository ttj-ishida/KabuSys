# KabuSys

KabuSys は日本株のデータ取得・前処理・ファクター計算・ニュースNLP・市場レジーム判定・監査ログなどを含む日本株自動売買 / リサーチ基盤のライブラリ群です。DuckDB を主要なローカルデータストアとして利用し、J-Quants API / OpenAI（LLM） / kabuステーション 等と連携する設計になっています。

主な目的は「データプラットフォーム」「リサーチ（ファクター探索）」「AI を用いたニュース評価」「監査トレーサビリティ」を提供することで、戦略層や実行層が安全に・再現性を持って動作できるようにすることです。

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 簡単な使い方（コード例）
- 環境変数（.env）と自動ロード挙動
- ディレクトリ構成

---

## プロジェクト概要

- モジュール群は以下のサブパッケージに分かれています（主要なもの）:
  - kabusys.data: ETL、J-Quants クライアント、ニュース収集、データ品質チェック、カレンダー管理、監査ログ初期化 など
  - kabusys.research: ファクター計算、特徴量探索、統計ユーティリティ
  - kabusys.ai: ニュースNLP によるセンチメント付与、マクロニュースと価格に基づく市場レジーム判定
  - kabusys.config: 環境変数 / 設定管理
- 永続化は主に DuckDB（ファイル or in-memory）を想定。監視・軽量メタデータには SQLite なども想定されています。
- 外部 API:
  - J-Quants: 株価・財務・カレンダー等の取得
  - OpenAI: ニュースセンチメント / マクロセンチメント（gpt-4o-mini を利用する設計）
  - Slack（トークン・チャンネルIDは設定に含むが本コードベースでは Slack 連携の実装は設定参照に留まる）

---

## 機能一覧

- データ取得 / ETL
  - J-Quants からの株価日足、財務データ、上場情報、マーケットカレンダー取得（ページネーション・レート制御・自動トークンリフレッシュ）
  - 差分ロード、バックフィル、品質チェック（欠損/スパイク/重複/日付不整合）
  - 日次 ETL パイプライン（run_daily_etl）
- ニュース処理
  - RSS 収集（SSRF 対策、サイズリミット、トラッキングパラメータ除去）
  - OpenAI を用いた銘柄別ニュースセンチメント付与（score_news）
  - マクロ記事を用いた市場レジーム判定（score_regime）
- リサーチ / ファクター
  - モメンタム / ボラティリティ / バリュー系ファクター計算（calc_momentum, calc_volatility, calc_value）
  - 将来リターン計算、IC（情報係数）算出、ファクター統計サマリー
  - z-score 正規化ユーティリティ
- 監査ログ（トレーサビリティ）
  - signal_events, order_requests, executions を含む監査スキーマの初期化（init_audit_schema / init_audit_db）
  - 発注の冪等キー・ステータス遷移設計
- 設定管理
  - .env / .env.local 自動読み込み（プロジェクトルート検出）と必須環境変数チェック（kabusys.config.Settings）

---

## セットアップ手順

1. 必須ソフトウェア
   - Python 3.10+（typing の一部構文を使用）
   - DuckDB（Python パッケージ）
   - OpenAI Python SDK（v1 互換を想定）
   - defusedxml（RSS パース時の安全対策）

2. 推奨インストール（例）
   - 仮想環境を作成してアクティブ化
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
   - 必要パッケージをインストール（プロジェクトに requirements.txt がない場合、少なくとも次を入れてください）
     - pip install duckdb openai defusedxml

3. パッケージのインストール（パッケージ化されている場合）
   - pip install -e .

4. データディレクトリの準備
   - デフォルトでは DuckDB ファイルは data/kabusys.duckdb、監視用 SQLite は data/monitoring.db に置かれます（環境変数で変更可能）。

---

## 環境変数（.env）

kabusys.config.Settings により以下の環境変数が使用されます（必要なものは必須とコメント）:

- J-Quants / データ
  - JQUANTS_REFRESH_TOKEN (必須): J-Quants のリフレッシュトークン（get_id_token 用）
  - DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
  - SQLITE_PATH: SQLite ファイルパス（デフォルト data/monitoring.db）

- kabuステーション API
  - KABU_API_PASSWORD (必須): kabu API のパスワード
  - KABU_API_BASE_URL: kabu API ベース URL（デフォルト http://localhost:18080/kabusapi）

- OpenAI
  - OPENAI_API_KEY: OpenAI API キー（score_news, score_regime 等で利用）

- Slack
  - SLACK_BOT_TOKEN (必須): Slack ボットトークン
  - SLACK_CHANNEL_ID (必須): 送信対象チャンネル ID

- 実行環境 / ログ
  - KABUSYS_ENV: development | paper_trading | live（デフォルト development）
  - LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL（デフォルト INFO）

自動 .env 読み込み:
- プロジェクトルート（.git または pyproject.toml のあるディレクトリ）にある .env と .env.local を自動で読み込みます。
  - 読み込み順: OS 環境変数 > .env.local (override=True) > .env (override=False)
- 自動ロードを無効化する場合:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト用途等）。

例 (.env):
OPENAI_API_KEY=sk-...
JQUANTS_REFRESH_TOKEN=xxxxxxxx
KABU_API_PASSWORD=secret
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C12345678
DUCKDB_PATH=data/kabusys.duckdb
LOG_LEVEL=INFO
KABUSYS_ENV=development

---

## 使い方（コード例）

以下は代表的な操作の例です。実運用ではロガー設定・例外処理を適切に追加してください。

- DuckDB 接続を作成して日次 ETL を実行する例:

```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
# ETL を今日分で実行（必要な環境変数を設定済みであること）
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- ニュースセンチメントをスコアリングして ai_scores に保存する:

```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
# OPENAI_API_KEY を環境変数または api_key 引数で指定
n_written = score_news(conn, target_date=date(2026, 3, 20))
print("書き込み銘柄数:", n_written)
```

- マクロ＋価格を用いた市場レジームスコアを算出して market_regime に書き込む:

```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査用 DuckDB データベースの初期化:

```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit_kabusys.duckdb")
# conn を使って order_requests 等へ書き込み・クエリが可能
```

- リサーチ系ファクター計算例:

```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

conn = duckdb.connect("data/kabusys.duckdb")
target = date(2026, 3, 20)
mom = calc_momentum(conn, target)
val = calc_value(conn, target)
vol = calc_volatility(conn, target)
```

注意点:
- OpenAI API 呼び出しはネットワーク・課金が発生します。テスト時はモック（unittest.mock.patch）を使って _call_openai_api 関数を置き換えられる設計です。
- ETL 系は外部 API 呼び出しと DB 書込を行うため、実行前に必要な環境変数（JQUANTS_REFRESH_TOKEN 等）を正しく設定してください。

---

## ディレクトリ構成

（抜粋・主要ファイル）

- src/kabusys/
  - __init__.py
  - config.py  -- 環境変数 / 設定管理（.env 自動ロード・必須チェック）
  - ai/
    - __init__.py
    - news_nlp.py        -- ニュース NLP（score_news）
    - regime_detector.py -- マクロ + MA200 による市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - pipeline.py        -- ETL パイプライン（run_daily_etl 等）、ETLResult
    - jquants_client.py  -- J-Quants API クライアント（fetch/save 系）
    - news_collector.py  -- RSS 収集（SSRF 対策・XML パース）
    - quality.py         -- データ品質チェック
    - stats.py           -- 統計ユーティリティ（zscore_normalize）
    - calendar_management.py -- マーケットカレンダー管理（is_trading_day 等）
    - audit.py           -- 監査ログスキーマ初期化（init_audit_schema / init_audit_db）
    - etl.py             -- ETL の公開インターフェース（ETLResult エクスポート）
  - research/
    - __init__.py
    - factor_research.py -- momentum/value/volatility 計算
    - feature_exploration.py -- 将来リターン、IC、summary、rank
  - monitoring/ (案内: SQLite と併用する想定のコードがここにある可能性)
  - execution/, strategy/ など（パッケージ公開名には含まれるが実装は別途）

---

## 注意点 / 運用上のメモ

- Look-ahead bias 対策が随所に組み込まれています（target_date 以前のデータだけ参照する等）。
- OpenAI の呼び出しは retry/backoff とレスポンスバリデーションを行いますが、API キーの管理・コスト管理はユーザー側で行ってください。
- J-Quants API レート制御（120 req/min）に対応する RateLimiter を実装済みです。大量のページネーションを行うワークフローでもレートに配慮してください。
- .env の自動読み込みはプロジェクトルート検出に依存します（__file__ を基準に親ディレクトリを探索）。テストで自動ロードを止めたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を利用してください。
- DuckDB の executemany に空リストを渡すと困るケース（バージョン依存）があるため、コード内で空チェックを行っています。

---

必要であれば、セットアップ用の requirements.txt や具体的な運用コマンド（systemd / cron / Airflow の DAG 例）、CI/CD 用のテスト例、または API の追加ドキュメント（各関数の引数詳細や戻り値の例）を追記します。どの情報が必要か教えてください。