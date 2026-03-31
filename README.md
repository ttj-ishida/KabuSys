# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ。J-Quants API、ニュース収集、LLM を用いたニュースセンチメント評価、DuckDB を用いた ETL・品質チェック・監査ログなどの機能を提供します。

---

目次
- プロジェクト概要
- 主な機能
- 前提・依存関係
- セットアップ手順
- 環境変数（.env）について
- 使い方（サンプル）
- ディレクトリ構成

---

## プロジェクト概要

KabuSys は日本株向けデータプラットフォームとリサーチ／自動売買基盤を構成する Python パッケージ群です。  
主な目的は次のとおりです。

- J-Quants API を利用した株価・財務・カレンダーの差分 ETL
- RSS を用いたニュース収集と銘柄紐付け
- OpenAI（gpt-4o-mini 等）を用いたニュース NLP（銘柄別スコア、マクロセンチメント）
- DuckDB をバックエンドにした時系列データ保存・品質チェック・監査ログ
- 研究用ファクター計算（モメンタム・バリュー・ボラティリティ等）と特徴量解析ユーティリティ

設計方針としては、ルックアヘッドバイアス回避、冪等性（INSERT ... ON CONFLICT）、フェールセーフ（APIエラー時は継続）を重視しています。

---

## 主な機能一覧

- data
  - J-Quants API クライアント（fetch / save 機能、レート制御、リトライ、トークン自動更新）
  - ETL パイプライン (run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl)
  - market_calendar 管理と営業日ユーティリティ（is_trading_day, next_trading_day 等）
  - news_collector: RSS 収集、SSRF 対策、URL 正規化、前処理、冪等保存
  - quality: データ品質チェック（欠損・スパイク・重複・日付不整合）
  - audit: 監査ログスキーマの生成 / 初期化（signal_events, order_requests, executions）
  - stats: 汎用統計ユーティリティ（zscore_normalize）
- ai
  - news_nlp.score_news: 銘柄ごとにニュースセンチメントを LLM で評価して ai_scores テーブルへ保存
  - regime_detector.score_regime: ETF 1321 の MA200 乖離とマクロニュース LLM スコアを合成して市場レジームを判定・保存
- research
  - factor_research: calc_momentum / calc_value / calc_volatility
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank
- config
  - Settings クラスで環境変数を集約（自動 .env ロード機能あり）

---

## 前提・依存関係

- Python 3.10 以上（| 型注釈や構文を使用しているため）
- 必要パッケージ（一例）
  - duckdb
  - openai
  - defusedxml
- 標準ライブラリ（urllib, json, datetime など）を使用

pip での例:
```
pip install duckdb openai defusedxml
```

プロジェクト配布時は pyproject.toml / requirements.txt に依存が定義されていることを想定しています。

---

## セットアップ手順

1. リポジトリをクローン／取得し、仮想環境を作成してアクティブ化します。
2. 必要パッケージをインストールします（上記参照）。
3. 環境変数を設定します（下記「環境変数（.env）について」を参照）。
   - プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（config モジュール）。
   - 自動読み込みを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。
4. DuckDB 等のデータベースファイル用ディレクトリを用意（デフォルトは `data/`）。
   - config.settings.duckdb_path のデフォルト: `data/kabusys.duckdb`
   - audit 用 DB は別ファイルに分けられます（init_audit_db で初期化可能）

例: 必要ディレクトリ作成
```bash
mkdir -p data
```

---

## 環境変数 (.env) — 必須 / 任意

主に以下の環境変数が使用されます。`.env.example` を参考に `.env` を作成してください。

必須:
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（ETL の認証）
- KABU_API_PASSWORD: kabuステーション（発注API）のパスワード（実行系で使用）
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（通知機能を使う場合）
- SLACK_CHANNEL_ID: Slack 送信先チャンネル ID
- OPENAI_API_KEY: OpenAI API キー（ai.score_news / ai.regime_detector を使用する場合）

任意 / デフォルトあり:
- KABUSYS_ENV: "development" | "paper_trading" | "live"（デフォルト: development）
- LOG_LEVEL: "DEBUG" | "INFO" | "WARNING" | "ERROR" | "CRITICAL"（デフォルト: INFO）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1: 自動 .env 読み込みを無効化

