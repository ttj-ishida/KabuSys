# KabuSys — 日本株自動売買 / データ & リサーチ基盤

KabuSys は日本株向けのデータプラットフォーム・リサーチ・自動売買のユーティリティ群です。  
DuckDB ベースのデータレイク、J-Quants 経由の ETL、ニュース収集・NLP（OpenAI）を使ったスコアリング、ファクター計算、監査ログ（トレーサビリティ）などを含みます。

以下はこのリポジトリの主要機能、セットアップ、基本的な使い方、ディレクトリ構成の説明です。

---

目次
- プロジェクト概要
- 機能一覧
- 必要条件 / 依存ライブラリ
- 環境変数
- セットアップ手順
- 使い方（主要 API の例）
- ディレクトリ構成
- 補足・設計上の注意

---

## プロジェクト概要

- データ取得：J-Quants API から株価（日足）・財務データ・JPX カレンダーを差分取得して DuckDB に保存する ETL パイプライン。
- データ品質：欠損・重複・日付不整合・スパイク検出を行う品質チェック。
- ニュース収集：RSS からニュースを収集し raw_news に保存、銘柄との紐付けを行う。
- ニュース NLP：OpenAI（gpt-4o-mini）を用いて銘柄単位のニュースセンチメントを算出し ai_scores に保存。
- レジーム判定：ETF（1321）の200日移動平均乖離とマクロニュースの LLM センチメントを組み合わせて日次の市場レジームを判定・保存。
- 監査ログ：シグナル → 注文要求 → 約定に至るトレーサビリティ用の監査スキーマ（DuckDB）を初期化するユーティリティ。
- 研究用ユーティリティ：ファクター（モメンタム／バリュー／ボラティリティなど）、将来リターン、IC 等の解析関数。

---

## 機能一覧（主要）

- data/
  - ETL：run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl
  - J-Quants クライアント（fetch / save）
  - カレンダー管理（is_trading_day, next_trading_day 等）
  - ニュース収集（RSS -> raw_news）
  - 品質チェック（missing / spike / duplicates / date consistency）
  - 監査ログ初期化（init_audit_schema / init_audit_db）
  - 汎用統計（zscore_normalize）
- ai/
  - score_news(conn, target_date, api_key=None)：銘柄毎ニュースセンチメントを計算して ai_scores に保存
  - score_regime(conn, target_date, api_key=None)：市場レジームを計算して market_regime に保存
- research/
  - ファクター計算（calc_momentum, calc_value, calc_volatility）
  - 特徴量探索（calc_forward_returns, calc_ic, factor_summary, rank）
- config.py
  - 環境変数読み込み（.env / .env.local 自動ロード）
  - settings オブジェクト経由で設定値を取得

---

## 必要条件 / 依存ライブラリ

（このリポジトリに requirements ファイルがない場合は下記をインストールしてください）

- Python 3.10+（型注釈に union | 使用のため）
- duckdb
- openai (OpenAI の公式 SDK)
- defusedxml
- （標準ライブラリのみで実装されている機能も多いです）

例：
pip install duckdb openai defusedxml

---

## 環境変数

このプロジェクトは複数の機密情報や設定を環境変数で取得します。必須項目は Settings クラスのプロパティ参照を参照してください。主なもの：

- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- KABU_API_BASE_URL — kabu API のベース URL（省略時: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID — Slack チャンネル ID（必須）
- DUCKDB_PATH — DuckDB データベースファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト data/monitoring.db）
- OPENAI_API_KEY — OpenAI API キー（ai.score_news / score_regime で利用）
- KABUSYS_ENV — 動作環境 ("development", "paper_trading", "live")（デフォルト development）
- LOG_LEVEL — ログレベル ("DEBUG","INFO",...）（デフォルト INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env ロードを無効化（1 を設定）

自動読み込み:
- パッケージはプロジェクトルート（.git または pyproject.toml のある親ディレクトリ）を探索し、見つかればルートの .env を読み込み、その後 .env.local を上書きして環境変数を設定します（OS 環境変数は保護され上書きされません）。
- 自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## セットアップ手順（ローカル）

1. 仮想環境を作成・有効化（例）
   python -m venv .venv
   source .venv/bin/activate  # macOS/Linux
   .venv\Scripts\activate     # Windows

2. 必要パッケージをインストール
   pip install duckdb openai defusedxml

   （プロジェクトによっては他のパッケージが必要になることがあります。requirements.txt がある場合はそれを使用してください。）

3. 環境変数を設定
   プロジェクトルートに .env ファイルを作成するか、環境変数を直接設定します。
   例 (.env):
   JQUANTS_REFRESH_TOKEN=あなたのリフレッシュトークン
   OPENAI_API_KEY=sk-...
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   KABUSYS_ENV=development
   DUCKDB_PATH=data/kabusys.duckdb

4. DuckDB ファイルが保存されるディレクトリを作成（必要なら）
   mkdir -p data

5. （初回のみ）監査ログ DB の初期化（必要に応じて）
   Python レベルで init_audit_db を呼び出して監査用DBを作成できます（例を下記に示します）。

---

## 使い方（簡単なコード例）

※ 全ての関数は DuckDB の接続オブジェクト（duckdb.connect(...) が返す接続）を受け取ります。

- DuckDB に接続する
```python
import duckdb
conn = duckdb.connect("data/kabusys.duckdb")
```

- 日次 ETL を実行する
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=date(2026,3,20))
print(result.to_dict())
```

- ニュースセンチメントを算出して ai_scores に書き込む
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

# api_key を引数で渡すか、環境変数 OPENAI_API_KEY を設定する
n_written = score_news(conn, target_date=date(2026,3,20), api_key=None)
print("書き込み銘柄数:", n_written)
```

- 市場レジームを算出して market_regime に書き込む
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026,3,20), api_key=None)
```

- 監査ログスキーマを初期化（プロジェクト内の監査用 DB を作る）
```python
from kabusys.data.audit import init_audit_db
conn_audit = init_audit_db("data/audit.db")
# conn_audit は初期化済みの DuckDB 接続
```

- ファクター計算（研究用）
```python
from kabusys.research.factor_research import calc_momentum
from datetime import date

records = calc_momentum(conn, target_date=date(2026,3,20))
# records は各銘柄ごとの dict のリスト
```

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys パッケージの主なファイル・モジュール構成です（抜粋）:

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
    - etl.py (ETLResult 再エクスポート)
    - news_collector.py
    - calendar_management.py
    - quality.py
    - stats.py
    - audit.py
    - (その他補助モジュール)
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - research のユーティリティは data.stats を参照する設計です

（リポジトリ全体に他のスクリプトや設定ファイルが存在する可能性があります。上は提供コードベースから抽出した主要モジュールです。）

---

## 補足・設計上の注意

- Look-ahead バイアス対策：多くの処理（ETL / AI スコアリング / レジーム判定 / ファクター計算）は内部で date を外から与える方式を取り、date.today() を直接参照しない設計になっています。バックテストでの利用に配慮した設計です。
- 冪等性：J-Quants からの保存処理（save_*）や監査スキーマの初期化は冪等（ON CONFLICT）を意識して実装されています。
- フェイルセーフ：AI 呼び出し失敗や一時的 API エラー時には、スコアを 0.0 にフォールバックする、または部分成功で処理を続行する実装になっています。
- 環境変数自動ロード：config モジュールは .git または pyproject.toml を基準にプロジェクトルートを探し、.env → .env.local の順に自動的に読み込みます。テスト等で無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定します。

---

必要であれば README に「運用手順（cron / Airflow / systemd などによる定期 ETL 実行例）」「SQL スキーマ（raw_prices / raw_financials / raw_news 等）」「.env.example のテンプレート」や、より詳細な API リファレンス（関数ごとの引数/戻り値/例外）を追加できます。どの情報を優先して追加しますか？