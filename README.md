# KabuSys

KabuSys は日本株向けの自動売買プラットフォーム用ライブラリ群です。データ収集（J-Quants）、ETL、特徴量作成、シグナル生成、ニュース収集、監査・スキーマ管理などを含むモジュール化された実装を提供します。

- パッケージ名: `kabusys`
- バージョン: 0.1.0（src/kabusys/__init__.py）

---

## プロジェクト概要

KabuSys は主に以下の責務を持ちます：

- J-Quants API からの市場データ（株価、財務、マーケットカレンダー）の取得と DuckDB への保存（冪等）
- ETL パイプライン（差分取得・バックフィル・品質チェック）
- 研究用ファクター計算（モメンタム・ボラティリティ・バリュー等）
- 特徴量（features）作成・正規化
- シグナル（BUY/SELL）生成ロジック（ファクター＋AIスコア統合、ベア判定、エグジット判定）
- RSS ベースのニュース収集・前処理・記事→銘柄紐付け
- DuckDB スキーマ定義と初期化、監査ログスキーマ
- 環境変数ベースの設定管理（.env 自動読み込みをサポート）

設計上の要点：
- ルックアヘッドバイアスを防ぐため、target_date 時点で利用可能なデータのみを使用
- DuckDB を中心としたオンディスク DB（または :memory:）
- 冪等性を重視（ON CONFLICT、トランザクション処理）
- テスト容易性を考慮した ID トークン注入など

---

## 主な機能一覧

- data/
  - jquants_client: J-Quants API クライアント（レートリミット、リトライ、トークンリフレッシュ、ページネーション対応）
  - pipeline: 日次差分 ETL（prices / financials / calendar）
  - schema: DuckDB スキーマ定義と初期化（Raw / Processed / Feature / Execution 層）
  - news_collector: RSS 収集・正規化・DB 保存（SSRF 対策・サイズ制限・トラッキングパラメータ除去）
  - stats: 汎用統計ユーティリティ（z-score 正規化）
  - calendar_management: 営業日判定・カレンダー更新ジョブ
  - audit: 監査ログ（signal / order_request / execution 等）
- research/
  - factor_research: Momentum / Volatility / Value 等のファクター計算
  - feature_exploration: 将来リターン計算・IC（Spearman）・統計サマリー
- strategy/
  - feature_engineering: raw ファクターを正規化・合成して features テーブルへ保存
  - signal_generator: features + ai_scores を統合し BUY/SELL シグナルを生成
- config: 環境変数管理（.env 自動ロード、必須 env の検証）

---

## 必要条件

- Python 3.10 以上（ソース内での型ヒントに `|` を使用）
- 必要となる主要ライブラリ（例）:
  - duckdb
  - defusedxml
- ネットワークアクセス（J-Quants API、RSS フィード）

（実際の依存はプロジェクトの packaging/requirements ファイルに従ってください。ここではコードから推測した最低限の依存を記載しています。）

---

## セットアップ手順

1. リポジトリをクローンし、仮想環境を作成・有効化します。

   ```bash
   git clone <repo-url>
   cd <repo>
   python -m venv .venv
   source .venv/bin/activate   # macOS/Linux
   .venv\Scripts\activate      # Windows (PowerShell)
   ```

2. 必要なパッケージをインストールします（例: duckdb, defusedxml）。パッケージ管理方法に合わせて調整してください。

   ```bash
   pip install -U pip
   pip install duckdb defusedxml
   # 開発時: pip install -e .
   ```

3. 環境変数を設定します。プロジェクトルートの `.env` / `.env.local` を使えます。以下の環境変数が利用されます（必須は明示）:

   必須:
   - JQUANTS_REFRESH_TOKEN   : J-Quants の refresh token（get_id_token に使用）
   - KABU_API_PASSWORD       : kabuステーション等の API パスワード
   - SLACK_BOT_TOKEN         : Slack 通知用 Bot トークン
   - SLACK_CHANNEL_ID        : Slack 通知先チャネル ID

   オプション:
   - KABUSYS_ENV             : 実行環境 ("development" / "paper_trading" / "live") — デフォルト "development"
   - LOG_LEVEL               : ログレベル ("DEBUG","INFO",...)
   - DUCKDB_PATH             : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH             : 監視用 SQLite（デフォルト: data/monitoring.db）
   - KABUSYS_DISABLE_AUTO_ENV_LOAD : "1" にすると自動 .env ロードを抑止

   例 (.env):
   ```
   JQUANTS_REFRESH_TOKEN=your_refresh_token_here
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   ```

   注意: src/kabusys/config.py は起動時にプロジェクトルート（.git または pyproject.toml）を探し、`.env` / `.env.local` を自動読み込みします。自動読み込みを無効化したいテスト時などは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

