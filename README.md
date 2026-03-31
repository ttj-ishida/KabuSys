# KabuSys

KabuSys は日本株向けのデータプラットフォームとリサーチ / AI 補助機能を提供する小規模な自動売買系ライブラリです。主に以下を目的とします：

- J-Quants API からのデータ取得（株価・財務・マーケットカレンダー）
- ETL パイプラインとデータ品質チェック（DuckDB ベース）
- ニュースの NLP スコアリング（OpenAI）
- 市場レジーム判定（MA200 + マクロニュース LLM）
- 監査ログ（発注・約定のトレーサビリティ）スキーマ初期化
- 研究用ユーティリティ（ファクター計算・特徴量解析、統計ユーティリティ）

このリポジトリはライブラリとしてインポートし、スクリプトやジョブから各機能を呼び出して運用します。

重要: ルックアヘッドバイアス対策や冪等性を設計方針として重視しています。各モジュールの docstring に設計意図が詳述されています。

---

## 主な機能一覧

- data
  - jquants_client: J-Quants API からのデータ取得・DuckDB への保存（差分・ページネーション・リトライ・レート制御）
  - pipeline: 日次 ETL 実行（market calendar, prices, financials）と品質チェック、ETLResult の返却
  - news_collector: RSS 取得・前処理・raw_news への格納（SSRF・Gzip・XML 安全処理）
  - quality: データ品質チェック（欠損、重複、スパイク、日付不整合）
  - calendar_management: 営業日ロジック（is_trading_day, next_trading_day, prev_trading_day, get_trading_days）と calendar_update_job
  - audit: 監査ログ用 テーブル定義 / 初期化ユーティリティ（init_audit_schema, init_audit_db）
  - stats: zscore_normalize 等の統計ユーティリティ
- ai
  - news_nlp.score_news: ニュースを銘柄別にまとめて LLM に送りセンチメントを ai_scores に書き込む
  - regime_detector.score_regime: ETF(1321) の MA200 乖離とマクロニュース LLM を合成して market_regime テーブルへ書き込む
- research
  - factor_research: モメンタム / ボラティリティ / バリュー等のファクター計算
  - feature_exploration: 将来リターン計算、IC、統計サマリ、ランク変換
- config
  - 環境変数管理（.env 自動ロード、Settings オブジェクト）

---

## セットアップ手順

前提
- Python 3.10 以上（型注釈に `X | None` 構文を使用）
- 仮想環境を使うことを推奨

例:

1. リポジトリをクローン、仮想環境作成・有効化

   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows (PowerShell / CMD)

2. 必要パッケージをインストール（プロジェクトが pyproject.toml を持つ想定なら pip install -e . が使えます）。最低限の依存は以下です：

   pip install duckdb openai defusedxml

   （運用上、さらに logging / slack 用 SDK 等を追加することがあります）

3. 環境変数を設定
   - プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（config モジュールの自動ロード。無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセット）。
   - 必須の環境変数（Settings により参照されるもの）:
     - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD : kabu ステーション接続用パスワード（利用モジュールがある場合）
     - SLACK_BOT_TOKEN : Slack 通知に使う場合
     - SLACK_CHANNEL_ID : Slack 通知先チャンネル
   - 任意/デフォルト:
     - KABUSYS_ENV : development / paper_trading / live（デフォルト development）
     - LOG_LEVEL : DEBUG/INFO/…（デフォルト INFO）
     - KABUSYS_DISABLE_AUTO_ENV_LOAD : 1 で自動 .env ロードを無効化
     - DUCKDB_PATH : デフォルト data/kabusys.duckdb
     - SQLITE_PATH : デフォルト data/monitoring.db
   - OpenAI API を利用する場合は OPENAI_API_KEY を環境変数でセットするか、score_news/score_regime の api_key 引数で渡します。

4. データベース用ディレクトリ作成（必要なら）

   mkdir -p data

---

## 使い方（基本例）

以下はライブラリを直接呼び出す簡単な例です。実行は任意のスクリプトや cron / Airflow 等から行ってください。

- 日次 ETL を実行する

  from datetime import date
  import duckdb
  from kabusys.data.pipeline import run_daily_etl
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())

