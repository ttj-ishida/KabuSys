KabuSys
=======

概要
----
KabuSys は日本株向けの自動売買プラットフォーム用ライブラリ群です。  
主に以下機能を持ちます。

- J-Quants API からのデータ取得と DuckDB への永続化（株価、財務、マーケットカレンダー）
- RSS ニュース収集と銘柄抽出（SSRF 対策・トラッキングパラメータ除去）
- DuckDB スキーマ定義／初期化ツール
- ファクター計算（モメンタム／ボラティリティ／バリュー等）と特徴量生成（Zスコア正規化）
- シグナル生成（特徴量＋AIスコアの統合、BUY/SELL 判定）
- 日次 ETL パイプラインとカレンダー管理、監査ログ用スキーマ

設計方針の一部：
- ルックアヘッドバイアスを避けるため、常に target_date 時点までのデータのみを使用
- DuckDB を中心に冪等（idempotent）な保存処理を実装
- 外部依存は最小限（標準ライブラリ＋duckdb、defusedxml 等）

主な機能一覧
--------------
- data/
  - jquants_client: J-Quants API クライアント（レート制限・リトライ・トークン自動更新・保存機能）
  - news_collector: RSS 収集・前処理・DB保存・銘柄抽出
  - schema: DuckDB のスキーマ定義と初期化（raw/processed/feature/execution 層）
  - pipeline: 日次 ETL（差分取得・保存・品質チェック）
  - calendar_management: JPX カレンダー管理・営業日判定ユーティリティ
  - stats / features: Z スコア正規化等の統計ユーティリティ
  - audit: 監査ログ用スキーマ（トレーサビリティ）
- research/
  - factor_research: モメンタム・ボラティリティ・バリューなどのファクター計算
  - feature_exploration: 将来リターン計算・IC（Spearman）・ファクター統計サマリー
- strategy/
  - feature_engineering: 生ファクターの正規化・フィルタ・features テーブルへの UPSERT
  - signal_generator: features と ai_scores を統合して final_score を算出、BUY/SELL 生成
- config.py: .env 自動読み込み、環境変数ラッパー（settings）

セットアップ（開発環境）
---------------------
前提: Python 3.9+（typing | None 構文が使われています。お手元の環境に合わせて調整してください）

1. リポジトリをクローン／取得
   - 例: git clone <リポジトリ>

2. 仮想環境の作成と有効化
   - macOS / Linux:
     python -m venv .venv
     source .venv/bin/activate
   - Windows (PowerShell):
     python -m venv .venv
     .\.venv\Scripts\Activate.ps1

3. 依存パッケージのインストール
   - 最低限必要なパッケージ:
     pip install duckdb defusedxml
   - （プロジェクトで requirements.txt がある場合はそれを使用してください）

4. 環境変数（.env）を用意
   - プロジェクトルートに .env または .env.local を置くと自動ロードされます
   - 自動ロードを無効にする場合:
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

推奨される .env の例（.env.example として保存）:
- JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxx
- KABU_API_PASSWORD=your_kabu_password
- KABU_API_BASE_URL=http://localhost:18080/kabusapi  # 任意
- SLACK_BOT_TOKEN=xoxb-...
- SLACK_CHANNEL_ID=C12345678
- DUCKDB_PATH=data/kabusys.duckdb
- SQLITE_PATH=data/monitoring.db
- KABUSYS_ENV=development  # development|paper_trading|live
- LOG_LEVEL=INFO

主要な使い方（簡易ガイド）
-------------------------

1) DuckDB スキーマ初期化
- 最初にデータベースファイルを作成し、スキーマを初期化します。

Python REPL / スクリプト例:
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")

- ":memory:" を渡すとインメモリ DB が作成されます（テスト時に便利）。

2) 日次 ETL 実行（J-Quants からの差分取得 → 保存）
from datetime import date
from kabusys.data.pipeline import run_daily_etl
result = run_daily_etl(conn, target_date=date.today())
# 結果は ETLResult 型（fetched/saved/quality_issues 等を含む）

