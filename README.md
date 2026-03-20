# KabuSys

日本株向けの自動売買 / データ基盤ライブラリ。  
DuckDB をデータ層に使い、J-Quants API / RSS からのデータ収集、特徴量作成、戦略シグナル生成、監査ログ等のユーティリティを提供します。

主な設計方針:
- ルックアヘッドバイアス防止（各処理は target_date 時点の情報のみを使用）
- 冪等性（DB INSERT は ON CONFLICT やトランザクションで上書き/一貫性を担保）
- テスト容易性（ID トークン注入や自動 env ロード無効化など）
- 外部依存は限定（DuckDB・defusedxml 等のみ）

---

## 機能一覧
- 環境設定管理
  - .env / 環境変数をプロジェクトルート基準で自動ロード（無効化可）
  - 必須環境変数のバリデーション
- データ取得・保存（J-Quants クライアント）
  - 日足（OHLCV）、財務データ、マーケットカレンダーの取得（ページネーション対応）
  - 取得データを DuckDB に冪等保存するユーティリティ
  - レートリミット、リトライ、トークン自動リフレッシュ対応
- ETL パイプライン
  - 差分更新（最終取得日ベースの差分取得 + バックフィル）
  - 市場カレンダー / 株価 / 財務データの一括 ETL（run_daily_etl）
  - 品質チェック（外部 quality モジュールとの連携）
- データスキーマ管理
  - DuckDB 用スキーマ初期化（Raw / Processed / Feature / Execution 層）
  - インデックス定義、テーブル作成順を含む init_schema
- ニュース収集
  - RSS フィード取得・前処理・raw_news 保存
  - SSRF 対策、XML パース攻撃対策、受信サイズ制限
  - 記事ID は正規化 URL の SHA-256（先頭32文字）で冪等性を確保
  - 銘柄コード抽出・news_symbols への紐付け
- 研究（research）
  - ファクター計算（momentum / volatility / value 等）
  - 将来リターン計算、IC（Spearman）や統計サマリ
  - Z スコア正規化ユーティリティ
- 特徴量作成 / シグナル生成（strategy）
  - build_features: ファクター統合・ユニバースフィルタ・Z スコア正規化 → features テーブルへ
  - generate_signals: features / ai_scores を統合して final_score を算出、BUY/SELL シグナルを signals テーブルへ
  - Bear レジーム抑制、エグジット（ストップロス、スコア低下）判定
- 監査ログ（audit）
  - signal_events, order_requests, executions など監査用テーブル定義（UUID ベースのトレーサビリティ）

---

## 動作要件（推奨）
- Python 3.10+（型注釈に | を使用するため）
- pip パッケージ:
  - duckdb
  - defusedxml
- ネットワークアクセス（J-Quants API / RSS）

※実際の運用では発注系（kabu API）や Slack 通知など追加ライブラリが必要になることがあります。

---

## 環境変数 / .env（主な項目）
config.Settings で参照される主要環境変数:

- JQUANTS_REFRESH_TOKEN（必須） — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD（必須） — kabu ステーション API パスワード
- KABU_API_BASE_URL（任意） — kabu ステーション API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN（必須） — Slack ボットトークン（通知に使用）
- SLACK_CHANNEL_ID（必須） — Slack チャンネル ID（通知に使用）
- DUCKDB_PATH（任意） — DuckDB の DB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（任意） — 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV（任意） — 実行環境: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL（任意） — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）

自動 .env ロード:
- プロジェクトルート（.git または pyproject.toml を探索）にある `.env` と `.env.local` を自動で読み込みます。
- OS 環境変数 > .env.local > .env の優先順位。
- 自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

例 (.env):
KABUSYS_ENV=development
JQUANTS_REFRESH_TOKEN=your_refresh_token_here
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C12345678
DUCKDB_PATH=data/kabusys.duckdb
LOG_LEVEL=INFO

---

## セットアップ手順（ローカル開発向け）
1. リポジトリをクローン / ソース配置
2. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate（Windows: .venv\Scripts\activate）
3. 必要パッケージをインストール
   - pip install duckdb defusedxml
   - （セットアップ時に開発用依存をまとめる場合は requirements/dev.txt 等を用意してください）
4. プロジェクトルートに .env（上記参照）を作成
5. DuckDB スキーマ初期化
   - Python REPL またはスクリプトから:
     from kabusys.data import schema
     conn = schema.init_schema("data/kabusys.duckdb")
   - :memory: を使う場合は ":memory:" を指定可能

---

