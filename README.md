# KabuSys

日本株向けの自動売買プラットフォーム用ライブラリ。データ取得・ETL、ファクター計算、特徴量生成、シグナル生成、ニュース収集、監査テーブル定義などを含むモジュール群を提供します。

---

## 主要な特徴（機能一覧）

- J-Quants API クライアント
  - 日次株価（OHLCV）・財務データ・市場カレンダー取得
  - レート制限、リトライ、トークン自動リフレッシュ対応
- DuckDB スキーマ定義と初期化
  - Raw / Processed / Feature / Execution 層のテーブル群
  - 冪等なテーブル作成とインデックス定義
- ETL（差分取得）パイプライン
  - 日次ETL（カレンダー取得 → 株価 → 財務 → 品質チェック）
  - バックフィル、トレーディングデイ調整
- 研究（research）モジュール
  - モメンタム・ボラティリティ・バリュー等のファクター計算
  - 将来リターン計算、IC（Spearman）計算、ファクターサマリ
- 戦略（strategy）モジュール
  - 特徴量生成（Zスコア正規化、ユニバースフィルタ等）
  - シグナル生成（複数コンポーネントの重み付き合算、BUY/SELL判定、エグジット判定）
- ニュース収集（RSS）
  - RSS フィード取得、前処理、記事保存、銘柄コード抽出
  - SSRF 対策、XML Bomb 対策、サイズ制限
- 監査 / 発注・約定・ポジションのスキーマ
  - 監査ログ用テーブル（signal_events / order_requests / executions 等）

---

## 要件

- Python 3.9+
- 依存ライブラリ（最低限）
  - duckdb
  - defusedxml

（必要に応じてその他の依存を pyproject.toml / requirements.txt に追加してください）

---

## セットアップ手順

1. 仮想環境を作成しアクティベート（任意）
   - macOS / Linux:
     - python -m venv .venv
     - source .venv/bin/activate
   - Windows:
     - python -m venv .venv
     - .venv\Scripts\activate

2. 依存パッケージをインストール
   - pip install duckdb defusedxml

   （プロジェクトで requirements.txt / pyproject.toml があればそれを使ってください）

3. (任意) パッケージを開発モードでインストール
   - プロジェクトルートに pyproject.toml 等がある場合:
     - pip install -e .

4. データベース初期化（DuckDB）
   - Python からスキーマ初期化を実行します（例は後述）。

---

## 環境変数 / .env

このパッケージは環境変数を参照します。プロジェクトルートに `.env` / `.env.local` が置ければ自動読み込みします（CWD に依存せず、.git または pyproject.toml を基準に探索）。

主な必須変数:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- SLACK_BOT_TOKEN — Slack 通知用トークン（必須）
- SLACK_CHANNEL_ID — Slack チャンネル ID（必須）

任意 / デフォルト:
- KABUSYS_ENV — development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）

サンプル .env:
```
JQUANTS_REFRESH_TOKEN=your_refresh_token_here
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C12345678
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
LOG_LEVEL=INFO
```

自動読み込みを無効にする:
- 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロードを無効化します（テスト時など）。

---

## 使い方（主要な例）

以下は主要 API を利用する最小例です。すべてプログラムから呼び出す前提です。

1) DuckDB スキーマ初期化
```python
from kabusys.data.schema import init_schema

# ファイル DB を初期化
conn = init_schema("data/kabusys.duckdb")
# またはインメモリ
# conn = init_schema(":memory:")
```

2) 日次 ETL 実行（J-Quants からの差分取得）
```python
from kabusys.data.pipeline import run_daily_etl
from kabusys.data.schema import init_schema
from datetime import date

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

3) 特徴量（features）作成
```python
from kabusys.strategy import build_features
from kabusys.data.schema import init_schema
from datetime import date

conn = init_schema("data/kabusys.duckdb")
n = build_features(conn, target_date=date.today())
print(f"features upserted: {n}")
```

4) シグナル生成
```python
from kabusys.strategy import generate_signals
from kabusys.data.schema import init_schema
from datetime import date

conn = init_schema("data/kabusys.duckdb")
count = generate_signals(conn, target_date=date.today(), threshold=0.6)
print(f"signals written: {count}")
```

5) ニュース収集ジョブ（RSS）と保存
```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
# known_codes は銘柄コード集合（文字列）
results = run_news_collection(conn, known_codes={"7203","6758"})
print(results)
```

6) カレンダー夜間ジョブ
```python
from kabusys.data.calendar_management import calendar_update_job
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
saved = calendar_update_job(conn)
print(f"calendar saved: {saved}")
```

注意:
- 上の例はすべて API トークンなどが正しく設定されている前提です。
- ETL の実行はネットワークアクセスや大量の API コールを伴います。rate-limit に従って行われます。

---

## コード構成（ディレクトリ構成）

主要ファイル / モジュール（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py — 環境変数 / .env 自動ロードと Settings
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント（取得・保存ユーティリティ）
    - news_collector.py — RSS 収集・正規化・DB 保存
    - schema.py — DuckDB スキーマ定義と init_schema/get_connection
    - stats.py — zscore_normalize 等統計ユーティリティ
    - pipeline.py — 差分 ETL + 日次パイプライン
    - calendar_management.py — market_calendar 管理・営業日ロジック
    - features.py — データ系の公開インターフェース（zscore 再エクスポート）
    - audit.py — 監査ログ向け DDL（signal_events, order_requests, executions 等）
  - research/
    - __init__.py
    - factor_research.py — momentum/volatility/value の計算
    - feature_exploration.py — 将来リターン/IC/サマリ関数
  - strategy/
    - __init__.py
    - feature_engineering.py — features テーブル作成（正規化・フィルタ）
    - signal_generator.py — final_score 計算と signals テーブルへの書き込み
  - execution/ (発注 / オーケストレーション層のための placeholder)
  - monitoring/ (監視用コードを置く想定)

プロジェクトルートに .env(.local) と DuckDB ファイル（デフォルト data/kabusys.duckdb）を用意して運用します。

---

## 実運用上の注意

- 機密情報（API トークン等）は `.env` に置くか安全な Vault をお使いください。`.env` はリポジトリにコミットしないでください。
- J-Quants の API レート制限や kabu API のルールに従ってください。
- 本ライブラリの戦略ロジックはルックアヘッドバイアス回避等の配慮がされていますが、各自でバックテスト・リスク管理を十分行ってください。
- DuckDB のスキーマ設計は冪等性を重視しています。既存データを破壊しないため、初回実行時やマイグレーションは注意して行ってください。

---

もし README に追加したい情報（例: CLI、ユニットテスト実行方法、CI設定、ライセンス表記など）があれば教えてください。必要に応じてサンプルの .env.example や requirements.txt の雛形も作成します。