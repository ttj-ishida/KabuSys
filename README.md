# KabuSys — 日本株自動売買基盤（README）

KabuSys は日本株のデータパイプライン、研究（リサーチ）、ニュース NLP、マーケットレジーム判定、監査ログなどを備えた自動売買基盤向けのライブラリ群です。本 README はリポジトリの概要、機能、セットアップ、基本的な使い方、およびディレクトリ構成を日本語でまとめたものです。

---

## プロジェクト概要

KabuSys は以下を目的とした Python モジュール群です。

- J-Quants API から株価・財務・カレンダー等を差分取得して DuckDB に保存する ETL パイプライン
- 生データ品質チェック（欠損・スパイク・重複・日付不整合）
- ニュース記事の収集・前処理と OpenAI を用いた銘柄別センチメント（ai_score）算出
- マクロニュース + ETF（1321）の MA200 乖離を合成した市場レジーム判定（bull / neutral / bear）
- ファクター計算（モメンタム・バリュー・ボラティリティ等）と特徴量解析ユーティリティ
- 発注・約定に対する監査ログ（監査テーブル初期化ユーティリティ）
- 設定管理（.env 自動読み込み、環境変数管理）

設計上、バックテスト等でのルックアヘッドバイアスを最小化するため、target_date を明示する設計や DB 上のデータ範囲チェックを多用しています。

---

## 主な機能一覧

- data/
  - ETL: run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl
  - J-Quants クライアント（認証・レート制御・リトライ・DuckDB 保存）
  - カレンダー管理（営業日 / SQ 判定 / next/prev_trading_day）
  - ニュース収集（RSS -> raw_news 保存、SSRF 対策、トラッキングパラメータ除去）
  - 品質チェック（欠損・スパイク・重複・日付不整合）
  - 監査ログ初期化（監査テーブル・インデックス作成）
  - 統計ユーティリティ（zscore_normalize）
- ai/
  - news_nlp.score_news: 銘柄ごとのニュースセンチメント取得・ai_scores への保存（OpenAI 使用）
  - regime_detector.score_regime: マクロセンチメント + ETF MA200 を合成して market_regime に書き込み
- research/
  - factor_research: calc_momentum / calc_value / calc_volatility
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank
- config: .env 自動読み込みロジックと Settings（環境変数アクセス）

---

## 必要条件（依存ライブラリ）

- Python 3.10+
- duckdb
- openai (OpenAI Python SDK)
- defusedxml
- （標準ライブラリに依存する機能多数）

インストール例（仮想環境推奨）:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .         # 開発インストール（setup を用意している場合）
pip install duckdb openai defusedxml
```

※ このリポジトリに setup.py / pyproject.toml がある場合は `pip install -e .` で依存も自動解決できます。

---

## 環境変数 / .env

config.Settings で参照される主な環境変数:

必須（実行する機能に応じて）:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（get_id_token に使用）
- KABU_API_PASSWORD — kabuステーション API のパスワード（発注機能利用時）
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン（通知機能利用時）
- SLACK_CHANNEL_ID — Slack チャンネル ID

OpenAI 関連:
- OPENAI_API_KEY — OpenAI API キー（ai.score_news / ai.regime_detector が必要とする）

任意 / デフォルトあり:
- KABUSYS_ENV — "development" / "paper_trading" / "live"（デフォルト: development）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...、デフォルト INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 に設定すると .env の自動読み込みを無効化
- KABUSYS_API_BASE_URL — kabu API のベース URL（設定がある場合）

DB パス（デフォルト）:
- DUCKDB_PATH — データ DuckDB ファイル（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）

.env の自動読み込み挙動:
- プロジェクトルート（.git または pyproject.toml があるディレクトリ）を探索して .env を自動ロードします。
- 読み込み順: OS 環境 > .env.local > .env
- 自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

例 .env:

```
JQUANTS_REFRESH_TOKEN=xxxx...
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=your_kabu_pw
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
```

---

## セットアップ手順（最小セット）

1. リポジトリをクローン

```bash
git clone <repo-url>
cd <repo-dir>
```

2. 仮想環境の作成と依存インストール

```bash
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install duckdb openai defusedxml
# または `pip install -e .` が提供されていれば利用
```

3. .env を作成（必要な環境変数を設定）

4. データディレクトリを作成（必要に応じて）

```bash
mkdir -p data
```

5. DuckDB を使う場合、初期スキーマ（必要に応じて）や監査 DB を初期化

例: 監査データベース初期化

```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")  # ":memory:" も可能
```

---

## 基本的な使い方（コード例）

以下は代表的な利用例です。実行前に必要な環境変数（JQUANTS_REFRESH_TOKEN / OPENAI_API_KEY など）を設定しておいてください。

- 日次 ETL を実行して DuckDB にデータを保存する

```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュース NLP（銘柄別センチメント）を算出して ai_scores テーブルへ保存する

