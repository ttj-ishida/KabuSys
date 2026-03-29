# KabuSys

日本株向けの自動売買／データ基盤ライブラリです。  
データ収集（J-Quants）、ETL、データ品質チェック、ニュースセンチメント（OpenAI）、市場レジーム判定、監査ログ（発注→約定のトレーサビリティ）や研究用ファクター計算などを提供します。

主なユースケース:
- 日次 ETL による株価・財務・カレンダーの差分取得と DuckDB への保存
- ニュースを LLM（gpt-4o-mini）でセンチメント解析して銘柄別スコア化
- ETF とマクロニュースを合成した市場レジーム判定
- 研究用ファクター計算（モメンタム／バリュー／ボラティリティ等）
- 監査ログ（signal → order_request → execution）のスキーマ初期化

---

## 機能一覧

- データ収集・保存
  - J-Quants から株価（日足）、財務、上場銘柄情報、JPXカレンダーを取得（`data.jquants_client`）
  - DuckDB へ冪等保存（ON CONFLICT DO UPDATE）
- ETL パイプライン（差分更新 + 品質チェック）
  - 日次 ETL（カレンダー先読み・バックフィル対応）（`data.pipeline.run_daily_etl`）
  - 個別 ETL ジョブ（prices / financials / calendar）
- データ品質チェック（欠損・重複・スパイク・日付不整合）（`data.quality`）
- ニュース収集（RSS）と前処理（SSRF対策・トラッキング除去）（`data.news_collector`）
- ニュース NLP（OpenAI）による銘柄センチメントスコア付与（`ai.news_nlp.score_news`）
- 市場レジーム判定（ETFのMA乖離 + マクロニュースセンチメントの合成）（`ai.regime_detector.score_regime`）
- 研究用モジュール（ファクター計算・特徴量解析・IC計算）（`research`）
- 監査ログスキーマ初期化（監査テーブル・インデックス生成、専用 DB 初期化ユーティリティ）（`data.audit`）
- 設定管理（.env 自動読み込み／必須 env チェック）（`config.py`）

---

## 動作要件（推奨）

- Python 3.10+
- 必要ライブラリ（最低限）
  - duckdb
  - openai
  - defusedxml
  - その他標準ライブラリ（urllib 等）
- ネットワークアクセス: J-Quants API / OpenAI API / RSS フィード

（プロジェクトに requirements.txt がある場合はそちらを使用してください）

---

## セットアップ手順

1. リポジトリをクローン（例）
   ```bash
   git clone <repository-url>
   cd <repository>
   ```

2. Python 仮想環境を作成・有効化
   ```bash
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 必要パッケージをインストール
   - 直接主要パッケージをインストールする例:
     ```bash
     pip install duckdb openai defusedxml
     ```
   - 開発用や他の依存がある場合はプロジェクトの requirements を利用してください。

4. 環境変数設定
   - プロジェクトルートに `.env` を置くと自動読み込みされます（`config.py` の自動ロード機能）。自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。
   - 必須環境変数（例）
     - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
     - SLACK_BOT_TOKEN: Slack 通知を使う場合
     - SLACK_CHANNEL_ID: Slack 通知先チャンネル
     - KABU_API_PASSWORD: kabu API 用パスワード（注文連携がある場合）
   - 任意（デフォルト値あり）
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL（デフォルト: INFO）
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH: 監視用 sqlite ファイルパス（デフォルト: data/monitoring.db）
     - OPENAI_API_KEY: OpenAI API キー（score_news / score_regime の引数で渡しても可）

   - .env の例
     ```
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     OPENAI_API_KEY=sk-...
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     DUCKDB_PATH=data/kabusys.duckdb
     ```

5. DB 初期化（必要に応じて）
   - 監査ログ用 DuckDB を初期化:
     ```python
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")
     ```
   - 通常、スキーマやテーブルは ETL 実行や初期化ユーティリティ側で作成されます。プロジェクトにスキーマ初期化関数があれば利用してください。

---

## 使い方（簡単な例）

以下は Python REPL やスクリプトから利用する基本例です。日付操作は date オブジェクトを使います（内部で date.today() を直接参照しない実装方針に従っています）。

- DuckDB 接続を作成して日次 ETL を実行する
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")  # settings.duckdb_path を使うことも可能
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメントを算出して ai_scores に保存する
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  written = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
  print("scored:", written)
  ```

