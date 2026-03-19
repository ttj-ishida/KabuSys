# KabuSys

バージョン: 0.1.0

KabuSys は日本株向けの研究〜データプラットフォーム〜戦略〜発注に至る自動売買基盤の基礎コンポーネント群です。DuckDB をデータレイヤに用い、J-Quants API による市場データ取得、RSS ニュース収集、特徴量生成、シグナル生成、監査ログ機能などを備えています。

主な目的は「研究で検証したファクターを運用に繋げる」ための安全で冪等なデータ処理・戦略実行基盤を提供することです。

## 主な機能一覧
- 環境変数／設定管理
  - .env/.env.local の自動読み込み（プロジェクトルート基準）。KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能。
  - 各種必須環境変数のアクセスラッパー（設定の検証を含む）。
- データ取得 / ETL
  - J-Quants API クライアント（レート制限、リトライ、トークン自動更新、ページネーション対応）
  - 差分 ETL パイプライン（株価、財務、カレンダーの差分取得・保存）
  - 市場カレンダー更新ジョブ
- データ格納スキーマ（DuckDB）
  - Raw / Processed / Feature / Execution 層のテーブル定義と初期化（init_schema）
  - 冪等性を考慮した INSERT/UPSET 実装
- ニュース収集
  - RSS 取得、URL 正規化、トラッキングパラメータ除去、SSRF 対策、記事の保存と銘柄抽出
- 研究用ファクター計算
  - Momentum / Volatility / Value の計算関数（prices_daily / raw_financials を参照）
  - 将来リターン計算、IC（Spearman）計算、ファクター統計サマリ
- 特徴量エンジニアリング
  - 生ファクターの正規化（Z スコア）、ユニバースフィルタ、features テーブルへの日付単位 UPSERT
- シグナル生成
  - features / ai_scores / positions を統合して final_score を算出、BUY/SELL シグナルを生成して signals テーブルへ保存
  - Bear レジーム判定やストップロス等のエグジット判定を実装
- 監査（Audit）
  - signal_events / order_requests / executions 等、トレーサビリティ確保のためのテーブル群
- 汎用ユーティリティ
  - Z スコア正規化等の統計ユーティリティ

## 必要条件 / 依存
- Python 3.10 以上（型注釈に Python 3.10 の構文を使用）
- 主要依存ライブラリ（例）
  - duckdb
  - defusedxml
- ネットワークアクセス: J-Quants API / 各 RSS ソースへのアクセス

※ 実行環境に合わせて依存パッケージは requirements.txt 等で管理してください。

## 環境変数（主なもの）
以下はコード内で参照される主要な環境変数です（README 用抜粋）。

必須（未設定時は ValueError）:
- JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID — Slack チャネル ID

任意 / デフォルトあり:
- KABUSYS_ENV — 実行環境 (development | paper_trading | live), デフォルト: development
- LOG_LEVEL — ログレベル（DEBUG, INFO, ...）, デフォルト: INFO
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env ロードを無効化する場合は "1"
- KABUSYS_DISABLE_AUTO_ENV_LOAD を設定している場合は .env の自動読み込みを行いません
- KABUSYS 自動ロードではプロジェクトルートを .git または pyproject.toml を基準に探索します

データベース関連:
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）

## セットアップ手順（例）
1. Python 環境を準備（3.10+ 推奨）
   - venv を作成して有効化
     ```
     python -m venv .venv
     source .venv/bin/activate  # Unix/macOS
     .venv\Scripts\activate     # Windows
     ```

2. 依存パッケージをインストール
   ```
   pip install duckdb defusedxml
   ```
   ※ 実プロジェクトでは requirements.txt / pyproject.toml で依存管理してください。

3. 環境変数を準備
   - プロジェクトルートに .env を作成（.env.example を参考に）
   - 例 (.env):
     ```
     JQUANTS_REFRESH_TOKEN=xxxx
     KABU_API_PASSWORD=yyyy
     SLACK_BOT_TOKEN=zzz
     SLACK_CHANNEL_ID=C01234567
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     ```
   - 自動ロードを無効化する場合:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```

4. DuckDB スキーマ初期化（Python REPL またはスクリプトで）
   ```py
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")
   ```

## 使い方（主な API の例）

- DuckDB 接続とスキーマ初期化
  ```py
  from kabusys.data.schema import init_schema, get_connection
  conn = init_schema("data/kabusys.duckdb")  # 存在しなければディレクトリ作成・DDL 実行
  # 既存 DB に接続するだけなら:
  conn = get_connection("data/kabusys.duckdb")
  ```

- 日次 ETL 実行（市場カレンダー、株価、財務）
  ```py
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

