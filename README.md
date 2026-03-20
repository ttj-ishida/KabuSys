# KabuSys

KabuSys は日本株向けの自動売買基盤（データ収集 → 特徴量作成 → シグナル生成 → 発注／監査）を構成する Python モジュール群です。J-Quants API や RSS ニュースからデータを収集し、DuckDB 上に ETL を行い、戦略のための特徴量・シグナル生成を行うことを目的としています。

主な設計方針：
- ルックアヘッドバイアスを避ける（計算は target_date 時点のデータのみを使用）
- 冪等性（DB 保存は ON CONFLICT / トランザクションで安全に）
- ネットワーク呼び出しに対してリトライ・レート制御を行う
- セキュリティ対策（RSS の SSRF・XML 攻撃対策など）

## 機能一覧
- データ取得（J-Quants API クライアント）
  - 株価日足（OHLCV）
  - 財務データ（四半期 BS/PL）
  - JPX マーケットカレンダー
  - レート制限／リトライ／トークン自動リフレッシュ
- データ保存・スキーマ管理（DuckDB）
  - Raw / Processed / Feature / Execution 層のテーブル定義と初期化
- ETL パイプライン
  - 日次差分取得（backfill 対応）、品質チェックフック
- ニュース収集
  - RSS 収集、前処理、記事ID の冪等生成、銘柄抽出、DB 保存
  - XML/SSRF/サイズ制限等の安全対策
- 研究用ファクター計算 / 特徴量エンジニアリング
  - Momentum / Volatility / Value 等
  - Z スコア正規化ユーティリティ
- 戦略: シグナル生成
  - features + ai_scores を統合して最終スコアを算出
  - BUY / SELL の判定（Bear レジームフィルタ、ストップロス等）
- 実行・監査用スキーマ
  - signals / signal_queue / orders / executions / positions 等
  - 監査用テーブル群（signal_events / order_requests / executions）

## 要求環境
- Python >= 3.10（型ヒントに union 演算子 `|` を使用）
- 必須パッケージ（例）
  - duckdb
  - defusedxml
- 標準ライブラリで賄われる部分が多いですが、実行環境に応じて追加パッケージが必要になる場合があります（例: Slack 通知等）。

例（開発環境向け）:
pip install duckdb defusedxml

※ 実際のプロジェクト配布では requirements.txt / poetry / pyproject.toml を使って依存管理してください。

## セットアップ手順

1. リポジトリをクローン / パッケージをインストール
   - 開発時:
     - python -m venv .venv
     - source .venv/bin/activate
     - pip install -e .  （パッケージ化されている場合）
     - または必要なパッケージを直接インストール: pip install duckdb defusedxml

2. 環境変数の設定
   - プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（kabusys.config がプロジェクトルートを .git または pyproject.toml から探索して読み込みます）。
   - 自動読み込みを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します（テスト用途など）。

   主要な環境変数（キー名と説明）
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
   - KABU_API_PASSWORD: kabuステーション（証券API）パスワード（必須）
   - KABU_API_BASE_URL: kabuAPI のベース URL（デフォルト: http://localhost:18080/kabusapi）
   - SLACK_BOT_TOKEN: Slack Bot トークン（通知を使う場合に必須）
   - SLACK_CHANNEL_ID: Slack チャンネル ID（通知を使う場合に必須）
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH: SQLite（モニタリング用）パス（デフォルト: data/monitoring.db）
   - KABUSYS_ENV: 環境（development / paper_trading / live）, デフォルト development
   - LOG_LEVEL: ログレベル（DEBUG/INFO/...）, デフォルト INFO

   .env の記述例:
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxx
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C00000000
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   ```

3. DuckDB スキーマ初期化
   - Python REPL やスクリプトから以下を実行して DB とテーブルを初期化します。

   Python 例:
   ```python
   from kabusys.data.schema import init_schema, get_connection
   conn = init_schema("data/kabusys.duckdb")  # ファイルを作成して全テーブルを作る
   # 既に初期化済みの DB に接続する場合:
   # conn = get_connection("data/kabusys.duckdb")
   ```

## 使い方（主なワークフロー）

以下はよく使う関数／ジョブの実行例です。実運用ではジョブを cron / Airflow / Dagster 等に組み込む想定です。

1. 日次 ETL の実行（市場カレンダー取得 → 株価差分取得 → 財務取得 → 品質チェック）
```python
from datetime import date
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

