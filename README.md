# KabuSys

日本株自動売買プラットフォームのコアライブラリ。  
データの取得・ETL、ニュースに基づくAIセンチメント解析、市場レジーム判定、リサーチ用ファクター計算、監査ログスキーマなどを提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は日本株の自動売買システムの基盤となるライブラリ群です。主な責務は以下です。

- J-Quants API からの株価・財務・カレンダー取得と DuckDB への保存（ETL）
- RSS ベースのニュース収集と前処理
- OpenAI（gpt-4o-mini）を用いたニュースのセンチメント解析（銘柄単位・マクロ）
- ETF（1321）200日移動平均などを用いた市場レジーム判定
- ファクター計算・特徴量探索（バックテスト／リサーチ用途）
- 監査ログ（signal → order_request → execution）のスキーマ初期化ユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付不整合）

設計ではルックアヘッドバイアス防止、冪等性、フェイルセーフ（API障害時はスキップ／デフォルト値を採用）を重視しています。

---

## 機能一覧

- data/
  - jquants_client: J-Quants API クライアント（取得・保存・レート制御・再試行）
  - pipeline: 日次 ETL（run_daily_etl）・個別 ETL ジョブ（株価／財務／カレンダー）
  - news_collector: RSS 収集・前処理（SSRF 対策・gzip 限度・トラッキング除去）
  - quality: データ品質チェック（欠損／スパイク／重複／日付不整合）
  - calendar_management: 営業日判定・next/prev_trading_day 等
  - audit: 監査ログ（DDL・インデックス作成・init_audit_db）
  - stats: zscore_normalize などの統計ユーティリティ
- ai/
  - news_nlp.score_news: ニュースを銘柄単位でスコア化して ai_scores に書き込む
  - regime_detector.score_regime: ETF 指標 + マクロセンチメントから市場レジームを判定
- research/
  - factor_research: calc_momentum, calc_value, calc_volatility
  - feature_exploration: calc_forward_returns, calc_ic, factor_summary, rank
- config:
  - Settings クラス: 環境変数読み込み（.env 自動読み込み機能含む）と設定アクセス

---

## セットアップ手順

1. リポジトリをクローン／パッケージを取得

2. Python 仮想環境を作成（推奨: Python 3.10+）
   ```
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

3. 依存パッケージをインストール  
   ※ requirements.txt がある場合はそれを利用します。なければ最低限以下が必要になります:
   - duckdb
   - openai
   - defusedxml

   例:
   ```
   pip install duckdb openai defusedxml
   ```

4. 環境変数を設定  
   プロジェクトルートに `.env` または `.env.local` を置くと自動で読み込まれます（優先度: OS 環境 > .env.local > .env）。自動読み込みを無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

   必須の環境変数（主要なもの）:
   - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
   - KABU_API_PASSWORD     : kabuステーション API パスワード（発注系で使用する想定）
   - SLACK_BOT_TOKEN       : Slack 通知用 bot token
   - SLACK_CHANNEL_ID      : Slack チャンネル ID
   - OPENAI_API_KEY        : OpenAI API キー（ai モジュール実行時に必要）
   - （任意）KABUSYS_ENV (development | paper_trading | live)
   - （任意）LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL)

   `.env` の例:
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
   OPENAI_API_KEY=sk-...
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   ```

5. データベースディレクトリを作成（必要なら）
   ```
   mkdir -p data
   ```

---

## 使い方（主要な例）

以下はライブラリの代表的な呼び出し例です。実行は仮想環境内で行ってください。

