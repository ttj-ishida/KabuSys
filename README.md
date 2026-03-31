# KabuSys

日本株向けのデータ基盤・リサーチ・自動売買補助ライブラリ群です。  
J-Quants / DuckDB を用いたデータ収集（ETL）・品質チェック、ニュースの NLP スコアリング（OpenAI）、市場レジーム判定、ファクター計算、監査ログ用スキーマ等のユーティリティを提供します。

---

目次
- プロジェクト概要
- 機能一覧
- 前提条件
- 環境設定（環境変数）
- セットアップ手順
- 使い方（主要 API の例）
- ディレクトリ構成
- 開発／テスト向けメモ

---

## プロジェクト概要

KabuSys は次を主眼に設計されたモジュール群です。

- J-Quants API から日本株データ（株価日足・財務・マーケットカレンダー）を取得して DuckDB に保存する ETL パイプライン
- raw_news を収集・前処理し、OpenAI によるニュースセンチメント解析を行って ai_scores に保存するニュース NLP
- ETF の移動平均乖離とマクロニュースの LLM センチメントを組み合わせた市場レジーム判定
- 研究用途のファクター計算（モメンタム、バリュー、ボラティリティ等）と特徴量解析ユーティリティ
- データ品質チェック（欠損・重複・スパイク・日付不整合検出）
- 監査ログ（signal/order/execution）用の DuckDB スキーマ初期化ユーティリティ

設計上、ルックアヘッドバイアスを避けるために内部で現在時刻を乱用しない、API のリトライ／フェイルセーフを組み込む、DuckDB による冪等保存を行う等が特徴です。

---

## 機能一覧

- データ取得・保存
  - J-Quants から daily_quotes（OHLCV）、financial_statements、market_calendar を差分取得・冪等保存
  - rate limiter / リトライ / トークン自動リフレッシュ対応
- ETL パイプライン
  - run_daily_etl()：カレンダー→株価→財務→品質チェック の一括実行
  - 個別 ETL（run_prices_etl / run_financials_etl / run_calendar_etl）
- データ品質チェック
  - 欠損データ、スパイク、重複、日付整合性検査
- ニュース収集・解析
  - RSS フィードからの収集（SSRF 対策・トラッキング除去・サイズ制限）
  - OpenAI（gpt-4o-mini など）によるバッチセンチメント（score_news）
  - チャンク単位・再試行ロジック・レスポンス検証
- 市場レジーム判定
  - ETF 1321 の 200日 MA 乖離 + マクロニュースセンチメントで日次レジームを判定（score_regime）
- 研究用ユーティリティ
  - calc_momentum / calc_value / calc_volatility（ファクター計算）
  - calc_forward_returns / calc_ic / factor_summary / rank / zscore_normalize
- 監査ログ
  - 監査用スキーマとインデックスを DuckDB に作成（init_audit_schema / init_audit_db）

---

## 前提条件

- Python 3.10 以上（型注釈と構文に依存）
- 主な依存パッケージ（最低限）
  - duckdb
  - openai
  - defusedxml
- ネットワーク接続（J-Quants API / RSS / OpenAI）および対応 API キー

（プロジェクトの配布方法に応じて requirements.txt / pyproject.toml からインストールしてください）

---

## 環境設定（環境変数）

自動でプロジェクトルートの `.env` と `.env.local`（存在すれば）を読み込みます。自動読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

必要（必須）な環境変数：
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
- KABU_API_PASSWORD      : kabuステーション API のパスワード（発注関連）
- SLACK_BOT_TOKEN        : Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID       : Slack チャンネル ID
- OPENAI_API_KEY         : OpenAI API キー（score_news / score_regime のデフォルト）
- （任意）KABUSYS_ENV    : development / paper_trading / live（デフォルト: development）
- （任意）LOG_LEVEL      : DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）
- データベースパス（任意、デフォルト値あり）
  - DUCKDB_PATH : DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
  - SQLITE_PATH : 監視用 SQLite（デフォルト data/monitoring.db）

例（.env）:
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-xxxx
KABU_API_PASSWORD=your_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=CXXXXXXX
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb

---

## セットアップ手順

1. リポジトリをクローン
   - git clone ... を実行（プロジェクトルートに pyproject.toml がある想定）

2. Python 仮想環境の作成
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   - pip install -U pip
   - pip install duckdb openai defusedxml
   - （プロジェクトの pyproject.toml / requirements.txt がある場合はそれに従ってください）
   - 開発用: pytest 等を追加でインストール

