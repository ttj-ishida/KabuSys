# KabuSys

KabuSys は日本株の自動売買・データプラットフォーム用ライブラリです。J-Quants / kabuステーション / OpenAI（LLM）等と連携して、データ収集（ETL）、品質チェック、ファクター計算、ニュースセンチメント評価、監査ログ管理などの機能を提供します。

バージョン: 0.1.0

---

## 概要

このプロジェクトは以下の目的を持ちます。

- J-Quants API から株価・財務・市場カレンダーを差分取得して DuckDB に保存する ETL パイプライン
- ニュース（RSS）収集と LLM による銘柄別センチメント評価（ai_scores の生成）
- 市場レジーム判定（ETF 1321 の MA200 乖離 + マクロニュースセンチメントの合成）
- リサーチ（ファクター計算、将来リターン、IC、統計サマリー）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（signal / order_request / executions）用スキーマ初期化ユーティリティ

設計上の特徴：
- Look-ahead バイアス対策（内部で date.today()/datetime.now() を不用意に参照しない）
- DuckDB をメインのローカルデータストアに利用
- OpenAI（gpt-4o-mini 等）を JSON Mode で呼び出す想定の堅牢な API 呼び出しラッパ
- 冪等性（保存は基本的に ON CONFLICT DO UPDATE / DO NOTHING を使用）

---

## 主な機能一覧

- data/
  - ETL パイプライン（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - J-Quants クライアント（取得 / 保存 / リトライ / レート制御）
  - カレンダー管理（is_trading_day / next_trading_day / prev_trading_day / get_trading_days）
  - ニュース収集（RSS の取得・正規化・保存、SSRF/サイズ/圧縮対策）
  - データ品質チェック（欠損・スパイク・重複・日付不整合）
  - 監査ログスキーマ初期化（init_audit_schema / init_audit_db）
  - 汎用統計ユーティリティ（zscore 正規化など）
- ai/
  - news_nlp.score_news: ニュースを集約して OpenAI にセンチメント評価を依頼し ai_scores に書き込む
  - regime_detector.score_regime: ETF 1321 の MA200 乖離とマクロニュースセンチメントを合成して market_regime に書き込む
- research/
  - ファクター計算（calc_momentum / calc_value / calc_volatility）
  - 特徴量探索（calc_forward_returns / calc_ic / factor_summary / rank）
- config:
  - Settings クラスで環境変数から設定値を取得（自動的に .env / .env.local をロードする挙動あり）

---

## 必要条件（推奨）

- Python >= 3.10
- DuckDB（Python パッケージ: duckdb）
- OpenAI Python SDK（openai）
- defusedxml（RSS パース用）
- 標準ライブラリでカバーできる箇所は利用（urllib 等）

サンプル依存関係（requirements.txt の例）:
```
duckdb>=0.8
openai>=1.0
defusedxml>=0.7
```

（実プロジェクトでは他にもロギング・HTTP ライブラリなどが必要になる場合があります）

---

## セットアップ手順

1. リポジトリをクローンして仮想環境を作成
   ```
   git clone <repo-url>
   cd <repo-directory>
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   ```

2. 依存パッケージをインストール
   ```
   pip install -U pip
   pip install duckdb openai defusedxml
   # または requirements.txt を用意して pip install -r requirements.txt
   ```

3. 環境変数を設定
   - プロジェクトルート（.git または pyproject.toml のある場所）に .env または .env.local を置くと自動読み込みされます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると無効化できます）。

   必須の環境変数（例）:
   - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
   - KABU_API_PASSWORD : kabuステーション API のパスワード（必要時）
   - SLACK_BOT_TOKEN : Slack 通知を使う場合
   - SLACK_CHANNEL_ID : Slack 通知先チャンネル ID
   - OPENAI_API_KEY : OpenAI API キー（ai.score_news / regime_detector 等で必要）

   任意:
   - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH（監視等で使用、デフォルト: data/monitoring.db）
   - KABUSYS_ENV（development / paper_trading / live、デフォルト development）
   - LOG_LEVEL（DEBUG/INFO/...、デフォルト INFO）

   例 (.env):
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxx
   OPENAI_API_KEY=sk-...
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   ```

4. DuckDB ファイルと監査 DB の初期化（必要に応じて）
   - 監査ログ専用 DB を作る例:
   ```python
   from kabusys.data.audit import init_audit_db
   conn = init_audit_db("data/audit.duckdb")  # ディレクトリがなければ作成されます
   conn.close()
   ```

---

## 使い方（簡単なコード例）

- DuckDB 接続を取得して日次 ETL を実行する
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl
from kabusys.config import settings

# settings.duckdb_path は .env によらず明示的に Path オブジェクトで取得可能
db_path = settings.duckdb_path
conn = duckdb.connect(str(db_path))

# 日次 ETL（target_date を省略すると今日の日付が使われる）
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
conn.close()
```

- ニュースセンチメント（ai_scores へ書き込む）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
written = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
print(f"書き込み銘柄数: {written}")
conn.close()
```

- 市場レジーム判定の実行
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")
conn.close()
```

- 監査スキーマ初期化（既存 DuckDB 接続へ追加）
```python
from kabusys.data.audit import init_audit_schema
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
init_audit_schema(conn, transactional=True)
```

- リサーチ用ファクター計算例
```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum

conn = duckdb.connect("data/kabusys.duckdb")
momentum = calc_momentum(conn, target_date=date(2026, 3, 20))
print(len(momentum), "銘柄計算完了")
```

---

## 環境変数と設定の要点

- 自動 .env 読み込み
  - パッケージ起点の親ディレクトリから .git または pyproject.toml を探してプロジェクトルートを判定し、.env / .env.local を自動ロードします。
  - OS 環境変数は上書きされません。.env.local は .env を上書きします。
  - テストなどで自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

- Settings API（programmatic）
  - from kabusys.config import settings
  - settings.jquants_refresh_token, settings.duckdb_path, settings.env, settings.is_live などのプロパティから値を取得できます。
  - 必須変数が未設定だと ValueError が発生します（例: JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN 等）。

---

## ディレクトリ構成（概要）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py            — ニュースセンチメント（score_news）
    - regime_detector.py     — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント（fetch / save）
    - pipeline.py            — ETL パイプライン（run_daily_etl など）
    - etl.py                 — ETL 結果型の公開（ETLResult）
    - news_collector.py      — RSS 収集処理
    - calendar_management.py — 市場カレンダー管理・判定ロジック
    - quality.py             — データ品質チェック
    - stats.py               — 汎用統計ユーティリティ（zscore_normalize 等）
    - audit.py               — 監査ログスキーマ初期化
  - research/
    - __init__.py
    - factor_research.py     — ファクター計算
    - feature_exploration.py — 将来リターン・IC・統計サマリー
  - research/*, ai/*, data/*：各種ユーティリティや公開 API を提供

---

## よくある運用上の注意

- OpenAI 呼び出しおよび外部 API にはリトライ・バックオフが実装されていますが、API キーやレート制限は運用側で管理してください。
- データ保存は基本的に冪等（ON CONFLICT）を目指していますが、ETL 実行時はバックアップや監査ログの設計を検討してください。
- テスト時は外部ネットワーク呼び出しをモックすること（news_nlp/_call_openai_api、jquants_client._request、news_collector._urlopen などが差し替えポイント）。
- DuckDB の executemany に対するバージョン依存の挙動（空リスト不可など）に留意しています。ライブラリのバージョンにより微妙な差が出る可能性があります。

---

もし README に追加してほしい内容（CLI 実行例、CI 用のセットアップ、具体的な .env.example、開発ルール等）があれば教えてください。