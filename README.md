# KabuSys

日本株向けのデータ基盤・リサーチ・自動売買支援ライブラリです。  
DuckDB をデータ層に用い、J-Quants / RSS / OpenAI（LLM）などと連携してデータの取得・品質チェック・特徴量計算・ニュースセンチメント評価・市場レジーム判定・監査ログ管理などを行うことを目的としています。

バージョン: 0.1.0

---

## 主要な特徴

- データ収集（J-Quants API）と差分ETLパイプライン（株価 / 財務 / カレンダー）
- ニュース収集（RSS）と記事前処理（SSRF対策、トラッキング除去）
- ニュースの LLM ベースセンチメントスコアリング（gpt-4o-mini, JSON Mode）
- 市場レジーム判定（ETF 1321 の MA とマクロニュースの合成）
- ファクター計算（モメンタム / バリュー / ボラティリティ 等）
- 研究用ユーティリティ（将来リターン計算、IC、統計サマリー、Zスコア正規化）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（signal / order_request / executions）テーブル定義と初期化ユーティリティ
- 環境変数管理（.env 自動読み込み機能、テスト時に無効化可能）

---

## 依存関係（主なもの）

- Python 3.10+
- duckdb
- openai (OpenAI Python SDK)
- defusedxml
- 標準ライブラリの urllib, json, datetime など

（本リポジトリに requirements.txt / pyproject.toml がある前提で、そちらを利用してください。なければ上記パッケージをインストールしてください。）

---

## セットアップ手順（ローカル開発用）

1. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate（Windows の場合 .venv\Scripts\activate）

2. 必要パッケージをインストール
   - pip install duckdb openai defusedxml
   - （プロジェクトに pyproject.toml や requirements.txt があればそれに従う）
   - 開発中にパッケージのソースから直接使いたい場合:
     - pip install -e .

3. 環境変数を設定
   - プロジェクトルートに `.env` または `.env.local` を置くと自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を指定すると自動ロードを無効化できます）。
   - 必須環境変数（主なもの）:
     - JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン（必須）
     - KABU_API_PASSWORD — kabuステーション API のパスワード（必須）
     - SLACK_BOT_TOKEN — Slack 通知用 Bot トークン（必須）
     - SLACK_CHANNEL_ID — Slack チャンネル ID（必須）
     - OPENAI_API_KEY — OpenAI API キー（score_news / score_regime 実行時に引数でも指定可）
   - オプション / デフォルト:
     - KABUSYS_ENV — development / paper_trading / live（デフォルト: development）
     - LOG_LEVEL — DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
     - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH — 監視用 SQLite DB（デフォルト: data/monitoring.db）
   - .env の書式は一般的な KEY=VALUE をサポートし、export KEY=val の形式やクォート内のエスケープも処理されます。

4. データベース用ディレクトリを作成（必要に応じて）
   - mkdir -p data

---

## 使い方（代表的なユースケース）

以下は Python API を直接呼び出す例です。適宜 logging 設定やエラーハンドリングを行ってください。

- DuckDB 接続を作る例
  - import duckdb
  - conn = duckdb.connect(str(Path("data/kabusys.duckdb")))

- 日次 ETL を実行する（株価・財務・カレンダー取得 + 品質チェック）
  - from kabusys.data.pipeline import run_daily_etl
  - from datetime import date
  - result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  - print(result.to_dict())

- 株価日足のみの差分 ETL を実行
  - from kabusys.data.pipeline import run_prices_etl
  - fetched, saved = run_prices_etl(conn, target_date=date(2026, 3, 20))

- ニュースセンチメント（AI）スコアを計算して ai_scores に書き込む
  - from kabusys.ai.news_nlp import score_news
  - from datetime import date
  - count = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
  - print(f"scored {count} codes")

- 市場レジーム判定（1321 MA + マクロニュース）
  - from kabusys.ai.regime_detector import score_regime
  - score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")

- 監査ログ用 DB 初期化（監査専用 DuckDB ファイル）
  - from kabusys.data.audit import init_audit_db
  - audit_conn = init_audit_db("data/audit.duckdb")  # :memory: も可

- カレンダー更新バッチ実行（JPX カレンダーを J-Quants から取得）
  - from kabusys.data.calendar_management import calendar_update_job
  - saved = calendar_update_job(conn)  # lookahead のデフォルトは 90 日

- データ品質チェック（単体）
  - from kabusys.data.quality import run_all_checks
  - issues = run_all_checks(conn, target_date=date(2026, 3, 20))
  - for i in issues: print(i)

