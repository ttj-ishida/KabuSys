# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ群です。  
DuckDB をバックエンドとしたデータ収集（J-Quants）、ETL、品質チェック、特徴量計算、ニュース収集、監査ログなどのユーティリティを提供します。

---

## プロジェクト概要

KabuSys は日本株の自動売買基盤のための共通コンポーネント群です。  
主に以下の用途を想定しています。

- J-Quants API からの市場データ・財務データ・カレンダー取得（レート制御・リトライ・トークン自動更新対応）
- DuckDB によるデータレイヤ（Raw / Processed / Feature / Execution）の管理と初期化
- 日次 ETL パイプライン（差分取得・バックフィル・品質チェック）
- ニュース（RSS）収集と記事 → 銘柄紐付け
- ファクター / 特徴量計算（モメンタム・ボラティリティ・バリュー等）および研究ユーティリティ
- 監査ログ（signal → order → execution のトレース）用スキーマ
- マーケットカレンダー（営業日判定等）ユーティリティ

設計上、実際の発注 API 等の呼び出しは分離されており、Data / Research 層は外部 API を直接叩かないことを基本としています。

---

## 主な機能一覧

- 環境設定管理
  - .env / .env.local の自動読み込み（プロジェクトルートは .git または pyproject.toml を基準）
  - 必須環境変数の取得・検証（settings オブジェクト）
- J-Quants クライアント（kabusys.data.jquants_client）
  - 日足・財務・マーケットカレンダーの取得（ページネーション対応）
  - レートリミッタ、リトライ、401 トークン自動リフレッシュ、保存ユーティリティ
- DuckDB スキーマ管理（kabusys.data.schema）
  - Raw / Processed / Feature / Execution 層のテーブル定義と初期化
- ETL パイプライン（kabusys.data.pipeline）
  - 差分取得、バックフィル、品質チェック、日次 ETL 実行（run_daily_etl）
- データ品質チェック（kabusys.data.quality）
  - 欠損、スパイク、重複、日付不整合の検出
- ニュース収集（kabusys.data.news_collector）
  - RSS 取得・安全対策（SSRF対策、Gzip 上限、XML 防御）・前処理・DB 保存・銘柄抽出
- 研究用ファクター計算（kabusys.research）
  - calc_momentum / calc_volatility / calc_value / calc_forward_returns / calc_ic / factor_summary / rank
  - zscore_normalize（kabusys.data.stats）
- カレンダー管理（kabusys.data.calendar_management）
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / calendar_update_job
- 監査スキーマ（kabusys.data.audit）
  - signal_events, order_requests, executions テーブル等の初期化ユーティリティ

---

## 必要要件

- Python 3.10+
  - （コード中で | 型ヒントや match 等は使っていませんが、union 演算子 `X | Y` を使用しているため 3.10 以上を想定）
- 必須 Python パッケージ
  - duckdb
  - defusedxml

インストール例:
```bash
python -m pip install "duckdb" "defusedxml"
```

※パッケージ化している場合は `pip install -e .` 等でインストールしてください。

---

## 環境変数（主なもの）

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（get_id_token に使用）
- KABU_API_PASSWORD — kabuステーション等を利用する場合のパスワード
- SLACK_BOT_TOKEN — Slack 通知に使用する場合
- SLACK_CHANNEL_ID — Slack チャンネル ID

任意（デフォルトあり）:
- KABUSYS_ENV — development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視 DB 等（デフォルト: data/monitoring.db）

自動 .env ロード:
- プロジェクトルート（.git または pyproject.toml を基準）にある `.env` と `.env.local` を自動で読み込みます。
- 自動読み込みを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

