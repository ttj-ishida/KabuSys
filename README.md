# KabuSys

日本株向けの自動売買・データ基盤ライブラリ KabuSys の README。  
このリポジトリはデータ収集（ETL）、品質チェック、ニュースNLP、リサーチ（ファクター）、
監査ログ、及び市場レジーム判定などのユーティリティ群を提供します。

---

## プロジェクト概要

KabuSys は日本株の自動売買システムを構成するためのユーティリティライブラリ群です。  
主な目的は以下です。

- J-Quants からの株価・財務・マーケットカレンダーの差分取得（ETL）
- 取得データの品質チェック（欠損・スパイク・重複・日付不整合）
- RSS ベースのニュース収集と LLM による銘柄センチメント計測（news_nlp）
- マクロニュースと ETF（1321）のMA乖離を組み合わせた市場レジーム判定（regime_detector）
- 研究用のファクター計算・特徴量探索（research パッケージ）
- 発注〜約定の監査ログスキーマ初期化・管理（audit）
- DuckDB を使ったローカルデータベース中心の設計（look-ahead bias を考慮）

設計方針の例：
- 直接現在時刻を参照しない（ルックアヘッドバイアス防止）
- 外部 API 呼び出しは段階的にリトライ・フェイルセーフで扱う
- DuckDB 上に冪等性を保った保存ロジックを実装

---

## 機能一覧

主なモジュールと提供機能（抜粋）:

- kabusys.config
  - .env/.env.local の自動読み込み（プロジェクトルート検出）
  - 環境変数のラッピング（settings オブジェクト）
- kabusys.data
  - jquants_client: J-Quants API 呼び出し（取得・保存・認証リフレッシュ・レート制御）
  - pipeline: 日次 ETL 実行（run_daily_etl）
  - quality: データ品質チェック群（check_missing_data, check_spike, ...）
  - news_collector: RSS 取得と raw_news への保存ロジック（SSRF / XML Bomb 対策付き）
  - calendar_management: 市場カレンダー（営業日判定/次営業日/期間内営業日取得）
  - audit: 監査ログスキーマ初期化（init_audit_schema / init_audit_db）
  - stats: 汎用統計（zscore_normalize）
- kabusys.ai
  - news_nlp.score_news: 銘柄ごとのニュースセンチメントを取得して ai_scores に書き込む
  - regime_detector.score_regime: ETF（1321）のMA乖離 + マクロニュースで市場レジーム判定
- kabusys.research
  - factor_research: calc_momentum / calc_value / calc_volatility
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank

---

## セットアップ手順

下記は開発／実行に必要な最低限の手順（環境に応じて調整してください）。

1. Python 環境の準備（推奨: venv）
   ```
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

2. 必要なパッケージをインストール
   （本リポジトリに requirements.txt が無い場合の代表例）
   ```
   pip install duckdb openai defusedxml
   ```
   - duckdb: DB ストレージ／クエリ実行
   - openai: LLM 呼び出し（gpt-4o-mini 等）
   - defusedxml: RSS の安全なパース

3. 環境変数の設定
   プロジェクトルートに `.env`（および開発専用に `.env.local`）を置くと自動で読み込まれます。
   必要な環境変数（一例）:
   ```
   # J-Quants
   JQUANTS_REFRESH_TOKEN=xxxxx

   # OpenAI
   OPENAI_API_KEY=sk-...

   # kabuステーション（発注等を行う場合）
   KABU_API_PASSWORD=...

   # Slack（通知）
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567

   # DB パス（任意）
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db

   # 実行環境
   KABUSYS_ENV=development      # development / paper_trading / live
   LOG_LEVEL=INFO
   ```
   自動ロードを無効化する場合:
   ```
   export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
   ```

4. プロジェクトルート検出について
   - config モジュールは __file__ を基点に親ディレクトリを探索し、`.git` または `pyproject.toml` を検出してプロジェクトルートとみなします。
   - そのルートに `.env` / `.env.local` を置くと自動的に読み込みます。

---

## 使い方（基本例）

以下は主要な機能の簡単な利用例です。実行前に環境変数（特に JQUANTS_REFRESH_TOKEN と OPENAI_API_KEY）を設定してください。

- DuckDB 接続を作成して ETL を実行する例:
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect('data/kabusys.duckdb')
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメントをスコアリングして ai_scores に書き込む:
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect('data/kabusys.duckdb')
  # OPENAI_API_KEY は環境変数か api_key 引数で渡す
  written = score_news(conn, target_date=date(2026,3,20))
  print(f"wrote {written} scores")
  ```

