# KabuSys

日本株向けの自動売買・データ基盤ライブラリです。  
ETL（J-Quants からのデータ取得）、ニュース収集・NLP（OpenAI）、ファクター計算、品質チェック、監査ログ（発注トレース）など、自動売買システムに必要なデータ基盤および研究用ユーティリティを提供します。

バージョン: 0.1.0

---

## 主な特徴

- データ取得（J-Quants API）と ETL パイプライン
  - 日次株価（OHLCV）、財務諸表、JPX カレンダーの差分取得・冪等保存
  - レート制限／再試行／トークン自動リフレッシュ対応
- ニュース収集（RSS）と前処理
  - URL 正規化、トラッキングパラメータ除去、SSRF 対策、受信サイズ制限
- ニュース NLP（OpenAI）
  - 銘柄ごとのニュースを LLM に渡してセンチメントスコアを ai_scores に保存
  - チャンクバッチ、JSON モード、リトライ・フォールバック対応
- 市場レジーム判定（MA + マクロニュースの LLM センチメントを合成）
- リサーチモジュール（ファクター計算・特徴量探索）
  - モメンタム、ボラティリティ、バリュー、将来リターン計算、IC（Spearman）
  - Z スコア正規化ユーティリティ
- データ品質チェック
  - 欠損、重複、スパイク、日付不整合などの検出
- 監査（audit）スキーマ
  - signal → order_request → executions のトレース用テーブルを生成
  - 発注の冪等性（order_request_id）を考慮
- 環境設定管理
  - .env / .env.local の自動読み込み（プロジェクトルート検出）
  - 必須環境変数の明示的チェック

---

## 必要条件 / 依存

- Python 3.9+
- 必要パッケージ（代表例）
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants API、RSS フィード、OpenAI）

具体的な requirements.txt はプロジェクト側で管理してください。上記パッケージは本 README に記載された機能を使うために最低限必要となる代表例です。

---

## セットアップ手順

1. リポジトリをクローン／配置

2. 仮想環境の作成（例: venv）
   - macOS / Linux:
     - python -m venv .venv
     - source .venv/bin/activate
   - Windows:
     - python -m venv .venv
     - .venv\Scripts\activate

3. 依存パッケージのインストール（プロジェクトの requirements.txt に合わせて）
   - pip install --upgrade pip
   - pip install duckdb openai defusedxml

   （プロジェクトに requirements.txt がある場合はそれを使ってください。）
   - pip install -r requirements.txt

4. 環境変数 / .env の準備
   - プロジェクトルートに `.env` および（必要なら）`.env.local` を置くと、パッケージ読み込み時に自動で読み込まれます（ただしテスト等で無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。
   - 必須環境変数（config.Settings が require するもの）:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - SLACK_BOT_TOKEN
     - SLACK_CHANNEL_ID
   - 推奨／利用可能な環境変数:
     - OPENAI_API_KEY (score_news / score_regime を使う場合)
     - KABUSYS_ENV (development / paper_trading / live) — デフォルト development
     - LOG_LEVEL (DEBUG/INFO/WARNING/ERROR/CRITICAL) — デフォルト INFO
     - DUCKDB_PATH (デフォルト data/kabusys.duckdb)
     - SQLITE_PATH (デフォルト data/monitoring.db)

   例（.env）
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=sk-...
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   DUCKDB_PATH=data/kabusys.duckdb
   ```

5. データディレクトリの作成（必要に応じて）
   - mkdir -p data

---

## 使い方（代表的な API/ワークフロー）

以下は Python スクリプトからライブラリを利用する例です。DuckDB の接続は `duckdb.connect(path)` を使って取得します。

- 日次 ETL（株価・財務・カレンダー取得 + 品質チェック）
  ```python
  from datetime import date
  import duckdb
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースのセンチメント付与（ai/news_nlp.score_news）
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  written = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
  print(f"書き込んだ銘柄数: {written}")
  ```

- 市場レジーム判定（ai/regime_detector.score_regime）
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")
  ```

- 監査用 DuckDB 初期化（発注トレース用）
  ```python
  from kabusys.data.audit import init_audit_db

  conn = init_audit_db("data/audit.duckdb")
  ```

- カレンダー更新ジョブ（J-Quants から市場カレンダー差分取得）
  ```python
  from datetime import date
  import duckdb
  from kabusys.data.calendar_management import calendar_update_job

  conn = duckdb.connect("data/kabusys.duckdb")
  saved = calendar_update_job(conn, lookahead_days=90)
  print(f"saved: {saved}")
  ```

