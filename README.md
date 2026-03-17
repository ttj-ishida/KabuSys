# KabuSys

日本株向け自動売買基盤のコアライブラリ（KabuSys）。  
J-Quants / RSS 等からデータを取得・保存し、ETL・品質チェック・監査ログを備えたデータプラットフォームを提供します。

主な目的:
- 株価（OHLCV）・財務データ・市場カレンダーの自動取得と DuckDB への保存
- RSS ニュース収集と銘柄紐付け
- 日次 ETL パイプライン（差分取得・バックフィル・品質チェック）
- 監査ログ（シグナル → 発注 → 約定 のトレーサビリティ）

---

## 機能一覧

- 環境変数/設定管理（自動 .env / .env.local 読み込み、必須キーの検証）
- J-Quants API クライアント
  - 株価日足、財務データ、マーケットカレンダー取得
  - レート制限管理、リトライ、トークン自動リフレッシュ
  - DuckDB へ冪等（ON CONFLICT）で保存するユーティリティ
- RSS ニュースコレクタ
  - RSS 取得・XML 安全パース（defusedxml）、SSRF 対策、URL 正規化、記事ID ハッシュ化
  - raw_news 保存（チャンク挿入＋INSERT RETURNING）、記事と銘柄の紐付け
- DuckDB スキーマ定義・初期化
  - Raw / Processed / Feature / Execution / Audit 層をカバーするテーブル群とインデックス
- ETL パイプライン
  - 差分更新（最終取得日からの再取得、デフォルトで過去数日をバックフィル）
  - 市場カレンダー先読み
  - 品質チェック（欠損・重複・スパイク・日付不整合）
- データ品質チェックモジュール（QualityIssue を返す）
- 監査ログ（signal_events / order_requests / executions 等）初期化ユーティリティ

---

## セットアップ手順

前提: Python 3.9+（型ヒントに Union 演算子等を使用しているため）、git

1. レポジトリをクローン
   git clone <repo-url>
   cd <repo-dir>

2. 仮想環境（推奨）
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate

3. 依存パッケージをインストール  
   このコードベースで明示的に使われている外部依存例:
   - duckdb
   - defusedxml
   例:
   pip install duckdb defusedxml

   （パッケージ化されている場合は `pip install -e .` や `pip install .` を行ってください）

4. 環境変数の設定  
   ルートに `.env` / `.env.local` を置くと自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。

   必須環境変数（Settings により参照される）:
   - JQUANTS_REFRESH_TOKEN   （J-Quants リフレッシュトークン）
   - KABU_API_PASSWORD       （kabuステーション API パスワード）
   - SLACK_BOT_TOKEN         （Slack 通知用 Bot トークン）
   - SLACK_CHANNEL_ID        （Slack チャンネル ID）

   任意 / デフォルト:
   - KABUSYS_ENV             （development / paper_trading / live、デフォルト development）
   - LOG_LEVEL               （DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト INFO）
   - DUCKDB_PATH             （DuckDB ファイルパス、デフォルト data/kabusys.duckdb）
   - SQLITE_PATH             （監視用 SQLite パス、デフォルト data/monitoring.db）

   簡易 .env 例:
   JQUANTS_REFRESH_TOKEN=xxxxx
   KABU_API_PASSWORD=secret
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb

---

## 使い方（主要 API と実行例）

以下は Python からの簡単な利用例です。スクリプトやジョブランナーから呼び出して使います。

- DuckDB スキーマ初期化

  from kabusys.data.schema import init_schema
  from kabusys.config import settings

  conn = init_schema(settings.duckdb_path)

  またはメモリ DB:
  conn = init_schema(":memory:")

- J-Quants トークン取得 / データ取得

  from kabusys.data.jquants_client import get_id_token, fetch_daily_quotes

  id_token = get_id_token()  # 環境変数の JQUANTS_REFRESH_TOKEN を使用
  records = fetch_daily_quotes(id_token=id_token, date_from=date(2024,1,1), date_to=date(2024,1,31))

