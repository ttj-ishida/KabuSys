# KabuSys

日本株向けのデータ基盤・リサーチ・自動売買補助ライブラリ集です。  
DuckDB を用いた時系列データ管理、J-Quants からの ETL、ニュース収集・NLU（OpenAI）によるスコアリング、研究用ファクター計算、監査ログ（発注トレース）などを提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株のデータ取得（J-Quants）・保存（DuckDB）・品質チェック・ニュース収集・AI によるニュースセンチメント評価・ファクター計算・市場レジーム判定・監査ログ作成などを統合するライブラリです。  
設計上、バックテスト時のルックアヘッドバイアスを避けるために「現在時刻を直接参照しない」ことや、ETL の冪等性、API リトライ・レート制御、SSRF 対策などを重視しています。

主な用途:
- 日次 ETL（株価 / 財務 / カレンダー）
- ニュース収集と銘柄別センチメントスコア生成（OpenAI）
- 市場レジーム判定（ETF + マクロニュース）
- ファクター計算・特徴量探索（研究用途）
- 発注から約定までの監査ログ（監査テーブル初期化）

---

## 機能一覧

- 設定管理
  - .env 自動ロード（プロジェクトルート検出）と必須環境変数検証（kabusys.config）
- データ取得・保存（J-Quants）
  - 株価日足、財務データ、上場情報、マーケットカレンダーの取得と DuckDB 保存（kabusys.data.jquants_client）
  - レート制限、トークン自動リフレッシュ、リトライ実装
- ETL
  - 差分取得・バックフィル・品質チェックを含む日次 ETL（kabusys.data.pipeline）
- ニュース収集
  - RSS フィード収集、前処理、SSRF/サイズ/トラッキング除去対策（kabusys.data.news_collector）
- データ品質チェック
  - 欠損・スパイク・重複・日付不整合チェック（kabusys.data.quality）
- 監査ログ
  - signal_events / order_requests / executions テーブル定義と初期化ユーティリティ（kabusys.data.audit）
- AI（OpenAI）
  - ニュースセンチメント（銘柄ごと）スコア化（kabusys.ai.news_nlp）
  - マクロニュース + ETF MA200 を合成した市場レジーム判定（kabusys.ai.regime_detector）
- リサーチ
  - モメンタム / ボラティリティ / バリューなどのファクター計算、将来リターン計算、IC 計算、Z スコア正規化（kabusys.research, kabusys.data.stats）
- ユーティリティ
  - カレンダー管理と営業日判定（kabusys.data.calendar_management）
  - 設定管理（環境変数）と自動 .env 読み込み（kabusys.config）

---

## 必要要件（概略）

- Python 3.10 以上（型注釈に | 演算子を使用）
- 主要依存ライブラリ（例）
  - duckdb
  - openai
  - defusedxml
- 標準ライブラリ: urllib, json, datetime, logging 等

（実際の配布では requirements.txt / pyproject.toml を参照してください）

---

## セットアップ手順（簡易）

1. リポジトリをクローン / パッケージをインストール
   - 開発中: pip install -e .
   - 依存ライブラリ: pip install duckdb openai defusedxml

2. 環境変数（.env）を用意
   - プロジェクトルートの .env（または .env.local）に必要な値を設定します。自動読み込みはデフォルトで有効です（テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 必須の環境変数（kabusys.config.Settings で参照）
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - SLACK_BOT_TOKEN
     - SLACK_CHANNEL_ID
   - OpenAI を使う場合は:
     - OPENAI_API_KEY
   - 例 (.env):
     ```
     JQUANTS_REFRESH_TOKEN=xxxxx
     OPENAI_API_KEY=sk-xxxx
     KABU_API_PASSWORD=your_kabu_pass
     SLACK_BOT_TOKEN=xoxb-xxxx
     SLACK_CHANNEL_ID=C12345678
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     ```

