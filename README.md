# KabuSys

日本株向けの自動売買プラットフォーム向けライブラリ群です。データ取得・ETL、特徴量生成、シグナル生成、ニュース収集、マーケットカレンダー管理、発注監査などのコンポーネントを含み、研究（research）→データ（data）→戦略（strategy）→実行（execution）につながるワークフローを提供します。

主な設計方針
- ルックアヘッドバイアスを避ける（各処理は target_date 時点のデータのみを使用）
- DuckDB をローカルデータストアとして利用（冪等性とトランザクションを重視）
- 外部 API 呼び出しはクライアント層（jquants_client 等）に集約
- テスト性を考慮してトークン注入や自動ロードの抑止を可能にする

---

## 機能一覧（抜粋）
- データ取得・保存
  - J-Quants API クライアント（株価・財務・マーケットカレンダー取得、ページネーション・リトライ・レート制御）
  - raw テーブルへの冪等保存（ON CONFLICT / upsert）
- ETL / パイプライン
  - 差分取得（最終取得日に基づく差分更新・バックフィル）
  - 日次 ETL 実行（calendar / prices / financials + 品質チェック）
- データスキーマ管理
  - DuckDB スキーマ定義・初期化（raw / processed / feature / execution 層）
- 特徴量（feature）処理
  - research 層で計算した raw factor を正規化・合成して features テーブルへ保存
  - Z スコア正規化ユーティリティ
- シグナル生成
  - features と ai_scores を組み合わせて final_score を計算、BUY/SELL シグナル作成
  - Bear レジーム判定、ストップロス等のエグジット条件
- ニュース収集
  - RSS フィード取得・前処理・raw_news 保存、記事と銘柄コードの紐付け
  - SSRF 対策や XML 爆弾対策、受信サイズ制限など堅牢な実装
- マーケットカレンダー管理
  - JPX カレンダーの差分更新、営業日判定ユーティリティ（next/prev/get_trading_days 等）
- 監査ログ（audit）
  - signal → order_request → execution のトレーサビリティテーブル定義

---

## 必要条件
- Python 3.10+
- DuckDB
- defusedxml
- （プロジェクトの実行に応じて）ネットワークアクセス（J-Quants API、RSS）

代表的な Python パッケージ（requirements.txt 例）
- duckdb
- defusedxml

（実際の pyproject.toml / requirements.txt がある場合はそちらを参照してください）

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローンしてワークディレクトリへ移動
   - git clone ...
   - cd <repo>

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  # macOS / Linux
   - .venv\Scripts\activate     # Windows

3. 依存パッケージのインストール
   - pip install duckdb defusedxml
   - （プロジェクトに requirements.txt / pyproject.toml があればそれを使用）

4. 環境変数（.env）を作成
   プロジェクトルートに `.env` または `.env.local` を置くと自動で読み込まれます（自動読み込みを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセット）。

   必須環境変数（例）
   - JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   - KABU_API_PASSWORD=your_kabu_api_password
   - SLACK_BOT_TOKEN=your_slack_bot_token
   - SLACK_CHANNEL_ID=your_slack_channel_id

   任意（デフォルトあり）
   - KABU_API_BASE_URL (default: http://localhost:18080/kabusapi)
   - DUCKDB_PATH (default: data/kabusys.duckdb)
   - SQLITE_PATH (default: data/monitoring.db)
   - KABUSYS_ENV (development | paper_trading | live) (default: development)
   - LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL) (default: INFO)

   .env の例:
   ```
   JQUANTS_REFRESH_TOKEN=xxxx
   KABU_API_PASSWORD=yyyy
   SLACK_BOT_TOKEN=zzzz
   SLACK_CHANNEL_ID=CCCCCC
   DUCKDB_PATH=data/kabusys.duckdb
   ```

5. データベーススキーマの初期化（DuckDB）
   Python から実行例:
   ```python
   from kabusys.data.schema import init_schema
   init_schema("data/kabusys.duckdb")
   ```

---

## 使い方（主要な操作例）

