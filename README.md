# KabuSys

日本株向けの自動売買・データプラットフォーム用ライブラリ（部分実装）。  
本リポジトリはデータETL、ニュースNLP、マーケットレジーム判定、研究用ファクター計算、監査ログ初期化などの機能を提供します。

主な目的は「データ取得 → 品質チェック → AIによるニュース評価 → ファクター計算 → 戦略/発注へつなぐ」一連の基盤を提供することです。

---

目次
- プロジェクト概要
- 機能一覧
- 必要条件
- セットアップ手順
- 環境変数 (.env) 例
- 使い方（主要な利用例）
- ディレクトリ構成
- 補足（注意点）

---

## プロジェクト概要

KabuSys は日本株向けのデータ基盤と研究・自動売買補助のためのライブラリ群です。  
主に以下の領域をカバーします：

- J-Quants API を用いた株価/財務/カレンダーの差分ETL（jquants_client, pipeline）
- DuckDB をデータレイクとして用いる各種保存・初期化ユーティリティ（data.audit 等）
- RSS からのニュース収集と前処理（news_collector）
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント評価（ai.news_nlp）
- ETFとニュースを組み合わせた市場レジーム判定（ai.regime_detector）
- 研究用ファクター計算・特徴量解析（research.*）
- データ品質チェック（data.quality）

設計上の特徴：
- ルックアヘッドバイアス対策（target_date を明示し datetime.today() を直接参照しない等）
- DuckDB を中心とした高速なローカル分析
- 冪等性（DB書き込みは ON CONFLICT / DELETE→INSERT を利用）
- API 呼び出しに対する堅牢なリトライ/バックオフ/レート制御

---

## 機能一覧（抜粋）

- データ取得・保存
  - J-Quants から daily_quotes、financial_statements、trading_calendar を取得・保存
  - save_* 系は冪等（ON CONFLICT DO UPDATE）

- ETLパイプライン
  - run_daily_etl: カレンダー→株価→財務→品質チェックをまとめて実行

- データ品質チェック
  - 欠損（OHLC）、重複、スパイク（前日比閾値）、日付整合性チェック

- ニュース収集 & 前処理
  - RSS を取得、URL正規化、記事ID生成、テキスト正規化
  - SSRF 対策、gzip/サイズチェック、XML脆弱性対策

- AI（OpenAI）連携
  - ニュースを銘柄単位に集約し LLM に投げてセンチメントを取得（score_news）
  - マクロ記事 + ETF MA200乖離で市場レジーム判定（score_regime）
  - API 呼び出しは JSON mode / レート/リトライ考慮

- 研究用ユーティリティ
  - ファクター計算（momentum、value、volatility）
  - 将来リターン計算、IC（Spearman）計算、Zスコア正規化等

- 監査ログ（Audit）
  - signal_events / order_requests / executions テーブルのDDL定義と初期化（init_audit_schema / init_audit_db）

---

## 必要条件

- Python 3.10 以上（typing の | などを使用）
- 主な依存ライブラリ（例）
  - duckdb
  - openai
  - defusedxml
  - （標準ライブラリ以外の HTTP ライブラリは不要。必要に応じて Slack SDK 等を追加）

注意: requirements.txt は本コード例には同梱されていません。実行前に上記パッケージをインストールしてください。

---

## セットアップ手順（例）

1. Python 仮想環境を作成・有効化
   - Linux / macOS:
     - python -m venv .venv
     - source .venv/bin/activate
   - Windows:
     - python -m venv .venv
     - .venv\Scripts\activate

2. 依存パッケージをインストール
   - 最低限:
     - pip install duckdb openai defusedxml
   - もしプロジェクトを editable インストールできる場合:
     - pip install -e .

3. 環境変数の準備
   - プロジェクトルートに `.env` を作成する（下記サンプル参照）
   - 自動で .env を読み込む動作はデフォルトで有効（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）

4. DuckDB データベース用ディレクトリ作成（必要に応じて）
   - mkdir -p data

---

## 環境変数（.env）例

以下は最低限の例（実運用では実値で埋めてください）:

JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_api_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C12345678
OPENAI_API_KEY=sk-...
# オプション
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
KABUSYS_ENV=development
LOG_LEVEL=INFO

