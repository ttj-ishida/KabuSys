# KabuSys

KabuSys は日本株向けの自動売買プラットフォームのコアライブラリです。  
データ収集（J-Quants）、ETL、ファクター計算、特徴量エンジニアリング、シグナル生成、ニュース収集、監査ログ/スキーマ管理 などの一連処理をモジュール化して提供します。

主な設計方針：
- ルックアヘッドバイアスを避けるため「対象日（target_date）時点の情報のみ」を用いる
- DuckDB をデータストアとして利用し、冪等性（ON CONFLICT / トランザクション）を重視
- 外部API呼び出しは最小限・堅牢なリトライ／レート制御を実装
- 研究（research）／本番（execution）を分離できる構成

---

## 機能一覧

- 環境変数・設定管理
  - 自動でプロジェクトルートの `.env` / `.env.local` をロード（無効化可能）
  - 必須設定の取得・バリデーション（J-Quants、kabuAPI、Slack 等）

- データ取り込み／保存（J-Quants API クライアント）
  - 株価日足（OHLCV）取得（ページネーション対応、レートリミット制御）
  - 財務データ取得（四半期データ）
  - JPX マーケットカレンダー取得
  - DuckDB への冪等保存（raw テーブル群）

- ETL パイプライン
  - 日次差分更新（prices / financials / calendar）
  - backfill による修正吸収（最終取得日の数日前から再取得）
  - 品質チェック（quality モジュールとの連携）

- データスキーマ（DuckDB）
  - Raw / Processed / Feature / Execution 層を想定したテーブル群の初期化
  - インデックス定義、外部キー考慮の作成順序

- ファクター計算（research/factor_research）
  - Momentum / Volatility / Value / Liquidity などを DuckDB 上で計算

- 特徴量エンジニアリング（strategy/feature_engineering）
  - 生ファクターを正規化（Z スコア）・クリップ・ユニバースフィルタを適用して `features` テーブルに保存

- シグナル生成（strategy/signal_generator）
  - features と ai_scores を統合して final_score を計算
  - Bear レジーム検知、BUY/SELL の閾値判定、保有ポジションのエグジット判定
  - `signals` テーブルへの冪等書き込み

- ニュース収集（data/news_collector）
  - RSS 取得、テキスト前処理、記事ID の冪等生成（URL 正規化 + SHA-256）
  - SSRF 対策、受信サイズ制限、defusedxml による XML 攻撃対策
  - raw_news / news_symbols への保存

- 監査・トレーサビリティ（data/audit）
  - signal → order_request → execution の追跡用テーブル群（監査ログ）

---

## セットアップ手順

前提
- Python 3.10 以上（型注釈で Python 3.10 の構文（|）を使用）
- DuckDB を利用するためネイティブライブラリを利用可能な環境

1. リポジトリをクローンし、開発仮想環境を作成
   ```bash
   git clone <repo-url>
   cd <repo>
   python -m venv .venv
   source .venv/bin/activate
   pip install --upgrade pip
   ```

2. 必要なパッケージをインストール
   - 最低限の外部依存：
     - duckdb
     - defusedxml
   ```bash
   pip install duckdb defusedxml
   ```
   （プロジェクトで他のパッケージを使う場合は requirements.txt / pyproject.toml を参照してください）

3. 環境変数（.env）を用意
   - プロジェクトルートに `.env` または `.env.local` を作成すると自動で読み込まれます（自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1）。
   - 最低限必要な環境変数（例）:
     ```
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     KABU_API_PASSWORD=your_kabu_api_password
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C...
     # 任意
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db
     KABUSYS_ENV=development  # development | paper_trading | live
     LOG_LEVEL=INFO
     ```
   - `.env.example` を参考に作成してください（ソース内に参照コメントあり）。

4. データベース初期化（DuckDB）
   - Python REPL またはスクリプトでスキーマを作成します。
   ```python
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")  # :memory: も可
   ```

---

## 使い方（主要ユースケース）

以下は代表的な処理の呼び出し例です。詳細は各モジュールの docstring を参照してください。

1. DuckDB スキーマの初期化
   ```python
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")
   ```

2. 日次 ETL（株価 / 財務 / カレンダー の差分取得と保存）
   ```python
   from datetime import date
   from kabusys.data.pipeline import run_daily_etl
   # conn は init_schema で作成した接続
   result = run_daily_etl(conn, target_date=date.today())
   print(result.to_dict())
   ```

