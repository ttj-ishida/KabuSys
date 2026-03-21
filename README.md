# KabuSys

日本株向け自動売買基盤（ライブラリ） — データ収集・ETL、ファクター計算、特徴量生成、シグナル算出、監査用スキーマなどを提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株に特化した自動売買システムのコアライブラリです。主に以下の責務を持つモジュール群を含みます。

- J-Quants API からのデータ取得（株価・財務・マーケットカレンダー）
- RSS ベースのニュース収集と記事の前処理・銘柄紐付け
- DuckDB を用いたデータスキーマ定義・初期化
- ETL パイプライン（差分取得、保存、品質チェック）
- 研究用ファクター計算（モメンタム、ボラティリティ、バリュー等）
- 特徴量正規化・合成（features テーブルの作成）
- シグナル生成（final_score の計算、BUY/SELL 判定）
- マーケットカレンダー管理、監査ログ（order/signal トレーサビリティ）

設計上、ルックアヘッドバイアスを避けるため「target_date 時点のデータのみ」を使う方針や、DB への書き込みは冪等（ON CONFLICT / トランザクション）に配慮しています。

---

## 主な機能一覧

- data/jquants_client
  - API 呼び出し（ページネーション・レート制御・リトライ・トークン自動リフレッシュ）
  - データ保存用ユーティリティ（raw_prices / raw_financials / market_calendar）
- data/news_collector
  - RSS 取得・前処理（URL 正規化・トラッキング除去）
  - raw_news 保存、記事 ↔ 銘柄の紐付け
  - SSRF 対策・サイズ制限・XML 漏れ対策（defusedxml）
- data/schema
  - DuckDB 用のスキーマ定義と init_schema(db_path) による初期化
- data/pipeline
  - run_daily_etl: 日次 ETL（カレンダー先読み / 株価差分取得 / 財務差分取得 / 品質チェック）
- data/calendar_management
  - 営業日判定 / next/prev_trading_day / calendar_update_job
- research
  - calc_momentum / calc_volatility / calc_value（prices_daily / raw_financials を参照）
  - calc_forward_returns / calc_ic / factor_summary
- strategy
  - build_features: 生ファクターから features テーブルを構築
  - generate_signals: features と ai_scores から BUY/SELL シグナルを生成
- audit
  - 監査ログ用テーブル（signal_events / order_requests / executions 等）
- 共通ユーティリティ
  - data/stats.zscore_normalize など

---

## 要求環境（依存関係）

最低限の依存（概算）:

- Python 3.9+
- duckdb
- defusedxml

（HTTP は標準ライブラリ urllib を利用しています。実運用ではログ設定や追加の監視ライブラリなどを導入してください。）

インストール例（仮）:
```bash
python -m pip install duckdb defusedxml
# または
pip install -r requirements.txt  # リポジトリに requirements.txt を用意した場合
```

---

## 環境変数 / 設定

自動で .env / .env.local をプロジェクトルートから読み込みます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。主な必須環境変数:

- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID: Slack 通知先チャンネル ID（必須）

任意／デフォルト値:
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 sqlite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV: 実行環境 ("development" | "paper_trading" | "live", デフォルト "development")
- LOG_LEVEL: ログレベル ("DEBUG","INFO",...)（デフォルト "INFO"）

必須設定が不足した場合は Settings のプロパティで ValueError が出ます（kabusys.config.Settings を通じて参照）。

---

## セットアップ手順

1. リポジトリをクローン
   ```bash
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境作成（推奨）
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # macOS/Linux
   .venv\Scripts\activate     # Windows
   ```

3. 依存ライブラリをインストール
   ```bash
   pip install duckdb defusedxml
   ```

4. 環境変数を設定
   - プロジェクトルートに `.env` または `.env.local` を作成して必要なキーを設定してください（例は .env.example を参照してください）。
   - 自動読み込みが不要な場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

5. DuckDB スキーマ初期化
   Python REPL またはスクリプトから:
   ```python
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")  # :memory: も可
   conn.close()
   ```

---

## 使い方（代表的な API）

以下は代表的な利用例です。各関数はプログラム的に呼び出す用途を想定しています。

