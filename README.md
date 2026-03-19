KabuSys — 日本株自動売買プラットフォーム（README 日本語版）
================================================================================

概要
----
KabuSys は日本株向けの自動売買プラットフォームのコアライブラリ群です。本リポジトリは以下を目的としたモジュール群を含みます。

- J-Quants API から市場データ・財務データ・カレンダーを取得する ETL（差分取得・冪等保存・品質チェック）
- DuckDB によるデータスキーマ／保存・検索
- 研究（research）で算出した生ファクターを正規化して features を作成する特徴量パイプライン
- 正規化済みファクター + AI スコアを統合して売買シグナルを生成するロジック
- RSS からニュースを収集して raw_news に保存、記事と銘柄の紐付け
- マーケットカレンダー管理、監査ログ（発注〜約定トレーサビリティ）などのユーティリティ

主なモジュール（パッケージ構成）は kabusys.data, kabusys.research, kabusys.strategy, kabusys.execution, kabusys.monitoring です。

主な機能
--------
- データ取得（J-Quants）: 株価日足、財務諸表、JPX カレンダー（ページネーション／レート制限／トークン自動リフレッシュ対応）
- ETL パイプライン: 差分更新、バックフィル、品質チェック、冪等保存（ON CONFLICT）
- DuckDB スキーマ: Raw / Processed / Feature / Execution 層を定義する DDL を提供
- 特徴量エンジニアリング: momentum / volatility / value 等のファクター計算と Z スコア正規化（±3 クリップ）
- シグナル生成: ファクター + AI スコアを重み付けして final_score を計算、BUY/SELL シグナルの生成
- ニュース収集: RSS から記事を取得・正規化・保存、記事ID は正規化 URL の SHA-256（先頭 32 文字）
- カレンダー管理: 営業日判定 / next/prev_trading_day / calendar 更新ジョブ
- 監査ログ（audit）: signal → order_request → execution のトレース用テーブル

前提条件
--------
- Python 3.10 以上（PEP 604 の union 型記法 `X | Y` や型ヒントを用いているため）
- 必要なパッケージ（少なくとも）:
  - duckdb
  - defusedxml
- ネットワーク接続（J-Quants API、RSS フィード等）
- 実運用では J-Quants のリフレッシュトークン、Slack トークン、kabu API の認証情報 などが必要

インストール（開発環境）
-----------------------
1. 仮想環境を作成・有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存インストール（最低限）
   - pip install duckdb defusedxml

   開発用にパッケージとして編集インストールする場合（プロジェクトルートで）:
   - pip install -e .

環境変数 / .env
----------------
config.py により .env / .env.local が自動でロードされます（優先順位: OS 環境変数 > .env.local > .env）。自動ロードを無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

主な必須環境変数（settings で参照されるもの）
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD — kabu ステーション API パスワード（発注連携時）
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID — Slack チャンネル ID（必須）

任意 / デフォルトあり
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト http://localhost:18080/kabusapi）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト data/monitoring.db）
- KABUSYS_ENV — execution モード: development / paper_trading / live（デフォルト development）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト INFO）

例 (.env)
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=DEBUG
```

セットアップ手順（DB 初期化）
----------------------------
1. DuckDB スキーマを初期化
   Python REPL またはスクリプトで以下を実行します:

   ```python
   from kabusys.data.schema import init_schema
   init_schema("data/kabusys.duckdb")  # または settings.duckdb_path を参照
   ```

   この処理は必要なテーブルとインデックスをすべて作成します（冪等）。

基本的な使い方（サンプル）
-------------------------

1) 日次 ETL（株価 / 財務 / カレンダー取得 + 品質チェック）
```python
from datetime import date
from kabusys.data.schema import init_schema, get_connection
from kabusys.data.pipeline import run_daily_etl

# DB 初期化（初回のみ）
conn = init_schema("data/kabusys.duckdb")

# 日次 ETL を実行（今日分）
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

2) 特徴量ビルド（feature_engineering.build_features）
```python
from datetime import date
import duckdb
from kabusys.strategy import build_features
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
count = build_features(conn, target_date=date(2024, 1, 31))
print(f"features upserted: {count}")
```

