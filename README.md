# KabuSys

KabuSys は日本株の自動売買プラットフォームのコアライブラリです。  
データ収集（J-Quants）、ETL、特徴量生成、シグナル生成、ニュース収集、マーケットカレンダー管理、監査・実行レイヤのスキーマなどを含むモジュール群を提供します。

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方（サンプル）
- 環境変数一覧（.env 例）
- ディレクトリ構成
- 注意事項 / 設計上のポイント

---

## プロジェクト概要

KabuSys は DuckDB をデータストアとして用い、J-Quants API から市場データ・財務データ・マーケットカレンダーを取得して整形・保存し、研究（research）で作成した生ファクターを正規化・合成して戦略用の特徴量（features）を生成、最終的に売買シグナルを作成する一連の流れをサポートするライブラリです。  
監査ログ／発注要求／約定記録のスキーマも用意され、実運用（paper_trading / live）を想定した設計になっています。

主な設計方針:
- ルックアヘッドバイアス防止（target_date 時点のデータのみ使用）
- 冪等性（DB への保存は ON CONFLICT / トランザクションで原子性確保）
- 外部ライブラリは最小限（duckdb, defusedxml 等を使用）
- API レート・リトライ・トークンリフレッシュの実装

---

## 機能一覧

- データ取得（J-Quants クライアント）
  - 日足（OHLCV）/ 財務データ / マーケットカレンダーのページネーション対応取得
  - レート制限・リトライ・401 リフレッシュ対応
- DuckDB スキーマ定義と初期化（init_schema）
- ETL パイプライン（差分取得、backfill、品質チェック）
- 特徴量計算（research/factor_research: momentum/volatility/value 等）
- 特徴量正規化（Z スコア / stats.zscore_normalize）
- feature テーブル生成（strategy/feature_engineering.build_features）
- シグナル生成（strategy/signal_generator.generate_signals）
  - コンポーネントスコア統合、Bear レジーム抑制、売買・エグジット判定
- ニュース収集（RSS → raw_news、記事ID正規化、SSRF対策、truncated read 対策）
- マーケットカレンダー管理（営業日判定、next/prev/get_trading_days、calendar_update_job）
- 監査ログ用スキーマ（signal_events, order_requests, executions など）
- 実行レイヤ用スキーマ（signal_queue, orders, trades, positions, portfolio_performance）

---

## セットアップ手順

前提
- Python 3.10 以上（型ヒントに | を使用しているため）
- ネットワーク接続（J-Quants API へアクセスする場合）

推奨手順（ローカル開発環境）
1. 仮想環境作成
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 必要パッケージをインストール
   - pip install duckdb defusedxml
   - （必要に応じて）pip install -e . などでパッケージとしてインストール

   ※ 本リポジトリに requirements.txt がない場合は上の最低限のパッケージを入れてください。
   - duckdb: データベース接続
   - defusedxml: RSS パースのセキュリティ対策

3. 環境変数を設定
   - 重要なシークレット（J-Quants トークン等）を環境変数またはプロジェクトルートの `.env` / `.env.local` に設定します。
   - 自動.envロードはデフォルトで有効。テストで無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` をエクスポートします。

4. DuckDB スキーマ初期化
   - Python REPL やスクリプトで init_schema を呼んで DB ファイルを初期化します（例: data/kabusys.duckdb）。

   例:
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")

---

## 使い方（サンプル）

以下は代表的な操作のサンプルです。target_date は datetime.date オブジェクトを使います。

1) DuckDB 初期化
```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")  # data/ フォルダを自動作成して DB を初期化
```

2) 日次 ETL の実行（J-Quants からデータを差分取得して保存）
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

3) 特徴量のビルド（features テーブルへの upsert）
```python
from datetime import date
from kabusys.strategy import build_features

n = build_features(conn, target_date=date(2025, 1, 15))
print(f"features upserted: {n}")
```

4) シグナル生成（signals テーブルへの upsert）
```python
from datetime import date
from kabusys.strategy import generate_signals

total = generate_signals(conn, target_date=date(2025, 1, 15), threshold=0.6)
print(f"signals written: {total}")
```

5) ニュース収集（RSS 取得 → raw_news 保存 → 銘柄紐付け）
```python
from kabusys.data.news_collector import run_news_collection

# known_codes は有効な銘柄コード集合（extract_stock_codes に渡す）
known_codes = {"7203", "6758", "9984", ...}
results = run_news_collection(conn, known_codes=known_codes)
print(results)  # {source_name: saved_count, ...}
```

6) カレンダー更新ジョブ
```python
from kabusys.data.calendar_management import calendar_update_job

