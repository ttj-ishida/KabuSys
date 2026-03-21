# KabuSys

日本株向けの自動売買基盤ライブラリです。データ収集（J-Quants）、ETL、特徴量生成、シグナル生成、ニュース収集、監査ログなどを含むモジュール群を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下を目的としたモジュール群です。

- J-Quants API からの株価・財務・マーケットカレンダー取得（差分更新・ページネーション対応・レート制御）
- DuckDB を用いたデータスキーマ（Raw / Processed / Feature / Execution 層）と初期化
- ETL パイプライン（差分取得、保存、品質チェック）
- 研究用ファクター計算（モメンタム・ボラティリティ・バリュー等）と特徴量加工（Z スコア正規化等）
- シグナル生成（複数コンポーネントの重み付け合成、Bear レジーム抑制、エグジット判定）
- RSS ベースのニュース収集と銘柄紐付け（SSRF対策・gzip/サイズ制限・トラッキングパラメータ除去）
- 監査ログ用テーブル（signal → order → execution のトレーサビリティ）

設計の重点は「ルックアヘッドバイアスの回避」「冪等性（ON CONFLICT）」「ロバストなエラー/再試行ロジック」です。

---

## 主な機能一覧

- 環境設定管理（.env / .env.local 自動読み込み、KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化）
- DuckDB スキーマ初期化（init_schema）
- J-Quants クライアント（レート制御・リトライ・トークン自動リフレッシュ）
- 日次 ETL（run_daily_etl: カレンダー/株価/財務の差分取得 + 品質チェック）
- ファクター計算（calc_momentum/calc_volatility/calc_value）
- 特徴量作成（build_features: 正規化・フィルタ・features テーブルへのUPSERT）
- シグナル生成（generate_signals: final_score 計算、BUY/SELL シグナルの生成と保存）
- ニュース収集（RSS フェッチ、正規化、raw_news 保存、銘柄抽出・紐付け）
- マーケットカレンダー管理（営業日判定、next/prev/get_trading_days、calendar_update_job）
- 監査ログ（signal_events / order_requests / executions 等のDDLと保存処理）

---

## 要件

- Python 3.10 以上（型注釈の union 型 `X | Y` を使用）
- 必要なパッケージ（最低限）:
  - duckdb
  - defusedxml

インストール例:
```
python -m venv .venv
source .venv/bin/activate
pip install "duckdb" "defusedxml"
# プロジェクト配布パッケージがある場合は pip install -e . 等
```

（実際のプロダクション用途ではさらにロギング、監視、CI/CD、パッケージ依存を整備してください。）

---

## 環境変数 / .env

KabuSys は .env / .env.local から設定を自動読み込みします（プロジェクトルートは .git または pyproject.toml を起点に探索）。自動読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

主な環境変数:

- J-Quants
  - JQUANTS_REFRESH_TOKEN (必須) — J-Quants の refresh token
- kabuステーション API
  - KABU_API_PASSWORD (必須)
  - KABU_API_BASE_URL (任意, デフォルト: http://localhost:18080/kabusapi)
- Slack
  - SLACK_BOT_TOKEN (必須)
  - SLACK_CHANNEL_ID (必須)
- データベース・パス
  - DUCKDB_PATH (任意, デフォルト: data/kabusys.duckdb)
  - SQLITE_PATH (任意, デフォルト: data/monitoring.db)
- 実行環境
  - KABUSYS_ENV (development | paper_trading | live) — デフォルト development
  - LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL) — デフォルト INFO

注意: Settings に必須キーが無い場合は起動時に ValueError が発生します。.env.example を参考に .env を作成してください。

---

## セットアップ手順

1. リポジトリをクローンして仮想環境を作成・有効化
   - 例: python -m venv .venv && source .venv/bin/activate

2. 依存ライブラリをインストール
   - 例: pip install duckdb defusedxml

3. 環境変数の設定
   - プロジェクトルートに `.env`（または `.env.local`）を作成し、必要な値を設定してください。
   - 例:
     ```
     JQUANTS_REFRESH_TOKEN=xxxxx
     KABU_API_PASSWORD=xxxxx
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     ```

4. DuckDB スキーマ初期化
   - Python インタラクティブまたはスクリプトで init_schema を呼び出します:
     ```
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")
     ```
   - ":memory:" を渡すとインメモリ DB が使えます。

5. （オプション）ETL 実行・機能確認
   - run_daily_etl を使ってデータを取得・保存・品質チェックを実行できます（下の「使い方」を参照）。

---

## 使い方（サンプル）

以下は最低限の実行例です。実際にはログ設定や例外処理を行ってください。

