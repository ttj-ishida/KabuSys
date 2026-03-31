# KabuSys

日本株向けのデータプラットフォーム & 自動売買ユーティリティ群です。  
DuckDB をデータ層に用い、J-Quants / JQ API からのデータ取得、ニュース収集・NLP（OpenAI）、リサーチ用ファクター計算、ETL パイプライン、監査ログ（オーダー追跡）などを含みます。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下の主要機能を提供します。

- J-Quants（株価・財務・上場情報・マーケットカレンダー）からの差分 ETL と保存機能
- RSS ベースのニュース収集と記事の前処理（SSRF 対策・トラッキング除去）
- OpenAI を用いたニュースセンチメント（ai_score）算出（バッチ処理・JSON Mode）
- 市場レジーム判定（ETF 1321 の MA200 とマクロニュースの合成）
- リサーチ用ファクター計算（モメンタム、ボラティリティ、バリュー等）と特徴量解析ユーティリティ
- データ品質チェック（欠損、重複、スパイク、日付不整合）
- 監査ログ（signal → order_request → executions）のテーブル定義と初期化ユーティリティ
- 環境変数管理（.env 自動読み込み機能を備えた設定ラッパー）

設計上のポイント:
- ルックアヘッドバイアスを避ける（datetime.now()/today() に依存しない設計、ETL／判定は target_date を引数で受け取る）
- DuckDB を中心とした SQL ベース処理で高速・効率的に集計
- 外部 API 呼び出しに対するリトライ・バックオフ・フェイルセーフ処理を備える
- 冪等性を意識した保存（ON CONFLICT / upsert）を多用

---

## 主な機能一覧

- data/
  - jquants_client: J-Quants API クライアント、取得・保存関数（raw_prices, raw_financials, market_calendar など）
  - pipeline: 日次 ETL（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - news_collector: RSS 取得・正規化・raw_news への保存
  - quality: データ品質チェック（欠損、スパイク、重複、日付不整合）
  - calendar_management: 営業日判定・次営業日/前営業日の取得・calendar 更新ジョブ
  - audit: 監査ログ（signal_events, order_requests, executions）と初期化ユーティリティ
  - stats: zscore_normalize 等の統計ユーティリティ
- ai/
  - news_nlp.score_news: 複数銘柄に対するニュースセンチメントのバッチ取得と ai_scores への書き込み
  - regime_detector.score_regime: ETF 1321 の MA200 とマクロニュースを合成して market_regime を算出
- research/
  - factor_research: calc_momentum, calc_volatility, calc_value（ファクター計算）
  - feature_exploration: 将来リターン算出、IC（Spearman）計算、統計サマリ等
- config: .env 自動読み込みロジックと Settings（環境変数ラッパー）
- monitoring / execution / strategy 等（パッケージ公開に含める想定：README内では主要モジュールを上記に記載）

---

## 必要条件 / 依存関係

- Python 3.10+
- パッケージ（例）
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants API、RSS フィード、OpenAI 等）

requirements.txt に必要パッケージをまとめてください（本リポジトリには含まれていないため、各自管理）。

例:
pip install duckdb openai defusedxml

---

## 環境変数 / 設定

config.Settings が利用する主な環境変数:

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabu ステーション API のパスワード
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID (必須) — 通知先 Slack チャンネル ID
- DUCKDB_PATH — DuckDB の DB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite（モニタリング用）パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 環境 (development | paper_trading | live)（デフォルト: development）
- LOG_LEVEL — ログレベル (DEBUG | INFO | WARNING | ERROR | CRITICAL)（デフォルト: INFO）
- OPENAI_API_KEY — OpenAI API キー（ai モジュールで使用）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 を設定すると自動 .env ロードを無効化

自動 .env 読み込み:
- プロジェクトルート（.git または pyproject.toml を基準）から .env, .env.local を自動ロードします。OS 環境変数が優先されます。テスト時等に無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を使用してください。

例の .env（.env.example を作成して管理してください）:
JQUANTS_REFRESH_TOKEN=...
OPENAI_API_KEY=...
KABU_API_PASSWORD=...
SLACK_BOT_TOKEN=...
SLACK_CHANNEL_ID=...
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO

---

## セットアップ手順

1. リポジトリをクローン
   git clone <repo-url>
   cd <repo>

2. 仮想環境を作成・有効化（推奨）
   python -m venv .venv
   source .venv/bin/activate  # Unix/macOS
   .venv\Scripts\activate     # Windows

3. 依存パッケージをインストール
   pip install -U pip
   pip install duckdb openai defusedxml

   （プロジェクト用に requirements.txt を用意していれば `pip install -r requirements.txt`）

4. 環境変数を設定
   - プロジェクトルートに .env を作成するか、環境変数として設定してください。
   - 必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
   - OpenAI を使う場合: OPENAI_API_KEY

5. DuckDB データベース用ディレクトリ作成（必要に応じて）
   mkdir -p data

---

## 使い方（例）

以下は主要ユースケースの簡単な利用例です。実行は Python スクリプト内で行います。

- 日次 ETL を実行する（ETL は DuckDB 接続を受け取ります）:

```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメントを算出して ai_scores テーブルへ書き込む:

```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
print(f"書き込み銘柄数: {n_written}")
```

- 市場レジームを算出する（1321 の MA200 とマクロニュースの合成）:

```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")
```

- 監査ログ用 DB を初期化する（監査専用 DB を作る）:

```python
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/audit.duckdb")
# テーブル作成済みの conn を使って監査ログを書き込めます
```

- カレンダー更新ジョブ（J-Quants から calendar を取得・保存）:

```python
from datetime import date
import duckdb
from kabusys.data.calendar_management import calendar_update_job

conn = duckdb.connect("data/kabusys.duckdb")
saved = calendar_update_job(conn)
print(f"saved: {saved}")
```

備考:
- OpenAI 呼び出し（news_nlp / regime_detector）は `OPENAI_API_KEY` を環境変数で渡すか、api_key 引数で渡してください。
- 各関数はルックアヘッドバイアス防止のため target_date を受け取り、内部で直接現在時刻を参照しない設計です。

---

## ディレクトリ構成（主要ファイル）

（src/kabusys 以下を要約）

- kabusys/
  - __init__.py
  - config.py                — 環境変数管理 / .env 自動読み込み
  - ai/
    - __init__.py
    - news_nlp.py            — ニュースの OpenAI によるバッチセンチメント取得（score_news）
    - regime_detector.py     — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント（fetch / save / token管理）
    - pipeline.py            — ETL パイプライン（run_daily_etl 他）
    - etl.py                 — ETLResult の再エクスポート
    - news_collector.py      — RSS 収集・正規化・保存
    - quality.py             — データ品質チェック（check_missing_data 等）
    - calendar_management.py — カレンダー管理（is_trading_day, next_trading_day 等）
    - audit.py               — 監査ログ DDL & 初期化ユーティリティ
    - stats.py               — zscore_normalize 等統計ユーティリティ
  - research/
    - __init__.py
    - factor_research.py     — calc_momentum / calc_volatility / calc_value
    - feature_exploration.py — calc_forward_returns / calc_ic / factor_summary / rank
  - ai, data, research の他に strategy, execution, monitoring などを __all__ で公開する設計

---

## 開発 / テスト上の注意

- .env の自動読み込みはプロジェクトルート（.git または pyproject.toml を基準）を探索して行います。テストで自動ロードを止めたい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI / J-Quants API 呼び出しは外部依存のため、ユニットテストでは該当関数をモックしてください（本実装はテスト用に patch しやすいように内部呼び出しを分離しています）。
- DuckDB executemany は空リストを受け入れないバージョンがあるため、保存関数では事前に空チェックを行っています。ユニットテストでも同様の前提に注意してください。

---

## ライセンス / 貢献

（必要に応じてここにライセンス、コントリビュート方法やコードスタイル、テスト実行方法を記載してください）

---

以上がこのコードベースの README.md です。補足や具体的な利用シナリオ（CI設定、requirements.txt の生成、例コンフィグファイル .env.example 等）を追加したい場合は指示ください。