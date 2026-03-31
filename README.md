# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリです。  
ETL（J-Quants からの株価・財務・カレンダー取得）、ニュース収集・NLP（OpenAI を用いたセンチメント）、研究向けのファクター計算、監査テーブル（トレーサビリティ）、カレンダー管理などを備えています。

---

## 主要な機能一覧

- データ取得・保存（J-Quants API 経由）
  - 日次株価（OHLCV）、財務データ、JPX マーケットカレンダー等の差分取得と DuckDB への冪等保存（ON CONFLICT）
  - レートリミット制御、トークン自動リフレッシュ、リトライ/バックオフ実装

- ETL パイプライン
  - run_daily_etl による日次 ETL（カレンダー → 株価 → 財務 → 品質チェック）

- データ品質チェック
  - 欠損、重複、スパイク、将来日付 / 非営業日データ検出（QualityIssue オブジェクトで結果返却）

- ニュース収集
  - RSS フィード取得、前処理、raw_news への冪等保存、ニュースと銘柄の紐付け
  - SSRF / XML Bomb / 大容量レスポンス等への防御実装

- ニュース NLP（OpenAI）
  - 銘柄ごとのニュースをまとめて LLM（gpt-4o-mini）に投げ、クロスセクションの ai_score を ai_scores テーブルへ書き込み
  - API エラー・429・タイムアウト等に対するリトライとフェイルセーフ

- 市場レジーム判定（Regime Detector）
  - ETF 1321 の 200 日 MA 乖離（70%）とマクロニュースの LLM センチメント（30%）を合成して daily の市場レジーム（bull/neutral/bear）を保存

- 研究（Research）
  - Momentum / Value / Volatility などのファクター計算
  - 将来リターン計算、IC（スピアマンランク相関）、ファクター統計サマリー
  - z-score 正規化ユーティリティ

- 監査（Audit / Tracing）
  - signal_events, order_requests, executions の監査テーブル初期化ユーティリティ（DuckDB）
  - 発注フローのトレーサビリティを UUID で保証

---

## セットアップ手順

1. リポジトリをクローン（またはパッケージを展開）
   - 例: git clone <repo-url>

2. Python 環境を準備（推奨: venv）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - requirements.txt が無い場合は少なくとも以下をインストールしてください:
     - duckdb
     - openai
     - defusedxml
   - 例:
     - pip install duckdb openai defusedxml

   （プロジェクトに requirements.txt を用意する場合は pip install -r requirements.txt）

4. 環境変数の設定
   - プロジェクトルートに `.env` を置くと、自動的に読み込まれます（ただしテスト時など自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。
   - 必須の環境変数:
     - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
     - SLACK_BOT_TOKEN — Slack 通知を使う場合
     - SLACK_CHANNEL_ID — Slack 通知を使う場合
     - KABU_API_PASSWORD — kabuステーション API を使う場合のパスワード
     - OPENAI_API_KEY — OpenAI を利用する機能を使う場合（score_news / score_regime に必要）
   - データベース（任意、デフォルトを使う場合は作成不要）
     - DUCKDB_PATH (default: data/kabusys.duckdb)
     - SQLITE_PATH (default: data/monitoring.db) — 監視用 SQLite 等に使われる設定

   - .env の例（プロジェクトルート）:
     ```
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxx
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     KABU_API_PASSWORD=your_kabu_password
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db
     LOG_LEVEL=INFO
     KABUSYS_ENV=development
     ```

5. データベース用ディレクトリ作成（必要であれば）
   - mkdir -p data

---

## 主要な使い方（サンプル）

以下は簡単な利用例です。すべての例で共通して DuckDB 接続が必要です（duckdb.connect）。

- DuckDB へ接続する例:
  ```python
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL を実行する:
  ```python
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  # conn: duckdb connection
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースの NLP スコアを付与する（OpenAI API キー必須）:
  ```python
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  # OpenAI API キーは環境変数 OPENAI_API_KEY または api_key 引数で指定
  written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"wrote ai_scores for {written} codes")
  ```

- 市場レジーム査定を実行する:
  ```python
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  score_regime(conn, target_date=date(2026,3,20))
  ```