注意:
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定するとパッケージインポート時の .env 自動読み込みを無効化できます（テスト時に便利）。
- settings（kabusys.config.settings）からこれらの値を取得します。必須が未設定だと ValueError が発生します。

---

## 使い方（主要なサンプル）

以下は主要な API の簡単な利用例です（Python REPL やスクリプトで実行）。

- DuckDB 接続を作成する
  - import duckdb
  - conn = duckdb.connect("data/kabusys.duckdb")

- 日次 ETL を実行する
  - from datetime import date
    from kabusys.data.pipeline import run_daily_etl
    conn = duckdb.connect("data/kabusys.duckdb")
    result = run_daily_etl(conn, target_date=date(2026, 3, 20))
    print(result.to_dict())

- ニューススコアを計算して ai_scores に書き込む
  - from datetime import date
    import duckdb
    from kabusys.ai.news_nlp import score_news
    conn = duckdb.connect("data/kabusys.duckdb")
    n_written = score_news(conn, target_date=date(2026, 3, 20))
    print("scored:", n_written)

  - 注意: OPENAI_API_KEY が必要です（関数引数 api_key でも渡せます）。

- 市場レジーム判定を行う
  - from datetime import date
    import duckdb
    from kabusys.ai.regime_detector import score_regime
    conn = duckdb.connect("data/kabusys.duckdb")
    score_regime(conn, target_date=date(2026, 3, 20))

- 監査DBの初期化（監査専用 DB を作る場合）
  - from kabusys.data.audit import init_audit_db
    conn = init_audit_db("data/audit.duckdb")
    # これで signal_events / order_requests / executions 等が作成されます

- 研究用途のファクター計算
  - from datetime import date
    import duckdb
    from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
    conn = duckdb.connect("data/kabusys.duckdb")
    mom = calc_momentum(conn, date(2026, 3, 20))
    val = calc_value(conn, date(2026, 3, 20))

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 配下の主なファイルとモジュール（抜粋）です。

- src/
  - kabusys/
    - __init__.py
    - config.py                      # 環境変数・設定管理（.env 自動ロード）
    - ai/
      - __init__.py
      - news_nlp.py                  # ニュースNLP（score_news）
      - regime_detector.py           # 市場レジーム判定（score_regime）
    - data/
      - __init__.py
      - pipeline.py                  # ETL パイプライン（run_daily_etl 等）
      - jquants_client.py            # J-Quants API クライアント（fetch/save）
      - news_collector.py            # RSS ニュース収集
      - calendar_management.py       # 市場カレンダー管理
      - quality.py                   # データ品質チェック
      - stats.py                     # 統計ユーティリティ（zscore_normalize）
      - audit.py                     # 監査ログテーブル定義／初期化
      - etl.py                       # ETLResult 再エクスポート
    - research/
      - __init__.py
      - factor_research.py           # モメンタム/ボラティリティ/バリュー計算
      - feature_exploration.py       # 将来リターン/IC/統計サマリー 等
    - research/* (その他)
    - (strategy/, execution/, monitoring/ を __all__ に含むが実装は限定的)

---

## 補足・注意点

- APIキー・トークン
  - OpenAI（OPENAI_API_KEY）、J-Quants（JQUANTS_REFRESH_TOKEN）等の秘密情報は `.env` または環境変数で管理してください。
  - config.Settings は未設定の必須値に対して ValueError を投げます。

- ルックアヘッドバイアス対策
  - ほとんどの関数は target_date を明示して使用する設計です。datetime.today()/date.today() を直接参照する箇所を避けています（ETL のデフォルトは date.today を使用しますが分析関数は明示的な日付受け取り）。

- OpenAI 呼び出し
  - news_nlp / regime_detector は OpenAI の JSON mode を利用しています。API エラー時はフォールバックでスコア 0.0 を返す等の堅牢性機構を備えていますが、API 使用料やレートには注意してください。

- セキュリティ
  - news_collector は SSRF 対策、XML パースの防御（defusedxml）、レスポンスサイズ制限などを実装しています。

- DB 書き込み
  - DuckDB のバージョンや executemany の挙動に依存する処理があるため（コード中に注意書きあり）、実行環境の DuckDB バージョンが古すぎないか確認してください。

---

もし README の補足（例：CIの流れ、より詳しい環境構築手順、CLI コマンドの用意）や、特定モジュールの API ドキュメント（関数別の詳細な使い方）を追加希望でしたらお知らせください。