- 日次 ETL を実行してデータを収集・保存する
  ```python
  from kabusys.data.schema import init_schema
  from kabusys.data.pipeline import run_daily_etl

  conn = init_schema("data/kabusys.duckdb")
  result = run_daily_etl(conn)  # target_date を指定可能
  print(result.to_dict())
  ```

- 市場カレンダーの夜間更新ジョブ
  ```python
  from kabusys.data.schema import init_schema
  from kabusys.data.calendar_management import calendar_update_job

  conn = init_schema("data/kabusys.duckdb")
  saved = calendar_update_job(conn)
  print("saved:", saved)
  ```

- 研究用ファクター計算 / 特徴量生成 / シグナル生成（例）
  ```python
  from kabusys.data.schema import init_schema
  from datetime import date
  from kabusys.strategy import build_features, generate_signals

  conn = init_schema("data/kabusys.duckdb")
  target = date(2024, 1, 5)
  n_features = build_features(conn, target)
  n_signals = generate_signals(conn, target)
  print("features:", n_features, "signals:", n_signals)
  ```

- RSS ニュース収集ジョブ
  ```python
  from kabusys.data.schema import init_schema
  from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

  conn = init_schema("data/kabusys.duckdb")
  known_codes = {"7203", "6758", "9984"}  # 例: 有効な銘柄コードセット
  results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
  print(results)
  ```

- J-Quants から生データを取得して保存（個別呼び出し）
  ```python
  from kabusys.data.schema import init_schema
  from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes

  conn = init_schema("data/kabusys.duckdb")
  records = fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,5))
  saved = save_daily_quotes(conn, records)
  ```

注意: これらはライブラリ API の一例です。運用ではログ設定、例外ハンドリング、認証トークンの注入（テスト用）などを適切に行ってください。

---

## ディレクトリ構成

主要ファイル・ディレクトリの概観（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                     — 環境変数・設定管理
  - data/
    - __init__.py
    - jquants_client.py            — J-Quants API クライアント + 保存関数
    - news_collector.py            — RSS 取得・前処理・保存
    - schema.py                    — DuckDB スキーマ定義 & init_schema / get_connection
    - stats.py                     — zscore_normalize 等統計ユーティリティ
    - pipeline.py                  — ETL パイプライン（run_daily_etl 他）
    - calendar_management.py       — 営業日判定・カレンダー更新ジョブ
    - audit.py                     — 監査ログスキーマ
    - features.py                  — data.stats の再エクスポート
    - ...（他モジュール）
  - research/
    - __init__.py
    - factor_research.py           — calc_momentum / calc_volatility / calc_value
    - feature_exploration.py       — calc_forward_returns / calc_ic / factor_summary
  - strategy/
    - __init__.py
    - feature_engineering.py       — build_features
    - signal_generator.py          — generate_signals
  - execution/                     — 発注・ブローカー接続層（プレースホルダ）
  - monitoring/                    — 監視・可視化層（プレースホルダ）
- pyproject.toml (想定)
- .env / .env.local (プロジェクトルートで環境変数定義)

---

## 運用上の注意

- 環境（KABUSYS_ENV）は development / paper_trading / live のいずれかを設定してください。live で実行する前に十分なレビューとテストを行ってください。
- DuckDB スキーマは init_schema で作成します。稼働中にスキーマを直接変更するとデータ整合性に影響します。
- J-Quants API のレート制限（120 req/min）に合わせた実装が組み込まれていますが、運用の呼び出し頻度には注意してください。
- news_collector は外部 RSS を扱うため SSRF / XML 関連のリスクに配慮した実装ですが、運用環境でアクセス制御（プロキシ、ファイアウォール等）を併用してください。
- 生成される signals テーブルは発注システムへのインターフェースではありません。execution 層で取引所・証券会社の API に変換する実装が必要です。

---

## 開発・テストのヒント

- 自動環境変数ロードを無効にしてテストしたい場合:
  ```bash
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  ```
- DuckDB を :memory: で使えば単体テストが高速に回せます。
- jquants_client の HTTP 呼び出しや news_collector の _urlopen をモックして外部依存を切り離してテストしてください。

---

必要であれば README に「コマンドラインツール（例: run_etl.py）」や CI/デプロイ設定、.env.example の具体例、テスト実行方法などの追記を行えます。どの項目を優先して追記しますか？