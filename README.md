# KabuSys

日本株向け自動売買基盤（KabuSys）の軽量実装サンプルです。  
データ取得（J-Quants）、ETL、特徴量生成、シグナル生成、ニュース収集、DuckDB スキーマ／監査ログなど、研究→本番までのワークフローを想定したモジュール群を含みます。

主な設計方針：
- ルックアヘッドバイアスを防ぐ（日付単位での参照／計算）
- 冪等性（DB への保存は ON CONFLICT 等で安全に上書き）
- API レート制御・リトライ・トークンリフレッシュ対応
- DuckDB を用いた軽量オンディスク DB（デフォルト）

## 機能一覧
- 環境設定管理（kabusys.config）
  - プロジェクトルートから `.env` / `.env.local` を自動読み込み（無効化可能）
  - 必須環境変数チェック（例: JQUANTS_REFRESH_TOKEN）
- データ取得（kabusys.data.jquants_client）
  - J-Quants API から日足・財務・市場カレンダーデータをページネーション対応で取得
  - レートリミット、リトライ、401 時の自動トークンリフレッシュ対応
  - DuckDB への冪等保存（save_* 関数群）
- ETL パイプライン（kabusys.data.pipeline）
  - 差分取得、バックフィル、品質チェックを含む日次 ETL（run_daily_etl）
  - 個別ジョブ: run_prices_etl / run_financials_etl / run_calendar_etl
- スキーマ定義・初期化（kabusys.data.schema）
  - Raw / Processed / Feature / Execution 層のテーブルを定義
  - init_schema() による初期化（:memory: も可）
- ニュース収集（kabusys.data.news_collector）
  - RSS 取得・前処理・記事ID の生成（URL 正規化 + SHA256）
  - SSRF 対策、gzip サイズ制限、XML パース安全化（defusedxml）
  - raw_news / news_symbols への冪等保存
- 研究用ファクター計算（kabusys.research）
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - IC（Spearman）や将来リターン計算、統計サマリ機能
- 特徴量エンジニアリング（kabusys.strategy.feature_engineering）
  - 生ファクターの正規化（Z スコア）、ユニバースフィルタ、features テーブルへの保存
- シグナル生成（kabusys.strategy.signal_generator）
  - features と ai_scores を統合して final_score を計算
  - Bear レジーム抑制、BUY/SELL の判定、signals テーブルへの保存
- その他
  - 統計ユーティリティ（zscore_normalize）
  - カレンダー管理（営業日判定など）
  - 監査ログ（audit モジュール、トレーサビリティ設計）

---

## セットアップ手順

前提
- Python 3.9 以上を推奨（型ヒントに Union 後継の構文を利用）
- DuckDB, defusedxml 等の依存ライブラリが必要

1. リポジトリをクローン / checkout
2. 仮想環境を作成して有効化
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows (PowerShell では .venv\Scripts\Activate.ps1)
   ```
3. 必要パッケージをインストール（例）
   ```
   pip install duckdb defusedxml
   ```
   ※ 開発用にパッケージ管理ファイルがある場合はそれに従ってください（このサンプルでは requirements.txt は同梱されていない想定）。
4. パッケージをインストール（開発モード）
   ```
   pip install -e .
   ```
5. 環境変数を設定
   - 推奨: プロジェクトルートに `.env` を作成（.env.example を参考に）
   - 必須環境変数（Settings 参照）
     - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD: kabu ステーション API パスワード（execution 層利用時）
     - SLACK_BOT_TOKEN / SLACK_CHANNEL_ID: Slack 通知を使う場合
   - 任意
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（モニタリング用デフォルト: data/monitoring.db）
     - KABUSYS_ENV（development / paper_trading / live）
     - LOG_LEVEL（DEBUG/INFO/...）
   - 自動 .env 読み込みを無効にするには:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```
6. DuckDB スキーマ初期化
   ```python
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")
   ```
   上記で `data/` ディレクトリがなければ自動作成されます。

---

## 使い方（簡単な例）

以下は代表的なワークフロー例です。各関数は日付パラメータに datetime.date を受け取ります。

- DB 初期化（例）
  ```python
  from kabusys.data.schema import init_schema
  conn = init_schema("data/kabusys.duckdb")
  ```