- 監査テーブル（order/signals/executions）を初期化する:
  ```python
  from kabusys.data.audit import init_audit_db

  # ファイルベースの DuckDB を初期化
  audit_conn = init_audit_db("data/audit.duckdb")
  ```

- 研究用関数の呼び出し例:
  ```python
  from datetime import date
  from kabusys.research.factor_research import calc_momentum

  records = calc_momentum(conn, target_date=date(2026,3,20))
  ```

注意点:
- OpenAI の呼び出し箇所はテストしやすいように内部関数をパッチしてモックできます（例: kabusys.ai.news_nlp._call_openai_api）。
- 自動環境読み込みを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト時に推奨）。

---

## よく使うユーティリティ / API

- kabusys.config.settings — 環境変数からの設定取得（必須キーを要求するプロパティあり）
- kabusys.data.pipeline.run_daily_etl — 日次 ETL パイプライン
- kabusys.data.jquants_client — J-Quants API 取得/保存ユーティリティ
- kabusys.data.quality.run_all_checks — データ品質チェック
- kabusys.data.news_collector.fetch_rss — RSS から記事を取り出すユーティリティ
- kabusys.ai.news_nlp.score_news — ニュースセンチメントのスコア付与（ai_scores への書き込み）
- kabusys.ai.regime_detector.score_regime — 市場レジーム判定と market_regime 書き込み
- kabusys.data.audit.init_audit_db / init_audit_schema — 監査用 DB 初期化

---

## テストとモックについて

- OpenAI API 呼び出しは _call_openai_api をモック（unittest.mock.patch）してテストできます：
  - kabusys.ai.news_nlp._call_openai_api
  - kabusys.ai.regime_detector._call_openai_api
- J-Quants API 呼び出しは kabusys.data.jquants_client._request をモックするか、get_id_token / fetch_* をスタブ化してテストしてください。
- 自動 .env ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化できます。

---

## ディレクトリ構成（抜粋）

プロジェクトは主要サブパッケージに分かれています。主なファイル／モジュール:

- src/kabusys/
  - __init__.py
  - config.py — 環境変数・設定管理
  - ai/
    - __init__.py
    - news_nlp.py — ニュースセンチメント解析、ai_scores への書込み
    - regime_detector.py — 市場レジーム判定
  - data/
    - __init__.py
    - calendar_management.py — 市場カレンダー管理、営業日ロジック
    - etl.py — ETL の公開インターフェース
    - pipeline.py — ETL パイプラインの実装（run_daily_etl 等）
    - stats.py — z-score 等の統計ユーティリティ
    - quality.py — データ品質チェック
    - audit.py — 監査テーブル (signal_events, order_requests, executions) の DDL/初期化
    - jquants_client.py — J-Quants API クライアント（fetch/save 実装）
    - news_collector.py — RSS 取得・前処理・保存
  - research/
    - __init__.py
    - factor_research.py — Momentum/Value/Volatility 等
    - feature_exploration.py — 将来リターン・IC・統計サマリー等

（上記は本リポジトリに含まれる主要ファイルの抜粋です）

---

## 運用上の注意点

- Look-ahead バイアス防止:
  - 内部ロジックは基本的に date.today() や datetime.today() を直接参照しないよう設計されています（target_date を引数で与える）。
  - ETL / 研究 / レジーム判定では、過去データのみを参照する条件を厳密に守っています。

- フォールバックとフェイルセーフ:
  - OpenAI や外部 API が失敗した場合、ゼロや None をフォールバックして処理を続行する設計箇所があります（ログ出力あり）。本番運用では失敗状況を監視・アラートしてください。

- DB 書き込みは冪等に設計されています（ON CONFLICT DO UPDATE や個別 DELETE → INSERT で部分失敗を回避）。

---

## ライセンス / 貢献

（ご自身のリポジトリのライセンスや貢献ルールをここに記述してください）

---

必要であれば、README にサンプル .env.example、requirements.txt、あるいはデプロイ手順（systemd / cron / Airflow など）を追記します。追加で必要な情報があれば教えてください。