# KabuSys

日本株向けの自動売買基盤ライブラリ（ライブラリ群 / バッチ処理 / 研究ユーティリティ群）

この README は提供されたコードベースに基づいて作成した日本語ドキュメントです。ライブラリは主に以下を提供します：J-Quants API からのデータ取得、DuckDB スキーマ/初期化、ETL パイプライン、特徴量作成、シグナル生成、ニュース収集、マーケットカレンダー管理、監査ログ等。

---

## プロジェクト概要

KabuSys は日本株自動売買システム向けのデータ基盤と戦略モジュール群です。設計方針として以下を重視しています。

- データの冪等性（ON CONFLICT / upsert）とトレーサビリティ（fetched_at / created_at）
- ルックアヘッドバイアス回避（target_date 時点のデータのみを使用）
- 安全性（RSS の SSRF 対策、XML パース対策、API レート制御・リトライ）
- テスト性（id_token 注入や自動 env ロードの無効化など）
- DuckDB を用いたローカルデータベース中心の処理

主要モジュール例:
- data: J-Quants クライアント、ETL パイプライン、ニュース収集、スキーマ管理、統計ユーティリティ
- research: ファクター計算・探索ユーティリティ（IC, forward returns 等）
- strategy: 特徴量構築・シグナル生成
- execution / monitoring: 発注・監視に関する骨格（パッケージ公開 API に含む）

---

## 機能一覧

- J-Quants API クライアント（レートリミット、リトライ、トークン自動リフレッシュ）
  - 株価（日足）取得、財務データ取得、マーケットカレンダー取得
- DuckDB スキーマ定義・初期化（init_schema）
- ETL パイプライン（差分取得、バックフィル、品質チェック）
  - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl
- 特徴量計算・正規化
  - research.factor_research: momentum / volatility / value
  - strategy.feature_engineering: build_features（Zスコア正規化、ユニバースフィルタ、features テーブルへの UPSERT）
- シグナル生成
  - strategy.signal_generator: generate_signals（AIスコア統合、重み付け、BUY/SELL 判定、エグジット）
- ニュース収集（RSS）
  - data.news_collector: RSS 取得、前処理、raw_news 保存、銘柄コード抽出、news_symbols 紐付け
- マーケットカレンダー管理
  - data.calendar_management: is_trading_day / next_trading_day / prev_trading_day / calendar_update_job
- 統計ユーティリティ
  - data.stats.zscore_normalize（クロスセクションの Z スコア）
- 監査ログ（signal_events / order_requests / executions 等）スキーマ
- 安全・運用支援
  - SSRF 対策、gzip/サイズ制限、戻り値のエラーハンドリング、トランザクション処理（BEGIN/COMMIT/ROLLBACK）

---

## 前提・依存

- Python 3.9+（typing の新構文や型指定を使用）
- 必要な外部パッケージ（最低限）
  - duckdb
  - defusedxml

実際のプロジェクトでは requirements.txt / pyproject.toml に依存関係を明記してください。

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローン
   - git clone <repo-url>

2. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存インストール（例）
   - pip install duckdb defusedxml

   （実プロジェクトでは requirements.txt や pyproject を参照してください）
   - pip install -r requirements.txt

4. 環境変数設定
   - プロジェクトルートに `.env`（および開発時の `.env.local`）を作成
   - サンプル（.env.example）がある想定。主なキー:
     - JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
     - KABU_API_PASSWORD: kabuステーション API パスワード（必須）
     - KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
     - SLACK_BOT_TOKEN: Slack 通知用トークン（必須）
     - SLACK_CHANNEL_ID: Slack チャネル ID（必須）
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH: 監視 DB パス（デフォルト: data/monitoring.db）
     - KABUSYS_ENV: 開発環境 ("development" | "paper_trading" | "live")
     - LOG_LEVEL: ログレベル ("DEBUG" | "INFO" | ...)
   - 注: 起動時に自動で `.env` → `.env.local` をロードします。自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト時に便利）。

---

## 使い方（主要な操作例）

以下はいくつかの典型的な操作例です。これらはライブラリ API を直接呼ぶ形の例です。プロダクションではこれらをラッパー CLI やスケジューラ（cron / Airflow 等）から呼び出します。

1) DuckDB スキーマ初期化
```python
from kabusys.data.schema import init_schema
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)
# これで必要なテーブルがすべて作成される
```

2) 日次 ETL 実行（J-Quants からデータ取得して保存）
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl
from kabusys.data.schema import get_connection

conn = get_connection(settings.duckdb_path)
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

