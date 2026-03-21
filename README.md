# KabuSys

日本株向けの自動売買フレームワーク（KabuSys）。  
データ取得（J-Quants）、ETL、データスキーマ（DuckDB）、特徴量生成、戦略シグナル生成、ニュース収集、マーケットカレンダー管理、発注/監査ログ設計を含むモジュール群を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は、日本株のアルゴリズム取引プラットフォーム構築を支援するライブラリ群です。  
主要な役割は以下の通りです。

- J-Quants API から市場データ・財務データ・カレンダーを取得して DuckDB に保存（差分取得・冪等保存）
- データ品質チェック、ETL パイプラインの実行
- リサーチ向けファクター計算（モメンタム、ボラティリティ、バリュー等）
- ファクターの正規化・合成 → features テーブルへの保存（戦略用特徴量）
- features と AIスコアを統合したシグナル生成（BUY / SELL）の作成と signals テーブルへの保存
- RSS によるニュース収集と銘柄紐付け
- マーケットカレンダー管理（営業日判定・次営業日/前営業日の取得）
- DuckDB スキーマ定義および監査ログ設計

設計上、戦略・研究モジュールはルックアヘッドバイアスを防ぐため「target_date 時点のデータのみ」を参照するようになっています。また DB への保存は冪等（ON CONFLICT / DO UPDATE 等）を重視しています。

---

## 主な機能一覧

- data/
  - jquants_client: J-Quants API クライアント（レート制限・再試行・トークン自動リフレッシュ）
  - schema: DuckDB スキーマ定義・初期化関数（init_schema）
  - pipeline: 日次 ETL（run_daily_etl）・個別 ETL（prices/financials/calendar）
  - news_collector: RSS 取得、前処理、raw_news 保存、銘柄抽出・紐付け
  - calendar_management: 営業日判定、next/prev_trading_day、calendar_update_job
  - stats: zscore_normalize などの統計ユーティリティ
- research/
  - factor_research: mom/volatility/value 等のファクター計算（prices_daily / raw_financials を参照）
  - feature_exploration: 将来リターン計算、IC（Spearman ランク相関）計算、要約統計
- strategy/
  - feature_engineering.build_features: research の生ファクターを正規化・合成して features テーブルへ保存
  - signal_generator.generate_signals: features / ai_scores / positions 等を参照して BUY/SELL シグナルを生成し signals テーブルへ保存
- config:
  - Settings クラスによる環境変数管理（.env の自動ロード、必須設定チェック）
- execution/ （発注層の拡張ポイント。パッケージは存在）

その他、監査（audit）や実行レイヤー用のスキーマ・テーブル定義も含まれます。

---

## 動作環境 / 依存

- Python >= 3.10（ソースに Python の union 型（A | B）注釈を使用しているため）
- 必要パッケージ（最低限）:
  - duckdb
  - defusedxml
- 標準ライブラリで HTTP 処理等は実装されていますが、実行環境に合わせて追加のツール（例: テスト用モック、CI設定等）を導入してください。

インストール例（仮想環境推奨）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb defusedxml
# プロジェクトを editable install したい場合:
# pip install -e .
```

---

## 設定（環境変数）

自動でプロジェクトルートの `.env` / `.env.local` を読み込みます（環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。必要な主要環境変数:

- JQUANTS_REFRESH_TOKEN (必須) - J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) - kabuステーション等の API パスワード
- KABU_API_BASE_URL (任意) - デフォルト: http://localhost:18080/kabusapi
- SLACK_BOT_TOKEN (必須) - Slack 通知用 bot token
- SLACK_CHANNEL_ID (必須) - Slack 通知先チャンネル ID
- DUCKDB_PATH (任意) - DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH (任意) - 監視等で使う SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV (任意) - development / paper_trading / live（デフォルト: development）
- LOG_LEVEL (任意) - DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）

必須変数が不足していると Settings プロパティ呼び出しで ValueError が発生します。

---

## セットアップ手順

1. リポジトリをクローン
   ```bash
   git clone <repo-url>
   cd <repo>
   ```

2. Python 仮想環境を作成・有効化
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```

3. 依存パッケージをインストール
   ```bash
   pip install duckdb defusedxml
   # その他テスト/開発ツールがあれば追加
   ```

