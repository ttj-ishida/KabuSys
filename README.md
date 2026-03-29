# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ。  
ETL（J-Quants からのデータ取得）、ニュースの NLP スコアリング、マーケットレジーム判定、リサーチ向けファクター計算、監査ログ管理などのユーティリティを提供します。

---

## 概要

KabuSys は日本株のデータ収集・品質チェック・特徴量生成・AI を用いたニュースセンチメント評価・監査ログ生成から発注に至るワークフローを支援するモジュール群です。  
主に以下の用途を想定しています：

- J-Quants API からの株価・財務・カレンダー等の差分 ETL（DuckDB に保存）
- RSS ベースのニュース収集と OpenAI による銘柄ごとのセンチメント評価
- ETF ベースの市場レジーム判定（MA + マクロニュースを融合）
- リサーチ用ファクター計算（momentum / volatility / value 等）
- 監査ログ（signal → order_request → executions）のスキーマ初期化・管理
- データ品質チェック（欠損・スパイク・重複・日付不整合）

---

## 主な機能一覧

- data
  - ETL パイプライン（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - J-Quants クライアント（fetch / save 系）
  - 市場カレンダー管理（is_trading_day / next_trading_day / get_trading_days / calendar_update_job）
  - ニュース収集（RSS → raw_news / news_symbols 更新）
  - データ品質チェック（missing / spike / duplicates / date consistency）
  - 監査ログ初期化（init_audit_schema / init_audit_db）
  - 汎用統計ユーティリティ（zscore_normalize）
- ai
  - ニュース NLP（score_news：銘柄ごとのセンチメントを ai_scores テーブルへ）
  - 市場レジーム判定（score_regime：ETF 1321 の MA とマクロ NLP を融合）
- research
  - ファクター計算（calc_momentum / calc_volatility / calc_value）
  - 特徴量探索（calc_forward_returns / calc_ic / factor_summary / rank）
- config
  - 環境変数管理（Settings クラス、.env 自動ロード機構）

---

## 要件

- Python 3.10+
- 主要依存パッケージ（例）:
  - duckdb
  - openai
  - defusedxml
- その他標準ライブラリ（urllib, json, datetime, logging など）

インストール時にプロジェクトの requirements.txt / pyproject.toml を用意してください。

---

## インストール（開発環境例）

1. 仮想環境を作成・有効化（任意）:
   python -m venv .venv
   source .venv/bin/activate

2. 必要パッケージをインストール（例）:
   pip install duckdb openai defusedxml

3. パッケージを編集可能モードでインストール（プロジェクトルートに pyproject.toml ある想定）:
   pip install -e .

---

## 環境変数（主なもの）

KabuSys は .env / .env.local を自動でプロジェクトルートから読み込みます（.git または pyproject.toml を基準）。自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

必須（Settings で require されるもの）:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID — Slack 通知先チャンネル ID

任意（デフォルト値あり / 環境で上書き可能）:
- KABUSYS_ENV — "development" / "paper_trading" / "live"（デフォルト: development）
- LOG_LEVEL — "DEBUG" / "INFO" / "WARNING" / "ERROR" / "CRITICAL"（デフォルト: INFO）
- KABU_API_BASE_URL — kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH — データベースパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — モニタリング用 SQLite（デフォルト: data/monitoring.db）
- OPENAI_API_KEY — OpenAI 呼び出し用キー（ai.score_news / ai.regime_detector に使用）

例 .env:
JQUANTS_REFRESH_TOKEN=xxxx
OPENAI_API_KEY=sk-...
KABUS_API_PASSWORD=...

---

## 自動 .env 読み込みの挙動

- 読み込み順: OS 環境変数 > .env.local > .env
- プロジェクトルートを .git/pyproject.toml から探索。見つからない場合は自動読み込みをスキップ。
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動読み込みを無効化。

---

## セットアップ手順（簡易）

1. 必要な環境変数を設定（例: .env をプロジェクトルートに用意）
2. DuckDB ファイルの配置先ディレクトリを作成（例: data/）
3. 必要であれば監査 DB を初期化:
   - Python REPL / スクリプトで:
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")

4. ETL を実行するためのスクリプトを作成する（以下 Usage を参照）

---

## 使い方（例）

- DuckDB 接続を作り、日次 ETL を実行する:

```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースのセンチメントスコアを付与する（OpenAI API Key を環境変数に設定）:

```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # 環境変数 OPENAI_API_KEY を使用
print(f"written {n_written} scores")
```

- 市場レジームをスコアリングする:

```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

- 監査ログスキーマを初期化:

```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# conn を使って監査テーブルにアクセスできます
```

- リサーチ用ファクター計算例:

```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

conn = duckdb.connect("data/kabusys.duckdb")
momentum = calc_momentum(conn, date(2026,3,20))
vol = calc_volatility(conn, date(2026,3,20))
value = calc_value(conn, date(2026,3,20))
```

---

## 注意点 / 設計上の留意点

- ルックアヘッドバイアス回避:
  - 日付参照に datetime.today() / date.today() をむやみに使わず、target_date を明示して処理します（ETL / スコアリング関数は target_date 引数で制御）。
- OpenAI 呼び出し:
  - API 呼び出しはリトライ・バックオフ・レスポンスバリデーション付きで実装されています。API 失敗時は安全側にフォールバック（多くのケースでスコア 0.0）し、例外を全体に波及させない設計です。
- J-Quants クライアント:
  - レート制限（120 req/min）を守る RateLimiter と、401 時のトークン自動リフレッシュを備えています。
- ニュース収集:
  - SSRF 対策、受信サイズ制限、XML パースに defusedxml を使用するなどセキュリティ対策を施しています。
- DuckDB との相互作用:
  - executemany の空リスト処理や日付型変換等、DuckDB の仕様差に注意する実装になっています。

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
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
  - news_collector.py
  - calendar_management.py
  - quality.py
  - stats.py
  - audit.py
- research/
  - __init__.py
  - factor_research.py
  - feature_exploration.py

（上記は本リポジトリに含まれる主要モジュールを抜粋した一覧です）

---

## よくある運用フロー例

1. 毎朝（夜間バッチ）に run_daily_etl を実行して prices / financials / calendar を更新
2. ETL 後に run_all_checks でデータ品質を確認し、問題があれば運用アラート
3. 指定ウィンドウの raw_news を収集し、score_news で銘柄別 ai_scores を更新
4. score_regime で当日市場レジームを判定し戦略パラメータを切り替え
5. 戦略層で生成したシグナルは監査テーブルに保存、order_request_id を用いて発注ロジックと連携

---

## サポート / 追加情報

- 各モジュールの docstring に設計方針・注意点を詳細に記載しています。コードベースを参照してください。
- テスト時は自動 .env ロードを無効化するか、関数の内部 API 呼び出しをモックしてください（news_nlp / regime_detector は _call_openai_api を patch 可能）。
- DuckDB のスキーマ定義や初期化手順は data.audit.init_audit_schema 等を用いて行えます。

---

README は以上です。必要であればサンプルスクリプトや .env.example、pyproject.toml / requirements.txt のテンプレートも作成しますか？