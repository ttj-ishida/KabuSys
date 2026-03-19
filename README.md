# KabuSys

日本株向け自動売買プラットフォーム用ライブラリ（部分実装）

このリポジトリは、データ収集（J-Quants）、ETL、特徴量生成、シグナル生成、ニュース収集、マーケットカレンダー管理、監査ログ等の機能を提供するモジュール群を含むPythonパッケージです。DuckDBを用いたローカルデータベースと連携して、研究→本番までのワークフローを想定した設計になっています。

バージョン: 0.1.0

---

## 主要な概要

- データ取得: J-Quants API から株価・財務・マーケットカレンダーを取得（rate limit / リトライ / トークン自動更新）
- ETL: 差分取得・保存・品質チェックのパイプライン（DuckDB に保存）
- 特徴量計算: momentum / volatility / value 等のファクター計算と Z スコア正規化
- シグナル生成: 特徴量と AI スコアを統合して BUY/SELL シグナルを作成、signals テーブルへ冪等保存
- ニュース収集: RSS フィード取得、記事正規化、銘柄コード抽出、DB への冪等保存
- マーケットカレンダー管理: 営業日判定・前後営業日取得・定期更新ジョブ
- スキーマ管理: DuckDB のスキーマ初期化ユーティリティ
- 監査ログ: シグナル→発注→約定のトレーサビリティ用テーブル定義（監査用）

---

## 機能一覧（モジュール別）

- kabusys.config
  - .env / 環境変数の自動ロード（プロジェクトルート検出）
  - 必須設定取得ユーティリティ（Settings）
- kabusys.data.jquants_client
  - J-Quants API 呼び出し（fetch/save系、トークン管理、レートリミット、リトライ）
- kabusys.data.schema
  - DuckDB スキーマ定義と init_schema()/get_connection()
- kabusys.data.pipeline
  - run_daily_etl()/run_prices_etl()/run_financials_etl()/run_calendar_etl()
- kabusys.data.news_collector
  - RSS 取得、記事正規化、raw_news / news_symbols への保存
- kabusys.data.calendar_management
  - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, calendar_update_job
- kabusys.data.stats / features
  - zscore_normalize（クロスセクション正規化）
- kabusys.research.*
  - calc_momentum / calc_volatility / calc_value（ファクター計算）
  - calc_forward_returns / calc_ic / factor_summary（特徴量探索用ユーティリティ）
- kabusys.strategy.*
  - build_features（特徴量合成→features テーブルへの保存）
  - generate_signals（features と ai_scores を組み合わせ signals を生成）
- kabusys.data.audit
  - 監査ログ (signal_events, order_requests, executions) のDDL定義と初期化（トレーサビリティ）
- その他
  - 実行層（execution）用の骨組み（発注処理等を実装する想定）

---

## 必要条件 / 依存

- Python 3.9+（ソースは typing の新構文・from __future__ annotations を使用）
- 主要ライブラリ（例）:
  - duckdb
  - defusedxml
- 標準ライブラリで多くを実装しているため外部依存は限定的ですが、実行に必要なライブラリは環境に応じて追加してください。

インストール例:
```bash
python -m pip install duckdb defusedxml
# パッケージをeditableでインストールする場合（プロジェクトルートに pyproject.toml / setup がある場合）
# python -m pip install -e .
```

（requirements.txt / pyproject.toml がある場合はそちらを参照してください。）

---

## 環境変数・設定

config.Settings がアプリケーション設定をラップしています。自動で .env / .env.local をプロジェクトルートから読み込みます（優先順: OS 環境 > .env.local > .env）。プロジェクトルートは `.git` または `pyproject.toml` を起点に探索します。自動読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

主な環境変数:
- JQUANTS_REFRESH_TOKEN (必須) — J-Quants リフレッシュトークン
- KABU_API_PASSWORD (必須) — kabu ステーション API のパスワード
- KABU_API_BASE_URL (任意) — kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID (必須) — Slack チャンネル ID
- DUCKDB_PATH (任意) — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH (任意) — 監視用 SQLite（デフォルト: data/monitoring.db）
- KABUSYS_ENV (任意) — one of: development, paper_trading, live（デフォルト: development）
- LOG_LEVEL (任意) — DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）

設定が不足している場合、settings の該当プロパティ呼び出しで ValueError が発生します。

---

## セットアップ手順（ローカル）

1. リポジトリをクローン
   ```bash
   git clone <this-repo-url>
   cd <repo-root>
   ```

2. Python 仮想環境を作成して有効化（推奨）
   ```bash
   python -m venv .venv
   source .venv/bin/activate   # macOS/Linux
   .venv\Scripts\activate      # Windows
   ```

3. 必要パッケージをインストール
   ```bash
   python -m pip install --upgrade pip
   python -m pip install duckdb defusedxml
   ```

