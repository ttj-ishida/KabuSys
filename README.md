# KabuSys

日本株の自動売買プラットフォーム向けのライブラリ群です。データ取得（J-Quants）、ETL、特徴量作成、シグナル生成、ニュース収集、監査ログなどを備え、研究（research）〜本番（execution）までのワークフローをサポートします。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株のクオンツ／自動売買システムの基盤ライブラリです。主な目的は以下です。

- J-Quants API からの市場データ・財務データ・カレンダー取得（レートリミット・リトライ・トークンリフレッシュ対応）
- DuckDB ベースのデータ層（Raw / Processed / Feature / Execution）スキーマ定義および初期化
- ETL（差分取得・バックフィル・品質チェック）パイプライン
- ファクター計算（モメンタム・ボラティリティ・バリュー等）とクロスセクション正規化（Z スコア）
- 戦略用特徴量の作成・シグナル生成（BUY/SELL ルール、Bear レジームフィルタ、エグジット判定）
- RSS によるニュース収集と記事→銘柄紐付け（SSRF 対策・トラッキングパラメータ除去）
- 監査ログ（signal→order→execution のトレーサビリティ）構造

設計上の方針として、ルックアヘッドバイアス防止（計算は target_date 時点の情報のみ使用）、DB への冪等保存、外部依存を最小化（標準ライブラリ中心）することを重視しています。

---

## 主な機能一覧

- 環境設定管理（.env 自動読み込み、必須キーチェック）
- J-Quants クライアント（レート制御、リトライ、トークン自動更新）
- DuckDB スキーマ初期化（多数のテーブルとインデックス）
- ETL パイプライン（市場カレンダー / 株価 / 財務 データの差分取得）
- ファクター計算（momentum / volatility / value 等）
- 特徴量構築（Z スコア正規化、ユニバースフィルタ、features テーブルへのUPSERT）
- シグナル生成（final_score 計算、BUY/SELL 判定、signals テーブルへの保存）
- ニュース収集（RSS 取得・正規化・raw_news 保存、銘柄抽出）
- カレンダー管理（営業日判定、next/prev_trading_day 等）
- 監査テーブル（signal_events / order_requests / executions など）

---

## 必要な環境変数

下記は本ライブラリで参照される主要な環境変数です。`.env` ファイルに定義しておくと自動で読み込まれます（プロジェクトルートに `.git` または `pyproject.toml` がある場合）。

必須:
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
- KABU_API_PASSWORD: kabuステーション API パスワード（execution 層で使用）
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID: Slack 送信先チャンネル ID

任意（デフォルトあり）:
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV: 実行環境 ("development" / "paper_trading" / "live")（デフォルト: development）
- LOG_LEVEL: ログレベル ("DEBUG"/"INFO"/...、デフォルト: INFO)

自動ロードの無効化:
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると、パッケージインポート時の .env 自動読み込みを無効化します（テスト時などに便利）。

.env のパースはシェル風の書式（export KEY=val / quoted values / inline comment handling）に対応しています。

---

## セットアップ手順

以下はローカルで開発・実行するための基本手順です。プロジェクトに依存関係定義（requirements.txt / pyproject.toml）がない場合は必要なパッケージを手動でインストールしてください。

推奨 Python バージョン: 3.10+

1. リポジトリをクローン
   - git clone <repo-url>

2. 仮想環境を作成・有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   - 必要な主なパッケージ:
     - duckdb
     - defusedxml
   - 例:
     - pip install duckdb defusedxml

   （プロジェクトに pyproject.toml / requirements.txt があればそれに従ってください）

4. 環境変数を設定
   - プロジェクトルートに `.env` を作成（.env.example があればそれを参照）
   - 必須キーを設定してください（上記参照）

5. DuckDB スキーマを初期化
   - 下記の「使い方」例を参照してスキーマを初期化します。

---

## 使い方（主要な API と簡単なサンプル）

以下は Python REPL またはスクリプトでの最小実行例です。必要に応じてロギングの設定等を行ってください。

1) DuckDB スキーマ初期化
```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")
# conn は duckdb.DuckDBPyConnection
```

2) 日次 ETL の実行（J-Quants トークンは環境変数から取得されます）
```python
from kabusys.data.pipeline import run_daily_etl
from kabusys.data.schema import init_schema
from datetime import date

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

3) 特徴量構築（features テーブルへの書き込み）
```python
from kabusys.strategy import build_features
from kabusys.data.schema import get_connection
from datetime import date

