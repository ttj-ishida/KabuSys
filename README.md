# KabuSys

日本株向けの自動売買／データプラットフォーム用ライブラリ（KabuSys）。  
データ取得（J-Quants）、DuckDBベースのスキーマ管理、ETLパイプライン、ニュース収集、ファクター計算（リサーチ用）などのユーティリティ群を提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は日本株アルゴリズム売買のための内部ユーティリティ群を集合させたライブラリです。主に下記を目的としています。

- J-Quants API から株価・財務・市場カレンダーを取得して DuckDB に保存（冪等）
- DuckDB に対するスキーマ定義・初期化
- ETL（差分取得・バックフィル・品質チェック）の統合パイプライン
- RSS ベースのニュース収集と銘柄紐付け
- 研究用ファクター計算（モメンタム／ボラティリティ／バリュー等）と評価ユーティリティ（IC 計算、統計サマリー）
- マーケットカレンダー管理（営業日判定、次/前営業日取得）
- 環境変数ベースの設定管理（.env の自動読み込み機能あり）
- 監査ログ（発注〜約定のトレース）用スキーマ初期化ユーティリティ

設計方針として「DuckDB を中心に SQL + 最小限の Python ロジックで完結」「外部に発注する処理とは分離」「冪等性」「Look-ahead bias 防止のための fetched_at 記録」などを重視しています。

---

## 主な機能一覧

- 環境設定管理
  - .env/.env.local から自動読み込み（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）
  - 必須設定は取得時に明示的にエラー

- データアクセス / 取得
  - J-Quants API クライアント（レート制限・リトライ・トークン自動リフレッシュ対応）
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - 取得データを DuckDB に冪等保存する save_* 関数

- データ基盤
  - DuckDB スキーマ定義と初期化（raw / processed / feature / execution / audit 層）
  - init_schema, get_connection

- ETL パイプライン
  - run_daily_etl（カレンダー → 株価 → 財務 → 品質チェック）
  - 差分更新 / バックフィル（デフォルト 3 日）対応

- 品質チェック
  - 欠損データ、スパイク（前日比閾値）、重複、日付不整合などを検出
  - QualityIssue を返却し、致命度に応じて呼び出し側で判断可能

- ニュース収集
  - RSS フィード取得、前処理（URL除去、空白正規化）
  - 記事ID は正規化 URL の SHA-256（先頭32文字）で冪等化
  - SSRF 対策、gzip サイズ制限、defusedxml を用いた安全なXMLパース
  - raw_news 保存、news_symbols（記事⇄銘柄紐付け）

- 研究用（research）
  - calc_momentum / calc_volatility / calc_value（prices_daily / raw_financials を参照）
  - calc_forward_returns / calc_ic / factor_summary / rank
  - zscore_normalize（data.stats）でクロスセクション正規化

- マーケットカレンダー管理
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day
  - calendar_update_job（カレンダー差分更新ジョブ）

- 監査ログ（Audit）
  - signal_events / order_requests / executions 等の監査テーブルを初期化する init_audit_schema / init_audit_db

---

## セットアップ手順

前提:
- Python 3.10 以上（型注釈に | を使用しているため）
- DuckDB、defusedxml が必要（その他標準ライブラリのみで実装）

1. リポジトリをクローン（またはソースを入手）
   - 例: git clone <repo-url>

2. 仮想環境の作成と有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージのインストール
   - pip install duckdb defusedxml
   - （パッケージ配布がある場合）pip install -e .

4. 環境変数 / .env の準備
   - プロジェクトルート（pyproject.toml/.git があるディレクトリ）に .env を置くと自動読み込みされます。
   - 自動ロードを無効化する場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

.env の最低例（.env.example）
- JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
- KABU_API_PASSWORD=your_kabu_api_password
- KABU_API_BASE_URL=http://localhost:18080/kabusapi  # 必要に応じて
- SLACK_BOT_TOKEN=xoxb-...
- SLACK_CHANNEL_ID=C12345678
- DUCKDB_PATH=data/kabusys.duckdb
- SQLITE_PATH=data/monitoring.db
- KABUSYS_ENV=development  # development / paper_trading / live
- LOG_LEVEL=INFO

注意:
- settings から必須変数を取得するため、JQUANTS_REFRESH_TOKEN 等が未設定だと ValueError が発生します。

---

## 使い方（主要な利用例）

以下は代表的な利用例です。実行は Python スクリプト / ジョブとして組み込んでください。

