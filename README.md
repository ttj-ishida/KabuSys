# KabuSys

日本株向け自動売買システムのコアライブラリ（データプラットフォーム・リサーチ・AI・監査ログ等を含む）

概要
- KabuSys は日本株の自動売買システム構築のための内部ライブラリ群です。
- 主にデータ収集（J-Quants / RSS）、ETL、データ品質チェック、ファクター計算、AI（ニュースセンチメント／市場レジーム判定）、監査ログ管理を提供します。
- DuckDB をデータストアとして利用し、OpenAI（gpt-4o-mini）をニュース解析に用いる設計になっています。
- Look‑ahead バイアス対策、冪等性、堅牢なリトライ・レート制限、SSRF 対策等が盛り込まれています。

主な機能一覧
- データ取得・ETL
  - J-Quants API クライアント（株価・財務・上場銘柄・市場カレンダー）
  - 差分更新・バックフィルをサポートする日次 ETL（run_daily_etl 等）
  - ETL 実行の結果を格納する ETLResult（品質問題やエラーの集約）
- ニュース収集
  - RSS からの記事収集（URL 正規化、トラッキング除去、SSRF 対策）
  - raw_news / news_symbols テーブルへの冪等保存
- AI（OpenAI）
  - ニュースの銘柄ごとセンチメントスコア算出（news_nlp.score_news）
  - 市場レジーム判定（ETF 1321 の MA200 とマクロニュースを合成して bull/neutral/bear を判定）（regime_detector.score_regime）
  - API 呼び出しは JSON Mode を利用、再試行／フォールバックロジックあり
- リサーチ用ユーティリティ
  - モメンタム・バリュー・ボラティリティ等のファクター計算（research.calc_*）
  - 将来リターン計算、IC（情報係数）や統計サマリ（feature_exploration 等）
  - クロスセクション Z スコア正規化（data.stats.zscore_normalize）
- データ品質チェック
  - 欠損、スパイク、重複、日付不整合の検出（data.quality.run_all_checks）
- マーケットカレンダー管理
  - JPX カレンダーの差分取得と保存、営業日判定ユーティリティ（data.calendar_management）
- 監査ログ（Audit）
  - シグナル→発注→約定までトレーサビリティを保証する監査テーブル定義・初期化（data.audit.init_audit_db / init_audit_schema）
- 設定管理
  - .env または環境変数から設定を自動読み込み（kabusys.config.settings）
  - 自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能

必要条件（推奨）
- Python 3.10 以上（PEP 604 の型表記 "X | Y" を利用）
- 主要パッケージ（例）
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants API、OpenAI、RSS フィード）

セットアップ手順（開発環境向け）
1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo-dir>
   ```
2. 仮想環境作成（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```
3. 依存パッケージをインストール
   最低限：
   ```
   pip install duckdb openai defusedxml
   ```
   （プロジェクトに requirements.txt / pyproject.toml があればそちらからインストールしてください）
4. 環境変数 / .env の準備
   - プロジェクトルート（.git や pyproject.toml の位置）に `.env` / `.env.local` を配置すると自動で読み込まれます（kabusys.config の自動ロード）。
   - 必須の環境変数（代表例）:
     - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD: kabu API パスワード（kabu 関連機能を使う場合）
     - SLACK_BOT_TOKEN / SLACK_CHANNEL_ID: 通知用（必要なら）
     - OPENAI_API_KEY: OpenAI を利用する場合（score_news / score_regime でも引数で渡せます）
   - 例（.env）
     ```
     JQUANTS_REFRESH_TOKEN=xxxx...
     OPENAI_API_KEY=sk-...
     KABU_API_PASSWORD=your_kabu_password
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     ```
   - 自動読み込みを無効にする（テスト等）:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```

基本的な使い方（Python API 例）
- 設定と DuckDB 接続
  ```python
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  ```
- 日次 ETL 実行
  ```python
  from kabusys.data.pipeline import run_daily_etl
  from datetime import date

  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```
- ニュースのセンチメントスコアを生成（ai -> ai_scores テーブルへ保存）
  ```python
  from kabusys.ai.news_nlp import score_news
  from datetime import date

  written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"書き込み件数: {written}")
  ```
- 市場レジーム判定（market_regime テーブルへ保存）
  ```python
  from kabusys.ai.regime_detector import score_regime
  from datetime import date

  score_regime(conn, target_date=date(2026, 3, 20))
  ```
- 監査 DB 初期化（監査用 DuckDB ファイル生成）
  ```python
  from kabusys.data.audit import init_audit_db
  conn_audit = init_audit_db("data/audit.duckdb")
  ```
- 品質チェック実行
  ```python
  from kabusys.data.quality import run_all_checks
  issues = run_all_checks(conn, target_date=date(2026, 3, 20))
  for issue in issues:
      print(issue)
  ```

設定・環境変数一覧（主要なもの）
- JQUANTS_REFRESH_TOKEN (必須): J-Quants リフレッシュトークン（settings.jquants_refresh_token）
- OPENAI_API_KEY: OpenAI API キー（score_news/score_regime に引数で渡すことも可能）
- KABU_API_PASSWORD: kabu ステーション API のパスワード
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN / SLACK_CHANNEL_ID: Slack 通知用
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- PID_FILE_PATH / CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT: 監視設定
- KABUSYS_ENV: 実行環境（development / paper_trading / live）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）

設計上の注意点・運用メモ
- 自動読み込み: kabusys.config はプロジェクトルートの .env / .env.local を自動ロードします。テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。
- 冪等性: 多くの保存関数は ON CONFLICT DO UPDATE を使っており、再実行しても既存データを適切に更新します。
- Look-ahead バイアス対策: AI スコア / ファクター計算は内部で日付条件を厳密に扱い、date.today() を不適切に参照しない設計になっています（バックテストでの利用を意識）。
- OpenAI 呼び出し: API の失敗はフェイルセーフとしてスコアをスキップ（0 または空）して継続するロジックを持っています。テスト時は内部の _call_openai_api をモック可能です。
- RSS 取得: SSRF 対策、受信サイズ制限、XML の安全パーシング（defusedxml）を実装しています。

簡易ディレクトリ構成
（主要モジュールのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py
    - regime_detector.py
  - data/
    - __init__.py
    - calendar_management.py
    - etl.py
    - pipeline.py
    - stats.py
    - quality.py
    - audit.py
    - jquants_client.py
    - news_collector.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - research/...（その他ユーティリティ）
  - (execution/, monitoring/ 等はパッケージ公開リストに含まれますが、コードベースにより追加モジュールがある想定)

テスト・開発
- OpenAI / ネットワーク依存箇所はモック可能です（news_nlp._call_openai_api, regime_detector._call_openai_api 等をパッチ）。
- DuckDB を用いるためユニットテストはインメモリ接続（":memory:"）で軽量に実行できます。
- 大規模 ETL の統合テストは小さなサンプルデータベースを用意して実行してください。

最後に
- 本リポジトリは自動売買システムのコア部を構成するライブラリ群です。実際の発注モジュールやリスク管理層、運用の可観測化（監視・アラート）は別モジュール／運用設計と組み合わせて利用してください。
- 追加のドキュメント（StrategyModel.md、DataPlatform.md 等）があれば合わせて参照することを推奨します。

ご希望があれば、README にサンプル .env.example、より詳細な API 使用例や運用手順（cron / systemd / Docker など）を追記します。