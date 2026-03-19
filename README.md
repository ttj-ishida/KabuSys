# KabuSys

日本株向け自動売買基盤（KabuSys）の Python パッケージ。  
データ取得（J-Quants）、ETL、特徴量作成、シグナル生成、ニュース収集、DuckDB スキーマ管理など、戦略運用に必要な基盤機能を提供します。

---

## 目次
- プロジェクト概要
- 主な機能
- 前提・必要環境
- セットアップ手順
- 環境変数（.env）例
- 使い方（簡単な例）
- ディレクトリ構成
- トラブルシューティング／補足

---

## プロジェクト概要
KabuSys は日本株アルゴリズム売買のための基盤ライブラリ群です。  
主に以下のレイヤーを提供します。

- Data Layer: J-Quants からの株価・財務・カレンダー・ニュース取得と DuckDB への保存（冪等）
- ETL Pipeline: 差分取得・品質チェックを含む日次 ETL
- Research: ファクター計算・特徴量探索（IC / forward returns / summary）
- Strategy: 特徴量正規化（Z スコア）、最終スコア算出、BUY/SELL シグナル生成
- Execution / Audit: 発注・約定・ポジション監査用のスキーマ（監査トレーサビリティ設計）
- News Collection: RSS 収集・前処理・銘柄抽出

設計上の特徴:
- DuckDB をストレージに採用し、高速なローカル分析と永続化を実現
- API 呼び出しはレート制御・リトライ・トークンリフレッシュを内蔵
- 冪等保存（ON CONFLICT / upsert）で再実行に安全
- ルックアヘッドバイアス対策（時刻/日付を明確に扱う）

---

## 主な機能（抜粋）
- jquants_client: J-Quants API から日足・財務・カレンダーを取得（ページネーション対応・レート制御・自動トークン更新）
- data.schema: DuckDB のテーブル定義と初期化（Raw / Processed / Feature / Execution 層）
- data.pipeline: 日次 ETL（差分取得、backfill、品質チェック）
- data.news_collector: RSS 取得、正規化、raw_news 保存、銘柄抽出
- data.stats: Z スコア正規化等の統計ユーティリティ
- research.factor_research: momentum/volatility/value 等のファクター計算
- research.feature_exploration: forward returns / IC / factor summary
- strategy.feature_engineering: 生ファクターの正規化・ユニバースフィルタ適用・features テーブルへの保存
- strategy.signal_generator: features と ai_scores を統合して BUY/SELL シグナルを生成
- audit（監査）スキーマ: signal → order_request → execution までトレース可能なテーブル定義

---

## 前提・必要環境
- Python 3.9+（型アノテーションに基づく記述を使用）
- DuckDB（Python パッケージ duckdb）
- インターネット接続（J-Quants / RSS 取得時）
- （任意）Slack 連携用のトークン等

必要パッケージはリポジトリに requirements.txt があればそれを参照してください。無ければ最低限以下をインストールしてください（例）:

pip install duckdb defusedxml

---

## セットアップ手順（ローカル開発向け）
1. リポジトリをクローン
   - git clone <repo-url>
2. 仮想環境作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）
3. パッケージインストール
   - pip install -e .            （プロジェクトを editable install）
   - または requirements.txt があれば:
     - pip install -r requirements.txt
4. 環境変数設定（.env ファイルをプロジェクトルートに置く）
   - 下記「環境変数（.env）例」を参照
   - 注: パッケージは起動時にプロジェクトルート（.git または pyproject.toml のあるディレクトリ）から .env / .env.local を自動読み込みします。自動読み込みを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
5. DuckDB スキーマ初期化
   - Python REPL やスクリプトで init_schema() を実行（例は次節）

---

## 環境変数（.env）例
必須項目（Settings クラスで _require を使っているもの）:
- JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
- KABU_API_PASSWORD=your_kabu_password
- SLACK_BOT_TOKEN=xoxb-...
- SLACK_CHANNEL_ID=C01234567

任意 / デフォルトあり:
- KABUSYS_ENV=development|paper_trading|live  （デフォルト: development）
- LOG_LEVEL=INFO|DEBUG|...  （デフォルト: INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1  （自動 .env ロード無効化）
- KABUSYS_API_BASE_URL=...  （kabu API ベース URL を必要に応じて上書き）
- DUCKDB_PATH=data/kabusys.duckdb  （デフォルト）
- SQLITE_PATH=data/monitoring.db

