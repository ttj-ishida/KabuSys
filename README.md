# KabuSys

日本株向け自動売買基盤（研究・データプラットフォーム・戦略・発注監査を含むモジュール群）

このリポジトリは、J-Quants などの外部データソースからのデータ取得、DuckDB を用いたデータ基盤、特徴量計算、シグナル生成、ニュース収集、発注監査ログなどを提供する日本株自動売買システムのコア実装です。

---

## 主要な特徴

- データ取得
  - J-Quants API クライアント（レートリミット遵守・リトライ・トークン自動リフレッシュ・ページネーション対応）
  - 株価（OHLCV）、財務データ、JPXカレンダーの取得・保存
- データ基盤（DuckDB）
  - Raw / Processed / Feature / Execution の多層スキーマを定義する初期化機能（冪等）
  - 各種テーブル・インデックスを含むスキーマ管理
- ETL パイプライン
  - 差分更新・バックフィル・品質チェックを含む日次 ETL（run_daily_etl）
- 特徴量・研究ユーティリティ
  - ファクター計算（Momentum / Volatility / Value / Liquidity）
  - Z スコア正規化、将来リターン・IC 計算などの研究用ユーティリティ
- 戦略層
  - 特徴量の作成（build_features）とシグナル生成（generate_signals）
  - Bear レジームフィルタ、BUY/SELL ロジック、エグジット判定（ストップロス等）
- ニュース収集
  - RSS フィード取得（SSRF 対策、gzip 対応、トラッキング除去）と銘柄抽出・保存
- 発注監査
  - signal → order_request → execution のトレーサビリティを担保する監査テーブル設計
- セキュリティ・信頼性設計
  - 冪等性（ON CONFLICT / INSERT ... DO UPDATE）、トランザクション、ログ出力
  - SSRF 対策、XML の安全パーサ（defusedxml）、応答サイズ制限
  - 環境変数管理（.env 自動読み込み、必須変数チェック）

---

## 必要環境

- Python 3.10+
  - 型注釈（X | Y）の使用に伴い 3.10 以上を想定しています
- DuckDB
- defusedxml
- （任意）その他標準ライブラリのみで多くの処理を実装していますが、実行時に必要な外部パッケージは pip で導入してください

推奨パッケージ（例）
- duckdb
- defusedxml

---

## セットアップ手順

1. リポジトリをクローン／取得

2. 仮想環境作成（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows (PowerShell)
   ```

3. 依存パッケージをインストール
   ```
   pip install -U pip
   pip install duckdb defusedxml
   # プロジェクトをeditableインストール（pyproject.toml がある想定）
   pip install -e .
   ```

4. 環境変数（.env）を用意
   プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env` または `.env.local` を置くと、自動で読み込まれます（自動読み込みを無効化する場合は env に `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定）。

   必須（例）
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   KABU_API_PASSWORD=your_kabu_api_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   ```

   任意（デフォルトは README に記載の通り）
   ```
   KABU_API_BASE_URL=http://localhost:18080/kabusapi
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   KABUSYS_ENV=development  # development|paper_trading|live
   LOG_LEVEL=INFO
   ```

---

## 初期化（DuckDB スキーマ作成）例

Python スクリプトや REPL で初期化します。

```python
from kabusys.config import settings
from kabusys.data.schema import init_schema

# settings.duckdb_path は .env の DUCKDB_PATH に依存（デフォルト: data/kabusys.duckdb）
conn = init_schema(settings.duckdb_path)
```

- ":memory:" を渡すとインメモリ DB になります（テスト用）。
- init_schema はテーブル作成を冪等で行います。

---

## 主要な使い方サンプル

以下は代表的な処理の呼び出し例です。実運用ではエラーハンドリング・ログ管理を適切に行ってください。

1) 日次 ETL（株価・財務・カレンダーを差分取得）
```python
from datetime import date
from kabusys.config import settings
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl

conn = init_schema(settings.duckdb_path)
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

2) 特徴量作成（features テーブルへ保存）
```python
from datetime import date
from kabusys.config import settings
from kabusys.data.schema import init_schema
from kabusys.strategy import build_features

conn = init_schema(settings.duckdb_path)
count = build_features(conn, target_date=date(2025, 3, 1))
print(f"upserted features: {count}")
```

3) シグナル生成（signals テーブルへ保存）
```python
from datetime import date
from kabusys.config import settings
from kabusys.data.schema import init_schema
from kabusys.strategy import generate_signals

