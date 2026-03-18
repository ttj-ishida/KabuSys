# KabuSys

日本株自動売買システム用ライブラリ (KabuSys)。  
このリポジトリはデータ収集（J-Quants / RSS）、データベーススキーマ（DuckDB）、ETLパイプライン、データ品質チェック、マーケットカレンダー管理、監査ログ（発注〜約定トレーサビリティ）など、戦略・実行層の基盤機能を提供します。

---

## 主な特徴（概要）

- J-Quants API クライアント
  - 日足（OHLCV）、四半期財務データ、JPXマーケットカレンダーの取得
  - APIレート制御（120 req/min のスロットリング）
  - 自動リトライ（指数バックオフ、最大3回）、401発生時はリフレッシュトークンによるトークン再取得
  - 取得時刻（fetched_at）を UTC で記録し look-ahead bias を防止
  - DuckDB への冪等保存（ON CONFLICT …）

- RSS ニュース収集
  - RSS フィードの取得・前処理（URL除去、空白正規化）
  - 記事IDは正規化URLの SHA-256（先頭32文字）
  - SSRF対策（スキーム検証、プライベートIPブロック、リダイレクト検証）
  - レスポンスサイズ制限（デフォルト 10MB）
  - defusedxml を使用した XML 攻撃対策
  - DuckDB への冪等保存（INSERT … RETURNING を利用）

- DuckDB スキーマ管理
  - Raw / Processed / Feature / Execution 層のテーブル定義を提供
  - インデックス、外部キー、チェック制約を含むDDL
  - スキーマ初期化のユーティリティ（init_schema 等）

- ETL パイプライン
  - 差分更新（DBの最終取得日から未取得分のみを取得）
  - backfill による直近再取得で API 側の後出し修正に対応
  - 市場カレンダー先読み（lookahead）
  - 品質チェックの実行（欠損・重複・スパイク・日付不整合）

- データ品質チェック
  - 欠損データ検出、主キー重複、株価スパイク（前日比閾値）、将来日付・非営業日データ検出
  - 問題は QualityIssue オブジェクト群で返却（severityに応じて呼び出し側が対応）

- マーケットカレンダー管理
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day 等のユーティリティ
  - DBにない日付は曜日（平日/週末）でフォールバック

- 監査ログ（Audit）
  - signal_events / order_requests / executions 等、UUID によるトレーサビリティ設計
  - 発注の冪等性（order_request_id）をサポート
  - UTC タイムゾーン固定

---

## 必要環境 / 依存

- Python 3.10 以上（PEP 604 の型記法（| None）を使用）
- 必要パッケージ（例）
  - duckdb
  - defusedxml

（実際の requirements.txt がある場合はそれを使用してください。ない場合は最低限上記をインストールしてください。）

例:
pip install duckdb defusedxml

---

## 環境変数（設定）

自動で `.env` / `.env.local` をプロジェクトルートから読み込みます（CWD に依存しません）。自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト用）。

主に使用する環境変数:

- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API 用パスワード（必須）
- KABU_API_BASE_URL: kabuAPI のベースURL（省略可、デフォルト http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID: Slack チャンネルID（必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト data/monitoring.db）
- KABUSYS_ENV: 環境 ("development" | "paper_trading" | "live")
- LOG_LEVEL: ログレベル ("DEBUG" | "INFO" | "WARNING" | "ERROR" | "CRITICAL")

例 (.env):
JQUANTS_REFRESH_TOKEN=your_refresh_token_here
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C12345678
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO

---

## セットアップ手順

1. リポジトリをクローン
   git clone <repo-url>
   cd <repo-dir>

2. 仮想環境作成（推奨）
   python -m venv .venv
   source .venv/bin/activate  # Unix系
   .venv\Scripts\activate     # Windows

3. 依存パッケージをインストール
   pip install duckdb defusedxml

   （requirements.txt がある場合は pip install -r requirements.txt）

4. 環境変数を設定
   - プロジェクトルートに `.env` を作成して必要な環境変数を記載
   - 自動読み込みをテストで無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

5. DuckDB スキーマ初期化（Python から）
   サンプル:
   from kabusys.data import schema
   conn = schema.init_schema("data/kabusys.duckdb")

