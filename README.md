# KabuSys

日本株向け自動売買／データプラットフォーム用ライブラリ（KabuSys）。  
ETL、ニュース収集・NLP、ファクター計算、監査ログ、J-Quants / OpenAI連携など、バックテスト・実運用で必要となる主要機能を提供します。

> 注意: この README はソースツリー（src/kabusys）にあるモジュール群に基づいて作成しています。

---

## プロジェクト概要

KabuSys は日本株市場データの収集・品質管理から、ニュースセンチメント（LLM による分析）、市場レジーム判定、研究用ファクター計算、監査ログの管理までを統合したライブラリ群です。データは主に DuckDB に保持し、J-Quants API から株価・財務・市場カレンダーを取得します。OpenAI（gpt-4o-mini 等）を用いたニュースNLP・マクロセンチメント評価を行う機能も含まれます。

主な設計方針：
- ルックアヘッドバイアス防止（バックテストで現在日時の参照を避ける実装）
- 冪等性（DB 保存は ON CONFLICT / upsert）、堅牢なリトライ・フェイルセーフ
- 外部 API 呼び出しは明示的にキー注入可能（テスト容易性）
- 標準ライブラリ中心で実装、外部依存は最小限（ただし duckdb / openai / defusedxml 等は必要）

---

## 機能一覧

- 環境設定管理
  - .env / .env.local の自動ロード（プロジェクトルート検出）
  - 必須環境変数を Settings 経由で取得

- データ取得・ETL（kabusys.data.pipeline）
  - J-Quants から差分取得（株価日足 / 財務 / カレンダー）
  - 差分保存・品質チェック（quality モジュール）
  - run_daily_etl による一括 ETL 実行

- J-Quants クライアント（kabusys.data.jquants_client）
  - レートリミット管理、リトライ、トークン自動リフレッシュ
  - fetch / save のペア関数（raw_prices, raw_financials, market_calendar 等）

- ニュース収集（kabusys.data.news_collector）
  - RSS 収集、URL 正規化、SSRF 対策、gzip・サイズ制限、前処理
  - raw_news / news_symbols への冪等保存（設計済み）

- ニュース NLP（kabusys.ai.news_nlp）
  - OpenAI（gpt-4o-mini）を用いた銘柄別センチメント算出（ai_scores へ保存）
  - バッチ処理、JSON モード、リトライ、レスポンス検証

- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF 1321 の 200 日 MA 乖離 + マクロニュース LLM センチメントを合成して日次レジーム判定
  - market_regime テーブルへの冪等書き込み

- 研究・解析（kabusys.research）
  - モメンタム / ボラティリティ / バリュー 等のファクター計算
  - 将来リターン計算、IC（情報係数）、統計サマリー、Zスコア正規化

- カレンダー管理（kabusys.data.calendar_management）
  - market_calendar に基づく営業日判定、next/prev_trading_day、SQ 判定、夜間バッチ更新ジョブ

- データ品質チェック（kabusys.data.quality）
  - 欠損・重複・スパイク・日付不整合チェック、QualityIssue 形式で収集

- 監査ログ（kabusys.data.audit）
  - signal_events / order_requests / executions 等の監査テーブル定義・初期化
  - init_audit_db で専用 DuckDB を初期化可能

---

## セットアップ手順

前提
- Python 3.10+ を推奨（typing の近代的機能を使用）
- Git リポジトリルートに .env（/.env.local）を置く想定

1. リポジトリをクローンし、開発環境に移動:
   - git clone ...
   - cd <repo>

2. 仮想環境作成（推奨）:
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール:
   - pip install duckdb openai defusedxml
   - （開発用に setuptools / wheel / pytest 等を追加）

   注: 実行環境により追加の依存が必要な場合があります。requirements.txt があればそちらを使ってください。

4. (任意) パッケージを editable インストール:
   - pip install -e .

