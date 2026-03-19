# KabuSys

日本株向け自動売買基盤ライブラリ（KabuSys）のリポジトリ向け README。  
このドキュメントはコードベース（src/kabusys）を参照して作成しています。実装済みのモジュール群を使って、データ取得（J-Quants）、ETL、特徴量作成、シグナル生成、ニュース収集、データベース初期化などを行えます。

---
## プロジェクト概要

KabuSys は日本株のクオンツ運用・自動売買システム向けのライブラリ群です。主な目的は以下です。

- J-Quants API から市場データ（株価・財務・カレンダー）を取得して DuckDB に保存する ETL パイプライン
- 研究で算出した生ファクターを正規化・統合して特徴量テーブルを作成する機能
- 特徴量・AI スコアを元に売買シグナルを生成するロジック
- RSS ベースのニュース収集と銘柄紐付け
- DuckDB に基づくスキーマ初期化・監査・実行レイヤの管理

設計上のポイント：
- ルックアヘッドバイアス防止（target_date 時点のデータのみ使用）
- 冪等（idempotent）保存（ON CONFLICT 等）
- API レート制御・リトライ・トークン自動更新などの堅牢性機能
- DuckDB を中心とした軽量オンプレ型データレイク

---
## 主な機能一覧

- 環境設定読み込み
  - .env / .env.local 自動ロード（プロジェクトルート検出）
  - 必須設定の取得 API（settings）
- データ収集（J-Quants）
  - 株価日足取得（ページネーション対応・レートリミット・リトライ）
  - 財務データ、JPX カレンダー取得
  - DuckDB への冪等保存（raw_prices / raw_financials / market_calendar 等）
- ETL パイプライン
  - 差分取得、バックフィル、品質チェックを含む日次 ETL（run_daily_etl）
- スキーマ管理
  - DuckDB の全テーブル・インデックスを初期化（init_schema）
- 特徴量処理（research / strategy）
  - モメンタム/ボラティリティ/バリュー等のファクター計算
  - Z スコア正規化ユーティリティ
  - features テーブルへの一括書込（build_features）
- シグナル生成
  - features, ai_scores, positions を元に final_score を計算し BUY/SELL シグナルを生成（generate_signals）
  - Bear レジーム抑制、エグジット判定（ストップロス等）
- ニュース収集
  - RSS 取得・安全対策（SSRF対策、XML デコード防御、サイズ上限）
  - raw_news / news_symbols への冪等保存
  - 銘柄コード抽出（4 桁コード）
- 監査・実行レイヤ
  - signal_events / order_requests / executions 等の監査テーブル定義

---
## セットアップ手順

前提：
- Python 3.8+（コードは typing の最新構文を利用しているため環境に合わせてください）
- DuckDB（Python パッケージ経由で利用）

1. リポジトリをクローン
   git clone <repo-url>
   cd <repo-root>

2. 開発環境インストール（例）
   - pip install -e . などでパッケージをインストールできる形にしている想定です。
   - 最低依存（必須）:
     - duckdb
     - defusedxml
   例:
     pip install duckdb defusedxml

   ※ 実際の requirements.txt は本コードには含まれていません。環境に応じて必要なライブラリを追加してください。

3. 環境変数設定
   - プロジェクトルートに `.env` を置くと自動で読み込まれます（.git または pyproject.toml を基準にルートを探索）。
   - 自動読み込みを無効にする場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

   必須変数（Settings で require されるもの）:
   - JQUANTS_REFRESH_TOKEN
   - KABU_API_PASSWORD
   - SLACK_BOT_TOKEN
   - SLACK_CHANNEL_ID

   任意 / デフォルトあり:
   - KABUSYS_ENV (development|paper_trading|live) — デフォルト: development
   - LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL) — デフォルト: INFO
   - DUCKDB_PATH — デフォルト: data/kabusys.duckdb
   - SQLITE_PATH — デフォルト: data/monitoring.db

   例 .env:
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   KABU_API_PASSWORD=your_kabu_api_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=CXXXXXXX
   KABUSYS_ENV=development
   DUCKDB_PATH=data/kabusys.duckdb
   LOG_LEVEL=DEBUG
   ```

4. DuckDB スキーマ初期化
   Python REPL やスクリプトで初期化できます。デフォルトパスは settings.duckdb_path（.env で変更可能）。

   例（コマンドライン）:
   ```
   python -c "from kabusys.data.schema import init_schema; init_schema('data/kabusys.duckdb')"
   ```

   メモリ DB（テスト用）:
   ```
   python -c "from kabusys.data.schema import init_schema; init_schema(':memory:')"
   ```

---
## 使い方（よく使う関数 / ワークフロー例）

以下は Python から直接呼び出すサンプルコード例です。適宜スクリプト化して運用してください。

1) DuckDB スキーマ初期化
```
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")
```

2) 日次 ETL 実行（J-Quants から差分取得して保存）
```
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn)  # target_date を指定可能
print(result.to_dict())
```

3) 特徴量作成（features テーブルへ UPSERT）
```
from kabusys.data.schema import init_schema
from kabusys.strategy import build_features
from datetime import date

