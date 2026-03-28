# KabuSys

KabuSys は日本株向けの自動売買・データプラットフォームのライブラリ群です。  
J-Quants API や RSS ニュース、OpenAI を活用したデータ収集・ETL・NLP（ニュースセンチメント）・ファクター計算・監査ログなどを備え、バックテスト／研究／運用に必要な基盤処理を提供します。

主な設計方針：
- ルックアヘッドバイアスを避ける（内部で date.today()/datetime.today() に依存しない設計）
- DuckDB を中心としたローカル DB 管理（ETL は冪等／差分更新）
- 外部 API 呼び出しはリトライ／レート制御を備えた安全実装
- 監査ログ（signal → order → execution トレース）を保持

## 機能一覧
- 環境設定管理（.env 自動読み込み、必須キーチェック）
- J-Quants クライアント
  - 株価日足（OHLCV）取得・保存（ページネーション対応）
  - 財務データ取得・保存
  - JPX マーケットカレンダー取得・保存
  - レート制限 / トークン自動リフレッシュ / 再試行
- ETL パイプライン（デイリー差分取得・保存・品質チェック）
- データ品質チェック（欠損、重複、スパイク、日付不整合）
- ニュース収集（RSS、SSRF/サイズ対策、前処理、news ↔ 銘柄紐付け）
- ニュース NLP（OpenAI による銘柄別センチメント → ai_scores へ保存）
- 市場レジーム判定（ETF 1321 の MA とマクロ記事の LLM センチメントを合成）
- 研究用ユーティリティ（ファクター計算、forward returns、IC、Zスコア正規化）
- 監査ログスキーマ（signal_events / order_requests / executions）と初期化ユーティリティ
- DuckDB ベースの監査 DB 初期化補助

---

## 必要条件
- Python 3.10+
- 必要パッケージ（例）
  - duckdb
  - openai
  - defusedxml
  - （標準ライブラリのみで実装された部分も多いですが、上記は最低限必要）
- J-Quants API のリフレッシュトークン、OpenAI API キー など外部 API の認証情報

（プロジェクト配布時は requirements.txt を用意してください）

---

## セットアップ手順

1. 仮想環境作成（例）
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install --upgrade pip
   ```

2. パッケージのインストール（開発中は editable）
   ```bash
   pip install -e .
   # または必要パッケージを直接インストール
   pip install duckdb openai defusedxml
   ```

3. 環境変数設定
   - プロジェクトルート（.git または pyproject.toml が置かれたディレクトリ）を基準に自動で `.env` / `.env.local` を読み込みます。
   - 自動読み込みを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

4. 必須環境変数（.env の例）
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=your_openai_api_key
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=your_slack_bot_token
   SLACK_CHANNEL_ID=your_slack_channel_id
   # オプション
   KABUSYS_ENV=development  # valid: development, paper_trading, live
   LOG_LEVEL=INFO
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   KABUSYS_DISABLE_AUTO_ENV_LOAD=0
   ```

   - 自動読み込みの優先順位: OS 環境変数 > .env.local > .env
   - 必須キーは Settings クラス（kabusys.config）でチェックされ、未設定の場合は ValueError が発生します。

---

## 使い方（簡易サンプル）

以下は Python REPL やスクリプト内での利用例です。各関数は DuckDB の接続オブジェクト（duckdb.connect(...) の戻り値）を受け取ります。

- DuckDB 接続例
  ```python
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 監査 DB を初期化する（ファイルがなければ親ディレクトリを作成）
  ```python
  from kabusys.data.audit import init_audit_db

  audit_conn = init_audit_db(settings.duckdb_path)  # あるいは別パス
  ```

- 日次 ETL 実行
  ```python
  from kabusys.data.pipeline import run_daily_etl
  from kabusys.config import settings
  import duckdb
  from datetime import date

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメント（ai）評価を実行し ai_scores に保存
  ```python
  from kabusys.ai.news_nlp import score_news
  from kabusys.config import settings
  import duckdb
  from datetime import date

  conn = duckdb.connect(str(settings.duckdb_path))
  # OPENAI_API_KEY は環境変数か api_key 引数で指定
  n = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
  print("written codes:", n)
  ```

- 市場レジーム評価（score_regime）
  ```python
  from kabusys.ai.regime_detector import score_regime
  from datetime import date
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  score_regime(conn, target_date=date(2026, 3, 20), api_key=None)  # OpenAIキーは環境変数でも可
  ```

- 研究用ファクター計算
  ```python
  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
  from datetime import date
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  mom = calc_momentum(conn, target_date=date(2026, 3, 20))
  vol = calc_volatility(conn, target_date=date(2026, 3, 20))
  val = calc_value(conn, target_date=date(2026, 3, 20))
  ```

- 研究ユーティリティ：forward returns / IC / zscore 正規化
  ```python
  from kabusys.research.feature_exploration import calc_forward_returns, calc_ic
  from kabusys.data.stats import zscore_normalize
  ```

注意点：
- OpenAI を使う関数（news_nlp.score_news / regime_detector.score_regime）は APIキー（api_key 引数または環境変数 OPENAI_API_KEY）を必要とします。
- ETL / 保存処理は冪等（ON CONFLICT DO UPDATE）で設計されていますが、実行前にバックアップやスキーマ確認を行ってください。
- news_collector は RSS の取得時に SSRF・gzip・XML 攻撃対策を行っています。

---

## 主要モジュールの説明（抜粋）
- kabusys.config
  - .env 自動読み込み、Settings クラス（環境変数のラッパー）
  - キー例: JQUANTS_REFRESH_TOKEN, OPENAI_API_KEY, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
  - KABUSYS_ENV の有効値: development / paper_trading / live

- kabusys.data
  - jquants_client: J-Quants API 呼び出し、保存ユーティリティ（save_*）
  - pipeline: 日次 ETL（run_daily_etl など）
  - quality: データ品質チェック（欠損・スパイク・重複・日付不整合）
  - news_collector: RSS 取得・正規化・保存ロジック
  - calendar_management: market_calendar の管理、営業日判定ユーティリティ
  - audit: 監査スキーマ定義と初期化ユーティリティ

- kabusys.ai
  - news_nlp: 銘柄別ニュースセンチメントの LLM スコアリング（score_news）
  - regime_detector: ETF とマクロ記事を合成して市場レジームを判定（score_regime）

- kabusys.research
  - factor_research: momentum / volatility / value の計算
  - feature_exploration: forward returns, IC（Spearman ρ）, factor summary, rank
  - data.stats: zscore_normalize（クロスセクション Z スコア）

---

## ディレクトリ構成

概略（src/kabusys 以下）:

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
    - audit 初期化・DB ヘルパ
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - research utilities, data stats, etc.

（実際のファイルは README 作成元のコードベースを参照してください）

---

## 開発・デバッグのヒント
- テスト時に環境変数自動読み込みを無効化する：
  ```bash
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  ```
- OpenAI 呼び出しやネットワーク依存処理はユニットテストでモック可能です（コード内に patch しやすい設計あり）。
- DuckDB のクエリを直接確認することで ETL の動作確認が容易です。

---

## 参考
- settings（kabusys.config）で定義される主要プロパティ:
  - jquants_refresh_token, kabu_api_password, kabu_api_base_url
  - slack_bot_token, slack_channel_id
  - duckdb_path, sqlite_path
  - env, log_level, is_live / is_paper / is_dev

---

必要に応じて README のチュートリアル（ETL のスケジュール設定 / Slack 通知連携 / 本番の注意点）を追加できます。どの部分を詳しく書くか指示をください。