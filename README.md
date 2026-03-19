# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ（KabuSys）。  
J-Quants API や RSS を使ったデータ収集、DuckDB ベースのスキーマ定義、ETL パイプライン、データ品質チェック、ファクター計算・リサーチユーティリティを提供します。

主な設計方針は「API呼び出し・DB操作は冪等」「Look-ahead-bias を避けるための fetched_at 記録」「外部への発注等は分離してテスト可能にすること」です。

---

## 機能一覧

- データ取得（J-Quants API）と保存
  - 株価日足（OHLCV）、財務データ、JPX マーケットカレンダーの取得（ページネーション対応）
  - レートリミット管理、リトライ、トークン自動リフレッシュ
  - DuckDB へ冪等的に保存（ON CONFLICT DO UPDATE）
- DuckDB スキーマ管理
  - Raw / Processed / Feature / Execution / Audit 層のテーブル定義と初期化
  - 監査用テーブル群（signal / order_request / execution 等）
- ETL パイプライン
  - 差分取得（最終取得日からの差分）・バックフィル・品質チェックを組み合わせた日次 ETL（run_daily_etl）
- ニュース収集
  - RSS から記事収集、前処理、記事IDの生成、raw_news への冪等保存、銘柄コード抽出・紐付け
  - SSRF 対策、圧縮チェック、XML パース保護（defusedxml）
- データ品質チェック
  - 欠損、重複、将来日付、スパイク（急騰/急落）などの検出（QualityIssue を返却）
- リサーチ／特徴量計算
  - Momentum / Volatility / Value 等のファクター計算（DuckDB を直接参照）
  - 将来リターン、IC（スピアマンランク相関）、ファクター統計サマリー
  - Zスコア正規化ユーティリティ（data.stats.zscore_normalize）
- 補助ユーティリティ
  - マーケットカレンダー管理（営業日判定、次/前営業日取得、夜間カレンダー更新ジョブ）
  - 監査ログ（init_audit_schema / init_audit_db）

注: strategy/ execution モジュールはパッケージ構造を提供しています（発注ロジックは別途実装想定）。

---

## 要件（概略）

- Python 3.10+
- 依存ライブラリ（例）
  - duckdb
  - defusedxml
（その他は標準ライブラリで実装されています。細かいバージョンは pyproject.toml / requirements を参照してください）

インストール例:
```bash
python -m pip install --upgrade pip
python -m pip install duckdb defusedxml
# パッケージを開発モードでインストールする場合
python -m pip install -e .
```

---

## 環境変数 / 設定

設定は環境変数またはプロジェクトルートに置いた `.env` / `.env.local` から自動で読み込まれます（モジュール `kabusys.config`）。自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

重要な環境変数（必須）:
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（API 認証）
- KABU_API_PASSWORD: kabu ステーション API パスワード（発注機能を有効にする場合）
- SLACK_BOT_TOKEN: Slack 通知に使用する Bot トークン
- SLACK_CHANNEL_ID: Slack 通知先チャンネル ID

任意 / デフォルトあり:
- KABUSYS_ENV: 実行環境 (development | paper_trading | live)。デフォルト: development
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）。デフォルト: INFO
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）

