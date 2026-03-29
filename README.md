# KabuSys

KabuSys は日本株向けの自動売買・データ基盤ライブラリです。J-Quants や RSS、OpenAI（LLM）を組み合わせてデータ収集（ETL）・品質チェック・ニュース NLP（センチメント）・市場レジーム判定・ファクター計算・監査ログ管理などを行うためのモジュール群を提供します。

主な設計方針：
- ルックアヘッドバイアスを防ぐ（date 引数ベースでの処理、datetime.today() の直接参照禁止）
- DuckDB を中心としたローカル DB / ETL パイプライン
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント評価（JSON Mode）
- J-Quants からのデータ取得はレート制御・リトライ・トークン自動リフレッシュを実装
- 冪等性（ON CONFLICT DO UPDATE / INSERT ... DO NOTHING）を重視

---

## 機能一覧

- 環境変数 / 設定管理
  - .env/.env.local の自動読み込み（プロジェクトルート検出）
  - 必須パラメータの取得ユーティリティ

- データ取得・ETL（kabusys.data）
  - J-Quants クライアント（株価日足、財務、上場情報、マーケットカレンダー）
  - ETL パイプライン（差分取得・保存・品質チェック）
  - 市場カレンダー管理（営業日判定、next/prev/get_trading_days）
  - ニュース収集（RSS → raw_news、SSRF 対策、正規化）
  - データ品質チェック（欠損、スパイク、重複、日付不整合）
  - 監査ログ初期化 / 監査 DB（signal / order_request / execution）

- 研究・ファクター（kabusys.research）
  - Momentum / Volatility / Value 等のファクター計算
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー
  - z-score 正規化ユーティリティ

- AI（kabusys.ai）
  - ニュースの NLP スコアリング（score_news）
  - 市場レジーム判定（score_regime） — ETF 1321 の MA200 乖離とマクロニュースを組合せ

- その他ユーティリティ
  - 統計ユーティリティ（zscore_normalize）
  - DuckDB / SQLite パス設定、ログレベル・環境モード管理

---

## 必要条件

- Python 3.10 以上（typing の | 演算子を使用）
- 主要依存パッケージ（例）
  - duckdb
  - openai
  - defusedxml
  - その他標準ライブラリ

（実際のプロジェクトでは pyproject.toml / requirements.txt に依存関係を記載してください）

---

## セットアップ手順

1. リポジトリをクローン／取得する（既に src/ 配下にコードがある想定）。

2. 仮想環境を作成して有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - pip install duckdb openai defusedxml

   （プロジェクトに requirements があればそれを使用してください）

4. 開発インストール（パッケージとして利用する場合）
   - pip install -e .

5. 環境変数を設定する
   - プロジェクトルートに `.env` または `.env.local` を置くと、自動的に読み込まれます（自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定）。
   - 主要な環境変数（例）:
     - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
     - KABU_API_PASSWORD: kabuステーション API パスワード（必須）
     - KABU_API_BASE_URL: kabu API ベース URL（省略時ローカルデフォルト）
     - OPENAI_API_KEY: OpenAI API キー（score_news / regime で使用）
     - SLACK_BOT_TOKEN: Slack Bot トークン（通知等）
     - SLACK_CHANNEL_ID: Slack チャンネル ID
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH: SQLite（監視用）ファイルパス（デフォルト data/monitoring.db）
     - KABUSYS_ENV: 環境 ("development" | "paper_trading" | "live")
     - LOG_LEVEL: ログレベル ("DEBUG" | "INFO" | ...)

6. データベースの初期化（監査ログ用など）
   - 監査 DB を初期化する例:
     - from kabusys.data.audit import init_audit_db
       conn = init_audit_db("data/audit.duckdb")

---

## 使い方（基本例）

以下はライブラリの主な使い方のサンプルです。実行はアプリケーションの要件に合わせて調整してください。

- DuckDB 接続の作成（ETL / AI 関数は DuckDB 接続を受け取ります）
  - import duckdb
  - from kabusys.config import settings
  - conn = duckdb.connect(str(settings.duckdb_path))

- 日次 ETL 実行
  - from kabusys.data.pipeline import run_daily_etl
  - from datetime import date
  - result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  - print(result.to_dict())

  run_daily_etl は市場カレンダー→株価→財務データ→品質チェックの順で差分取得し、ETLResult を返します。

