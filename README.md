# KabuSys

バージョン: 0.1.0

KabuSys は日本株向けの自動売買およびデータプラットフォームのライブラリです。J-Quants API からマーケットデータ／財務データを取得して DuckDB に蓄積し、ファクター計算、特徴量生成、シグナル生成、ニュース収集、マーケットカレンダー管理などの機能を提供します。設計上、本番発注層（execution）とは分離しており、戦略ロジックや ETL を再現可能かつ冪等に実行できるように実装されています。

主な用途の想定例:
- 日次 ETL によるマーケットデータ取得・保存
- 研究（research）で計算したファクターの正規化・保存
- 戦略でのシグナル生成（BUY / SELL 判定）
- RSS ベースのニュース収集と銘柄紐付け
- JPX カレンダー管理（営業日判定 / 更新）

---

## 機能一覧

- データ取得 / ETL
  - J-Quants API クライアント（差分取得・ページネーション・リトライ・レート制御）
  - 日次 ETL パイプライン（株価・財務・市場カレンダー）
  - DuckDB への冪等保存（ON CONFLICT/UPSERT を利用）
- データスキーマ
  - Raw / Processed / Feature / Execution 層のテーブル定義と初期化（DuckDB）
- Research / Factor
  - Momentum / Volatility / Value 等のファクター計算
  - 将来リターン計算、IC（Spearman）やファクター統計量
  - Z スコア正規化ユーティリティ
- Strategy
  - 特徴量構築（ファクター正規化・ユニバースフィルタ・features テーブルへの UPSERT）
  - シグナル生成（最終スコア計算、BUY/SELL の判定、signals テーブルへの書き込み）
- Data（ニュース）
  - RSS フィードからの記事収集、前処理、raw_news 保存
  - 記事 → 銘柄コード（4桁）抽出、news_symbols への紐付け
  - SSRF 対策・サイズ制限・XML サニタイズ等の安全設計
- カレンダー管理
  - market_calendar の差分更新／営業日判定／next/prev/get_trading_days 等
- 設定管理
  - .env / 環境変数の自動ロード（プロジェクトルート検出）
  - 必須環境変数のラッパー（settings オブジェクト）

---

## 必要要件（依存）

主要な Python パッケージ（抜粋）:
- Python 3.9+
- duckdb
- defusedxml

（実行環境に応じて urllib / 標準ライブラリのみで動作する部分も多くありますが、DuckDB と defusedxml は推奨されます）

---

## セットアップ手順

1. リポジトリをクローン／配置

   git clone ... または ローカルに展開

2. 仮想環境の作成（推奨）

   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate

3. 依存パッケージをインストール

   pip install duckdb defusedxml
   # またはプロジェクトに requirements.txt があれば pip install -r requirements.txt

4. 環境変数設定
   - プロジェクトルート（.git または pyproject.toml を含むディレクトリ）に `.env` を置くと、自動で読み込まれます。
   - 自動読み込みを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

   必須の環境変数（Settings 参照）:
   - JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
   - KABU_API_PASSWORD: kabu ステーション API のパスワード（必須、execution 関連）
   - SLACK_BOT_TOKEN: Slack 通知用トークン（必須）
   - SLACK_CHANNEL_ID: Slack チャンネル ID（必須）

   任意（デフォルトあり）:
   - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
   - LOG_LEVEL: DEBUG/INFO/...（デフォルト: INFO）
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH: 監視用 SQLite のパス（デフォルト: data/monitoring.db）

   例 (.env):
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxx
   KABU_API_PASSWORD=secret-password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

5. DuckDB スキーマの初期化

   Python REPL やスクリプトで次を実行:

   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")

   これにより必要なすべてのテーブルとインデックスが作成されます。

---

## 使い方（クイックスタート）

以下は代表的な利用例です。実際はスクリプト化して cron/CI 等で定期実行する想定です。

