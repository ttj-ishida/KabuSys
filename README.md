# KabuSys

日本株向けのデータプラットフォームおよび自動売買補助ライブラリ。J-Quants / kabuステーション / RSS / OpenAI を組み合わせてデータ取得・品質管理・AI スコアリング・リサーチ・監査ログを提供します。

## 概要

KabuSys は以下の主要機能を持つ Python パッケージです。

- J-Quants から株価・財務・マーケットカレンダーを差分取得して DuckDB に保存する ETL パイプライン
- RSS を取得してニュースを収集・前処理し raw_news テーブルに保存するニュースコレクタ
- OpenAI（gpt-4o-mini）を用いたニュースの銘柄別センチメント（ai_scores）生成
- マーケットレジーム判定（ETF 1321 の MA200 とマクロニュースの LLM 評価を合成）
- 研究用途のファクター計算・前方リターン・IC 計算・統計ユーティリティ
- データ品質チェック（欠損・重複・スパイク・日付不整合）
- 監査ログ（signal / order_request / execution）用のスキーマ初期化ユーティリティ

設計方針として、バックテスト等でのルックアヘッドバイアス防止、冪等性（DB保存はON CONFLICTで上書き）、外部 API 呼び出しに対するリトライ / フェイルセーフを重視しています。

---

## 主な機能一覧

- data
  - ETL（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - J-Quants クライアント（fetch / save 関数、認証トークン自動更新、レート制御）
  - カレンダー管理（営業日判定・next/prev/get_trading_days）
  - ニュース収集（RSS の正規化・SSRF 対策・前処理）
  - 品質チェック（欠損・重複・スパイク・日付不整合）
  - 監査ログスキーマの初期化（init_audit_schema / init_audit_db）
  - 統計ユーティリティ（zscore 正規化）
- ai
  - ニュース NLP（score_news：銘柄ごとのセンチメントを ai_scores に書込）
  - レジーム判定（score_regime：ma200 と LLM のマクロセンチメントを合成）
- research
  - ファクター計算（momentum / value / volatility）
  - 特徴量探索（forward returns / IC / summary / rank）
- config
  - .env 自動読み込み（プロジェクトルート検出）と Settings クラス経由の環境変数取得

---

## 動作環境・依存

- Python 3.10+
- 主要依存（例）
  - duckdb
  - openai (OpenAI Python SDK)
  - defusedxml
- 標準ライブラリの urllib 等を利用
- J-Quants API / OpenAI API を利用する場合は各 API キーが必要

インストールは通常の Python パッケージと同様に行ってください（pip install -e . など）。

---

## セットアップ手順

1. リポジトリをクローン
   - git clone <repo>

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  または .venv\Scripts\activate

3. 依存パッケージをインストール
   - pip install -r requirements.txt
     - （requirements.txt がない場合は最低限 duckdb, openai, defusedxml をインストールしてください）
   - 例:
     - pip install duckdb openai defusedxml

4. 環境変数 (.env) を用意
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env` / `.env.local` を置くと自動で読み込まれます（読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。
   - 必須環境変数（Settings で必須とされるもの）
     - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD — kabuステーション API パスワード
     - SLACK_BOT_TOKEN — Slack 通知を使う場合
     - SLACK_CHANNEL_ID — Slack 通知先チャンネル
   - 参考の .env 例（.env.example として保存）
     - JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     - KABU_API_PASSWORD=your_kabu_password
     - SLACK_BOT_TOKEN=xoxb-...
     - SLACK_CHANNEL_ID=C12345678
     - OPENAI_API_KEY=sk-...
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - KABUSYS_ENV=development
     - LOG_LEVEL=INFO

5. データベースディレクトリ作成（必要に応じて）
   - デフォルトの DuckDB パスは `data/kabusys.duckdb`
   - 必要であれば `mkdir -p data`

---

## 使い方（簡易サンプル）

以下は Python から直接利用する例です。各関数は duckdb の接続（duckdb.connect(...) の返り値）を受け取って処理します。

- DuckDB 接続の生成（ファイル DB）
  ```python
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")
  ```

- 日次 ETL 実行
  ```python
  from kabusys.data.pipeline import run_daily_etl
  from datetime import date

  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュース NLP スコアリング（OpenAI API キーが必要）
  ```python
  from kabusys.ai.news_nlp import score_news
  from datetime import date

  # OPENAI_API_KEY を環境変数に設定するか、api_key 引数にキーを渡す
  written = score_news(conn, target_date=date(2026, 3, 20))
  print("書き込んだ銘柄数:", written)
  ```

