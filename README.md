# KabuSys

日本株向けの自動売買・データ基盤ライブラリ。J-Quants からのデータ取得（ETL）、ニュースの NLP スコアリング（OpenAI）、市場レジーム判定、研究用ファクター計算、監査ログ（オーダー/約定トレーサビリティ）などを提供します。

---

## プロジェクト概要

KabuSys は以下の機能を持つモジュール群から構成される Python パッケージです。

- J-Quants API を用いたデータ取得（株価日足・財務・マーケットカレンダー）
- DuckDB に対する ETL パイプライン（差分取得・保存・品質チェック）
- ニュース収集・NLP による銘柄センチメント評価（OpenAI）
- 市場レジーム判定（ETF MA とマクロニュースの混合スコア）
- 研究用ファクター計算（モメンタム/バリュー/ボラティリティ等）
- 監査ログ（signal / order_request / executions）スキーマ初期化ユーティリティ
- 各種ユーティリティ（カレンダー管理、データ品質チェック、統計ユーティリティなど）

設計上の特徴:
- Look-ahead バイアス対策（内部で date.today()/datetime.today() を不用意に参照しない等）
- 冪等（idempotent）な DB 操作（ON CONFLICT / INSERT ... DO UPDATE）
- 外部 API 呼び出しに対するリトライ・レート制御・フェイルセーフを組み込み

---

## 主な機能一覧

- data
  - ETL（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - J-Quants クライアント（fetch / save 系）
  - 市場カレンダー管理（is_trading_day / next_trading_day / calendar_update_job）
  - ニュース収集（RSS -> raw_news）
  - データ品質チェック（missing_data / spike / duplicates / date_consistency）
  - 監査ログスキーマ初期化（init_audit_schema / init_audit_db）
  - 統計ユーティリティ（zscore_normalize）
- ai
  - ニュース NLP（score_news: 銘柄別センチメントを ai_scores に保存）
  - レジーム判定（score_regime: market_regime テーブルへ書き込み）
- research
  - ファクター計算（calc_momentum, calc_value, calc_volatility）
  - 特徴量探索（calc_forward_returns, calc_ic, factor_summary, rank）
- config
  - 環境変数読み込み・管理（Settings クラス、.env 自動読み込み機能）

---

## 動作要件（依存）

最低限の依存ライブラリ（例）:
- Python 3.10+
- duckdb
- openai (OpenAI Python SDK)
- defusedxml

開発時に使われているその他の標準ライブラリ: urllib, json, datetime, logging など。

pip でのインストール例（仮）:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb openai defusedxml
# パッケージをローカルで編集しながら使う場合
pip install -e .
```

※ 実プロジェクトでは requirements.txt / pyproject.toml を利用して依存管理してください。

---

## セットアップ手順

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境作成・有効化（任意）
   ```
   python -m venv .venv
   source .venv/bin/activate  # Unix/macOS
   .\.venv\Scripts\activate   # Windows PowerShell
   ```

3. 必要パッケージをインストール
   ```
   pip install duckdb openai defusedxml
   # もしローカルでパッケージ化している場合
   pip install -e .
   ```

4. 環境変数 / .env の準備

   必須環境変数（少なくとも開発時に必要なもの）:
   - JQUANTS_REFRESH_TOKEN  (J-Quants のリフレッシュトークン)
   - KABU_API_PASSWORD      (kabuステーション API パスワード)
   - SLACK_BOT_TOKEN        (Slack 通知に使う Bot トークン)
   - SLACK_CHANNEL_ID       (Slack 通知先チャンネルID)

   任意 / デフォルト有り:
   - KABUSYS_ENV            (development | paper_trading | live) デフォルト: development
   - LOG_LEVEL              (DEBUG/INFO/...) デフォルト: INFO
   - DUCKDB_PATH            (例: data/kabusys.duckdb) デフォルトあり
   - SQLITE_PATH            (例: data/monitoring.db) デフォルトあり

   .env 例:
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   DUCKDB_PATH=data/kabusys.duckdb
   ```

   Notes:
   - パッケージ起動時に .env / .env.local を自動読み込みします（プロジェクトルート検出: .git または pyproject.toml）。自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト時に便利です）。

5. DB ディレクトリ作成等
   - DUCKDB_PATH の親フォルダを作成しておくと安全です（いくつかのユーティリティは自動作成しますが念のため）。

---

## 使い方（例）

