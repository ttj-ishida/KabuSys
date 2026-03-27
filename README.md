# KabuSys

KabuSys は日本株のデータパイプライン・リサーチ・自動売買に関する共通ライブラリ群です。  
ETL（J-Quants からのデータ取り込み）、ニュース収集／NLP（OpenAI を利用したセンチメント評価）、ファクター計算、マーケットカレンダー管理、監査ログ（発注・約定トレース）など、取引システム／リサーチ基盤で必要となる機能をモジュール化して提供します。

主要な設計方針
- ルックアヘッドバイアス防止（内部で date.today() / datetime.today() を直接参照しない等）
- DuckDB を中心としたローカル DB によるデータ永続化（冪等保存）
- 外部 API 呼び出しにはリトライやレート制御を実装
- OpenAI（gpt-4o-mini）を用いた JSON Mode による厳格なレスポンス設計
- テスト容易性のため API 呼び出しや時間関数を差し替え可能に設計

---

## 主な機能一覧
- 設定管理
  - .env / .env.local / 環境変数から設定を読み込む（自動ロード機構あり）
- データ ETL（kabusys.data.pipeline / etl）
  - J-Quants API 経由の株価・財務・カレンダー差分取得と保存
  - 品質チェック（欠損、スパイク、重複、日付不整合）
- J-Quants クライアント（kabusys.data.jquants_client）
  - 認証（リフレッシュトークン → id_token）
  - ページネーション対応のデータ取得
  - レート制御・リトライ・ID トークンの自動リフレッシュ
  - DuckDB への冪等保存（raw_prices, raw_financials, market_calendar 等）
- ニュース収集（kabusys.data.news_collector）
  - RSS フィードの取得、前処理、raw_news への冪等保存、SSRF・gzip・XML 攻撃対策
- ニュース NLP（kabusys.ai.news_nlp）
  - 指定ウィンドウのニュースを銘柄毎に集約し、OpenAI によるセンチメントスコアを ai_scores テーブルへ保存
  - バッチ・トークン肥大化対策、詳細なレスポンスバリデーションとリトライ
- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF(1321) の 200 日移動平均乖離（70%）とマクロニュースセンチメント（30%）を合成して市場レジームを判定
- リサーチ（kabusys.research）
  - ファクター計算（モメンタム、バリュー、ボラティリティ等）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリー
- マーケットカレンダー管理（kabusys.data.calendar_management）
  - JPX カレンダーの取得・保存・営業日判定・前後の営業日取得等
- 監査ログ・トレーサビリティ（kabusys.data.audit）
  - signal → order_request → execution の階層的監査テーブルの初期化・運用支援
- ユーティリティ（kabusys.data.stats など）
  - Z-score 正規化等の共通統計関数

---

## セットアップ（開発環境）
動作には Python 3.10+ を想定しています。以下は開発時の最小手順例です。

1. リポジトリをクローンし、仮想環境を作成
   ```
   git clone <このリポジトリ>
   cd <repo>
   python -m venv .venv
   source .venv/bin/activate   # Windows: .venv\Scripts\activate
   ```

2. 必要パッケージをインストール（例）
   ```
   pip install duckdb openai defusedxml
   ```
   - 実際のプロジェクトでは requirements.txt / pyproject.toml を参照してインストールしてください。