- DuckDB 接続例
  ```python
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL を実行（pipeline.run_daily_etl）
  ```python
  from kabusys.data.pipeline import run_daily_etl

  result = run_daily_etl(conn)
  print(result.to_dict())
  ```

- ニュースセンチメントスコア（前日15:00～当日08:30 JST ウィンドウ）
  ```python
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  n_written = score_news(conn, target_date=date(2026, 3, 20))
  print("書き込み銘柄数:", n_written)
  ```

- 市場レジーム判定（ETF 1321 の MA200 とマクロセンチメント合成）
  ```python
  from kabusys.ai.regime_detector import score_regime
  from datetime import date

  score_regime(conn, target_date=date(2026, 03, 20))
  ```

- 監査ログ DB 初期化（監査専用 DB ファイルを作る）
  ```python
  from kabusys.data.audit import init_audit_db

  audit_conn = init_audit_db("data/audit.duckdb")
  ```

- カレンダー判定ユーティリティ例
  ```python
  from kabusys.data.calendar_management import is_trading_day, next_trading_day
  from datetime import date

  d = date(2026, 3, 20)
  print(is_trading_day(conn, d))
  print(next_trading_day(conn, d))
  ```

- リサーチ用: モメンタム計算
  ```python
  from kabusys.research.factor_research import calc_momentum
  from datetime import date

  records = calc_momentum(conn, target_date=date(2026, 3, 20))
  ```

注意点:
- ai モジュール（news_nlp, regime_detector）は OpenAI API を呼び出します。OPENAI_API_KEY を設定するか、api_key 引数で渡してください。API 呼び出し失敗時はフェイルセーフとして 0.0 を返す処理が組まれています（例外を上げない挙動の箇所あり）。
- run_daily_etl は複数ステップ（calendar → prices → financials → quality）を順に実行し、部分的な失敗でも可能な範囲で処理を継続します。

---

## 実装上の注意・設計方針（抜粋）

- ルックアヘッドバイアス防止: 多くのモジュールで datetime.today()/date.today() を直接使わず、target_date を明示的に渡す設計。
- 冪等性: DB への保存は ON CONFLICT DO UPDATE（jquants_client.save_*）で実装。
- フェイルセーフ: 外部 API 失敗時は例外を上位に伝播させる箇所と、スコアをデフォルト化して継続する箇所があります（モジュールごとに明記）。
- セキュリティ対策: news_collector では SSRF 対策、XML の defusedxml 使用、レスポンスサイズ制限等を実施。

---

## ディレクトリ構成

（src/kabusys 以下の主なファイル/フォルダ）
```
kabusys/
├─ __init__.py
├─ config.py
├─ ai/
│  ├─ __init__.py
│  ├─ news_nlp.py
│  └─ regime_detector.py
├─ data/
│  ├─ __init__.py
│  ├─ jquants_client.py
│  ├─ pipeline.py
│  ├─ etl.py
│  ├─ news_collector.py
│  ├─ quality.py
│  ├─ calendar_management.py
│  ├─ stats.py
│  └─ audit.py
├─ research/
│  ├─ __init__.py
│  ├─ factor_research.py
│  └─ feature_exploration.py
└─ research/
```

主要な公開 API（一例）
- kabusys.config.settings
- kabusys.ai.news_nlp.score_news
- kabusys.ai.regime_detector.score_regime
- kabusys.data.pipeline.run_daily_etl
- kabusys.data.jquants_client.fetch_daily_quotes / save_daily_quotes / get_id_token
- kabusys.data.audit.init_audit_db / init_audit_schema
- kabusys.research.factor_research.calc_momentum / calc_value / calc_volatility
- kabusys.data.stats.zscore_normalize

---

## テスト・開発時のヒント

- 自動 .env 読み込みはプロジェクトルート（.git または pyproject.toml を基準）から行われます。テストの際は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を使って無効化できます。
- OpenAI 呼び出し箇所は unit test でモック（patch）しやすい構造になっています（内部の _call_openai_api を差し替えられます）。
- DuckDB をインメモリで使う場合は接続文字列に `":memory:"` を渡せます（audit.init_audit_db も対応）。

---

## 最後に

この README はコードベースの主要機能と使い方の導入を目的としています。実運用では各モジュールのログ出力・エラーハンドリング・テストケースを十分に整備し、必要に応じてパラメータ（スパイク閾値・API リトライポリシー等）をチューニングしてください。

問題点や改善提案があればコードコメントや PR で共有してください。