6. 監査DB初期化（オプション）
   from kabusys.data import audit
   conn = audit.init_audit_db("data/audit.duckdb")

---

## 使い方（主要な API／例）

以下の例は Python REPL / スクリプトから実行する想定です。

- スキーマ初期化（既存ならスキップ）
  from kabusys.data import schema
  conn = schema.init_schema("data/kabusys.duckdb")

- 日次 ETL 実行（J-Quants からデータを取得して保存・品質チェック）
  from kabusys.data import pipeline
  result = pipeline.run_daily_etl(conn)
  print(result.to_dict())

- 個別 ETL ジョブ
  # 株価差分ETL
  pipeline.run_prices_etl(conn, target_date=date.today())
  # 財務データETL
  pipeline.run_financials_etl(conn, target_date=date.today())
  # カレンダーETL
  pipeline.run_calendar_etl(conn, target_date=date.today())

- RSS ニュース収集（既存 DuckDB 接続へ保存）
  from kabusys.data.news_collector import run_news_collection
  results = run_news_collection(conn, sources=None, known_codes={"7203","6758"})
  print(results)

- J-Quants のトークンを直接取得する
  from kabusys.data.jquants_client import get_id_token
  token = get_id_token()  # settings.jquants_refresh_token を使用

- DuckDB 接続取得（スキーマ初期化せず既存DBに接続）
  from kabusys.data import schema
  conn = schema.get_connection("data/kabusys.duckdb")

- 品質チェックのみ実行
  from kabusys.data import quality
  issues = quality.run_all_checks(conn)
  for i in issues:
      print(i)

注意:
- ETL・API 呼び出しはネットワークアクセスを行います。必要な環境（VPN・プロキシ等）がある場合は適宜設定してください。
- 自動トークンリフレッシュ、レート制御、リトライは jquants_client に実装されています。

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py
- config.py                — 環境変数 / 設定管理（.env 自動ロード、Settings）
- data/
  - __init__.py
  - jquants_client.py      — J-Quants API クライアント（取得 / 保存 関数）
  - news_collector.py      — RSS ニュース収集、前処理、DB保存
  - pipeline.py            — ETL パイプライン（差分取得・保存・品質チェック）
  - schema.py              — DuckDB スキーマ定義と初期化
  - calendar_management.py — 市場カレンダー操作・夜間更新ジョブ
  - audit.py               — 監査ログ（signal/order/execution）スキーマ
  - quality.py             — データ品質チェック（欠損・重複・スパイク・日付不整合）
- strategy/
  - __init__.py            — 戦略層（将来の拡張用）
- execution/
  - __init__.py            — 発注 / ブローカー接続関連（将来の拡張用）
- monitoring/
  - __init__.py            — 監視用コード（将来の拡張用）

README.md（本ファイル）

---

## 設計上の留意点 / 運用メモ

- ID トークンのキャッシュと自動リフレッシュによりページネーション間でトークン共有を行います。401受信時は1回のみリフレッシュして再試行します。
- J-Quants API のレート制限（120 req/min）に合わせた固定間隔スロットリングを実装しています。大量データ取得時はスループットが制限されます。
- DuckDB への保存は可能な限り冪等化（ON CONFLICT）してあり、ETL を複数回実行しても重複を防ぎます。
- RSS ニュースは SSRF、XML bomb、gzip爆弾対策を行っています。公開ソース以外を追加する際は注意してください。
- KABUSYS_ENV を `live` に切り替えると本番向けの運用フラグが有効となる箇所が想定されています（実装拡張の想定）。
- テスト時は自動 .env 読み込みを抑止するため KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してテスト専用環境をロードしてください。

---

## 追加情報 / 貢献

- バグ報告や改善提案は issue を立ててください。
- 新しい戦略や接続（kabu API 実装等）は strategy/ と execution/ に追加して下さい。
- 本 README はコードベースの現状に基づいて作成しています。実装追加に伴い README を更新してください。

--- 

以上が KabuSys の概要と基本的な使い方です。必要であれば、セットアップスクリプト、requirements.txt、サンプル .env.example を追記して README を拡張できます。どの部分を優先して詳述しますか？