- 市場レジーム判定（1321 の MA200 乖離 + マクロニュース）:
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect('data/kabusys.duckdb')
  score_regime(conn, target_date=date(2026,3,20))
  ```

- 監査ログ DB を初期化する:
  ```python
  from kabusys.data.audit import init_audit_db

  conn = init_audit_db("data/audit.duckdb")
  # conn は初期化済みの DuckDB 接続
  ```

- ファクター計算（research）:
  ```python
  from datetime import date
  import duckdb
  from kabusys.research.factor_research import calc_momentum

  conn = duckdb.connect('data/kabusys.duckdb')
  res = calc_momentum(conn, target_date=date(2026,3,20))
  # res は各銘柄ごとの dict のリスト
  ```

注意:
- OpenAI 呼び出しはコストとレート制限があるため、本番で実行する場合は適切に制御してください（バッチング・リトライロジックは実装済み）。
- J-Quants API 使用時は rate limit と認証（refresh token）の取り扱いに注意してください。

---

## ディレクトリ構成

主要なソース構成（リポジトリの src/kabusys 以下）:

- src/kabusys/
  - __init__.py
  - config.py                          # 環境変数・設定読み込みロジック（.env 自動ロード含む）
  - ai/
    - __init__.py
    - news_nlp.py                       # ニュースセンチメント解析（OpenAI）
    - regime_detector.py                # 市場レジーム判定（1321 MA + マクロニュース）
  - research/
    - __init__.py
    - factor_research.py                # Momentum / Value / Volatility 等
    - feature_exploration.py            # forward returns, IC, summary
  - data/
    - __init__.py
    - jquants_client.py                 # J-Quants API クライアント（取得/保存/認証/リトライ）
    - pipeline.py                       # ETL パイプライン（run_daily_etl 等）
    - etl.py                            # ETLResult 公開
    - quality.py                        # データ品質チェック
    - news_collector.py                 # RSS 収集（SSRF防止・XML安全化）
    - calendar_management.py            # 市場カレンダー管理（営業日判定等）
    - stats.py                          # 統計ユーティリティ（zscore_normalize 等）
    - audit.py                          # 監査ログスキーマ初期化 / init_audit_db
  - (その他: strategy, execution, monitoring 用のプレースホルダが __all__ にあり得る)

（上記は本リポジトリの主要ファイルを抜粋したものです。実際のリポジトリには追加ファイルやテストが含まれる場合があります。）

---

## 注意点・運用上のヒント

- 環境（KABUSYS_ENV）は "development" / "paper_trading" / "live" のいずれかを指定してください。live 実行時は特に取り扱いに注意。
- LLM（OpenAI）や外部 API（J-Quants）呼び出しは外部料金・レート制限があります。テストや開発時は小さいデータ範囲で実行してください。
- ニュース収集は外部 RSS を解析するため、RSS の仕様差やエンコーディング等に注意してください。defusedxml を使用して XML 攻撃対策は行っていますが、運用時の監視は必要です。
- DuckDB のバージョン差異で executemany の挙動に依存する箇所があるため、動作確認済みの DuckDB バージョンを使用してください。
- database ファイル（DUCKDB_PATH）をバックアップ・バージョニングしておくとデータ監査に便利です。

---

必要に応じて README に以下の付録を追加します：
- .env.example のサンプル
- 代表的なユースケース（cron ジョブ例、Airflow タスク例）
- 詳細な API 使用フロー（J-Quants の pagination や OpenAI バッチサイズのチューニング指南）

追加で欲しい内容（例: .env.example、cron 例、具体的なコマンド例）を教えてください。