- 日次 ETL を実行（J-Quants から差分取得 → 保存 → 品質チェック）
  ```python
  from kabusys.data.pipeline import run_daily_etl
  from datetime import date

  # conn は init_schema の返り値
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

- 研究ファクターから特徴量を生成して features テーブルへ保存
  ```python
  from kabusys.strategy import build_features
  from datetime import date

  cnt = build_features(conn, target_date=date.today())
  print(f"features upserted: {cnt}")
  ```

- シグナル生成（features / ai_scores / positions を参照して signals に書き込む）
  ```python
  from kabusys.strategy import generate_signals
  from datetime import date

  total = generate_signals(conn, target_date=date.today(), threshold=0.6)
  print(f"signals written: {total}")
  ```

- ニュース収集ジョブの実行（既知の銘柄コードセットを渡して紐付け）
  ```python
  from kabusys.data.news_collector import run_news_collection
  known_codes = {"7203", "6758", "9984"}  # 例
  results = run_news_collection(conn, known_codes=known_codes)
  print(results)  # {source_name: saved_count}
  ```

- J-Quants から直接データ取得（認証は Settings を利用）
  ```python
  from kabusys.data.jquants_client import fetch_daily_quotes
  from kabusys.config import settings
  from datetime import date

  # id_token を明示的に渡すことも可能（get_id_token を利用）
  records = fetch_daily_quotes(date_from=date(2024, 1, 1), date_to=date(2024, 1, 31))
  ```

注意:
- run_daily_etl 等は内部で例外をキャッチして処理を続行する設計です。戻り値（ETLResult）でエラーや品質問題を確認してください。
- features と signals の生成は DuckDB 内のテーブルを前提とします（prices_daily / raw_financials / ai_scores / positions 等）。

---

## 環境変数（主なもの）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (kabuAPI を使う場合必須)
- SLACK_BOT_TOKEN, SLACK_CHANNEL_ID (Slack 通知を使う場合必須)
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db)
- KABUSYS_ENV (development | paper_trading | live)
- LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL)
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 （自動 .env 読み込みを無効化）

例（.env の最小例）
```
JQUANTS_REFRESH_TOKEN=your_refresh_token_here
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## ディレクトリ構成（主要ファイル）
（この README は src/kabusys 配下の実装に基づきます）

- src/kabusys/
  - __init__.py
  - config.py  — 環境変数と Settings
  - data/
    - __init__.py
    - jquants_client.py  — J-Quants API クライアント（取得・保存）
    - news_collector.py  — RSS ニュース収集・前処理
    - schema.py  — DuckDB スキーマ定義 & init_schema / get_connection
    - stats.py  — zscore_normalize 等の統計ユーティリティ
    - pipeline.py  — ETL パイプライン（run_daily_etl 等）
    - features.py — zscore_normalize の再エクスポート
    - calendar_management.py — 営業日ロジック・calendar_update_job
    - audit.py — 監査ログ（signal_events, order_requests, executions）
    - (その他データ層関連モジュール)
  - research/
    - __init__.py
    - factor_research.py  — calc_momentum / calc_volatility / calc_value
    - feature_exploration.py — 将来リターン / IC / 統計サマリ
  - strategy/
    - __init__.py (build_features, generate_signals をエクスポート)
    - feature_engineering.py  — features を作る処理
    - signal_generator.py     — final_score 計算と signals 生成
  - execution/  — 発注・ブローカー連携層（空のパッケージ置き場）
  - monitoring/ — 監視・モニタリング関連（SQLite など）※実装は状況に応じて

---

## 開発時の注意点 / 設計のポイント
- 日付取り扱いはすべて date オブジェクト（datetime ではなく timezone 混在を避ける設計）を前提としている箇所が多いです。
- DuckDB の 型変換・NULL 処理に注意（多くの SQL は NULL を前提にガードしています）。
- ETL／API クライアントは冪等性を重視しているため、何度実行しても重複データが蓄積しないよう設計されています。
- ニュース収集は SSRF 防止 / レスポンスサイズ制限 / XML パースの安全化を含む保守的な実装です。
- AI スコア等外部モジュールは ai_scores テーブルに保存する想定で、信号生成では未登録時に中立値を補完します。

---

## ライセンス・貢献
この README はコードベースに対する簡易ドキュメントです。実運用前に十分なテスト・セキュリティ監査・エラーハンドリング強化を行ってください。貢献・改善提案は Pull Request / Issue で歓迎します。

---

必要であれば README にサンプル .env.example、より詳細な CLI / systemd / cron の実行例、運用チェックリスト（バックアップ、モニタ、再実行手順）なども追加できます。どの情報を追加しますか？