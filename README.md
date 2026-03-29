# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリです。  
ETL・データ品質チェック・ニュース収集・AIを用いたニュースセンチメント・ファクター計算・監査ログなど、取引システム／リサーチ基盤で必要となる機能群を提供します。

概要
- パッケージ名: kabusys
- 目的: J-Quants 等の外部 API からデータを取得して DuckDB に保持し、品質チェックやファクター計算、ニュースセンチメント評価、監査ログを行う。さらに AI を用いたニュース解析や市場レジーム判定のユーティリティも含む。

主な機能一覧
- ETL
  - J-Quants API から株価日足（OHLCV）・財務データ・マーケットカレンダーを差分取得して DuckDB に冪等保存
  - 日次パイプライン run_daily_etl によるまとめ実行
- データ品質チェック
  - 欠損・重複・将来日付・スパイク検出などのチェック（quality モジュール）
- ニュース収集
  - RSS フィード取得、前処理、raw_news および news_symbols への保存（news_collector）
  - SSRF/サイズ/トラッキングパラメータ対策実装
- AI（OpenAI）
  - ニュースセンチメントを銘柄ごとに評価して ai_scores に書き込む score_news（gpt-4o-mini を想定）
  - マクロ指標（ETF 1321 の MA200 乖離）とマクロニュースの LLM センチメントを合成して市場レジーム判定する score_regime
  - 失敗時はフォールバック（安全策）を備えた堅牢な実装
- 研究用ユーティリティ
  - モメンタム / ボラティリティ / バリュー等のファクター計算（research パッケージ）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー
- 監査ログ
  - シグナル→発注→約定までのトレーサビリティ用テーブル／初期化ユーティリティ（audit モジュール）
- J-Quants クライアント
  - レート制御（120 req/min）・リトライ・トークン自動更新・ページネーション対応
- 環境設定管理
  - .env ファイル / OS 環境変数からの設定読み込み（自動ロードを無効化するフラグあり）

セットアップ手順 (開発環境向け)
1. リポジトリをクローン
   ```
   git clone <your-repo-url>
   cd <repo>
   ```

2. Python 環境を用意（推奨: venv / pyenv）
   ```
   python -m venv .venv
   source .venv/bin/activate
   ```

3. 依存関係をインストール  
   （本コードでは openai, duckdb, defusedxml などを使用しています。プロジェクト側の requirements.txt / poetry を用意している想定です）
   ```
   pip install -r requirements.txt
   ```
   もし requirements.txt が無い場合、最低限:
   ```
   pip install duckdb openai defusedxml
   ```

4. 環境変数を設定  
   プロジェクトルートに .env / .env.local を置くと自動読み込みされます（ただしテスト等で無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。
   主要な環境変数（必須）
   - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（ETL 用）
   - KABU_API_PASSWORD     : kabuステーション API のパスワード（注文実行系）
   - SLACK_BOT_TOKEN       : Slack 通知用 Bot トークン（通知機能が使われる場合）
   - SLACK_CHANNEL_ID      : Slack チャネル ID
   - OPENAI_API_KEY        : OpenAI API キー（score_news / score_regime 等の AI 機能で使用）
   任意・デフォルト付き
   - KABUSYS_ENV           : execution 環境 ('development' / 'paper_trading' / 'live')、デフォルト 'development'
   - LOG_LEVEL             : ログレベル（'DEBUG'/'INFO'/...）、デフォルト 'INFO'
   - KABU_API_BASE_URL     : kabuAPI ベース URL（デフォルト http://localhost:18080/kabusapi）
   - DUCKDB_PATH           : DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
   - SQLITE_PATH           : SQLite (monitoring) パス（デフォルト data/monitoring.db）

   例 (.env):
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
   OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxx
   SLACK_BOT_TOKEN=xoxb-xxxxxxxxxxxx
   SLACK_CHANNEL_ID=C0123456789
   KABU_API_PASSWORD=your_kabu_pwd
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   ```

5. データベースディレクトリの作成（必要に応じて）
   ```
   mkdir -p data
   ```

初期化（監査テーブル等）
- 監査ログ用 DuckDB ファイルを初期化する例:
  ```python
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  # conn は DuckDB 接続オブジェクト
  ```

使い方（主要な例）
- 設定読み込み（settings）
  ```python
  from kabusys.config import settings
  print(settings.jquants_refresh_token)  # 必須環境変数を参照
  ```

- 日次 ETL の実行
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメントのスコア付け（AI）
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  n_written = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-xxx")
  print("written:", n_written)
  ```

- 市場レジームスコアの計算（AI + MA200）
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-xxx")
  ```

- カレンダー関連ユーティリティ
  ```python
  from datetime import date
  import duckdb
  from kabusys.data.calendar_management import is_trading_day, next_trading_day, get_trading_days

  conn = duckdb.connect("data/kabusys.duckdb")
  d = date(2026, 3, 20)
  print(is_trading_day(conn, d))
  print(next_trading_day(conn, d))
  print(get_trading_days(conn, date(2026,3,1), date(2026,3,31)))
  ```

- 監査スキーマ初期化（既存接続へ適用）
  ```python
  from kabusys.data.audit import init_audit_schema
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")
  init_audit_schema(conn, transactional=True)
  ```

注意点 / 運用上のポイント
- OpenAI 呼び出しは外部 API であり、レスポンス不安定時はフォールバックする実装になっていますが、API キーと利用状況は運用者で管理してください。
- J-Quants API はレート制限（デフォルト 120 req/min）に従うよう内部で制御しています。ただし運用時はトークンの有効期限や API レスポンスの状態監視が必要です。
- 自動で .env を読み込む仕組みがあります。自動読み込みを無効化したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB の executemany に関する制約に配慮した実装（空パラメータ回避など）になっています。

ディレクトリ構成（抜粋）
- src/kabusys/__init__.py
- src/kabusys/config.py
- src/kabusys/ai/
  - __init__.py
  - news_nlp.py
  - regime_detector.py
- src/kabusys/data/
  - __init__.py
  - jquants_client.py
  - pipeline.py
  - etl.py
  - quality.py
  - stats.py
  - news_collector.py
  - calendar_management.py
  - audit.py
  - pipeline.py
  - etl.py
- src/kabusys/research/
  - __init__.py
  - factor_research.py
  - feature_exploration.py
- src/kabusys/ai (AI 関連)
- src/kabusys/research (研究用ユーティリティ)
- そのほか: strategy, execution, monitoring 等の上位モジュールはパッケージ公開名に含まれます（コードベースに応じて拡張されます）。

ライセンス・貢献
- リポジトリに LICENSE ファイルがある場合はそちらを参照してください。貢献やバグ報告は Pull Request / Issue を通じて行ってください。

問い合わせ
- 実行時の問題や仕様の質問は、プロジェクトの Issue またはチーム内の連絡手段で相談してください。

以上がこのコードベースの利用ガイド兼 README です。追加でサンプルスクリプトや CI / デプロイ手順を追記したい場合は、希望する用途（例: 本番デプロイ、テストのモック設定、Docker 化など）を教えてください。