- DuckDB スキーマ初期化

  ```python
  from kabusys.data.schema import init_schema
  from kabusys.config import settings

  conn = init_schema(settings.duckdb_path)  # Path オブジェクトでも文字列でも可
  ```

- 日次 ETL 実行（J-Quants から差分取得して保存・品質チェック）

  ```python
  from kabusys.data.pipeline import run_daily_etl
  from kabusys.data.schema import init_schema
  from kabusys.config import settings
  from datetime import date

  conn = init_schema(settings.duckdb_path)
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

- ニュース収集ジョブ実行

  ```python
  from kabusys.data.news_collector import run_news_collection
  from kabusys.data.schema import init_schema

  conn = init_schema("data/kabusys.duckdb")
  known_codes = {"7203", "6758", "9432"}  # 事前に有効銘柄コードセットを用意
  stats = run_news_collection(conn, known_codes=known_codes)
  print(stats)  # {source_name: saved_count}
  ```

- 研究用ファクター計算（例：モメンタム）

  ```python
  from kabusys.research import calc_momentum
  from kabusys.data.schema import get_connection
  from datetime import date

  conn = get_connection("data/kabusys.duckdb")
  records = calc_momentum(conn, target_date=date(2024, 1, 31))
  # records は各銘柄ごとの辞書リスト
  ```

- IC（Information Coefficient）計算例

  ```python
  from kabusys.research import calc_forward_returns, calc_ic, calc_momentum

  fwd = calc_forward_returns(conn, target_date=date(2024,1,31), horizons=[1])
  factors = calc_momentum(conn, target_date=date(2024,1,31))
  ic = calc_ic(factors, fwd, factor_col="mom_1m", return_col="fwd_1d")
  print(ic)
  ```

- 監査スキーマの初期化（発注／約定監査用）

  ```python
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/kabusys_audit.duckdb")
  ```

ログレベルや挙動は環境変数（LOG_LEVEL / KABUSYS_ENV）で制御します。KABUSYS_ENV の値は "development" / "paper_trading" / "live" のいずれかです。

---

## ディレクトリ構成（主なファイル・モジュール）

以下は src/kabusys 以下の主要モジュールと役割の一覧です。

- kabusys/
  - __init__.py
  - config.py
    - 環境変数読み込みと Settings クラス
  - data/
    - __init__.py
    - jquants_client.py
      - J-Quants API クライアント（取得・保存ユーティリティ）
    - news_collector.py
      - RSS 取得、記事前処理、raw_news / news_symbols 保存
    - schema.py
      - DuckDB スキーマ定義と init_schema / get_connection
    - stats.py
      - zscore_normalize 等の統計ユーティリティ
    - features.py
      - data.stats の公開ラッパー
    - pipeline.py
      - ETL の差分更新ロジックと run_daily_etl
    - quality.py
      - データ品質チェック（欠損・スパイク・重複・日付不整合）
    - calendar_management.py
      - カレンダー更新ジョブと営業日ユーティリティ
    - audit.py
      - 監査ログ用スキーマ初期化ユーティリティ
    - etl.py
      - ETLResult の再エクスポート
  - research/
    - __init__.py
      - 研究用 API のエクスポート
    - feature_exploration.py
      - 将来リターン計算 / IC / ランク / 要約統計
    - factor_research.py
      - momentum / volatility / value の計算
  - strategy/
    - __init__.py
    - （戦略モデルの実装はここに配置する想定）
  - execution/
    - __init__.py
    - （発注ロジック、ブローカー連携はここに実装）
  - monitoring/
    - __init__.py
    - （監視・メトリクス関連の実装予定）

---

## 注意事項 / 補足

- 本ライブラリはデータ取得と分析・ETL に重点を置いており、実際の証券会社への発注処理（実口座での自動売買）を直接行う部分は別途実装する想定です。発注処理や本番運用前には必ず十分な検証を行ってください。
- J-Quants API のレート制限・認証ルールに従う必要があります。get_id_token 等で設定ミスがあると例外が発生します。
- DuckDB のバージョンや挙動によっては制約やインデックス周りが異なる場合があります。README 内に明示している通り、DuckDB 1.5.x の制約（ON DELETE CASCADE 未サポート等）を考慮した設計になっています。
- セキュリティ:
  - news_collector は SSRF 対策や XML の安全パース（defusedxml）を実装していますが、実運用ではさらに監査・監視を行ってください。
  - .env に機密情報を保存する場合はファイル権限等に注意してください。

---

もし README に追加してほしいサンプルスクリプトや、CI / デプロイ手順（Docker, systemd ジョブ例など）があれば教えてください。必要に応じて例を追記します。