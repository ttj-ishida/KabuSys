# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリです。  
DuckDB をデータ層に用い、J-Quants API からのデータ取得、ETL、品質チェック、ニュース収集、ファクター計算、監査ログなどを提供します。

主な設計方針は「冪等性」「Look‑ahead bias の回避」「テスト可能性」「軽量依存」です。  
（外部ライブラリへの依存は最小限に抑え、標準ライブラリ中心で実装されています。）

## 機能一覧

- 環境設定管理
  - .env / .env.local の自動ロード（プロジェクトルート探索）
  - 必須環境変数取得のヘルパ
- データ取得（J-Quants API クライアント）
  - 日足 OHLCV、財務データ、JPX カレンダー取得（ページネーション対応）
  - レートリミット遵守、再試行、401 自動リフレッシュ
  - DuckDB への冪等保存ユーティリティ
- ETL パイプライン
  - 差分更新（バックフィル対応）、市場カレンダー先読み
  - 日次 ETL エントリポイント（run_daily_etl）
- データ品質チェック
  - 欠損、スパイク、重複、日付不整合チェック（QualityIssue）
  - run_all_checks でまとめて実行
- ニュース収集
  - RSS フィード取得、前処理、ID 正規化、SSRF 対策、DuckDB への冪等保存
  - 銘柄コード抽出・紐付け機能
- ファクター計算 / リサーチ
  - Momentum / Volatility / Value 等のファクター計算（DuckDB 結合ベース）
  - 将来リターン計算、IC（Spearman）計算、統計サマリー、Zスコア正規化
  - research モジュールは外部 API にアクセスしない設計
- スキーマ管理
  - DuckDB スキーマの初期化（init_schema / init_audit_schema）
  - Raw / Processed / Feature / Execution / Audit 層のテーブル定義
- 監査（Audit）
  - signal → order_request → execution を追跡する監査テーブル群
  - UTC タイムゾーン固定、冪等・トレーサビリティ重視

## 要求依存パッケージ

最低限必要なパッケージ（例）:
- Python 3.10+ を想定
- duckdb
- defusedxml

インストール例:
```bash
pip install duckdb defusedxml
```
（プロジェクトの requirements.txt があればそちらを使用してください）

## 環境変数（主なもの）

コード内で必須/既定値が参照される環境変数の例：

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabu ステーション API 用パスワード
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID — Slack チャンネルID

任意 / 既定あり:
- KABUSYS_ENV — "development" / "paper_trading" / "live"（デフォルト: development）
- LOG_LEVEL — "DEBUG"/"INFO"/...
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 を設定すると .env 自動ロードを無効化
- KABUSYS 自動ロードはプロジェクトルート（.git または pyproject.toml）を基準に .env → .env.local の順で読み込み（.env.local が上書き）

データベースパス（既定値あり）:
- DUCKDB_PATH — data/kabusys.duckdb（デフォルト）
- SQLITE_PATH — data/monitoring.db（デフォルト）

※ 環境変数は .env（または .env.local）で管理するのが推奨です。

## セットアップ手順（簡易）

1. リポジトリをクローン
2. Python 環境を作成（venv 等）
3. 依存ライブラリをインストール
   - pip install duckdb defusedxml
4. .env を作成し、必要な環境変数を設定
   - .env.example があれば参照
5. DuckDB スキーマ初期化
   - 下記「初期化／実行例」を参照

## 初期化 / 実行例（Python）

以下は最小限の操作例です。インタプリタ、スクリプト、またはタスクランナーから実行してください。

- DuckDB スキーマ初期化
```python
from kabusys.data.schema import init_schema

# ファイルに保存する場合
conn = init_schema("data/kabusys.duckdb")

# メモリ内 DB の場合
# conn = init_schema(":memory:")
```

- 監査ログ用スキーマ初期化（既存接続に追加）
```python
from kabusys.data.audit import init_audit_schema

init_audit_schema(conn, transactional=True)
```

- 日次 ETL 実行
```python
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn)  # target_date を指定することも可
print(result.to_dict())
```

- ニュース収集（RSS）実行
```python
from kabusys.data.news_collector import run_news_collection

# known_codes: 銘柄コードセットを渡すと抽出→紐付けまで行う
known_codes = {"7203", "6758"}
res = run_news_collection(conn, known_codes=known_codes)
print(res)  # {source_name: saved_count, ...}
```