3. 特徴量生成（features テーブルへ書き込み）
   ```python
   from datetime import date
   from kabusys.strategy import build_features
   count = build_features(conn, target_date=date(2026, 1, 31))
   print(f"features written: {count}")
   ```

4. シグナル生成（signals テーブルへ書き込み）
   ```python
   from datetime import date
   from kabusys.strategy import generate_signals
   total = generate_signals(conn, target_date=date(2026, 1, 31))
   print(f"signals written: {total}")
   ```

5. ニュース収集ジョブ
   ```python
   from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
   # known_codes は extract_stock_codes に使う有効コード集合（例: 上場銘柄リスト）
   results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=set(["7203","6758"]))
   print(results)
   ```

6. J-Quants API を直接利用してデータ取得・保存
   ```python
   from kabusys.data import jquants_client as jq
   records = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
   saved = jq.save_daily_quotes(conn, records)
   ```

注意点：
- 各処理は冪等に設計されています（対象日分を削除して再挿入等）。
- ETL の HTTP 呼び出しは内部でレート制御・リトライを行います。
- 一部モジュールは research（分析）用途向けで、本番の execution 層（kabu API へ発注）には依存しない設計です。

---

## 環境変数／設定一覧（主なもの）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (任意、デフォルト: http://localhost:18080/kabusapi)
- SLACK_BOT_TOKEN (必須)
- SLACK_CHANNEL_ID (必須)
- DUCKDB_PATH (任意、デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (任意、デフォルト: data/monitoring.db)
- KABUSYS_ENV (development | paper_trading | live)（任意、デフォルト: development）
- LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL)（任意、デフォルト: INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセットすると自動 .env ロードを無効化できます（テスト用）。

設定は kabusys.config.settings からアクセスできます:
```python
from kabusys.config import settings
print(settings.jquants_refresh_token)
```

---

## ディレクトリ構成（概略）

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数読み込みと Settings クラス
  - data/
    - __init__.py
    - jquants_client.py
      - J-Quants API クライアント（取得 / 保存 / レート制御 / リトライ）
    - news_collector.py
      - RSS 収集・記事正規化・保存・銘柄紐付け
    - schema.py
      - DuckDB の DDL 定義と init_schema(), get_connection()
    - stats.py
      - 汎用統計ユーティリティ（zscore_normalize）
    - pipeline.py
      - ETL パイプライン（run_daily_etl 等）
    - features.py
      - data.stats の再エクスポート
    - calendar_management.py
      - market_calendar の管理・営業日判定・更新ジョブ
    - audit.py
      - 発注／約定の監査ログ用 DDL
  - research/
    - __init__.py
    - factor_research.py
      - Momentum/Value/Volatility 等のファクター計算
    - feature_exploration.py
      - IC 計算、将来リターン計算、ファクター統計
  - strategy/
    - __init__.py
    - feature_engineering.py
      - features テーブル作成ロジック（正規化・フィルタ）
    - signal_generator.py
      - final_score 計算、BUY/SELL 生成、signals 保存
  - execution/
    - __init__.py
      - （発注レイヤー用の拡張ポイント）
  - monitoring/
    - （監視・メトリクス関連のモジュールを想定）

---

## 開発・拡張のヒント

- テスト／CI：
  - 環境変数自動ロードが邪魔な場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して無効化できます。
  - DuckDB の `:memory:` を使えばテスト用にインメモリ DB を作成できます。

- ログレベル：
  - LOG_LEVEL 環境変数で調整（DEBUG にすると内部の SQL 試行や警告が詳細に出力されます）。

- 安全性：
  - news_collector は SSRF / XML 攻撃 / 大容量レスポンスに対する対策を実装していますが、外部フィードを追加する際は信頼性の確認を推奨します。

---

## 参考・ドキュメント参照先（ソース内）
各モジュールに詳しい docstring が記載されています。実装仕様（StrategyModel.md、DataPlatform.md、DataSchema.md）に依存する説明もありますので、プロジェクト内のドキュメント（該当ファイルが存在する場合）を合わせて参照してください。

---

問題や使い方の詳細が必要であれば、どのワークフロー（ETL / feature build / signal generation / news collection など）について知りたいか教えてください。具体的なコード例やトラブルシュートも提供します。