- ニュース NLP（score_news）
  - from kabusys.ai.news_nlp import score_news
  - from datetime import date
  - n = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")  # api_key を省略すると環境変数 OPENAI_API_KEY を参照
  - print(f"scored {n} securities")

  注意: score_news は target_date の前日 15:00 JST ～ 当日 08:30 JST の記事を対象にする時間ウィンドウ計算を行います（ルックアヘッド回避）。

- 市場レジーム判定（score_regime）
  - from kabusys.ai.regime_detector import score_regime
  - from datetime import date
  - score_regime(conn, target_date=date(2026, 3, 20), api_key=None)  # OPENAI_API_KEY を参照

  内部では ETF 1321 の MA200 乖離とマクロニュースの LLM スコアを組合せ、market_regime テーブルへ冪等書き込みします。

- 監査スキーマ初期化（監査ログを使用する場合）
  - from kabusys.data.audit import init_audit_schema
  - init_audit_schema(conn, transactional=True)

---

## 注意事項 / 実装上のポイント

- 全体的に「ルックアヘッドバイアス防止」が意識されており、関数は target_date を受け取り、内部で現在時刻を参照しないように実装されています。バックテストやオフライン解析時に重要です。

- .env のパース実装はクォート・エスケープ・コメントに対応しています。自動読み込みはパッケージ読み込み時に実行されますが、テスト時等は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で抑止できます。

- J-Quants クライアントはレート制御（120 req/min）を実装しており、リトライ（408/429/5xx）や 401 時のトークン自動リフレッシュに対応しています。

- ニュース収集は SSRF 対策（リダイレクト時のホストチェック、プライベート IP 拒否）、受信サイズ上限、defusedxml による XML 安全パースを行っています。

- OpenAI 呼び出し時は JSON Mode（response_format={"type": "json_object"}）を利用する設計で、レスポンスのバリデーション・リトライ制御が組み込まれています。API エラー時はフェイルセーフとして 0.0 を返すなどの保護があるため、システム全体の継続性が確保されています。

---

## ディレクトリ構成

概要（主要ファイル）:

- src/kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py          — ニュースセンチメントスコアリング（score_news）
    - regime_detector.py   — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py    — J-Quants API クライアント（fetch / save）
    - pipeline.py          — ETL パイプライン（run_daily_etl 等）
    - etl.py               — ETLResult の再エクスポート
    - news_collector.py    — RSS 収集・前処理・保存
    - calendar_management.py — マーケットカレンダー管理（is_trading_day 等）
    - quality.py           — データ品質チェック
    - stats.py             — 統計ユーティリティ（zscore_normalize）
    - audit.py             — 監査ログスキーマ初期化・監査 DB ヘルパ
  - research/
    - __init__.py
    - factor_research.py   — Momentum / Volatility / Value 等
    - feature_exploration.py — 将来リターン計算・IC・統計サマリー
  - ai/ (上記)
  - research/ (上記)

（実際のプロジェクトでは tests/、examples/、pyproject.toml、LICENSE などが存在することが想定されます）

---

## よくある質問

- Q: OpenAI のキーはどの環境変数を使いますか？
  - A: OPENAI_API_KEY を参照します。score_news / score_regime 呼び出し時に api_key 引数で上書き可能です。

- Q: .env は自動で読み込まれますか？
  - A: はい。プロジェクトルート（.git または pyproject.toml があるディレクトリ）を起点に `.env` と `.env.local` を読み込みます。自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセットしてください。

- Q: ETL の差分取得の基準日は？
  - A: run_daily_etl の target_date（省略時は today）が基準です。market_calendar を先に取得・反映してから prices/financials を差分取得します。

---

## 貢献 / 拡張

- 新しいニュースソースを追加する場合は data/news_collector.py の DEFAULT_RSS_SOURCES を拡張し、適宜前処理を追加してください。
- OpenAI モデルやプロンプトは ai/news_nlp.py / ai/regime_detector.py に記載されています。モデル変更やプロンプト調整で挙動が変わりますのでテストを行ってください。
- ETL や品質チェックに新ルールを追加する場合は data/pipeline.py / data/quality.py を拡張してください。

---

README の内容はコードベースの現状（src 以下の実装）に基づいて作成しました。追加で「サンプル .env テンプレート」「実行スクリプト例」「CI / テスト手順」などを含めたい場合はその旨を教えてください。