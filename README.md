# KabuSys

日本株のデータパイプライン・リサーチ・自動売買基盤のライブラリ群です。  
ETL（J-Quants）→ データ品質チェック → ニュースNLP（OpenAI）→ 市場レジーム判定 → 監査ログ の一連処理を提供します。  
（ライブラリは発注実行レイヤーや監視連携なども想定したモジュール構成になっています。）

バージョン: 0.1.0

---

## 概要

KabuSys は主に以下を目的とする Python パッケージです。

- J-Quants API からの株価・財務・カレンダー等の差分 ETL（DuckDB へ保存）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- ニュース記事の収集・前処理・LLM（OpenAI）による銘柄センチメント解析（ai_scores 生成）
- マーケット（ETF 1321）とマクロニュースを組み合わせた市場レジーム判定（bull/neutral/bear）
- 監査ログ（signal_events / order_requests / executions）の初期化ユーティリティ
- 研究用ファクター計算（モメンタム / ボラティリティ / バリュー）と特徴量解析ユーティリティ

設計上の特徴（抜粋）:
- Look-ahead バイアスを避ける実装（日時参照の扱いに注意）
- DuckDB を用いたローカル高速ストア
- OpenAI 呼び出しは JSON Mode を利用、リトライ／フェイルセーフ設計
- ETL・保存は冪等性を考慮（ON CONFLICT 等）
- テストしやすい設計（API 呼び出し部分をモック可能）

---

## 主な機能一覧

- ETL / Data
  - run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl（kabusys.data.pipeline）
  - jquants_client: API 呼び出し、保存関数（save_daily_quotes 等）
  - market calendar 管理（calendar_update_job, is_trading_day, next_trading_day 等）
  - data quality チェック（check_missing_data, check_spike, check_duplicates, check_date_consistency）
  - news_collector: RSS 取得・前処理・保存ユーティリティ
  - audit: 監査ログスキーマ初期化（init_audit_schema / init_audit_db）

- AI / NLP
  - news_nlp.score_news: 銘柄別ニュースセンチメントを ai_scores に保存
  - regime_detector.score_regime: ma200 とマクロニュース（LLM）で市場レジーム判定

- Research
  - calc_momentum, calc_value, calc_volatility（kabusys.research.factor_research）
  - calc_forward_returns, calc_ic, factor_summary, rank（kabusys.research.feature_exploration）
  - zscore_normalize（kabusys.data.stats）

- 設定管理
  - kabusys.config.Settings 経由で環境変数を参照。プロジェクトルートの .env / .env.local を自動ロード（任意無効化可）。

---

## 必要条件 / 依存

- Python >= 3.10
- 必須パッケージ（例）:
  - duckdb
  - openai
  - defusedxml
- その他標準ライブラリ + requests 系は標準で十分なはずです（実行環境に合わせ追加してください）。

インストール例（仮）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install "duckdb" "openai" "defusedxml"
# またはパッケージ化されている場合:
# pip install -e .
```

---

## 環境変数 / 設定

kabusys.config.Settings により環境変数を参照します。主要な環境変数:

必須（各機能を使う場合は設定が必要）:
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（jquants_client）
- SLACK_BOT_TOKEN        : Slack 通知を使う場合
- SLACK_CHANNEL_ID       : Slack チャネル ID
- KABU_API_PASSWORD      : kabuステーション API を使う場合のパスワード
- OPENAI_API_KEY         : OpenAI 呼び出しを行う場合（news_nlp / regime_detector）

任意/デフォルトあり:
- KABUSYS_ENV : "development" / "paper_trading" / "live"（デフォルト: development）
- LOG_LEVEL   : "DEBUG" / "INFO" / ...
- DUCKDB_PATH : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH : 監視用 SQLite（デフォルト: data/monitoring.db）

自動 .env ロード:
- プロジェクトルート（.git または pyproject.toml のある親ディレクトリ）にある `.env` / `.env.local` を自動で読み込みます。自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

例: `.env`（簡易）
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
KABU_API_PASSWORD=your_password
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
```

