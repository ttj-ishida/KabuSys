# KabuSys

日本株向け自動売買 / データプラットフォームのライブラリです。  
ETL（J-Quants からのデータ取得）・ニュース収集・AI によるニューススコアリング・市場レジーム判定・リサーチ用ファクター計算・監査ログ（オーダートレーサビリティ）などを含みます。

---

## プロジェクト概要

KabuSys は日本株の自動売買システムに必要なデータ基盤・リサーチ・AI評価・監査機構をモジュール化して提供する Python パッケージです。主に以下の領域をカバーします。

- J-Quants API を用いた株価・財務・マーケットカレンダー等の ETL
- RSS ベースのニュース収集と前処理（SSRF 対策・サイズ制限）
- OpenAI（gpt-4o-mini）を利用したニュースセンチメント分析（銘柄別）およびマクロセンチメントによる市場レジーム判定
- DuckDB を利用した分析・保存処理
- ファクター計算（モメンタム、バリュー、ボラティリティ等）と特徴量探索ユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（signal → order_request → execution のトレーサビリティ）用スキーマ作成ユーティリティ

---

## 主な機能一覧

- data/
  - ETL パイプライン（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - J-Quants クライアント（認証・リトライ・ページネーション・DuckDB への冪等保存）
  - カレンダー管理（営業日判定・next/prev_trading_day 等）
  - ニュース収集（RSS パース、URL 正規化、SSRF 防止、raw_news への保存補助）
  - 品質チェック（欠損、スパイク、重複、日付不整合）
  - 監査ログ初期化（init_audit_schema / init_audit_db）
  - 統計ユーティリティ（zscore_normalize）
- ai/
  - news_nlp.score_news: 銘柄別ニュースセンチメントを取得して ai_scores テーブルへ保存
  - regime_detector.score_regime: ETF(1321) の MA とマクロニュースの LLM スコアを合成して market_regime に保存
- research/
  - calc_momentum, calc_value, calc_volatility（ファクター計算）
  - calc_forward_returns, calc_ic, factor_summary, rank（特徴量評価・IC 等）
- config.py
  - .env 自動読み込み（.env / .env.local、CWD に依存しないプロジェクトルート探索）
  - 環境変数ラッパ（必須チェック・型変換・env / log level 判定）

---

## セットアップ手順

前提
- Python 3.10 以上（型注釈に `X | None` などを使用しているため）
- DuckDB を利用（ローカル DB ファイルに永続化）
- OpenAI API（ニュース分析 / レジーム判定に必要）
- J-Quants リフレッシュトークン（データ ETL に必要）

1. リポジトリをクローン / ダウンロード
   - 例: git clone <repository-url>

2. 仮想環境作成（任意だが推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージのインストール
   - pip install -U pip
   - 必要な主なパッケージ（例）:
     - duckdb
     - openai
     - defusedxml
   - 例:
     - pip install duckdb openai defusedxml

   （プロジェクトに requirements.txt / pyproject.toml があればそれを利用してください）
   - pip install -e .

4. 環境変数設定
   - プロジェクトルート（.git または pyproject.toml が存在するディレクトリ）に `.env` を置くと自動的に読み込まれます。
   - 自動読み込みを無効化する場合:
     - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定
   - 必須の環境変数（コード上で必須チェックされるもの）
     - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD — kabuステーション API のパスワード（発注関連）
     - SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
     - SLACK_CHANNEL_ID — Slack 通知先チャンネル ID
   - 任意 / デフォルトあり:
     - KABUSYS_ENV (development | paper_trading | live) 既定: development
     - LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL) 既定: INFO
     - KABUS_API_BASE_URL 既定: http://localhost:18080/kabusapi
     - DUCKDB_PATH 既定: data/kabusys.duckdb
     - SQLITE_PATH 既定: data/monitoring.db
     - OPENAI_API_KEY — OpenAI 呼び出しに使用（AI モジュールで使う。関数引数でも渡せます）

   - .env の例（.env.example を用意している想定）:
     - JQUANTS_REFRESH_TOKEN=...
     - OPENAI_API_KEY=...
     - KABU_API_PASSWORD=...
     - SLACK_BOT_TOKEN=...
     - SLACK_CHANNEL_ID=...
     - KABUSYS_ENV=development

---

## 使い方（簡単な例）

以下は Python スクリプト / REPL から呼び出す例です。実行前に環境変数を設定し、DuckDB のファイルパスが書き込み可能であることを確認してください。

