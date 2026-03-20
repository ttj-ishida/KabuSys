# KabuSys

バージョン: 0.1.0

KabuSys は日本株向けのデータ基盤・特徴量生成・シグナル生成を備えた自動売買システムのコアライブラリです。DuckDB をデータベースとして用い、J‑Quants API や RSS ニュースからデータを取得・保存し、戦略用の特徴量（features）やシグナル（signals）を生成します。モジュール設計により、ETL・研究（research）・戦略（strategy）・発注（execution）層が分離されています。

主な用途:
- 市場データ（OHLCV）・財務データ・市場カレンダーの差分取得と保存（J‑Quants）
- raw → processed → feature → execution の多層スキーマ（DuckDB）
- 研究用途のファクター計算・IC/forward-return 分析
- 戦略用特徴量の正規化・合成（feature_engineering）
- シグナル生成（signal_generator）
- RSS ベースのニュース収集と銘柄紐付け（news_collector）

---

## 機能一覧

- データ収集
  - J‑Quants API クライアント（rate limit / retry / token refresh 対応）
  - RSS フィード収集（SSRF 防御、トラッキングパラメータ除去、gzip 対応）
- ETL
  - 差分更新・バックフィル・品質チェックを含む日次 ETL（run_daily_etl）
  - 市場カレンダーの先読み（calendar_update_job）
- データ保存
  - DuckDB スキーマ定義・初期化（init_schema）
  - raw / processed / feature / execution の多層テーブル群（冪等保存）
- 研究（research）
  - momentum / volatility / value 等のファクター計算
  - forward returns / IC（Spearman） / 統計サマリー
  - クロスセクション Z スコア正規化ユーティリティ
- 戦略（strategy）
  - 特徴量生成（build_features: 正規化・ユニバースフィルタ・日付単位の UPSERT）
  - シグナル生成（generate_signals: final_score 計算、Bear レジーム抑制、BUY/SELL 判定）
- 発注・監査（execution / audit）
  - signals / signal_queue / order_requests / executions / positions 等のスキーマ
  - 監査ログ（signal_events / order_requests / executions）によりトレーサビリティ確保

---

## セットアップ手順

前提
- Python 3.8+（コードは型注釈で 3.10+ の記法も使われていますが、3.8+ を想定）
- DuckDB ライブラリ
- defusedxml（RSS パースで使用）

1. リポジトリをクローン（例）
   ```
   git clone <repo-url>
   cd <repo-root>
   ```

2. 仮想環境の作成・有効化（任意）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 必要パッケージのインストール（最低限）
   ```
   pip install duckdb defusedxml
   ```
   ※ プロジェクトに pyproject.toml / requirements.txt があればそちらを使ってください（例: pip install -e .）。

4. 環境変数設定
   - プロジェクトルートの `.env`（または `.env.local`）に必要な環境変数を設定します。
   - 自動読み込み: package 起動時に `.env` → `.env.local` が自動でプロジェクトルートから読み込まれます（OS 環境変数が優先されます）。
   - 自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します（テスト用）。

   必須となる環境変数（config.Settings に準拠）:
   - JQUANTS_REFRESH_TOKEN: J‑Quants のリフレッシュトークン
   - KABU_API_PASSWORD: kabuステーション API パスワード（execution 層で利用）
   - SLACK_BOT_TOKEN: Slack 通知用 Bot トークン
   - SLACK_CHANNEL_ID: Slack 送信先チャンネル ID

   オプション（デフォルトを持つもの）:
   - KABUSYS_ENV: development | paper_trading | live （デフォルト development）
   - LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL （デフォルト INFO）
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
   - SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）

   例: `.env.example`
   ```
   JQUANTS_REFRESH_TOKEN=__your_jquants_refresh_token__
   KABU_API_PASSWORD=__your_kabu_api_password__
   SLACK_BOT_TOKEN=__your_slack_bot_token__
   SLACK_CHANNEL_ID=__your_slack_channel_id__
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   ```

5. DuckDB スキーマの初期化
   Python REPL またはスクリプトで以下を実行して DB とテーブルを作成します。
   ```python
   from kabusys.data.schema import init_schema, settings
   conn = init_schema(settings.duckdb_path)  # デフォルト: data/kabusys.duckdb
   ```

---

## 使い方（主要なコード例）

以下は代表的な操作例です。実運用ではログ・エラーハンドリング・スケジューラを組み合わせてください。

- 日次 ETL（市場カレンダー・株価・財務・品質チェック）
```python
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)
result = run_daily_etl(conn)  # target_date を指定可能
print(result.to_dict())
```