例 .env（簡易）
```
JQUANTS_REFRESH_TOKEN=xxxx...
OPENAI_API_KEY=sk-xxxx...
KABU_API_PASSWORD=yourpasswd
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
```

---

## 使い方（代表的なサンプル）

以下は Python から直接利用する典型的な例です。

- 設定を参照する
```python
from kabusys.config import settings
print(settings.jquants_refresh_token)
print(settings.duckdb_path)  # Path object
```

- DuckDB 接続を作って ETL を実行する（run_daily_etl）
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- ニュースセンチメント（銘柄別）をスコアリングして ai_scores に書き込む
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

# conn: duckdb connection, target_date: date（計算対象日）
count = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # OPENAI_API_KEY を環境で指定していれば None で可
print(f"scored {count} stocks")
```

- 市場レジーム判定
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20))  # market_regime テーブルに書き込み
```

- 監査ログ DB の初期化（audit 用）
```python
from kabusys.data.audit import init_audit_db
conn_audit = init_audit_db("data/audit.duckdb")
# conn_audit を使って order_requests や executions を操作できます
```

- 研究用ファクター計算
```python
from kabusys.research.factor_research import calc_momentum
from datetime import date

records = calc_momentum(conn, target_date=date(2026, 3, 20))
# records は各銘柄ごとの dict のリスト
```

- ニュース RSS を取得する（news_collector.fetch_rss）
```python
from kabusys.data.news_collector import fetch_rss

articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", "yahoo_finance")
for a in articles:
    print(a["id"], a["title"], a["datetime"])
```
注: fetch_rss は SSRF 対策や最大サイズ保護を実装しています。URL スキームは http/https のみです。

---

## 初期化・運用上の注意

- .env 自動ロード:
  - パッケージ import 時にプロジェクトルートを探して `.env` / `.env.local` を自動的に読み込みます。
  - テストなどで無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- Look-ahead バイアス回避:
  - LLM や ETL の各処理は内部で date 引数を明示的に受け取り、datetime.today() を直接参照しない実装方針です。バックテスト時には target_date を明示してください。
- リトライ / フェールセーフ:
  - 外部 API 呼び出し（OpenAI / J-Quants）はリトライロジックを備えていますが、API が利用不可の際には一部処理をスキップして継続する設計です（ログで通知）。
- DuckDB の executemany に関する注意:
  - 一部コードでは DuckDB のバージョンに対する互換性考慮（空リストの executemany を避ける等）があります。DuckDB のバージョン差異に注意してください。

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py
- ai/
  - __init__.py
  - news_nlp.py
  - regime_detector.py
- data/
  - __init__.py
  - calendar_management.py
  - etl.py
  - pipeline.py
  - stats.py
  - quality.py
  - audit.py
  - jquants_client.py
  - news_collector.py
  - (その他 jquants_client で使用されるユーティリティ)
- research/
  - __init__.py
  - factor_research.py
  - feature_exploration.py
- monitoring, execution, strategy 等（パッケージ定義に入るがここに含まれないモジュールも想定）

主要ファイルの役割:
- config.py: 環境変数の読み込み / Settings
- data/pipeline.py: 日次 ETL のエントリポイント (run_daily_etl, run_prices_etl 等)
- data/jquants_client.py: J-Quants API の取得・保存ロジック
- data/news_collector.py: RSS 取得・前処理・冪等保存
- ai/news_nlp.py: 銘柄別ニューススコア作成
- ai/regime_detector.py: マクロ + MA200 を合成した市場レジーム判定
- research/*.py: ファクター計算・特徴量解析ユーティリティ
- data/audit.py: 監査ログテーブル定義と初期化ユーティリティ

---

## 最後に

この README はコードベースからの要点をまとめたものです。実運用時は
- .env（および機密情報）の管理（Vault や Secrets Manager の利用）
- API レート制限に関する運用設計
- LLM 呼び出しコスト管理
- DuckDB ファイルのバックアップとスキーマ管理
に十分注意してください。

追加で README に含めたい具体的なコマンドやサンプル（例えば CI 用のスクリプト、Dockerfile、pyproject の例など）があれば教えてください。README を拡張して反映します。