# KabuSys

日本株向け自動売買 / データプラットフォーム用ライブラリ集です。  
ETL、ニュース収集・NLP、研究用ファクター計算、監査ログ、J‑Quants クライアントなどを含み、バックテストや運用バッチの基盤処理を提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は以下の目的を持ったモジュール群を提供します。

- J-Quants API からの株価・財務・カレンダーの差分取得（ETL）
- RSS を使ったニュース収集と前処理（SSRF 対策やトラッキング除去対応）
- OpenAI（gpt-4o-mini）を使ったニュースのセンチメント評価（銘柄別 ai_score / マクロセンチメント）
- 市場レジーム判定（ETF の MA乖離 と マクロセンチメントの合成）
- 研究向けファクター計算（モメンタム／ボラティリティ／バリュー等）
- データ品質チェック（欠損、重複、スパイク、日付整合性）
- 監査ログスキーマ（シグナル→発注→約定のトレーサビリティ）
- DuckDB を使ったローカル DB 操作ユーティリティ

設計上の特徴：
- Look-ahead bias を避ける設計（明示的な target_date を多用）
- 冪等操作（DB 保存は基本 ON CONFLICT / 個別 DELETE→INSERT など）
- フェイルセーフな外部 API 呼び出し（リトライ／バックオフ／部分失敗保護）
- 外部依存は最小限（標準ライブラリ + 必要なパッケージ）

---

## 機能一覧

主な機能（モジュール別）

- kabusys.config
  - .env / 環境変数の読み込み・設定管理（自動読み込み: .env → .env.local）
  - 必須設定の検査（例: JQUANTS_REFRESH_TOKEN, OPENAI_API_KEY など）
- kabusys.data.jquants_client
  - J-Quants API からのデータ取得（prices / financials / calendar / listed info）
  - DuckDB への保存ユーティリティ（save_daily_quotes, save_financial_statements, save_market_calendar）
  - レートリミット・リトライ・トークン自動リフレッシュ対応
- kabusys.data.pipeline / etl
  - 日次 ETL パイプライン（run_daily_etl）と個別 ETL ジョブ（run_prices_etl 等）
  - ETL 結果を ETLResult で集約（品質問題やエラー情報含む）
- kabusys.data.news_collector
  - RSS 取得・前処理・記事 ID 正規化（トラッキング除去、SSRF 対策）
  - raw_news / news_symbols への冪等保存用補助
- kabusys.data.quality
  - 欠損・スパイク・重複・日付不整合のチェック（run_all_checks）
- kabusys.data.calendar_management
  - JPX カレンダーの管理、営業日判定（is_trading_day / next_trading_day / prev_trading_day / get_trading_days）
  - calendar_update_job（J-Quants から差分取得して保存）
- kabusys.data.audit
  - 監査ログ用スキーマ定義・初期化（signal_events / order_requests / executions）
  - init_audit_schema / init_audit_db
- kabusys.ai.news_nlp
  - 銘柄ごとのニュース集合を LLM に送りセンチメントスコアを ai_scores テーブルへ書き込む（score_news）
- kabusys.ai.regime_detector
  - ETF（1321）の 200 日 MA 乖離とマクロニュースセンチメントを合成して market_regime に記録（score_regime）
- kabusys.research
  - ファクター計算（calc_momentum, calc_value, calc_volatility）
  - 特徴量探索（calc_forward_returns, calc_ic, factor_summary, rank）
- kabusys.data.stats
  - zscore_normalize（クロスセクション Z スコア正規化）

---

## 前提 / 必要環境

- Python 3.10 以上（PEP 604 の型注釈（A | B）を利用しているため）
- 推奨パッケージ（最低限）:
  - duckdb
  - openai
  - defusedxml

例（pip）:
pip install duckdb openai defusedxml

実際の運用ではさらにログ収集、Slack 通知等の依存が必要になる場合があります（トークンは環境変数で設定）。

---

## セットアップ手順（ローカル開発用）

1. リポジトリをクローン
   git clone <repo-url>
   cd <repo>

2. 仮想環境を作成・有効化（任意）
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows

3. 必要パッケージをインストール
   pip install -U pip
   pip install duckdb openai defusedxml

   （プロジェクトで requirements.txt がある場合は pip install -r requirements.txt）

4. 環境変数を設定
   - 推奨はプロジェクトルートに `.env` / `.env.local` を作成して設定する（自動読み込みされます）。
   - 自動読み込みを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。

   主な環境変数:
   - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（必須）
   - OPENAI_API_KEY         : OpenAI API キー（score_news / score_regime で必要）
   - KABU_API_PASSWORD      : kabu API パスワード（発注連携がある場合）
   - KABU_API_BASE_URL      : kabu API の base URL（省略時: http://localhost:18080/kabusapi）
   - SLACK_BOT_TOKEN        : Slack ボットトークン（通知等に使用する場合）
   - SLACK_CHANNEL_ID       : Slack チャンネル ID
   - DUCKDB_PATH            : DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
   - SQLITE_PATH            : SQLite（監視用）パス（デフォルト data/monitoring.db）
   - KABUSYS_ENV            : environment ('development' / 'paper_trading' / 'live')
   - LOG_LEVEL              : ログレベル（DEBUG/INFO/...）

