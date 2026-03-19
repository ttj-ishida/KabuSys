# KabuSys

日本株向けの自動売買システム用ライブラリ（Research / Data / Strategy / Execution レイヤーを含む）

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株のデータ収集（J-Quants 経由）、データ品質チェック、特徴量計算、シグナル生成、発注・監査のための基盤ライブラリです。  
モジュールは大きく以下のレイヤーに分かれており、研究環境（research）と本番実行（execution）を分離した設計になっています。

- Data Layer: J-Quants API クライアント、ETL パイプライン、ニュース収集、DuckDB スキーマ定義
- Research Layer: ファクター計算・特徴量探索ユーティリティ
- Strategy Layer: 特徴量を合成してシグナルを生成するロジック
- Execution / Monitoring Layer: 発注・監視用のインターフェース（execution モジュールは拡張を想定）

設計上の主なポリシー:
- ルックアヘッドバイアス回避（target_date 時点のデータのみを使用）
- 冪等性（DBへの保存は ON CONFLICT / トランザクションで保証）
- ネットワーク堅牢性（レートリミット・リトライ・トークンリフレッシュ等）
- 外部依存を最小化（可能な限り標準ライブラリ + duckdb）

---

## 主な機能一覧

- J-Quants API クライアント
  - 日足（OHLCV）取得、財務諸表、JPX カレンダー取得
  - レートリミット管理、リトライ、トークン自動リフレッシュ
- DuckDB スキーマ定義と初期化（init_schema）
  - Raw / Processed / Feature / Execution 層のテーブル設計
- ETL パイプライン
  - 差分取得（backfill を含む）、保存、品質チェック呼び出し、日次実行用エントリ（run_daily_etl）
- ニュース収集
  - RSS フィード取得、前処理、記事保存、銘柄抽出と紐付け
  - SSRF 対策、XML 安全処理、受信サイズ制限
- ファクター計算（research）
  - Momentum / Volatility / Value 等のファクター算出
  - 将来リターン計算、IC（Spearman ρ）、ファクター統計要約
- 特徴量エンジニアリング（strategy）
  - 生ファクターの正規化（Zスコア）、ユニバースフィルタ、features テーブルへの UPSERT（build_features）
- シグナル生成（strategy）
  - 正規化済み特徴量 + AI スコアを統合して final_score を算出し、BUY / SELL シグナルを生成・保存（generate_signals）
- 監査・トレーサビリティ設計（audit モジュール）
  - signal_events / order_requests / executions 等の監査ログ用テーブル定義

---

## 必要な環境変数

自動で .env/.env.local をロードします（プロジェクトルートに .git または pyproject.toml があることを前提）。  
テストや特殊用途では環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化できます。

必須:
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（jquants_client で使用）
- KABU_API_PASSWORD: kabuステーション API のパスワード（execution 層で使用）
- SLACK_BOT_TOKEN: Slack 通知用ボットトークン
- SLACK_CHANNEL_ID: Slack チャネル ID

任意（デフォルトあり）:
- KABUSYS_ENV: 実行環境 (development | paper_trading | live)（デフォルト: development）
- LOG_LEVEL: ログレベル (DEBUG | INFO | WARNING | ERROR | CRITICAL)（デフォルト: INFO）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: モニタリング DB パス（デフォルト: data/monitoring.db）

設定参照例（Python）:
```python
from kabusys.config import settings
token = settings.jquants_refresh_token
```

---

## セットアップ手順

前提: Python 3.9+（typing の記法や型ヒントを使用）、duckdb が必要です。

