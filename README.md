# KabuSys

バージョン: 0.1.0

KabuSys は日本株向けの自動売買 / データプラットフォーム用ライブラリです。J-Quants 等の外部データソースから市場データ・財務データ・ニュースを取得し、DuckDB に蓄積、特徴量の生成、シグナル算出、発注監査などの基本機能を備えます。研究（research）と本番（execution）を分離した設計になっており、ルックアヘッドバイアス対策や冪等性、堅牢な ETL を考慮しています。

主な目的:
- 市場データ / 財務データ / ニュースのETL（差分取り込み、品質チェック）
- 研究用ファクター計算・特徴量生成
- 戦略のスコアリングとシグナル生成（BUY / SELL）
- DuckDB によるデータ管理と監査ログ基盤

---

## 主な機能一覧

- 環境設定管理（.env / 環境変数の自動読み込み）
- J-Quants API クライアント（ページネーション、リトライ、トークン自動更新、レートリミット）
- DuckDB スキーマ定義と初期化（Raw / Processed / Feature / Execution 層）
- ETL パイプライン（run_daily_etl：カレンダー → 株価 → 財務 → 品質チェック）
- ニュース収集（RSS 取得、正規化、SSRF対策、トラッキングパラメータ除去、銘柄紐付け）
- 研究用ファクター計算（モメンタム / ボラティリティ / バリュー 等）
- 特徴量作成（Zスコア正規化、ユニバースフィルタ、±3 クリップ、features テーブルへの UPSERT）
- シグナル生成（各種スコアの合成、ベア相場抑制、エグジット判定、signals テーブルへの出力）
- カレンダー管理（営業日判定／前後営業日探索／夜間カレンダー更新）
- 監査ログ用テーブル群（signal / order / execution のトレース）

---

## 必要条件 / 依存

最低限の依存（例）
- Python 3.9+
- duckdb
- defusedxml

※ 実行環境や追加機能により他パッケージが必要になることがあります。J-Quants API、kabuステーション API、Slack API 等へ接続する場合はネットワークと各種トークンが必要です。

例（pip インストール）:
pip install duckdb defusedxml

---

## 環境変数（必須/任意）

config.Settings から参照される主な環境変数:

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabu API のパスワード
- SLACK_BOT_TOKEN — Slack ボットトークン
- SLACK_CHANNEL_ID — Slack 通知用チャンネルID

任意（デフォルトあり）:
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite（モニタリング用）パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 環境: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — ログレベル: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）

.env の自動ロード:
- パッケージはプロジェクトルート（.git または pyproject.toml を目印）にある .env / .env.local を自動で読み込みます。
- OS 環境変数 > .env.local > .env の優先順位で適用されます。
- 自動読み込みを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## セットアップ手順（例）

1. リポジトリをクローン
   git clone <repo-url>
   cd <repo-dir>

2. 仮想環境を作る（推奨）
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate

3. 必要パッケージをインストール
   pip install -U pip
   pip install duckdb defusedxml

   （開発用に requirements.txt / extras があればそちらを利用）

4. 環境変数設定
   - .env をプロジェクトルートに作成するか、OS 環境変数で設定してください。
   - 必須トークン（JQUANTS_REFRESH_TOKEN 等）を設定すること。

   例 .env:
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567

5. DuckDB スキーマ初期化
   Python REPL またはスクリプトで:
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")

   ":memory:" を渡すとインメモリ DB になります。

---

## 使い方：主要な API と実行例

以下は基本的なワークフローの例です。実運用ではログ設定や例外処理・スケジューリングが必要です。

1) DB を初期化
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")

2) 日次 ETL（市場カレンダー → 株価 → 財務 → 品質チェック）
from kabusys.data.pipeline import run_daily_etl
result = run_daily_etl(conn)  # target_date を渡さなければ本日
print(result.to_dict())

3) 特徴量生成（features テーブル作成）
from kabusys.strategy import build_features
from datetime import date
count = build_features(conn, date(2025, 1, 15))
print(f"features upserted: {count}")

4) シグナル生成
from kabusys.strategy import generate_signals
from datetime import date
n = generate_signals(conn, date(2025, 1, 15))
print(f"signals created: {n}")

5) ニュース収集ジョブ
from kabusys.data.news_collector import run_news_collection
known_codes = {"7203", "6758", "6501"}  # 例: 有効な銘柄コードセット
results = run_news_collection(conn, known_codes=known_codes)
print(results)

6) カレンダー夜間更新ジョブ
from kabusys.data.calendar_management import calendar_update_job
saved = calendar_update_job(conn)
print(f"market_calendar saved: {saved}")

注意点:
- J-Quants へアクセスする関数はネットワークと有効なトークンが必要です。
- ETL の差分ロジックは DB の最終取得日を参照して自動で date_from を決定します。
- feature / signal の処理は target_date 時点のデータのみを使用し、ルックアヘッドバイアスを避ける設計です。

---

## 主要モジュール説明（抜粋）

- kabusys.config
  - .env / 環境変数の読み込み、Settings クラスで設定値を提供

- kabusys.data
  - jquants_client: J-Quants API クライアント（取得/保存ユーティリティ）
  - schema: DuckDB スキーマ定義と init_schema / get_connection
  - pipeline: ETL パイプライン（run_daily_etl 等）
  - news_collector: RSS 取得・解析・DB 保存（SSRF 対策、トラッキング除去）
  - calendar_management: 営業日判定 / カレンダー更新 / next/prev_trading_day
  - stats / features: 統計ユーティリティ（zscore_normalize 等）
  - audit: 発注〜約定の監査ログ用テーブル定義

- kabusys.research
  - factor_research: モメンタム・ボラティリティ・バリュー等のファクター計算
  - feature_exploration: 将来リターン計算 / IC / summary 等の研究ユーティリティ

- kabusys.strategy
  - feature_engineering: raw ファクターから features テーブルを作る
  - signal_generator: features / ai_scores を統合して signals を作成

- kabusys.execution
  - 発注・証券会社連携ロジック（現状プレースホルダ／別実装想定）

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py
- data/
  - __init__.py
  - jquants_client.py
  - news_collector.py
  - schema.py
  - pipeline.py
  - calendar_management.py
  - features.py
  - stats.py
  - audit.py
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
- monitoring/  (パッケージとして公開されているが個別実装はコードベースに依存)

各ファイルにはモジュールレベルの docstring があり、実装の意図・設計方針・公開 API が記載されています。詳細は各モジュールの docstring を参照してください。

---

## 運用上の注意 / ベストプラクティス

- 機密情報（API トークン等）は .env に置く場合でもアクセス制御を徹底すること。
- 本番 env は KABUSYS_ENV=live を使用し、paper_trading と明確に分離すること。
- DuckDB ファイルは定期的にバックアップを取ること（監査ログを保持しているため削除不可の場合が多い）。
- ETL はスケジューラ（cron / Airflow / Prefect 等）で夜間に実行し、ログと結果を監視すること。
- news_collector の RSS 取得は公開フィードの仕様に準拠する。過度な頻度は避ける。

---

フィードバックや機能追加要望があればお知らせください。README の補足（例: .env.example、CI / テスト手順、具体的な運用例）を追加できます。