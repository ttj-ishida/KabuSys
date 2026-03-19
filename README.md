# KabuSys

日本株自動売買システム (KabuSys) の README。  
このリポジトリはデータ収集・ETL、特徴量生成、シグナル生成、ニュース収集、監査・スキーマ管理までを含む日本株向けの自動売買プラットフォームのコアライブラリです。

---

## プロジェクト概要

KabuSys は以下を目的とした Python パッケージです。

- J-Quants API などから市場データ・財務データを取得して DuckDB に保存する ETL パイプライン
- 研究結果（raw factor）を加工して戦略用特徴量（features）を構築する機能
- 正規化済み特徴量と AI スコア等を統合して売買シグナル（BUY/SELL）を生成する機能
- RSS ベースのニュース収集と記事→銘柄の紐付け
- 発注／約定／ポジションのためのデータスキーマおよび監査ログ

設計上の留意点（抜粋）:
- ルックアヘッドバイアス防止のため、すべての集計・シグナルは target_date 時点の観測可能データのみを使用します。
- DuckDB をコア DB として採用し、冪等な保存（ON CONFLICT）・トランザクションを重視します。
- 外部依存は最小化し、ネットワーク処理等は堅牢化（リトライ・レートリミット・SSRF対策等）しています。

---

## 主な機能一覧

- data/
  - J-Quants API クライアント（取得・保存・ページネーション・トークンリフレッシュ）
  - DuckDB スキーマ定義・初期化（init_schema）
  - ETL パイプライン（差分取得・バックフィル・品質チェック）
  - ニュース収集（RSS -> raw_news、記事ID正規化、銘柄抽出）
  - マーケットカレンダー管理（営業日判定、next/prev_trading_day 等）
  - 各種統計ユーティリティ（zscore_normalize など）
- research/
  - ファクター計算（momentum / volatility / value）
  - 研究支援ユーティリティ（将来リターン / IC / 統計サマリー）
- strategy/
  - 特徴量エンジニアリング（build_features: 正規化・フィルタ適用・features テーブル書き込み）
  - シグナル生成（generate_signals: final_score 計算、BUY/SELL 生成、signals テーブル書き込み）
- data.audit: 監査ログ用スキーマ（信頼できるトレーサビリティ）
- config: 環境変数管理（.env 自動読み込み、必須変数チェック）

---

## 必要な環境変数

config.Settings で利用する主要な環境変数（必須／任意）:

必須:
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
- KABU_API_PASSWORD: kabu ステーション API のパスワード
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID: Slack チャンネル ID

任意（デフォルトあり）:
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV: 実行環境（development / paper_trading / live、デフォルト: development）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト: INFO）

自動 .env 読み込み:
- プロジェクトルート（.git もしくは pyproject.toml があるディレクトリ）にある `.env`、続けて `.env.local` を自動で読み込みます。
- 自動読み込みを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## セットアップ手順

1. リポジトリをクローン、プロジェクトルートへ移動

   ```
   git clone <repo-url>
   cd <repo-root>
   ```

2. Python 仮想環境の作成（例: venv）

   ```
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

3. 依存パッケージのインストール

   コードベースで使用している主な外部パッケージ:
   - duckdb
   - defusedxml

   例:
   ```
   pip install duckdb defusedxml
   ```

   （実運用では requirements.txt や poetry/poetry.lock を使って依存管理してください。）

4. 環境変数設定

   プロジェクトルートに `.env` を作成し、必要なキーを設定します（例）:

   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

   注意: `.env.local` はローカル上書き用に優先して読み込まれます。

5. DuckDB スキーマ初期化

   Python REPL またはスクリプトから init_schema を実行します:

   ```python
   from kabusys.data.schema import init_schema
   init_schema("data/kabusys.duckdb")  # :memory: も可能
   ```

---

## 基本的な使い方（例）

以下は主要な処理フローの利用例です。

- 日次 ETL（市場カレンダー・株価・財務の差分取得 + 品質チェック）:

```python
from datetime import date
import duckdb
from kabusys.data.schema import init_schema, get_connection
from kabusys.data.pipeline import run_daily_etl

