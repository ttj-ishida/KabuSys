# KabuSys

日本株向けのデータ基盤・研究・自動売買補助ライブラリ群です。  
データの ETL（J-Quants）、ニュース収集／NLP、ファクター計算、監査ログ、研究用ユーティリティ、簡易な市場レジーム判定などを提供します。

主な設計方針は「Look-ahead bias を防ぐ」「DuckDB を用いたローカル DB」「外部 API 呼び出しはリトライ／フェイルセーフ実装」「冪等性」です。

---

## 機能一覧

- 環境設定管理
  - .env / .env.local 自動読み込み（プロジェクトルート検出）
  - 必須環境変数の取得・バリデーション（Settings）
- データ ETL（kabusys.data.pipeline）
  - J-Quants API から日次株価、財務、マーケットカレンダーを差分取得・保存
  - 品質チェック（欠損・重複・スパイク・日付不整合）
  - 日次 ETL 実行エントリポイント（run_daily_etl）
- J-Quants クライアント（kabusys.data.jquants_client）
  - 認証（refresh_token → id_token）
  - ページネーション対応データ取得 / DuckDB への冪等保存
  - レートリミット管理・リトライ・401 自動リフレッシュ
- ニュース収集（kabusys.data.news_collector）
  - RSS フィード取得、URL 正規化、トラッキング除去、SSRF 対策、記事 ID 生成、raw_news へ保存（冪等）
- ニュース NLP（kabusys.ai.news_nlp）
  - 指定ウィンドウのニュースを銘柄ごとにまとめ、OpenAI（gpt-4o-mini）でセンチメントを取得して ai_scores に保存
  - API リトライ、レスポンスバリデーション、スコアクリップ
- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF 1321 の 200 日 MA 乖離 + マクロニュースの LLM センチメントを合成して市場レジームを日次で判定・保存
- 研究ユーティリティ（kabusys.research）
  - ファクター計算（モメンタム・バリュー・ボラティリティ）
  - 将来リターン計算、IC（Spearman）計算、統計サマリー
- 監査ログ（kabusys.data.audit）
  - signal_events, order_requests, executions の監査テーブル定義と初期化ユーティリティ
  - init_audit_schema / init_audit_db（DuckDB）
- 汎用統計（kabusys.data.stats）
  - Z スコア正規化など

---

## セットアップ手順

前提: Python 3.9+ を推奨（typing|duckdb|openai 等の互換性を考慮）。

1. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate (macOS / Linux) または .venv\Scripts\activate (Windows)

2. 依存パッケージをインストール
   - 必須例:
     - pip install duckdb openai defusedxml
   - プロジェクトに requirements.txt / pyproject.toml がある場合:
     - pip install -e . あるいは pip install -r requirements.txt

3. 環境変数を設定
   - プロジェクトルート（.git または pyproject.toml のある階層）に `.env` / `.env.local` を配置すると自動読み込みされます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すれば自動ロード無効）。
   - 必須環境変数（本コードで要求されるもの）:
     - JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン
     - KABU_API_PASSWORD — kabuステーション API パスワード（発注等で利用）
     - SLACK_BOT_TOKEN — Slack 通知用トークン
     - SLACK_CHANNEL_ID — Slack チャンネル ID
   - あると便利な環境変数:
     - OPENAI_API_KEY — OpenAI 呼び出し時に省略した場合に参照される
     - DUCKDB_PATH（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト data/monitoring.db）
     - PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
     - KABUSYS_ENV（development / paper_trading / live）
     - LOG_LEVEL（DEBUG/INFO/...）

   例 .env（最小）
   ```
   JQUANTS_REFRESH_TOKEN=your_refresh_token
   OPENAI_API_KEY=sk-...
   KABU_API_PASSWORD=your_pw
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C12345678
   ```

4. データディレクトリの準備（必要に応じて）
   - デフォルトの DuckDB ファイルパスは data/kabusys.duckdb。ディレクトリを作るか、init 関数が自動作成します。

---

## 使い方（簡単な例）

以下は Python REPL / スクリプトからの利用例です。OpenAI 用キーは環境変数（OPENAI_API_KEY）でも、関数引数で明示的に渡しても良いです。

