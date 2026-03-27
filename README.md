# KabuSys

日本株向けのデータ基盤・リサーチ・自動売買補助ライブラリです。  
DuckDB を中心としたデータ ETL、ニュースの NLP スコアリング（OpenAI）、市場レジーム判定、リサーチ用ファクター計算、監査ログ（トレーサビリティ）などを含むモジュール群を提供します。

---

## 概要

KabuSys は以下の目的で設計されています。

- J-Quants API からの差分取得（株価・財務・カレンダー）および DuckDB への冪等保存（ETL）
- RSS ベースのニュース収集と文章前処理（SSRF / Gzip / トラッキング対策）
- OpenAI を用いたニュースセンチメント（銘柄別）とマクロセンチメントの評価
- ETF の移動平均や LLM のセンチメントを合成した市場レジーム判定
- 研究用途のファクター計算（Momentum / Volatility / Value）と特徴量解析ユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（signal → order_request → execution のトレース用テーブル定義・初期化）

設計上の重要点：

- ルックアヘッドバイアス回避（内部で date.today()/datetime.today() を直接参照しない設計）
- 冪等処理（ETL / 保存）
- フェイルセーフ：外部 API 失敗時や不完全データ時は安全側の動作（例: スコア 0.0）で継続
- DuckDB を前提とした SQL と Python の組み合わせ

---

## 主な機能一覧

- データ ETL（kabusys.data.pipeline）
  - run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl
- J-Quants API クライアント（kabusys.data.jquants_client）
  - fetch / save の一貫実装、トークン自動リフレッシュ、レートリミット管理
- ニュース収集（kabusys.data.news_collector）
  - RSS 取得、URL 正規化、SSRF 対策、raw_news への保存想定
- データ品質チェック（kabusys.data.quality）
  - 欠損・スパイク・重複・日付不整合検出
- 監査ログ初期化（kabusys.data.audit）
  - signal_events / order_requests / executions の DDL と初期化ユーティリティ
- AI 関連（kabusys.ai）
  - news_nlp.score_news（銘柄別ニュースセンチメント）
  - regime_detector.score_regime（マクロ + ETF ma200 による市場レジーム判定）
- 研究ユーティリティ（kabusys.research）
  - calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary, zscore_normalize

---

## セットアップ手順

前提: Python 3.10+ を推奨（型ヒントの構文や一部の標準機能に依存）

