# KabuSys

日本株向けの自動売買システムの基盤ライブラリ（KabuSys）。  
データ取得・ETL・データ品質チェック・特徴量生成・リサーチユーティリティ・監査ログなど、戦略開発と運用に必要な共通機能を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は下記の目的を持つモジュール群を含む Python パッケージです。

- J-Quants API から株価・財務・市場カレンダーを安全かつ効率的に取得し、DuckDB に冪等的に保存する（例: ON CONFLICT 句を利用）。
- ETL パイプライン (差分取得、バックフィル、品質チェック) を提供。
- ニュース RSS の収集、前処理、記事→銘柄紐付け（SSRF 対策、サイズ制限、トラッキングパラメータ除去）。
- 研究用ファクター計算（モメンタム、バリュー、ボラティリティ等）と統計ユーティリティ（Z スコア正規化、IC 計算など）。
- 監査ログ用スキーマ（シグナル→発注→約定のトレース）を提供。
- 設定は .env または環境変数で管理。自動ロードロジックと保護機構あり。

設計上の重要点：
- DuckDB をデータレイヤに採用（オンディスク／インメモリ両対応）。
- 外部依存は必要最小限（`duckdb`, `defusedxml` 等）。
- レート制限・リトライ・トークンリフレッシュ・SSRF 対策など運用上の安全設計を重視。

---

## 主な機能一覧

- 環境変数管理: 自動 .env ロード、必須値チェック（kabusys.config）
- J-Quants クライアント: レート制御・リトライ・ページネーション・トークン自動更新（kabusys.data.jquants_client）
- DuckDB スキーマ初期化: data.schema.init_schema / init_audit_db
- ETL パイプライン: 日次 ETL（run_daily_etl）、個別 ETL ジョブ（prices/financials/calendar）
- データ品質チェック: 欠損・重複・スパイク・日付不整合（kabusys.data.quality）
- ニュース収集・保存: RSS 取得・安全検証・正規化・DB 保存（kabusys.data.news_collector）
- 特徴量計算: momentum/volatility/value（kabusys.research.factor_research）
- 研究用ユーティリティ: 将来リターン計算、IC（Spearman）計算、統計サマリー（kabusys.research.feature_exploration）
- 統計ユーティリティ: Zスコア正規化（kabusys.data.stats）
- 監査ログスキーマ: signal_events / order_requests / executions（kabusys.data.audit）

---

## セットアップ手順

前提
- Python 3.10 以上（コードは `|` 型合併や型注釈を使用）
- duckdb
- defusedxml

1. 仮想環境作成（任意）
   ```
   python -m venv .venv
   source .venv/bin/activate  # Unix/macOS
   .venv\Scripts\activate     # Windows
   ```

2. 依存インストール（例）
   ```
   pip install duckdb defusedxml
   ```

3. パッケージを開発インストール（プロジェクトルートに setup/pyproject がある前提）
   ```
   pip install -e .
   ```

4. 環境変数設定
   - プロジェクトルートに `.env` / `.env.local` を置くと自動読み込みされます（既存 OS 環境変数は保護）。
   - 自動ロードを無効化する場合:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```

推奨される環境変数（.env の例）
```
# J-Quants
JQUANTS_REFRESH_TOKEN=your_refresh_token

# kabuステーション API
KABU_API_PASSWORD=your_kabu_password
KABU_API_BASE_URL=http://localhost:18080/kabusapi

# Slack (通知用)
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567

# DB パス
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db

# 実行環境
KABUSYS_ENV=development   # development|paper_trading|live
LOG_LEVEL=INFO
```

---

## 使い方

以下は主要なユースケースのサンプルコード例です。環境変数は事前に設定しておいてください。

1) DuckDB スキーマ初期化
```python
from kabusys.data.schema import init_schema
from kabusys.config import settings

# ファイルパスは settings.duckdb_path を利用する例
conn = init_schema(settings.duckdb_path)
```

- インメモリ DB を使う場合:
```python
conn = init_schema(":memory:")
```

2) 日次 ETL の実行（市場カレンダー → 株価 → 財務 → 品質チェック）
```python
from kabusys.data.pipeline import run_daily_etl
from kabusys.data.schema import init_schema
from kabusys.config import settings
from datetime import date

conn = init_schema(settings.duckdb_path)
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

3) ニュース収集ジョブの実行
```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
# known_codes は銘柄コードセット。None だと抽出をスキップ
res = run_news_collection(conn, sources=None, known_codes={"7203", "6758"})
print(res)
```