saved = calendar_update_job(conn)
print(f"calendar saved: {saved}")
```

注意:
- 各公開関数は DuckDB 接続と target_date（date）を受け取り、target_date ごとの冪等置換を行います（既存日付を削除して再挿入）。
- jquants_client の fetch/save 系は idempotent（ON CONFLICT で更新）です。

---

## 環境変数（主要）

config.Settings クラスで参照される主要な環境変数（必須・デフォルト値含む）:

必須:
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API のパスワード（必須）
- SLACK_BOT_TOKEN: Slack 通知用ボットトークン（必須）
- SLACK_CHANNEL_ID: 通知先 Slack チャンネル ID（必須）

任意 / デフォルトあり:
- KABUSYS_ENV: 実行環境 ("development" | "paper_trading" | "live")、デフォルト "development"
- LOG_LEVEL: ログレベル（"DEBUG"|"INFO"|"WARNING"|"ERROR"|"CRITICAL"）、デフォルト "INFO"
- KABUSYS_DISABLE_AUTO_ENV_LOAD: "1" を設定するとプロジェクトルートの .env 自動読み込みを無効化
- KABU_API_BASE_URL: kabu API のベース URL、デフォルト "http://localhost:18080/kabusapi"
- DUCKDB_PATH: DuckDB ファイルパス、デフォルト "data/kabusys.duckdb"
- SQLITE_PATH: 監視用 SQLite パス、デフォルト "data/monitoring.db"

例: .env のサンプル（実運用では値を適切に秘匿してください）
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C1234567890
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
```

---

## ディレクトリ構成

主要ファイル・パッケージ（src/kabusys 以下）:

- kabusys/
  - __init__.py
  - config.py                  — 環境変数/設定管理（.env 自動読み込み、Settings クラス）
  - data/
    - __init__.py
    - jquants_client.py         — J-Quants API クライアント（取得・保存・リトライ・レート制限）
    - news_collector.py        — RSS ニュース収集・前処理・保存・銘柄抽出
    - schema.py                — DuckDB スキーマ定義・init_schema/get_connection
    - stats.py                 — zscore_normalize 等の統計ユーティリティ
    - pipeline.py              — ETL パイプライン（run_daily_etl, run_prices_etl, ...）
    - features.py              — data 側の features 再エクスポート
    - calendar_management.py   — マーケットカレンダー管理（営業日判定、update job）
    - audit.py                 — 監査ログ用 DDL（signal_events, order_requests, executions）
    - (その他: quality モジュールを想定)
  - research/
    - __init__.py
    - factor_research.py       — ファクター計算（momentum / volatility / value）
    - feature_exploration.py   — 将来リターン, IC, 統計サマリー
  - strategy/
    - __init__.py
    - feature_engineering.py   — features テーブル構築（正規化・ユニバースフィルタ）
    - signal_generator.py      — final_score 計算・BUY/SELL 判定・signals 書き込み
  - execution/                 — 発注/実行に関するパッケージ（骨組み）
  - monitoring/               — 監視系（SQLite 等）を想定するパッケージ

注: 上記はコードベースの主要モジュールのみ抜粋しています。実行レイヤーや監視周りは発展的実装が想定されています。

---

## 注意事項 / 設計上のポイント

- Python バージョン: 3.10 以上を想定しています（型ヒントに | を使用）。
- セキュリティ:
  - news_collector は SSRF 対策、gzip BOM 対策、XML パースの安全ライブラリを使用しています（defusedxml）。
  - トークン等は .env / 環境変数経由で管理し、リポジトリにハードコードしないでください。
- データ整合性:
  - DuckDB のテーブル作成は冪等。init_schema は既存テーブルを上書きせずに作成します。
  - save_* 系関数は ON CONFLICT を用いて更新（冪等）します。
- 実運用の留意点:
  - run_daily_etl は品質チェック（quality モジュール）を呼び出します。品質エラーがあっても ETL は可能な限り継続しますが、運用ルールに応じてアラートや停止を実装してください。
  - signal_generator は Bear レジームの判定やストップロス判定が実装されていますが、実際の発注は execution 層（ブローカー API 結合）で厳密に行ってください。

---

開発・拡張メモ
- 研究環境（research）で新しいファクターを作成し、strategy.feature_engineering.build_features に組み込むことで戦略を更新できます。
- 実取引に移行する前に paper_trading 環境で十分に検証してください（KABUSYS_ENV=paper_trading）。
- テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して .env 自動読み込みを避けると制御しやすくなります。

---

以上が README の概要です。必要であれば、README に以下を追加できます:
- API リファレンス（関数・引数一覧）
- 実運用のデプロイ手順（systemd / cron / コンテナ化）
- サンプル .env.example ファイル（より詳細なコメント付き）
- quality モジュールや execution 層の使い方・設計ドキュメント

どの情報を追記しますか？