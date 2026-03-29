# KabuSys

日本株向けの自動売買・データプラットフォーム用ライブラリです。  
ETL（J-Quants からの市場データ取得）、ニュース収集・NLP（OpenAI を利用したセンチメント分析）、ファクター算出、監査ログ（監査用 DuckDB スキーマ）などを提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は日本株のデータ取得・前処理、ML/リサーチ用ファクター計算、ニュースの NLP スコアリング、そして売買フローの監査ログを一貫して扱えるように設計された Python パッケージです。  
主な目的は以下です。

- J-Quants API からの差分 ETL（株価・財務・カレンダー）
- RSS からのニュース収集と前処理（SSRF/サイズ上限対策あり）
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント評価（銘柄別 / マクロ）
- ファクター計算（モメンタム、ボラティリティ、バリュー等）および統計解析ユーティリティ
- 取引シグナルから約定までトレース可能な監査テーブル（DuckDB）

設計上の特徴:
- ルックアヘッドバイアス防止（target_date を明示）
- 冪等性（ETL/保存処理は ON CONFLICT / upsert）
- フェイルセーフ（API 失敗時はフォールバック動作）
- DuckDB を中核に軽量にローカル保存可能

---

## 機能一覧

- data:
  - ETL パイプライン（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - J-Quants クライアント（取得・保存・認証・レート制御・リトライ）
  - マーケットカレンダー管理（営業日判定、next/prev/get_trading_days）
  - ニュース収集（RSS -> raw_news、SSRF や受信サイズ保護）
  - データ品質チェック（欠損・スパイク・重複・日付不整合）
  - 監査ログスキーマ初期化（init_audit_schema / init_audit_db）
  - 統計ユーティリティ（zscore_normalize）
- ai:
  - 銘柄別ニュースセンチメント（score_news）
  - マクロレジーム判定（score_regime: ETF 1321 の MA200 とマクロニュースを統合）
- research:
  - ファクター計算（calc_momentum / calc_value / calc_volatility）
  - 特徴量探索・IC 計算（calc_forward_returns / calc_ic / factor_summary / rank）
- config:
  - 環境変数読み込み（.env 自動読み込み・明示的無効化オプション）
  - settings オブジェクトで設定取得（必須鍵の検出・バリデーション）

---

## 要件

- Python >= 3.10（PEP 604 型注釈などを使用）
- 主な Python パッケージ:
  - duckdb
  - openai (OpenAI Python SDK)
  - defusedxml
- 標準ライブラリ: urllib, json, datetime など

パッケージ管理は任意（pip / poetry 等）。プロジェクトには pyproject.toml が想定されています。

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境を作成して有効化（例）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 必要な依存関係をインストール
   - 簡易インストール例（最低限）
     ```
     pip install duckdb openai defusedxml
     ```
   - プロジェクト配布パッケージがある場合:
     ```
     pip install -e .
     ```

4. 環境変数を設定（またはプロジェクトルートに `.env` を作成）
   - 必須（config.Settings 内で _require() が使われているもの）:
     - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD : kabuステーション API パスワード（設定に使用）
     - SLACK_BOT_TOKEN : Slack 通知に使用する Bot Token
     - SLACK_CHANNEL_ID : 通知先 Slack チャンネル ID
   - 推奨 / 利用機能に応じて:
     - OPENAI_API_KEY : OpenAI 呼び出し（score_news / score_regime など）
     - DUCKDB_PATH / SQLITE_PATH : データベースファイルパスの上書き
     - KABUSYS_ENV : development / paper_trading / live
     - LOG_LEVEL : INFO / DEBUG / ...
   - 自動ロードを無効にする場合:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```

5. データディレクトリなどを作成（設定次第）
   ```
   mkdir -p data
   ```

---

## 使い方（例）

以下は主要なユースケースの最小例です。実運用ではログ設定やエラーハンドリングを追加してください。

- DuckDB 接続と日次 ETL の実行
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースのセンチメントスコア（銘柄別）
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  cnt = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
  print(f"scored {cnt} symbols")
  ```

- マクロレジーム判定（market_regime テーブルへ書き込み）
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")
  ```

- 監査 DB 初期化（監査テーブル作成）
  ```python
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/kabusys_audit.duckdb")
  # conn は初期化済み DuckDB 接続
  ```

- RSS フィード取得（ニュース収集の一部）
  ```python
  from kabusys.data.news_collector import fetch_rss
  articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
  for a in articles[:5]:
      print(a["datetime"], a["title"])
  ```

注意:
- OpenAI を使う関数は api_key を引数で渡すか環境変数 `OPENAI_API_KEY` を設定してください。未設定だと ValueError が発生します。
- ETL 実行時、J-Quants の認証は settings.jquants_refresh_token を参照します。

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 以下の主なファイル・モジュール概要です。

- kabusys/
  - __init__.py
  - config.py                -- 環境変数解析と Settings
  - ai/
    - __init__.py
    - news_nlp.py            -- 銘柄別ニュースセンチメント（score_news）
    - regime_detector.py     -- マクロレジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py      -- J-Quants API クライアント + 保存関数
    - pipeline.py            -- ETL パイプライン（run_daily_etl 等）
    - etl.py                 -- ETLResult のエクスポート
    - calendar_management.py -- マーケットカレンダー管理
    - news_collector.py      -- RSS 収集・前処理
    - quality.py             -- データ品質チェック
    - stats.py               -- 統計ユーティリティ（zscore_normalize）
    - audit.py               -- 監査ログスキーマ初期化（init_audit_schema）
  - research/
    - __init__.py
    - factor_research.py     -- calc_momentum / calc_value / calc_volatility
    - feature_exploration.py -- calc_forward_returns / calc_ic / factor_summary / rank
  - research/（その他）
  - ...（将来的に strategy / execution / monitoring などのパッケージを想定）

---

## よくあるトラブルと対処

- ValueError: 環境変数が未設定
  - settings のプロパティは必須項目を _require() で取得します。`.env` を正しく配置するか、該当キーを環境変数で設定してください。

- OpenAI / J-Quants API 呼び出しの失敗
  - ネットワークエラーやレート制限時には内部でリトライ処理を行いますが、API キーやトークン期限切れは手動更新が必要です。J-Quants は refresh token を用いて id_token を取得します（settings.jquants_refresh_token を確認）。

- DuckDB に関するエラー
  - DuckDB のファイルパス（デフォルト: data/kabusys.duckdb）に書き込み権限があるか確認してください。
  - executemany の空リスト渡しなどバージョン差に敏感な箇所があるため、システムの duckdb バージョンに注意してください。

---

## 開発・貢献

- コーディング規約、テスト方針、CI 等はリポジトリの CONTRIBUTING.md を参照してください（存在する場合）。
- 単体テストやモック（OpenAI / HTTP 呼び出し）を用いたテスト設計が可能です。既存コードはテストで差し替えやすいように設計されています（内部呼び出しを別関数化してある等）。

---

## ライセンス

プロジェクトのライセンス情報はリポジトリルートの LICENSE を参照してください。

---

README はここまでです。必要であれば、インストール用の requirements.txt サンプルや具体的な .env.example のテンプレート、よく使うスクリプト（cron / GitHub Actions 例）を追記します。どの情報を追加しますか？