サンプル .env（プロジェクトルートに配置）:
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
KABUSYS_ENV=development
LOG_LEVEL=DEBUG
DUCKDB_PATH=data/kabusys.duckdb
```

kabusys.config は必須キーが未設定だと ValueError を投げます。

---

## セットアップ手順（初期化例）

1. 依存ライブラリをインストールする
   ```bash
   python -m pip install duckdb defusedxml
   python -m pip install -e .
   ```

2. `.env` を作成して必須の環境変数を設定する（上記参照）。

3. DuckDB スキーマを初期化する（Python スクリプト例）:
   ```python
   from kabusys.data import schema
   from kabusys.config import settings

   # settings.duckdb_path は環境変数 DUCKDB_PATH を参照
   conn = schema.init_schema(settings.duckdb_path)
   ```

4. 監査ログ用スキーマ（オプション）:
   ```python
   from kabusys.data import audit
   # 既存の conn に監査テーブルを追加
   audit.init_audit_schema(conn, transactional=True)
   ```

---

## 基本的な使い方

- 日次 ETL を実行する（例: 現在日を対象に J-Quants から取得して保存・品質チェック）:
  ```python
  from kabusys.data import schema, pipeline
  from kabusys.config import settings

  conn = schema.get_connection(settings.duckdb_path)  # 既に init_schema を実行済みであること
  result = pipeline.run_daily_etl(conn)
  print(result.to_dict())
  ```

- 差分 ETL（株価のみ）を個別に実行:
  ```python
  from kabusys.data import pipeline
  from kabusys.data import schema
  from kabusys.config import settings
  import datetime

  conn = schema.get_connection(settings.duckdb_path)
  fetched, saved = pipeline.run_prices_etl(conn, target_date=datetime.date.today())
  print(f"fetched={fetched}, saved={saved}")
  ```

- ニュース収集ジョブを実行:
  ```python
  from kabusys.data.news_collector import run_news_collection
  from kabusys.data import schema
  from kabusys.config import settings

  conn = schema.get_connection(settings.duckdb_path)
  # known_codes を渡すと本文から銘柄コードを抽出して news_symbols を作る
  known_codes = {"7203", "6758"}  # サンプル
  results = run_news_collection(conn, known_codes=known_codes)
  print(results)  # {source_name: 新規保存数, ...}
  ```

- リサーチ / ファクター計算の利用例:
  ```python
  from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, zscore_normalize
  from kabusys.data import schema
  import datetime

  conn = schema.get_connection("data/kabusys.duckdb")
  target = datetime.date(2025, 1, 10)

  mom = calc_momentum(conn, target)
  vol = calc_volatility(conn, target)
  val = calc_value(conn, target)

  # 将来リターン計算
  fwd = calc_forward_returns(conn, target, horizons=[1,5,21])

  # IC 計算（例）
  ic = calc_ic(mom, fwd, factor_col="mom_1m", return_col="fwd_1d")
  ```

- Zスコア正規化:
  ```python
  from kabusys.data.stats import zscore_normalize
  normalized = zscore_normalize(mom, ["mom_1m", "mom_3m", "mom_6m", "ma200_dev"])
  ```

---

## よくあるトラブルと対処

- 環境変数が見つからない / ValueError が出る:
  - `kabusys.config.Settings` の必須キー (例: JQUANTS_REFRESH_TOKEN) が未設定です。`.env` または環境に設定してください。
  - 自動で `.env` を読み込ませたくないテスト時は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。

- duckdb がインポートできない:
  - Python 環境に duckdb をインストールしてください（pip install duckdb）。

- J-Quants API の認証エラー:
  - リフレッシュトークンが正しいか、ネットワークから API に接続できるか確認してください。get_id_token は 401 を受けた場合に自動でトークンをリフレッシュします。

- RSS 取得で XML パースエラーや巨大レスポンス:
  - news_collector は受信サイズの上限（10MB）や defusedxml を使った安全な XML パースを行っています。外部ソースの内容が想定外の場合はログを確認してください。

---

## ディレクトリ構成（主要ファイル）

概略:

- src/kabusys/
  - __init__.py
  - config.py                    — 環境変数/設定管理
  - data/
    - __init__.py
    - jquants_client.py          — J-Quants API クライアント + 保存ロジック
    - news_collector.py         — RSS 収集と DB 保存
    - schema.py                 — DuckDB スキーマ定義 & init_schema / get_connection
    - pipeline.py               — ETL パイプライン（run_daily_etl 等）
    - features.py               — 特徴量ユーティリティ（再エクスポート）
    - calendar_management.py    — カレンダー更新と営業日ユーティリティ
    - audit.py                  — 監査ログテーブル初期化
    - etl.py                    — ETL の public 型再エクスポート
    - quality.py                — データ品質チェック
    - stats.py                  — 統計ユーティリティ（zscore_normalize）
  - research/
    - __init__.py
    - feature_exploration.py    — 将来リターン、IC、summary 等
    - factor_research.py        — momentum/volatility/value 等の計算
  - strategy/                    — 戦略関連（スケルトン）
  - execution/                   — 実行/発注関連（スケルトン）
  - monitoring/                  — 監視（空の __init__ がある）

（README は主要なモジュールのみ抜粋しています。詳細は各ソースファイルの docstring を参照してください。）

---

## 追加メモ / 開発者向け情報

- 型アノテーションや設計ドキュメントの記述があるため、IDE の型チェックや静的解析（mypy, flake8 等）を導入すると開発が楽になります。
- テスト時に環境変数の自動読み込みを抑制するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定し、テスト用に明示的に環境を注入してください。
- DB 初期化関数は冪等です（既存テーブルがあれば上書きしません）。監査スキーマは別関数で追加できます。

---

この README はコードベースの主要機能と利用方法をまとめたものです。実運用前に必ず `.env.example` を元に環境変数を正しく設定し、ステージングやペーパー取引環境で十分に検証してください。