- DuckDB 接続を作る:
  ```python
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")
  ```

- 日次 ETL 実行（株価・財務・カレンダー取得 + 品質チェック）:
  ```python
  from kabusys.data.pipeline import run_daily_etl
  from datetime import date
  res = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(res.to_dict())
  ```

- ニュース NLP スコア生成:
  ```python
  from kabusys.ai.news_nlp import score_news
  from datetime import date
  n = score_news(conn, target_date=date(2026, 3, 20))  # OPENAI_API_KEY を環境変数にセットしておく
  print(f"scored {n} codes")
  ```

- 市場レジーム判定:
  ```python
  from kabusys.ai.regime_detector import score_regime
  from datetime import date
  score_regime(conn, target_date=date(2026,3,20))  # OpenAI キーは引数でも可
  ```

- 監査ログ DB 初期化（専用 DB を作る場合）:
  ```python
  from kabusys.data.audit import init_audit_db
  audit_conn = init_audit_db("data/audit.duckdb")
  ```

- J-Quants の単体 API 呼び出し（例: 上場銘柄情報）
  ```python
  from kabusys.data.jquants_client import fetch_listed_info
  infos = fetch_listed_info()
  ```

- RSS フィード取得（ニュース収集の一部を試す）
  ```python
  from kabusys.data.news_collector import fetch_rss
  articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", "yahoo_finance")
  ```

注意点:
- AI による処理（news_nlp, regime_detector）は OpenAI API を呼びます。API キーと利用料に注意してください。
- news_collector は SSRF 対策や受信サイズ制限を実装しています。外部 URL の扱いには注意してください。
- run_daily_etl などは内部で date.today() を使う箇所があるため、再現性が重要な研究用途では target_date を明示してください（多くの処理は look-ahead bias を防ぐ設計になっています）。

---

## 主要モジュールの簡単説明

- kabusys.config
  - 環境変数の自動読み込み（.env / .env.local）と Settings クラス
- kabusys.data
  - jquants_client: J-Quants API の取得・保存、認証、レートリミット、保存用ユーティリティ
  - pipeline: ETL の実行フロー（run_daily_etl 等）と ETLResult
  - news_collector: RSS 取得・前処理・保存（SSRF 対策、トラッキング除去）
  - quality: データ品質チェック（欠損・重複・スパイク・日付不整合）
  - audit: 監査ログテーブルの定義と初期化
  - calendar_management: 市場カレンダーの判定・次営業日探索など
  - stats: zscore_normalize 等
- kabusys.ai
  - news_nlp: ニュースから銘柄ごとのセンチメント算出（OpenAI）
  - regime_detector: MA とマクロニュースを組合せた市場レジーム判定（OpenAI）
- kabusys.research
  - factor_research: momentum / value / volatility 計算
  - feature_exploration: forward returns / IC / summary / rank 等

---

## ディレクトリ構成（コードベースの抜粋）

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
    - quality.py
    - stats.py
    - calendar_management.py
    - audit.py
    - pipeline.py
    - etl.py
    - audit.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - monitoring/ (存在を __all__ に含むが本リポジトリでの詳細は個別実装による)

（README はソースの抜粋に基づく簡易ツリーです）

---

## 運用上の注意 / ベストプラクティス

- 環境変数は機密情報を含むため、`.env` をバージョン管理しないでください（`.env.example` を用意して鍵情報は除外）。
- OpenAI / J-Quants の API 呼び出しには費用が発生します。開発環境では小規模なテスト、paper_trading 環境を使う等を推奨します。
- run_daily_etl は部分失敗に強い設計ですが、ETLResult の has_errors / has_quality_errors を必ずチェックして運用判断を行ってください。
- DuckDB ファイルは定期的にバックアップしてください。監査ログは削除しない前提の設計です。
- unit tests のために .env 自動読み込みを無効化したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

必要であれば以下の追加情報を作成します:
- .env.example のサンプル
- デプロイ / systemd サービス定義例（ETL / execution のデーモン化）
- より詳細な API 使用例（jquants_client のパラメータ・返り値説明）
- 開発者向けのテスト実行手順

ご希望があれば教えてください。