3. DuckDB データベースの準備
   - 必要に応じて監査ログ用 DB を初期化:
     ```python
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")  # ":memory:" も可
     ```
   - ETL 用の DuckDB 接続を作成してスキーマを整備する（本リポジトリに schema init 関数がある前提の使用を想定）。

---

## 使い方（代表的な API と利用例）

以下はライブラリの主要な呼び出し例です。実行前に環境変数（特に API キー）が設定されていることを確認してください。

- 日次 ETL 実行（株価・財務・カレンダーの差分取得と品質チェック）
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメントスコア（銘柄別）生成（OpenAI 必須）
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  written = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
  print(f"wrote {written} scores")
  ```

- 市場レジーム判定（ETF 1321 の MA200 とマクロニュースを合成）
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")
  ```

- RSS フィードの取得（ニュース収集）
  ```python
  from kabusys.data.news_collector import fetch_rss
  articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
  for a in articles[:5]:
      print(a["id"], a["datetime"], a["title"])
  ```

- 監査スキーマの初期化（既存接続に追加）
  ```python
  from kabusys.data.audit import init_audit_schema
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")
  init_audit_schema(conn, transactional=True)
  ```

注意点:
- OpenAI 呼び出しは API 料金とレートに留意してください。
- J-Quants API は認証トークンやレート制限があるため設定値に従ってください。

---

## 環境変数（主要）

- JQUANTS_REFRESH_TOKEN — J-Quants の refresh token（必須）
- OPENAI_API_KEY — OpenAI API キー（AI 機能を使う場合必須）
- KABU_API_PASSWORD — kabu ステーション API パスワード（必須）
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN — Slack ボットトークン（必須）
- SLACK_CHANNEL_ID — Slack チャネル ID（必須）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite（監視用）パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 環境 ("development" | "paper_trading" | "live")
- LOG_LEVEL — ログレベル ("DEBUG" | "INFO" | ...)

自動 .env ロードを無効化する:
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py
- config.py                — 環境変数読み込み・設定管理
- ai/
  - __init__.py
  - news_nlp.py            — ニュースセンチメント（銘柄別）スコアリング
  - regime_detector.py     — 市場レジーム判定（ETF + マクロニュース）
- data/
  - __init__.py
  - jquants_client.py      — J-Quants API クライアント & DuckDB 保存
  - pipeline.py            — ETL パイプライン（run_daily_etl 等）
  - etl.py                 — ETL インターフェース再エクスポート
  - news_collector.py      — RSS 収集・前処理
  - quality.py             — データ品質チェック
  - stats.py               — 統計ユーティリティ（zscore_normalize）
  - calendar_management.py — 市場カレンダー管理（営業日判定等）
  - audit.py               — 監査ログスキーマ初期化（signal/order/execution）
- research/
  - __init__.py
  - factor_research.py     — Momentum/Value/Volatility の計算
  - feature_exploration.py — 将来リターン・IC・統計サマリー
- monitoring/ (※監視関連モジュールが存在する前提)
- strategy/ (戦略層インターフェース想定)
- execution/ (約定 / 発注関連想定)
- monitoring/ (監視・アラート関連想定)

---

## 開発・テスト時の注意

- DuckDB の SQL 実行はバージョン差で細かな挙動が異なる場合があります。開発環境では DuckDB の互換バージョンに注意してください。
- OpenAI と J-Quants の外部 API 呼び出しはテストでモックする設計になっており、各モジュールは呼び出し関数を差し替えやすく実装されています（例: news_nlp._call_openai_api を patch）。
- .env 自動ロードはプロジェクトルート（.git または pyproject.toml により検出）を基に行われます。パッケージ配布後も安全に動作するよう工夫されています。

---

この README はコードベースの現状を元にした概要・利用例をまとめたものです。細かな API の使用方法やスキーマ定義、追加のユーティリティは該当モジュールの docstring を参照してください。質問や補足があればお知らせください。