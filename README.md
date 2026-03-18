# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリです。  
データ取得（J-Quants）、DuckDB ベースのスキーマ、ETL パイプライン、ニュース収集、ファクター計算（リサーチ用途）や監査ログなど、投資アルゴリズムの開発・運用に必要な機能群を含みます。

バージョン: 0.1.0

---

## 概要

KabuSys は以下の目的を持つモジュール群で構成された Python パッケージです。

- J-Quants API からの株価・財務・カレンダー取得（レート制御・リトライ・トークン自動リフレッシュ対応）
- DuckDB を用いたデータスキーマ定義と冪等保存（ON CONFLICT ベース）
- ETL パイプライン（差分取得、バックフィル、品質チェック）
- RSS ベースのニュース収集と銘柄紐付け（SSRF対策・トラッキング除去）
- ファクター計算・探索（モメンタム・ボラティリティ・バリュー・IC計算 等）
- 監査ログ（シグナル→発注→約定までのトレーサビリティ）
- 設定管理（.env / 環境変数の自動ロード、必須キーの取得）

設計方針として、本番 API（発注等）に不要な処理・アクセスは行わず、研究（Research）やデータ基盤（DataPlatform）用途に安全に使えることを重視しています。

---

## 機能一覧

主要な機能（モジュール別）

- kabusys.config
  - .env ファイル自動読み込み（プロジェクトルート検出）
  - 必須環境変数の取得（settings オブジェクト経由）
  - KABUSYS_ENV / LOG_LEVEL の検証
- kabusys.data.jquants_client
  - J-Quants API ラッパー（レートリミット・リトライ・トークン管理）
  - fetch_* / save_* 系関数（daily_quotes, financials, market_calendar）
- kabusys.data.schema
  - DuckDB 用スキーマ定義、init_schema() による初期化
- kabusys.data.pipeline
  - 日次 ETL（run_daily_etl）：カレンダー→株価→財務→品質チェック
  - 個別 ETL ヘルパー（run_prices_etl 等）
- kabusys.data.news_collector
  - RSS 取得（fetch_rss）、記事正規化、raw_news への冪等保存
  - 銘柄抽出・紐付け（extract_stock_codes, save_news_symbols）
- kabusys.data.quality
  - 欠損・スパイク・重複・日付不整合チェック（run_all_checks）
- kabusys.research
  - ファクター計算: calc_momentum / calc_volatility / calc_value
  - 特徴量解析: calc_forward_returns / calc_ic / factor_summary / rank
  - zscore 正規化ユーティリティ（data.stats.zscore_normalize）
- kabusys.data.audit
  - 監査ログ用テーブル定義 / 初期化（init_audit_schema / init_audit_db）

---

## 必要な環境変数

設定は .env ファイルまたは環境変数から読み込まれます。自動ロードを無効にしたい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

