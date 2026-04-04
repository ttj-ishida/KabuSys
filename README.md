# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ。  
ETL（J-Quants）、ニュース収集・NLP（OpenAI）、ファクター計算、監査ログ、マーケットカレンダー管理などを備え、バックテスト・運用・研究ワークフローを支援します。

※この README は src/kabusys のコードベースに基づいて作成しています。

---

## 概要

KabuSys は以下の機能をモジュール単位で提供します。

- J-Quants API を用いた株価・財務・マーケットカレンダー等の差分取得（ETL）
- DuckDB を用いたローカルデータ保存と冪等保存ルール
- ニュース収集（RSS）と前処理、記事から銘柄への紐付け
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント解析（銘柄ごとの ai_score とマクロセンチメント）
- ETF（1321）の MA200 乖離とマクロセンチメントを合成した「市場レジーム判定」
- ファクター計算（モメンタム / ボラティリティ / バリュー 等）と特徴量解析ユーティリティ
- データ品質チェック（欠損、スパイク、重複、日付不整合）
- 監査ログ（signal → order_request → execution）用テーブル定義と初期化ユーティリティ
- 設定管理（.env 自動読み込み、環境変数）

設計上の特徴：
- ルックアヘッドバイアスを防ぐ実装（内部で datetime.today()/date.today() を直接参照しない等）
- 冪等性（DB 保存は ON CONFLICT DO UPDATE / DO NOTHING）
- 外部API呼び出しに対するリトライ / バックオフ / レート制御
- セキュリティ考慮（RSS の SSRF対策、defusedxml 利用）

---

## 主な機能一覧

- data
  - ETL パイプライン（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - J-Quants クライアント（fetch / save 関数、get_id_token）
  - カレンダー管理（is_trading_day, next_trading_day, prev_trading_day, calendar_update_job）
  - ニュース収集（fetch_rss, URL 正規化、前処理）
  - データ品質チェック（check_missing_data, check_spike, check_duplicates, check_date_consistency）
  - 監査ログ初期化（init_audit_schema / init_audit_db）
  - 汎用統計（zscore_normalize）
- ai
  - ニュース NLP（score_news）: 銘柄別センチメントを ai_scores に書き込み
  - レジーム判定（score_regime）: ETF 1321 の MA とマクロセンチメントを合成して market_regime に書き込み
- research
  - ファクター計算（calc_momentum, calc_volatility, calc_value）
  - 特徴量探索（calc_forward_returns, calc_ic, factor_summary, rank）
- config
  - 環境変数の自動読み込み（.env / .env.local）と Settings オブジェクト（settings）による取得

---

## 要求環境 (推奨)

- Python 3.10+
- 必須外部パッケージ例（実行する機能による）:
  - duckdb
  - openai
  - defusedxml

（プロジェクトの pyproject.toml / requirements.txt があればそちらを参照して下さい）

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローン／取得

2. 仮想環境作成・有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. インストール（開発モード想定）
   - pip install -U pip
   - pip install -e .     （プロジェクトに pyproject/setup がある場合）
   - または必要パッケージを個別にインストール:
     - pip install duckdb openai defusedxml

4. 環境変数の設定
   - プロジェクトルート（.git または pyproject.toml の親）に .env ファイルを置くと自動読み込みされます。
   - 読み込み順序: OS 環境変数 > .env.local > .env
   - 自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。

   代表的な環境変数（最低限必要なもの）:
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
   - OPENAI_API_KEY: OpenAI API キー（score_news / score_regime を使う場合は必須）
   - KABU_API_PASSWORD: kabu ステーション API 用パスワード（発注等を追加実装する場合）
   - KABUSYS_ENV: development / paper_trading / live（デフォルト development）
   - LOG_LEVEL: DEBUG / INFO / ...（デフォルト INFO）
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
   - その他（LINE 関連、監視用ファイルパスなど）は Settings 参照

   例 .env（参考）
   ```
   JQUANTS_REFRESH_TOKEN=xxxx...
   OPENAI_API_KEY=sk-....
   KABU_API_PASSWORD=your_password
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

---

## 使い方（よく使う例）

以下は最小限の Python からの呼び出し例です。DuckDB 接続は duckdb.connect('<path>') で取得します。

- ETL（1日分の ETL 実行）
  ```
  from datetime import date
  import duckdb
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニューススコアリング（score_news）
  ```
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  # OPENAI_API_KEY が環境変数にある場合、api_key は省略可能
  written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
  print("書き込み銘柄数:", written)
  ```

