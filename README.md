KabuSys — 日本株自動売買プラットフォーム
================================

概要
----
KabuSys は日本株向けのデータプラットフォームと戦略レイヤを備えた自動売買システムのコアライブラリです。  
主に以下を提供します。

- J-Quants API からの市場データ取得・保存（DuckDB）
- 市場データの ETL（差分取得・品質チェック）
- ファクター計算（モメンタム／バリュー／ボラティリティ等）
- 特徴量正規化・合成（features テーブル生成）
- シグナル生成（BUY / SELL 判定、エグジット判定）
- RSS ベースのニュース収集と銘柄紐付け
- 市場カレンダー管理と営業日判定
- 発注・発注履歴・監査用スキーマ（DuckDB 上の実行レイヤ）

設計思想のポイント
- DuckDB を用いた単一ファイル型ローカルデータベース（冪等な保存）
- ルックアヘッドバイアス回避のため「target_date 時点で利用可能なデータのみ」を明確に扱う
- ネットワークリトライ、レート制御、SSRF 等の安全対策を考慮
- 外部依存は最小限（標準ライブラリ + 必要ライブラリ）で research と production 層を分離

機能一覧
--------
主な機能（抜粋）:

- data
  - jquants_client: J-Quants API クライアント（レートリミット・リトライ・トークン自動更新）
  - pipeline: 日次 ETL（市場カレンダー、株価、財務）
  - schema: DuckDB スキーマ初期化
  - news_collector: RSS 収集・記事前処理・銘柄抽出・保存
  - calendar_management: 営業日判定・次営業日/前営業日の取得
  - stats: Z スコア正規化等の統計ユーティリティ
- research
  - factor_research: モメンタム／ボラティリティ／バリューの計算
  - feature_exploration: 将来リターン・IC・統計サマリ
- strategy
  - feature_engineering.build_features: features テーブル生成（Zスコア正規化・ユニバースフィルタ等）
  - signal_generator.generate_signals: ai_scores と統合した最終スコア計算、BUY/SELL 判定
- execution / monitoring: 発注・実行・監査用スキーマの準備（audit モジュール等）

セットアップ手順
----------------

前提
- Python 3.10 以上（typing の union 演算子等を利用）
- pip が利用可能

1. リポジトリをクローン／配置
   - 本 README はパッケージ配下の src/kabusys を前提としています。パッケージをインストールするか、開発モードで使います。

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - 主要な外部依存:
     - duckdb
     - defusedxml
   - 例:
     - pip install duckdb defusedxml
   - 開発モードインストール（プロジェクトの setup/pyproject がある場合）
     - pip install -e .

4. 環境変数 / .env
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に .env を置くと自動で読み込まれます（kabusys.config が自動ロード）。
   - 自動ロードを無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

   重要な環境変数（最低限）
   - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（必須）
   - KABU_API_PASSWORD     : kabu API のパスワード（必須）
   - SLACK_BOT_TOKEN       : Slack 通知用 Bot トークン（必須）
   - SLACK_CHANNEL_ID      : Slack チャンネル ID（必須）
   - DUCKDB_PATH           : DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
   - SQLITE_PATH           : 監視用 SQLite パス（デフォルト data/monitoring.db）
   - KABUSYS_ENV           : development / paper_trading / live（デフォルト development）
   - LOG_LEVEL             : ログレベル（DEBUG/INFO/...、デフォルト INFO）

   .env の例（.env.example を参考に作成してください）:
   - JQUANTS_REFRESH_TOKEN=xxxxxxxx
   - KABU_API_PASSWORD=your_kabu_password
   - SLACK_BOT_TOKEN=xoxb-...
   - SLACK_CHANNEL_ID=C0123456789
   - DUCKDB_PATH=data/kabusys.duckdb
   - KABUSYS_ENV=development

5. データベース初期化
   - サンプルコマンド:
     - python -c "from kabusys.data.schema import init_schema; init_schema('data/kabusys.duckdb')"
   - あるいは Python スクリプト内で init_schema を呼んで下さい。

使い方（基本ワークフロー）
------------------------

以下はライブラリ関数を使った典型的な処理例です。運用用途ではジョブスケジューラ（cron, systemd timer, Airflow 等）から呼び出します。