サンプル .env:
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C12345678
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=~/kabusys/data/kabusys.duckdb
```

---

## セットアップ手順（簡易）

1. リポジトリをクローン
   ```bash
   git clone <repo-url>
   cd <repo>
   ```

2. Python 依存関係をインストール
   ```bash
   python -m pip install -r requirements.txt   # もし requirements.txt があれば
   # または最小:
   python -m pip install duckdb defusedxml
   ```

3. 環境変数を設定
   - プロジェクトルートに `.env` を作成するか、環境変数を直接設定します。
   - 上のサンプルを参考に必要な値を埋めてください。

4. DuckDB スキーマ初期化
   - Python REPL かスクリプトで実行:
   ```python
   from kabusys.config import settings
   from kabusys.data.schema import init_schema

   conn = init_schema(settings.duckdb_path)
   # これで DuckDB ファイルが作成され、全テーブルが作成されます
   ```

5. 監査ログスキーマ（任意）
   ```python
   from kabusys.data.audit import init_audit_schema
   init_audit_schema(conn, transactional=True)
   ```

---

## 使い方（代表的な例）

- 日次 ETL を実行する（基本例）
  ```python
  from datetime import date
  import duckdb
  from kabusys.config import settings
  from kabusys.data.schema import init_schema
  from kabusys.data.pipeline import run_daily_etl

  conn = init_schema(settings.duckdb_path)
  result = run_daily_etl(conn)  # target_date=None なら今日を使用
  print(result.to_dict())
  ```

- ニュース収集ジョブを実行する
  ```python
  from kabusys.config import settings
  from kabusys.data.schema import init_schema
  from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

  conn = init_schema(settings.duckdb_path)
  known_codes = {"7203", "6758", "4433"}  # 事前に有効な銘柄コードを準備
  results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
  print(results)
  ```

- 研究・ファクター計算の例
  ```python
  from datetime import date
  from kabusys.config import settings
  from kabusys.data.schema import init_schema
  from kabusys.research import calc_momentum, calc_volatility, calc_value, zscore_normalize

  conn = init_schema(settings.duckdb_path)
  target = date(2024, 1, 4)
  mom = calc_momentum(conn, target)
  vol = calc_volatility(conn, target)
  val = calc_value(conn, target)

  # Zスコア正規化の例
  normalized = zscore_normalize(mom, ["mom_1m", "mom_3m", "mom_6m", "ma200_dev"])
  ```

- カレンダー系ユーティリティ
  ```python
  from datetime import date
  from kabusys.data.calendar_management import is_trading_day, next_trading_day

  # conn は DuckDB 接続
  d = date(2024, 1, 2)
  print(is_trading_day(conn, d))
  print(next_trading_day(conn, d))
  ```

- J-Quants API を直接使ってデータを取得する（テストやバックフィル）
  ```python
  from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
  data = fetch_daily_quotes(code="7203", date_from=date(2023,1,1), date_to=date(2023,12,31))
  saved = save_daily_quotes(conn, data)
  ```

---

## 運用・自動化のヒント

- 日次バッチ化: run_daily_etl を cron / Airflow / GitHub Actions 等で定期実行
- ロギング: settings.log_level によりログレベルを調整
- 本番環境では KABUSYS_ENV=live を設定し、設定分岐（is_live / is_paper / is_dev）を利用
- .env.local はローカル専用の上書き用ファイル（.env を上書き）として利用可
- 自動 .env 読み込みはプロジェクトルートを基準に行われるため、CI では環境変数を直接渡すか KABUSYS_DISABLE_AUTO_ENV_LOAD を利用

---

## ディレクトリ構成（抜粋）

```
src/
└─ kabusys/
   ├─ __init__.py
   ├─ config.py                    # 環境変数 / settings
   ├─ data/
   │  ├─ __init__.py
   │  ├─ jquants_client.py         # J-Quants API クライアント + 保存ユーティリティ
   │  ├─ news_collector.py         # RSS 取得・前処理・保存・銘柄抽出
   │  ├─ schema.py                 # DuckDB スキーマ定義・初期化
   │  ├─ stats.py                  # zscore_normalize 等
   │  ├─ pipeline.py               # ETL パイプライン（run_daily_etl 等）
   │  ├─ calendar_management.py    # カレンダー更新 / 営業日判定
   │  ├─ quality.py                # データ品質チェック
   │  ├─ audit.py                  # 監査ログスキーマ初期化
   │  └─ features.py
   ├─ research/
   │  ├─ __init__.py
   │  ├─ feature_exploration.py    # calc_forward_returns / calc_ic / factor_summary / rank
   │  └─ factor_research.py        # calc_momentum / calc_value / calc_volatility
   ├─ strategy/
   │  └─ __init__.py
   ├─ execution/
   │  └─ __init__.py
   └─ monitoring/
      └─ __init__.py
```

---

## 注意事項 / 設計上のポイント

- DuckDB の INSERT は冪等（ON CONFLICT DO UPDATE / DO NOTHING）を使って重複を排除する設計になっています。
- J-Quants API のレート制御（120 req/min）・リトライ・401 リフレッシュ処理を組み込んでいます。
- ニュース収集では SSRF 対策、XML 防御、Gzip サイズ上限など安全性を考慮しています。
- Research / Data モジュールは本番発注 API にはアクセスしない設計で、実験的解析・検証に使いやすくしています。
- 型やエラーチェックを行い、実運用での堅牢性を重視しています。

---

## 開発・コントリビュート

- コーディングスタイルやテストはプロジェクトの方針に従ってください。
- .env や機密情報はリポジトリにコミットしないでください（.gitignore で除外すること）。

---

README は以上です。必要であれば「導入スクリプト例」「cron / systemd のジョブファイル例」「より詳細な API リファレンス（各関数の引数・戻り値）」などを追加します。どの部分を詳しくしたいか教えてください。