- 市場レジーム判定（score_regime）
  ```
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
  ```

- 監査ログ DB 初期化
  ```
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  ```

- 設定の参照
  ```
  from kabusys.config import settings
  print(settings.duckdb_path)
  print(settings.is_live)
  ```

注意点:
- OpenAI 呼び出しを行う関数は api_key 引数で明示的にキーを渡すか、環境変数 OPENAI_API_KEY を設定してください。未設定だと ValueError が発生します。
- settings にある必須環境変数（JQUANTS_REFRESH_TOKEN 等）が未設定だと ValueError を送出します。
- ETL やニュース収集で使用する DB スキーマ（raw_prices / raw_news / ai_scores / market_regime 等）は ETL 実行や別スキーマ初期化ロジックで作成する必要があります（audit モジュールには init_audit_db があります）。

---

## 設計上の重要な挙動／注意点

- ルックアヘッドバイアス対策: 各 AI / リサーチ関数は target_date を引数に取り、内部で現在日時を参照して未来データを取り込まないよう設計されています。
- .env ロード挙動:
  - プロジェクトルート（.git または pyproject.toml を基準）から .env と .env.local を自動読み込みします。
  - OS 環境変数が優先され、.env.local が .env を上書きします。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロードを無効化します。
- J-Quants クライアント:
  - レート制限（120 req/min）を内部で制御します。
  - 401 を受けた場合は自動でトークンリフレッシュを行い 1 回再試行します。
  - ページネーション対応、リトライ / バックオフ実装あり。
- RSS ニュース収集:
  - SSRF 対策、受信最大サイズ制限、URL 正規化（utm 等除去）などが実装されています。
- OpenAI 呼び出し:
  - JSON Mode を利用して厳密に JSON を受け取り、パース失敗時はフェイルセーフでスコアを 0 にするなど安全側の挙動を行います。
  - リトライ / バックオフを実装。

---

## ディレクトリ構成

（src/kabusys をルートとした主要ファイル・モジュールの概要）

- src/kabusys/
  - __init__.py
  - config.py                   -- .env 自動読み込み・Settings
  - ai/
    - __init__.py
    - news_nlp.py               -- 銘柄ニュースのセンチメント解析（score_news）
    - regime_detector.py        -- 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py         -- J-Quants API client (fetch / save / get_id_token)
    - pipeline.py               -- ETL パイプライン（run_daily_etl 等）
    - etl.py                    -- ETLResult を再エクスポート
    - news_collector.py         -- RSS 取得・前処理・保存ヘルパー
    - calendar_management.py    -- 市場カレンダー管理・判定
    - quality.py                -- 品質チェック（欠損・スパイク・重複・日付不整合）
    - audit.py                  -- 監査ログスキーマ初期化・init_audit_db
    - stats.py                  -- zscore_normalize 等統計ユーティリティ
  - research/
    - __init__.py
    - factor_research.py        -- calc_momentum / calc_volatility / calc_value
    - feature_exploration.py    -- calc_forward_returns / calc_ic / factor_summary / rank

---

## トラブルシューティング（よくある問題）

- ValueError: 環境変数が見つからない
  - settings の必須項目（例: JQUANTS_REFRESH_TOKEN）を .env または環境変数で設定してください。
- OpenAI API エラー / レート制限
  - OPENAI_API_KEY の設定、あるいはリトライ待ち時間を確認してください。大量バッチ送信時はモデル側のレート制限に留意。
- DuckDB のテーブルがない / スキーマ不備
  - ETL や保存先テーブル（raw_prices, raw_news, ai_scores, market_regime 等）は事前にスキーマを用意するか、ETL 初回実行で作成するスクリプトを用意してください。audit 用の init_audit_db は utils として提供されています。
- RSS の fetch_rss でプライベートアドレスにブロックされる
  - セキュリティ上の仕様です。公開 RSS の URL を使用してください。

---

## 貢献 / 追加実装案

- 発注（kabu ステーション）との統合層（execution モジュール）実装
- Web UI / 監視ダッシュボード（LINE 通知や SQLite 監視 DB の連携）
- バックテスト用のデータ初期化スクリプト（過去データのロード）
- CI 用のテストスイート（DuckDB を使ったユニットテスト）

---

必要に応じて README の改善や、具体的なセットアップ手順（pyproject の依存情報、サンプル .env.example、DB スキーマ初期化スクリプトなど）を追記できます。どの部分を詳しくしたいか教えてください。