3) 特徴量構築（features テーブルへ書き込む）
```python
from datetime import date
import duckdb
from kabusys.strategy import build_features
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
count = build_features(conn, target_date=date.today())
print(f"upserted features: {count}")
```

4) シグナル生成（features / ai_scores / positions を参照して signals へ書き込む）
```python
from datetime import date
from kabusys.strategy import generate_signals
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
total = generate_signals(conn, target_date=date.today(), threshold=0.6)
print(f"signals written: {total}")
```

5) ニュース収集ジョブ（RSS 取得→raw_news 保存→銘柄紐付け）
```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import get_connection

conn = get_connection(settings.duckdb_path)
# known_codes は銘柄抽出で使う4桁コードの集合（例: set(['7203', '6758', ...])）
res = run_news_collection(conn, known_codes={'7203','6758'})
print(res)  # ソースごとの新規保存数
```

6) マーケットカレンダー更新（夜間バッチジョブ）
```python
from kabusys.data.calendar_management import calendar_update_job
from kabusys.data.schema import get_connection

conn = get_connection(settings.duckdb_path)
saved = calendar_update_job(conn)
print(f"saved calendar rows: {saved}")
```

---

## 主要な環境変数（まとめ）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (オプション, default: http://localhost:18080/kabusapi)
- SLACK_BOT_TOKEN (必須)
- SLACK_CHANNEL_ID (必須)
- DUCKDB_PATH (オプション, default: data/kabusys.duckdb)
- SQLITE_PATH (オプション, default: data/monitoring.db)
- KABUSYS_ENV (development | paper_trading | live, default: development)
- LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL, default: INFO)
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で .env 自動読み込みを無効化

設定は .env / .env.local / OS 環境変数の順序で読み込まれます（OS 環境変数が最優先）。.env.local は .env を上書きする目的で使います。

---

## ディレクトリ構成（主要ファイル）

以下はソースツリー（抜粋）です。実際にはテストやドキュメント等の追加ファイルがあるかもしれません。

- src/kabusys/
  - __init__.py
  - config.py                        # 環境変数・設定管理
  - data/
    - __init__.py
    - jquants_client.py              # J-Quants API クライアント
    - pipeline.py                    # ETL パイプライン（run_daily_etl 等）
    - news_collector.py              # RSS ニュース収集
    - schema.py                      # DuckDB スキーマ定義と init_schema
    - stats.py                       # 統計ユーティリティ（zscore_normalize）
    - features.py                    # data.features (再エクスポート)
    - calendar_management.py         # マーケットカレンダー管理
    - audit.py                       # 監査ログスキーマ
    - pipeline.py                    # ETL 実装（既出）
  - research/
    - __init__.py
    - factor_research.py             # モメンタム/ボラティリティ/バリュー計算
    - feature_exploration.py         # IC / forward returns / 統計サマリー
  - strategy/
    - __init__.py
    - feature_engineering.py         # build_features
    - signal_generator.py            # generate_signals
  - execution/                        # 発注実装のスケルトン
  - monitoring/                       # 監視用ユーティリティ

---

## 設計上の注意点 / 運用上の留意事項

- DuckDB の初期化は init_schema() を呼び出すことで行います。既存テーブルは上書きせずスキップされるため冪等です。
- ETL は差分取得とバックフィル（デフォルト3日）を組み合わせています。初回ロードは J-Quants の開始日（コード中の _MIN_DATA_DATE）から取得します。
- RSS 取得は SS RF 対策やサイズ制限を入れていますが、外部フィードの変化には注意してください。
- シグナル生成は Bear レジーム検出やストップロスなどのルールを実装しています。実運用ではリスク管理やオーダー発行の追加チェックが必要です。
- テスト目的で自動 env ロードを無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- ログレベルや KABUSYS_ENV によって挙動が変わる箇所があるため、本番( live )運用時は設定の見直しを行ってください。

---

## 開発／貢献について

- 新しい機能を追加する場合は、対応する DuckDB スキーマの変更を `data/schema.py` に反映し、init_schema で新旧互換性を考慮してください。
- API クライアントの変更はリトライ/トークン更新ロジックやレート制御を壊さないよう注意してください。
- テストでは DuckDB のインメモリ（":memory:"）接続を使うと便利です。
- セキュリティに関わる部分（RSS の URL 検証、XML パース、外部ホストアクセス）を修正する場合は、既存の防御（_is_private_host, _SSRFBlockRedirectHandler, defusedxml）に留意してください。

---

ご不明点や README に追加したい具体的な使用例（CLI 化、Docker サンプル、CI/CD ワークフロー等）があれば教えてください。必要に応じて README を拡張します。