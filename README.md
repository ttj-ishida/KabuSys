# KabuSys

日本株のデータ取得・特徴量生成・シグナル生成・監査/実行管理を目的とした自動売買支援ライブラリ群です。DuckDB をデータ層に採用し、J-Quants API や RSS ニュースなどからデータを収集して、戦略（feature -> signal）までの処理をモジュール化しています。

主な設計方針：
- ルックアヘッドバイアスを防ぐ（target_date 時点のデータのみ参照）
- DuckDB への保存は冪等（ON CONFLICT / UPSERT）で実行
- API 呼び出しはレート制限・リトライ・自動トークンリフレッシュ対応
- システム設定は環境変数/.env で管理（自動ロード機能あり）

---

## 主な機能一覧

- データ取得・保存
  - J-Quants から株価日足（OHLCV）、財務データ、マーケットカレンダーを取得（jquants_client）
  - RSS からニュース収集して raw_news に保存（news_collector）
  - DuckDB スキーマ定義と初期化（data.schema.init_schema）
  - ETL（差分取得、バックフィル、品質チェック）を実行するパイプライン（data.pipeline）
- 研究 / ファクター計算
  - モメンタム / ボラティリティ / バリューなどのファクター計算（research.factor_research）
  - 将来リターン計算・IC（Spearman）計算・統計サマリー（research.feature_exploration）
- 特徴量生成・シグナル生成（strategy）
  - 生ファクターの正規化・ユニバースフィルタを適用して features テーブルに保存（strategy.feature_engineering.build_features）
  - features と ai_scores を統合して final_score を計算、BUY/SELL シグナルを signals テーブルに保存（strategy.signal_generator.generate_signals）
- カレンダー管理、ニュース銘柄抽出、監査ログ/実行テーブル等の補助機能
- ログ出力・設定管理（config.Settings）

---

## 必要条件

- Python 3.9+（コード中の型注釈と記述に基づく想定）
- 必須ライブラリ（例）
  - duckdb
  - defusedxml
- ネットワークアクセス（J-Quants API、RSS ソース）を行う場合は適切な API トークン・ネットワーク設定

（実際のプロジェクトでは requirements.txt / pyproject.toml を参照して依存解決してください）

---

## セットアップ手順（ローカル開発用）

1. リポジトリをクローンし、仮想環境を作成
   ```bash
   git clone <repo-url>
   cd <repo>
   python -m venv .venv
   source .venv/bin/activate
   ```

2. 必要パッケージをインストール（例）
   ```bash
   pip install duckdb defusedxml
   # あるいはプロジェクトのパッケージを編集可能インストール
   pip install -e .
   ```

