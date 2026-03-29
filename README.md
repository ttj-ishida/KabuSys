# KabuSys — 日本株自動売買プラットフォーム（README）

簡潔な概要・セットアップ・使い方・ディレクトリ構成などをまとめた README です。

---

## プロジェクト概要

KabuSys は日本株のデータ取得（ETL）、ニュース NLP によるセンチメント評価、マーケットレジーム判定、ファクター研究、監査ログ（トレーサビリティ）、および発注監査用のユーティリティ群を含むモジュール群です。  
設計上の特徴として以下を重視しています。

- DuckDB をデータストアとして使用し、ETL／分析を SQL と軽量な Python で実装
- J-Quants API を利用した差分取得（ページネーション / レート制御 / トークン自動更新）
- OpenAI（gpt-4o-mini 等）を用いたニュースセンチメント（JSON Mode）評価（リトライ・フォールバック実装）
- ニュース収集時の SSRF 対策、XML の安全パース、サイズ制限
- ETL／保存処理は冪等（idempotent）設計（ON CONFLICT / DELETE→INSERT 等）
- バックテストでのルックアヘッドバイアス対策（date.now の直接参照を避ける等）
- 監査ログスキーマ（signal → order_request → executions）の提供

バージョン: 0.1.0（src/kabusys/__init__.py）

---

## 主な機能一覧

- data
  - ETL パイプライン: 日次 ETL（株価・財務・カレンダー）run_daily_etl
  - J-Quants クライアント: 認証・fetch/save（株価・財務・マーケットカレンダー・上場銘柄）
  - カレンダー管理: is_trading_day / next_trading_day / prev_trading_day / calendar_update_job
  - ニュース収集: RSS フィード取得（SSRF 対策、前処理）fetch_rss
  - データ品質チェック: 欠損・スパイク・重複・日付不整合の検出
  - 監査ログスキーマ初期化 / 監査 DB 初期化（init_audit_schema, init_audit_db）
  - 統計ユーティリティ: zscore_normalize
- ai
  - ニュース NLP スコアリング: score_news（銘柄ごとの ai_score を ai_scores に書き込み）
  - 市場レジーム検出: score_regime（ETF 1321 の MA200 とマクロ記事の LLM センチメントを合成）
- research
  - ファクター計算: calc_momentum, calc_value, calc_volatility
  - 特徴量探索 / 統計: calc_forward_returns, calc_ic, factor_summary, rank
- config
  - 環境変数読み込み（.env / .env.local 自動ロード）と必須設定取得
- audit（data.audit）
  - signal_events / order_requests / executions テーブル定義、インデックス、初期化ユーティリティ

その他、細かいユーティリティ関数（URL 正規化、JSON Mode の API 呼び出しラッパー、リトライやレートリミッタなど）を多数含みます。

---

## 必要な前提・依存

- Python 3.10+（ソースで PEP 604 の X | Y 型注釈を使用）
- パッケージ（少なくとも以下が必要）
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants API / OpenAI / RSS ソース 等）

（実際のプロジェクトでは requirements.txt / pyproject.toml を参照してインストールしてください）

例:
```bash
python -m pip install duckdb openai defusedxml
```

---

## 環境変数 / .env

config.Settings が環境変数を参照します。プロジェクトルート（.git または pyproject.toml を探索）にある `.env` および `.env.local` を自動読み込みします（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

主に必要な環境変数例:

- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabu ステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY: OpenAI API キー（ai.score_news / ai.score_regime 実行時に必要）
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID: Slack 通知先チャンネル ID（必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite（監視用）パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL: DEBUG/INFO/...（デフォルト: INFO）

.sample `.env`（README 用例）:
```env
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-xxxxxx
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

注意:
- `.env.local` は `.env` の上書き（優先）として読み込まれます。
- OS 側で既に設定された環境変数は上書きされません（ただし .env.local は override=True の挙動で既存環境変数を上書きする仕組みになっていますが、設定実装上 os.environ のキーは protected として扱われます）。

---

## セットアップ手順（簡易）

1. リポジトリをクローン
   ```bash
   git clone <repo-url>
   cd <repo>
   ```

2. Python 仮想環境を作成（任意）
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```

3. 必要パッケージをインストール
   - 実プロジェクトに requirements.txt / pyproject.toml があればそれを使ってください。最低パッケージ例:
   ```bash
   pip install duckdb openai defusedxml
   ```