- ファクター計算（リサーチ）
```python
from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic
from datetime import date

d = date(2024, 1, 10)
mom = calc_momentum(conn, d)
vol = calc_volatility(conn, d)
val = calc_value(conn, d)

# 将来リターンと IC の例
fwd = calc_forward_returns(conn, d, horizons=[1,5,21])
# calc_ic の呼び出しは、factor_records と forward_records を code で結合して渡す
# 例: calc_ic(factor_records=mom, forward_records=fwd, factor_col="mom_1m", return_col="fwd_1d")
```

- 設定値参照
```python
from kabusys.config import settings

print(settings.duckdb_path)
print(settings.is_live)
```

## よく使う API 概要

- kabusys.config
  - settings: 環境変数から読み取る設定オブジェクト
- kabusys.data.schema
  - init_schema(db_path)
  - get_connection(db_path)
- kabusys.data.jquants_client
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - save_daily_quotes / save_financial_statements / save_market_calendar
  - get_id_token()
- kabusys.data.pipeline
  - run_daily_etl(...)
- kabusys.data.news_collector
  - fetch_rss(url, source)
  - save_raw_news(conn, articles)
  - run_news_collection(conn, sources=None, known_codes=None)
- kabusys.data.quality
  - run_all_checks(conn, target_date=None)
- kabusys.research
  - calc_momentum / calc_volatility / calc_value / calc_forward_returns / calc_ic / factor_summary / rank
- kabusys.data.stats
  - zscore_normalize(records, columns)

## ディレクトリ構成

（本 README はリポジトリの src/kabusys を想定）

- src/
  - kabusys/
    - __init__.py
    - config.py
    - data/
      - __init__.py
      - jquants_client.py        # J-Quants API クライアント（取得/保存）
      - news_collector.py       # RSS ニュース収集・前処理・保存
      - schema.py               # DuckDB スキーマ定義と初期化
      - stats.py                # 汎用統計ユーティリティ（zscore 等）
      - pipeline.py             # ETL パイプライン（run_daily_etl 等）
      - features.py             # feature ユーティリティ（zscore 等の再エクスポート）
      - calendar_management.py  # market_calendar 管理（営業日判定等）
      - audit.py                # 監査ログ（signal/request/execution テーブル）
      - etl.py                  # ETL public インターフェース再エクスポート
      - quality.py              # データ品質チェック
    - research/
      - __init__.py
      - feature_exploration.py  # 将来リターン / IC / summary
      - factor_research.py      # Momentum/Volatility/Value の計算
    - strategy/                 # （空）戦略層のエントリポイント
    - execution/                # （空）発注・execution 層のエントリポイント
    - monitoring/               # （空）監視用エントリポイント

## 運用上の注意

- 環境変数管理
  - .env/.env.local の自動読み込みはプロジェクトルート（.git or pyproject.toml）を起点に行われます。テスト時などに自動ロードを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- API レート制限
  - J-Quants のレート制限（120 req/min）をクライアント層で尊重しますが、運用側でも過度な同時実行を避けてください。
- DuckDB のトランザクション
  - 一部の初期化関数はトランザクションを使用します（init_schema は BEGIN/COMMIT）。既にトランザクション中の接続を渡すと影響が出る場合があるため注意してください。
- 本番運用: is_live フラグ（KABUSYS_ENV=live）や paper_trading モードを活用して、発注実行とテストを分離してください。
- 外部との連携（kabu ステーション・Slack等）は本 README に記載の環境変数を設定のうえ、各モジュールを実装・接続してください（本コードベースの多くは API 駆動部分と DB 保存に注力しています）。

## 開発 / テスト

- 単体テスト用に KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定し、settings の環境依存読み込みを制御できます。
- jquants_client の HTTP 呼び出しは urllib を使用しているため、テスト時は _request や _urlopen をモックして振る舞いを制御してください。
- news_collector は _urlopen を置き換え可能にしており、テストでのエラー注入・レスポンス制御が容易です。

---

質問や追加してほしいドキュメント（詳細な API リファレンス、運用手順、例外一覧など）があれば教えてください。README のサンプル .env.example や簡易 CLI の使い方なども作成できます。