conn = init_schema("data/kabusys.duckdb")
n = build_features(conn, target_date=date(2024, 1, 31))
print(f"upserted features: {n}")
```

4) シグナル生成（signals テーブルへ書き込み）
```
from kabusys.data.schema import init_schema
from kabusys.strategy import generate_signals
from datetime import date

conn = init_schema("data/kabusys.duckdb")
count = generate_signals(conn, target_date=date(2024, 1, 31))
print(f"signals written: {count}")
```

5) ニュース収集ジョブ
```
from kabusys.data.schema import init_schema
from kabusys.data.news_collector import run_news_collection

conn = init_schema("data/kabusys.duckdb")
known_codes = {"7203","6758","9984"}  # 有効な銘柄コードセット
res = run_news_collection(conn, known_codes=known_codes)
print(res)
```

6) J-Quants 生データ取得（テスト的に直接）
```
from kabusys.data.jquants_client import fetch_daily_quotes, fetch_financial_statements
# settings.jquants_refresh_token を .env で設定しておくこと
quotes = fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
```

7) テスト / 開発時の設定
- 自動 .env ロードを無効化: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- DuckDB をインメモリで使えば副作用なく単体関数を実行できます（init_schema(':memory:')）。

---
## 重要な設計・運用上の注意

- 環境 (KABUSYS_ENV): "development", "paper_trading", "live" のいずれか。live 時は実取引に繋がる設定や挙動を厳密に確認してください。
- 冪等性: 多くの保存関数は ON CONFLICT により冪等化されていますが、外部の発注 API と連携する際は運用側で更なる二重発注回避対策（order_request_id の利用等）を行ってください。
- API 認証情報は厳重に管理してください（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, Slack トークン等）。
- ニュース収集では SSRF 対策や XML 脆弱性対策を組み込んでいますが、外部 URL を扱うため運用時の監視を推奨します。

---
## ディレクトリ構成

主要ファイル・モジュール構成（src/kabusys）:

- src/kabusys/
  - __init__.py
  - config.py                       — 環境変数 / Settings
  - data/
    - __init__.py
    - jquants_client.py              — J-Quants API クライアント（取得 + 保存）
    - news_collector.py              — RSS ニュース収集・DB 保存
    - schema.py                      — DuckDB スキーマ定義・初期化
    - pipeline.py                    — ETL パイプライン（run_daily_etl 等）
    - features.py                    — zscore_normalize の再エクスポート
    - stats.py                       — 統計ユーティリティ（zscore_normalize）
    - calendar_management.py         — 市場カレンダー管理
    - audit.py                       — 監査ログDDL
    - pipeline.py (ETL ロジック)
  - research/
    - __init__.py
    - factor_research.py             — momentum/volatility/value のファクター計算
    - feature_exploration.py         — 将来リターン / IC / 統計サマリー
  - strategy/
    - __init__.py
    - feature_engineering.py         — features テーブル作成（build_features）
    - signal_generator.py            — シグナル生成（generate_signals）
  - execution/
    - __init__.py
    # （発注実装は execution 層で実施する想定。ただし本コード内では発注API連携実装は省略）
  - monitoring/
    # 監視・Slack 通知等を実装するモジュールを想定

（実際のファイルはリポジトリ内に一覧のとおり存在します）

---
## 開発・貢献

- バグ報告や機能追加は Issue / PR でお願いします。
- コードはドキュメント文字列・コメントが豊富にあるため、それに沿って実装やテストを追加してください。
- テストはユニットテストで DuckDB の :memory: 接続を利用し外部 API 呼び出しをモックすることを推奨します。

---
## ライセンス

本 README はコードベースの説明用です。実際のリポジトリでは LICENSE ファイルをご確認ください。

---

必要であれば、README に以下を追加できます：
- 具体的な CLI スクリプト例（サービス化・cron 定義）
- Docker/コンテナ化手順
- 運用チェックリスト（監視・Slack 通知の設定例）
どれを追加したいか教えてください。