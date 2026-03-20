# KabuSys

日本株向けの自動売買／データプラットフォーム用ライブラリです。  
データ取得（J-Quants）、ETL、特徴量生成、シグナル生成、ニュース収集、DuckDB ベースのスキーマや監査ログなどを一貫して提供します。

---

## プロジェクト概要

KabuSys は以下の責務を持つモジュール群から構成されるライブラリです。

- データ取得・保存（J-Quants API クライアント、ニュース収集）
- DuckDB を用いたデータスキーマ定義と永続化（Raw / Processed / Feature / Execution 層）
- ETL（差分取得・バックフィル・品質チェック）
- 研究用ファクター計算（momentum / volatility / value）と特徴量エンジニアリング
- シグナル生成（最終スコアの計算、BUY / SELL シグナル生成）
- カレンダー管理（営業日判定・更新ジョブ）
- 監査ログ・トレーサビリティ（オーダー/約定の監査）

設計上のポイント：
- 可能な限り冪等（idempotent）に動作するよう ON CONFLICT 等で保存を行います。
- ルックアヘッドバイアスを避け、target_date 時点のデータのみを用いる設計です。
- 外部ライブラリへの依存を最小限にし、主要処理は標準ライブラリと DuckDB で実装しています。

---

## 主な機能一覧

- data/jquants_client
  - J-Quants API クライアント（レートリミット、リトライ、トークン自動更新、ページネーション対応）
  - 日次株価・財務・マーケットカレンダーの取得と DuckDB への保存（冪等）
- data/schema
  - DuckDB 上のスキーマ定義と初期化（raw_prices, prices_daily, features, signals, orders, executions 等）
- data/pipeline
  - 日次差分 ETL（カレンダー、株価、財務）と品質チェックの統合ジョブ
- data/news_collector
  - RSS フィードからのニュース収集、正規化、raw_news 保存、銘柄コード抽出
- research
  - ファクター計算（momentum / volatility / value）
  - 将来リターン計算、IC（Information Coefficient）や統計サマリー
- strategy
  - feature_engineering.build_features(conn, target_date)：ファクターの統合・正規化・features テーブルへの保存
  - signal_generator.generate_signals(conn, target_date, ...)：final_score 計算と signals テーブルへの出力
- data/calendar_management
  - market_calendar の更新、営業日判定・前後営業日取得ユーティリティ
- audit
  - シグナル→オーダー→約定のトレーサビリティ用テーブル定義

---

## 要件（推奨）

- Python 3.10+
  - 型注釈で `|` を使用しているため Python 3.10 以上を推奨します。
- 必須パッケージ（例）
  - duckdb
  - defusedxml
- ネットワークアクセス（J-Quants API、RSS フィードなど）