3) 特徴量の生成（build_features）
from datetime import date
from kabusys.strategy import build_features
count = build_features(conn, target_date=date.today())
# features テーブルに指定日の特徴量がUPSERTされる

4) シグナル生成（generate_signals）
from datetime import date
from kabusys.strategy import generate_signals
num_signals = generate_signals(conn, target_date=date.today(), threshold=0.6)
# signals テーブルに BUY/SELL がUPSERTされる

5) ニュース収集（RSS）
from kabusys.data.news_collector import run_news_collection
# known_codes: 有効な4桁銘柄コードの集合（extract_stock_codes で使用）
results = run_news_collection(conn, sources=None, known_codes={"7203","6758"})

6) カレンダーユーティリティ例
from datetime import date
from kabusys.data.calendar_management import is_trading_day, next_trading_day
is_td = is_trading_day(conn, date(2026,3,20))
next_td = next_trading_day(conn, date(2026,3,20))

設定 API（settings）
-------------------
kabusys.config.settings 経由で環境設定を参照します（.env または OS 環境変数からロード）。
主なプロパティ:
- settings.jquants_refresh_token
- settings.kabu_api_password
- settings.kabu_api_base_url
- settings.slack_bot_token
- settings.slack_channel_id
- settings.duckdb_path (Path)
- settings.sqlite_path (Path)
- settings.env (development|paper_trading|live)
- settings.log_level

KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数を 1 に設定すると、config.py による .env 自動読み込みを無効化できます（テスト用途など）。

ロギング / 環境
---------------
- KABUSYS_ENV: development / paper_trading / live（settings.env）
- LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（settings.log_level）

内部設計のポイント（抜粋）
-------------------------
- ETL は「差分更新（差分取得 + backfill）」を採用し、API 側の後出し修正を吸収する設計
- DB 保存は ON CONFLICT / トランザクションを用いて冪等に実装
- ファクター/シグナルの計算はルックアヘッドを避ける（target_date までのデータのみ利用）
- ニュース収集には SSRF 対策、XML 固有の脆弱性対策（defusedxml）を実装
- J-Quants クライアントはレート制御、リトライ、401 時のトークン自動更新を備える

ディレクトリ構成
-----------------
（主要ファイルのみ抜粋）
src/
  kabusys/
    __init__.py
    config.py
    execution/              # 発注周り（今後実装）
    strategy/
      feature_engineering.py
      signal_generator.py
      __init__.py
    research/
      feature_exploration.py
      factor_research.py
      __init__.py
    data/
      __init__.py
      jquants_client.py
      news_collector.py
      schema.py
      pipeline.py
      features.py
      calendar_management.py
      stats.py
      audit.py
    monitoring/             # 監視用モジュール（別途実装想定）
その他:
  pyproject.toml / .git / .env.example（プロジェクトルートに配置想定）

注意事項 / ベストプラクティス
----------------------------
- 実運用（live）環境では KABUSYS_ENV=live に設定し、API キーやパスワード等は安全に管理してください（シークレット管理推奨）。
- DuckDB ファイルは定期的にバックアップしてください。
- J-Quants のレート上限を超えないため、並列で多数のリクエストを発行する際は注意してください（jquants_client は単純スロットリングを実装済み）。
- ニュース収集や外部 URL 取得は外部ネットワークの可用性・セキュリティに依存します。適切なタイムアウトと例外処理を行ってください。

貢献 / 開発フロー
-----------------
- バグ修正や機能追加は PR でお願いします。ユニットテスト、静的型チェック（mypy など）を追加すると歓迎します。
- ETL / データ処理系は再現性が重要なため、変更の際は既存 DB との互換性（DDL / 型）に注意してください。

---

不明点や特定機能のサンプル（例: signals→orders のフロー、Kabu API との連携など）が必要であれば、使い方の具体的なコード例を追加します。どの場面の使用例が欲しいか教えてください。