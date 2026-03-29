# KabuSys

日本株自動売買システムのコアライブラリ群。データETL、ニュース収集・NLP、ファクター研究、監査ログ、マーケットカレンダーやJ-Quants APIクライアントなどを含み、バックテスト／リサーチ／運用で使えるユーティリティ群を提供します。

---

## 概要

KabuSys は日本株に関するデータ収集、品質管理、ファクター計算、ニュースベースのAIスコアリング、そして監査可能な注文ログ構造などを備えたライブラリです。主な目的は次のとおりです。

- J-Quants API からの差分ETL（株価・財務・カレンダー）
- RSS ニュース収集と前処理（SSRF対策・トラッキング除去等）
- OpenAI を用いたニュースセンチメント（銘柄別 ai_score）およびマクロレジーム判定
- ファクター（モメンタム／バリュー／ボラティリティ等）計算と探索的解析
- DuckDB を利用したデータ保存・監査テーブル（冪等処理、トレーサビリティ）
- データ品質チェックとバッチ実行エントリポイント

---

## 主な機能一覧

- 環境設定の自動読み込み（.env / .env.local、KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化）
- J-Quants API クライアント（レート制御・リトライ・トークン自動リフレッシュ）
- ETL パイプライン（run_daily_etl によりカレンダー→株価→財務→品質チェックの一連処理）
- RSS ニュース収集（SSRF/サイズ/Gzip対策、URL 正規化、記事ID生成）
- OpenAI を使ったニュースセンチメント（score_news）・市場レジーム判定（score_regime）
- 研究用ユーティリティ（ファクター計算、将来リターン、IC計算、Zスコア正規化）
- データ品質チェック（欠損・スパイク・重複・日付不整合検出）
- 監査ログ（signal_events / order_requests / executions、監査DB初期化補助）

---

## 必要条件

- Python 3.10 以上（型アノテーションに `|` を使用）
- 推奨パッケージ（一例）:
  - duckdb
  - openai
  - defusedxml

実際のプロジェクトでは requirements.txt を用意して pip でインストールしてください。最低限必要なものを手動で入れる場合の例:

```
pip install duckdb openai defusedxml
```

（パッケージのバージョンは利用環境に合わせて調整してください）

---

## 環境変数 / 設定

KabuSys は環境変数から設定を読み込みます。以下が主要な必須／任意の設定です（.env に記載することを想定）。

必須:
- JQUANTS_REFRESH_TOKEN: J-Quants の refresh token（ETL 用）
- KABU_API_PASSWORD: kabuステーション API のパスワード（発注連携用）
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID: Slack 通知先チャンネル ID

OpenAI 関連:
- OPENAI_API_KEY: OpenAI 呼び出しに利用（score_news / score_regime で使用可能）

その他:
- KABUSYS_ENV: 環境（development / paper_trading / live）デフォルト: development
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）デフォルト: INFO
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite（監視用DB）パス（デフォルト: data/monitoring.db）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 自動 .env ロードを無効化（値を設定すれば無効）

注意:
- パッケージはプロジェクトルート（.git または pyproject.toml がある場所）から .env/.env.local を自動読み込みします。
- テストなどで自動読み込みを無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。

---

## セットアップ手順（例）

1. リポジトリをクローン／配置

2. 仮想環境を作成して有効化（推奨）

```
python -m venv .venv
source .venv/bin/activate  # macOS / Linux
.venv\Scripts\activate     # Windows
```

3. 必要パッケージをインストール

（プロジェクトに requirements.txt がある想定）
```
pip install -r requirements.txt
```
または最低限：
```
pip install duckdb openai defusedxml
```

4. .env を作成（.env.example を参考に必須値を設定）

5. DuckDB データベースの配置ディレクトリ作成（必要なら）
```
mkdir -p data
```

6. 監査DBを初期化する（任意）
Python REPL やスクリプトで:
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")  # ":memory:" も可
conn.close()
```

---

## 使い方（Python API の例）

以下はライブラリの主要な利用例です。各関数は duckdb 接続オブジェクト（duckdb.DuckDBPyConnection）を受け取ります。

- 日次ETL を実行する（run_daily_etl）

```python
import duckdb
from kabusys.data.pipeline import run_daily_etl
from kabusys.config import settings
from datetime import date

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
conn.close()
```

- ニュースセンチメント（OpenAI API 必須、OPENAI_API_KEY を環境変数でセット推奨）

```python
from kabusys.ai.news_nlp import score_news
import duckdb
from datetime import date

