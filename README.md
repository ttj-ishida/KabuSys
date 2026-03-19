# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリです。  
市場データ取得（J‑Quants） → DuckDB への永続化 → 特徴量生成 → シグナル生成 → 発注・監査までの主要な層を揃えたモジュール群を提供します。

主な設計方針
- ルックアヘッドバイアス防止（各処理は target_date 時点のデータのみを参照）
- DuckDB を中心としたローカルデータ管理（冪等保存、トランザクション）
- 外部 API 呼び出しはクライアント層に集約（リトライ・レートリミット・トークン更新対応）
- Research / Production の両環境を意識した分離（研究用の factor 計算／探索機能を提供）

バージョン: 0.1.0

---

## 機能一覧

- 環境変数管理
  - プロジェクトルートの `.env` / `.env.local` を自動読み込み（必要に応じて無効化可能）
  - 必須項目は Settings 経由で取得し未設定時はエラーを出す

- データ取得・保存（J‑Quants）
  - 日次株価（OHLCV）、四半期財務、JPX カレンダーの取得・保存
  - レート制限・リトライ・トークン自動リフレッシュ対応
  - DuckDB へ冪等保存（ON CONFLICT / トランザクション）

- ETL パイプライン
  - 差分取得（最終取得日からの差分）とバックフィル対応
  - quality モジュールと連携する品質チェック（欠損・スパイク等の検出）

- カレンダー管理
  - market_calendar を使った営業日判定、前後営業日探索、期間内営業日取得
  - カレンダーの差分更新ジョブ

- ニュース収集
  - RSS フィード収集、URL 正規化、記事ID（SHA-256 先頭 32 文字）で冪等保存
  - SSRF 対策、受信サイズ上限、XML パースの保護（defusedxml）

- 研究用 / 戦略用
  - ファクター計算（momentum / volatility / value 等）
  - Zスコア正規化ユーティリティ
  - 特徴量生成（features テーブルへの UPSERT）
  - シグナル生成（final_score 計算、BUY / SELL 判定、signals テーブル保存）

- DuckDB スキーマ管理
  - Raw / Processed / Feature / Execution 層のテーブル定義と初期化
  - インデックス定義、トランザクションを使った安全な初期化

---

## 必要条件

- Python 3.10 以上（PEP 604 の `X | Y` 型表記を使用）
- 必要な Python パッケージ（最低限）
  - duckdb
  - defusedxml

（上記に加えて本番や運用用には適宜ログ周り、Slack 通知、kabu API クライアントなどの依存が追加される可能性があります）

---

## セットアップ手順

1. リポジトリをクローン
   ```
   git clone <repository-url>
   cd <repository>
   ```