- 市場レジームを算出して market_regime に保存する
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")
  ```

- 研究用ファクター計算（例: モメンタム）
  ```python
  from kabusys.research.factor_research import calc_momentum
  import duckdb
  from datetime import date

  conn = duckdb.connect("data/kabusys.duckdb")
  recs = calc_momentum(conn, target_date=date(2026, 3, 20))
  print(len(recs))
  ```

- 監査ログスキーマ初期化（既存接続に追加）
  ```python
  from kabusys.data.audit import init_audit_schema
  import duckdb

  conn = duckdb.connect("data/kabusys.duckdb")
  init_audit_schema(conn, transactional=True)
  ```

注意:
- OpenAI API を使う関数（score_news, score_regime）は api_key を引数で与えるか、環境変数 `OPENAI_API_KEY` を設定してください。
- テスト時は OpenAI 呼び出し内の `_call_openai_api` をモックして外部 API 依存を切り離せます（コード中にその意図を示す記述があります）。

---

## 主要モジュールとディレクトリ構成

（ソースツリーは `src/kabusys` 配下を想定）

- src/kabusys/
  - __init__.py
    - パッケージのバージョンやエクスポート設定
  - config.py
    - .env / 環境変数の自動読み込み、settings オブジェクト（必須 env の検査）
  - ai/
    - __init__.py
    - news_nlp.py
      - ニュースをまとめて LLM に投げ銘柄別スコアを ai_scores に保存（バッチ処理・リトライ含む）
    - regime_detector.py
      - ETF(1321)のMA乖離とマクロニュースセンチメントを合成して market_regime に保存
  - data/
    - __init__.py
    - jquants_client.py
      - J-Quants API クライアント（認証・リトライ・レート制御・DuckDB 保存関数）
    - pipeline.py
      - ETL パイプライン（run_daily_etl 等）と ETLResult
    - etl.py
      - ETL の公開インターフェース（ETLResult の再エクスポート）
    - news_collector.py
      - RSS 取得・前処理・raw_news へ冪等保存（SSRF/サイズ制限対応）
    - calendar_management.py
      - JPX カレンダー管理・営業日判定ユーティリティ
    - quality.py
      - データ品質チェック（欠損・重複・スパイク・日付不整合）
    - stats.py
      - 共通統計ユーティリティ（zscore_normalize）
    - audit.py
      - 監査ログスキーマ定義・初期化（signal_events / order_requests / executions）
  - research/
    - __init__.py
    - factor_research.py
      - Momentum / Value / Volatility 等のファクター計算
    - feature_exploration.py
      - 将来リターン計算、IC、統計サマリー、rank 等

---

## 開発・運用上の注意点

- 環境切替:
  - KABUSYS_ENV = development | paper_trading | live
  - settings.is_live / is_paper / is_dev を参照して挙動を切替え可能
- セキュリティ:
  - news_collector は SSRF 対策やレスポンスサイズ制限を実装
  - J-Quants クライアントは 401 発生時のトークン自動リフレッシュとリトライを実装
- LLM 呼び出し:
  - OpenAI の呼び出しはリトライ・バックオフ・レスポンスバリデーションが組み込まれています
  - テスト時は内部の _call_openai_api をモックしてください
- Look-ahead バイアス防止:
  - モジュール群は date.today() の直接参照を避け、target_date を引数で与える設計が基本
- ロギング:
  - LOG_LEVEL で出力レベルを制御（settings.log_level）
- トランザクション:
  - ETL/スコア書き込みは冪等性・トランザクション管理を意識して実装（BEGIN / DELETE / INSERT / COMMIT）

---

## よくある質問（FAQ）

Q: .env 自動読み込みを無効化したい  
A: 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` をセットしてください。

Q: OpenAI のレスポンスが不正な場合はどうなる？  
A: モジュールはフェイルセーフでスコアを 0.0 にフォールバックしたり、そのチャンクをスキップして続行します。例外を投げない設計箇所が多くあります（ログは出力されます）。

Q: DuckDB のスキーマはどこで作成する？  
A: audit 用スキーマは `data.audit.init_audit_schema`、その他スキーマ初期化が必要な場合はプロジェクトのスキーマ初期化ユーティリティを参照してください（本リポジトリの他ファイルでスキーマ作成ロジックを提供している想定）。

---

必要であれば、README を拡張して以下を追加できます:
- Docker イメージや docker-compose の例
- より詳しい API リファレンス（各関数の引数・戻り値例）
- CI / テストの実行方法（ユニットテスト・モック例）
- 公開されるテーブル定義（DDL）一覧

ご希望があれば追記します。