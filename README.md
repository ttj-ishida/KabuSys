# KabuSys

日本株向け自動売買 / データプラットフォーム用ライブラリ KabuSys

- バージョン: 0.1.0
- 概要: DuckDB をデータストアに、J-Quants や RSS、OpenAI（LLM）等を組み合わせて日本株のデータ収集（ETL）、ニュースNLP によるセンチメント評価、マーケットレジーム判定、ファクター計算、監査ログ管理などの基盤機能を提供する内部ライブラリです。実取引（kabuステーション）との接続や Slack 通知等も設定に応じて組み込み可能な設計です。

---

## 主要機能一覧

- 環境変数 / 設定管理
  - .env / .env.local をプロジェクトルート（.git または pyproject.toml を基準）から自動読込（無効化フラグあり）
  - 必須環境変数の検査や環境に応じたモード判定（development / paper_trading / live）

- データ取得 / ETL（J-Quants）
  - 株価日足（OHLCV）、財務データ、JPX カレンダー等を差分取得して DuckDB に冪等保存
  - ページネーション対応、レート制御、リトライ・トークン自動リフレッシュ

- ニュース収集・前処理
  - RSS からのニュース取得（SSRF/圧縮/サイズ上限/トラッキングパラメータ除去等、安全性重視）
  - raw_news テーブルへの冪等保存および銘柄紐付け

- ニュースNLP（OpenAI）
  - 銘柄ごとに記事を集約して LLM に投げ、センチメント（ai_score）を ai_scores テーブルへ保存
  - バッチ/チャンク処理、JSON Mode 利用、堅牢なバリデーションとリトライ

- 市場レジーム判定
  - ETF (1321) の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成し
    'bull' / 'neutral' / 'bear' を daily 単位で判定して market_regime に書き込む

- リサーチ用ファクター計算
  - Momentum / Value / Volatility / Liquidity 等のファクターを DuckDB 内のデータから計算
  - 将来リターン計算、IC（Spearman）や統計サマリー、Z スコア正規化ユーティリティ等

- データ品質チェック
  - 欠損、重複、スパイク、日付不整合（未来日付や非営業日のデータ）検出
  - QualityIssue オブジェクトによる結果集約

- 監査ログ（トレーサビリティ）
  - signal_events / order_requests / executions などの監査テーブルを DuckDB に冪等で作成
  - UUID ベースの階層的トレーサビリティ、UTC タイムスタンプ

---

## セットアップ手順

前提:
- Python 3.9+（コードは型アノテーションに union 節などを使っています。適宜 pyproject の指定に合わせてください）
- system のネットワークから J-Quants API と OpenAI API にアクセス可能であること

1. リポジトリをクローン / 取得

2. 仮想環境を作成して有効化（推奨）
   - macOS/Linux:
     - python -m venv .venv
     - source .venv/bin/activate
   - Windows (PowerShell):
     - python -m venv .venv
     - .\.venv\Scripts\Activate.ps1

3. 依存パッケージをインストール
   - 最低限必要な外部パッケージの例:
     - duckdb
     - openai
     - defusedxml
   - インストール例:
     - pip install duckdb openai defusedxml
   - （開発用に package 配布がある場合はプロジェクトルートで `pip install -e .` を使っても良い）

