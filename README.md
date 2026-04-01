# KabuSys

日本株向けのデータプラットフォーム兼自動売買リサーチ／実行基盤のライブラリです。  
DuckDB をデータ層に使い、J-Quants からマーケットデータを取得して ETL → 品質チェック → リサーチ（ファクター計算・特徴量解析）→ ニュース NLP / レジーム判定 → 監査ログ（発注/約定トレーサビリティ）までを想定したモジュール群を提供します。

## 主な機能
- J-Quants API クライアント
  - 株価日足（OHLCV）、財務データ、JPX カレンダーの差分取得（ページネーション対応）
  - トークン自動リフレッシュ、レートリミット・リトライ実装
- ETL パイプライン
  - 差分取得、DuckDB への冪等保存（ON CONFLICT DO UPDATE）、品質チェック実行
  - run_daily_etl による日次一括処理
- データ品質チェック
  - 欠損、スパイク、重複、日付不整合の検出（QualityIssue を返す）
- ニュース収集・NLP（OpenAI）
  - RSS 収集（SSRF 対策、トラッキングパラメータ除去、gzip 対応）
  - ニュースを銘柄ごとにまとめ、OpenAI（gpt-4o-mini）でセンチメントを算出して ai_scores に保存（score_news）
  - レジーム判定（ETF 1321 の MA200 乖離 + マクロニュースの LLM センチメントを合成）→ market_regime に保存（score_regime）
- リサーチユーティリティ
  - モメンタム / ボラティリティ / バリュー等のファクター計算（prices_daily / raw_financials を参照）
  - 将来リターン計算、IC（スピアマン）計算、Z-score 正規化など
- 監査ログ（audit）
  - signal_events / order_requests / executions の DDL 定義と初期化ユーティリティ（init_audit_schema / init_audit_db）
  - 発注→約定までのトレーサビリティ設計

## 依存関係（主なもの）
- Python 3.10+
- duckdb
- openai
- defusedxml
- （標準ライブラリのみで実装されている機能も多いです）

必要に応じて pyproject.toml / requirements.txt を確認してください。

## セットアップ手順

1. Python 3.10 以上を準備します。

2. リポジトリをクローンし、プロジェクトルートへ移動します。

3. 開発環境／インストール：
   - editable インストール（開発時推奨）
     ```bash
     pip install -e .
     ```
   - または通常インストール：
     ```bash
     pip install .
     ```

4. 必要なパッケージをインストール（例）:
   ```bash
   pip install duckdb openai defusedxml
   ```

5. 環境変数設定
   - プロジェクトルートに `.env` または `.env.local` を作成すると自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロードを無効化します）。
   - 最低限必要な環境変数（例）:
     ```
     JQUANTS_REFRESH_TOKEN=<your_jquants_refresh_token>
     OPENAI_API_KEY=<your_openai_api_key>
     KABU_API_PASSWORD=<password_for_kabu_api>
     SLACK_BOT_TOKEN=<slack_bot_token>
     SLACK_CHANNEL_ID=<slack_channel_id>
     ```
   - 任意（デフォルト値あり）:
     ```
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db
     PID_FILE_PATH=data/execution.pid
     LOG_LEVEL=INFO
     KABUSYS_ENV=development  # development | paper_trading | live
     ```

6. DuckDB データベースや監査用 DB のディレクトリを用意する（save 関数などは親ディレクトリがない場合に自動作成する箇所がありますが、念のため）:
   ```bash
   mkdir -p data
   ```

## 使い方（主要な例）

以下はライブラリ関数を直接呼ぶシンプルな例です。実運用ではロギング設定やエラーハンドリング、ジョブスケジューラ（cron / systemd timer / Airflow 等）を組み合わせてください。

- DuckDB 接続を作って日次 ETL を実行する
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメントをスコアして ai_scores に保存
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  count = score_news(conn, target_date=date(2026, 3, 20))
  print(f"scored {count} codes")
  ```

- 市場レジーム判定を実行
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログスキーマを初期化（監査専用 DB 作成例）
  ```python
  from kabusys.data.audit import init_audit_db

  audit_conn = init_audit_db("data/audit.duckdb")
  # audit_conn を使って監査テーブルにアクセスできます
  ```

- ファクター計算（例: momentum）
  ```python
  from kabusys.research.factor_research import calc_momentum
  import duckdb
  from datetime import date

  conn = duckdb.connect("data/kabusys.duckdb")
  records = calc_momentum(conn, target_date=date(2026,3,20))
  # records は各銘柄の dict のリスト
  ```

注意点:
- OpenAI を呼ぶ処理（score_news / regime_detector）は API キーが必要です。関数引数で api_key を渡すか、環境変数 OPENAI_API_KEY を設定してください。
- ETL / API 呼び出しはネットワーク／認証エラーや API レート制限に対するリトライロジックがありますが、十分なエラーハンドリングをアプリ側でも行ってください。
- ライブラリの多くは DuckDB 上のテーブル（raw_prices, raw_financials, market_calendar, raw_news, news_symbols, ai_scores, market_regime 等）を期待します。スキーマは各モジュールの保存・DDL 関数を参照してください。

## 自動 .env 読み込み
- `kabusys.config` モジュールはプロジェクトルート（.git または pyproject.toml のある親ディレクトリ）を探索し、`.env` → `.env.local` の順で環境変数を自動読み込みします。
- 自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- 必須の環境変数が未設定だと Settings プロパティアクセス時に ValueError が発生します（例: JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, KABU_API_PASSWORD）。

## 主要なディレクトリ構成（src/kabusys）
- kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py          — ニュース NLP（OpenAI を使ったセンチメント評価）
    - regime_detector.py   — マーケットレジーム判定（ETF 1321 MA200 + マクロニュース）
  - data/
    - __init__.py
    - jquants_client.py    — J-Quants API クライアント（fetch / save）
    - pipeline.py          — ETL パイプライン（run_daily_etl 等）
    - etl.py               — ETL 結果クラスの再エクスポート
    - calendar_management.py — マーケットカレンダー管理（営業日判定等）
    - news_collector.py    — RSS 収集モジュール（SSRF 対策等）
    - quality.py           — データ品質チェック
    - stats.py             — 共通統計ユーティリティ（zscore_normalize）
    - audit.py             — 監査ログ（DDL / 初期化）
  - research/
    - __init__.py
    - factor_research.py   — モメンタム/ボラティリティ/バリュー計算
    - feature_exploration.py — 将来リターン / IC / 統計サマリー
  - ai/、data/、research/ 内の関数は相互に利用されていますが、設計時にルックアヘッドバイアスやモジュール結合に配慮した実装になっています。

## 開発・テスト時の注意
- 多くの関数は外部 API（J-Quants / OpenAI / RSS）に依存するため、ユニットテストでは API 呼び出し部分をモックすることを想定しています（コード中にも patch しやすい内部ラッパー関数が用意されています）。
- DuckDB のバージョン差異に起因する挙動（executemany の空リスト扱いなど）に注意して実装されていますが、運用環境の DuckDB バージョンでの振る舞いを確認してください。
- 本ライブラリはバックテストや本番注文ロジックを完全に含むわけではなく、ETL・データ管理・リサーチ・監査ログを提供する基盤です。実際の発注実装（証券会社 API 統合・リスク管理）は別レイヤで実装してください。

---

不明点や README に追記したい操作（例: 実行スクリプト、Docker 化、CI 設定など）があれば教えてください。必要に応じて README を拡張します。