4. DuckDB スキーマを初期化します（サンプル）:

   ```python
   >>> from kabusys.data.schema import init_schema
   >>> conn = init_schema("data/kabusys.duckdb")
   ```

---

## 使い方（主要なユースケース）

以下はライブラリの主要関数の使い方例です。実運用ではジョブスクリプトや Airflow / cron に組み込みます。

1. スキーマ初期化

   ```python
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")
   ```

2. 日次 ETL を実行（J-Quants から差分取得して保存）

   ```python
   from kabusys.data.pipeline import run_daily_etl
   result = run_daily_etl(conn)  # target_date を省略すると今日
   print(result.to_dict())
   ```

3. 特徴量（features）を構築

   - 研究モジュールで計算した raw factors（calc_momentum 等）を正規化して `features` に保存します。

   ```python
   from kabusys.strategy import build_features
   from datetime import date
   count = build_features(conn, date(2025, 3, 20))
   print(f"upserted {count} features")
   ```

4. シグナル生成

   ```python
   from kabusys.strategy import generate_signals
   from datetime import date
   total = generate_signals(conn, date(2025, 3, 20), threshold=0.6)
   print(f"generated {total} signals")
   ```

   - `weights` を与えてファクター重みを指定可能（不正なキーや負値は無視され、合計は自動正規化されます）。

5. ニュース収集ジョブ

   ```python
   from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
   results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes={"7203","6758"})
   print(results)
   ```

6. J-Quants からのデータ取得（下位 API）

   ```python
   from kabusys.data.jquants_client import fetch_daily_quotes, fetch_financial_statements
   rows = fetch_daily_quotes(date_from=date(2025,1,1), date_to=date(2025,3,20))
   ```

---

## 環境設定と挙動に関する注意

- 設定値は `kabusys.config.settings` 経由で参照できます。必須環境変数が足りないと `ValueError` が発生します。
- 自動 .env 読み込みの挙動:
  - 読み込み順: OS 環境 > .env.local（上書き）> .env（既存値は上書きしない）
  - 自動読み込みを無効にする: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`
- `KABUSYS_ENV` は "development", "paper_trading", "live" のいずれかでなければ例外になります。
- J-Quants API リクエストではレートリミット（120 req/min）を守るため内部でスロットリングを実装しています。
- DuckDB の初期化は `init_schema(db_path)` を使って実行してください。既存テーブルがあればスキップされ、冪等に作成されます。

---

## ディレクトリ構成

以下は主要ファイル（src 配下）を抜粋した構成です（簡易ツリー）:

- src/
  - kabusys/
    - __init__.py
    - config.py
    - data/
      - __init__.py
      - jquants_client.py
      - news_collector.py
      - schema.py
      - stats.py
      - pipeline.py
      - features.py
      - calendar_management.py
      - audit.py
      - ...（execution, その他モジュール）
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
    - monitoring/  (モニタリング関連の実装予定/別モジュール)
  - pyproject.toml / setup.cfg / その他パッケージ管理ファイル（プロジェクトルート）

（実際のリポジトリには README を補完する形でドキュメントや examples フォルダを追加すると良いです）

---

## よくあるトラブルと対処

- ValueError: 環境変数が設定されていません
  - 必須 env（JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, KABU_API_PASSWORD）を `.env` または OS 環境に設定してください。

- DuckDB への接続/ファイル作成エラー
  - `init_schema` は親ディレクトリを自動作成しますが、パスの権限を確認してください。
  - `:memory:` を使えばインメモリ DB で動作確認できます。

- J-Quants API で 401 が返る
  - `JQUANTS_REFRESH_TOKEN` の値が正しいか確認してください。クライアントは 401 を受けると自動でトークンをリフレッシュして 1 回だけ再試行します。

- RSS フィード取得で SSRF/ホスト拒否される
  - RSS URL のスキームは http/https のみ許可されます。内部プライベート IP へのアクセスは保護されています。

---

## 今後の拡張案 / 注意事項

- execution 層（発注実行ロジック）や broker adapter の実装（kabuステーションや他ブローカーとの接続）
- モニタリング / アラート用の UI または監視エンドポイント
- CI/CD 用のテスト、ユニットテスト、統合テストの追加
- ドキュメント（StrategyModel.md, DataPlatform.md 等）の同梱

---

もし README に含めたい具体的なセットアップ例（Docker, systemd, CI）や、使い方の完全なジョブスクリプト例が必要であれば、目的（ETL バッチ / リアルタイム実行 / バックテスト 等）を教えてください。そこに合わせたサンプルを追加します。