4. 環境変数を準備（.env または OS 環境）
   - 例 `.env`（プロジェクトルート）:
     ```
     JQUANTS_REFRESH_TOKEN=xxxx
     KABU_API_PASSWORD=yyyy
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     ```
   - 必須変数は必ず設定してください。settings を呼び出すと未設定項目で例外が投げられます。

5. DuckDB スキーマ初期化
   ```python
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")
   ```
   またはコマンドラインスクリプトを用意して初期化してください。

---

## 使い方（代表的な例）

以下はライブラリの代表的な利用例です。実際にはエントリポイントスクリプトやジョブ管理（cron / Airflow / systemd timer 等）から呼び出して運用します。

1) スキーマ初期化
```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")
```

2) 日次 ETL 実行（市場カレンダー・株価・財務の差分取得）
```python
from kabusys.data.pipeline import run_daily_etl
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn)  # target_date を指定可能
print(result.to_dict())
```

3) 特徴量の構築（features テーブルへ保存）
```python
from datetime import date
import duckdb
from kabusys.strategy import build_features

conn = duckdb.connect("data/kabusys.duckdb")
count = build_features(conn, date(2025, 3, 1))
print(f"features upserted: {count}")
```

4) シグナル生成（signals テーブルへ保存）
```python
from datetime import date
import duckdb
from kabusys.strategy import generate_signals

conn = duckdb.connect("data/kabusys.duckdb")
total = generate_signals(conn, date(2025, 3, 1), threshold=0.6)
print(f"signals written: {total}")
```

5) RSS ニュース収集ジョブ（news -> raw_news, news_symbols）
```python
from kabusys.data.news_collector import run_news_collection
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
known_codes = {"7203", "6758", "9432"}  # 有効銘柄コードセット
results = run_news_collection(conn, known_codes=known_codes)
print(results)
```

6) カレンダー関連ユーティリティ
```python
from kabusys.data.calendar_management import is_trading_day, next_trading_day
import duckdb
from datetime import date

conn = duckdb.connect("data/kabusys.duckdb")
d = date(2025, 3, 21)
print(is_trading_day(conn, d))
print(next_trading_day(conn, d))
```

---

## API / モジュールの注意事項・設計方針

- 冪等性を重視:
  - DuckDB への INSERT は ON CONFLICT や INSERT ... RETURNING を使って重複を防止する実装が多くあります。
- ルックアヘッドバイアス対策:
  - 特徴量・シグナル生成では target_date 時点のデータのみを使用するよう設計されています。
- レート制御・リトライ:
  - J-Quants クライアントは固定間隔スロットリングおよび指数バックオフのリトライを実装しています。401 はトークンリフレッシュをトリガーします。
- セキュリティ:
  - RSS 収集では SSRF 対策、gzip サイズ制限、defusedxml を使った XML パースを行っています。
- ロギング/運用:
  - 各処理は logger を利用し、重大な操作は情報ログ・警告ログを出します。運用側で LOG_LEVEL を設定してください。

---

## ディレクトリ構成

（主要ファイルのみ抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py
    - data/
      - __init__.py
      - jquants_client.py
      - news_collector.py
      - schema.py
      - pipeline.py
      - features.py
      - stats.py
      - calendar_management.py
      - audit.py
      - pipeline.py
      - (その他: quality モジュールなど実装想定)
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
    - strategy/
      - __init__.py
      - feature_engineering.py
      - signal_generator.py
    - execution/
      - __init__.py
    - monitoring/  (パッケージ列挙にあるが個別ファイルはここでは省略)

READMEに掲載している以外にもユーティリティ・補助モジュールが含まれます。実行前に `src/` を PYTHONPATH に含めるか、パッケージとしてインストールしてください。

---

## 運用上のヒント

- テスト環境では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定し、明示的な環境変数注入や .env の差し替えでテストを制御してください。
- DuckDB はファイルベースかメモリ（":memory:"）で利用可能。バックテスト・ユニットテストでは ":memory:" を使って軽量に検証できます。
- daily ETL は市場カレンダー取得→株価差分→財務差分→品質チェックの順で実行されます（run_daily_etl）。品質チェック結果は ETLResult に保持されます。
- シグナル生成時、AI スコア（ai_scores テーブル）や positions テーブルの状態に応じて BUY/SELL が出力されます。運用時は execution 層でのリスク制御・発注ロジックを実装してください。

---

## ライセンス・貢献

本ドキュメントはコードベースに基づいたサマリーです。リポジトリの LICENSE ファイルを参照してください。バグ報告・機能提案は Issue にお願いします。

---

必要であれば、README にサンプルスクリプト（CLI 呼び出し例）、詳細な環境変数一覧、運用フローチャート、テストの実行方法などを追加します。どの情報を優先して追加しますか？