2. カレンダー夜間更新ジョブ（JPX カレンダー差分更新）
```python
from kabusys.data.schema import init_schema
from kabusys.data.calendar_management import calendar_update_job

conn = init_schema("data/kabusys.duckdb")
saved = calendar_update_job(conn, lookahead_days=90)
print("saved:", saved)
```

3. ニュース収集ジョブ（RSS 取得→ raw_news 保存 → 銘柄紐付け）
```python
from kabusys.data.schema import init_schema
from kabusys.data.news_collector import run_news_collection

conn = init_schema("data/kabusys.duckdb")
# known_codes は銘柄コードの集合（抽出に使用）
known_codes = {"7203", "6758", "9432"}  # 例
results = run_news_collection(conn, known_codes=known_codes)
print(results)
```

4. 特徴量構築（research の出力を正規化して features テーブルへ UPSERT）
```python
from datetime import date
import duckdb
from kabusys.strategy import build_features

conn = duckdb.connect("data/kabusys.duckdb")
n = build_features(conn, target_date=date(2025,1,15))
print("features upserted:", n)
```

5. シグナル生成
```python
from datetime import date
import duckdb
from kabusys.strategy import generate_signals

conn = duckdb.connect("data/kabusys.duckdb")
count = generate_signals(conn, target_date=date(2025,1,15), threshold=0.6)
print("signals generated:", count)
```

## 主要モジュール / API の説明（簡潔）
- kabusys.config
  - 環境変数の自動読み込み（.env, .env.local）と Settings クラス（settings）を提供。
  - 必須変数取得時は _require が ValueError を投げる。
- kabusys.data.jquants_client
  - J-Quants との通信、fetch_xxx / save_xxx の組合せでデータ取得と DuckDB 保存を行う。
- kabusys.data.schema
  - DuckDB テーブル定義と init_schema を提供。
- kabusys.data.pipeline
  - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl 等の ETL ジョブ。
- kabusys.data.news_collector
  - RSS フィードの取得、記事前処理、DB 保存、銘柄抽出。
- kabusys.research
  - calc_momentum / calc_volatility / calc_value / calc_forward_returns / calc_ic / factor_summary 等、研究用ユーティリティ。
- kabusys.strategy
  - build_features（特徴量作成）、generate_signals（シグナル生成）。

## ディレクトリ構成

以下は本パッケージの主要ファイル一覧（抜粋）です：

- src/kabusys/
  - __init__.py
  - config.py
  - data/
    - __init__.py
    - jquants_client.py
    - news_collector.py
    - schema.py
    - stats.py
    - pipeline.py
    - features.py
    - calendar_management.py
    - audit.py
    - pipeline.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - strategy/
    - __init__.py
    - feature_engineering.py
    - signal_generator.py
  - execution/  (発注関連の実装やラッパーを配置するための空パッケージ)
  - monitoring/  (監視・通知実装用ディレクトリ、今回のコードベースでは参照のみ)
  - その他: 各モジュールの実装はコメント・ドキュメントで仕様（StrategyModel.md, DataPlatform.md 等）に準拠

（注）上記は現在の実装で存在するファイルのうち主要なものを抜粋しています。実際のリポジトリではテスト・ドキュメント・CI 設定等が別ディレクトリに含まれることがあります。

## 運用上の注意 / 補足
- DB の初期化は init_schema() を必ず使ってください（DDL の順序やインデックスを考慮しています）。
- J-Quants の API レート制限や 401 リフレッシュロジックを実装済みですが、長時間のバッチでは rate limit に注意してください。
- RSS フェッチは外部ネットワークを利用します。SSRF 対策やレスポンスサイズ制限を施していますが、運用時の例外処理をログ監視してください。
- シグナル生成・発注は実運用時のリスクが高いため、paper_trading 環境で十分に検証してください。環境変数 KABUSYS_ENV による環境切替（development / paper_trading / live）が用意されています。
- 自動環境変数読み込み（.env）を無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定できます（ユニットテスト等で便利です）。

---

この README はコードコメントおよびコードの公開 API を基に作成しています。さらに詳しい設計・仕様（StrategyModel.md, DataPlatform.md, DataSchema.md 等）がリポジトリに含まれている場合はそちらも参照してください。必要であればサンプルワークフローやデプロイスクリプト、CI 設定例も追加できます。希望があれば教えてください。