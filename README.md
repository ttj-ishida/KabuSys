# KabuSys

KabuSys は日本株向けの自動売買 / データプラットフォーム用ライブラリ群です。  
J-Quants（株価・財務・カレンダー）や RSS ニュース、OpenAI を組み合わせてデータ取得、品質チェック、AI によるニュースセンチメント、研究用ファクター計算、監査ログの管理などを提供します。

---

## 主な特徴

- データ ETL
  - J-Quants API からの株価（日足）・財務・市場カレンダーの差分取得と DuckDB への冪等保存
  - 品質チェック（欠損、スパイク、重複、日付不整合）
- ニュース処理
  - RSS 収集（SSRF 対策、トラッキングパラメータ削除）
  - OpenAI を用いた銘柄別ニュースセンチメント（ai_scores への保存）
- 市場レジーム判定
  - ETF 1321 の MA200 とマクロ記事の LLM センチメントを組み合わせて日次レジーム判定
- リサーチ（研究向けユーティリティ）
  - モメンタム、バリュー、ボラティリティ等のファクター計算
  - 将来リターン計算、IC（Spearman）や統計サマリー
  - Zスコア正規化ユーティリティ
- 監査ログ（トレーサビリティ）
  - signal_events / order_requests / executions などの監査テーブル作成ユーティリティ
- 設定管理
  - .env / .env.local / OS 環境変数からの設定読み込み（自動ロード、優先順位あり）

---

## 必要条件

- Python 3.10+（型注釈の Union shorthand を使用）
- 推奨パッケージ（一部抜粋）:
  - duckdb
  - openai
  - defusedxml
  - （標準ライブラリを中心に実装されていますが、J-Quants 接続や OpenAI 呼び出しのため上記が必要です）

例:
```
pip install duckdb openai defusedxml
# またはプロジェクトがパッケージ化されていれば
pip install -e .
```

---

## 環境変数 / .env

このプロジェクトは .env ファイルまたは OS 環境変数を使用します。自動読み込みの仕様:

- 自動ロード条件:
  - 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` をセットすると自動ロードを無効化できます（テスト用途）。
  - プロジェクトルートは __file__ の親ディレクトリから `.git` または `pyproject.toml` を探索して特定します。見つからなければ自動ロードをスキップ。

- 読み込み優先順位:
  1. OS 環境変数
  2. .env.local（存在すれば .env を上書き可能）
  3. .env

- .env のパースは `export KEY=val`、クォート、インラインコメント等に対応しています。

主に必要となる環境変数（代表）:
- JQUANTS_REFRESH_TOKEN  ← J-Quants 用リフレッシュトークン（必須）
- KABU_API_PASSWORD       ← kabu API パスワード（必須）
- SLACK_BOT_TOKEN         ← Slack 通知用トークン（必須）
- SLACK_CHANNEL_ID        ← Slack チャンネル ID（必須）
- OPENAI_API_KEY          ← OpenAI 呼び出し（score_news / score_regime 等で使用）
- DUCKDB_PATH             ← データベースパス（既定: data/kabusys.duckdb）
- SQLITE_PATH             ← 監視用 SQLite（既定: data/monitoring.db）
- KABUSYS_ENV             ← development / paper_trading / live（既定: development）
- LOG_LEVEL               ← DEBUG/INFO/WARNING/ERROR/CRITICAL（既定: INFO）

例: `.env`（簡易）
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
LOG_LEVEL=INFO
```

---

## セットアップ手順（基本）

1. リポジトリをクローン
2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate
3. 必要パッケージをインストール
   - pip install -r requirements.txt
   - または個別に pip install duckdb openai defusedxml
4. .env を作成（.env.example を参照して必要なキーを設定）
5. DuckDB ファイルや出力ディレクトリを作成（自動作成されることもあります）
6. （任意）KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動読み込みを制御

---

## 使い方（簡単な例）

以下は Python REPL やスクリプト内での利用例です。

- DuckDB 接続を作る（既定のパスは settings.duckdb_path）:
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

- デイリー ETL を実行する:
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメントをスコアリング（OpenAI APIキーは env か api_key 引数で指定）:
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

n_written = score_news(conn, target_date=date(2026, 3, 20))
print(f"wrote {n_written} ai_scores")
```

- 市場レジームを判定して保存:
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ用 DB 初期化（専用 DB を使う例）:
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# これで監査テーブルが作成されます
```

- RSS フィードを取得（ニュース収集ヘルパー）:
```python
from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES

articles = fetch_rss(DEFAULT_RSS_SOURCES["yahoo_finance"], source="yahoo_finance")
for a in articles:
    print(a["id"], a["title"], a["datetime"])
```

注意点:
- OpenAI を呼ぶ関数は api_key を引数で渡すことが可能です（テスト用途に便利）。
- ETL / 品質チェック / AI スコアリングは外部 API に依存するため、キーとネットワークが必要です。
- run_daily_etl は複数ステップ（カレンダー→株価→財務→品質チェック）を順に実行します。各ステップは個別にエラーハンドリングされています。

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定管理（.env 自動読み込み）
  - ai/
    - __init__.py
    - news_nlp.py            — ニュースの LLM スコアリング（score_news）
    - regime_detector.py     — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント（取得・保存）
    - pipeline.py            — ETL パイプライン（run_daily_etl 等）
    - etl.py                 — ETL インターフェース再エクスポート（ETLResult）
    - news_collector.py      — RSS 収集（SSRF 対策・正規化）
    - quality.py             — データ品質チェック（各チェック）
    - stats.py               — 汎用統計ユーティリティ（zscore_normalize 等）
    - calendar_management.py — 市場カレンダー管理（営業日判定・更新ジョブ）
    - audit.py               — 監査ログ（テーブル定義・初期化）
  - research/
    - __init__.py
    - factor_research.py     — Momentum / Value / Volatility 計算
    - feature_exploration.py — 将来リターン / IC / 統計サマリー 等

各モジュールは DuckDB 接続オブジェクト（duckdb.DuckDBPyConnection）を受け取る設計になっており、DB への直接アクセスや外部ブローカーへの発注は実装範囲外（研究・データ処理・監査用の機能群）です。

---

## 実運用上の注意・設計方針（抜粋）

- ルックアヘッドバイアス対策:
  - 関数は内部で date.today() / datetime.today() を参照しない設計が多く、target_date を明示して処理を行います。
- 冪等性:
  - J-Quants 保存関数や監査テーブルの初期化は冪等に設計されています（ON CONFLICT など）。
- フェイルセーフ:
  - OpenAI などの外部 API 呼び出しはリトライやフォールバックを行い、致命的エラーを避ける設計です（失敗時はスコアを 0 とする等）。
- セキュリティ:
  - RSS 収集は SSRF 対策（リダイレクト検査、プライベートIPブロック）と XML の防御（defusedxml）を実装しています。

---

この README はリポジトリ内コードの主要機能を要約したものです。より詳細な設計背景やドキュメント（DataPlatform.md / StrategyModel.md 等）がリポジトリに含まれている場合はそちらを参照してください。必要であれば、利用例や CI / デプロイ手順の追加ドキュメントも作成します。