4) 研究用ファクター計算（モメンタム等）
```python
from kabusys.research import calc_momentum, calc_volatility, calc_value
from kabusys.data.schema import get_connection
from datetime import date

conn = get_connection("data/kabusys.duckdb")
records = calc_momentum(conn, target_date=date(2025, 1, 31))
# records は [{ "date": ..., "code": "7203", "mom_1m": ..., ...}, ...]
```

5) 将来リターン・IC 計算
```python
from kabusys.research import calc_forward_returns, calc_ic
# forward_records = calc_forward_returns(conn, target_date, horizons=[1,5,21])
# factor_records = ... (calc_momentum 等の出力)
ic = calc_ic(factor_records, forward_records, factor_col="mom_1m", return_col="fwd_1d")
```

6) J-Quants の個別 API 呼び出し（テスト・開発用）
```python
from kabusys.data.jquants_client import fetch_daily_quotes
# トークンを明示的に渡すか、settings から自動取得
quotes = fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,12,31))
```

注意点:
- jquants_client は API レート制限（120 req/min）を内蔵の RateLimiter で順守します。
- HTTP 429/408/5xx に対する指数バックオフとリトライを実装しています。
- 401 を受けた場合はトークン自動リフレッシュを行い1回リトライします。

---

## 主要モジュールとディレクトリ構成

プロジェクト（src/kabusys）内の主なファイルとディレクトリ:

- src/kabusys/__init__.py
- src/kabusys/config.py
  - 環境変数の自動読み込み・検証（JQUANTS_REFRESH_TOKEN 等）
- src/kabusys/data/
  - jquants_client.py      : J-Quants API クライアント（取得・保存）
  - news_collector.py     : RSS 収集・正規化・DB 保存
  - schema.py             : DuckDB スキーマ定義・初期化
  - stats.py              : 統計ユーティリティ（zscore_normalize 等）
  - pipeline.py           : ETL パイプライン（run_daily_etl 等）
  - features.py           : 特徴量ユーティリティ公開（zscore の再エクスポート）
  - calendar_management.py: 市場カレンダー管理・更新ジョブ
  - audit.py              : 監査ログスキーマの初期化
  - etl.py                : ETL 結果型エクスポート
  - quality.py            : データ品質チェック
- src/kabusys/research/
  - feature_exploration.py: 将来リターン・IC・summary 等
  - factor_research.py    : momentum/volatility/value の計算
  - __init__.py           : 研究ユーティリティの公開 API
- src/kabusys/strategy/   : 戦略層（未実装の初期化）
- src/kabusys/execution/  : 実行層（未実装の初期化）
- src/kabusys/monitoring/ : 監視モジュール（初期化済みファイルあり）

（上記は本コードベースに含まれる主要ファイルの一覧です）

---

## 設定項目（settings）

kabusys.config.Settings からアクセスできる主な設定プロパティ:

- jquants_refresh_token -> JQUANTS_REFRESH_TOKEN (必須)
- kabu_api_password -> KABU_API_PASSWORD (必須)
- kabu_api_base_url -> KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- slack_bot_token -> SLACK_BOT_TOKEN (必須)
- slack_channel_id -> SLACK_CHANNEL_ID (必須)
- duckdb_path -> DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- sqlite_path -> SQLITE_PATH (デフォルト: data/monitoring.db)
- env -> KABUSYS_ENV (development|paper_trading|live)
- log_level -> LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL)
- is_live/is_paper/is_dev ブール判定ヘルパー

未設定の必須環境変数にアクセスすると ValueError が発生します。

---

## 運用・開発上の注意

- DuckDB スキーマ初期化は冪等（既存テーブルはスキップ）ですが、監査スキーマ初期化には transactional オプションがあります（init_audit_schema）。
- ETL は差分更新・バックフィルを行い、ON CONFLICT による重複防止を採用しています。
- ニュース収集は SSRF 対策・サイズ制限・XML パースの安全化（defusedxml）を実装しています。
- レート制限やリトライのロジックを内蔵しているため、API 呼び出しは簡単に過負荷を引き起こさない設計です。
- テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定し、自動 .env 読み込みを無効化できます。

---

もし README に追加して欲しい項目（例: CI/CD 手順、より詳細な DB スキーマ説明、サンプル .env.example ファイル、パッケージ配布方法）があれば教えてください。必要に応じて追記します。