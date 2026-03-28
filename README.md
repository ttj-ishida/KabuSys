# KabuSys

日本株向けのデータパイプライン・リサーチ・AI支援・監査付き自動売買基盤（ライブラリ）

このリポジトリは、J-Quants / kabuステーション 等を用いた日本株のデータETL、ファクター計算、ニュースNLP（LLM）評価、市場レジーム判定、監査ログ管理などを行うためのモジュール群をまとめたライブラリです。

主な用途例:
- J-Quants から株価/財務/カレンダーを差分取得して DuckDB に格納する ETL
- RSS 収集→ニュースの前処理→LLM による銘柄センチメントの算出（ai_scores）
- ETF とマクロニュースを組み合わせた市場レジーム判定
- ファクター算出・統計分析（Research）
- 監査ログ（signal, order_request, executions）用スキーマの初期化・運用

要求環境（目安）
- Python 3.10 以上（型注釈で | 演算子を使用）
- 必要外部ライブラリ（例）
  - duckdb
  - openai
  - defusedxml

（プロジェクトの packaging/requirements に従ってインストールしてください）

## 機能一覧

- data
  - ETL パイプライン（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - J-Quants API クライアント（ページネーション・リトライ・トークン自動更新・レート制御）
  - 市場カレンダー管理（is_trading_day / next_trading_day / prev_trading_day / get_trading_days）
  - ニュース収集（RSS 取り込み、SSRF 対策、前処理、raw_news への保存補助）
  - データ品質チェック（欠損、重複、スパイク、日付不整合）
  - 監査ログ初期化（監査用テーブル・インデックスの作成、監査DB初期化ユーティリティ）
  - 汎用統計ユーティリティ（zscore_normalize）
- ai
  - ニュース NLP（gpt-4o-mini を用いた銘柄ごとのセンチメント算出: score_news）
  - 市場レジーム判定（ETF 1321 の MA とマクロニュースを組み合わせる: score_regime）
  - 各種 OpenAI 呼び出しはリトライ・フォールバック設計（失敗時は安全なデフォルトを利用）
- research
  - ファクター計算（momentum / value / volatility）
  - 将来リターン計算、IC（スピアマン）計算、統計サマリー、ランク化ユーティリティ

## セットアップ手順

1. リポジトリをクローンしてパッケージをインストール（開発モード推奨）
   ```
   git clone <repo-url>
   cd <repo-dir>
   pip install -e .
   ```
   もしくは requirements.txt がある場合はそれに従ってください（duckdb, openai, defusedxml 等）。

2. Python バージョン確認（3.10+ 推奨）

3. 環境変数の設定
   - プロジェクトルートの .env / .env.local を自動で読み込みます（OS 環境変数優先）。
   - 自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（主にテスト用）。
   - 必須の環境変数（一例）
     - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD: kabuステーション API のパスワード
     - SLACK_BOT_TOKEN: Slack 通知に使用する Bot トークン
     - SLACK_CHANNEL_ID: Slack チャンネル ID
     - OPENAI_API_KEY: OpenAI 呼び出しに使用する API キー（score_news / score_regime 等）
   - 任意の環境変数
     - KABUSYS_ENV: development / paper_trading / live（デフォルト development）
     - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト INFO）
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH: 監視用 SQLite パス（デフォルト data/monitoring.db）

   .env の書き方は一般的な KEY=VALUE の形式のほか `export KEY=VALUE`、クォートやインラインコメント処理に対応しています。

4. データベース初期化（監査ログ等）
   - 監査DB（例: DuckDB ファイル）を初期化するには:
     ```python
     from kabusys.data.audit import init_audit_db
     from kabusys.config import settings

     conn = init_audit_db(settings.duckdb_path)
     ```
   - その他のスキーマはプロジェクトのスキーマ初期化関数（存在する場合）を利用してください。

## 使い方（主な API & 実行例）

以下は Python REPL / スクリプトでの利用例です。DuckDB 接続は duckdb.connect(<path>) を使用します。

- 日次 ETL の実行
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメント（score_news）
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  # api_key を明示するか環境変数 OPENAI_API_KEY を設定
  written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
  print(f"書き込んだ銘柄数: {written}")
  ```

- 市場レジーム判定（score_regime）
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査DB 初期化（既述）
  ```python
  from kabusys.data.audit import init_audit_db
  from kabusys.config import settings

  conn = init_audit_db(settings.duckdb_path)
  ```

- 市場カレンダー判定ユーティリティ例
  ```python
  from kabusys.data.calendar_management import is_trading_day, next_trading_day
  import duckdb
  from datetime import date

  conn = duckdb.connect("data/kabusys.duckdb")
  print(is_trading_day(conn, date(2026,3,20)))
  print(next_trading_day(conn, date(2026,3,20)))
  ```

注意点・設計上の挙動
- ETL や AI モジュールはルックアヘッドバイアスを避ける設計（内部で date.today() を参照しない、対象日未満/以前のデータのみを使用）です。バックテスト等での利用時は注意してください。
- OpenAI 呼び出しはリトライとフォールバックを行い、失敗時はゼロ等の安全値を採用します（例: macro_sentiment=0.0）。
- J-Quants クライアントは rate limit（120 req/min）やトークンリフレッシュを扱います。

## 推奨ワークフロー（運用例）

1. .env をプロジェクトルートに作成（JQUANTS_REFRESH_TOKEN, OPENAI_API_KEY 等を設定）
2. cron / ワーカーで毎晩 run_daily_etl を呼び出してデータを更新
3. 毎朝 score_news を実行して ai_scores を更新
4. market_regime を定期的に算出（score_regime）
5. signal → order_request → executions に至る流れは監査テーブルに残す

## ディレクトリ構成（抜粋）

- src/kabusys/
  - __init__.py (パッケージ定義、バージョン)
  - config.py
    - 環境変数・設定管理（.env 自動ロード、Settings クラス）
  - ai/
    - __init__.py
    - news_nlp.py         : ニュースの LLM センチメント算出（score_news）
    - regime_detector.py  : ETF とマクロニュースを合成した市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py   : J-Quants API クライアント（fetch / save / レート制御）
    - pipeline.py         : ETL パイプライン実装（run_daily_etl など）
    - calendar_management.py : 市場カレンダー管理
    - news_collector.py   : RSS 収集・前処理（SSRF 対策等）
    - quality.py          : データ品質チェック（欠損・重複・スパイク・日付不整合）
    - stats.py            : 汎用統計ユーティリティ（zscore_normalize）
    - etl.py              : ETL 結果クラス公開（ETLResult）
    - audit.py            : 監査ログの DDL / 初期化ユーティリティ
  - research/
    - __init__.py
    - factor_research.py  : モメンタム/ボラティリティ/バリュー等のファクター計算
    - feature_exploration.py : 将来リターン / IC / 統計サマリー等

（コメント・ドキュメントは各モジュール内に詳細に記載されています）

## 開発・テストに関する補足

- config._parse_env_line は .env の複雑な書式（export, クォート内エスケープ, コメント）に対応しています。
- news_collector は defusedxml による XML 解析、SSRF 防止のためのホスト検証、受信サイズ制限、gzip 解凍の保護などセキュリティ考慮がなされています。
- OpenAI の呼び出しは各モジュールで独立して実装されており、テスト時は関数単位でモック差し替えが可能です（例: unittest.mock.patch で _call_openai_api を差し替え）。

---

問題や追加したいドキュメント、サンプルスクリプト（cron やワーカー用）などがあれば指示してください。README に追記します。