注意点:
- OpenAI を使う関数（score_news / score_regime）は api_key を引数で渡すか、環境変数 OPENAI_API_KEY を設定する必要があります。未設定時は ValueError が発生します（明示的に捕捉してください）。
- ETL / API 呼び出しはリトライ / レート制御実装あり。J-Quants はレート制限 (120 req/min) を順守する仕組みがあります。
- DuckDB に対する INSERT は可能な限り冪等に設計されています（ON CONFLICT DO UPDATE 等）。

---

## 環境変数一覧（主要）

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabu API 用パスワード
- KABU_API_BASE_URL — kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack Bot トークン（通知などで使用）
- SLACK_CHANNEL_ID (必須) — Slack チャンネル ID
- OPENAI_API_KEY — OpenAI API キー（score_news / regime_detector で使用）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite ファイル（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 環境識別（development / paper_trading / live）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 を設定すると .env 自動読み込みを無効にする

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py — パッケージ初期化、バージョン情報
- config.py — 環境変数/設定管理（.env 自動ロード、Settings クラス）
- ai/
  - __init__.py
  - news_nlp.py — ニュースの LLM センチメントスコアリング（ai_scores へ保存）
  - regime_detector.py — マーケットレジーム判定ロジック（1321 MA + マクロ記事）
- data/
  - __init__.py
  - calendar_management.py — 市場カレンダー管理 / 営業日判定 / カレンダー更新ジョブ
  - etl.py — ETL インターフェース再エクスポート
  - pipeline.py — ETL パイプライン（run_daily_etl / 個別 ETL ジョブ）
  - stats.py — 汎用統計ユーティリティ（zscore_normalize）
  - quality.py — データ品質チェック（欠損・スパイク・重複・日付不整合）
  - audit.py — 監査ログ（テーブル定義 / 初期化）
  - jquants_client.py — J-Quants API クライアント（取得・保存・認証・レート管理）
  - news_collector.py — RSS 収集 / 前処理 / SSRF 対策 / raw_news 保存
- research/
  - __init__.py
  - factor_research.py — ファクター計算（momentum/value/volatility）
  - feature_exploration.py — 将来リターン / IC / 統計サマリー / ランク
- ai モジュールと research モジュールは、研究・信号生成に必要な主要処理を提供します。

（README 上では主要ファイルを抜粋して紹介しています。実装の詳細は各モジュールの docstring を参照してください。）

---

## 運用上の注意 / 設計方針（要約）

- ルックアヘッドバイアス対策: 内部関数は datetime.today()/date.today() を直接参照せず、target_date を明示的に受け取って処理します。
- 冪等性: ETL の保存処理は可能な限り ON CONFLICT / DELETE+INSERT 等で冪等に実行されます。
- フェイルセーフ: LLM や API 呼び出しが失敗した場合、致命的な例外を避けるためフォールバック値を採る（例: macro_sentiment=0.0）か、ステップ単位でエラーを集約して上位に返します。
- セキュリティ: news_collector では SSRF 対策、gzip/サイズ制限、defusedxml を利用した安全な XML パースを実施しています。
- テスト容易性: OpenAI 呼び出しなどは内部のヘルパー関数をモック可能に実装しています（unittest.mock.patch 等で差し替えられる）。

---

## よくある利用フロー（例）

1. 初回セットアップ
   - .env を準備（J-Quants / OpenAI / Slack 等のキー）
   - DuckDB を作る（ファイルパスの親ディレクトリ作成）
   - audit DB を初期化（必要なら）

2. 夜間バッチ（スケジュール）
   - run_daily_etl を cron で実行してデータを取得・品質チェック
   - calendar_update_job を先に走らせカレンダーを更新する

3. 朝の処理
   - news_collector で RSS を収集 → raw_news 保存
   - score_news を実行して ai_scores を更新
   - score_regime を実行して market_regime を更新

4. リサーチ / モデル学習
   - research モジュールでファクター作成 → 正規化 → IC/forward returns を計算

5. 注文 / 監査
   - 戦略層が生成した信号を監査テーブル（signal_events）に記録し、order_requests 経由で発注 → executions に戻す流れで完全トレーサビリティを確保

---

## 開発 / 貢献

- コードの理解・修正は各モジュールの docstring を参照してください（各関数に詳細な説明と設計方針が書かれています）。
- テストを追加する際は、外部 API 呼び出し（OpenAI / J-Quants / ネットワーク）をモックして deterministic にしてください。
- .env 自動読み込みはテスト時に KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化できます。

---

問題や使い方の相談、追加ドキュメント希望があれば具体的なユースケース（どの関数をどう使いたいか、エラーの抜粋等）を教えてください。README や使用例の追記・改善をお手伝いします。