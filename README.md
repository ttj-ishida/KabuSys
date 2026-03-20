# KabuSys

KabuSys は日本株向けの自動売買 / データプラットフォーム用ライブラリです。J-Quants API などからデータを取得・保存し、ファクター計算、特徴量生成、シグナル作成、発注・監査までの基本的なワークフローを備えています。研究（research）用モジュールと本番（execution）層を分離して設計しており、DuckDB をデータストアとして使用します。

主な設計方針：
- ルックアヘッドバイアスを防ぐ（計算は target_date 時点のデータのみ使用）
- 冪等性（DB の保存は ON CONFLICT / トランザクションで安全）
- 最小限の外部依存（DuckDB, defusedxml など）
- API レート制御・リトライ・トークン自動リフレッシュ（J-Quants クライアント）

---

## 主な機能一覧

- データ取得・保存（data.jquants_client）
  - 株価日足（OHLCV）、財務データ、マーケットカレンダーの取得・DuckDB への保存（冪等）
  - リトライ、指数バックオフ、レート制御、トークン自動リフレッシュ
- ETL パイプライン（data.pipeline）
  - 差分更新（バックフィル）、品質チェックとの統合、日次 ETL 実行
- DuckDB スキーマ管理（data.schema）
  - Raw / Processed / Feature / Execution 層のテーブル定義と初期化
- ニュース収集（data.news_collector）
  - RSS から記事を取得、前処理、記事ID生成（URL 正規化+SHA-256）、銘柄抽出、DB 保存
  - SSRF 対策、XML パーサ安全化、サイズ上限など
- カレンダー管理（data.calendar_management）
  - 営業日判定、next/prev 営業日、カレンダー差分更新バッチジョブ
- 研究用ファクター計算（research.factor_research）
  - Momentum / Volatility / Value 等のファクターを prices_daily, raw_financials を元に計算
- 特徴量生成（strategy.feature_engineering）
  - research で得た生ファクターをユニバースフィルタ、Z スコア正規化して features テーブルへ保存
- シグナル生成（strategy.signal_generator）
  - features + ai_scores を統合して final_score を算出、BUY/SELL シグナルを signals テーブルへ保存
- 統計ユーティリティ（data.stats）
  - クロスセクション Z スコア正規化など
- 監査ログ定義（data.audit）
  - シグナル→発注→約定のトレーサビリティテーブル（order_request_id 等）

---

## 要件

- Python 3.10 以上（typing の構文に依存）
- 必須パッケージ（例）
  - duckdb
  - defusedxml
- 標準ライブラリで多くを実装していますが、実行環境に応じて上記パッケージをインストールしてください。

推奨インストールコマンド例：
pip install duckdb defusedxml

（パッケージ化されている場合は `pip install -e .` など）

---

## 環境変数 / 設定

設定は環境変数またはプロジェクトルートの `.env` / `.env.local` から自動読み込みされます（プロジェクトルートは .git または pyproject.toml を探索して決定）。自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

重要な環境変数（Settings による必須/既定値）：
- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabu ステーション API のパスワード
- KABU_API_BASE_URL (任意) — デフォルト: http://localhost:18080/kabusapi
- SLACK_BOT_TOKEN (必須) — Slack 通知用トークン
- SLACK_CHANNEL_ID (必須) — Slack 通知先チャンネル ID
- DUCKDB_PATH (任意) — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH (任意) — 監視用 SQLite（デフォルト: data/monitoring.db）
- KABUSYS_ENV (任意) — development / paper_trading / live（デフォルト: development）
- LOG_LEVEL (任意) — DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）

注意点：
- Settings の必須キーが未設定だと起動時に ValueError が発生します。
- `.env` のパースは shell 風の簡易仕様（コメント、export、クォート対応）に従います。

---

## セットアップ手順（例）

1. リポジトリをクローン
   git clone <repo-url>
   cd <repo>

2. 仮想環境作成（任意）
   python -m venv .venv
   source .venv/bin/activate

3. 依存ライブラリをインストール
   pip install duckdb defusedxml

   （プロジェクトに setup.py / pyproject.toml がある場合は `pip install -e .`）

4. 環境変数を準備
   プロジェクトルートに `.env` を作成。例:
   JQUANTS_REFRESH_TOKEN=your_refresh_token
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C12345678
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO

5. DuckDB スキーマ初期化（スクリプト例は次節）

---

## 使い方（簡単なコード例）