1. DB を初期化（1 回）
   - from kabusys.data.schema import init_schema
     conn = init_schema('data/kabusys.duckdb')

2. 日次 ETL（市場カレンダー、株価、財務を差分取得）
   - from kabusys.data.pipeline import run_daily_etl
     result = run_daily_etl(conn)
     print(result.to_dict())

   - オプション:
     - target_date を指定して特定日を処理可能
     - id_token を渡して J-Quants 認証トークンを注入可能（テスト用）

3. 特徴量構築（features テーブルへ）
   - from kabusys.strategy import build_features
     from datetime import date
     n = build_features(conn, date(2024, 1, 15))
     print(f"features upserted: {n}")

4. シグナル生成（features + ai_scores を参照して signals に書き込む）
   - from kabusys.strategy import generate_signals
     from datetime import date
     total = generate_signals(conn, date(2024, 1, 15))
     print(f"signals written: {total}")

5. ニュース収集（RSS）
   - from kabusys.data.news_collector import run_news_collection
     results = run_news_collection(conn, known_codes={'7203','6758', ...})
     print(results)

6. カレンダー更新ジョブ
   - from kabusys.data.calendar_management import calendar_update_job
     saved = calendar_update_job(conn)
     print(f"saved calendar rows: {saved}")

7. 実行層 / 監査
   - audit / execution 層のスキーマは schema.init_schema で作成済みです。発注実装やブローカー連携はこのレイヤを使って実装します。

運用上の注意
- J-Quants API のレート制限（120 req/min）やエラー応答に対してクライアントはリトライ・バックオフを実装していますが、運用時は過度な同時実行を避けてください。
- ETL は差分更新ロジックを備えていますが、初回は過去データの取得に時間がかかる場合があります。
- production（ライブ）運用時は KABUSYS_ENV=live を設定し、設定値・ログの権限管理に注意してください。
- ネットワーク呼び出しや外部 API はテスト時にモック可能な設計にしています（get_id_token や _urlopen 等を差し替えてテスト）。

ディレクトリ構成
----------------

主要なファイル／モジュール構成（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                    # 環境変数・.env ローダー
  - data/
    - __init__.py
    - jquants_client.py          # J-Quants API クライアント
    - pipeline.py                # ETL パイプライン
    - schema.py                  # DuckDB スキーマ定義・初期化
    - stats.py                   # 統計ユーティリティ（zscore_normalize 等）
    - news_collector.py          # RSS 収集・保存
    - calendar_management.py     # 営業日判定・カレンダー更新ジョブ
    - features.py                # features の公開インターフェース
    - audit.py                   # 監査ログ用スキーマ
  - research/
    - __init__.py
    - factor_research.py         # ファクター計算（mom/vol/value）
    - feature_exploration.py     # 将来リターン・IC・サマリー
  - strategy/
    - __init__.py
    - feature_engineering.py     # features 作成（正規化・ユニバースフィルタ）
    - signal_generator.py        # シグナル生成（final_score 計算等）
  - execution/                    # 実行層用プレースホルダ（発注実装等）
  - monitoring/                   # 監視・メトリクス関連（別途実装）

実例スニペット
--------------
DB 初期化と日次 ETL をまとめて実行する簡単なスクリプト例:

python
from datetime import date
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl
conn = init_schema('data/kabusys.duckdb')
res = run_daily_etl(conn, target_date=date.today())
print(res.to_dict())

貢献
----
バグ報告・改善提案・プルリクエストは歓迎します。開発にあたってはテストを追加の上で PR を送ってください。

補足（開発者向けメモ）
--------------------
- 自動 .env 読み込みは config._find_project_root によって .git または pyproject.toml を起点に行われます。テスト環境で自動ロードを無効にする場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。
- ネットワーク関数や外部 API 呼び出し部（jquants_client._request、news_collector._urlopen 等）はユニットテストでモックするよう設計されています。

---

この README はコードベースの主要機能と使い方をまとめたものです。さらに詳細な設計仕様（StrategyModel.md / DataPlatform.md / DataSchema.md 等）がプロジェクト内に存在する想定ですので、実運用・拡張時はそれらのドキュメントも参照してください。