3. 環境変数の設定
   - プロジェクトルートに `.env` / `.env.local` を配置することで自動的に読み込まれます（読み込み順: OS 環境 > .env.local > .env）。
   - 自動ロードを無効にする場合:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```
   - 主な環境変数（必須箇所）
     - JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン（必須）
     - OPENAI_API_KEY — OpenAI API キー（score_news / score_regime の未指定時に参照）
     - KABU_API_PASSWORD — kabu API 用パスワード（システム連携用）
     - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID — 通知用
     - DUCKDB_PATH — デフォルト "data/kabusys.duckdb"
     - SQLITE_PATH — 監視 DB 等 "data/monitoring.db"
     - KABUSYS_ENV — "development" | "paper_trading" | "live"（デフォルト "development"）
     - LOG_LEVEL — "DEBUG" | "INFO" | "WARNING" | "ERROR" | "CRITICAL"

---

## 使い方（主要サンプル）
以下は各主要 API の使い方例（Python スクリプト内で呼び出す想定）。

- DuckDB 接続の例
  ```py
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL を実行（run_daily_etl）
  ```py
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  # ETL を target_date（省略時は今日）で実行
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメントをスコアリングして ai_scores に保存
  ```py
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  # OPENAI_API_KEY を環境変数に設定しておくか、api_key 引数に指定
  n_written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"written: {n_written}")
  ```

- 市場レジームを判定して market_regime テーブルに保存
  ```py
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログスキーマの初期化（監査専用 DB を作る）
  ```py
  from kabusys.data.audit import init_audit_db

  audit_conn = init_audit_db("data/audit_duckdb.duckdb")
  ```

- J-Quants の id_token を明示的に取得する
  ```py
  from kabusys.data.jquants_client import get_id_token

  id_token = get_id_token()  # settings.jquants_refresh_token を使用
  ```

注意点
- OpenAI の呼び出しは外部 API なのでテスト時は該当呼び出し関数をモックする想定（各モジュール内で差し替え可能）。
- ETL / 保存処理は冪等化されているため、複数回実行しても既存データは更新扱いになります。

---

## ディレクトリ構成（抜粋）
以下はソース内の主なファイルと役割の一覧（本 README に掲載されたコードベースに基づく抜粋）。

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数 / .env 自動読み込み / settings オブジェクト
  - ai/
    - __init__.py
    - news_nlp.py
      - ニュース記事の集約・OpenAI による銘柄別スコアリング
    - regime_detector.py
      - ETF の MA とマクロニュースで市場レジームを判定
  - data/
    - __init__.py
    - jquants_client.py
      - J-Quants API クライアント（認証・取得・保存）
    - pipeline.py
      - 日次 ETL 実行ロジック（run_daily_etl 等）
    - etl.py
      - ETL 結果型の再エクスポート（ETLResult）
    - news_collector.py
      - RSS 取得・前処理・raw_news 保存（SSRF 対策等）
    - calendar_management.py
      - market_calendar 管理、営業日判定、calendar_update_job
    - quality.py
      - データ品質チェック（欠損・スパイク・重複・日付不整合）
    - stats.py
      - zscore_normalize 等の統計ユーティリティ
    - audit.py
      - 監査ログ（signal_events, order_requests, executions）スキーマ定義・初期化
  - research/
    - __init__.py
    - factor_research.py
      - モメンタム、バリュー、ボラティリティ等の計算
    - feature_exploration.py
      - 将来リターン、IC、統計サマリー、ランク関数
  - ai/__init__.py, research/__init__.py, data/__init__.py などはパブリック API を整理

---

## テスト／開発メモ
- OpenAI 呼び出し箇所（news_nlp._call_openai_api / regime_detector._call_openai_api）はユニットテストで patch して差し替え可能です。
- network IO を伴う関数（fetch_rss、jquants_client._request 等）は統合テストでのみ実行するか、HTTP レスポンスをモックしてテストしてください。
- DuckDB に対する executemany の空リスト扱いなど、バージョン依存の挙動に注意（コード内に互換対策があります）。

---

## 最後に
この README はコードベースの主要な使い方と構成をまとめたものです。実運用ではさらに以下を用意してください：
- .env.example（必須環境変数のテンプレート）
- CI 用の秘匿情報管理（API キーはシークレットストアを利用）
- 運用手順書（ETL スケジュール、監視／アラート設計）

ご要望があれば、README を実例付きのチュートリアル（初回 ETL 実行、監査 DB の確認、ニューススコア確認）に展開します。必要な出力形式（Markdown、プレーンテキスト等）があればお知らせください。