# KabuSys

日本株向けのデータプラットフォーム＋研究・AI・売買監査を統合した自動売買支援ライブラリです。  
ETL（J-Quants からのデータ取得）、ニュース収集・LLM によるニュースセンチメント、ファクター計算、マーケットレジーム判定、監査ログの初期化などを含みます。

---

## プロジェクト概要

KabuSys は以下の目的を持つモジュール群で構成されています。

- データ収集・ETL（J-Quants API 経由の株価/財務/カレンダー取得、RSS ニュース収集）
- データ品質チェック（欠損・スパイク・重複・日付整合性など）
- ニュースセンチメント（OpenAI を用いた銘柄別/マクロのスコアリング）
- 市場レジーム判定（ETF の MA とマクロセンチメントを合成）
- 研究用ファクター計算（モメンタム／バリュー／ボラティリティ等）と統計ユーティリティ
- 監査ログ（シグナル→発注→約定のトレーサビリティを確保する監査 DB）

設計上の共通方針：
- ルックアヘッドバイアスを避ける（内部で datetime.today()/date.today() を直接参照しない箇所あり）
- DuckDB を主要データストアとして利用（監査用 DB も DuckDB を想定）
- OpenAI（gpt-4o-mini）を JSON mode で呼び出し、レスポンスは厳密な JSON を期待
- 冪等性・フォールバック・リトライ・レート制御を重視

---

## 機能一覧

主な機能（モジュール単位）：

- kabusys.config
  - .env 自動ロード（プロジェクトルート基準）、環境変数設定管理、必須項目のチェック
- kabusys.data
  - ETL パイプライン（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - J-Quants クライアント（fetch / save の一括実装、認証ロジック、レート制御、リトライ）
  - RSS ニュース収集（SSRF 対策、トラッキングパラメータ除去、前処理）
  - market calendar 操作・営業日判定ユーティリティ
  - データ品質チェック（欠損、スパイク、重複、日付不整合）
  - 監査ログ初期化・インデックス作成（init_audit_schema / init_audit_db）
  - 汎用統計ユーティリティ（zscore_normalize）
- kabusys.ai
  - news_nlp.score_news: 銘柄ごとのニュースセンチメント算出 → ai_scores テーブルへ保存
  - regime_detector.score_regime: ETF (1321) の MA とマクロセンチメントを合成して market_regime へ保存
- kabusys.research
  - ファクター計算（calc_momentum, calc_value, calc_volatility）
  - 特徴量探索（calc_forward_returns, calc_ic, factor_summary, rank）
- その他
  - データ統計・正規化（kabusys.data.stats）
  - ETL 結果を表す ETLResult データクラス

---

## セットアップ手順

前提
- Python 3.9+（typing の一部新機能を使用）
- DuckDB を利用するため duckdb パッケージが必要
- OpenAI API を利用する場合は openai パッケージが必要
- RSS XML パースに defusedxml を使用

例: 仮想環境を作成して依存をインストールする

1. 仮想環境作成・アクティベート（例: venv）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 必要パッケージのインストール（例）
   - pip install duckdb openai defusedxml

   （プロジェクトとして配布する場合は pyproject / requirements.txt を参照して pip install -e . 等でインストールしてください）

3. 環境変数設定
   - プロジェクトルートに .env または .env.local を置くと自動で読み込まれます（os 環境変数が優先）。
   - 自動読み込みを無効化する場合: 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

必須の環境変数（最低限）
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（get_id_token に使用）
- KABU_API_PASSWORD: kabu ステーション API パスワード（実行系で使用）
- SLACK_BOT_TOKEN: Slack 通知用ボットトークン（通知機能を使う場合）
- SLACK_CHANNEL_ID: Slack チャンネル ID
- OPENAI_API_KEY: OpenAI API キー（AI モジュールを使う場合）

任意（デフォルトがある）
- KABUSYS_ENV: development / paper_trading / live（デフォルト development）
- LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト INFO）
- DUCKDB_PATH: data/kabusys.duckdb（デフォルト）
- SQLITE_PATH: data/monitoring.db（デフォルト）

