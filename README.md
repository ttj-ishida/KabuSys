# KabuSys

日本株向けのデータ基盤・リサーチ・自動売買補助ライブラリです。  
データ取得（J-Quants）、ETL、品質チェック、ニュースの自然言語処理（OpenAI）、市場レジーム判定、リサーチ用ファクター計算、監査ログ（発注～約定のトレース）などを含みます。

## 特徴（機能一覧）
- 環境変数・設定管理
  - .env / .env.local の自動読み込み（プロジェクトルート判定）。必要な環境変数チェックを提供。
- データ取得・ETL（J-Quants）
  - 株価日足（OHLCV）、財務データ、JPX マーケットカレンダーの差分取得・保存（冪等）。
  - レートリミット・認証（refresh token → id token）・リトライ実装。
- データ品質チェック
  - 欠損、スパイク（前日比）、重複、日付不整合の検出。QualityIssue を返す。
- ニュース収集
  - RSS 収集、前処理（URL正規化・トラッキング除去）、SSRF対策、raw_news / news_symbols への冪等保存設計（※実装のDB保存部分は実コードに準拠）。
- ニュース NLP（OpenAI）
  - 銘柄ごとのニュースを LLM（gpt-4o-mini）でセンチメント付与（ai_scores テーブルへ保存）。
  - マクロニュースを用いた市場センチメント評価（regime 判定モジュール）。
  - JSON Mode を使った堅牢なレスポンス検証・リトライ処理。
- リサーチ用ユーティリティ
  - Momentum / Value / Volatility 等のファクター算出、将来リターン計算、IC（スピアマン）計算、Zスコア正規化など。
- 監査ログ（Audit）
  - signal_events / order_requests / executions テーブル定義と初期化ユーティリティ。発注から約定までのトレーサビリティ設計。
- カレンダー管理
  - market_calendar を元に営業日判定や next/prev_trading_day、calendar_update_job の夜間バッチを実装。
- DuckDB を主な永続化先として想定（データベースパスは設定可能）。

---

## セットアップ

前提
- Python 3.9+（型アノテーション等を使用しているため、適切なバージョンを推奨）
- 必要なライブラリ（例）
  - duckdb
  - openai
  - defusedxml
  - （標準ライブラリ以外の依存は setup.py / pyproject.toml を参照してください）

インストール（開発環境）
- リポジトリルートで editable インストール（pyproject.toml または setup.py がある前提）:
  - pip install -e .

環境変数
- 必須（実運用・一部機能で必須）:
  - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
  - KABU_API_PASSWORD — kabuステーション API パスワード（発注機能を使う場合）
  - SLACK_BOT_TOKEN — Slack 通知用（必要な場合）
  - SLACK_CHANNEL_ID — Slack チャンネルID
  - OPENAI_API_KEY — OpenAI 呼び出しに使用（news_nlp / regime_detector）
- 任意 / デフォルト値あり:
  - KABUSYS_ENV — "development" / "paper_trading" / "live"（デフォルト: development）
  - LOG_LEVEL — "DEBUG" / "INFO" / ...（デフォルト: INFO）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD — "1" を設定すると .env 自動読み込みを無効化
  - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）
- .env 自動読み込み
  - プロジェクトルート（.git または pyproject.toml を基準）にある `.env` と `.env.local` を自動で読み込みます。
  - 読み込み順: OS 環境 > .env.local > .env。テスト時に自動読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

データベース初期化（監査ログ）
- 監査ログ用 DuckDB を初期化する例:
  - from pathlib import Path
    import duckdb
    from kabusys.data.audit import init_audit_db
    conn = init_audit_db(Path("data/audit.duckdb"))

---

## 使い方（代表的な例）

基本的な前提: settings を経由して設定値を参照できます。
- 例: from kabusys.config import settings; settings.duckdb_path

DuckDB 接続
- import duckdb
  conn = duckdb.connect(str(settings.duckdb_path))

日次 ETL 実行
- from datetime import date
  from kabusys.data.pipeline import run_daily_etl
  result = run_daily_etl(conn, target_date=date(2026, 3, 20), id_token=None)
  # ETLResult を返し、品質チェックなどの情報を含む

ニュースセンチメントスコア付与（LLM）
- from datetime import date
  from kabusys.ai.news_nlp import score_news
  n = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
  # ai_scores テーブルへ書き込まれた銘柄数を返す

市場レジーム判定（マクロ + ETF MA200）
- from datetime import date
  from kabusys.ai.regime_detector import score_regime
  r = score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
  # market_regime テーブルへ書き込み、1 を返す（成功）

カレンダー更新バッチ
- from kabusys.data.calendar_management import calendar_update_job
  saved = calendar_update_job(conn, lookahead_days=90)

監査スキーマ初期化（既存 DB に追加）
- from kabusys.data.audit import init_audit_schema
  init_audit_schema(conn, transactional=True)

リサーチ関数例
- from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
  mom = calc_momentum(conn, target_date=date(2026,3,20))
  vol = calc_volatility(conn, target_date=date(2026,3,20))
  val = calc_value(conn, target_date=date(2026,3,20))
- from kabusys.research.feature_exploration import calc_forward_returns, calc_ic, factor_summary
  fwd = calc_forward_returns(conn, target_date=date(2026,3,20))
  ic = calc_ic(mom, fwd, "mom_1m", "fwd_1d")

注意点 / 実運用のヒント
- LLM 呼び出しでは API エラーや JSON パースエラーに対してフォールバック（0.0 など）する設計です。テスト時は _call_openai_api をモックして deterministic にできます。
- ETL / calendar_update_job 等は外部 API（J-Quants）に依存するため、ネットワーク・認証情報の管理に注意してください。
- DuckDB executemany の挙動（空リスト不可など）を考慮した実装ガードが入っています。

---

## ディレクトリ構成（主要ファイル）
以下は src/kabusys 配下の主要モジュール一覧（抜粋）です。

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数・設定管理
  - ai/
    - __init__.py            — score_news エクスポート
    - news_nlp.py            — ニュースセンチメント（LLM）処理
    - regime_detector.py     — 市場レジーム判定（MA + マクロセンチメント）
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント & DuckDB 保存関数
    - pipeline.py            — ETL パイプライン（run_daily_etl 等）
    - etl.py                 — ETLResult 再エクスポート
    - stats.py               — 統計ユーティリティ（zscore_normalize）
    - quality.py             — データ品質チェック
    - news_collector.py      — RSS ニュース収集
    - calendar_management.py — 市場カレンダー管理・判定ロジック
    - audit.py               — 監査ログ（テーブル定義・初期化）
  - research/
    - __init__.py
    - factor_research.py     — Momentum/Value/Volatility 等
    - feature_exploration.py — 将来リターン / IC / 統計サマリー

（上記以外にも strategy / execution / monitoring 等のパッケージが想定されますが、今回のコードベースでは主に data / ai / research の実装が含まれています。）

---

## 開発・テストのヒント
- 環境変数自動読み込みを無効化したいテストでは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- OpenAI / J-Quants 等の外部呼び出しはユニットテストでモックしてください。各モジュールは _call_openai_api や _urlopen などを差し替え可能に実装しています。
- DuckDB を :memory: で使用するとテストが容易です（init_audit_db(":memory:") 等）。

---

この README はコードベースから抽出した設計意図・使用方法の要約です。各関数の詳細な引数・戻り値や副作用については、該当モジュールの docstring を参照してください。補足やサンプル追加の希望があればお知らせください。