- DuckDB 接続の作成
  - import duckdb
  - from kabusys.config import settings
  - conn = duckdb.connect(str(settings.duckdb_path))

- ETL（日次パイプライン実行）
  - from datetime import date
  - from kabusys.data.pipeline import run_daily_etl
  - result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  - print(result.to_dict())

- ニューススコアリング（AI による銘柄別センチメント）
  - from datetime import date
  - from kabusys.ai.news_nlp import score_news
  - n = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
  - print(f"written codes: {n}")

  - api_key を省略すると環境変数 OPENAI_API_KEY が使われます。

- 市場レジーム判定（ETF 1321 の MA とマクロ LLM を合成）
  - from kabusys.ai.regime_detector import score_regime
  - score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")

- 監査ログ DB 初期化（監査専用 DB を新規作成）
  - from kabusys.data.audit import init_audit_db
  - audit_conn = init_audit_db("data/audit.duckdb")

- 研究用ファクター計算例
  - from kabusys.research.factor_research import calc_momentum
  - records = calc_momentum(conn, target_date=date(2026,3,20))

- カレンダー関連ユーティリティ
  - from kabusys.data.calendar_management import is_trading_day, next_trading_day
  - is_trade = is_trading_day(conn, date(2026,3,20))
  - nxt = next_trading_day(conn, date(2026,3,20))

注意点:
- AI 呼び出しは外部 API（OpenAI）に依存します。API キーの設定・課金に注意してください。
- ETL / API 呼び出しはネットワークや外部サービスの状態に依存するため、例外処理やログ監視を行ってください。
- news_nlp / regime_detector はルックアヘッドバイアスを避ける設計になっています（target_date 未満のデータのみ参照）。

---

## 主要ファイル・ディレクトリ構成

（src/kabusys 配下を抜粋）

- src/kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py            — ニュースセンチメント（銘柄別）を取得し ai_scores テーブルへ書き込む
    - regime_detector.py     — マクロセンチメント + ETF MA を合成して market_regime に書き込み
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント（取得・保存・認証・リトライ）
    - pipeline.py            — ETL パイプライン（run_daily_etl 等）
    - etl.py                 — ETL の公開インターフェース（ETLResult 再エクスポート）
    - calendar_management.py — マーケットカレンダー管理（営業日判定 等）
    - news_collector.py      — RSS 収集・前処理・SSRF 対策
    - quality.py             — データ品質チェック
    - stats.py               — zscore_normalize 等の統計ユーティリティ
    - audit.py               — 監査ログ（テーブル定義・初期化）
  - research/
    - __init__.py
    - factor_research.py     — モメンタム/ボラティリティ/バリュー等の計算
    - feature_exploration.py — 将来リターン計算、IC、統計サマリー、rank
  - monitoring/ (存在宣言のみ: モニタリング関連モジュールを想定)
  - strategy/ (戦略実装用プレースホルダ)
  - execution/ (発注・ブローカー接続の抽象化プレースホルダ)

---

## 環境変数の自動読み込みについて

- config.py はプロジェクトルート（.git または pyproject.toml があるディレクトリ）を探索し、`.env` と `.env.local` を自動的に読み込みます。
  - 読み込み優先度: OS 環境変数 > .env.local > .env
  - テストなどで自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- 必須変数が未設定の場合、settings プロパティ（例: settings.jquants_refresh_token）を参照すると ValueError が発生します。

---

## 開発・テスト時のヒント

- OpenAI 呼び出しや外部 HTTP 呼び出し箇所はテスト用に差し替え（patch / mock 可能）な設計になっています（内部の _call_openai_api、_urlopen など）。
- DuckDB はインメモリ（":memory:"）でのテスト接続が可能です。audit.init_audit_db(":memory:") などを利用すると便利です。
- ETL の各ステップは独立してエラーハンドリングされるため、部分的な障害でも他処理は継続する設計です。ログを参照して集約的に監視してください。

---

## 最後に

この README はコードベースの主要な利用方法と設計方針を簡潔にまとめたものです。内部ロジック（例: LLM のプロンプト設計、ETL の差分ロジック、DuckDB への冪等保存等）はソースのドキュメンテーション文字列（docstring）に詳細が書かれているため、実装を変更する際は該当モジュールの docstring を参照してください。質問や追加で README に含めたい情報があれば教えてください。