4. 環境変数の設定
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env`（および必要なら `.env.local`）を置くと自動読込されます。
   - 自動読み込みを無効化する場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
   - 必須の環境変数（config.Settings 参照）:
     - JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン（必須）
     - KABU_API_PASSWORD — kabu API パスワード（必須）
     - SLACK_BOT_TOKEN — Slack bot token（必須）
     - SLACK_CHANNEL_ID — Slack チャネル ID（必須）
   - その他任意/デフォルト値:
     - KABUSYS_ENV — "development" | "paper_trading" | "live"（デフォルト: development）
     - LOG_LEVEL — "DEBUG"/"INFO"/...（デフォルト: INFO）
     - KABU_API_BASE_URL — kabu API base（デフォルト: http://localhost:18080/kabusapi）
     - DUCKDB_PATH — DuckDB DB パス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH — SQLite（監視用）パス（デフォルト: data/monitoring.db）
     - OPENAI_API_KEY — OpenAI API キー（score_news / score_regime に使う。関数呼び出し時に api_key 引数で上書き可能）
   - サンプル .env（最低限の例）:
     - JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     - KABU_API_PASSWORD=your_kabu_password
     - SLACK_BOT_TOKEN=xoxb-...
     - SLACK_CHANNEL_ID=C01234567
     - OPENAI_API_KEY=sk-...

5. データベース初期化（監査DBなど）
   - 監査テーブルを作成するには次のようにします（例: Python REPL やスクリプト内で）:
     - from kabusys.data.audit import init_audit_db
     - conn = init_audit_db("data/audit.duckdb")
   - 既存の DuckDB 接続にテーブルを追加したい場合は `init_audit_schema(conn)` を呼ぶことも可能。

---

## 使い方（主要 API の例）

以下はライブラリの主要な使い方スニペット例です。実際は適切なエラーハンドリングやロギングを追加してください。

- DuckDB 接続の作成（既定 path を settings から取得）
  - from kabusys.config import settings
    import duckdb
    conn = duckdb.connect(str(settings.duckdb_path))

- 日次 ETL の実行
  - from datetime import date
    from kabusys.data.pipeline import run_daily_etl
    result = run_daily_etl(conn, target_date=date(2026, 3, 20))
    print(result.to_dict())

- ニュースの NLP スコアリング（指定日分）
  - from datetime import date
    from kabusys.ai.news_nlp import score_news
    n = score_news(conn, target_date=date(2026, 3, 20))
    print(f"scored {n} codes")

  - 注意: OPENAI_API_KEY を環境変数に入れるか、api_key 引数で渡してください。
  - テスト時は内部の _call_openai_api を unittest.mock.patch で差し替えられます。

- 市場レジーム判定
  - from datetime import date
    from kabusys.ai.regime_detector import score_regime
    score_regime(conn, target_date=date(2026, 3, 20))

- ファクター計算 / リサーチ
  - from datetime import date
    from kabusys.research import calc_momentum, calc_value, calc_volatility, zscore_normalize
    mom = calc_momentum(conn, target_date=date(2026,3,20))
    vol = calc_volatility(conn, target_date=date(2026,3,20))
    val = calc_value(conn, target_date=date(2026,3,20))
    mom_z = zscore_normalize(mom, ["mom_1m", "mom_3m", "mom_6m"])

- 品質チェック実行
  - from kabusys.data.quality import run_all_checks
    issues = run_all_checks(conn, target_date=date(2026,3,20))
    for i in issues:
        print(i)

- 監査スキーマの初期化（既存接続への適用）
  - from kabusys.data.audit import init_audit_schema
    init_audit_schema(conn, transactional=True)

---

## 注意点 / 設計上の考慮

- Look-ahead bias 回避:
  - 多くのモジュール（news_nlp, regime_detector, ETL など）は内部で datetime.today() を参照せず、呼び出し側から target_date を受け取り、その日以前のデータのみを参照する設計です。バックテストや再現性のため、この呼び出し方を守ってください。

- 冪等性:
  - J-Quants からの取得→DuckDB への保存処理は冪等（ON CONFLICT / DO UPDATE 等）で設計されています。

- 外部 API のリトライ/フェイルセーフ:
  - OpenAI 呼び出しや J-Quants 呼び出しにはリトライ・バックオフ・フェイルセーフロジックが組み込まれており、API エラー時はゼロ埋めやスキップで処理を続行する箇所があります（ログ出力はされます）。

- セキュリティ:
  - RSS の取得処理には SSRF ブロックや最大受信サイズ・defusedxml を使った XML パースなど安全性対策が実装されています。

---

## ディレクトリ構成（抜粋）

プロジェクトの主要モジュール構成は以下の通りです（src/kabusys 配下）:

- kabusys/
  - __init__.py
  - config.py                   — 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py               — ニュースセンチメント（LLM）
    - regime_detector.py        — 市場レジーム判定
  - data/
    - __init__.py
    - calendar_management.py    — 市場カレンダー管理
    - etl.py                    — ETL インターフェース
    - pipeline.py               — ETL パイプライン実装
    - stats.py                  — 汎用統計ユーティリティ
    - quality.py                — 品質チェック
    - audit.py                  — 監査ログスキーマ & 初期化
    - jquants_client.py         — J-Quants API クライアント（取得 & 保存）
    - news_collector.py         — RSS ニュース収集
  - research/
    - __init__.py
    - factor_research.py        — ファクター計算（Momentum/Value/Volatility）
    - feature_exploration.py    — 将来リターン・IC・統計サマリー

（上記は主要ファイルの抜粋です。さらに strategy / execution / monitoring 等の領域は __all__ に定義があり、将来的な追加や別パッケージで実装されることが想定されます。）

---

## テスト・開発ヒント

- OpenAI 呼び出し等をユニットテストする際は、モジュール内の `_call_openai_api` を patch してエミュレートすることが想定されています（news_nlp._call_openai_api, regime_detector._call_openai_api など）。
- DuckDB はインメモリ（":memory:"）で起動できるため、テスト用に軽量に初期テーブルをセットアップして検証できます。
- 自動 .env ロードはプロジェクトルートを基準に行います。CI やテスト時に自動ロードを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

もし README に追加してほしい例（CLI 実行例、より詳細な .env.example、CI / デプロイ手順、戦略レイヤーの使い方 など）があれば、その内容を教えてください。必要に応じて README を拡張します。