- 環境設定の確認
  ```python
  from kabusys.config import settings
  print(settings.env, settings.log_level, settings.duckdb_path)
  ```

注意点:
- OpenAI を使う関数は api_key 引数を受け取るか、環境変数 OPENAI_API_KEY を参照します。
- ほとんどの関数は DuckDB の特定のテーブル（raw_prices, raw_financials, raw_news, ai_scores, market_regime, market_calendar など）を参照します。初回はスキーマ作成や ETL 実行でテーブルが生成されます。
- 自動読み込みされる .env の挙動はパッケージ import 時に行われます（プロジェクトルート検出は __file__ の親から .git または pyproject.toml を探します）。テスト等で自動読み込みを止めたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## よく使うモジュール / API の説明

- kabusys.config
  - Settings クラス: 必須環境変数チェック、パスやフラグ（is_live 等）を提供
  - 自動的にプロジェクトルートの `.env` / `.env.local` を読み込むロジックあり
- kabusys.data
  - pipeline.py: run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl
  - jquants_client.py: J-Quants API の低レイヤクライアント（fetch_* / save_*）
  - news_collector.py: RSS 取得と raw_news 保存ロジック
  - quality.py: データ品質チェック群（check_missing_data, check_spike, ...）
  - calendar_management.py: 営業日判定・カレンダー更新ジョブ
  - audit.py: 監査スキーマ初期化（init_audit_schema / init_audit_db）
  - stats.py: zscore_normalize
- kabusys.ai
  - news_nlp.py: score_news（記事→銘柄別スコア）
  - regime_detector.py: score_regime（MA + LLM 合成で市場レジーム判定）
- kabusys.research
  - factor_research.py: calc_momentum / calc_value / calc_volatility
  - feature_exploration.py: calc_forward_returns / calc_ic / factor_summary / rank

---

## ディレクトリ構成（抜粋）

プロジェクトの実装例（主要ファイル）:

- src/
  - kabusys/
    - __init__.py
    - config.py
    - ai/
      - __init__.py
      - news_nlp.py
      - regime_detector.py
    - data/
      - __init__.py
      - jquants_client.py
      - pipeline.py
      - etl.py
      - news_collector.py
      - calendar_management.py
      - quality.py
      - stats.py
      - audit.py
      - pipeline.py
      - etl.py
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
      - ...
    - research.py (パッケージ初期化)
    - ai.py (パッケージ初期化)
    - data.py (パッケージ初期化)

（上記は README に含まれる代表的なファイル群の抜粋です。より詳細なファイル構成はリポジトリルートのツリーを参照してください。）

---

## 運用・デプロイの注意点

- 実稼働（live）時は KABUSYS_ENV を `live` に設定してください。`is_live` フラグにより実行制御が可能です。
- OpenAI や J-Quants の API 呼び出しは課金対象となるため、rate/usage の監視を行ってください。
- ETL は差分更新とバックフィルを行いますが、初回はかなりのデータ量を取得するため注意してください（DuckDB ファイルのサイズ等）。
- ニュース収集時の外部 URL 処理では SSRF 対策を講じていますが、運用環境のプロキシ／ネットワーク設定に応じた検証を行ってください。
- 監査テーブルは削除しないことを前提としているため容量計画をしてください。

---

## トラブルシューティング

- ValueError: 環境変数が未設定
  - 必須の環境変数（JQUANTS_REFRESH_TOKEN 等）が設定されているか確認してください。
- OpenAI / J-Quants API エラー
  - API キーの有効性、ネットワーク、レート制限を確認してください。J-Quants は 401 時にリフレッシュ処理を行いますが、refresh token が無効だと失敗します。
- DuckDB テーブルが存在しない
  - 初回は ETL 実行やスキーマ初期化（audit.init_audit_schema）でテーブルが作成されます。必要に応じてスキーマ初期化処理を呼んでください。
- RSS 取得で防御に引っかかる
  - fetch_rss はプライベート IP や非 http/https スキームを弾きます。対象 URL を確認してください。

---

## 開発・テストについて

- テスト中に自動 .env 読み込みを無効にしたい場合:
  - 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセットしてください。
- OpenAI 呼び出しのモック:
  - ai モジュール内の内部関数（_call_openai_api 等）はユニットテストで patch して差し替え可能に設計されています。

---

以上が本ライブラリの概要と導入・利用ガイドです。詳細な API の仕様や追加のユーティリティについてはソースコード（各モジュールの docstring）を参照してください。必要であれば README に追記すべきサンプルや運用手順（cron/ジョブ設定、監視方法など）を追加しますのでお知らせください。