- DuckDB 初期化:
  ```
  from kabusys.data.schema import init_schema
  conn = init_schema("data/kabusys.duckdb")
  ```

- 日次 ETL 実行（市場カレンダー・株価・財務の差分取得）:
  ```
  from kabusys.data.pipeline import run_daily_etl
  result = run_daily_etl(conn)
  print(result.to_dict())
  ```

- 特徴量（features）作成:
  ```
  from datetime import date
  from kabusys.strategy import build_features
  cnt = build_features(conn, date(2024, 1, 10))
  print("upserted features:", cnt)
  ```

- シグナル生成:
  ```
  from datetime import date
  from kabusys.strategy import generate_signals
  total = generate_signals(conn, date(2024, 1, 10))
  print("signals written:", total)
  ```

- ニュース収集ジョブ:
  ```
  from kabusys.data.news_collector import run_news_collection
  known_codes = {"7203", "6758", "9432"}  # 既知の銘柄コードセット
  results = run_news_collection(conn, known_codes=known_codes)
  print(results)
  ```

- マーケットカレンダー更新（夜間バッチ）:
  ```
  from kabusys.data.calendar_management import calendar_update_job
  saved = calendar_update_job(conn)
  print("calendar saved:", saved)
  ```

注意:
- それぞれの関数は DuckDB 接続（duckdb.DuckDBPyConnection）を引数に取ります。
- シグナル生成・特徴量作成は DB に期待するテーブル（prices_daily / raw_financials / features / ai_scores / positions 等）が存在し、必要なデータが入っていることが前提です。

---

## ディレクトリ構成（主要ファイル）

（プロジェクトの src/kabusys 以下にある主なモジュール一覧）

- src/kabusys/
  - __init__.py
  - config.py                     — 環境変数・設定管理
  - data/
    - __init__.py
    - jquants_client.py           — J-Quants API クライアント（取得・保存）
    - schema.py                   — DuckDB スキーマ定義と init_schema / get_connection
    - pipeline.py                 — ETL パイプライン（run_daily_etl など）
    - news_collector.py           — RSS ニュース収集・正規化・保存
    - calendar_management.py      — 市場カレンダー管理（is_trading_day 等）
    - features.py                 — data.stats の再エクスポート
    - stats.py                    — 統計ユーティリティ（zscore_normalize）
    - audit.py                    — 監査ログ用 DDL と初期化
    - (その他: quality.py 等が想定)
  - research/
    - __init__.py
    - factor_research.py          — ファクター計算（momentum / volatility / value）
    - feature_exploration.py      — IC / forward returns / summary 等
  - strategy/
    - __init__.py
    - feature_engineering.py      — features 作成ワークフロー
    - signal_generator.py         — final_score 計算と signals 生成
  - execution/
    - __init__.py                 — 発注・実行層（将来的に拡張）
  - monitoring/                   — 監視・メトリクス系（存在想定、__all__ に含む）

---

## 注意事項 / 運用上のポイント

- 環境変数は .env / .env.local から自動読み込みされますが、OS 環境変数が優先されます。.env.local は override=True の扱いで OS 環境変数以外を上書きします。テスト時には KABUSYS_DISABLE_AUTO_ENV_LOAD を利用してください。
- J-Quants API のレート制限（120 req/min）やリトライポリシーが実装されていますが、実運用ではさらに運用監視を行ってください。
- DuckDB スキーマは冪等（CREATE TABLE IF NOT EXISTS / ON CONFLICT）設計です。スキーマ変更は後方互換性に注意してください。
- シグナル生成では Bear レジーム検知やストップロス等のルールを実装していますが、資金管理・発注ロジックは別途実装してください（execution 層は依存しない設計）。
- ニュース収集は SSRF や XML Bomb、過大レスポンス対策を施していますが、外部フィードの整合性チェックや監視を行ってください。
- 本リポジトリのコードは一部研究/プロトタイプ用途を想定しています。実際の金銭取引で用いる前に十分なテスト、シミュレーション、リスクレビューを行ってください。

---

## 貢献 / 開発者向け

- テスト: 各モジュールは DuckDB のインメモリ接続 (":memory:") を用いてユニットテストが書きやすくなっています。
- ローカルでの開発では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定し、明示的に settings をモックすることが推奨されます。
- ドキュメントや DataSchema.md / StrategyModel.md / DataPlatform.md 等、設計ドキュメントと整合性を保って開発してください。

---

必要であれば、README に具体的な例（.env.example、テーブル定義の抜粋、よくあるエラーと対処法）を追加します。どの部分を詳しくしたいか教えてください。