主要な必須 / 推奨変数:

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabu ステーション API 用パスワード（発注等を使う場合）
- KABU_API_BASE_URL (省略可, default: http://localhost:18080/kabusapi)
- SLACK_BOT_TOKEN (必須) — Slack 通知に使用する場合
- SLACK_CHANNEL_ID (必須) — Slack チャネル ID
- DUCKDB_PATH (省略可, default: data/kabusys.duckdb)
- SQLITE_PATH (省略可, default: data/monitoring.db)
- KABUSYS_ENV (default: development) — 有効値: development, paper_trading, live
- LOG_LEVEL (default: INFO) — 有効値: DEBUG, INFO, WARNING, ERROR, CRITICAL

サンプル .env（README 目的の例）
```
JQUANTS_REFRESH_TOKEN=your_refresh_token_here
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C0123456789
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順

1. Python 仮想環境を作成・有効化
   - python3 -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール
   - 主要な依存:
     - duckdb
     - defusedxml
   - 例:
     - pip install duckdb defusedxml

   （パッケージ配布用の requirements.txt / setup.py がある場合は適宜 pip install -e . や pip install -r requirements.txt を使ってください。）

3. リポジトリルートに .env を作成し、必要な環境変数を設定

4. DuckDB スキーマ初期化
   - Python REPL またはスクリプトで:
     from kabusys.config import settings
     from kabusys.data.schema import init_schema
     conn = init_schema(settings.duckdb_path)
   - これにより DuckDB ファイル（デフォルト data/kabusys.duckdb）が作成され、全テーブルが作成されます。

5. 監査ログ用スキーマ（必要に応じて）
   - from kabusys.data.audit import init_audit_schema
     init_audit_schema(conn, transactional=True)

---

## 使い方（代表的な例）

以下は最小限の利用例です。実運用ではエラーハンドリングやログ設定、定期実行（cron / Airflow / scheduler）を追加してください。

- settings の利用（環境変数取得）
```
from kabusys.config import settings
print(settings.jquants_refresh_token)
print(settings.duckdb_path)
```

- スキーマ初期化
```
from kabusys.config import settings
from kabusys.data.schema import init_schema

conn = init_schema(settings.duckdb_path)
```

- 日次 ETL を実行する（全体）
```
from kabusys.config import settings
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl

conn = init_schema(settings.duckdb_path)
result = run_daily_etl(conn)
print(result.to_dict())
```

- ニュース収集ジョブ（RSS）
```
from kabusys.data.schema import init_schema
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

conn = init_schema("data/kabusys.duckdb")
known_codes = {"7203", "6758", "9984"}  # 既知銘柄リスト
res = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
print(res)
```

- ファクター計算 / リサーチ
```
from datetime import date
import duckdb
from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, zscore_normalize

conn = duckdb.connect("data/kabusys.duckdb")
target = date(2024, 1, 4)

mom = calc_momentum(conn, target)
vol = calc_volatility(conn, target)
val = calc_value(conn, target)

# 将来リターンを計算して IC を算出（例）
fwd = calc_forward_returns(conn, target, horizons=[1,5])
# factor_records は例えば mom をそのまま使う
ic = calc_ic(mom, fwd, factor_col="mom_1m", return_col="fwd_1d")
print("IC:", ic)
```

- zscore 正規化
```
from kabusys.data.stats import zscore_normalize
normed = zscore_normalize(mom, ["mom_1m", "ma200_dev"])
```

---

## ディレクトリ構成

リポジトリ（パッケージ）の主要ファイル構成（抜粋）

- src/kabusys/
  - __init__.py
  - config.py                        — 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py              — J-Quants API クライアント（取得/保存）
    - news_collector.py              — RSS ニュース収集 / 保存
    - schema.py                      — DuckDB スキーマ定義・初期化
    - pipeline.py                    — ETL パイプライン（run_daily_etl 等）
    - features.py                    — 特徴量ユーティリティ再エクスポート
    - stats.py                       — 統計ユーティリティ（zscore_normalize）
    - calendar_management.py         — 市場カレンダー管理
    - quality.py                      — データ品質チェック
    - audit.py                        — 監査ログテーブル初期化
    - etl.py                          — ETL 公開インターフェース（型の再エクスポート）
  - research/
    - __init__.py
    - feature_exploration.py         — 将来リターン・IC・サマリー等
    - factor_research.py             — momentum / volatility / value 計算
  - strategy/                         — 戦略モジュール（拡張用）
  - execution/                        — 発注実行関連（拡張用）
  - monitoring/                       — 監視・モニタリング（拡張用）

（実際のツリーはプロジェクトに合わせて異なる場合があります）

---

## 運用上の注意

- 環境変数管理: .env 自動ロード機能があるため、リポジトリルートに .env を置くと自動で読み込まれます。自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- J-Quants API のレート制限（120 req/min）をクライアント側で制御していますが、大量バッチ実行時は制限に注意してください。
- DuckDB のバージョン差異により一部機能（外部キーの ON DELETE 動作や UNIQUE の NULL 扱い等）が異なることがあります。README の SQL 設計は DuckDB 1.5 系を念頭にしています。
- ニュース収集では外部 URL の検証（SSRF 対策）、受信サイズ上限、XML デコード対策（defusedxml）を実施しています。外部に公開する場合はさらに堅牢な運用を推奨します。
- live 環境での発注機能を追加する場合は、Kabu API の認証・実装部分の追加と十分なテストが必要です（本コードベースはデータ取得・計算・監査を主眼としています）。

---

## 貢献 / 開発

- コードはモジュール毎に役割が分かれているため、機能追加やテストの追加はモジュール単位で行ってください。
- テストおよび CI を整備する際は、環境変数の自動ロードを無効化する `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を使うとテストが安定します。
- DuckDB をインメモリで使う場合は `db_path=":memory:"` を指定して init_schema を呼び出してください。

---

必要であれば README にサンプルの CLI コマンド、docker-compose / systemd ユニット例、CI 設定例、より詳細な API ドキュメント（各関数の引数説明や戻り値）などを追加できます。どの情報を優先して追加しますか？