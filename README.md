# KabuSys

日本株向けの自動売買／データプラットフォーム用ライブラリ群です。  
ETL、データ品質チェック、ニュース収集・NLP（LLM を使ったセンチメント評価）、市場レジーム判定、研究用ファクター計算、監査ログなどを含むモジュール群を提供します。

この README ではプロジェクト概要、主な機能、セットアップ手順、使い方（主要 API の例）、ディレクトリ構成を日本語で説明します。

---

目次
- プロジェクト概要
- 機能一覧
- 要件
- 環境変数 / 設定
- セットアップ手順
- 基本的な使い方（例）
  - ETL（run_daily_etl）
  - ニュースセンチメント（score_news）
  - 市場レジーム判定（score_regime）
  - 監査ログ DB 初期化
- ディレクトリ構成（主要ファイル説明）
- 自動 .env ロードの挙動
- 注意事項 / 設計上のポイント

---

## プロジェクト概要

KabuSys は以下を目的とした Python モジュール群です。

- J-Quants API を用いた日本株のデータ ETL（株価、財務、マーケットカレンダー）
- DuckDB を中心としたデータ保存と品質チェック
- RSS ベースのニュース収集と LLM による銘柄センチメント評価（OpenAI）
- マクロニュース＋ETF の移動平均乖離から市場レジーム（bull/neutral/bear）判定
- 研究用ファクター計算（モメンタム、バリュー、ボラティリティ）、特徴量解析ユーティリティ
- 発注・約定の監査ログスキーマ（監査用 DuckDB）

設計上、バックテストや研究用途でルックアヘッドバイアスを避ける実装・制約が盛り込まれています（例: datetime.today()/date.today() を直接参照しない等）。

---

## 機能一覧

主な機能（モジュール単位）

- kabusys.config
  - 環境変数の取得と自動 .env 読み込み（.env / .env.local）
  - 各種設定プロパティ（J-Quants トークン、kabu API、Slack、DB パス 等）

- kabusys.data
  - jquants_client: J-Quants API クライアント（取得・保存・リトライ・レート制御）
  - pipeline / etl: run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl
  - quality: データ品質チェック（欠損、スパイク、重複、日付整合性）
  - calendar_management: 営業日判定、next/prev_trading_day、calendar_update_job
  - news_collector: RSS 取得・前処理・保存（SSRF 対策・gzip 上限等）
  - audit: 発注→約定フローの監査テーブル定義と初期化ユーティリティ
  - stats: zscore_normalize 等の統計ユーティリティ

- kabusys.ai
  - news_nlp.score_news: LLM を用いた銘柄ごとのニュースセンチメント生成（ai_scores テーブルへ書込）
  - regime_detector.score_regime: ETF（1321）MA200 乖離 + マクロニュース（LLM）から市場レジーム判定・保存

- kabusys.research
  - factor_research: calc_momentum, calc_value, calc_volatility（prices_daily, raw_financials を参照）
  - feature_exploration: calc_forward_returns, calc_ic, factor_summary, rank

---

## 要件

- Python 3.10 以上（typing の | といった構文を使用）
- 主に利用されるライブラリ（例）:
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants API、OpenAI、RSS フィード等）

requirements.txt が別にある場合はそちらを使用してください。最低限は上記パッケージが必要です。

---

## 環境変数 / 設定

必須（少なくとも本機能を使う場合）:

- JQUANTS_REFRESH_TOKEN
  - J-Quants のリフレッシュトークン。jquants_client.get_id_token で使用。

- OPENAI_API_KEY
  - OpenAI を使う機能（news_nlp, regime_detector）で利用。関数呼び出し時に api_key 引数を渡すことでも指定可能。

- KABU_API_PASSWORD
  - kabu ステーション API（発注等）に必要（使用する場合）。

- SLACK_BOT_TOKEN
- SLACK_CHANNEL_ID
  - Slack 通知を行う場合に使用。

オプション（デフォルトあり）:

- KABUSYS_ENV: development / paper_trading / live （デフォルト: development）
- LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 を設定すると自動 .env ロードを無効化
- KABU_API_BASE_URL: kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite（監視用など）（デフォルト: data/monitoring.db）

設定は `.env` または `.env.local` に記述しておくと自動読み込みされます（優先順位: OS 環境変数 > .env.local > .env）。自動読み込みを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

簡易的な .env 例（プロジェクトルートの .env.example を参考にする想定）:

OPENAI_API_KEY=sk-...
JQUANTS_REFRESH_TOKEN=xxxx
KABU_API_PASSWORD=yyyy
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C0123456789
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO

---

## セットアップ手順

1. リポジトリをクローン

   git clone <repo-url>
   cd <repo-root>

2. Python 仮想環境の作成（任意）

   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows

3. 必要パッケージのインストール（例）

   pip install duckdb openai defusedxml

   あるいはパッケージ化されていれば:
   pip install -e .

4. 環境変数設定

   プロジェクトルートに .env を作成（上の例を参照）。ライブラリは自動的に .env / .env.local を読み込みます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD に注意）。

5. DuckDB ファイルの準備

   デフォルトでは data/kabusys.duckdb を使用。必要に応じて settings.duckdb_path を変更してください。