4. 環境変数 / .env の準備
   - プロジェクトルートに .env を作成し、上記の必須値を設定
   - 自動読み込みは config.py がプロジェクトルートを検出して行います

5. パッケージのインストール（ローカル開発）
   - プロジェクトルート（pyproject.toml がある場所）で:
     - pip install -e .

6. データディレクトリの作成（任意）
   - mkdir -p data

---

## 使い方（主要 API の例）

以下は Python REPL / スクリプトからの利用例です。実行前に必要な環境変数（特に OPENAI_API_KEY / JQUANTS_REFRESH_TOKEN）を設定してください。

- DuckDB 接続を作る（デフォルト path: data/kabusys.duckdb）
  from pathlib import Path
  import duckdb
  conn = duckdb.connect(str(Path("data/kabusys.duckdb")))

- ETL（日次）を実行する
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl
  result = run_daily_etl(conn, target_date=date(2026,3,20))
  print(result.to_dict())

- ニュース NLP スコアを生成する（OpenAI API キーが環境変数にある場合は api_key 引数省略可）
  from datetime import date
  from kabusys.ai.news_nlp import score_news
  n_written = score_news(conn, target_date=date(2026,3,20))
  print("書き込んだ銘柄数:", n_written)

- 市場レジーム判定を実行する
  from kabusys.ai.regime_detector import score_regime
  score_regime(conn, target_date=date(2026,3,20))  # OPENAI_API_KEY を環境変数に設定しておく

- 研究用ファクター計算
  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
  recs = calc_momentum(conn, target_date=date(2026,3,20))
  # z-score 正規化
  from kabusys.data.stats import zscore_normalize
  normed = zscore_normalize(recs, ["mom_1m","mom_3m","mom_6m","ma200_dev"])

- 監査 DB 初期化（監査専用 DB を作る）
  from kabusys.data.audit import init_audit_db
  audit_conn = init_audit_db("data/audit.duckdb")

注意点:
- score_news / score_regime は OpenAI を呼ぶため、API キーとネットワークが必要です。テスト時は内部の _call_openai_api をモックできます。
- run_daily_etl は J-Quants へのリクエストを行うため JQUANTS_REFRESH_TOKEN が必要です。

---

## ディレクトリ構成

主要なファイル／モジュール構成（抜粋）

src/
  kabusys/
    __init__.py
    config.py                    # 環境変数・設定管理
    ai/
      __init__.py
      news_nlp.py                # ニュース NLP スコアリング
      regime_detector.py         # 市場レジーム判定
    data/
      __init__.py
      jquants_client.py          # J-Quants API クライアント + DuckDB 保存
      pipeline.py                # ETL パイプライン
      etl.py                     # ETL の公開型（ETLResult）
      quality.py                 # 品質チェック
      stats.py                   # 統計ユーティリティ
      news_collector.py          # RSS 収集
      calendar_management.py     # マーケットカレンダー管理
      audit.py                   # 監査スキーマ初期化
    research/
      __init__.py
      factor_research.py         # ファクター計算
      feature_exploration.py     # 将来リターン・IC・サマリー等
    research/                    # etc.

このリポジトリはモジュール毎に責務が分割されており、Data / AI / Research / Execution（発注系は別モジュール想定）を分離しています。

---

## 開発／テスト向けメモ

- 環境変数自動読み込み
  - config.py はプロジェクトルート（.git または pyproject.toml があるディレクトリ）を基に .env / .env.local を自動読み込みします。
  - テスト時に自動読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

- OpenAI 呼び出しのモック
  - テストでは kabusys.ai.news_nlp._call_openai_api や kabusys.ai.regime_detector._call_openai_api を unittest.mock.patch で差し替えられます（実装上意図的に別実装にしているためモジュール間の共有はありません）。

- DuckDB の互換性
  - 一部コードは DuckDB の executemany 空リスト問題や DATE/TIMESTAMP の返却型差異に対応する実装になっています。実行する DuckDB バージョンによって挙動差が出る可能性があるため、CI で使用する DuckDB バージョンは固定することを推奨します。

---

以上がこのコードベースの概要と基本的な利用方法です。README に不足している内容や、具体的な利用シナリオ（発注フロー、Slack 通知の例、CI 設定等）が必要であれば追記します。