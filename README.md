# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリです。  
データ取得（J-Quants） → ETL（DuckDB） → 特徴量生成 → シグナル生成 → 発注／監視の各層を想定したモジュール群を提供します。

主な設計方針：
- ルックアヘッドバイアスを避ける設計（target_date 時点のデータのみ使用）
- DuckDB によるローカル DB（冪等保存、トランザクション保護）
- API レート制御・再試行・トークン自動リフレッシュ等を備えた J-Quants クライアント
- RSS ニュース収集の堅牢化（SSRF対策、トラッキング除去、重複排除）

バージョン: 0.1.0

---

## 機能一覧

- 環境変数管理（.env 自動読み込み、必須チェック）
  - 自動ロード: プロジェクトルートの `.env` / `.env.local`（KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可）
- データ取得（J-Quants API）
  - 株価日足、財務データ、マーケットカレンダーのフェッチ（ページネーション対応）
  - レートリミット管理、リトライ、401 トークン再取得対応
  - DuckDB への冪等保存（ON CONFLICT DO UPDATE）
- ETL パイプライン
  - 日次 ETL（市場カレンダー→株価→財務 → 品質チェック）
  - 差分更新 / バックフィル機能
- DuckDB スキーマ定義 / 初期化
  - Raw / Processed / Feature / Execution 層のテーブル定義
- 研究用ファクター計算（research）
  - momentum / volatility / value 等のファクター計算関数
  - 将来リターン計算、IC（Spearman）や統計サマリー
- 特徴量エンジニアリング（strategy）
  - ファクター正規化（Zスコア）、ユニバースフィルタ、features テーブルへの upsert
- シグナル生成（strategy）
  - features と ai_scores を統合し final_score を算出、BUY/SELL シグナル生成、SELL (exit) 判定
- ニュース収集（RSS）
  - RSS 取得、前処理、ID 生成、raw_news 保存、銘柄抽出（4桁コード）
- 監査ログ（audit） & 実行層スキーマ（orders / trades / positions 等）
- 汎用統計ユーティリティ（zscore_normalize 等）

---

## セットアップ手順

前提：Python 3.9+、pip が利用可能であること。

1. リポジトリをクローン
   - git clone ...（リポジトリ URL）

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - 例（必要なパッケージの代表例）
     - duckdb
     - defusedxml
   - pip install duckdb defusedxml
   - 開発モードでインストール可能なら:
     - pip install -e .

   > 実プロジェクトでは requirements.txt / pyproject.toml に依存を定義してください。

4. 環境変数 / .env の準備  
   プロジェクトルートに `.env`（および `.env.local`、任意）を配置すると自動読み込みされます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。必須の環境変数は読み込み時にアクセスすると例外が発生します。

   最低限設定が必要な変数（例）:
   - JQUANTS_REFRESH_TOKEN=...
   - KABU_API_PASSWORD=...
   - SLACK_BOT_TOKEN=...
   - SLACK_CHANNEL_ID=...

   任意 / デフォルト:
   - KABUSYS_ENV=development | paper_trading | live  （デフォルト: development）
   - LOG_LEVEL=INFO（DEBUG/INFO/WARNING/ERROR/CRITICAL）
   - DUCKDB_PATH=data/kabusys.duckdb（デフォルト）
   - SQLITE_PATH=data/monitoring.db（監視用）

   サンプル .env:
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   DUCKDB_PATH=data/kabusys.duckdb
   ```

5. DB スキーマ初期化（DuckDB）
   - 以下は Python から実行する例（REPL / スクリプト）:
     ```python
     from kabusys.data.schema import init_schema
     from kabusys.config import settings

     conn = init_schema(settings.duckdb_path)
     ```

---

## 使い方（主要 API の例）

以下は代表的な処理のサンプルコード例です。実際はアプリケーション内で適切にラップして使用してください。

- 日次 ETL の実行（市場カレンダー・株価・財務＋品質チェック）
  ```python
  from datetime import date
  from kabusys.data.schema import init_schema
  from kabusys.data.pipeline import run_daily_etl
  from kabusys.config import settings

  conn = init_schema(settings.duckdb_path)
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

