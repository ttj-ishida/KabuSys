# KabuSys

日本株向けの自動売買システム用ライブラリ（KabuSys）。  
市場データ取得（J-Quants）、ETL、特徴量生成、シグナル生成、ニュース収集、DuckDB スキーマ管理などを提供します。

主な設計方針は「ルックアヘッドバイアスの回避」「冪等性（idempotent）」「外部発注層からの独立」「監査可能性の確保」です。

---

## 機能一覧

- データ取得 / 保存
  - J-Quants API クライアント（fetch / save: 株価日足、財務データ、マーケットカレンダー）
  - ETL パイプライン（差分取得 / バックフィル / 品質チェック）
  - DuckDB スキーマ定義・初期化（init_schema）
- データ処理 / 特徴量
  - ファクター計算（momentum / volatility / value）
  - クロスセクション Z スコア正規化
  - features テーブルへの一括アップサート（冪等）
- 戦略
  - final_score に基づくシグナル生成（BUY / SELL）
  - Bear レジーム判定、エグジット（ストップロス等）
- ニュース収集
  - RSS フィード取得・前処理・記事保存（SSRF や XML 弱点対策あり）
  - 記事 → 銘柄コードの紐付け
- カレンダー管理
  - JPX 市場カレンダー更新・営業日判定ユーティリティ
- 監査・トレーサビリティ（監査ログ用 DDL を含む）
- コンフィグ管理
  - プロジェクトルートの `.env` / `.env.local` を自動ロード（オプションで無効化可）

---

## 要件 / 依存関係

- Python 3.10+
  - （ソースで | 型ヒント等を使用しているため 3.10 以上を想定）
- 必須ライブラリ（最低限）
  - duckdb
  - defusedxml
- 標準ライブラリ: urllib, datetime, logging, hashlib, ipaddress, socket など

実際に使う場合は requirements.txt を用意して pip でインストールしてください。例:

pip install duckdb defusedxml

---

## 環境変数

config.Settings が参照する主要な環境変数:

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants リフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API パスワード
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack Bot トークン
- SLACK_CHANNEL_ID (必須) — Slack チャネル ID
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 sqlite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — environment: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — ログレベル: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）

自動でプロジェクトルートの `.env` / `.env.local` を読み込みます。自動ロードを無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

例 (.env):
JQUANTS_REFRESH_TOKEN=your_refresh_token_here
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO

---

## セットアップ手順

1. リポジトリをクローン
   - git clone <repo-url>

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存関係をインストール
   - pip install -U pip
   - pip install duckdb defusedxml

   （プロジェクトに requirements.txt がある場合はそれを使用）

4. 環境変数を設定
   - プロジェクトルートに `.env` を作成するか、システム環境変数をセットします。
   - 必須項目: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID

5. DuckDB スキーマ初期化
   - 下記の Python スニペットを実行して DB を初期化します（例: data/kabusys.duckdb）。
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")

---

## 使い方（主要な API と使用例）

以下はライブラリの代表的な呼び出し例です。実際はアプリケーション側でジョブスケジューラや監視を組み合わせて使用します。

- DuckDB スキーマ初期化

  from kabusys.data.schema import init_schema
  conn = init_schema("data/kabusys.duckdb")

- 日次 ETL（市場カレンダー・株価・財務データの差分取得）

  from kabusys.data.pipeline import run_daily_etl
  result = run_daily_etl(conn)  # target_date を指定可能
  print(result.to_dict())

- 特徴量作成（features テーブルへ保存）

  from kabusys.strategy import build_features
  from datetime import date
  count = build_features(conn, date(2025, 1, 31))
  print(f"features upserted: {count}")

- シグナル生成（signals テーブルへ保存）

  from kabusys.strategy import generate_signals
  from datetime import date
  n = generate_signals(conn, date(2025, 1, 31))
  print(f"signals generated: {n}")

- ニュース収集ジョブ（RSS フィード → raw_news / news_symbols）

  from kabusys.data.news_collector import run_news_collection
  known_codes = {"7203", "6758", "9432"}  # 有効銘柄コードセット
  results = run_news_collection(conn, known_codes=known_codes)
  print(results)

- J-Quants からデータ取得（直接呼び出し）

  from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
  records = fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,12,31))
  saved = save_daily_quotes(conn, records)

- カレンダー/営業日ユーティリティ

  from kabusys.data.calendar_management import is_trading_day, next_trading_day
  print(is_trading_day(conn, date(2025,1,1)))
  print(next_trading_day(conn, date(2025,1,1)))

注意点:
- 多くの関数は DuckDB の接続オブジェクト（duckdb.DuckDBPyConnection）を引数に取ります。
- ETL / save 系の関数は冪等（ON CONFLICT）を意識して実装されています。
- J-Quants API 呼び出しはレート制御とリトライを内蔵しています。

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py
- config.py
  - 環境変数の自動ロードと Settings クラス
- data/
  - __init__.py
  - jquants_client.py        — J-Quants API クライアント（fetch/save）
  - news_collector.py       — RSS 取得／前処理／DB 保存
  - schema.py               — DuckDB スキーマ定義・初期化（init_schema）
  - stats.py                — zscore_normalize 等の統計ユーティリティ
  - pipeline.py             — ETL (run_daily_etl、run_prices_etl 等)
  - calendar_management.py  — 市場カレンダー / 営業日ロジック
  - features.py             — data.stats の再エクスポート
  - audit.py                — 監査ログ用 DDL（signal_events / order_requests / executions）
- research/
  - __init__.py
  - factor_research.py      — momentum / volatility / value の計算
  - feature_exploration.py  — 将来リターン計算、IC、統計サマリー
- strategy/
  - __init__.py
  - feature_engineering.py  — 生ファクター→正規化→features へ保存
  - signal_generator.py     — features + ai_scores → signals 生成
- execution/                 — 発注関連（空の __init__.py を含む）
- monitoring/                — 監視・Slack 通知など（未記載の実装箇所）
- その他: logging の利用や、monitoring 用の外部連携を想定した設定

---

## 実運用上の注意 / ベストプラクティス

- シークレット（トークン・パスワード）は `.env` または環境変数で管理し、ソース管理には含めないでください。
- DuckDB のファイルは定期バックアップを行ってください。:memory: を使うと永続化されません。
- J-Quants のレート制限（120 req/min）を本ライブラリは想定しています。複数インスタンスで同一 API を叩く場合は注意してください。
- ETL は品質チェックで警告・エラーを収集しますが、デフォルトでは可能な限り処理を継続します。品質問題の取り扱い方針は運用ルールに合わせてください。
- 本ライブラリは「戦略層が生成したシグナルを DB に保存する」までを想定しており、実際の発注・ブローカー連携は別層（execution）で扱う設計です。

---

## ライセンス / 貢献

（この README にライセンス記載がない場合はプロジェクトの LICENSE ファイルを参照してください。）  

貢献する場合は Pull Request を送る前に issue を立て、変更内容の説明とテスト方法を明記してください。

---

README はここまでです。必要であれば「導入例のフルスクリプト」「CI 用の DB 初期化手順」「詳細な環境変数一覧（デフォルト値含む）」など追記できます。どの項目を深掘りしますか？