conn = get_connection("data/kabusys.duckdb")
n = build_features(conn, target_date=date(2025, 3, 1))
print(f"features upserted: {n}")
```

4) シグナル生成
```python
from kabusys.strategy import generate_signals
from kabusys.data.schema import get_connection
from datetime import date

conn = get_connection("data/kabusys.duckdb")
count = generate_signals(conn, target_date=date(2025, 3, 1))
print(f"signals written: {count}")
```

5) ニュース収集（RSS）と保存
```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
# known_codes は銘柄存在リスト（抽出のため）
known_codes = {"7203", "6758", ...}
results = run_news_collection(conn, sources=None, known_codes=known_codes)
print(results)
```

注意点:
- 各関数は DuckDB の接続オブジェクト（duckdb.DuckDBPyConnection）を受け取ります。init_schema は DB の初期化と接続を返します。get_connection は既存 DB への接続を返します（スキーマ初期化は行いません）。
- jquants_client のリクエストは内部でレート制御・リトライ・ID トークン自動更新を行います。401 時はトークンを再取得して 1 回リトライします。

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py
- config.py
  - 環境変数読み込み・Settings クラス
- data/
  - __init__.py
  - jquants_client.py         — J-Quants API クライアント（取得・保存ユーティリティ）
  - news_collector.py         — RSS 収集・正規化・DB 保存
  - schema.py                 — DuckDB スキーマ定義・初期化
  - pipeline.py               — ETL パイプライン（run_daily_etl 等）
  - stats.py                  — zscore_normalize 等の統計ユーティリティ
  - features.py               — data.stats の再エクスポート
  - calendar_management.py    — market_calendar 管理（営業日判定等）
  - audit.py                  — 監査ログ用 DDL（signal/events/order/exec）
  - （その他: quality モジュール等を想定）
- research/
  - __init__.py
  - factor_research.py        — momentum/volatility/value の計算
  - feature_exploration.py    — 将来リターン・IC・統計サマリー
- strategy/
  - __init__.py
  - feature_engineering.py    — features 構築（ユニバースフィルタ・Z スコア）
  - signal_generator.py       — final_score 計算、BUY/SELL 判定、signals 保存
- execution/
  - __init__.py               — 発注/実行層（実装は別途）
- monitoring/                 — 監視・アラート系（別モジュール想定）

DB スキーマ（主なテーブル、schema.py に定義）
- Raw 層: raw_prices, raw_financials, raw_news, raw_executions
- Processed 層: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
- Feature 層: features, ai_scores
- Execution 層: signals, signal_queue, orders, trades, positions, portfolio_targets, portfolio_performance
- Audit 層: signal_events, order_requests, executions など

---

## 開発・運用上の注意事項

- Python バージョン: Union 型表記（|）や組み込みの型注釈が多用されているため Python 3.10+ を推奨します。
- DuckDB を利用しているため、データサイズやメモリを考慮して DB の配置・バックアップを行ってください。
- jquants_client は API レート（120 req/min）に従って固定間隔スロットリングを行います。大量の銘柄取得では時間がかかります。
- ニュース収集では SSRF 対策・レスポンスサイズ制限・XML 脆弱性対策（defusedxml）を実装していますが、外部 RSS の取り扱いには注意してください。
- 環境変数の読み込みは自動実行されますが、テストなどで無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を使ってください。
- シグナル生成・発注ロジックは本番環境での自動売買に影響します。paper_trading 等で十分に検証してください（KABUSYS_ENV を利用）。

---

## トラブルシューティング

- 環境変数が見つからない / settings で ValueError が出る場合:
  - `.env` がプロジェクトルートにあり自動ロードが有効な場合はロードされます。テスト環境では KABUSYS_DISABLE_AUTO_ENV_LOAD を確認してください。
  - 必須変数（JQUANTS_REFRESH_TOKEN 等）が未設定だと Settings で例外が発生します。

- DuckDB の接続/DDL エラー:
  - init_schema は parent ディレクトリを自動作成しますが、ファイル権限やディスク容量を確認してください。

- J-Quants API の 401 エラーが頻発する場合:
  - リフレッシュトークンが無効または期限切れの可能性があります。get_id_token が失敗するとエラーになります。

---

この README はコードベースの主要機能・使い方の概観をまとめたものです。詳細な仕様（StrategyModel.md / DataPlatform.md / Research 文書等）が別ファイルにある想定です。必要に応じて README を補強してサンプルスクリプトや CI / デプロイ手順、requirements を追加してください。