3. 環境変数を設定（.env をプロジェクトルートに配置することで自動読み込みされます）
   - 自動ロードはデフォルト有効（project root に .git または pyproject.toml がある場合）
   - 無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定

   例 `.env`（安全な場所で管理してください）
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C0123456789
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   KABUSYS_ENV=development  # development | paper_trading | live
   LOG_LEVEL=INFO
   ```

4. DuckDB スキーマ初期化
   - Python コンソールやスクリプトからスキーマを作成します：
   ```python
   from kabusys.data.schema import init_schema
   from kabusys.config import settings

   conn = init_schema(settings.duckdb_path)  # ファイル DB を初期化して接続を返す
   ```

---

## 基本的な使い方（コード例）

以下は代表的な処理フローの例です。すべて DuckDB 接続（duckdb.DuckDBPyConnection）を受け取る形で実行できます。

1. 日次 ETL（市場カレンダー・株価・財務の差分取得）
   ```python
   from kabusys.data.schema import init_schema
   from kabusys.data.pipeline import run_daily_etl

   conn = init_schema("data/kabusys.duckdb")
   result = run_daily_etl(conn)  # target_date を指定可能
   print(result.to_dict())
   ```

2. 特徴量（features）生成
   ```python
   from kabusys.strategy import build_features
   from kabusys.data.schema import get_connection
   from datetime import date

   conn = get_connection("data/kabusys.duckdb")
   cnt = build_features(conn, target_date=date(2025, 1, 15))
   print(f"features upserted: {cnt}")
   ```

3. シグナル生成
   ```python
   from kabusys.strategy import generate_signals
   from kabusys.data.schema import get_connection
   from datetime import date

   conn = get_connection("data/kabusys.duckdb")
   total = generate_signals(conn, target_date=date(2025,1,15), threshold=0.6)
   print(f"signals written: {total}")
   ```

4. ニュース収集（RSS）
   ```python
   from kabusys.data.news_collector import run_news_collection
   from kabusys.data.schema import get_connection

   conn = get_connection("data/kabusys.duckdb")
   known_codes = {"7203", "6758", "9984"}  # 有効な銘柄コードセット（任意）
   results = run_news_collection(conn, known_codes=known_codes)
   print(results)  # 各ソースごとの新規保存数
   ```

5. カレンダー更新ジョブ（夜間バッチ）
   ```python
   from kabusys.data.calendar_management import calendar_update_job
   from kabusys.data.schema import get_connection

   conn = get_connection("data/kabusys.duckdb")
   saved = calendar_update_job(conn)
   print(f"calendar saved: {saved}")
   ```

6. J-Quants API を直接利用してデータをフェッチ
   ```python
   from kabusys.data.jquants_client import fetch_daily_quotes
   quotes = fetch_daily_quotes(date_from=date(2025,1,1), date_to=date(2025,1,15))
   ```

---

## 重要な環境変数（要設定）

- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API のパスワード（必須）
- SLACK_BOT_TOKEN: Slack 通知用 bot トークン（必須）
- SLACK_CHANNEL_ID: 通知先チャネル ID（必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV: 環境（development / paper_trading / live）
- LOG_LEVEL: ログレベル（DEBUG, INFO, WARNING, ERROR, CRITICAL）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1: .env の自動ロードを無効化

config.Settings クラスを通じてアプリケーション全体で使用されます。必須値が未設定の場合は ValueError が投げられます。

---

## 開発・運用に関するメモ

- DuckDB の初期化は `init_schema()` を一度実行してから通常の `get_connection()` を使って接続してください。
- jquants_client は内部で ID トークンをキャッシュし、自動リフレッシュ・リトライ・レート制御を行います。
- news_collector は RSS の解析に defusedxml を使用し、SSRF/Zip爆弾などに対する対策を組み込んでいます。
- strategy 側は直接発注を行わず、signals テーブルを更新します。実際の発注は execution 層で管理する想定です。
- KABUSYS_ENV が `live` のときは実運用フラグとして利用できます。発注などを自動化する際はこのフラグを参照して安全設計してください。

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py                     -- 環境変数・設定管理
- data/
  - __init__.py
  - jquants_client.py            -- J-Quants API クライアント（取得 + 保存）
  - news_collector.py            -- RSS ニュース収集・前処理・DB 保存
  - pipeline.py                  -- ETL パイプライン（run_daily_etl 等）
  - schema.py                    -- DuckDB スキーマ定義・初期化
  - stats.py                     -- 統計ユーティリティ（zscore_normalize）
  - features.py                  -- features へのインターフェース再エクスポート
  - calendar_management.py       -- 市場カレンダー管理（next_trading_day 等）
  - audit.py                     -- 監査ログ用テーブル定義
  - ...（その他）
- research/
  - __init__.py
  - factor_research.py           -- モメンタム/ボラティリティ/バリュー計算
  - feature_exploration.py       -- 将来リターン・IC・統計サマリー
- strategy/
  - __init__.py
  - feature_engineering.py       -- features 作成（正規化・ユニバースフィルタ）
  - signal_generator.py          -- final_score 計算・BUY/SELL 生成
- execution/                      -- 発注・約定・ポジション管理（骨格）
- monitoring/                     -- 監視・メトリクス（予定/補助）

（実際のリポジトリではさらにユーティリティやモジュールが存在します）

---

## トラブルシューティング

- .env が自動で読み込まれない場合
  - プロジェクトルートが .git または pyproject.toml を含む階層でないと自動検出されません。手動で環境変数を設定するか `KABUSYS_DISABLE_AUTO_ENV_LOAD` を利用してください。
- J-Quants API で 401 が発生する場合
  - jquants_client は自動でトークンリフレッシュを試みますが、refresh token が無効な場合は設定を確認してください。
- DuckDB の接続・ファイル権限エラー
  - DUCKDB_PATH の親ディレクトリが存在するか、プロセスに書き込み権限があるか確認してください。init_schema は親ディレクトリを自動作成しますが、権限が不足していると失敗します。

---

必要であれば、README にサンプルの .env.example、CI 実行例、デプロイ手順、ユニットテストの実行方法（pytest 等）を追加できます。どの情報がさらに必要か教えてください。