# KabuSys

日本株向け自動売買プラットフォーム（ライブラリ）。  
データ収集（J-Quants）、ETL、特徴量計算、シグナル生成、ニュース収集、カレンダー管理、DuckDB ベースのスキーマ等を備えたモジュール群です。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買ワークフローを構成するための内部ライブラリ群です。主な目的は以下の通りです。

- J-Quants API からの市場データ・財務データ・カレンダーの取得（レート制御・リトライ・トークン自動リフレッシュを備える）
- DuckDB によるローカルデータベース管理（Raw / Processed / Feature / Execution 層）
- ETL パイプライン（差分更新・バックフィル・品質チェック）
- 研究環境向けのファクター計算・特徴量探索
- 特徴量の正規化と戦略用特徴量の生成（冪等処理）
- 戦略のシグナル生成（BUY/SELL 判定、エグジット条件、Bear レジーム処理）
- RSS からのニュース収集と銘柄紐付け（SSRF/サイズ制限等の防御策あり）
- マーケットカレンダー管理（営業日判定・next/prev/trading days）

設計上の特徴:
- ルックアヘッドバイアス回避（target_date 時点のデータのみを使用）
- 冪等処理（DB は ON CONFLICT/トランザクションで安全化）
- 外部依存を最小化（多くのユーティリティは標準ライブラリで実装）
- テストしやすいようにトークン注入やモック可能な内部関数を用意

---

## 機能一覧

- data/
  - jquants_client: J-Quants API クライアント（ページネーション・レート制御・リトライ・保存ユーティリティ）
  - pipeline: 日次 ETL（prices / financials / calendar）と差分更新ロジック
  - schema: DuckDB スキーマ定義・初期化（Raw / Processed / Feature / Execution 層）
  - news_collector: RSS 取得・記事前処理・DB 保存・銘柄抽出
  - calendar_management: market_calendar の更新と営業日判定ユーティリティ
  - stats: Z スコア正規化等の統計ユーティリティ
- research/
  - factor_research: Momentum / Volatility / Value 等のファクター計算
  - feature_exploration: 将来リターン計算、IC（Spearman）など探索的解析
- strategy/
  - feature_engineering: research 結果を正規化・フィルタして features テーブルへ保存
  - signal_generator: features と ai_scores を統合して final_score を算出、BUY/SELL シグナル生成
- execution/ monitoring/ (エントリポイントを含む設計。発注層や監視ロジックの実装拡張用)

---

## セットアップ手順

前提:
- Python 3.10+ を想定（型指定・構文より）
- duckdb を使用するためシステムに対応する Python パッケージをインストール

1. リポジトリをクローン・配置（例）
   ```bash
   git clone <repo-url>
   cd <repo-root>
   ```

2. 仮想環境を作成・有効化（推奨）
   ```bash
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .\.venv\Scripts\activate    # Windows (PowerShell)
   ```

3. 必要なパッケージをインストール
   基本的に標準ライブラリ中心ですが、少なくとも DuckDB と defusedxml は必要です:
   ```bash
   pip install duckdb defusedxml
   ```
   （プロジェクトに pyproject.toml / requirements.txt がある場合はそちらを優先してください）