---

## 基本的な使い方（コード例）

以下はライブラリをインポートして主要機能を実行する簡単なサンプルです。実行前に必要な環境変数（特に OPENAI_API_KEY, JQUANTS_REFRESH_TOKEN）が設定されていることを確認してください。

- ETL 日次実行（run_daily_etl）

```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

# DuckDB に接続（ファイルパスは settings.duckdb_path に合わせてください）
conn = duckdb.connect("data/kabusys.duckdb")

# 日次ETL を実行（target_date=None で今日の ETL）
result = run_daily_etl(conn, target_date=date(2026, 3, 20))

print("ETLResult:", result.to_dict())
```

- ニュースセンチメント（OpenAI を使用）

```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
# target_date に対して前日 15:00 JST ～ 当日 08:30 JST の記事を対象にスコア化する
n_written = score_news(conn, target_date=date(2026, 3, 20))
print("書き込み銘柄数:", n_written)
```

- 市場レジーム判定（ETF 1321 の MA200 とマクロニュースを組合せ）

```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ DB 初期化（audit テーブルを作成）

```python
from kabusys.data.audit import init_audit_db

# インメモリまたはファイルに初期化
conn = init_audit_db(":memory:")
# または
conn = init_audit_db("data/audit.duckdb")
```

- 研究用ファクター計算（例: モメンタム）

```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum

conn = duckdb.connect("data/kabusys.duckdb")
records = calc_momentum(conn, target_date=date(2026, 3, 20))
# records は各銘柄のファクター辞書のリスト
```

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 以下の主要モジュールと役割の概観です。

- src/kabusys/__init__.py
  - パッケージのエントリ。バージョン定義等。

- src/kabusys/config.py
  - 環境変数管理、settings オブジェクト（J-Quants / kabu / Slack / DB パス / 環境判定 等）

- src/kabusys/data/
  - jquants_client.py: J-Quants API クライアント（取得・保存・トークン管理・レート制御）
  - pipeline.py: ETL パイプライン（run_daily_etl, run_prices_etl, ...）と ETLResult
  - etl.py: ETLResult の再エクスポート
  - news_collector.py: RSS 取得 / 前処理 / 保存（SSRF 対策・gzip 限度）
  - quality.py: データ品質チェック（欠損、スパイク、重複、日付整合性）
  - calendar_management.py: 市場カレンダー管理・営業日判定
  - stats.py: zscore_normalize 等の共通統計ユーティリティ
  - audit.py: 監査ログスキーマ定義と初期化ユーティリティ

- src/kabusys/ai/
  - news_nlp.py: ニュースセンチメント（OpenAI 呼出し、レスポンス検証、ai_scores へ保存）
  - regime_detector.py: ETF MA200 + マクロニュース LLM を組合わせた市場レジーム判定

- src/kabusys/research/
  - factor_research.py: モメンタム / ボラティリティ / バリュー の計算
  - feature_exploration.py: 将来リターン計算、IC、統計サマリー、ランク関数
  - __init__.py: 主要関数のエクスポート

---

## 自動 .env ロードの挙動

- 実行時、KABUSYS_DISABLE_AUTO_ENV_LOAD が設定されていない場合、プロジェクトルート（.git または pyproject.toml が見つかる親ディレクトリ）を起点に以下を読み込みます:
  - .env（読み取り専用: すでに設定された OS 環境変数を上書きしない）
  - .env.local（override=True: OS 環境変数で保護されたキー以外は上書き）

- .env ファイルのパースはシェル形式に近い仕様をサポートします（コメント・クォート・export プレフィックス等）。

- 自動ロードを無効化するには:
  - 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

---

## 注意事項 / 設計上のポイント

- ルックアヘッドバイアス対策:
  - AI モジュール・ETL・研究用計算の多くは target_date 引数を受け取り、内部で現在時刻を直接参照しないよう設計されています。バックテスト等での利用時は target_date を明確に指定してください。

- OpenAI:
  - news_nlp / regime_detector は OpenAI の Chat Completions（gpt-4o-mini を想定）を利用します。API のエラーやパース失敗はフェイルセーフ（0.0 等）にフォールバックする設計です。

- J-Quants:
  - jquants_client はレート制御（120 req/min）・リトライ・401 自動リフレッシュ等のロジックを備えています。J-Quants のトークンは settings.jquants_refresh_token 経由で提供されます。

- DuckDB:
  - データ保存は DuckDB を想定しています。ETL は冪等性（ON CONFLICT DO UPDATE）を考慮して設計されています。

- セキュリティ:
  - RSS 取得では SSRF 対策・GZIP 上限チェック・XML パースの安全ライブラリ（defusedxml）を使用しています。
  - URL 正規化・トラッキングパラメータ除去による記事 ID の生成を行っています。

---

この README はライブラリの主要な目的、使い方、設計上の重要点をまとめたものです。実運用時には .env.example を作成して機密情報を管理し、OpenAI/J-Quants の API レート制限や料金、発注ロジック（live 環境での実行）について慎重に扱ってください。必要であれば、各モジュールの docstring・関数コメントを参照してください。