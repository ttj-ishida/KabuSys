# KabuSys

日本株向けの自動売買 / データ基盤ライブラリ。  
ETL（J-Quants）→ DuckDB によるデータ保存、ニュース収集・NLP（OpenAI）によるセンチメント評価、ファクター計算・リサーチツール、監査ログ（約定トレーサビリティ）などを含むモジュール群を提供します。

主な設計方針:
- ルックアヘッドバイアスに注意した日付処理（内部で datetime.today()/date.today() を不用意に参照しない）
- DuckDB を主要なローカルデータストアとして使用
- 外部 API 呼び出しにはリトライ・レート制御・フェイルセーフを備える
- 冪等性（ON CONFLICT 等）と監査証跡を重視

---

## 機能一覧
- データ取得 / ETL
  - J-Quants からの日足（OHLCV）、財務データ、JPX カレンダー取得（jquants_client）
  - 差分取得・バックフィル・品質チェックを備えた日次 ETL（data.pipeline.run_daily_etl）
- ニュース収集・NLP
  - RSS 収集（news_collector.fetch_rss）と raw_news への保存ロジック
  - OpenAI（gpt-4o-mini）を用いた記事／銘柄単位のセンチメントスコア (ai.news_nlp.score_news)
  - マクロニュース + ETF MA200乖離を合成した市場レジーム判定 (ai.regime_detector.score_regime)
- リサーチ / ファクター
  - モメンタム / ボラティリティ / バリュー等のファクター計算（research.factor_research）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー等（research.feature_exploration）
  - z-score 正規化ユーティリティ（data.stats.zscore_normalize）
- 監査・実行記録
  - シグナル → 発注要求 → 約定 のトレーサビリティを保証する監査スキーマ（data.audit）
  - 監査 DB 初期化ユーティリティ（init_audit_schema / init_audit_db）
- カレンダー管理
  - market_calendar を用いた営業日判定・次営業日/前営業日計算（data.calendar_management）
- データ品質チェック
  - 欠損、スパイク、重複、日付不整合の検出（data.quality）

---

## セットアップ手順（開発環境向け）
推奨: Python 3.10 以上（typing の `X | Y` 構文などを使用）

1. リポジトリをクローン
   - git clone ... && cd <repo>

2. 仮想環境の作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  # Windows: .venv\Scripts\activate

3. インストール
   - プロジェクトルートに pyproject.toml がある想定で編集開発する場合:
     - python -m pip install -e .
   - もしくは必要なパッケージだけ入れる場合:
     - python -m pip install duckdb openai defusedxml

   （プロジェクトの packaging によっては依存項目が pyproject.toml / requirements.txt に記載されています）

4. 環境変数（.env）設定
   - プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動読み込みを無効化可）。
   - 必要な主な環境変数（実行に応じて設定してください）:
     - JQUANTS_REFRESH_TOKEN：J-Quants リフレッシュトークン（必須：ETL 用）
     - OPENAI_API_KEY：OpenAI API キー（必須：ニュース NLP / レジーム判定）
     - KABU_API_PASSWORD：kabuステーション API パスワード（発注連携がある場合）
     - KABU_API_BASE_URL：（オプション）kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID：（任意）通知連携用
     - DUCKDB_PATH：（デフォルト）data/kabusys.duckdb
     - SQLITE_PATH：（監視 DB）data/monitoring.db
     - PID_FILE_PATH / KILL_FLAG_PATH / その他監視用設定
   - 例（.env に記載する最小例）:
     - JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxx
     - OPENAI_API_KEY=sk-xxxxxxxxxxxx
     - DUCKDB_PATH=data/kabusys.duckdb

5. データディレクトリ作成
   - デフォルトでは `data/` 以下を使用します。必要に応じて作成:
     - mkdir -p data

---

## 基本的な使い方（コード例）
ライブラリはプログラムから直接呼び出して利用します。以下は代表的な例です。

- 設定読み取り
  - from kabusys.config import settings
  - settings.duckdb_path などでパスやフラグを取得可能  
  - 自動で .env がプロジェクトルートから読み込まれます（不要なら KABUSYS_DISABLE_AUTO_ENV_LOAD=1）

- DuckDB 接続の作成
  - import duckdb
  - conn = duckdb.connect(str(settings.duckdb_path))

- 日次 ETL 実行
  - from kabusys.data.pipeline import run_daily_etl
  - result = run_daily_etl(conn, target_date=some_date)  # some_date を指定しない場合は今日

