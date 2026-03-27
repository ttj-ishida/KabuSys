# KabuSys

KabuSys は日本株向けの自動売買・データプラットフォーム用ライブラリです。  
データ収集（J-Quants）、ニュースの NLP スコアリング（OpenAI）、市場レジーム判定、ETL パイプライン、データ品質チェック、監査ログなど、アルゴリズムトレーディングに必要な基盤機能を提供します。

## 主な特徴
- J-Quants API と連携した株価・財務・カレンダーの差分 ETL（ページネーション・レート制御・リトライ付き）
- ニュース収集（RSS）と前処理、OpenAI を用いた銘柄単位センチメントスコアリング（gpt-4o-mini を想定）
- 市場レジーム判定（ETF 1321 の MA200乖離 + マクロニュースセンチメントの合成）
- DuckDB を用いたローカルデータストアと冪等保存（ON CONFLICT）
- データ品質チェック（欠損・スパイク・重複・日付整合性）
- 監査ログ（signal → order_request → execution のトレーサビリティを担保するスキーマ）
- Look-ahead バイアス回避を意識した設計（外部 API 呼び出しや日付参照における注意）

---

## 動作環境（推奨）
- Python 3.10+
- 必要な主要ライブラリ（例）
  - duckdb
  - openai
  - defusedxml

（プロジェクトに requirements.txt があればそれを使用してください。ここでは代表的なパッケージを示しています。）

---

## セットアップ手順（開発環境向け簡易手順）

1. リポジトリをクローン
   ```bash
   git clone <repository-url>
   cd <repository>
   ```

2. 仮想環境の作成（推奨）
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

3. 必要パッケージのインストール（例）
   ```bash
   pip install duckdb openai defusedxml
   ```
   - 実際のプロジェクトでは requirements.txt / pyproject.toml を参照してください。

4. 環境変数の設定
   - プロジェクトルートに `.env` / `.env.local` を置くと、自動的に読み込まれます（`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能）。
   - 必須の環境変数（主要なもの）:
     - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD: kabuステーション API のパスワード
     - SLACK_BOT_TOKEN: Slack 通知用 Bot トークン
     - SLACK_CHANNEL_ID: Slack チャンネル ID
     - OPENAI_API_KEY: OpenAI API キー（score_news / score_regime に使用）
   - 任意 / デフォルトがあるもの:
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト `development`
     - LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL) — デフォルト `INFO`
     - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env 自動読み込みを無効化できます

   例 `.env`（最小）
   ```
   JQUANTS_REFRESH_TOKEN=xxxx
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C...
   OPENAI_API_KEY=sk-...
   KABU_API_PASSWORD=your_kabu_password
   ```

---

## 使い方（簡単な例）

ライブラリはプログラムからインポートして利用します。以下は DuckDB 接続を使った主要なユースケースの例です。

- 日次 ETL の実行（データ収集・保存・品質チェック）
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュース NLP（銘柄ごとの AI スコア付与）
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"書き込み銘柄数: {written}")
  ```
  - score_news は OpenAI API キーを引数 `api_key` で渡せます（指定しない場合は環境変数 OPENAI_API_KEY を参照）。

- 市場レジーム判定
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログ DB の初期化
  ```python
  from kabusys.data.audit import init_audit_db

  conn = init_audit_db("data/audit.duckdb")  # または ":memory:"
  ```

- ファクター計算（研究用）
  ```python
  from kabusys.research.factor_research import calc_momentum
  import duckdb
  from datetime import date

  conn = duckdb.connect("data/kabusys.duckdb")
  res = calc_momentum(conn, target_date=date(2026, 3, 20))
  ```

---

## 主要モジュール概要

- kabusys.config
  - 環境変数の読み込みと設定取得（.env 自動ロード、必須チェック）
- kabusys.data
  - jquants_client: J-Quants API 連携（fetch / save / 認証・レート制御・リトライ）
  - pipeline: 日次 ETL の実装（run_daily_etl, run_prices_etl, ...）
  - news_collector: RSS 収集・前処理（SSRF 対策、gzip 対応）
  - quality: データ品質チェック（欠損・重複・スパイク・日付整合性）
  - calendar_management: 市場カレンダー管理（営業日判定、next/prev_trading_day 等）
  - audit: 監査ログスキーマ定義と初期化
  - stats: 汎用統計ユーティリティ（zscore 正規化）
- kabusys.ai
  - news_nlp: ニュースを LLM に投げて銘柄ごとのセンチメントを計算・保存
  - regime_detector: ETF とマクロニュースから市場レジームを判定
- kabusys.research
  - factor_research: Momentum / Value / Volatility 等のファクター計算
  - feature_exploration: 将来リターン、IC、統計サマリー等

---

## ディレクトリ構成（抜粋）
以下はコードベースの主要ファイル/ディレクトリ（src/kabusys 以下）の抜粋です。

- src/kabusys/
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
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - research/*.py（ファクター・解析用ユーティリティ）

（実際のリポジトリにはさらに strategy / execution / monitoring 等のモジュールやドキュメントが含まれる場合があります。）

---

## 注意事項 / 設計上のポイント
- Look-ahead bias の回避を強く意識して実装されています。target_date より未来のデータを参照しないようクエリや時間ウィンドウが設計されています。
- OpenAI 呼び出しや外部 API の失敗は多くの箇所でフェイルセーフ（スコア 0、スキップ、ログ出力）となっており、部分失敗がシステム全体を停止させないようになっています。
- DuckDB に対する一括保存は冪等（ON CONFLICT）で設計されています。ETL の再実行や部分的な差分更新に耐えます。
- ニュース収集は SSRF 対策・XML デコーダの安全化（defusedxml）・応答サイズ制限などセキュリティに配慮しています。

---

## よくある質問 / トラブルシューティング
- .env が読み込まれない:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 が設定されていないか確認してください。
  - 自動検出は .git または pyproject.toml の位置からプロジェクトルートを探します。パッケージ配布後やテスト時は環境変数を直接設定するのが確実です。
- OpenAI 呼び出しが失敗する:
  - ネットワーク、API キー、レート制限、モデル名（gpt-4o-mini）を確認してください。score_news / score_regime はリトライロジックを持ちますが、キー未設定だと ValueError を投げます。
- DuckDB テーブルが存在しない:
  - 初回は ETL 実行前に schema を作成するスクリプトが必要です（プロジェクトに schema 初期化ユーティリティがある場合はそれを使用してください）。監査ログ用の init_audit_db はスキーマ初期化を行います。

---

README に載せていない詳細な API やパラメータの説明は、各モジュールの docstring を参照してください。追加で README に含めたいサンプル（例: 実運用でのジョブ設定・cron / Airflow の設定例）があれば教えてください。