---

## セットアップ手順（簡易）

1. Python 仮想環境を作成・有効化
2. 必要パッケージをインストール（duckdb, openai, defusedxml 等）
3. プロジェクトルートに `.env` を作成し必要な環境変数を設定
4. DuckDB データベース用ディレクトリを用意（例: data/）
5. （任意）監査用 DB 初期化:
   - init_audit_db を使って監査用 DuckDB を初期化できます（ファイル or :memory:）。

---

## 使い方（コード例）

以下は代表的な利用例です。実運用ではログ・例外ハンドリング・ID トークンの注入等を適切に行ってください。

- DuckDB に接続して日次 ETL を実行する:
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- News NLP スコアを実行して ai_scores に書き込む:
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026, 3, 20))
print("written:", n_written)
```

- 市場レジーム判定:
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログスキーマ（監査 DB）を初期化する:
```python
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/audit.duckdb")
# 必要に応じて同 conn を使用して order_requests 等を操作
```

- 研究用ファクター計算:
```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum

conn = duckdb.connect("data/kabusys.duckdb")
records = calc_momentum(conn, date(2026, 3, 20))
# z-score 正規化
from kabusys.data.stats import zscore_normalize
normed = zscore_normalize(records, ["mom_1m", "mom_3m", "mom_6m"])
```

---

## 実装上の注意 / テストしやすさ

- 日付の扱いは Look-ahead を避けるように設計されています。関数は target_date を引数で受け取り、内部で date.today()/datetime.today() を直接参照しないことが多いです。
- OpenAI 呼び出しや外部 HTTP はモック差し替え可能な設計（内部の `_call_openai_api` や `_urlopen` を patch してください）。
- DuckDB の executemany は空リストを受け取れないケースがあるため、実装内で空チェックをしています。
- J-Quants API 呼び出し部分はレートリミッタやリトライ、401 トークンリフレッシュを内包しています。

---

## ディレクトリ構成（主要ファイル）

（src/kabusys 以下の主要モジュール）

- src/kabusys/__init__.py
- src/kabusys/config.py
- src/kabusys/ai/
  - __init__.py
  - news_nlp.py
  - regime_detector.py
- src/kabusys/data/
  - __init__.py
  - jquants_client.py
  - pipeline.py
  - etl.py
  - calendar_management.py
  - news_collector.py
  - quality.py
  - stats.py
  - audit.py
  - pipeline.py (ETLResult 再エクスポート)
- src/kabusys/research/
  - __init__.py
  - factor_research.py
  - feature_exploration.py
- src/kabusys/ai/__init__.py

（その他）
- データベースファイル例: data/kabusys.duckdb, data/audit.duckdb

---

## よくある運用フロー（例）

1. Cron / Airflow 等で nightly に run_daily_etl を実行してデータ更新
2. ETL 成果を品質チェック（quality.run_all_checks）で確認し Slack 通知等を行う
3. ニュース収集と news_nlp.score_news を実行して ai_scores を更新
4. regime_detector.score_regime を実行して market_regime を更新
5. 研究チームは research モジュールでファクター探索・IC 検証
6. 戦略・実行層は監査ログ（order_requests / executions）へ書き込みながら運用

---

## 開発・拡張のヒント

- OpenAI 呼び出し部はテスト用に patch しやすいように内部関数を分離しています。
- DuckDB スキーマ変更時は audit.init_audit_schema などの初期化関数を参考にしてください。
- news_collector は SSRF 対策・受信サイズ検査・XML 脆弱性対策（defusedxml）を行っています。新しい RSS ソースを追加する際は DEFAULT_RSS_SOURCES に登録してください。

---

必要があれば、README に含める詳細なコマンド例（systemd / cron でのスケジュール、サンプル .env.example、CI テストのセットアップ）も作成できます。どの部分を詳しく記載しますか？