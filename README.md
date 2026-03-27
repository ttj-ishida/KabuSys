# KabuSys

日本株向けのデータプラットフォーム兼自動売買補助ライブラリです。  
J-Quants や RSS、OpenAI を組み合わせてデータ取得・前処理・品質チェック・AIセンチメント解析・ファクター計算・監査ログを行うことを目的としています。  
モジュール設計により、ETL / 研究（Research） / AI / 監査（Audit） / カレンダー管理 を独立して利用できます。

主な用途例:
- 日次 ETL による株価・財務・カレンダーの差分取得と DuckDB への保存
- ニュースの収集と LLM による銘柄センチメント算出（ai_score）
- マクロ＋テクニカルを合成した市場レジーム判定
- ファクター計算・IC 分析などのリサーチ処理
- 発注前後のトレーサビリティを確保する監査ログスキーマの初期化

---

## 機能一覧

- データ取得・保存
  - J-Quants API クライアント（株価日足 / 財務 / マーケットカレンダー / 上場銘柄情報）
  - 差分 ETL（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - DuckDB への冪等保存（ON CONFLICT DO UPDATE を利用）
- ニュース処理
  - RSS 収集（SSRF対策・トラッキング除去・サイズ制限）
  - 銘柄紐付けと raw_news 保存
- AI（OpenAI）連携
  - 銘柄別ニュースのセンチメント算出（news_nlp.score_news）
  - ETF とマクロ記事を組み合わせた市場レジーム判定（regime_detector.score_regime）
  - API 呼び出しに対するリトライ・フォールバック処理を実装
- 研究（Research）
  - モメンタム / ボラティリティ / バリュー等ファクター算出
  - 将来リターン計算・IC（Spearman）・Zスコア正規化・統計サマリ
- データ品質管理
  - 欠損 / スパイク / 重複 / 日付不整合チェック（quality.run_all_checks）
- マーケットカレンダー管理（JPX）
  - 営業日判定、次/前営業日、営業日リスト取得、夜間更新ジョブ
- 監査ログ（Audit）
  - signal_events / order_requests / executions テーブル定義と初期化ユーティリティ
  - 監査 DB 初期化（init_audit_db）で UTC タイムスタンプを固定

---

## 動作要件

- Python 3.10+
- ライブラリ例（最低限）:
  - duckdb
  - openai
  - defusedxml

※ 他に標準ライブラリの urllib 等を使用します。実運用時は kakabu/kabuステーション 接続など別途準備が必要です。

---

## セットアップ手順

1. リポジトリをクローン（またはパッケージをインストール）
   - 開発環境で編集する場合:
     ```
     git clone <repo-url>
     cd <repo>
     pip install -e .
     ```
   - 最低限の依存を手動で入れる場合:
     ```
     pip install duckdb openai defusedxml
     ```

2. Python バージョンを満たすことを確認してください（3.10+）。

3. 環境変数を設定
   - .env ファイルをプロジェクトルートに置くと自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
   - 必須の環境変数（主なもの）:
     - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
     - SLACK_BOT_TOKEN : Slack 通知を使う場合の Bot トークン
     - SLACK_CHANNEL_ID : Slack 通知先チャンネル ID
     - KABU_API_PASSWORD : kabuステーション API パスワード（発注系を使う場合）
     - OPENAI_API_KEY : OpenAI を使う機能（score_news, score_regime）を使う場合（関数引数からも渡せる）
   - 任意 / デフォルト値あり:
     - KABUSYS_ENV : development / paper_trading / live （デフォルト: development）
     - LOG_LEVEL : DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）
     - KABU_API_BASE_URL : kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
     - DUCKDB_PATH : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH : SQLite（監視用）パス（デフォルト: data/monitoring.db）

   - .env の例:
     ```
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     OPENAI_API_KEY=sk-...
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     KABU_API_PASSWORD=your_password
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     ```

4. データベース用ディレクトリ作成
   - DUCKDB_PATH の親ディレクトリを作成しておくと安全です（init 関数は自動生成を行う箇所もありますが、念のため）。
     ```
     mkdir -p data
     ```

---

## 使い方（主要な関数・実行例）

下記は Python REPL やスクリプトからの呼び出し例です。