```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
written = score_news(conn, target_date=date(2026, 3, 20))
print(f"written scores: {written}")
```

- マーケットレジーム判定を実行（ETF 1321 + マクロニュース）

```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026,3,20))
```

- ファクター計算（モメンタム / ボラティリティ / バリュー）

```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum, calc_volatility, calc_value

conn = duckdb.connect("data/kabusys.duckdb")
m = calc_momentum(conn, date(2026,3,20))
v = calc_volatility(conn, date(2026,3,20))
val = calc_value(conn, date(2026,3,20))
```

- 監査スキーマだけ初期化する

```python
from kabusys.data.audit import init_audit_schema
import duckdb
conn = duckdb.connect("data/kabusys.duckdb")
init_audit_schema(conn, transactional=True)
```

---

## 注意事項 / 実装上のポイント

- OpenAI API 呼び出しは retry/backoff を伴い、失敗時はフォールバック（例: macro_sentiment = 0.0）する実装です。ただし API キーは必ず用意してください（score_news, score_regime）。
- J-Quants API 呼び出しはレート制限（120 req/min）・リトライ・401 リフレッシュを実装しています。JQUANTS_REFRESH_TOKEN を .env に設定してください。
- DuckDB に保存する各テーブル（raw_prices, raw_financials, raw_news, ai_scores, market_regime 等）は ETL / save_* 関数で冪等に更新されます（ON CONFLICT DO UPDATE 等）。
- ETL / レジーム判定 / ニューススコアリングの各関数はルックアヘッドバイアスを防ぐため、内部で date.today() を直接参照しない設計が徹底されています。必ず target_date を渡すことを推奨します。
- news_collector では SSRF 対策・レスポンスサイズチェック・XML パースの安全化（defusedxml）などセキュリティ対策が組み込まれています。

---

## ディレクトリ構成（主なファイルと説明）

（src/kabusys 以下）

- __init__.py
  - パッケージのメタ情報（__version__）とサブパッケージ公開
- config.py
  - 環境変数の自動読み込み・Settings クラス（アプリ設定の取得）
- ai/
  - __init__.py
  - news_nlp.py — ニュースのセンチメント付与（score_news）
  - regime_detector.py — マクロセンチメント + ETF MA200 による市場レジーム判定（score_regime）
- data/
  - __init__.py
  - jquants_client.py — J-Quants API クライアントと DuckDB 保存ロジック
  - pipeline.py — 日次 ETL のエントリポイント（run_daily_etl など）
  - etl.py — ETLResult の再エクスポート
  - calendar_management.py — 市場カレンダー管理・営業日ロジック
  - news_collector.py — RSS 収集・前処理・raw_news 保存ユーティリティ
  - quality.py — データ品質チェック
  - stats.py — zscore_normalize など統計ユーティリティ
  - audit.py — 監査ログスキーマの初期化（監査テーブル / インデックス）
- research/
  - __init__.py
  - factor_research.py — ファクター計算（momentum, value, volatility）
  - feature_exploration.py — 将来リターン計算 / IC / 統計サマリー等

---

## 開発・テストについて

- モジュール内の外部 API 呼び出し（OpenAI / J-Quants / HTTP）は単体テストでモック（patch）しやすいよう設計されています（例: _call_openai_api の差し替えなど）。
- .env の自動読み込みはテスト環境で無効化可能です（KABUSYS_DISABLE_AUTO_ENV_LOAD=1）。

---

## 最後に

この README はコードベースの主要機能と使い方の概要をまとめたものです。より詳細な設計仕様（DataPlatform.md / StrategyModel.md 等）がプロジェクト内に存在する想定ですので、運用・拡張を行う際はそちらも参照してください。必要があれば、README に追記（例: データスキーマ定義、DB マイグレーション手順、CI/CD の記載）しますので、追加で欲しい情報を教えてください。