- ニュース NLP スコアを計算して ai_scores に書き込む

  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  # OPENAI_API_KEY が環境変数にあれば api_key 引数は省略可能
  n_written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"wrote {n_written} ai scores")

- 市場レジーム判定を行う

  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect(str(settings.duckdb_path))
  score_regime(conn, target_date=date(2026, 3, 20))

- 監査ログ DB を初期化する（監査専用 DB を作る）

  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  # これで audit テーブル群が作成されます

- ETL と品質チェック結果の確認
  run_daily_etl の戻り値は ETLResult。to_dict() で内容をログや監査に保存できます。

注意点:
- OpenAI 呼び出しのリトライやフォールバックは各モジュール内で実装されています。API 失敗時はゼロにフォールバックして継続する設計方針の箇所が多くあります（フェイルセーフ）。
- DuckDB のバージョン差異に起因する挙動（executemany の空リストなど）に配慮した実装になっています。

---

## 主要モジュール / 関数リファレンス（抜粋）

- kabusys.config.settings
  - settings.jquants_refresh_token / settings.duckdb_path / settings.env / settings.is_live など

- kabusys.data.jquants_client
  - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - save_daily_quotes, save_financial_statements, save_market_calendar
  - get_id_token

- kabusys.data.pipeline
  - run_daily_etl(conn, target_date=None, id_token=None, run_quality_checks=True, ...)

- kabusys.ai.news_nlp
  - score_news(conn, target_date, api_key=None)

- kabusys.ai.regime_detector
  - score_regime(conn, target_date, api_key=None)

- kabusys.data.audit
  - init_audit_schema(conn, transactional=False)
  - init_audit_db(db_path)

- kabusys.research
  - calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary, rank
  - zscore_normalize は kabusys.data.stats にて提供

---

## ディレクトリ構成

src/kabusys/
- __init__.py
- config.py                 — 環境変数・設定管理
- ai/
  - __init__.py
  - news_nlp.py             — ニュース NLP（OpenAI）による銘柄別スコアリング
  - regime_detector.py      — 市場レジーム判定（MA200 + マクロニュース）
- data/
  - __init__.py
  - jquants_client.py       — J-Quants API クライアント、DuckDB 保存関数
  - pipeline.py             — ETL パイプラインとユーティリティ（run_daily_etl 等）
  - news_collector.py       — RSS ニュース収集（SSRF 対策、XML 安全処理）
  - calendar_management.py  — 市場カレンダー管理、営業日判定ロジック
  - quality.py              — データ品質チェック（欠損・重複・スパイク・日付整合性）
  - stats.py                — 統計ユーティリティ（zscore_normalize）
  - audit.py                — 監査ログスキーマ定義・初期化
  - pipeline.py             — ETL の ETLResult 再エクスポート（注意: ファイルに同名が複数ないか確認）
  - etl.py                  — ETL インターフェース（ETLResult 再エクスポート）
- research/
  - __init__.py
  - factor_research.py      — ファクター計算（momentum, value, volatility）
  - feature_exploration.py  — 将来リターン / IC / 統計サマリ等

その他:
- pyproject.toml / .git/ 等（プロジェクトルート検出に使用）

---

## 運用上の注意 / ベストプラクティス

- 設定/秘匿情報は .env（または CI シークレット）で管理し、リポジトリに含めないこと。
- OpenAI や J-Quants の API キーは適切にローテーション・最小権限で管理すること。
- DuckDB ファイルは定期的にバックアップするか、監査ログは別 DB に分離する（audit.init_audit_db を利用）。
- ETL はジョブスケジューラ（cron / Airflow 等）で定期実行し、ETLResult を監査・アラート基盤に送ることを推奨。
- 本コードは Look-ahead Bias を避ける設計になっていますが、バックテストで利用する際はデータの取得日時（fetched_at）や market_calendar の取得タイミングに注意してください。

---

## 問い合わせ・貢献

- バグ報告や改善提案は Issue を通してください。
- コードの変更は PR を作成し、ユニットテスト・簡単な動作確認を添えてください（本リポジトリにテストフレームワークの設定がない場合は説明を付けてください）。

---

この README はコード内の docstring / コメントをもとに作成しています。各モジュールに詳細な使用例や追加の運用手順を追記することを推奨します。