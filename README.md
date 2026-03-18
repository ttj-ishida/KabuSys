# KabuSys

日本株向けの自動売買・データ基盤ライブラリです。  
J-Quants / RSS 等からデータを取得し、DuckDB に保存・整形し、研究（ファクター計算）・戦略実行・監査までを想定したモジュール群を提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は以下の目的で設計された Python パッケージです。

- J-Quants API から株価・財務・マーケットカレンダーを安全に取得するクライアント
- RSS を収集してニュースを前処理・保存するニュースコレクタ
- DuckDB を利用したデータスキーマと ETL（差分取得・品質チェック）
- ファクター（モメンタム・ボラティリティ・バリュー等）計算と研究ユーティリティ
- 発注・監査（audit）用スキーマを含む実行・監視基盤の骨組み

設計のポイント:
- 外部依存を最小化（多くのモジュールは標準ライブラリのみで実装）
- DuckDB を中心にした三層（Raw / Processed / Feature）スキーマ
- 冪等性（ON CONFLICT）やレートリミット／リトライなどの堅牢性考慮
- Look-ahead Bias を防ぐ fetched_at トレーサビリティ

---

## 機能一覧（主要モジュール）

- kabusys.config
  - .env 自動読み込み（プロジェクトルート検出: .git または pyproject.toml）
  - 必須環境変数チェック（settings オブジェクト）
- kabusys.data.jquants_client
  - J-Quants API クライアント（ページネーション・トークン自動リフレッシュ・リトライ）
  - fetch / save の一対で冪等保存（raw_prices, raw_financials, market_calendar 等）
- kabusys.data.news_collector
  - RSS 収集・前処理・SSRF/サイズ制限/トラッキング除去・DuckDB 保存（raw_news, news_symbols）
- kabusys.data.schema
  - DuckDB スキーマ定義（Raw/Processed/Feature/Execution/Audit）と初期化関数 init_schema()
- kabusys.data.pipeline
  - 日次 ETL 実行 run_daily_etl（差分取得 + 品質チェック + 保存）
  - 個別 ETL ジョブ（prices, financials, calendar）
- kabusys.data.quality
  - データ品質チェック（欠損、重複、スパイク、日付不整合）
- kabusys.data.calendar_management
  - market_calendar の管理、営業日判定、next/prev_trading_day 等
- kabusys.research
  - ファクター計算: calc_momentum, calc_volatility, calc_value
  - 特徴量探索: calc_forward_returns, calc_ic, factor_summary, rank
  - 統計ユーティリティ: zscore_normalize
- kabusys.data.audit
  - 発注〜約定〜監査のためのテーブル定義と初期化ヘルパー

---

## セットアップ手順

前提
- Python 3.10 以上を推奨（型ヒントと PEP 604 の union 表記を使用）
- DuckDB を利用します（pip パッケージ duckdb）
- defusedxml をニュース収集で利用

1. 仮想環境作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 必要パッケージをインストール
   - 例:
     pip install duckdb defusedxml

   （プロジェクトに requirements.txt / pyproject.toml があればそちらを使ってください）

3. 開発インストール（プロジェクトルートに setup/pyproject がある前提）
   - pip install -e .

4. 環境変数の設定
   - プロジェクトルート（.git または pyproject.toml のある場所）に .env / .env.local を置くと自動で読み込まれます。
   - 自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト等で使用）。

必須環境変数（settings 参照）:
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
- KABU_API_PASSWORD: kabuステーション API パスワード
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID: Slack 通知先チャンネル ID

任意（デフォルトあり）:
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db)
- KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL: DEBUG/INFO/...（デフォルト: INFO）

例 .env テンプレート:
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C12345678
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 使い方（簡単な例）

Python REPL やスクリプトからライブラリを利用できます。以下は代表的な使い方の抜粋です。

1) DuckDB スキーマ初期化
```python
from kabusys.data import schema
# ファイルに DB を作成（親ディレクトリを自動作成）
conn = schema.init_schema("data/kabusys.duckdb")
```