5. データディレクトリの作成（必要に応じて）
   mkdir -p data

---

## 使い方（簡単な例）

以下は Python REPL やスクリプトから呼び出す最小例です。OpenAI / J‑Quants の認証情報は環境変数か引数で渡してください。

- DuckDB 接続を開いて日次 ETL を実行する例:
  from datetime import date
  import duckdb
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect(str("data/kabusys.duckdb"))
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())

- ニュースのスコア付け（ai_scores へ書き込む）:
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  n_written = score_news(conn, target_date=date(2026, 3, 20))
  print("written:", n_written)

  ※ OPENAI_API_KEY を環境変数で設定するか、score_news(..., api_key="...") を渡す。

- 市場レジーム判定:
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20))

- 監査ログ DB 初期化:
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")

- 研究用ファクター計算（例: モメンタム）:
  from datetime import date
  import duckdb
  from kabusys.research.factor_research import calc_momentum

  conn = duckdb.connect("data/kabusys.duckdb")
  records = calc_momentum(conn, target_date=date(2026, 3, 20))
  print(len(records), "銘柄")

---

## 注意点 / 運用上のヒント

- Look-ahead bias を避けるため、各モジュールは明示的な target_date を引数に取る設計です。テストやバックテストではその点に注意してください。
- OpenAI 呼び出しはコスト・レイテンシが発生します。score_news / score_regime はバッチ的に実行することを推奨します。
- J-Quants の API レートリミットや認証は jquants_client が管理します。大量のページネーションが発生する場合は実行計画に注意してください。
- news_collector は外部 RSS の取得において SSRF・圧縮爆弾対策・追跡パラメータ除去を実装しています。独自ソースを追加する際は DEFAULT_RSS_SOURCES を更新してください。
- DuckDB のバージョン差異により executemany の挙動等が異なる場合があります（コード内で互換性対策済み）。

---

## ディレクトリ構成（主なファイルと説明）

src/kabusys/
- __init__.py
  - パッケージのエクスポート設定（data, strategy, execution, monitoring）

- config.py
  - 環境変数／.env の自動読み込み、Settings クラス

- ai/
  - __init__.py
    - score_news の公開
  - news_nlp.py
    - ニュースセンチメントのバッチ評価（score_news）
  - regime_detector.py
    - 市場レジーム判定（score_regime）

- data/
  - __init__.py
  - jquants_client.py
    - J-Quants API クライアント＆DuckDB 保存ユーティリティ
  - pipeline.py / etl.py
    - ETL パイプライン、run_daily_etl 等、ETLResult
  - news_collector.py
    - RSS ニュース収集、前処理、SSRF 対策
  - quality.py
    - データ品質チェック（欠損・スパイク・重複・日付整合性）
  - calendar_management.py
    - JPX カレンダー管理、営業日判定、calendar_update_job
  - audit.py
    - 監査ログ（signal_events / order_requests / executions）スキーマ初期化
  - stats.py
    - 汎用統計ユーティリティ（zscore_normalize）
  - etl.py
    - ETLResult の再エクスポート（外部公開インターフェース）

- research/
  - __init__.py
    - 研究系関数の公開
  - factor_research.py
    - calc_momentum / calc_value / calc_volatility
  - feature_exploration.py
    - calc_forward_returns / calc_ic / factor_summary / rank

（strategy / execution / monitoring パッケージは __all__ に含まれていますが、このスナップショットでは主要な data/ai/research モジュールに重点を置いています）

---

## トラブルシューティング

- .env が自動読み込みされない場合
  - KABUSYS_DISABLE_AUTO_ENV_LOAD を確認（1 の場合は無効化）
  - プロジェクトルートの検出は .git または pyproject.toml を基準にします。パッケージを別ディレクトリで展開した場合は環境変数を手動で設定してください。

- OpenAI / J-Quants のエラー
  - API キーやトークンの有効期限を確認してください。jquants_client は 401 を検出するとリフレッシュを試みますが、refresh token の有効性が前提です。
  - レート制限・429 は自動バックオフで再試行されますが、繰り返し発生する場合は実行間隔を広げてください。

---

必要であれば、導入スクリプト（systemd タイマー用の起動スクリプト、簡易 CLI、Dockerfile など）のテンプレートも作成できます。どの運用形態に合わせた手順が欲しいか教えてください。