## 使い方（主要 API 例）

- DuckDB スキーマ初期化
  - 簡単なスクリプト例:
    from kabusys.data import schema
    conn = schema.init_schema("data/kabusys.duckdb")

- 日次 ETL 実行（株価・財務・カレンダー取得 + 品質チェック）
  - 例:
    from datetime import date
    import duckdb
    from kabusys.data.pipeline import run_daily_etl
    from kabusys.data.schema import init_schema
    conn = init_schema("data/kabusys.duckdb")
    result = run_daily_etl(conn, target_date=date.today())
    print(result.to_dict())

- 特徴量作成（features テーブルへの書き込み）
  - 例:
    from datetime import date
    from kabusys.data.schema import get_connection
    from kabusys.strategy import build_features
    conn = get_connection("data/kabusys.duckdb")
    count = build_features(conn, target_date=date(2024, 1, 31))
    print(f"features upserted: {count}")

- シグナル生成（signals テーブルへの書き込み）
  - 例:
    from datetime import date
    from kabusys.data.schema import get_connection
    from kabusys.strategy import generate_signals
    conn = get_connection("data/kabusys.duckdb")
    total = generate_signals(conn, target_date=date(2024, 1, 31))
    print(f"signals written: {total}")

- ニュース収集ジョブ
  - 例:
    from kabusys.data.news_collector import run_news_collection
    from kabusys.data.schema import get_connection
    conn = get_connection("data/kabusys.duckdb")
    known_codes = {"7203", "6758", ...}  # 有効な銘柄コード集合
    results = run_news_collection(conn, sources=None, known_codes=known_codes)
    print(results)

- カレンダー夜間バッチ
  - 例:
    from kabusys.data.calendar_management import calendar_update_job
    conn = get_connection("data/kabusys.duckdb")
    saved = calendar_update_job(conn)
    print(f"saved calendar rows: {saved}")

（上記はライブラリ呼び出し例です。運用ではスケジューラ（cron / Airflow 等）から呼び出すことを想定しています）

---

## 注意点 / 動作上の留意事項
- J-Quants API のレート制限（120 req/min）やリトライ・トークンリフレッシュは jquants_client に実装済みです。
- ETL は差分取得を行いますが、初回は _MIN_DATA_DATE から全件取得します（init 時の負荷に注意）。
- DB の初期化（init_schema）は一度だけ行ってください。get_connection は既存 DB への接続を返します。
- news_collector は外部ネットワーク接続を行うため、SSRF や XML 脆弱性に配慮した実装（defusedxml、ホスト/スキーム検査、サイズ制限）を組み込んでいます。
- 実運用（ライブ口座）では KABUSYS_ENV=live を設定し、発注 / 実行フローを慎重に検証してください。paper_trading 環境との切り替えで振る舞いが異なる可能性があります。
- 一部モジュール（execution 層・監視・Slack 通知等）は外部サービス側の実装や追加ライブラリが必要です。

---

## ディレクトリ構成
（主要ファイルのみ抜粋）

src/kabusys/
- __init__.py
- config.py                    — 環境変数 / 設定管理
- data/
  - __init__.py
  - jquants_client.py          — J-Quants API クライアント（取得/保存）
  - news_collector.py         — RSS ニュース取得・保存
  - pipeline.py               — ETL パイプライン（run_daily_etl 等）
  - schema.py                 — DuckDB スキーマ定義 / init_schema
  - stats.py                  — 統計ユーティリティ（zscore_normalize）
  - features.py               — features 公開インターフェース
  - calendar_management.py    — マーケットカレンダー管理
  - audit.py                  — 監査テーブル定義
  - ...（quality 等の関連モジュール）
- research/
  - __init__.py
  - factor_research.py        — momentum / volatility / value の計算
  - feature_exploration.py    — 将来リターン / IC / サマリー
- strategy/
  - __init__.py
  - feature_engineering.py    — build_features
  - signal_generator.py       — generate_signals
- execution/
  - __init__.py               — 発注・実行層（拡張箇所）
- monitoring/                 — 監視・アラート系（未展開）
- ... その他モジュール

---

## 開発 / 貢献
- バグ報告や機能提案は Issue を作成してください
- 大きな変更は PR（ブランチ・単体テスト・更新されたドキュメント）をお願いします

---

README は以上です。必要であれば以下を追記します:
- CI / テスト実行方法
- 追加の運用手順（発注フローの安全対策、ロールバック方法）
- サンプルワークフロー（cron / systemd / Airflow 用の例）