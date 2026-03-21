# KabuSys

バージョン: 0.1.0

KabuSys は日本株の自動売買向けデータプラットフォームと戦略レイヤーを提供する Python パッケージです。J-Quants API からの市場データ取得、DuckDB によるデータ格納・変換、ファクター計算、特徴量生成、シグナル生成、RSS によるニュース収集、監査用スキーマなどを含むエンドツーエンドの基盤を想定しています。

---

## 主な機能

- データ取得
  - J-Quants API クライアント（株価日足 / 財務 / 市場カレンダー）
  - レート制限・リトライ・トークン自動リフレッシュ対応
- データ保管
  - DuckDB スキーマ定義／初期化（raw / processed / feature / execution 層）
  - Idempotent な保存（ON CONFLICT / upsert）
- ETL パイプライン
  - 差分取得、バックフィル、品質チェックを含む日次 ETL（run_daily_etl）
- 研究・ファクター処理
  - Momentum / Volatility / Value 等のファクター計算（research/factor_research）
  - Zスコア正規化ユーティリティ（data.stats）
  - ファクター探索・IC 計算（research/feature_exploration）
- 特徴量・シグナル生成
  - features テーブル構築（strategy.build_features）
  - ai_scores と統合して最終スコア計算、BUY/SELL シグナル生成（strategy.generate_signals）
- ニュース収集
  - RSS フィード取得・前処理・raw_news 保存・銘柄紐付け（data.news_collector）
  - SSRF対策、サイズ制限、XML安全処理（defusedxml）
- カレンダー管理
  - market_calendar を元に営業日判定・next/prev_trading_day 等を提供（data.calendar_management）
- 監査ログ
  - シグナル→発注→約定までトレース可能な監査スキーマ（data.audit）

---

## 必要環境 / 依存関係

- Python 3.9+ 推奨（typing の union 型等を使用）
- 主な Python ライブラリ:
  - duckdb
  - defusedxml
- （任意）J-Quants API の利用にはネットワークアクセスと認証情報が必要

適宜 pyproject.toml/requirements.txt がある前提で以下のようにインストールしてください（プロジェクトルートにいること）:

```bash
# 開発中にパッケージをインストール（編集可能）
pip install -e .

# 必要な最低パッケージを個別にインストールする例
pip install duckdb defusedxml
```

---

## 環境変数 / 設定

設定は環境変数またはプロジェクトルートの `.env` / `.env.local` から自動読み込みされます（自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定）。

主要な環境変数（Settings により参照）:

- J-Quants / データ取得
  - JQUANTS_REFRESH_TOKEN (必須)
- kabuステーション（発注連携など）
  - KABU_API_PASSWORD (必須)
  - KABU_API_BASE_URL (省略可、デフォルト: http://localhost:18080/kabusapi)
- Slack 通知
  - SLACK_BOT_TOKEN (必須)
  - SLACK_CHANNEL_ID (必須)
- DB パス
  - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
  - SQLITE_PATH (デフォルト: data/monitoring.db)
- 動作モード / ログ
  - KABUSYS_ENV (development | paper_trading | live) — default: development
  - LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL) — default: INFO

必須変数が未設定の場合、Settings のプロパティが ValueError を投げます。

---

## セットアップ手順（最短）

1. リポジトリをクローン／取得する
2. Python 環境を準備する（仮想環境を推奨）
3. 依存パッケージのインストール（例: duckdb, defusedxml）
4. 環境変数を用意する（.env を作成）
   - プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます
   - 例:
     ```
     JQUANTS_REFRESH_TOKEN=xxxxx
     KABU_API_PASSWORD=xxxxx
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     ```
5. DuckDB スキーマを初期化する（任意のパスを指定）
   - Python REPL やスクリプトから:
     ```python
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")
     ```
   - ":memory:" を渡せばインメモリ DB になります（テスト時に便利）。

---

## 使用例（よく使うワークフロー）

以下は代表的な Python API 呼び出し例です。