- マーケットレジーム判定
  ```python
  from kabusys.ai.regime_detector import score_regime
  from datetime import date

  # OpenAI API key は環境変数 OPENAI_API_KEY、または api_key 引数で指定
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログ DB を初期化して接続を得る（独立 DB）
  ```python
  from kabusys.data.audit import init_audit_db
  conn_audit = init_audit_db("data/audit.duckdb")
  # テーブルが作成され、UTC タイムゾーンがセットされます
  ```

- 研究用ファクター計算
  ```python
  from kabusys.research.factor_research import calc_momentum
  from datetime import date

  records = calc_momentum(conn, target_date=date(2026, 3, 20))
  ```

- 設定値参照
  ```python
  from kabusys.config import settings
  print(settings.duckdb_path)
  print(settings.is_live)
  ```

---

## .env の自動読み込み

- パッケージはインポート時にプロジェクトルート（.git または pyproject.toml）を探索して `.env` / `.env.local` を自動で読み込みます。
  - 読み込み順：OS 環境 > .env.local（上書き） > .env
  - 自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト用途など）。

---

## 注意点・設計上のポイント

- ルックアヘッドバイアス防止
  - AI モジュールや ETL は基本的に内部で datetime.today() を直接参照する実装を避け、呼び出し側から target_date を渡す方式を採用しています。
- 冪等性
  - DB への保存は ON CONFLICT DO UPDATE などで冪等に設計されています。
- API のリトライとレート制御
  - J-Quants クライアントはレート制御（120 req/min）とリトライ（指数バックオフ）を実装しています。
  - OpenAI 呼び出しはリトライやフェイルセーフ（失敗時はスコア 0.0）を行います。
- セキュリティ
  - news_collector では SSRF・XML Bomb 対策（ホストのプライベート判定、defusedxml、受信サイズ制限）を実装しています。

---

## ディレクトリ構成

主要ファイル / モジュールの一覧（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                         — 環境変数・設定管理
  - ai/
    - __init__.py
    - news_nlp.py                      — ニュースセンチメント（score_news）
    - regime_detector.py               — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - pipeline.py                      — ETL パイプライン（run_daily_etl 等）
    - jquants_client.py                — J-Quants API クライアント / 保存処理
    - news_collector.py                — RSS ニュース収集
    - calendar_management.py           — マーケットカレンダー管理
    - quality.py                       — データ品質チェック
    - stats.py                         — 統計ユーティリティ（zscore_normalize）
    - audit.py                         — 監査ログスキーマ初期化
    - etl.py                           — ETL インタフェース再エクスポート
  - research/
    - __init__.py
    - factor_research.py               — ファクター計算
    - feature_exploration.py           — forward returns / IC / summary
  - monitoring/ (存在は __all__ に含まれるが今回の抜粋では詳細なし)

---

## よくある質問

- OpenAI の API キーはどこで設定しますか？
  - 環境変数 `OPENAI_API_KEY` を設定するか、score_news / score_regime の api_key 引数に直接渡してください。

- DuckDB のデータスキーマはどこで定義されていますか？
  - 本 README のコード抜粋ではスキーマ定義を省略している箇所もあります。ETL 実行前に適切なスキーマ初期化スクリプトを用意してください（例: raw_prices / raw_financials / market_calendar / raw_news / news_symbols / ai_scores / prices_daily 等）。

- テスト環境で .env を読み込ませたくない場合は？
  - 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して自動ロードをスキップできます。

---

必要であれば README に使用例の詳細なコードスニペット（ETL の設定オプション、news_collector の RSS 登録例、監査ログの使い方など）や、DuckDB のスキーマ定義テンプレート、CI / デプロイ手順を追加できます。どの情報を優先して追加しますか？