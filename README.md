# KabuSys

日本株向けの自動売買・データプラットフォーム用ライブラリ群です。データ取得（J-Quants）、ETL、データ品質チェック、ニュースセンチメント（LLM）、市場レジーム判定、リサーチ用ファクター計算、監査ログ（約定トレーサビリティ）などのユーティリティを提供します。

概要
- 目的: 日本株向けのデータパイプラインとリサーチ・自動売買インフラの基盤を提供する
- 設計方針: ルックアヘッドバイアス回避、冪等性、フェイルセーフなエラーハンドリング、外部APIのレート制御とリトライ、DuckDB中心の軽量データストア

主な機能一覧
- 環境設定管理（settings）：.env / .env.local 自動読み込み、必須環境変数取得
- データ取得（jquants_client）：J-Quants API から日次株価、財務、マーケットカレンダーなど取得・保存（DuckDB）
- ETL パイプライン（data.pipeline）：差分取得・保存・品質チェックを行う日次ETL run_daily_etl
- データ品質チェック（data.quality）：欠損、スパイク、重複、日付不整合の検出
- カレンダー管理（data.calendar_management）：営業日判定、next/prev_trading_day、calendar_update_job
- ニュース収集（data.news_collector）：RSS 収集、前処理、安全対策（SSRF/Gzip/サイズ制限）
- AI ニュース NLP（ai.news_nlp）：OpenAI（gpt-4o-mini）で銘柄ごとのニュースセンチメントを計算し ai_scores に保存
- 市場レジーム判定（ai.regime_detector）：ETF（1321）のMA乖離とマクロニュースセンチメントを合成して market_regime を更新
- リサーチ（research）：モメンタム/バリュー/ボラティリティ等のファクター計算、将来リターン、IC/ランク・サマリー
- 監査ログ（data.audit）：signal → order_request → execution のトレーサビリティ用テーブル定義と初期化ユーティリティ
- ユーティリティ（data.stats）：Zスコア正規化など

必要な環境変数（主なもの）
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API 用パスワード（必須）
- SLACK_BOT_TOKEN, SLACK_CHANNEL_ID: Slack 通知用（必須）
- OPENAI_API_KEY: OpenAI API キー（score_news / score_regime 実行時に使用）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite（監視等）パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV: 環境 ("development" / "paper_trading" / "live")（デフォルト: development）
- LOG_LEVEL: ログレベル ("DEBUG", "INFO", ...)

.env の自動読み込み
- プロジェクトルート（.git または pyproject.toml があるディレクトリ）を探索して .env を自動読み込みします。
- 読み込み順: OS環境変数 > .env.local > .env
- テスト等で自動読み込みを無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

セットアップ手順（例）
1. Python バージョン
   - Python 3.10 以降を推奨（型ヒントの表記に依存）

2. 仮想環境作成（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージのインストール（最低限の例）
   - pip install duckdb openai defusedxml
   - その他プロジェクトに必要なパッケージがある場合は requirements.txt を用意して pip install -r requirements.txt

4. 環境変数の設定
   - プロジェクトルートに .env を作成して必要なキーを設定（例は下）
     ```
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     OPENAI_API_KEY=your_openai_api_key
     KABU_API_PASSWORD=your_kabu_password
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     ```
   - .env.local を使ってローカル上書きも可能

5. DuckDB データベース（ファイル）は自動で作成されます（パスの親ディレクトリは自動作成されます）。

使い方（簡単な例）
- 共通: 設定を参照する
  ```
  from kabusys.config import settings
  print(settings.duckdb_path)
  ```

- ETL（デイリーパイプライン）実行
  ```
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメント（LLM）でスコアを生成し ai_scores に保存
  ```
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect(str(settings.duckdb_path))
  written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # 環境変数 OPENAI_API_KEY を使用
  print(f"written={written}")
  ```

- 市場レジーム判定の実行
  ```
  import duckdb
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect(str(settings.duckdb_path))
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログ用 DB 初期化
  ```
  from kabusys.data.audit import init_audit_db

  conn_audit = init_audit_db("data/audit.duckdb")
  # conn_audit を使って監査ログの INSERT/SELECT を行う
  ```

注意点
- OpenAI 呼び出しは外部 API を利用するため API キーと通信環境が必要です。API呼び出しはリトライとフォールバックを備えていますが、レート制限やコストに注意してください。
- J-Quants API へのアクセスにはリフレッシュトークンが必要です。get_id_token 関数で ID トークンを取得して内部キャッシュを利用します。
- ETL/API呼び出しはネットワークや外部サービスに依存するため、エラーはログに残して部分実行を継続する設計です。
- DuckDB の executemany に関して特定バージョンでの制約（空リスト不可）に配慮した実装が含まれています。

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py                : パッケージ初期化、バージョン定義
  - config.py                  : 環境変数・設定管理（settings）
  - ai/
    - __init__.py
    - news_nlp.py              : ニュースセンチメント（OpenAI）処理（score_news）
    - regime_detector.py      : 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py       : J-Quants API クライアント + DuckDB 保存関数
    - pipeline.py             : ETL 実行ロジック（run_daily_etl 他）
    - etl.py                  : ETL公開インターフェース（ETLResult 再エクスポート）
    - news_collector.py       : RSS 収集・前処理
    - calendar_management.py  : 市場カレンダー管理（営業日判定、update_job）
    - quality.py              : データ品質チェック（check_* / run_all_checks）
    - stats.py                : Zスコア等の統計ユーティリティ
    - audit.py                : 監査ログ（テーブル定義、初期化）
  - research/
    - __init__.py
    - factor_research.py      : モメンタム・バリュー・ボラティリティ等の計算
    - feature_exploration.py  : 将来リターン、IC、統計サマリー、ランク

開発・テストに関するヒント
- 自動.env ロードを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト時など）。
- OpenAI の呼び出しや HTTP を行う箇所はテストしやすいように _call_openai_api / _urlopen 等を差し替えてモックできます。
- DuckDB をインメモリで使う場合は ":memory:" を DB パスに指定してください（init_audit_db 等）。

貢献・拡張
- 新しいデータソースやモデルを追加する場合はデータ取得（jquants_client みたいなクライアント）→保存（save_*）→ETL のワークフローに沿って実装してください。
- AI モジュールは現在 gpt-4o-mini と JSON Mode を想定しています。将来的に別のプロバイダやモデルに差し替え可能なように抽象化を推奨します。

問い合わせ・補足
- README に載せてほしい追加の使用例や CI / デプロイ手順があれば教えてください。必要に応じてサンプル .env.example やコマンドラインツールのドキュメントも作成します。