4. 環境変数を設定
   - プロジェクトルートに `.env`（および必要に応じ `.env.local`）を作成してください。
   - 例（.env.example を用意している想定）:
     ```
     JQUANTS_REFRESH_TOKEN=your_refresh_token
     KABU_API_PASSWORD=your_kabu_password
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C12345678
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     ```

5. DuckDB スキーマ初期化
   - Python から:
     ```python
     from kabusys.data import schema
     from kabusys.config import settings
     conn = schema.init_schema(settings.duckdb_path)
     ```
   - またはメモリ DB でテスト:
     ```python
     conn = schema.init_schema(":memory:")
     ```

---

## 基本的な使い方（例）

- 日次 ETL の実行:
  ```python
  from datetime import date
  import duckdb
  from kabusys.data import pipeline, schema
  from kabusys.config import settings

  conn = schema.init_schema(settings.duckdb_path)
  result = pipeline.run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

- 特徴量（features）を構築:
  ```python
  from datetime import date
  from kabusys.strategy import build_features
  from kabusys.data import schema
  from kabusys.config import settings

  conn = schema.get_connection(settings.duckdb_path)
  count = build_features(conn, target_date=date(2024, 1, 5))
  print(f"{count} 銘柄の features を保存しました")
  ```

- シグナル生成:
  ```python
  from datetime import date
  from kabusys.strategy import generate_signals
  from kabusys.data import schema
  from kabusys.config import settings

  conn = schema.get_connection(settings.duckdb_path)
  total = generate_signals(conn, target_date=date(2024, 1, 5))
  print(f"{total} 件のシグナルを書き込みました")
  ```

- ニュース収集ジョブ:
  ```python
  from kabusys.data.news_collector import run_news_collection
  from kabusys.data import schema
  from kabusys.config import settings

  conn = schema.get_connection(settings.duckdb_path)
  # known_codes は銘柄抽出に使う有効なコード集合（例: {"7203","6758",...}）
  res = run_news_collection(conn, known_codes={"7203","6758"})
  print(res)
  ```

- カレンダー更新ジョブ:
  ```python
  from kabusys.data.calendar_management import calendar_update_job
  from kabusys.data import schema
  from kabusys.config import settings

  conn = schema.get_connection(settings.duckdb_path)
  saved = calendar_update_job(conn)
  print(f"saved={saved}")
  ```

---

## 開発者向けメモ

- ルックアヘッドバイアス対策:
  - 戦略・研究モジュールは target_date 時点までのデータのみ参照する実装方針です。将来情報を参照しないよう注意してください。
- 冪等性:
  - DB 保存関数は基本的に ON CONFLICT DO UPDATE / DO NOTHING を用いた冪等設計です。bulk insert はトランザクションでまとめて行います。
- テスト:
  - pipeline 等は id_token を注入できるため、外部 API をモックして単体テストしやすい設計になっています。
- 環境変数自動ロード:
  - config._find_project_root() は .git または pyproject.toml を基準にプロジェクトルートを探索します。テスト時に自動ロードを止めたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## ディレクトリ構成

（主要ファイルのみ抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py
    - execution/
      - __init__.py
    - strategy/
      - __init__.py
      - feature_engineering.py
      - signal_generator.py
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
    - data/
      - __init__.py
      - jquants_client.py
      - pipeline.py
      - schema.py
      - stats.py
      - features.py
      - news_collector.py
      - calendar_management.py
      - audit.py
    - monitoring/  (モニタリング関連—ディレクトリは __all__ に含まれますが実装は別途)
    - ...（追加モジュール）

上記はコードベースに含まれる主なモジュールを示します。各モジュールはさらに細かな関数・ユーティリティを含みます。

---

## ライセンス / 責任

本リポジトリ内のコードは実運用に使用する前に十分なレビュー・テストを行ってください。特に発注・約定・資金管理に関わる実装は重大なリスクを伴います。J-Quants 等外部 API 利用にあたっては各サービスの利用規約を遵守してください。

---

必要であれば README に含めるコマンド例、.env.example、CI / テスト実行手順、または各モジュールの詳しい API 参照（関数引数・戻り値の詳細）を追加します。どの情報を優先して追加しましょうか？