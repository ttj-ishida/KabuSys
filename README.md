# KabuSys

日本株向けの自動売買 / データ基盤ライブラリ群です。  
ETL（J-Quants からのデータ取得）、ニュースの NLP スコアリング（OpenAI）、市場レジーム判定、研究用ファクター計算、監査ログスキーマなどを含むモジュール設計になっています。

## 概要

KabuSys は以下の役割を持つコンポーネントを提供します。

- J-Quants API からのデータ取得（株価・財務・カレンダー）
- DuckDB を用いたデータ保存・ETL パイプライン
- ニュース収集・NLP（OpenAI）による銘柄センチメント算出
- 市場レジーム判定（ETF MA とマクロニュースの合成）
- 研究用ファクター計算（モメンタム、ボラティリティ、バリュー等）
- データ品質チェック（欠損・スパイク・重複・日付整合性）
- 監査ログ（signal → order_request → executions）のスキーマ初期化

設計上、ルックアヘッドバイアスを避けるために日付参照の扱いに注意しており、外部 API 呼び出しは明示的な関数呼び出しで行います。

---

## 主な機能一覧

- data/
  - jquants_client: J-Quants API クライアント（取得・ページング・保存・トークン自動リフレッシュ・レート制御）
  - pipeline: 日次 ETL パイプライン（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - news_collector: RSS 取得・前処理・raw_news 保存（SSRF 対策、トラッキング除去）
  - news_nlp: OpenAI を使った銘柄別ニューススコアリング（score_news）
  - regime_detector: ETF MA とマクロニュースで市場レジームを算出（score_regime）
  - calendar_management: マーケットカレンダー管理（営業日判定、next/prev_trading_day など）
  - quality: データ品質チェック（欠損・スパイク・重複・日付不整合）
  - audit: 監査ログ（テーブル・インデックス定義、init_audit_db）
  - stats: 汎用統計ユーティリティ（zscore_normalize）
- research/
  - factor_research, feature_exploration: ファクター計算・前方リターン・IC 計算・統計サマリー
- ai/
  - news_nlp, regime_detector: OpenAI を使った NLP・レジーム判定ロジック
- config.py
  - 環境変数ロード（.env / .env.local の自動読み込み）、設定アクセス用オブジェクト settings

---

## 要件

最低限必要な外部パッケージ（抜粋）:

- Python 3.10+
- duckdb
- openai
- defusedxml

（実際のプロジェクトでは requirements.txt/pyproject.toml を参照してください。）

---

## セットアップ手順

1. リポジトリをクローン / コピー

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install duckdb openai defusedxml
   - （プロジェクトに pyproject.toml や requirements があればそれを使用）

4. 開発パッケージとしてインストール（任意）
   - pip install -e .

5. 環境変数の準備
   - プロジェクトルートに `.env` を配置すると自動的に読み込まれます（CWD ではなくパッケージファイル位置からプロジェクトルートを探索して読み込み）。
   - 自動ロードを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

必須または重要な環境変数（代表例）:
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- OPENAI_API_KEY: OpenAI API キー（score_news / score_regime 実行時に必要）
- KABU_API_PASSWORD: kabuステーション API パスワード（注文実行部分がある場合）
- DUCKDB_PATH: デフォルト data/kabusys.duckdb
- SQLITE_PATH: デフォルト data/monitoring.db

.env 例（.env.example を参照してください）:
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=your_kabu_password
DUCKDB_PATH=data/kabusys.duckdb
```

---

## 使い方（クイックスタート）

以下は主要なユースケースの簡単な使用例です。実行前に必要な環境変数や DB パスの準備を行ってください。

- DuckDB 接続を作って ETL を実行する（例: 日次 ETL）
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect('data/kabusys.duckdb')  # デフォルトのパスを使用
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュース NLP（銘柄スコア計上）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect('data/kabusys.duckdb')
# OPENAI_API_KEY は環境変数で指定するか api_key 引数に渡す
num_written = score_news(conn, target_date=date(2026, 3, 20))
print("書き込んだ銘柄数:", num_written)
```

- 市場レジームスコア算出
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect('data/kabusys.duckdb')
# OpenAI の API キーを env または api_key 引数で指定する必要あり
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ用 DB 初期化
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/monitoring_audit.duckdb")
# これで監査用テーブルが作成されます
```

- カレンダー判定ユーティリティ
```python
from datetime import date
import duckdb
from kabusys.data.calendar_management import is_trading_day, next_trading_day

conn = duckdb.connect('data/kabusys.duckdb')
d = date(2026, 3, 20)
print("is trading:", is_trading_day(conn, d))
print("next trading:", next_trading_day(conn, d))
```

---

## 設定（config.py のポイント）

- .env 自動ロード
  - プロジェクトルートにある `.env` / `.env.local` が自動的に読み込まれます。
  - 優先順位: OS 環境変数 > .env.local > .env
  - 自動ロード無効化: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

- settings オブジェクト
  - kabusys.config.settings を通じて設定値を取得できます（プロパティで lazy に取得）。
  - 例: settings.jquants_refresh_token, settings.duckdb_path, settings.env, settings.log_level

---

## ディレクトリ構成（主要ファイル）

以下はコードベースの主要ファイルと簡単な説明です。

- src/kabusys/
  - __init__.py
  - config.py — 環境変数読み込みと settings
  - ai/
    - __init__.py
    - news_nlp.py — ニュースの OpenAI スコアリング（score_news）
    - regime_detector.py — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント（fetch / save）
    - pipeline.py — ETL パイプライン（run_daily_etl 等）
    - etl.py — ETLResult エクスポート
    - news_collector.py — RSS 収集・前処理
    - calendar_management.py — マーケットカレンダー管理（is_trading_day など）
    - stats.py — zscore_normalize 等の統計ユーティリティ
    - quality.py — データ品質チェック（check_missing_data, check_spike, ...）
    - audit.py — 監査ログスキーマ初期化（init_audit_schema, init_audit_db）
  - research/
    - __init__.py
    - factor_research.py — モメンタム / ボラティリティ / バリュー計算
    - feature_exploration.py — 将来リターン計算 / IC / 統計サマリー

---

## 注意事項 / 設計上のポイント

- ルックアヘッドバイアス回避のため、関数は内部で datetime.today() を参照しない設計です（target_date を明示的に渡す方式を推奨）。
- OpenAI 呼び出しはリトライやレスポンス検証を実装していますが、API キーや呼び出し量に注意してください（コスト・レート制限）。
- J-Quants API はレート制限（120 req/min）に合わせたレートリミッタを実装しています。
- DuckDB を用いた保存処理は冪等（ON CONFLICT DO UPDATE）を意識しています。
- ニュース収集は SSRF 対策（ホスト検証、リダイレクト検査）や XML の安全パースを行っています（defusedxml 使用）。

---

## さらに進めるには

- production 実行や運用用の supervisor / systemd 起動スクリプトを用意するとよいです。
- モニタリング（CPU/メモリ/ディスク閾値）やプロセス監視は config の設定を参照して実装できます（settings.pid_file_path, kill_flag_path 等）。
- テスト時は環境変数自動ロードを無効化し、OpenAI 呼び出し等をモックすることで安定したテストが可能です。

---

必要であれば README にサンプル .env.example、詳細な API リファレンス、デプロイ手順（systemd, Dockerfile など）を追加します。欲しい項目を教えてください。