例（.env）:
JQUANTS_REFRESH_TOKEN=your_refresh_token_here
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-xxxxxxxxxxxxxxxx
SLACK_CHANNEL_ID=C0123456789
KABUSYS_ENV=development
LOG_LEVEL=DEBUG
DUCKDB_PATH=data/kabusys.duckdb

---

## 使い方（簡単な例）

### 1) DuckDB スキーマ初期化
Python スクリプトまたは REPL で:

from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")

※ ":memory:" を渡すとインメモリ DB になります:
conn = init_schema(":memory:")

### 2) 日次 ETL 実行
from datetime import date
from kabusys.data.pipeline import run_daily_etl
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())

ETL は market_calendar → prices → financials → 品質チェック の順に実行します。ID トークンは settings.jquants_refresh_token を利用して自動で取得します。

### 3) 特徴量作成（features テーブルへ保存）
from datetime import date
from kabusys.strategy import build_features
count = build_features(conn, target_date=date.today())
print(f"features updated for {count} symbols")

内部で research.factor_research の各ファクターを呼び、ユニバースフィルタ・Z スコア正規化を行い features に日次置換で保存します。

### 4) シグナル生成
from datetime import date
from kabusys.strategy import generate_signals
num = generate_signals(conn, target_date=date.today(), threshold=0.60)
print(f"{num} signals written")

generate_signals は ai_scores を参照し、ファクター重みの補正や Bear レジームでの BUY 抑制、SELL（エグジット）判定を行い signals テーブルへ保存します。

### 5) ニュース収集
from kabusys.data.news_collector import run_news_collection
results = run_news_collection(conn, sources=None, known_codes=set_of_codes)
# results は {source_name: saved_count} の辞書

---

## ディレクトリ構成（主要ファイル説明）
以下はパッケージ内の主要モジュールとその役割の簡易一覧（src/kabusys 以下）。

- __init__.py
  - パッケージのメタ情報（__version__）とサブパッケージエクスポート

- config.py
  - 環境変数読み込み・Settings クラス。.env 自動読み込み、必須キー検査、環境種別（development/paper_trading/live）など

- data/
  - jquants_client.py: J-Quants API クライアント（レート制御、リトライ、保存ユーティリティ）
  - news_collector.py: RSS 収集・前処理・raw_news 保存・銘柄抽出
  - schema.py: DuckDB スキーマ定義と init_schema()
  - stats.py: zscore_normalize 等の統計ユーティリティ
  - pipeline.py: ETL パイプライン、run_daily_etl 等
  - calendar_management.py: market_calendar 管理・営業日判定・更新ジョブ
  - features.py: データ層の特徴量ユーティリティ公開（再エクスポート）

- research/
  - factor_research.py: momentum / volatility / value ファクター計算
  - feature_exploration.py: forward returns / IC / summary 等
  - __init__.py: 研究用 API のエクスポート

- strategy/
  - feature_engineering.py: features の構築（正規化・ユニバースフィルタ）
  - signal_generator.py: final_score 計算・BUY/SELL シグナル生成
  - __init__.py: strategy API のエクスポート

- execution/ (現在 init のみ: 発注層用の実装箇所)
  - __init__.py

- monitoring/ (監視・Slack 通知等の実装想定場所)

---

## トラブルシューティング / 補足
- .env の自動読み込みはプロジェクトルート（.git または pyproject.toml があるディレクトリ）を起点に行います。CI などで自動ロードを避ける場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- J-Quants API 呼び出しはレート制御（120 req/min）を実装しています。大量取得時は遅延が発生します。
- DuckDB のテーブル定義は冪等（CREATE IF NOT EXISTS）で書かれています。既存の DB に対するマイグレーションは別途検討してください。
- news_collector は defusedxml を使用し XML Bomb 対策や SSRF 防止の検証を行っています。RSS の形式差でパースに失敗することがあります（ログ参照）。
- strategy 層は発注 API へ直接依存しない設計です。実際の発注は execution 層に実装を追加してください。
- テスト時にトークンの自動リフレッシュを止めたい場合は jquants_client の _request 呼び出しで allow_refresh=False を明示できます（主に内部用）。

---

必要に応じて README を拡張して、CI 実行例、デバッグ手順、インストール済みパッケージ一覧、より詳細な API 使用例（フル ETL ジョブのサンプル）を追加できます。必要であれば続けて作成しますか？