1. リポジトリをクローン
   ```bash
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境の作成（推奨）
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

3. 依存パッケージをインストール（例: duckdb）
   - 必要に応じて requirements.txt を用意してください。最小例:
     ```bash
     pip install duckdb defusedxml
     ```
   - 開発用にローカルパッケージとしてインストールする場合:
     ```bash
     pip install -e .
     ```

4. 環境変数設定
   - プロジェクトルートに `.env` を作成して必要な値を設定します（.env.example を参照）。
   - 例:
     ```
     JQUANTS_REFRESH_TOKEN=your_refresh_token
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C0123456789
     KABU_API_PASSWORD=secret
     KABUSYS_ENV=development
     DUCKDB_PATH=data/kabusys.duckdb
     ```

5. DuckDB スキーマ初期化
   ```python
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")
   ```

---

## 使い方（主要ワークフロー例）

以下は代表的な操作フローの例です。実運用ではエラーハンドリング・ロギング・認証トークン管理等を追加してください。

1. DuckDB スキーマの初期化（1回だけ）
   ```python
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")
   ```

2. 日次 ETL を実行（J-Quants から取得して保存 → 品質チェック）
   ```python
   from kabusys.data.pipeline import run_daily_etl
   from kabusys.data.schema import init_schema
   from datetime import date

   conn = init_schema("data/kabusys.duckdb")
   result = run_daily_etl(conn, target_date=date.today())
   print(result.to_dict())
   ```

3. 特徴量（features）の構築
   ```python
   from kabusys.strategy import build_features
   from kabusys.data.schema import get_connection
   from datetime import date

   conn = get_connection("data/kabusys.duckdb")
   n = build_features(conn, target_date=date.today())
   print(f"features upserted: {n}")
   ```

4. シグナル生成（BUY / SELL を signals テーブルへ保存）
   ```python
   from kabusys.strategy import generate_signals
   from kabusys.data.schema import get_connection
   from datetime import date

   conn = get_connection("data/kabusys.duckdb")
   total = generate_signals(conn, target_date=date.today(), threshold=0.6)
   print(f"signals generated: {total}")
   ```

5. ニュース収集ジョブ実行例
   ```python
   from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
   from kabusys.data.schema import get_connection

   conn = get_connection("data/kabusys.duckdb")
   known_codes = {"7203", "6758", "9984"}  # 有効銘柄コードのセット
   results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
   print(results)
   ```

---

## 主要モジュール説明（簡易）

- kabusys.config
  - 環境変数ロード・管理（.env 自動読み込み、必須チェック、環境名/ログレベル検証）

- kabusys.data
  - jquants_client.py: J-Quants API クライアント（fetch/save 関数）
  - schema.py: DuckDB スキーマ定義 / init_schema / get_connection
  - pipeline.py: ETL パイプライン（run_daily_etl 等）
  - news_collector.py: RSS 収集・保存・銘柄抽出
  - calendar_management.py: 市場カレンダーの判定・更新ユーティリティ
  - audit.py: 監査テーブルの DDL（signal_events / order_requests / executions）
  - stats.py: zscore_normalize 等の統計ユーティリティ
  - features.py: zscore_normalize の再エクスポート

- kabusys.research
  - factor_research.py: momentum / volatility / value 等のファクター計算
  - feature_exploration.py: 将来リターン計算、IC、factor_summary、rank

- kabusys.strategy
  - feature_engineering.py: 生ファクターを正規化して features テーブルに保存（build_features）
  - signal_generator.py: final_score 計算、BUY/SELL シグナル生成（generate_signals）

- kabusys.execution
  - 発注・ブローカー連携用の土台（空の __init__.py、実装は拡張想定）

---

## ディレクトリ構成

（主要ファイルのみ抜粋）

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
      - calendar_management.py
      - audit.py
      - stats.py
      - features.py
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
    - monitoring/  (エクスポート対象だが実装ファイルはここに配置)
- pyproject.toml / setup.cfg / README.md / .env.example など（プロジェクトルート）

---

## 運用上の注意 / 補足

- データ品質
  - ETL の最後に品質チェックを必ず実行することを推奨します（pipeline.run_daily_etl の run_quality_checks オプション）。
- 冪等性
  - jquants_client の save_* 系関数、news_collector の保存処理は ON CONFLICT を用いて冪等を確保しています。
- セキュリティ
  - RSS の取得では SSRF 対策、XML の安全パーサ（defusedxml）を使用しています。
  - API トークン等は必ず安全に管理してください（.env をリポジトリに含めない）。
- 本番切替
  - KABUSYS_ENV を `paper_trading` / `live` に切り替え、発注・監視のポリシーを分離してください。

---

## 貢献 / ライセンス

この README はソースコードからの概要説明を目的としており、実装や運用に合わせて追記・修正してください。  
（ライセンス情報や貢献ガイドラインはプロジェクトルートの該当ファイルを参照してください。）

---

必要であれば、README に含めるサンプル .env.example、CI 用の実行例、あるいはより詳しい API リファレンスを追記します。どの情報を追加しますか？