2) 日次 ETL 実行（J-Quants から差分取得して保存・品質チェック）
```python
from kabusys.data.pipeline import run_daily_etl
result = run_daily_etl(conn)  # target_date を指定可能
print(result.to_dict())
```

3) ニュース収集ジョブ実行（既知銘柄セットを渡して銘柄紐付け）
```python
from kabusys.data.news_collector import run_news_collection
# known_codes は価格データ等から取得した有効な銘柄コード集合
known_codes = {"7203", "6758", "9984"}  # 例
res = run_news_collection(conn, known_codes=known_codes)
print(res)  # {source_name: 新規保存件数}
```

4) 研究・ファクター計算
```python
from kabusys.research import calc_momentum, calc_volatility, calc_value
from datetime import date

d = date(2024, 1, 31)
mom = calc_momentum(conn, d)
vol = calc_volatility(conn, d)
val = calc_value(conn, d)

# z-score 正規化
from kabusys.data.stats import zscore_normalize
normed = zscore_normalize(mom, ["mom_1m", "mom_3m", "mom_6m"])
```

5) 監査スキーマ初期化（発注/約定用）
```python
from kabusys.data.audit import init_audit_db
audit_conn = init_audit_db("data/audit.duckdb")
```

注意:
- jquants_client は内部でレート制限／リトライ／トークンリフレッシュを行います。API の利用は必ず settings に有効なトークンを設定してから実行してください。
- ETL・ニュース収集は I/O / ネットワークを伴うため、ログや例外を適切に監視してください。

---

## ディレクトリ構成

（プロジェクトの src/ 以下を抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py                        — 環境変数 / 設定管理（settings オブジェクト）
    - data/
      - __init__.py
      - jquants_client.py              — J-Quants API クライアント（fetch / save）
      - news_collector.py              — RSS ニュース収集・前処理・保存
      - schema.py                      — DuckDB スキーマ定義 & init_schema
      - pipeline.py                    — ETL パイプライン（run_daily_etl 等）
      - quality.py                     — データ品質チェック
      - stats.py                       — 統計ユーティリティ（zscore_normalize）
      - features.py                    — 特徴量ユーティリティ再エクスポート
      - calendar_management.py         — 市場カレンダー管理（営業日判定等）
      - etl.py                         — ETL 用公開型（ETLResult 等）
      - audit.py                       — 監査ログ（発注/約定）スキーマ初期化
    - research/
      - __init__.py
      - factor_research.py             — モメンタム/ボラ/バリュー計算
      - feature_exploration.py         — forward return / IC / summary 等
    - strategy/                         — 戦略層（骨組み）
      - __init__.py
    - execution/                        — 発注・約定処理（骨組み）
      - __init__.py
    - monitoring/                       — 監視用モジュール（骨組み）

---

## 補足・運用上の注意

- 環境変数の自動ロードはプロジェクトルートの検出 (.git または pyproject.toml) に依存します。CI・テストでは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自前で環境設定を行うと安定します。
- DuckDB のファイルはデフォルトで data/kabusys.duckdb に作成します。運用環境では適切な永続ストレージパスに変更してください。
- J-Quants のレート制限（120 req/min）に従うよう実装されていますが、大量データ取得時は API 利用ルールを再確認してください。
- ニュース収集は外部 URL を解釈するため、SSRF 対策・最大受信サイズ等の安全対策が組み込まれています。実行環境のネットワークポリシーにも注意してください。
- production（live）環境では実際の発注処理が動く可能性があるため、KABUSYS_ENV を正しく設定して paper_trading / live の区別を行ってください。

---

## 参考（よく使う API）

- settings
  - from kabusys.config import settings
  - settings.jquants_refresh_token, settings.duckdb_path, settings.env, settings.is_live など

- DB スキーマ
  - from kabusys.data import schema
  - conn = schema.init_schema(settings.duckdb_path)

- ETL
  - from kabusys.data.pipeline import run_daily_etl
  - result = run_daily_etl(conn)

- 研究系
  - from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic

---

もし README に追加したい具体的な実行例（cron 設定、Dockerfile、CI ワークフロー等）があれば教えてください。必要に応じて .env.example や運用手順のテンプレートも作成します。