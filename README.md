# KabuSys

日本株向けのデータプラットフォームと自動売買基盤のコアモジュール集です。  
DuckDB を用いたデータ管理、J-Quants からの ETL、RSS ニュース収集・LLM によるニュースセンチメント解析、マーケットレジーム判定、監査ログ（発注→約定トレース）などの機能を提供します。

バージョン: 0.1.0

---

## 主な特徴（機能一覧）

- 環境設定の自動読み込み（プロジェクトルートの .env / .env.local）
- J-Quants API クライアント
  - 株価日足（OHLCV）取得・保存（ページネーション・再試行・レート制御対応）
  - 財務データ取得・保存
  - JPX マーケットカレンダー取得・保存
- ETL パイプライン
  - 日次 ETL（カレンダー → 株価 → 財務 → 品質チェック）
  - 差分取得 / バックフィル機能
  - 品質チェック（欠損・重複・スパイク・日付不整合）
- ニュース収集（RSS）
  - URL 正規化、SSRF 保護、gzip 制限、記事ID の冪等化
  - raw_news / news_symbols への保存に対応
- ニュース NLP（OpenAI）
  - 銘柄ごとのニュースをまとめて LLM に投げてセンチメントを算出し ai_scores に保存
  - バッチ・リトライ・レスポンス検証付き
- 市場レジーム判定
  - ETF（1321）の 200 日 MA 乖離とマクロニュースセンチメントを合成して日次レジーム判定
- 監査ログ（audit）
  - signal_events, order_requests, executions のスキーマと初期化ユーティリティ
  - 発注フローのトレーサビリティ（UUID ベースの冪等管理）
- 研究用ユーティリティ（research）
  - ファクター計算（Momentum / Volatility / Value）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリ、Z-score 正規化

---

## 必要条件

- Python 3.10 以上（構文に | 型注釈などを使用）
- 必要パッケージ（主なもの）
  - duckdb
  - openai
  - defusedxml
- ネットワーク接続（J-Quants / OpenAI / RSS ソース など）

※ 実行する機能によって追加パッケージが必要になる場合があります。

---

## セットアップ手順（ローカル開発用）

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境を作成・有効化
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 必要パッケージをインストール
   - 簡易：
     ```
     pip install duckdb openai defusedxml
     ```
   - またはプロジェクトに requirements.txt / pyproject.toml があればそちらを利用してください。

4. 環境変数設定
   - プロジェクトルート（.git または pyproject.toml が存在するディレクトリ）に `.env` または `.env.local` を置くと、自動で読み込まれます。
   - 自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

---

## 環境変数一覧（主要）

- JQUANTS_REFRESH_TOKEN (必須)  
  - J-Quants のリフレッシュトークン。ETL 等で使用。

- OPENAI_API_KEY (必須 for NLP)  
  - OpenAI の API キー（news_nlp / regime_detector で使用）。関数呼び出し時に api_key 引数で上書き可能。

- KABU_API_PASSWORD (必須 for execution)  
  - kabuステーション API のパスワード（発注実装で使用）。

- KABU_API_BASE_URL (任意)  
  - kabu API ベース URL。デフォルト: http://localhost:18080/kabusapi

- SLACK_BOT_TOKEN (必須 if notifications)  
  - Slack 通知に使用する Bot トークン。

- SLACK_CHANNEL_ID (必須 if notifications)  
  - Slack 通知先のチャンネル ID。

- DUCKDB_PATH (任意)  
  - デフォルトの DuckDB ファイルパス。デフォルト: data/kabusys.duckdb

- SQLITE_PATH (任意)  
  - 監視用 sqlite のデフォルトパス。デフォルト: data/monitoring.db

- KABUSYS_ENV (任意)  
  - 実行環境: development / paper_trading / live。デフォルト: development

- LOG_LEVEL (任意)  
  - ログレベル: DEBUG, INFO, WARNING, ERROR, CRITICAL。デフォルト: INFO

注意: 必須の環境変数が未設定の場合、kabusys.config.Settings プロパティは ValueError を送出します。

---

## 基本的な使い方（コード例）

以下は最小限の呼び出し例です。詳細な運用は用途に応じてラッパーやジョブスケジューラを作成してください。

- DuckDB 接続を作る（デフォルトファイルを使用）
  ```py
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL を実行する
  ```py
  from kabusys.data.pipeline import run_daily_etl

  result = run_daily_etl(conn)  # target_date を指定可能
  print(result.to_dict())
  ```

- ニュースセンチメントスコアを作成（ai_scores へ保存）
  ```py
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"書き込み銘柄数: {written}")
  # api_key 引数を渡すと OPENAI_API_KEY より優先される
  ```

- 市場レジーム判定を実行（market_regime へ保存）
  ```py
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査用 DuckDB を初期化する
  ```py
  from kabusys.data.audit import init_audit_db

  audit_conn = init_audit_db("data/audit.duckdb")
  # audit_conn を使って発注ログ周りを操作
  ```

- RSS フェッチ（ニュース収集機能の一部）
  ```py
  from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES

  articles = fetch_rss(DEFAULT_RSS_SOURCES["yahoo_finance"], source="yahoo_finance")
  for a in articles:
      print(a["id"], a["datetime"], a["title"])
  ```

各関数はドキュメンテーション文字列で振る舞い（再試行、フォールバック、エラーハンドリング）を説明しています。OpenAI への呼び出しは関数引数で api_key を注入可能で、テスト時には内部の _call_openai_api をモックできます。

---

## 運用上の注意点

- Look-ahead バイアス対策: 多くの関数は内部で現在日付を直接参照せず、引数で target_date を与える設計になっています。バックテスト等で利用する際は target_date を明示してください。
- API キーの管理: J-Quants の ID トークンは自動リフレッシュされますが、refresh token の保護は重要です。
- OpenAI 呼び出し: レートやコストに注意してください。news_nlp/regime_detector はリトライやフェイルセーフ（失敗時は中立スコア）を備えていますが、運用での監視が必要です。
- DuckDB の executemany はバージョンによって空リストを受け付けないため、モジュール内で保護処理があります。パッケージ依存性を固定して運用してください。

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py
  - config.py                          -- 環境変数 / 設定
  - ai/
    - __init__.py
    - news_nlp.py                       -- ニュース NLP（OpenAI 連携）
    - regime_detector.py                -- 市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py                 -- J-Quants API クライアント & 保存ロジック
    - pipeline.py                       -- ETL パイプライン（run_daily_etl 等）
    - etl.py                            -- ETLResult 再エクスポート
    - news_collector.py                 -- RSS ニュース収集
    - calendar_management.py            -- 市場カレンダー管理
    - stats.py                          -- 統計ユーティリティ（zscore）
    - quality.py                        -- データ品質チェック
    - audit.py                          -- 監査ログスキーマ / 初期化
  - research/
    - __init__.py
    - factor_research.py                -- ファクター計算（momentum/value/volatility）
    - feature_exploration.py            -- forward returns / IC / summary

（上記はこの README に含まれる主要モジュールの抜粋です）

---

README では主要な利用例と運用時の注意をまとめました。詳細は各モジュールの docstring を参照してください。問題報告や機能追加の提案はリポジトリの Issue をご利用ください。