- DuckDB 接続を作成して日次 ETL を実行する
  ```python
  import duckdb
  from datetime import date
  from kabusys.config import settings
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメント（銘柄別 ai_score）を算出して ai_scores テーブルへ書き込む
  ```python
  import duckdb
  from datetime import date
  from kabusys.config import settings
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect(str(settings.duckdb_path))
  # OPENAI_API_KEY は環境変数に設定済みか、api_key 引数で渡す
  n_written = score_news(conn, target_date=date(2026, 3, 20))
  print("written:", n_written)
  ```

- 市場レジームを判定して market_regime テーブルへ書き込む
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログ用の DuckDB を初期化する
  ```python
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")  # ディレクトリがなければ作成されます
  ```

- マーケットカレンダーを更新（夜間ジョブの一部）:
  ```python
  from kabusys.data.calendar_management import calendar_update_job
  saved = calendar_update_job(conn)
  print("calendar saved:", saved)
  ```

注意:
- AI を使う機能（score_news, score_regime）は OpenAI の API キーが必要です。関数引数に api_key を渡すか、環境変数 OPENAI_API_KEY を設定してください。
- ETL 等は外部 API（J-Quants）へリクエストを行うため、J-Quants の認証情報が必要です（JQUANTS_REFRESH_TOKEN）。

---

## 主要ディレクトリ構成（抜粋）

プロジェクトの src/kabusys 以下の主な構成:

- kabusys/
  - __init__.py
  - config.py
    - 環境変数読み込み・Settings（J-Quants / kabu / Slack / DB / システム設定）
  - ai/
    - __init__.py
    - news_nlp.py        -> 銘柄別ニュースセンチメント算出（score_news）
    - regime_detector.py -> ETF MA + マクロニュースで市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py  -> J-Quants API クライアント + DuckDB 保存関数
    - pipeline.py        -> ETL パイプライン（run_daily_etl 等）および ETLResult
    - calendar_management.py -> マーケットカレンダー管理
    - news_collector.py  -> RSS 取得・前処理・raw_news 保存
    - quality.py         -> データ品質チェック（欠損/スパイク/重複/日付不整合）
    - stats.py           -> zscore 正規化など統計ユーティリティ
    - audit.py           -> 監査ログスキーマ定義・初期化ユーティリティ
    - pipeline.py (ETL の中心)
  - research/
    - __init__.py
    - factor_research.py -> Momentum/Volatility/Value のファクター計算
    - feature_exploration.py -> forward returns / IC / summary / rank
  - (その他)
    - execution / monitoring などの名前空間が __all__ 等で公開される想定

実際のファイル構成はリポジトリルートにある src ディレクトリ配下を参照してください。

---

## 設定・環境変数一覧（抜粋）

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants リフレッシュトークン
- OPENAI_API_KEY (必須 for AI) — OpenAI API キー（score_news / score_regime）
- KABU_API_PASSWORD (必須 for kabu) — kabu API（発注）用パスワード
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN, SLACK_CHANNEL_ID — Slack 通知に使用
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite（監視 DB）パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — ログレベル（デフォルト: INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env ロードを無効化（値を設定すると無効）

---

## 開発・貢献

- 自動テストや CI の設定はリポジトリ側に従ってください（本 README では省略）。
- モジュール内のプライベート関数はテスト時にモックしやすいよう設計されています（例: OpenAI 呼び出し関数の差し替え）。
- 実運用に移す場合は credentials（API キー等）の管理、rate limiting、監査ログの保全、発注系の安全設計を十分に行ってください。

---

## トラブルシューティング（よくある問題）

- ValueError: 環境変数が未設定
  - .env を作成するか環境変数を設定してください（config.Settings._require がチェックします）。
- DuckDB のパスがない / ディレクトリが作れない
  - DUCKDB_PATH の親ディレクトリを手動で作成するか、init_audit_db が自動で作成する処理を利用してください。
- OpenAI への接続エラー / RateLimit
  - OPENAI_API_KEY の有無を確認し、API 呼び出しのリトライログ等を参照してください。API 側の制限により一時失敗することが想定され、ライブラリはフォールバック（0.0）を用います。

---

必要であれば、README にコマンドラインツールの使い方、CI 設定、より詳細な .env.example、テーブルスキーマ一覧なども追記できます。どの部分を詳細化したいか教えてください。