- 日次 ETL 実行

  from datetime import date
  from kabusys.data.pipeline import run_daily_etl
  from kabusys.data.schema import init_schema
  from kabusys.config import settings

  conn = init_schema(settings.duckdb_path)
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())

  run_daily_etl は内部で市場カレンダー取得 → 株価取得 → 財務取得 → 品質チェックを順に実行します。各ステップは個別にエラーハンドリングされます。

- RSS ニュース収集（単独）

  from kabusys.data.news_collector import run_news_collection
  from kabusys.data.schema import init_schema
  from kabusys.config import settings

  conn = init_schema(settings.duckdb_path)
  # sources を指定しない場合は DEFAULT_RSS_SOURCES を使用
  results = run_news_collection(conn, known_codes={"7203","6758"})
  print(results)  # { source_name: 新規保存数 }

- 生データの保存関数（例: 株価を保存）
  from kabusys.data.jquants_client import save_daily_quotes
  # conn: DuckDB 接続、records: fetch_daily_quotes の戻り値
  saved = save_daily_quotes(conn, records)

- 品質チェック単体実行
  from kabusys.data.quality import run_all_checks
  issues = run_all_checks(conn, target_date=None)
  for i in issues:
      print(i.check_name, i.severity, i.detail)

- 自動 .env 読み込みの無効化（ユニットテスト等）
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

## 設計上の注意・運用メモ

- J-Quants のレートリミット（120 req/min）を _RateLimiter で守る設計です。大量データ取得時は待ちが発生します。
- API 呼び出しはリトライと指数バックオフを組み合わせています。401 を受けた場合はトークン自動リフレッシュを試みます。
- DuckDB への書き込みは冪等（ON CONFLICT DO UPDATE / DO NOTHING）を基本としています。外部からの直接操作時の整合性には注意してください。
- news_collector は SSRF 対策（スキーム/プライベート IP チェック）・XML 安全対策（defusedxml）・受信サイズ制限を実装しています。
- 監査テーブルは削除しない運用を想定しています（FK は ON DELETE RESTRICT 等）。タイムゾーンは UTC を標準とします。
- KABUSYS_ENV の値は "development", "paper_trading", "live" のいずれかにしてください。LOG_LEVEL は標準的なレベル文字列を使用します。

---

## ディレクトリ構成

src/kabusys/
- __init__.py                - パッケージ定義（version 等）
- config.py                  - 環境変数 / 設定管理（.env 自動読み込み、Settings クラス）
- data/
  - __init__.py
  - jquants_client.py        - J-Quants API クライアント、保存ユーティリティ
  - news_collector.py        - RSS ニュース収集・前処理・DB 保存
  - schema.py                - DuckDB スキーマ定義と初期化（init_schema / get_connection）
  - pipeline.py              - ETL パイプライン（差分取得・ETL 実行・品質チェック）
  - audit.py                 - 監査ログ（signal_events / order_requests / executions）初期化
  - quality.py               - データ品質チェック（欠損・スパイク・重複・日付不整合）
- strategy/
  - __init__.py              - 戦略関連（要実装 / 拡張ポイント）
- execution/
  - __init__.py              - 発注・ブローカー連携（要実装 / 拡張ポイント）
- monitoring/
  - __init__.py              - 監視・メトリクス関連（要実装 / 拡張ポイント）

各モジュールは設計ドキュメント（DataPlatform.md 等）を想定した実装方針と合わせて構築されています。

---

## 拡張ポイント / 開発メモ

- strategy / execution / monitoring は拡張用のエントリ空間として用意済みです。戦略実装は signals / signal_queue / orders / trades / positions 等スキーマに沿って行ってください。
- 外部ブローカー連携は execution 層で実装し、監査テーブル（order_requests / executions）へ確実に記録してください。
- テスト環境では KABUSYS_DISABLE_AUTO_ENV_LOAD を有効にして環境依存を除去し、DuckDB の ":memory:" を使用すると良いです。

---

不明点や README に追加したい例（CI/CD、docker-compose、requirements.txt の内容、運用ガイド等）があれば教えてください。README をさらに詳細化して提供します。