2. 仮想環境を作成して有効化（任意）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .\.venv\Scripts\activate    # Windows (Powershell/コマンドプロンプト)
   ```

3. 必要パッケージをインストール
   ```
   pip install "duckdb>=1.0" defusedxml
   # 開発用にパッケージを editable インストールする場合:
   pip install -e .
   ```

4. 環境変数の準備
   - プロジェクトルートに `.env`（または `.env.local`）を作成してください。
   - 主に必要となる環境変数例:
     - JQUANTS_REFRESH_TOKEN=...
     - KABU_API_PASSWORD=...
     - KABU_API_BASE_URL (任意; デフォルト: http://localhost:18080/kabusapi)
     - SLACK_BOT_TOKEN=...
     - SLACK_CHANNEL_ID=...
     - DUCKDB_PATH (任意; デフォルト: data/kabusys.duckdb)
     - SQLITE_PATH (任意; デフォルト: data/monitoring.db)
     - KABUSYS_ENV = development | paper_trading | live
     - LOG_LEVEL = DEBUG | INFO | WARNING | ERROR | CRITICAL

   自動で `.env` を読み込みたくない場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## 使い方（基本例）

下記はライブラリを利用する際の代表的なワークフロー例です。

- DuckDB スキーマ初期化
  ```python
  from kabusys.data.schema import init_schema

  conn = init_schema("data/kabusys.duckdb")  # ":memory:" も可
  ```

- 日次 ETL 実行（J‑Quants からの差分取得 → 保存 → 品質チェック）
  ```python
  from kabusys.data.pipeline import run_daily_etl
  from kabusys.data.schema import init_schema
  from datetime import date

  conn = init_schema("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

- 特徴量を生成して features テーブルへ保存
  ```python
  from kabusys.strategy import build_features
  from kabusys.data.schema import get_connection
  from datetime import date

  conn = get_connection("data/kabusys.duckdb")
  n = build_features(conn, target_date=date(2025, 3, 1))
  print(f"features upserted: {n}")
  ```

- シグナル生成
  ```python
  from kabusys.strategy import generate_signals
  from kabusys.data.schema import get_connection
  from datetime import date

  conn = get_connection("data/kabusys.duckdb")
  total = generate_signals(conn, target_date=date(2025, 3, 1), threshold=0.6)
  print(f"signals generated: {total}")
  ```

- ニュース収集（RSS）ジョブ
  ```python
  from kabusys.data.news_collector import run_news_collection
  from kabusys.data.schema import get_connection

  conn = get_connection("data/kabusys.duckdb")
  results = run_news_collection(conn, sources=None, known_codes={"7203","6758"})
  print(results)
  ```

- カレンダー更新ジョブ
  ```python
  from kabusys.data.calendar_management import calendar_update_job
  from kabusys.data.schema import get_connection

  conn = get_connection("data/kabusys.duckdb")
  saved = calendar_update_job(conn, lookahead_days=90)
  print(f"calendar saved: {saved}")
  ```

注意点
- ETL やシグナル生成は DuckDB のテーブル（raw_prices, raw_financials, prices_daily, features, ai_scores, positions 等）を参照します。初回はデータ投入（ETL）を行ってください。
- run_daily_etl は複数ステップを独立に実行し、各ステップで発生したエラーを集約して結果オブジェクトに格納します。

---

## 主要モジュールと簡単な説明

- kabusys.config
  - Settings: 環境変数から設定を取得。自動 `.env` ロード機能あり。

- kabusys.data
  - jquants_client: J‑Quants API クライアント（レートリミット・リトライ・ページング・保存関数）
  - schema: DuckDB のスキーマ定義と初期化（init_schema / get_connection）
  - pipeline: ETL パイプライン（run_prices_etl / run_financials_etl / run_calendar_etl / run_daily_etl）
  - news_collector: RSS 取得・前処理・保存（SSRF 対策、gzip 対応）
  - calendar_management: 営業日判定 / 更新ジョブ
  - stats: zscore_normalize 等の統計ユーティリティ

- kabusys.research
  - factor_research: momentum / volatility / value の計算（prices_daily, raw_financials を参照）
  - feature_exploration: 将来リターン計算、IC（Spearman）計算、統計サマリ

- kabusys.strategy
  - feature_engineering.build_features: 生ファクターの正規化・フィルタ・features への UPSERT
  - signal_generator.generate_signals: features と ai_scores を統合して BUY/SELL シグナル生成

- kabusys.execution
  - 発注・ブローカー連携周りの実装領域（パッケージは存在するが詳細実装は個別に追加）

---

## ディレクトリ構成

（プロジェクト内の `src/kabusys/` に相当するツリーの抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py
    - data/
      - __init__.py
      - jquants_client.py
      - news_collector.py
      - schema.py
      - pipeline.py
      - stats.py
      - calendar_management.py
      - audit.py
      - features.py
      - audit.py
      - ...（その他 data 関連モジュール）
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
    - strategy/
      - __init__.py
      - feature_engineering.py
      - signal_generator.py
    - execution/
      - __init__.py
      - ...（発注ロジック等を配置）
    - monitoring/  (パッケージ参照のみ: README にあるがコードベースに応じて追加)
    - ...

---

## 環境変数（主なもの）

- JQUANTS_REFRESH_TOKEN: J‑Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabu ステーション API パスワード（必須: 発注周りを使う場合）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN / SLACK_CHANNEL_ID: Slack 通知用（必須: Slack 通知機能を使う場合）
- DUCKDB_PATH / SQLITE_PATH: データベースファイルパス（任意）
- KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL: ログレベル（デフォルト: INFO）

.env.example をプロジェクトルートに置いておくと初期セットアップが楽です。

---

## 開発・テスト

- 自動ロードされる環境変数の挙動をテストで無効化する場合:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してからテスト実行

- 単体テストや CI を整備する場合は DuckDB の in-memory データベース（":memory:"）を使うと速く安全に実行できます。

---

## 最後に / 貢献

本 README はコードベースの主要機能と使い方の入門を目的としています。  
バグ報告・機能追加・ドキュメント改善のプルリクエスト歓迎します。運用に関する注意（実際の発注を行う場合のリスク、資金管理、レイテンシー・ネットワーク障害対策など）は別途運用ガイドを用意してください。

--- 

必要であれば、README にサンプル .env.example、より詳しい API 使用例（J‑Quants の id_token 管理や kabu API の発注フロー）、監査テーブルの利用方法などを追記します。どの部分を詳細化したいか教えてください。