以下はいくつかの典型的な操作例です。これらは Python スクリプトや REPL で実行します。

1) DuckDB 接続を開いて日次 ETL を実行する
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

# DuckDB ファイルに接続（ファイルがなければ作成されます）
conn = duckdb.connect("data/kabusys.duckdb")

# ETL を実行（target_date を省略すると今日）
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

2) ニュース NLP（銘柄別スコア）を実行（OpenAI API キーが必要）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
# 環境変数 OPENAI_API_KEY を設定している場合 api_key 引数は省略可
n = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
print(f"scored {n} codes")
```

3) 市場レジーム判定を実行
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

4) 監査ログ（audit）DB を初期化する
```python
from kabusys.data.audit import init_audit_db

# ":memory:" でインメモリ DB、またはファイルパスを指定
conn = init_audit_db("data/audit.duckdb")
# conn は duckdb.DuckDBPyConnection
```

5) 研究用ファクター計算の呼び出し例
```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum

conn = duckdb.connect("data/kabusys.duckdb")
records = calc_momentum(conn, target_date=date(2026, 3, 20))
# records は dict のリスト [{"date": ..., "code": "1301", "mom_1m": ..., ...}, ...]
```

---

## 主要 API / エントリポイント一覧（抜粋）

- kabusys.config.settings — 環境設定アクセス（例: settings.jquants_refresh_token）
- kabusys.data.pipeline.run_daily_etl(...) — 日次 ETL のメイン
- kabusys.data.jquants_client.fetch_daily_quotes(...) / save_daily_quotes(...) — J-Quants API クライアント
- kabusys.data.calendar_management.* — 営業日判定・更新ジョブ
- kabusys.ai.news_nlp.score_news(...) — ニュース NLP スコア生成（ai_scores へ書き込み）
- kabusys.ai.regime_detector.score_regime(...) — 市場レジーム判定（market_regime へ書き込み）
- kabusys.data.audit.init_audit_db(...) / init_audit_schema(...) — 監査ログ初期化

---

## 注意点 / 運用上のメモ

- OpenAI / J-Quants の API キーは必須です（実行時に ValueError が出ます）。環境変数: OPENAI_API_KEY, JQUANTS_REFRESH_TOKEN を設定してください。
- 外部 API 呼び出しはリトライやレート制御を行いますが、キーやネットワークが正しくないと処理はスキップ／0件返却になります。ログを確認してください。
- DuckDB の executemany に空リストを渡すとエラーになるバージョンがあるため、コード内で保護されています（空チェック済み）。
- Look-ahead バイアス防止のため、多くの関数は target_date 引数を受け、内部で未来データを参照しないよう設計されています。バックテスト等では過去データのみを用いる運用を心がけてください。
- 自動で .env を読み込む機構があります（プロジェクトルートを .git や pyproject.toml で検出）。テストなどで無効化したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## ディレクトリ構成

パッケージの主要なファイル／ディレクトリ構成（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py           # ニュース NLP スコアリング
    - regime_detector.py    # 市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py     # J-Quants API クライアント（fetch / save）
    - pipeline.py           # ETL パイプライン（run_daily_etl 等）
    - etl.py                # ETLResult エクスポート
    - calendar_management.py# マーケットカレンダー管理
    - news_collector.py     # RSS 収集
    - quality.py            # データ品質チェック
    - stats.py              # 汎用統計ユーティリティ
    - audit.py              # 監査ログスキーマ初期化
  - research/
    - __init__.py
    - factor_research.py    # ファクター計算
    - feature_exploration.py# 将来リターン / IC / 統計サマリー

各モジュールは docstring に詳細な仕様や設計方針が記載されています。まずは該当モジュールの docstring を参照してください。

---

## トラブルシューティング

- 「環境変数が設定されていません」というエラー:
  - .env を作成して必要なキーを設定するか、環境変数をエクスポートしてください。
- OpenAI API 呼び出しで 401/429/5xx が発生:
  - ライブラリ内でリトライ処理があります。API キー/レート制限/ネットワークを確認してください。
- DuckDB 関連のエラー:
  - 接続先パスやパーミッション、テーブルスキーマが正しいか確認してください。

---

README はここまでです。実際の運用／デプロイ時は、プロジェクトの pyproject.toml / requirements.txt に合わせて依存管理と CI を整備してください。必要であれば README に CLI 実行コマンドや systemd / cron ジョブの例、Slack 通知フローなどの追加も作成します。必要なら教えてください。