- 日次 ETL を実行してデータを更新する

  from datetime import date
  from kabusys.data.schema import init_schema
  from kabusys.data.pipeline import run_daily_etl

  conn = init_schema("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())

- 特徴量（features）を構築する

  from datetime import date
  from kabusys.data.schema import get_connection, init_schema
  from kabusys.strategy import build_features

  conn = get_connection("data/kabusys.duckdb")
  # 初回は init_schema を実行しておくこと
  count = build_features(conn, target_date=date.today())
  print(f"features upserted: {count}")

- シグナルを生成する

  from datetime import date
  from kabusys.data.schema import get_connection
  from kabusys.strategy import generate_signals

  conn = get_connection("data/kabusys.duckdb")
  total = generate_signals(conn, target_date=date.today(), threshold=0.6)
  print(f"signals generated: {total}")

- ニュース収集ジョブを実行（RSS）

  from kabusys.data.schema import get_connection
  from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

  conn = get_connection("data/kabusys.duckdb")
  known_codes = {"7203", "6758", "9984", ...}  # 既知の銘柄コードセット
  results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
  print(results)

- カレンダー更新ジョブ（夜間バッチ）

  from kabusys.data.schema import get_connection
  from kabusys.data.calendar_management import calendar_update_job

  conn = get_connection("data/kabusys.duckdb")
  saved = calendar_update_job(conn)
  print(f"market_calendar saved: {saved}")

---

## API のポイント（設計・注意点）

- 冪等性
  - データ保存関数（save_*）やテーブル初期化は冪等に動作する設計です。繰り返し実行しても二重登録を避けます。
- Look-ahead バイアス対策
  - 特徴量計算やシグナル生成は target_date 時点のみのデータを使用する設計です（過去データのみ参照）。
  - データ取得時には fetched_at を UTC で保持し、いつそのデータがシステムで利用可能になったかトレース可能です。
- リトライ / レート制御
  - J-Quants クライアントはリトライ（指数バックオフ）と固定間隔のレート制御を実装しています。
  - 401 エラー時はリフレッシュトークンで自動更新 → 再試行を行います（1 回のみ）。
- セキュリティ / 安全設計
  - RSS 取得時には SSRF 対策（リダイレクト先検査、プライベート IP 拒否）、XML サニタイズ（defusedxml）を行います。
  - .env の自動ロードはプロジェクトルートを走査して行います（CWD に依存せずパッケージ配布後も安全）。

---

## ディレクトリ構成（主要ファイル）

リポジトリの主要なモジュール構成（src/kabusys 以下）:

- kabusys/
  - __init__.py
  - config.py                      # 環境変数 / 設定の読み込み
  - data/
    - __init__.py
    - jquants_client.py             # J-Quants API クライアント（取得 / 保存）
    - news_collector.py             # RSS ニュース収集・保存・紐付け
    - schema.py                     # DuckDB スキーマ定義・初期化
    - stats.py                      # 統計ユーティリティ（zscoreなど）
    - pipeline.py                   # ETL パイプライン（run_daily_etl 等）
    - calendar_management.py        # 市場カレンダー管理
    - features.py                   # data 層の特徴量ユーティリティ公開
    - audit.py                      # 監査ログ（signal → order → execution のトレーサビリティ）
  - research/
    - __init__.py
    - factor_research.py            # ファクター計算（momentum, volatility, value）
    - feature_exploration.py        # 将来リターン・IC・統計サマリ
  - strategy/
    - __init__.py
    - feature_engineering.py        # features の構築（正規化・ユニバースフィルタ）
    - signal_generator.py           # シグナル生成ロジック
  - execution/                       # 発注 / ブローカー連携（空の __init__ が存在）
  - monitoring/                      # 監視・メトリクス（将来実装想定）

（上記は主要モジュールの抜粋です。詳細は各ファイルの docstring を参照してください。）

---

## よくある質問 / トラブルシューティング

- .env の自動ロードが動作しない
  - パッケージは .git または pyproject.toml を探してプロジェクトルートを決定します。これらがないと自動ロードをスキップします。テスト等で自動ロードを無効化したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- J-Quants の認証エラー（401）
  - refresh token が無効・期限切れの可能性があります。Settings.jquants_refresh_token を確認してください。get_id_token は自動リフレッシュを試みますが、失敗するとエラーになります。
- DuckDB 関連
  - 初回は init_schema() を必ず実行してください（テーブル定義の作成）。既存 DB に接続する場合は get_connection() を使います。
- ニュース収集で記事が保存されない
  - RSS に link / guid が無い、または不正なスキーム（http/https 以外）の場合はスキップされます。raw_news に対しては id（URL 正規化 → SHA256）で衝突判定を行い、重複はスキップされます。

---

## 貢献 / 開発

- 仕様ドキュメント（StrategyModel.md, DataPlatform.md 等）に準拠して実装されています。新機能追加や修正は対応するドキュメントを更新してください。
- テストは各モジュールごとに単体テストを追加してください（外部 API 呼び出しはモック推奨）。

---

必要であれば、README に利用例のスクリプト（systemd timer / cron / CI 用）や .env.example のテンプレートを追加します。追加したい項目があれば指示してください。