# DB 初期化（初回のみ）
conn = init_schema("data/kabusys.duckdb")

# 日次 ETL 実行（target_date を指定しないと今日）
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- 特徴量構築（build_features）:

```python
from datetime import date
from kabusys.strategy import build_features
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
count = build_features(conn, target_date=date(2025, 1, 14))
print(f"features upserted: {count}")
```

- シグナル生成（generate_signals）:

```python
from datetime import date
from kabusys.strategy import generate_signals
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
total = generate_signals(conn, target_date=date(2025, 1, 14))
print(f"signals written: {total}")
```

- ニュース収集（run_news_collection）:

```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
# known_codes は既知の銘柄コードセットを渡すと記事→銘柄紐付けを行う
results = run_news_collection(conn, known_codes={"7203", "6758"})
print(results)
```

- J-Quants からデータを直接取得して保存:

```python
from kabusys.data import jquants_client as jq
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
records = jq.fetch_daily_quotes(date_from=date(2025,1,1), date_to=date(2025,1,10))
saved = jq.save_daily_quotes(conn, records)
print(f"saved {saved} rows")
```

---

## ロギングと実行モード

- 実行環境は `KABUSYS_ENV` で設定します（development / paper_trading / live）。`Settings.is_live` / `is_paper` / `is_dev` が参照できます。
- ログレベルは `LOG_LEVEL` で設定（デフォルト `INFO`）。
- 自動 .env 読み込みは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化できます（テスト時に便利）。

---

## ディレクトリ構成（主要ファイル）

以下は package 内の主要ファイル・モジュール一覧（src/kabusys 以下）:

- kabusys/
  - __init__.py
  - config.py                      — 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py             — J-Quants API クライアント（取得・保存）
    - news_collector.py             — RSS ニュース収集・前処理・保存
    - schema.py                     — DuckDB スキーマ定義・初期化（init_schema）
    - stats.py                      — 統計ユーティリティ（zscore_normalize）
    - pipeline.py                   — ETL パイプライン（run_daily_etl 等）
    - calendar_management.py        — 市場カレンダー操作（is_trading_day 等）
    - features.py                   — features 用公開ユーティリティ
    - audit.py                      — 監査ログ / トレーサビリティ用 DDL
  - research/
    - __init__.py
    - factor_research.py            — Momentum / Volatility / Value の計算
    - feature_exploration.py        — IC, forward returns, summary 等
  - strategy/
    - __init__.py
    - feature_engineering.py        — build_features
    - signal_generator.py           — generate_signals
  - execution/                      — 発注関連の実装（骨組み）
  - monitoring/                     — 監視用モジュール（監査/メトリクス、未記載の実装が想定される）

（実際のファイル一覧はリポジトリを参照してください。README は主要なエントリを抜粋しています。）

---

## 開発メモ / 注意点

- DuckDB の SQL を多用しており、date 型/タイムスタンプの取り扱いに注意してください。init_schema は既存テーブルがあっても冪等に実行されます。
- J-Quants API はレート制限（120 req/min）を考慮した実装になっています。APIトークンの取り扱いは厳重に行ってください。
- NewsCollector は RSS を外部接続するため SSRF 対策（スキーム検証・プライベートIP検出）や最大受信サイズチェックを実装していますが、運用時はフェッチ先リストに注意してください。
- 本コードには各所で「未実装」や「将来的に拡張することを想定」している部分があり、実運用前に十分なテスト／レビューが必要です。特に発注（execution）・資金管理・リスク管理は慎重に扱ってください。

---

もし README にサンプル .env.example、CI 実行方法、テスト手順、または特定のモジュールのより詳細なドキュメントを追加したい場合は、その要件を教えてください。