インストール例（仮想環境推奨）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install "duckdb" "defusedxml"
# パッケージ開発中であればプロジェクトルートで:
pip install -e .
```

---

## 環境変数 / 設定 (.env)

kabusys/config.py が環境変数を読み込みます。プロジェクトルートの `.env` / `.env.local` が自動で読み込まれます（CWD に依存せず、.git または pyproject.toml を基準に探索）。

主要な環境変数（必須のもの）
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API のパスワード（必須）
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID: Slack 通知先チャンネル ID（必須）

任意・デフォルト
- KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL: ログレベル（DEBUG/INFO/…、デフォルト INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動 .env ロードを無効化できます。

DB パス（デフォルト）
- DUCKDB_PATH: data/kabusys.duckdb
- SQLITE_PATH: data/monitoring.db

例 `.env`:
```
JQUANTS_REFRESH_TOKEN=your_refresh_token_here
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C12345678
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=DEBUG
```

---

## セットアップ手順

1. リポジトリをクローンして仮想環境を作成
   ```bash
   git clone <repo-url>
   cd <repo>
   python -m venv .venv
   source .venv/bin/activate
   pip install -U pip
   ```

2. 依存パッケージをインストール
   ```bash
   pip install duckdb defusedxml
   # もしパッケージを編集して使うなら:
   pip install -e .
   ```

3. 環境変数を設定（`.env` を作成）
   - 上の「環境変数 / 設定」例を参考に `.env` を作成してください。

4. DuckDB スキーマ初期化
   - Python から実行例:
     ```python
     from kabusys.config import settings
     from kabusys.data.schema import init_schema

     conn = init_schema(settings.duckdb_path)
     conn.close()
     ```
   - これにより必要なテーブル・インデックスが作成されます。

---

## 使い方（主要なワークフロー例）

以下は典型的な日次バッチの実行順序例です。

1. DuckDB スキーマ初期化（初回のみ）
   ```python
   from kabusys.config import settings
   from kabusys.data.schema import init_schema

   conn = init_schema(settings.duckdb_path)
   ```

2. 日次 ETL を実行（カレンダー・株価・財務の差分取得と保存）
   ```python
   from kabusys.data.pipeline import run_daily_etl

   result = run_daily_etl(conn)  # target_date を省略すると今日が使われる
   print(result.to_dict())
   ```

3. 特徴量の構築（研究モジュールで計算した raw factor を統合し features テーブルへ保存）
   ```python
   from datetime import date
   from kabusys.strategy import build_features

   cnt = build_features(conn, target_date=date(2024, 1, 31))
   print(f"features upserted: {cnt}")
   ```

4. シグナル生成（features / ai_scores / positions を参照して signals を作成）
   ```python
   from kabusys.strategy import generate_signals

   total = generate_signals(conn, target_date=date(2024, 1, 31))
   print(f"signals generated: {total}")
   ```

5. ニュース収集（RSS）と銘柄紐付け
   ```python
   from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
   known_codes = {"7203", "6758", "9984"}  # 事前に有効銘柄リストを用意
   res = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
   print(res)
   ```

6. カレンダー更新ジョブ（夜間バッチ）
   ```python
   from kabusys.data.calendar_management import calendar_update_job

   saved = calendar_update_job(conn)
   print(f"calendar records saved: {saved}")
   ```

ログは標準的な logging を使用しています。実運用ではログレベルや出力先を設定してください。

---

## ディレクトリ構成（主要ファイル）

プロジェクトは src/kabusys 以下にモジュールを配置しています。主なファイル・モジュール:

- src/kabusys/
  - __init__.py
  - config.py                  — 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py        — J-Quants API クライアント・保存ロジック
    - news_collector.py        — RSS ニュース収集・保存・銘柄抽出
    - schema.py                — DuckDB スキーマ定義 / 初期化
    - stats.py                 — 汎用統計ユーティリティ（zscore_normalize）
    - pipeline.py              — ETL パイプライン（run_daily_etl 等）
    - features.py              — data 層の公開インターフェース（zscore 再エクスポート）
    - calendar_management.py   — market_calendar の更新・営業日ユーティリティ
    - audit.py                 — 監査ログ用スキーマ
    - execution/               — 発注 / 実行関連（空パッケージ階層）
  - research/
    - __init__.py
    - factor_research.py       — モメンタム / ボラティリティ / バリュー計算
    - feature_exploration.py   — 将来リターン / IC / 統計サマリー
  - strategy/
    - __init__.py
    - feature_engineering.py   — ファクター統合・正規化・features 保存
    - signal_generator.py      — final_score 計算と signals 保存
  - monitoring/                — 監視関連（DB/モニタリング用、実装箇所に応じて）
  - execution/                 — 実際の発注実装（外部 API への接続はこの層に集約）

（実際のツリーはリポジトリのファイル一覧に合わせてください。上は抜粋です。）

---

## 動作上の注意 / 実運用メモ

- 環境変数は必須項目があり、未設定だと Settings プロパティが ValueError を送出します。
- J-Quants API のレート制限（120 req/min）を守る実装が入っていますが、運用キャパシティに注意してください。
- DuckDB ファイルはデフォルトで data/kabusys.duckdb に保存されます。バックアップやファイルパスの管理を行ってください。
- ETL の差分ロジックは最終取得日を基に再取得範囲を算出します。初回ロードやフルバックフィル時は run_prices_etl 等へ date_from を明示して下さい。
- ニュース収集は SSRF 等を意識した堅牢化（スキーム検証・プライベートホスト拒否・受信サイズ上限など）をしていますが、外部フィードの扱いには注意してください。
- strategy 層は発注 API を直接呼ばない設計です。生成した signals を execution 層で取り込み、リスク管理 → 発注という流れを実装してください。
- 単体/統合テスト用に KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を使い .env 自動ロードを無効化できます。

---

## サンプル（ワンライナーでの初期化と ETL 実行）
```bash
python - <<'PY'
from kabusys.config import settings
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl
conn = init_schema(settings.duckdb_path)
res = run_daily_etl(conn)
print(res.to_dict())
conn.close()
PY
```

---

以上がこのリポジトリの README になります。必要であれば「運用例（cron / systemd / Airflow での日次ジョブ化）」「開発時のローカルデバッグ方法（モックやテスト用 DuckDB の利用）」「主要な SQL テーブル定義の抜粋」など、追加のセクションを作成します。どの情報がさらに欲しいか教えてください。