5. 環境変数の設定:
   - プロジェクトルートに .env または .env.local を作成するか、OS 環境変数を設定します。
   - 主要な環境変数（必須）
     - JQUANTS_REFRESH_TOKEN: J-Quants の refresh token
     - KABU_API_PASSWORD: kabu ステーション API パスワード（発注連携がある場合）
     - SLACK_BOT_TOKEN: Slack 通知用ボットトークン
     - SLACK_CHANNEL_ID: Slack チャネル ID
     - OPENAI_API_KEY: OpenAI 利用時（score_news / score_regime のデフォルト）
   - オプション
     - DUCKDB_PATH: デフォルト data/kabusys.duckdb
     - SQLITE_PATH: デフォルト data/monitoring.db
     - KABUSYS_ENV: development | paper_trading | live（デフォルト development）
     - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL
     - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env の自動ロードを無効化できます（テスト時に有用）

   サンプル .env:
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxx
   OPENAI_API_KEY=sk-...
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   ```

---

## 使い方（代表的な API と実行例）

以下はライブラリ内の主要ユーティリティを使うための Python スニペット例です。

- DuckDB 接続を作成して日次 ETL を実行する
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- OpenAI を使ったニューススコア計算（score_news）
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  # api_key を明示的に渡すか、環境変数 OPENAI_API_KEY を設定
  count = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
  print(f"scored {count} codes")
  ```

- 市場レジーム評価（score_regime）
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")
  ```

- 監査ログ用 DuckDB を初期化する
  ```python
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  ```

- Settings を使って環境変数を取得する
  ```python
  from kabusys.config import settings
  print(settings.duckdb_path)        # Path オブジェクト
  print(settings.is_live)           # 環境フラグ
  ```

注意点:
- OpenAI 呼び出しは api_key を引数で渡すか、OPENAI_API_KEY 環境変数を設定してください。空文字も未設定とみなされます。
- DuckDB の各テーブル（raw_prices, raw_financials, raw_news, news_symbols, ai_scores, market_regime 等）は ETL や初期化スクリプトで作成される想定です。スキーマは各モジュールに記載された DDL に従ってください。
- news_collector.fetch_rss は SSRF 対策やサイズチェックを実装しています。外部 RSS を扱う際は URL スキームが http/https であることを確認してください。

---

## ディレクトリ構成

主要モジュールのみ抜粋（src/kabusys 以下）：

- kabusys/
  - __init__.py
  - config.py                     # 環境変数 / Settings 管理、.env 自動ロード
  - ai/
    - __init__.py
    - news_nlp.py                  # ニュース NLP（銘柄別スコア、OpenAI）
    - regime_detector.py           # マクロ + MA200 による市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py            # J-Quants API client + save_* 関数
    - pipeline.py                  # ETL パイプライン run_daily_etl 等
    - etl.py                       # ETLResult 再エクスポート
    - news_collector.py            # RSS 取得、前処理、保存ロジック
    - calendar_management.py       # market_calendar 管理、営業日判定
    - quality.py                   # 品質チェック（欠損、スパイク、重複、日付不整合）
    - stats.py                     # zscore_normalize 等ユーティリティ
    - audit.py                     # 監査ログ用 DDL / 初期化
  - research/
    - __init__.py
    - factor_research.py           # momentum, value, volatility ファクター
    - feature_exploration.py       # forward returns, IC, summary, rank

---

## 運用・開発のヒント

- 自動環境読み込み:
  - config.py はパッケージファイル位置から .git または pyproject.toml を探索してプロジェクトルートを特定し、.env / .env.local を自動でロードします。自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

- OpenAI 呼び出しのテスト:
  - news_nlp._call_openai_api や regime_detector の内部 API 呼び出しはテストでモックしやすいよう設計されています（unittest.mock.patch を利用）。

- DuckDB への批量挿入:
  - DuckDB のバージョン差異（executemany の空リスト制約など）を考慮して実装されています。アップグレード時は互換性に注意してください。

- エラーハンドリング:
  - ETL や NLP は API エラー時に全処理が止まらないようにフェイルセーフ設計です（部分失敗でも他処理を継続）。結果オブジェクト（ETLResult）やログを確認して運用判断をしてください。

---

## ライセンス / 貢献

本リポジトリのライセンス情報や貢献方法はリポジトリのルートにある LICENSE / CONTRIBUTING を参照してください（存在しない場合はリポジトリ管理者に確認してください）。

---

README はここまでです。具体的な利用シナリオ（バッチ設定、ジョブスケジューラ設定、監視・Slack 通知フローなど）や DB スキーマの初期化手順が必要であれば、用途に合わせて追加のドキュメントを作成します。どの部分を詳しく書いてほしいか教えてください。