- 特徴量作成（features テーブルへの書き込み）
  ```python
  from datetime import date
  from kabusys.data.schema import get_connection
  from kabusys.strategy import build_features
  from kabusys.config import settings

  conn = get_connection(settings.duckdb_path)
  count = build_features(conn, target_date=date.today())
  print(f"features upserted: {count}")
  ```

- シグナル生成
  ```python
  from datetime import date
  from kabusys.data.schema import get_connection
  from kabusys.strategy import generate_signals
  from kabusys.config import settings

  conn = get_connection(settings.duckdb_path)
  total_signals = generate_signals(conn, target_date=date.today(), threshold=0.6)
  print(f"signals generated: {total_signals}")
  ```

- ニュース収集ジョブ（RSS）
  ```python
  from kabusys.data.news_collector import run_news_collection
  from kabusys.data.schema import get_connection
  from kabusys.config import settings

  conn = get_connection(settings.duckdb_path)
  results = run_news_collection(conn, sources=None, known_codes=None)
  print(results)
  ```

- J-Quants のデータフェッチ（低レベル）
  ```python
  from kabusys.data import jquants_client as jq

  # トークンは settings による自動取得/リフレッシュに対応
  daily = jq.fetch_daily_quotes(date_from=..., date_to=...)
  ```

注意点：
- 各種関数は DuckDB の接続オブジェクト（DuckDBPyConnection）を受け取ります。接続は init_schema / get_connection で取得してください。
- run_daily_etl など主要関数は内部で例外を捕捉して継続する設計ですが、戻り値（ETLResult）を確認し問題がないかを判断してください。

---

## ディレクトリ構成

主要なファイル／モジュールのツリー（src/kabusys）:

- kabusys/
  - __init__.py
  - config.py                         -- 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py               -- J-Quants API クライアント + 保存ロジック
    - news_collector.py               -- RSS 収集・DB保存・銘柄抽出
    - schema.py                       -- DuckDB スキーマ定義・初期化
    - stats.py                        -- 統計ユーティリティ（zscore_normalize）
    - pipeline.py                     -- ETL パイプライン（run_daily_etl 等）
    - features.py                     -- features 用再エクスポート
    - calendar_management.py          -- カレンダー管理 / 営業日判定
    - audit.py                        -- 監査ログ用スキーマ
    - ...（その他の data 関連モジュール）
  - research/
    - __init__.py
    - factor_research.py              -- momentum / volatility / value 計算
    - feature_exploration.py          -- 将来リターン / IC / summary
  - strategy/
    - __init__.py
    - feature_engineering.py          -- features の作成（正規化・フィルタ）
    - signal_generator.py             -- final_score 計算・BUY/SELL 生成
  - execution/                         -- 発注・実行層（パッケージプレースホルダ）
  - monitoring/                        -- 監視機能（DB/Slack 等、実装想定）

上記に加え、プロジェクトルートに .env / pyproject.toml / requirements.txt 等を置く想定です。

---

## 補足・運用上の注意

- .env の自動ロードはプロジェクトルートの検出によるため、CWD に依存せず動作します。テスト等で自動ロードを無効にする場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- KABUSYS_ENV により挙動（paper_trading / live 等）を分ける想定です。settings.is_live / is_paper を使用してコード内で分岐可能です。
- DuckDB のファイルパス（settings.duckdb_path）はデフォルトで data/kabusys.duckdb。初期化時に親ディレクトリが自動作成されます。
- ニュース収集時は既知銘柄リスト（known_codes）を渡すことで記事と銘柄の紐付けが行えます。
- J-Quants API 利用時はレート制限（120 req/min）に注意。クライアントはこれを尊重する実装になっています。

---

問題の報告や機能追加、ドキュメント改善の提案があれば issue を立ててください。README のサンプルコードは運用環境に合わせて適宜ラップ・例外処理・ログ出力を追加して使用してください。