- 日次 ETL（市場カレンダー・株価・財務の差分取得、品質チェック）:
  ```python
  from datetime import date
  import duckdb
  from kabusys.data.schema import init_schema
  from kabusys.data.pipeline import run_daily_etl

  conn = init_schema("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

- 特徴量（features）構築:
  ```python
  from datetime import date
  from kabusys.strategy import build_features
  from kabusys.data.schema import get_connection

  conn = get_connection("data/kabusys.duckdb")
  count = build_features(conn, target_date=date.today())
  print("features upserted:", count)
  ```

- シグナル生成:
  ```python
  from datetime import date
  from kabusys.strategy import generate_signals
  from kabusys.data.schema import get_connection

  conn = get_connection("data/kabusys.duckdb")
  total = generate_signals(conn, target_date=date.today(), threshold=0.6)
  print("signals written:", total)
  ```

- RSS ニュース収集と保存（銘柄紐付けに known_codes を渡す）:
  ```python
  from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
  from kabusys.data.schema import get_connection

  conn = get_connection("data/kabusys.duckdb")
  known_codes = {"7203", "6758", "9432"}  # 例: 有効な銘柄コードセット
  results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
  print(results)
  ```

- カレンダー夜間更新ジョブ:
  ```python
  from kabusys.data.calendar_management import calendar_update_job
  from kabusys.data.schema import get_connection

  conn = get_connection("data/kabusys.duckdb")
  saved = calendar_update_job(conn)
  print("calendar saved:", saved)
  ```

注意: ここで使用している API は内部で DuckDB のテーブル存在やスキーマ初期化を前提とします。初回は先に init_schema() を呼んでテーブルを作成してください。

---

## 主要なモジュール / ディレクトリ構成

（実装ファイルの一部を抜粋しています）

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数/設定読み込みロジック、Settings
  - data/
    - __init__.py
    - jquants_client.py     — J-Quants API クライアント（取得・保存ユーティリティ）
    - schema.py             — DuckDB スキーマ定義・初期化
    - pipeline.py           — ETL パイプライン（run_daily_etl 等）
    - news_collector.py     — RSS 取得・前処理・保存
    - calendar_management.py— 市場カレンダー管理・営業日判定
    - features.py           — zscore_normalize の公開
    - stats.py              — zscore_normalize 等の統計ユーティリティ
    - audit.py              — 監査ログ用スキーマ
  - research/
    - __init__.py
    - factor_research.py    — momentum / volatility / value 等のファクター計算
    - feature_exploration.py— forward returns / IC / summary 等
  - strategy/
    - __init__.py
    - feature_engineering.py— features の合成・正規化（build_features）
    - signal_generator.py   — final_score の計算と signals 生成（generate_signals）
  - execution/              — （発注・約定処理用プレースホルダ）
  - monitoring/            — （監視・モニタリング用プレースホルダ）

---

## 設計上の注意点 / ポイント

- ルックアヘッドバイアス防止: ファクター・シグナル計算は target_date 時点で利用可能なデータのみを使う設計です。
- 冪等性: DB への保存は ON CONFLICT や日付単位のDELETE+INSERT で置換し、何度実行しても同一結果になるよう意識されています。
- セキュリティ / 安全性:
  - RSS 取得時は SSRF 対策、gzip サイズ制限、defusedxml を使用。
  - J-Quants API はレートリミットとリトライロジックを備えています。
- テストしやすさ:
  - ID トークンや HTTP 呼び出しを外部から注入（引数）できる箇所があります。
  - DuckDB の ":memory:" を使えば完全にメモリ上での単体テストが可能です。

---

## 開発・貢献

バグや改善提案、機能追加の要望は Issue として提起してください。コードスタイルやテストの方針はリポジトリ内の CONTRIBUTING や pyproject.toml を参照してください（存在する場合）。

---

必要であれば、この README に「実際の .env.example のテンプレート」や「よくあるトラブルシューティング（例: トークン刷新エラー、DuckDB の権限問題）」、さらに詳しい API リファレンス（関数ごとの引数/戻り値の具体例）を追記できます。どの項目を優先して追加しますか？