3) シグナル生成（strategy.signal_generator.generate_signals）
```python
from datetime import date
from kabusys.strategy import generate_signals
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
signals_count = generate_signals(conn, target_date=date(2024, 1, 31))
print(f"signals generated: {signals_count}")
```

4) ニュース収集ジョブ（RSS 取得 → raw_news 保存 → 銘柄紐付け）
```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
# known_codes は銘柄コードのセット（抽出時に利用）
known_codes = {"7203", "6758", "9984"}
results = run_news_collection(conn, sources=None, known_codes=known_codes)
print(results)  # {source_name: new_saved_count}
```

5) カレンダー夜間更新ジョブ
```python
from kabusys.data.calendar_management import calendar_update_job
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
saved = calendar_update_job(conn)
print(f"calendar saved: {saved}")
```

運用上の注意
------------
- J-Quants API のレート制限（120 req/min）に合わせた RateLimiter と再試行ロジックが実装されていますが、運用中は API 利用規約を守ってください。
- ETL は差分取得とバックフィル（デフォルト 3 日）を行います。API の後出し訂正を取り込むためです。
- features / signals などは日付単位で "DELETE してから INSERT" の置換を行うため冪等です。
- news_collector は SSRF / XML Bomb / 大容量レスポンス対策などの安全対策を実装していますが、外部 RSS を扱う際は注意してください。
- KABUSYS_ENV を "live" に設定して実際の発注に接続する場合は、kabu API の設定・安全確認・エラーハンドリングを十分に検証してください（実戦稼働は自己責任）。

構成（ディレクトリ構成）
-----------------------
主要なファイル・フォルダ（src/kabusys 以下）:

- kabusys/
  - __init__.py
  - config.py                # 環境変数・設定管理
  - data/
    - __init__.py
    - jquants_client.py      # J-Quants API クライアント + 保存ロジック
    - news_collector.py      # RSS ニュース収集
    - schema.py              # DuckDB スキーマ定義 & init_schema
    - stats.py               # 統計ユーティリティ（z-score 等）
    - pipeline.py            # ETL パイプライン（run_daily_etl 等）
    - features.py            # 公開インターフェース（zscore_normalize 等）
    - calendar_management.py # マーケットカレンダー管理
    - audit.py               # 監査ログ DDL
    - (その他: quality など想定)
  - research/
    - __init__.py
    - factor_research.py     # momentum / volatility / value 計算
    - feature_exploration.py # forward returns / IC / summary
  - strategy/
    - __init__.py
    - feature_engineering.py # features を作成（build_features）
    - signal_generator.py    # signals 生成（generate_signals）
  - execution/
    - __init__.py
  - monitoring/
    - (監視・Slack 通知等の実装想定)

（ソースの大半は src/kabusys 以下に実装されています。README に記載した関数は各モジュールで公開されています。）

依存関係（抜粋）
----------------
- duckdb — データベース（必須）
- defusedxml — XML パースの安全対策（news_collector）
- 標準ライブラリの urllib / logging / datetime / math 等

推奨ワークフロー（開発）
-----------------------
1. 仮想環境作成・依存インストール
2. .env で必要なトークンを設定（JQUANTS_REFRESH_TOKEN 等）
3. init_schema() で DB を作成
4. run_daily_etl() でデータを取得
5. build_features(), generate_signals() を順に実行してシグナルを取得
6. execution 層（未実装部分を自分で接続）を用いて発注を行う

サポート / 拡張ポイント
-----------------------
- execution 層は発注実装（kabu API 連携）に接続するためのフックとして設計されています。実運用に繋ぐ際はここを実装してください。
- quality モジュール（ETL 品質チェック）は pipeline.run_daily_etl から呼ばれます。検査ルールの追加や閾値調整が可能です。
- AI スコアやニュースを加味したスコア調整・リスク管理ロジックは strategy 層で拡張可能です。

最後に
------
この README はコードベース（src/kabusys 以下）から主要な使い方と構成をまとめたものです。実行前に .env を正しく整備し、テスト環境（paper_trading）で十分に検証してから live 環境に移行してください。質問や補足が必要であれば教えてください。