4. 環境変数の設定
   ルートに `.env` または `.env.local` を置くと自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

   必須環境変数:
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
   - KABU_API_PASSWORD: kabu ステーション API パスワード（実運用時）
   - SLACK_BOT_TOKEN: Slack 通知（未使用でも将来通知に利用）
   - SLACK_CHANNEL_ID: Slack 通知先チャンネル ID

   任意:
   - KABUSYS_ENV: development | paper_trading | live（デフォルト development）
   - LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL（デフォルト INFO）
   - KABUSYS_DISABLE_AUTO_ENV_LOAD: 1（自動 .env 読み込みを無効化）
   - KABUSYS の DB パス:
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH: 監視 DB 等（デフォルト data/monitoring.db）

   .env 例:
   ```
   JQUANTS_REFRESH_TOKEN="your_jquants_refresh_token"
   KABU_API_PASSWORD="your_kabu_password"
   SLACK_BOT_TOKEN="xoxb-..."
   SLACK_CHANNEL_ID="C12345678"
   DUCKDB_PATH="data/kabusys.duckdb"
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

---

## 使い方（基本的なワークフロー例）

以下はライブラリをインポートして使う簡単な例です。DuckDB の接続初期化、ETL、特徴量構築、シグナル生成、ニュース収集などの基本フローを示します。

1. DuckDB スキーマの初期化
   ```python
   from kabusys.config import settings
   from kabusys.data.schema import init_schema

   conn = init_schema(settings.duckdb_path)  # ファイル作成および全テーブル定義
   ```

2. 日次 ETL の実行（J-Quants からデータ取得して保存）
   ```python
   from kabusys.data.pipeline import run_daily_etl

   result = run_daily_etl(conn)  # デフォルトで今日を対象に ETL 実行
   print(result.to_dict())
   ```

3. 特徴量の構築（strategy レイヤー用 features テーブルの作成）
   ```python
   from datetime import date
   from kabusys.strategy import build_features

   target = date(2025, 3, 20)
   n = build_features(conn, target)
   print(f"features upserted: {n}")
   ```

4. シグナルの生成
   ```python
   from kabusys.strategy import generate_signals

   total_signals = generate_signals(conn, target)
   print(f"signals written: {total_signals}")
   ```

5. ニュース収集（RSS） → raw_news 保存 → 銘柄紐付け
   ```python
   from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

   known_codes = {"7203", "6758", ...}  # 有効銘柄コードセット
   results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
   print(results)
   ```

6. カレンダー更新ジョブ（夜間バッチ想定）
   ```python
   from kabusys.data.calendar_management import calendar_update_job

   saved = calendar_update_job(conn)
   print(f"calendar saved: {saved}")
   ```

注意:
- run_daily_etl は品質チェックを行い、問題は ETLResult.quality_issues に報告します。
- 生成された signals テーブルは発注/エグゼキューション層へ渡す元データです。実際の発注は execution 層で行います（未実装の部分は拡張可能）。

---

## 環境変数一覧（主なもの）

- JQUANTS_REFRESH_TOKEN (必須)  
  J-Quants のリフレッシュトークン。get_id_token() で ID トークンを取得します。

- KABU_API_PASSWORD (必須)  
  kabu ステーション API のパスワード（発注連携に使用）。

- KABU_API_BASE_URL (任意)  
  kabu API ベース URL（デフォルト http://localhost:18080/kabusapi）。

- SLACK_BOT_TOKEN / SLACK_CHANNEL_ID (必須)  
  Slack 通知用。未設定だと通知機能は使えません。

- DUCKDB_PATH (任意)  
  DuckDB のファイルパス（デフォルト data/kabusys.duckdb）。

- SQLITE_PATH (任意)  
  モニタリング用 SQLite パス（デフォルト data/monitoring.db）。

- KABUSYS_ENV (任意)  
  実行環境: development / paper_trading / live（デフォルト development）。settings.is_live/is_paper/is_dev が参照します。

- LOG_LEVEL (任意)  
  ログレベル（DEBUG/INFO/...）。settings.log_level により検証されます。

- KABUSYS_DISABLE_AUTO_ENV_LOAD (任意)  
  1 にするとパッケージインポート時の自動 .env 読み込みを無効化します（ユニットテスト等で有用）。

---

## ディレクトリ構成

（リポジトリ内の主要ファイル・モジュールを抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py
    - data/
      - __init__.py
      - jquants_client.py
      - schema.py
      - pipeline.py
      - stats.py
      - news_collector.py
      - calendar_management.py
      - features.py
      - audit.py
      - audit (DDL インデックス等継続記述)
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
    - monitoring/
      - (監視/通知用モジュール用ディレクトリ)
- .env.example (プロジェクトルートに置く想定)
- pyproject.toml / setup.cfg（もしあればパッケージ情報）

主要なモジュールの役割:
- data/schema.py: DuckDB の全テーブル DDL と初期化処理（init_schema）
- data/jquants_client.py: J-Quants API とのやり取りと DuckDB への冪等保存関数
- data/pipeline.py: 日次 ETL のオーケストレーション（差分取得・保存・品質チェック）
- research/*: ファクター計算および探索用ユーティリティ
- strategy/*: 特徴量の正規化・シグナル生成（features / signals テーブル操作）
- data/news_collector.py: RSS 収集・前処理・DB 保存・銘柄抽出
- data/calendar_management.py: 営業日判定（is_trading_day / next_trading_day / get_trading_days）と calendar 更新

---

## 開発・運用上の留意点

- DuckDB のバージョン差や SQL の互換性に注意してください（外部キー ON DELETE など一部機能が古いバージョンで制限される旨がコード中に注記されています）。
- J-Quants の API レート制限（120 req/min）や 401/429/5xx ハンドリングは jquants_client 内で実装されていますが、実行時の API 仕様変更に注意してください。
- ルックアヘッドバイアス防止のため、strategy や research の関数は target_date 時点以前のデータのみを参照するよう設計されています。外部からデータを挿入・更新する際は時刻概念（fetched_at）の扱いに注意してください。
- .env の自動読み込みはプロジェクトルートの検出 (.git または pyproject.toml) に依存します。CI やテストでは KABUSYS_DISABLE_AUTO_ENV_LOAD を使うと安定します。

---

## 例: よく使うスクリプトの雛形

init_db.py:
```python
from kabusys.config import settings
from kabusys.data.schema import init_schema

if __name__ == "__main__":
    conn = init_schema(settings.duckdb_path)
    print("DB initialized:", settings.duckdb_path)
```

daily_job.py:
```python
from kabusys.config import settings
from kabusys.data.schema import get_connection, init_schema
from kabusys.data.pipeline import run_daily_etl
from datetime import date

if __name__ == "__main__":
    conn = init_schema(settings.duckdb_path)
    result = run_daily_etl(conn, target_date=date.today())
    print(result.to_dict())
```

build_and_signal.py:
```python
from kabusys.data.schema import init_schema
from kabusys.strategy import build_features, generate_signals
from datetime import date

conn = init_schema("data/kabusys.duckdb")
t = date(2025, 3, 20)
build_features(conn, t)
generate_signals(conn, t)
```

---

必要であれば README をさらに詳細化（CI 設定例、Dockerfile、デプロイ手順、単体テスト・モック戦略等）できます。どの情報を追加しますか？