- 特徴量の構築（features テーブルへの日次 UPSET）
```python
from kabusys.data.schema import init_schema
from kabusys.strategy import build_features
from datetime import date

conn = init_schema("data/kabusys.duckdb")
n = build_features(conn, target_date=date(2025, 1, 15))
print(f"features upserted: {n}")
```

- シグナル生成（signals テーブルへの日次置換）
```python
from kabusys.data.schema import init_schema
from kabusys.strategy import generate_signals
from datetime import date

conn = init_schema("data/kabusys.duckdb")
count = generate_signals(conn, target_date=date(2025, 1, 15))
print(f"signals written: {count}")
```

- ニュース収集ジョブ（RSS 取得 → raw_news / news_symbols 保存）
```python
from kabusys.data.schema import init_schema
from kabusys.data.news_collector import run_news_collection
# known_codes は銘柄コードセット（例: {"7203", "6758", ...}）
conn = init_schema("data/kabusys.duckdb")
results = run_news_collection(conn, known_codes={"7203", "6758"})
print(results)
```

- J‑Quants から日足を直接取得して保存
```python
from kabusys.data import jquants_client as jq
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
records = jq.fetch_daily_quotes(date_from=date(2025,1,1), date_to=date(2025,1,15))
saved = jq.save_daily_quotes(conn, records)
print("saved:", saved)
```

注意点:
- 各関数は冪等性（ON CONFLICT / 日付単位置換）を考慮して設計されています。
- research / strategy モジュールは発注実行層や外部 API への副作用を持たないよう分離されています（テストしやすさを確保）。

---

## 環境変数（主要）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- SLACK_BOT_TOKEN (必須)
- SLACK_CHANNEL_ID (必須)
- DUCKDB_PATH (既定: data/kabusys.duckdb)
- SQLITE_PATH (既定: data/monitoring.db)
- KABUSYS_ENV: development | paper_trading | live（既定: development）
- LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL（既定: INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 を設定すると .env の自動読み込みを無効化

環境変数はプロジェクトルートの `.env` / `.env.local` から自動読み込みされます（ただし OS 環境変数が優先）。自動読み込みはプロジェクトルート判定時に .git または pyproject.toml の存在を確認します。

---

## ディレクトリ構成（簡易）

パッケージは `src/kabusys` 下に実装されています。主なファイルと役割は以下のとおりです。

- src/kabusys/__init__.py
  - パッケージメタ（__version__ 等）
- src/kabusys/config.py
  - 環境変数・設定管理（Settings クラス）
- src/kabusys/data/
  - jquants_client.py: J‑Quants API クライアント + 保存ユーティリティ
  - news_collector.py: RSS 収集・正規化・保存
  - schema.py: DuckDB スキーマ定義・初期化
  - pipeline.py: ETL パイプライン（run_daily_etl 等）
  - features.py, stats.py, calendar_management.py, audit.py, pipeline.py など
- src/kabusys/research/
  - factor_research.py: momentum / volatility / value 等のファクター計算
  - feature_exploration.py: forward returns / IC / summary 等（研究用）
- src/kabusys/strategy/
  - feature_engineering.py: features 作成処理
  - signal_generator.py: final_score 計算と BUY/SELL 生成
- src/kabusys/execution/
  - 発注・実行周り（現状イニシャルモジュール）
- src/kabusys/monitoring/
  - 監視・モニタリング関連（SQLite 等）※未詳細化

（各ファイル内に詳細なドキュメント文字列が含まれており、モジュールごとの仕様・設計意図が記載されています）

---

## 開発・運用上の注意

- スキーマの互換性: DuckDB の一部機能（ON DELETE CASCADE 等）はバージョンに依存するため、DDL のコメントを参照してください。
- 時刻: 監査・fetched_at 等のタイムスタンプは UTC を利用する設計です。運用時はタイムゾーンの扱いに注意してください。
- レート制御・リトライ: J‑Quants API 呼び出しは内部で rate limiter / retry / token refresh を実装しています。大量バッチを実行する際は API レートに注意してください。
- 安全対策: RSS の取得では SSRF / XML Bomb 対策を行っています（SSRF 検査・defusedxml・読み取りサイズ制限）。
- 本番環境切替: KABUSYS_ENV を `live` に設定するとライブ取引向けのフラグを有効化する設計です。paper_trading や development と挙動が異なる箇所に注意してください。

---

## 参考・問い合わせ

- ソースコード内の docstring に詳細な設計意図・参照箇所（DataPlatform.md / StrategyModel.md 等）が記載されています。新機能追加や挙動確認時は該当モジュールの docstring を参照してください。
- バグ報告・機能要望はリポジトリの Issue にお願いします。

---

README はここまでです。必要であれば、運用スクリプト（systemd タイマー / cron）や CI 用のテスト手順、より詳細な .env.example、requirements.txt のテンプレートなども追加できます。どれを優先しましょうか？