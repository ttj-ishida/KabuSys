# KabuSys

日本株向け自動売買基盤ライブラリ（Python）

このリポジトリは、J-Quants / kabu ステーション等を用いたデータプラットフォーム、特徴量生成、シグナル生成、ETL、ニュース収集、監査ログ等を含む自動売買基盤のコアロジックを提供します。研究用モジュール（research）と実運用を想定したデータ/戦略/実行レイヤーが含まれます。

バージョン: 0.1.0

---

## 主要な機能

- データ取得・保存
  - J-Quants API クライアント（差分取得・ページネーション・リトライ・レート制御）
  - DuckDB への冪等保存（ON CONFLICT を用いた upsert）
  - 市場カレンダーの管理
  - RSS ベースのニュース収集（SSRF対策・XMLデコード対策・URL正規化・銘柄紐付け）

- ETL パイプライン
  - 日次 ETL（市場カレンダー、株価、財務データの差分取得＋保存）
  - 品質チェックを組み込んだ実行フロー

- リサーチ / 特徴量
  - モメンタム / ボラティリティ / バリュー系ファクター計算
  - クロスセクション Z スコア正規化ユーティリティ
  - 将来リターン計算・IC（Spearman）などの探索ユーティリティ

- 戦略
  - 特徴量の作成（build_features）
  - AI スコアと統合したシグナル生成（generate_signals）
  - BUY / SELL の判定ロジック（ストップロス、Bear レジーム抑制 等）

- データベーススキーマ & 監査
  - DuckDB 用スキーマ定義（Raw / Processed / Feature / Execution 層）
  - 監査ログ（signal_events / order_requests / executions 等）

---

## 必要条件

- Python 3.10+
- 依存パッケージ（主なもの）
  - duckdb
  - defusedxml

その他は標準ライブラリの urllib 等を使用。pip でインストールしてください。

例:
pip install duckdb defusedxml

（プロジェクトに setup/pyproject があれば pip install -e . で依存を追加します）

---

## 環境変数（設定）

設定は環境変数またはプロジェクトルートの `.env` / `.env.local` から自動読み込みされます（デフォルト）。自動読み込みを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

必須の環境変数:
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
- KABU_API_PASSWORD : kabuステーション API のパスワード
- SLACK_BOT_TOKEN : Slack Bot トークン（通知等に使用）
- SLACK_CHANNEL_ID : 通知先 Slack チャネル ID

任意 / デフォルト値あり:
- KABU_API_BASE_URL : kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH : 監視用 SQLite（デフォルト: data/monitoring.db）
- KABUSYS_ENV : one of development / paper_trading / live（デフォルト: development）
- LOG_LEVEL : DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）

.example `.env`（README 用サンプル）:
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO

---

## セットアップ手順

1. リポジトリをクローン
   git clone <repo-url>
   cd <repo>

2. Python 仮想環境を作成・有効化（推奨）
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows

3. 依存パッケージをインストール
   pip install duckdb defusedxml

   （もし pyproject.toml/setup.cfg があれば）
   pip install -e .

4. 環境変数を設定
   - プロジェクトルートに `.env` を作成するか、OS 環境変数を設定します。
   - 自動ロードを無効にしたいテスト等のときは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

5. DuckDB スキーマ初期化
   Python REPL やスクリプトから実行します（例は下記）。

---

## 使い方（基本例）

以下は代表的な操作例です。各関数は duckdb 接続オブジェクト（kabusys.data.schema.init_schema / get_connection）を受け取ります。

- DB 初期化（スキーマ作成）
  from kabusys.data.schema import init_schema
  from kabusys.config import settings

  conn = init_schema(settings.duckdb_path)

- 日次 ETL 実行（J-Quants から差分取得して DB に保存）
  from kabusys.data.pipeline import run_daily_etl
  result = run_daily_etl(conn)  # 引数 target_date を指定可能
  print(result.to_dict())

- 特徴量生成（features テーブルの作成）
  from kabusys.strategy import build_features
  from datetime import date
  cnt = build_features(conn, date(2025, 1, 31))
  print(f"features processed: {cnt}")

- シグナル生成（signals テーブルへ書き込み）
  from kabusys.strategy import generate_signals
  from datetime import date
  total = generate_signals(conn, date(2025, 1, 31))
  print(f"signals written: {total}")

- ニュース収集ジョブの実行（RSS 収集 → raw_news 保存 → 銘柄紐付け）
  from kabusys.data.news_collector import run_news_collection
  known_codes = {"7203", "6758", "9984"}  # 既知銘柄コードセット
  res = run_news_collection(conn, known_codes=known_codes)
  print(res)

- カレンダー更新ジョブ
  from kabusys.data.calendar_management import calendar_update_job
  saved = calendar_update_job(conn)
  print(f"market_calendar saved={saved}")

- DuckDB 接続を直接取得する場合
  from kabusys.data.schema import get_connection
  conn = get_connection("data/kabusys.duckdb")

注意:
- これらの関数は I/O（ネットワーク／DB）を行うため、実運用時は例外ハンドリングやログ管理を適切に行ってください。
- generate_signals / build_features はトランザクションで日付単位の置換（冪等）を行います。

---

## 開発者向けメモ

- 自動環境変数ロード
  - パッケージはインポート時にプロジェクトルート（.git または pyproject.toml）から `.env` / `.env.local` を自動読み込みします。
  - テストや CI で自動読み込みを無効にする場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` をセットしてください。

- ログレベル
  - settings.log_level で設定を取得できます。環境変数 LOG_LEVEL を設定してください。

- Python バージョン
  - type hint に union 型（|）などを使用しています。Python 3.10 以上を想定しています。

- テスト
  - 各ネットワーク呼び出し（jquants_client._request、news_collector._urlopen 等）はモック可能な設計になっています。ユニットテストでは外部依存をモックして実行してください。

---

## ディレクトリ構成

以下はリポジトリ内の主要なファイル／モジュール構成（抜粋）です。

- src/kabusys/
  - __init__.py
  - config.py                         -- 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py               -- J-Quants API クライアント（取得・保存）
    - news_collector.py               -- RSS ニュース収集と DB 保存
    - schema.py                       -- DuckDB スキーマ定義・初期化
    - pipeline.py                     -- ETL パイプライン（run_daily_etl 等）
    - stats.py                        -- 統計ユーティリティ（zscore_normalize）
    - features.py                     -- features の公開インターフェース
    - calendar_management.py          -- 市場カレンダー管理とジョブ
    - audit.py                        -- 監査ログ用スキーマ
    - ...（その他実装ファイル）
  - research/
    - __init__.py
    - factor_research.py              -- momentum/volatility/value の計算
    - feature_exploration.py          -- IC・前方リターン・summary 等
  - strategy/
    - __init__.py
    - feature_engineering.py          -- build_features（ファクター正規化）
    - signal_generator.py             -- generate_signals（BUY/SELL 判定）
  - execution/                         -- 発注/約定/ポジション管理層（空のパッケージ）
  - monitoring/                        -- 監視／アラート層（必要に応じて実装）

---

## ライセンス / 貢献

このリポジトリのライセンス情報は別ファイル（LICENSE）を参照してください。  
バグ報告・機能リクエストは issue を通してお願いします。

---

README に書かれているコマンド・コード例は利用環境に応じて適宜修正してください。実運用で外部 API を叩く場合は認証情報の管理と適切な監視を行ってください。