conn = duckdb.connect("data/kabusys.duckdb")
written = score_news(conn, target_date=date(2026, 3, 20))  # ai_scores テーブルへ書き込み
print("wrote", written, "codes")
conn.close()
```

- 市場レジーム判定（ma200 + マクロニュース + OpenAI、OPENAI_API_KEY 必須）

```python
from kabusys.ai.regime_detector import score_regime
import duckdb
from datetime import date

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
conn.close()
```

- 監査スキーマを初期化（既存 DuckDB 接続に追加）

```python
from kabusys.data.audit import init_audit_schema
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
init_audit_schema(conn, transactional=True)
conn.close()
```

- 研究用ファクター計算例

```python
from kabusys.research import calc_momentum, calc_value, calc_volatility
import duckdb
from datetime import date

conn = duckdb.connect("data/kabusys.duckdb")
moms = calc_momentum(conn, date(2026, 3, 20))
vals = calc_value(conn, date(2026, 3, 20))
vols = calc_volatility(conn, date(2026, 3, 20))
conn.close()
```

注: OpenAI 呼び出しを伴う関数（score_news/score_regime）は api_key 引数でキー注入可能です。テスト時はモック可能な設計になっています。

---

## ディレクトリ構成（抜粋）

以下は src/kabusys 以下の主なモジュールと役割の一覧です。

- kabusys/
  - __init__.py
  - config.py
    - 環境変数読み込み・設定アクセスラッパー
  - ai/
    - __init__.py
    - news_nlp.py
      - 銘柄ごとのニュースセンチメント算出 → ai_scores に書き込む
    - regime_detector.py
      - マクロセンチメント + ETF(1321) MA200乖離で market_regime を判定
  - data/
    - __init__.py
    - pipeline.py
      - ETL パイプラインのエントリポイント（run_daily_etl など）
    - jquants_client.py
      - J-Quants API クライアント（取得・保存の実装）
    - news_collector.py
      - RSS 収集・前処理・raw_news 保存ロジック
    - calendar_management.py
      - market_calendar 管理・営業日判定など
    - stats.py
      - zscore_normalize 等の統計ユーティリティ
    - quality.py
      - データ品質チェック（欠損、スパイク、重複、日付不整合）
    - audit.py
      - 監査ログテーブル定義・初期化（signal_events / order_requests / executions）
    - etl.py
      - ETL 結果クラス（ETLResult）再エクスポート
  - research/
    - __init__.py
    - factor_research.py
      - モメンタム／ボラティリティ／バリュー等の計算
    - feature_exploration.py
      - 将来リターン、IC、統計サマリー等

※ 上記は実装の主要ファイルを抜粋したものです。詳細はコードベースを参照してください。

---

## 注意点・設計上の留意点

- Look-ahead bias（ルックアヘッドバイアス）回避を明示的に設計しており、関数は基本的に date/target_date を受け取り、内部で current date を無制限に参照しないようになっています。
- OpenAI 呼び出しはリトライやフォールバックを備えていますが、API失敗時はスコアを 0 にフォールバックするなどの安全策を採っています（例：score_regime, score_news）。
- J-Quants API へのアクセスはレート制御とリトライを実装しており、トークン自動更新もサポートしています。
- DuckDB のバージョン差異（executemany の空配列挙動など）に配慮した実装になっています。
- ニュース収集では SSRF や XML Bomb、巨大レスポンスに対する防御策を実装しています。

---

## 開発・テスト

- 自動 .env 読み込みを無効化する場合:
  - 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定
- OpenAI / ネットワーク呼び出しのユニットテスト時は各モジュールの内部 _call_openai_api / _urlopen 等をモックすることを想定した実装です。

---

ご不明点や README に追加したいサンプル、CI 連携の手順、運用時の Cron / バッチ実行例などがあれば教えてください。必要に応じて具体的な運用手順や systemd / cron / Airflow での実行例も追加します。