以下は README 用の簡単な実行例です。実行前に環境変数や DuckDB パスを設定してください。

- スキーマ初期化（DuckDB 作成 + テーブル作成）
```python
from kabusys.data.schema import init_schema
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)
```

- 日次 ETL 実行（市場カレンダー・株価・財務の差分取得 + 品質チェック）
```python
from kabusys.data.pipeline import run_daily_etl
from kabusys.data.schema import init_schema
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)
result = run_daily_etl(conn)  # target_date を指定しなければ今日で実行
print(result.to_dict())
```

- 特徴量ビルド（strategy.feature_engineering）
```python
from datetime import date
from kabusys.strategy import build_features
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
count = build_features(conn, target_date=date(2025, 3, 1))
print(f"built features: {count}")
```

- シグナル生成（strategy.signal_generator）
```python
from datetime import date
from kabusys.strategy import generate_signals
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
total = generate_signals(conn, target_date=date(2025, 3, 1))
print(f"signals written: {total}")
```

- ニュース収集ジョブ（RSS から raw_news, news_symbols 保存）
```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
# known_codes は銘柄コードのセット（例: 全上場銘柄の4桁コード）
results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes={"7203","6758"})
print(results)
```

- マーケットカレンダーのユーティリティ
```python
from datetime import date
from kabusys.data.calendar_management import is_trading_day, next_trading_day
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
d = date(2025, 1, 1)
print("is trading:", is_trading_day(conn, d))
print("next trading:", next_trading_day(conn, d))
```

注意：
- 上記の関数は DuckDB の該当テーブル（prices_daily, raw_financials, features, ai_scores, positions 等）を参照します。初回は ETL でデータを投入してください。
- generate_signals / build_features は target_date より前までのデータを参照する設計になっています（ルックアヘッド防止）。

---

## ディレクトリ構成（主要ファイル）

以下はパッケージ内部の主要モジュール構成（src/kabusys）です。各ファイルはコメントで目的と設計方針が詳述されています。

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数読み込み・Settings 定義
  - data/
    - __init__.py
    - jquants_client.py
      - J-Quants API クライアント（取得・保存ユーティリティ）
    - news_collector.py
      - RSS 取得、記事前処理、raw_news / news_symbols 保存
    - schema.py
      - DuckDB スキーマ定義・init_schema / get_connection
    - stats.py
      - zscore_normalize 等の統計ユーティリティ
    - pipeline.py
      - ETL（日次 ETL、個別 ETL ジョブ）
    - calendar_management.py
      - market_calendar 管理・営業日ユーティリティ
    - audit.py
      - 監査ログ（signal_events, order_requests, executions 等）
    - features.py
      - data.stats のエクスポート（公開インターフェース）
  - research/
    - __init__.py
    - factor_research.py
      - Momentum / Volatility / Value 等のファクター計算
    - feature_exploration.py
      - 将来リターン計算、IC（Spearman）計算、統計サマリー
  - strategy/
    - __init__.py
    - feature_engineering.py
      - 生ファクターを正規化して features テーブルへ保存
    - signal_generator.py
      - features + ai_scores -> final_score -> BUY/SELL の生成と signals テーブル保存
  - execution/
    - __init__.py
      - 発注・注文処理（実装ファイルは別途）
  - monitoring (記載されているがリポジトリ内に別ファイルがあればそちらを参照)

（注）ファイル内部に詳細な設計コメント / 処理フローが書かれているため、実装の拡張や運用時の理解が容易です。

---

## 開発・運用上の注意

- 環境変数の必須キーが未設定だと Settings のプロパティが ValueError を送出します。CI/デプロイでは .env の管理に注意してください。
- J-Quants API はレート制限（120 req/min）を守る実装になっています。大量取得やバックフィル時は負荷に注意してください。
- RSS の取得・外部接続では SSRF 対策や XML の安全パース（defusedxml）を行っていますが、運用環境のネットワークポリシーに従ってください。
- DuckDB のファイルパスは複数プロセスから同時書き込みを行うと問題が出ることがあります。運用設計に合わせてロック・ジョブスケジューリングを検討してください。
- strategy モジュールは発注 API 層との直接の結合を避ける方針です。execution 層にてシグナルを受け取り発注する設計を想定しています。

---

README はここまでです。必要であれば以下も作成できます：
- サンプル .env.example
- より具体的な運用手順（cron / Airflow / systemd などでの定期実行例）
- テスト実行方法（ユニットテスト / モックの例）