conn = init_schema(settings.duckdb_path)
signals_written = generate_signals(conn, target_date=date(2025, 3, 1))
print(f"signals written: {signals_written}")
```

4) ニュース収集ジョブ
```python
from kabusys.config import settings
from kabusys.data.schema import init_schema
from kabusys.data.news_collector import run_news_collection

conn = init_schema(settings.duckdb_path)
# known_codes: 抽出する有効な銘柄コードの集合（例: {'7203','6758',...}）
results = run_news_collection(conn, known_codes={'7203', '6758'})
print(results)
```

5) J-Quants API の直接利用例
```python
from kabusys.data import jquants_client as jq
from datetime import date

# トークンは settings から自動的に取得される（get_id_token は refresh トークンから idToken を取得）
id_token = jq.get_id_token()
records = jq.fetch_daily_quotes(id_token=id_token, date_from=date(2025,1,1), date_to=date(2025,1,31))
```

---

## 注意点 / 設計上の要点

- 環境変数
  - 必須の環境変数（JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD / SLACK_BOT_TOKEN / SLACK_CHANNEL_ID）は Settings クラスでチェックされ、未設定だと ValueError が発生します。
- レート制御・リトライ
  - J-Quants クライアントは 120 req/min を守るための固定間隔スロットリングと、指定ステータスコードに対する指数バックオフリトライを備えています。
- 冪等性とトランザクション
  - DB 保存処理は ON CONFLICT やトランザクションを用いて冪等性と原子性を確保します。
- 研究用コード分離
  - research パッケージの関数群は発注層や外部 API に依存しない設計になっています（ロジック検証・バックテストに利用）。
- セキュリティ
  - RSS 取得では SSRF 対策、XML の安全パース、受信サイズ制限を実装しています。
- 実運用とペーパートレード
  - KABUSYS_ENV により動作モード（development / paper_trading / live）を切り替えられます。is_live / is_paper / is_dev ヘルパーを利用してください。

---

## ディレクトリ構成（主要ファイル）

下記は src/kabusys 配下の主要モジュールです（この README は配布されたコードベースに基づいて作成しています）。

- kabusys/
  - __init__.py
  - config.py                     -- 環境変数・設定管理
  - data/
    - __init__.py
    - jquants_client.py           -- J-Quants API クライアント（取得・保存）
    - news_collector.py          -- RSS ニュース収集・保存・銘柄抽出
    - schema.py                  -- DuckDB スキーマ定義・初期化
    - stats.py                   -- Z スコア等統計ユーティリティ
    - pipeline.py                -- 日次 ETL パイプライン
    - calendar_management.py     -- 市場カレンダーの管理・取得ジョブ
    - features.py                -- features の公開ラッパ
    - audit.py                   -- 発注・約定の監査テーブル（DDL）
  - research/
    - __init__.py
    - factor_research.py         -- ファクター計算（momentum/volatility/value）
    - feature_exploration.py     -- 将来リターン / IC / summary 集計
  - strategy/
    - __init__.py
    - feature_engineering.py     -- features テーブル作成（正規化・フィルタ）
    - signal_generator.py        -- final_score 計算と signals 生成
  - execution/
    - __init__.py                -- 発注実装層（空ファイル・拡張ポイント）
  - monitoring/                  -- 監視・アラート関連（未列挙：コードベースにより追加想定）

（上記は提供されたファイルセットに基づく抜粋です。）

---

## 開発・貢献

- コーディング規約やテストはプロジェクト方針に従って追加してください。
- 実際の発注ロジック（証券会社 API との接続）を導入する場合は、execution 層を実装し、paper_trading/live の切り替え・安全策（取引上限・リスクチェック）を厳格に行ってください。
- シークレットは Git 管理しないこと。`.env` を `.gitignore` に追加してください。

---

## ライセンス

この README は実装例の説明を目的としています。実際のプロジェクトでは適切なライセンスを付与してください（例: MIT / Apache-2.0 等）。

---

何か特定のセットアップ手順（例: Docker 化、CI ワークフロー、具体的な SLACK 通知設定、kabu ステーション連携実装など）をREADMEへ追記したい場合は、使用する環境や要件を教えてください。必要に応じてサンプルスクリプトや追加の注意点も書きます。