4. `.env`（および任意で `.env.local`）を作成し必要な環境変数を設定

5. DuckDB 初期化（監査 DB を使う場合）
   - 監査 DB を作成・初期化する例（Python REPL またはスクリプト）:
   ```python
   from kabusys.data.audit import init_audit_db
   conn = init_audit_db("data/audit.duckdb")
   # conn は duckdb.DuckDBPyConnection オブジェクト
   ```

6. ETL 実行の準備
   - DuckDB 接続を作り、必要なスキーマが整っていることを確認してから実行してください（schema 初期化用ユーティリティが別途あることを想定）。

---

## 使い方（主要な例）

以下は最小限の利用例スニペットです。実運用ではロギング設定やエラーハンドリング、ジョブスケジューリング（cron / Airflow 等）を追加してください。

- DuckDB に接続して日次 ETL を実行する
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュース NLP スコアリング（OpenAI API キーが環境変数に設定されている想定）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # 環境変数 OPENAI_API_KEY を使用
print(f"written scores: {n_written}")
```

- 市場レジーム判定
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

- RSS フィード取得（ニュース収集）
```python
from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES

articles = fetch_rss(DEFAULT_RSS_SOURCES["yahoo_finance"], source="yahoo_finance")
for a in articles:
    print(a["id"], a["datetime"], a["title"])
```

- 監査スキーマの初期化（既存接続に追加）
```python
from kabusys.data.audit import init_audit_schema
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
init_audit_schema(conn, transactional=True)
```

- 研究用関数の呼び出し例（ファクター計算）
```python
from kabusys.research import calc_momentum, calc_value, calc_volatility
import duckdb
from datetime import date

conn = duckdb.connect("data/kabusys.duckdb")
momentum = calc_momentum(conn, date(2026, 3, 20))
vol = calc_volatility(conn, date(2026, 3, 20))
value = calc_value(conn, date(2026, 3, 20))
```

---

## 注意・運用上のポイント

- ルックアヘッドバイアス回避: 多くの関数は内部で date.today() を直接参照しない設計です。バッチやバックテストでは target_date を明示的に渡してください。
- 冪等性: ETL / save_* 関数は可能な限り ON CONFLICT 等で冪等に実装されていますが、部分失敗時の運用方針（再実行やロールバック）は運用側で検討してください。
- OpenAI 呼び出し: JSON Mode を活用し、応答のバリデーションを行ったうえで処理します。APIのエラーや解析失敗はフォールバック（スコア 0.0 等）して継続する実装方針です。
- J-Quants API: レート制限（120 req/min）に従う RateLimiter が組み込まれており、401 レスポンス時のトークン自動リフレッシュやリトライが行われます。
- セキュリティ: news_collector は SSRF 対策・XML パース防護・レスポンスサイズ制限を実装しています。RSS の取り込み先やネットワークアクセスの制限を運用で検討してください。

---

## ディレクトリ構成（主要ファイル）

リポジトリ配下の `src/kabusys` をベースに抜粋:

- src/kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py
    - regime_detector.py
  - data/
    - __init__.py
    - jquants_client.py
    - pipeline.py
    - etl.py
    - quality.py
    - stats.py
    - calendar_management.py
    - news_collector.py
    - audit.py
    - pipeline.py (ETLResult export)
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - research/ (exports zscore_normalize etc via data.stats)
  - other modules: （execution / monitoring / strategy 等が __all__ に列挙されている想定）

注意: 上記はソースベースの主要モジュールです。実運用では tests/ や docs/、スクリプト類（CLI, workers）等が別途存在することがあります。

---

## 開発・貢献

- コーディング規約・テスト方針: DuckDB の型・SQL の互換性に注意して、ユニットテストではネットワーク呼び出し（OpenAI / J-Quants / RSS）をモックしてください。
- 環境分離: KABUSYS_DISABLE_AUTO_ENV_LOAD を使うと自動 .env 読み込みを無効化できます（テスト時に便利）。
- 変更を行う場合は README / docstring に仕様変更を反映してください（特に外部 API の挙動や ETL の idempotency に関する部分）。

---

質問や追加したい章（例: CI 設定、運用 runbook、schema 初期化スクリプト例など）があれば教えてください。README に追記して整備します。