- 市場カレンダー更新ジョブ
  ```py
  from kabusys.data.calendar_management import calendar_update_job
  saved = calendar_update_job(conn)
  ```

- ニュース収集（RSS）と保存
  ```py
  from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

  known_codes = {"7203","6758", ...}  # 有効銘柄リスト
  res = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
  print(res)
  ```

- 特徴量（features）構築
  ```py
  from datetime import date
  from kabusys.strategy import build_features

  n = build_features(conn, target_date=date.today())
  print(f"features upserted: {n}")
  ```

- シグナル生成
  ```py
  from datetime import date
  from kabusys.strategy import generate_signals

  total = generate_signals(conn, target_date=date.today(), threshold=0.6)
  print(f"signals written: {total}")
  ```

- 研究用ユーティリティ
  ```py
  from kabusys.research import calc_forward_returns, calc_ic

  fwd = calc_forward_returns(conn, target_date=date.today(), horizons=[1,5,21])
  # factor_records は例えば calc_momentum の戻り値
  ic = calc_ic(factor_records, fwd, factor_col="mom_1m", return_col="fwd_1d")
  ```

## 自動 .env 読み込みの挙動
- パッケージ起動時にプロジェクトルート（.git または pyproject.toml があるディレクトリ）を探索して .env / .env.local を自動読み込みします。
- 読み込み優先順位: OS 環境 > .env.local > .env
- テスト等で自動ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。

## ログと動作モード
- KABUSYS_ENV（development / paper_trading / live）で内部の挙動やチェック基準を切り替えます。
- LOG_LEVEL 環境変数でログレベルを指定します（DEBUG, INFO, WARNING, ERROR, CRITICAL）。

## ディレクトリ構成（主要ファイル）
（パッケージルートに src ディレクトリを想定）

- src/kabusys/
  - __init__.py
  - config.py — 環境変数・設定管理
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント（取得/保存ユーティリティ含む）
    - news_collector.py — RSS ニュース収集と銘柄抽出
    - schema.py — DuckDB スキーマ定義・初期化
    - pipeline.py — ETL パイプライン（run_daily_etl 等）
    - calendar_management.py — 市場カレンダー管理・ユーティリティ
    - features.py — features 関連の再エクスポート（zscore_normalize）
    - stats.py — 統計ユーティリティ（zscore_normalize）
    - audit.py — 監査ログ用 DDL 定義（signal_events / order_requests / executions 等）
    - ...（その他データ関連モジュール）
  - research/
    - __init__.py
    - factor_research.py — momentum/volatility/value 計算
    - feature_exploration.py — 将来リターン / IC / summary 等
  - strategy/
    - __init__.py
    - feature_engineering.py — 生ファクター正規化・features 書き込み
    - signal_generator.py — final_score 計算と signals テーブル書き込み
  - execution/
    - __init__.py (発注層は今後実装)
  - monitoring/
    - (監視関連モジュールがここに入る想定)

## 実運用上の注意（重要）
- 金融データを扱うため、ルックアヘッドバイアスやトレード実行の冪等性に特に配慮した実装になっています。実際の運用では下記に留意してください:
  - API の認証情報・秘密情報は安全に保管すること（例: シークレット管理、アクセス制御）
  - 本コードは研究〜運用の骨組みを提供しますが、実運用前にバックテスト・ペーパー運用・監査を十分に行ってください
  - 発注層（execution）の実エンドポイント接続は別途安全性・リトライ・冪等性設計が必要です
  - DuckDB ファイルやログは定期的にバックアップしてください

## 貢献 / 拡張案
- execution 層のブローカーインテグレーション実装
- Slack 等への通知・モニタリング機能の充実
- 自動テスト・CI の追加（ETL のモックテスト等）
- Docker コンテナ化（実行環境の一元化）

---

詳しい API の仕様や設計ドキュメント（StrategyModel.md, DataPlatform.md, 等）がプロジェクト内にあれば、それに従って追加設定や運用ルールを整備してください。質問や具体的な使い方のサンプルが必要であれば、実行したいユースケース（例: 初回データロード、daily ETL の cron 設定、シグナル→発注フロー）を教えてください。対応例を示します。