1. 仮想環境作成（任意だが推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate    # macOS / Linux
   .venv\Scripts\activate       # Windows
   ```

2. 必要パッケージをインストール  
   （プロジェクトに requirements.txt / pyproject.toml があればそちらを使用してください。例として最低限の依存を列挙します）
   ```
   pip install duckdb openai defusedxml
   ```
   - openai: LLM 呼び出し用
   - duckdb: 内部 DB
   - defusedxml: RSS パースの安全化
   - その他、ネットワーク/ログ用の標準ライブラリのみで動作する箇所もあります

3. パッケージをインストール（開発中）
   ```
   pip install -e .
   ```
   （プロジェクトのルートに pyproject.toml / setup.cfg 等がある場合）

4. 環境変数設定  
   プロジェクトルートの .env / .env.local を用意することで自動的に読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロードを無効化できます）。

   主に必要な環境変数（例）:
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
   - KABU_API_PASSWORD: kabuステーション API 用パスワード（必須扱いのプロパティあり）
   - SLACK_BOT_TOKEN: Slack 通知用トークン（必須）
   - SLACK_CHANNEL_ID: Slack チャンネル ID（必須）
   - OPENAI_API_KEY: OpenAI API キー（score_news / score_regime 等で使用）
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
   - KABUSYS_ENV: 開発環境識別 (development | paper_trading | live)
   - LOG_LEVEL: ログレベル (DEBUG | INFO | WARNING | ERROR | CRITICAL)

   簡易 .env.example:
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=sk-...
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

---

## 使い方（簡易例）

以下はライブラリをインポートして処理を呼び出す基本例です。実行前に環境変数や DuckDB の初期スキーマ（必要なら）を準備してください。

- DuckDB 接続を作成する（ファイルパスは設定に従うこともできます）
  ```python
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL を実行する
  ```python
  from kabusys.data.pipeline import run_daily_etl
  from datetime import date

  # target_date を指定（省略すると今日）
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースのセンチメントを生成（AI スコアリング）
  ```python
  from kabusys.ai.news_nlp import score_news
  from datetime import date

  count = score_news(conn, target_date=date(2026, 3, 20))
  print(f"scored {count} symbols")
  ```

- 市場レジーム判定を実行
  ```python
  from kabusys.ai.regime_detector import score_regime
  from datetime import date

  score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")
  ```

- 監査ログ用 DB を初期化する
  ```python
  from kabusys.data.audit import init_audit_db

  audit_conn = init_audit_db("data/audit.duckdb")
  # 必要に応じてこの audit_conn をアプリの監査用に再利用
  ```

- RSS を取得する（ニュースコレクタの低レイヤーユーティリティ）
  ```python
  from kabusys.data.news_collector import fetch_rss

  articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
  for a in articles:
      print(a["id"], a["title"], a["datetime"])
  ```

注意点:
- score_news / score_regime は OpenAI API キーが必要です（引数に api_key を渡すか環境変数 OPENAI_API_KEY を設定）。
- run_daily_etl 等は J-Quants の認証トークンを内部で取得します（JQUANTS_REFRESH_TOKEN が必須）。
- 実行時はログを確認し、必要なテーブルスキーマが DuckDB に存在することを確認してください（初期スキーマ作成関数等が別途用意されている想定です）。

---

## ディレクトリ構成

（src/kabusys 下を抜粋）

- src/kabusys/__init__.py
  - パッケージの公開モジュール一覧、バージョン定義
- src/kabusys/config.py
  - 環境変数 / .env 自動読み込み、Settings クラス（アプリ設定）
- src/kabusys/ai/
  - __init__.py
  - news_nlp.py : 銘柄別ニュースの LLM スコアリング（score_news）
  - regime_detector.py : ETF MA とマクロ LLM を合成した市場レジーム判定（score_regime）
- src/kabusys/data/
  - __init__.py
  - jquants_client.py : J-Quants API クライアント（fetch / save）
  - pipeline.py : ETL パイプライン（run_daily_etl 等）
  - etl.py : ETLResult の再エクスポート
  - news_collector.py : RSS 収集・前処理ユーティリティ
  - calendar_management.py : マーケットカレンダー管理と判定ロジック
  - quality.py : データ品質チェック（check_missing_data, check_spike, ...）
  - stats.py : 共通統計ユーティリティ（zscore_normalize）
  - audit.py : 監査ログ（テーブル DDL / 初期化ユーティリティ）
- src/kabusys/research/
  - __init__.py
  - factor_research.py : モメンタム / ボラティリティ / バリューの計算
  - feature_exploration.py : 将来リターン計算、IC、統計サマリー、ランク付け
- src/kabusys/ai/__init__.py, src/kabusys/research/__init__.py などで必要 API をエクスポート

---

## 実装上の注意・運用メモ

- .env の自動ロードはプロジェクトルート（.git または pyproject.toml）を探索して行います。自動ロードを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- J-Quants API の呼び出しはモジュール内でレート制御とリトライを実装しています。429/408/5xx は指数バックオフでリトライ、401 はトークンリフレッシュを試みます。
- OpenAI 呼び出しは gpt-4o-mini を想定した JSON レスポンスモードを使用しています。API エラーや JSON パース失敗時はフェールセーフ（スコア 0.0）で継続します。
- DuckDB の executemany に空リストを渡すとエラーになるバージョンが存在するため、実装内で空チェックを行っています。
- ニュース収集は SSRF 対策・受信サイズ制限・gzip 解凍上限など安全性に配慮した実装です。

---

## 貢献 / 開発

- コードの変更はローカルでテストを行い、DuckDB のスキーマやテストデータを用意して動作確認してください。
- 自動ロードされる .env は機密情報を含むため Git 管理しないでください（.env は .gitignore に追加することを推奨）。

---

もし README に追加してほしい具体的なコマンド例、CI 設定例やテーブル定義（DDL）サンプル、あるいは特定のモジュールの API リファレンスなどがあれば教えてください。必要に応じて追記・詳細化します。