- ニュース NLP スコア生成（単体）
  - from kabusys.ai.news_nlp import score_news
  - from datetime import date
  - n = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")  # api_key を渡すか OPENAI_API_KEY を設定

- 市場レジーム判定
  - from kabusys.ai.regime_detector import score_regime
  - score_regime(conn, target_date=date(2026,3,20), api_key="sk-...")

- 監査 DB 初期化
  - from kabusys.data.audit import init_audit_db
  - audit_conn = init_audit_db("data/audit.duckdb")  # ":memory:" も可

- RSS 取得（ニュース収集の一部）
  - from kabusys.data.news_collector import fetch_rss
  - articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")

注意点:
- OpenAI 呼び出しは API レートやリトライを伴います。APIキーがない場合、score_news / score_regime は ValueError を投げます（あるいは api_key 引数を使って注入してください）。
- J-Quants の認証は JQUANTS_REFRESH_TOKEN を settings 経由で取得するか、jquants_client.get_id_token に直接渡します。

---

## 環境変数一覧（主なもの）
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- OPENAI_API_KEY: OpenAI API キー（ニュース NLP / レジーム判定で必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（発注連携が必要な場合）
- KABU_API_BASE_URL: kabu API ベース URL（デフォルト http://localhost:18080/kabusapi）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: LINE 通知用（任意）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: SQLite（監視用）パス（デフォルト data/monitoring.db）
- KABUSYS_ENV: 環境 ("development" | "paper_trading" | "live")（デフォルト development）
- LOG_LEVEL: ログレベル ("DEBUG","INFO",...)（デフォルト INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1: .env 自動ロードを無効化する（テストなどで使用）

設定は .env / .env.local / OS 環境変数から読み込まれます。優先順位は OS 環境 > .env.local > .env です。

---

## ディレクトリ構成（重要ファイルの概要）
（src 配下、パッケージ名は kabusys）

- src/kabusys/
  - __init__.py : パッケージ初期化、バージョン等
  - config.py : 環境変数・設定管理（settings オブジェクト）
  - ai/
    - __init__.py
    - news_nlp.py : ニュース記事→銘柄別センチメント（score_news）
    - regime_detector.py : ETF MA + マクロニュースで市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py : J-Quants API クライアント（取得 + DuckDB 保存関数）
    - pipeline.py : ETL パイプライン（run_daily_etl など）
    - etl.py : ETL 用の公開インターフェース（ETLResult）
    - news_collector.py : RSS 収集・下処理・保存ロジック
    - calendar_management.py : 市場カレンダー管理／営業日ロジック
    - stats.py : z-score 正規化ユーティリティ
    - quality.py : データ品質チェック
    - audit.py : 監査（signal/order/executions）スキーマ & 初期化ユーティリティ
  - research/
    - __init__.py
    - factor_research.py : Momentum / Volatility / Value ファクター計算
    - feature_exploration.py : 将来リターン計算、IC、統計サマリー、rank
  - monitoring/, execution/, strategy/, 等（パッケージ全体では __all__ に宣言）

（実際のリポジトリではさらに補助モジュールや CLI / worker 実装等が存在する可能性があります）

---

## 運用上の注意
- OpenAI / J-Quants の API 利用にはそれぞれの利用制限・料金があるため、鍵の管理・使用量に注意してください。
- ETL・API 呼び出しはネットワークの影響を受けるためログとリトライの挙動を理解した上で運用してください。
- 監査テーブルは削除前提ではないため、ディスク管理（バックアップ・アーカイブ等）を検討してください。
- 本リポジトリのコードは「ETL / リサーチ / スコアリング」用途に重点を置いており、実際の自動発注（本番運転）を行う場合はリスク管理・資金管理および発注ロジックの十分なレビュー・テストが必要です。

---

## 開発／テストのヒント
- .env の自動読み込みはプロジェクトルートの検出に .git または pyproject.toml を使用します。テスト時に自動読み込みを無効にしたい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI の呼び出しなど外部 API はモック可能なように内部呼び出し関数（例: _call_openai_api）が分離されています。ユニットテストはこれらを patch して実行してください。
- DuckDB を使うため、ローカルでの高速テストが容易です。テスト用に ":memory:" を使ったり、一時ファイルを利用してください。

---

必要に応じて README を拡張して、セットアップのための正確な依存関係（requirements.txt / pyproject.toml）や運用手順（systemd / supervisor 用のユニットファイル例）、サンプル .env.example を追加できます。どの情報を追記したいか教えてください。