- 日次 ETL 実行（J-Quants からデータ取得して保存）
  ```python
  from datetime import date
  import duckdb
  from kabusys.data.schema import init_schema
  from kabusys.data.pipeline import run_daily_etl

  conn = init_schema("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

- 特徴量のビルド（strategy.feature_engineering.build_features）
  ```python
  from datetime import date
  from kabusys.strategy import build_features
  from kabusys.data.schema import get_connection

  conn = get_connection("data/kabusys.duckdb")
  count = build_features(conn, target_date=date(2024, 1, 5))
  print(f"upserted features: {count}")
  ```

- シグナル生成（strategy.signal_generator.generate_signals）
  ```python
  from datetime import date
  from kabusys.strategy import generate_signals
  from kabusys.data.schema import get_connection

  conn = get_connection("data/kabusys.duckdb")
  n_signals = generate_signals(conn, target_date=date(2024, 1, 5))
  print(f"signals written: {n_signals}")
  ```

- ニュース収集ジョブの実行（RSS を取得して保存）
  ```python
  from kabusys.data.news_collector import run_news_collection
  from kabusys.data.schema import get_connection

  conn = get_connection("data/kabusys.duckdb")
  known_codes = {"7203", "6758", "9984"}  # 例: 有効な銘柄コードセット
  results = run_news_collection(conn, known_codes=known_codes)
  print(results)
  ```

- マーケットカレンダー更新
  ```python
  from kabusys.data.calendar_management import calendar_update_job
  from kabusys.data.schema import get_connection

  conn = get_connection("data/kabusys.duckdb")
  saved = calendar_update_job(conn)
  print(f"calendar saved: {saved}")
  ```

備考
- 多くの関数は DuckDB の接続オブジェクト（duckdb.DuckDBPyConnection）を受け取ります。init_schema はスキーマを初期化して接続を返します。get_connection は既存 DB への接続を返します（初回は init_schema を推奨）。
- jquants_client の API 呼び出しは id_token を内部で管理・リフレッシュします。テスト時は id_token を明示的に渡してモックすることが可能です。

---

## 主要モジュールとディレクトリ構成

リポジトリの主要なファイル・モジュール（src/kabusys 以下を抜粋）

- kabusys/
  - __init__.py
  - config.py
    - 環境変数管理（.env 自動ロード、必須チェック）
  - data/
    - __init__.py
    - jquants_client.py        -- J-Quants API クライアント（取得・保存ユーティリティ）
    - news_collector.py       -- RSS 取得と raw_news 保存、銘柄抽出
    - schema.py               -- DuckDB スキーマ定義・初期化
    - stats.py                -- zscore_normalize 等の統計ユーティリティ
    - features.py             -- data.stats の再エクスポート
    - pipeline.py             -- ETL パイプライン（run_daily_etl 等）
    - calendar_management.py  -- カレンダー更新・営業日ユーティリティ
    - audit.py                -- 監査ログ用テーブル DDL（signal_events / order_requests / executions）
    - (その他: quality.py 等を想定)
  - research/
    - __init__.py
    - factor_research.py      -- calc_momentum / calc_volatility / calc_value
    - feature_exploration.py  -- calc_forward_returns / calc_ic / factor_summary / rank
  - strategy/
    - __init__.py
    - feature_engineering.py  -- build_features（ファクター統合・Zスコア正規化）
    - signal_generator.py     -- generate_signals（final_score 計算、BUY/SELL 判定）
  - execution/                -- 発注・ブローカー連携（骨組み）
  - monitoring/               -- 監視・モニタリング用（DB監視やSlack通知などを想定）

（上記はコードベースから抽出した主要ファイルの一覧です。細部は実際のリポジトリを参照してください。）

---

## 開発メモ / 注意点
- env 自動読み込み
  - config.py はプロジェクトルート（.git または pyproject.toml が見つかる場所）から `.env` / `.env.local` を自動読み込みします。テストや CI で自動読み込みを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- 冪等性
  - データベース保存は基本的に ON CONFLICT / DO UPDATE / DO NOTHING を利用して冪等化しています。ETL は部分失敗があっても他処理を継続する設計です。
- 時刻 / タイムゾーン
  - 監査ログや取得時刻は UTC ベースで記録する方針です（jquants の fetched_at は UTC 表示）。
- セキュリティ
  - news_collector は SSRF や XML 攻撃対策（defusedxml、リダイレクト時のホスト検査、受信サイズ制限）を実装しています。

---

## よくある操作（クイックレファレンス）
- DB 初期化:
  - from kabusys.data.schema import init_schema; init_schema("data/kabusys.duckdb")
- ETL 実行:
  - from kabusys.data.pipeline import run_daily_etl; run_daily_etl(conn)
- 特徴量作成:
  - from kabusys.strategy import build_features; build_features(conn, date)
- シグナル作成:
  - from kabusys.strategy import generate_signals; generate_signals(conn, date)

---

必要であれば README に追記する内容（例）
- 実運用でのデプロイ手順（systemd / cron / Airflow 例）
- テスト実行方法（pytest）
- CI / CD の設定例
- より詳細な環境変数テンプレート（.env.example）
- サンプル SQL や DuckDB クエリの例

追加で必要な項目や、README の翻訳/整形（英語版の併記など）があれば教えてください。