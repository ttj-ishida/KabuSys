# KabuSys

日本株向けの自動売買／データプラットフォーム用ライブラリです。  
DuckDB をデータストアとして用い、J-Quants API や RSS からデータを収集し、ファクター計算・特徴量作成・シグナル生成までをサポートします。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下の目的で設計されたモジュール群を含みます。

- J-Quants からの株価・財務・カレンダー取得（idempotent 保存／ページネーション／レートリミット対応）
- DuckDB スキーマ定義・初期化と接続管理
- ETL パイプライン（差分取得・バックフィル・品質チェック）
- ファクター計算（Momentum / Volatility / Value 等）と特徴量生成（Z スコア正規化）
- シグナル生成（ファクター・AI スコア統合、BUY/SELL 判定）
- ニュース（RSS）収集と銘柄紐付け（SSRF 対策・XML セーフティ）
- 市場カレンダー管理（営業日判定・先読み更新）
- 発注・監査ログ用スキーマ（Execution / Audit 関連テーブル）

設計方針の主な要点:
- ルックアヘッドバイアスを避ける（target_date 時点のデータのみを使用）
- DuckDB へは冪等（ON CONFLICT / DO UPDATE / DO NOTHING）で保存
- 外部依存を最低限にし、テスト容易性を重視

---

## 機能一覧

- data
  - jquants_client: J-Quants API クライアント（認証自動更新・リトライ・レート制御）
  - schema: DuckDB スキーマ定義・init_schema/get_connection
  - pipeline: 日次 ETL（差分取得 / backfill / 品質チェック）
  - news_collector: RSS 取得・前処理・raw_news 保存・銘柄抽出
  - calendar_management: market_calendar の取得・営業日判定ユーティリティ
  - stats: Z スコア正規化など統計ユーティリティ
- research
  - factor_research: Momentum / Volatility / Value の計算
  - feature_exploration: 将来リターン・IC・統計サマリ
- strategy
  - feature_engineering: ファクターの統合・ユニバースフィルタ・Z スコア正規化 → features テーブル
  - signal_generator: final_score 計算・BUY/SELL シグナル生成 → signals テーブル
- execution / monitoring / audit 用のスキーマと土台コード（発注フローや監査ログ用）

---

## セットアップ手順

1. リポジトリをクローン
   - 例: git clone <リポジトリURL>

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. パッケージをインストール
   - pip install -e .  （開発モード）
   - 必須ライブラリ（主に）:
     - duckdb
     - defusedxml
   - 実際のプロジェクトでは requirements.txt / pyproject.toml を参照してください。

4. 環境変数の準備
   - プロジェクトルートに `.env` を置くと、自動的に読み込まれます（package 内の自動ロード機能）。
   - 自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

必須環境変数（例・説明）:
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API 用パスワード（必須）
- SLACK_BOT_TOKEN: Slack 通知トークン（必須）
- SLACK_CHANNEL_ID: Slack チャンネル ID（必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV: environment（development / paper_trading / live、デフォルト development）
- LOG_LEVEL: ログレベル（DEBUG / INFO / ...、デフォルト INFO）

.env の例（最小）:
JQUANTS_REFRESH_TOKEN=your_refresh_token
KABU_API_PASSWORD=your_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO

---

## 使い方（クイックスタート）

以下は Python スクリプトや REPL から利用する基本例です。

1) DuckDB スキーマ初期化と接続
```python
from kabusys.config import settings
from kabusys.data.schema import init_schema

# settings.duckdb_path は環境変数 DUCKDB_PATH を参照
conn = init_schema(settings.duckdb_path)
```

2) 日次 ETL を実行（J-Quants から差分取得 → 保存 → 品質チェック）
```python
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn)  # target_date を指定可能
print(result.to_dict())
```

3) 特徴量の作成（features テーブルの作成）
```python
from kabusys.strategy import build_features
from datetime import date

cnt = build_features(conn, target_date=date.today())
print(f"built features for {cnt} symbols")
```

4) シグナル生成（signals テーブルへ保存）
```python
from kabusys.strategy import generate_signals
from datetime import date

n = generate_signals(conn, target_date=date.today())
print(f"generated {n} signals")
```

5) RSS ニュース収集と保存
```python
from kabusys.data.news_collector import run_news_collection

# known_codes: 銘柄抽出時に参照する有効コード集合（例: 全上場銘柄コード）
results = run_news_collection(conn, sources=None, known_codes=set(["7203","6758"]))
```

6) カレンダー更新（夜間バッチ想定）
```python
from kabusys.data.calendar_management import calendar_update_job

saved = calendar_update_job(conn)
print(f"saved {saved} calendar records")
```

7) 設定参照（アプリ設定取得）
```python
from kabusys.config import settings
print(settings.duckdb_path, settings.is_live, settings.log_level)
```

注意点:
- 多くの処理は target_date 時点以前のデータのみを参照します（ルックアヘッド回避）。
- ETL / API 呼び出し部分はネットワーク依存・API レート制御・認証が絡むため、事前に環境変数を正しく設定してください。

---

## ディレクトリ構成

主要ファイル・モジュール構成（src/kabusys 以下）:

- kabusys/
  - __init__.py
  - config.py                     -- 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py           -- J-Quants API クライアント（fetch/save）
    - news_collector.py           -- RSS 取得・前処理・保存
    - schema.py                   -- DuckDB スキーマ定義・初期化
    - stats.py                    -- 統計ユーティリティ（zscore_normalize）
    - pipeline.py                 -- ETL パイプライン（run_daily_etl など）
    - calendar_management.py      -- market_calendar の管理と営業日ユーティリティ
    - features.py                 -- features インターフェース（再エクスポート）
    - audit.py                    -- 監査ログ（audit）スキーマ
  - research/
    - __init__.py
    - factor_research.py          -- Momentum / Volatility / Value 計算
    - feature_exploration.py      -- forward returns / IC / summary
  - strategy/
    - __init__.py
    - feature_engineering.py      -- features のビルド（正規化・フィルタ）
    - signal_generator.py         -- final_score 計算・シグナル生成
  - execution/                     -- 発注関連の土台（空の __init__ 等）
  - monitoring/                    -- 監視・メトリクス用（将来的な場所）

補足:
- schema.py に DuckDB の全テーブル DDL が定義されています（raw/processed/feature/execution 層）。
- jquants_client は API のページネーション・リトライ・token-refresh を内包します。
- news_collector は defusedxml を用いて XML の安全対策を行っています。

---

## 開発・テスト上のヒント

- 自動 .env のロードを無効化したいテストでは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB のテスト用にインメモリ DB を使う場合:
  - from kabusys.data.schema import init_schema
  - conn = init_schema(":memory:")
- 外部 API 呼び出しを避けるユニットテストでは、jquants_client._request / _urlopen 等をモックしてください。
- ニュース収集はネットワークに依存するため、fetch_rss をテストでモックして利用することが推奨されます。

---

## ライセンス・貢献

この README はコードベースの簡易ドキュメントです。実運用する際は DataPlatform.md / StrategyModel.md 等の設計ドキュメントや運用ルールを参照してください。貢献やバグ報告はリポジトリの issue とプルリクエストで受け付けてください。

---

必要であれば README に「API リファレンス例」「.env.example の自動生成スニペット」「コマンドラインツールの例」などを追記します。どの情報を優先して追加しますか？