サンプル .env（プロジェクトルート）
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
KABUSYS_ENV=development
LOG_LEVEL=INFO

---

## 使い方（簡単な例）

（以降は Python スクリプト/REPL からの呼び出し例）

- DuckDB 接続を作って ETL を実行する

```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメントをスコアリングして ai_scores テーブルへ書き込む

```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
written = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
print(f"書き込み銘柄数: {written}")
```

- 市場レジームを算出して market_regime テーブルへ書き込む

```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")
```

- 監査ログ用 DB を初期化する

```python
from kabusys.data.audit import init_audit_db
conn_audit = init_audit_db("data/audit.duckdb")
# conn_audit を使って監査テーブルへ書き込み可能
```

- カレンダー更新バッチを手動実行する

```python
from kabusys.data.calendar_management import calendar_update_job
import duckdb
from datetime import date

conn = duckdb.connect("data/kabusys.duckdb")
saved = calendar_update_job(conn)
print(f"保存レコード数: {saved}")
```

ポイント：
- 上記関数群は DuckDB の特定テーブル（raw_prices / raw_financials / raw_news / market_calendar / ai_scores / market_regime など）を前提に動きます。初期スキーマは ETL 実行前に別途用意するか、プロジェクトに含まれるスキーマ初期化ユーティリティを使用してください。
- OpenAI を使う関数は api_key 引数で明示的に渡すか、環境変数 OPENAI_API_KEY を設定してください。
- J-Quants の API 呼び出しは get_id_token / fetch_xxx 系を通じて行われ、内部でトークンのキャッシュ・自動リフレッシュ・レート制御を行います。

---

## ディレクトリ構成

この README は src 配下のパッケージ構成に基づきます（主要ファイルを抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                       : 環境変数 / .env 自動ロード、Settings
  - ai/
    - __init__.py                    : score_news エクスポート
    - news_nlp.py                    : ニュースセンチメント → ai_scores 書込
    - regime_detector.py             : マクロ + MA 合成による market_regime 判定
  - data/
    - __init__.py
    - jquants_client.py              : J-Quants API クライアント、保存関数（raw_prices/raw_financials/market_calendar）
    - pipeline.py                    : run_daily_etl 等 ETL パイプライン
    - etl.py                         : ETLResult の再エクスポート
    - calendar_management.py         : market_calendar 管理・営業日判定
    - news_collector.py              : RSS 取得・前処理・raw_news への保存
    - quality.py                     : データ品質チェック（欠損/スパイク/重複/日付不整合）
    - stats.py                       : zscore_normalize 等統計ユーティリティ
    - audit.py                       : 監査テーブル DDL / 初期化ユーティリティ
  - research/
    - __init__.py
    - factor_research.py             : calc_momentum / calc_value / calc_volatility
    - feature_exploration.py         : calc_forward_returns / calc_ic / factor_summary / rank

---

## 注意点・運用上のヒント

- .env 読み込み
  - 自動読み込みはプロジェクトルート（.git または pyproject.toml があるディレクトリ）を検出して行います。
  - 読み込み順序: OS 環境変数 > .env.local > .env
  - テストなどで自動ロードを止めるには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定
- LLM 呼び出し
  - レスポンスは厳密な JSON を期待しており、パース失敗時はフェイルセーフで中立（0.0）やスキップを行います。
  - レート制御・リトライは実装されていますが、API 使用量とコストには注意してください。
- DB スキーマ
  - ETL / 保存関数は既存スキーマ（テーブル）を前提に動作します。DuckDB にスキーマを作成する初期化手順を別途整備してください（audit.init_audit_db は監査テーブルの初期化を提供します）。
- テスト容易性
  - OpenAI など外部 API 呼び出しはモジュール内で抽象化され、テスト時は該当関数を patch して差し替えやすく設計されています。

---

もし README に追加したい内容（例: インストール方法の詳細、テーブルスキーマ定義、CI 実行手順、サンプルデータでのハンズオン手順など）があれば教えてください。必要に応じてサンプル .env.example や初期スキーマ SQL を追記します。