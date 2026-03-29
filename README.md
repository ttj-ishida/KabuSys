KabuSys — 日本株自動売買プラットフォーム（README）
=================================

概要
----
KabuSys は日本株のデータ収集（ETL）、データ品質チェック、ニュースベースの NLP（LLM）評価、調査（ファクター計算）、監査ログ管理、そして将来的な自動売買のための土台を提供する Python パッケージです。  
主に DuckDB をデータレイヤに利用し、J-Quants API から市場データ・財務データ・JPX カレンダーを取得、RSS からニュースを収集して LLM（OpenAI）でセンチメント分析を行い、研究・戦略モジュールへ供給します。

主な機能
--------
- データ ETL
  - J-Quants から日次株価（OHLCV）、財務諸表、取引カレンダーを差分取得・保存（冪等）
  - 日次パイプライン run_daily_etl を提供
- データ品質チェック
  - 欠損、スパイク、重複、日付整合性等のチェック
- ニュース収集・前処理
  - RSS 収集（SSRF 対策、トラッキングパラメータ除去）、raw_news への保存支援
- ニュース NLP / LLM
  - 銘柄別ニュースのセンチメントスコア化（score_news）
  - マクロニュース + ETF MA を用いた市場レジーム判定（score_regime）
  - OpenAI（gpt-4o-mini）との連携、JSON Mode 対応、リトライとフェイルセーフ設計
- 研究／リサーチツール
  - モメンタム / バリュー / ボラティリティ等のファクター計算
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー等
- 監査ログ（Audit）
  - signal_events / order_requests / executions の監査テーブル定義と初期化ユーティリティ
- J-Quants クライアント
  - レートリミット、トークン自動リフレッシュ、ページネーション、保存ユーティリティ

セットアップ手順
----------------
前提
- Python 3.10+（ソース内で PEP 604 の | 型ヒントを使用）
- DuckDB、OpenAI SDK 等の依存ライブラリ

1. 仮想環境作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  # Windows: .venv\Scripts\activate

2. 依存パッケージ（例）
   - pip install duckdb openai defusedxml
   - （実プロジェクトでは requirements.txt を用意して pip install -r requirements.txt を推奨）

3. ソース配置
   - パッケージは src/kabusys 以下にあります。開発環境ではプロジェクトルートに .git または pyproject.toml があると自動的に .env を読み込みます。

4. 環境変数設定
   - プロジェクトルートに .env を置くか、OS 環境変数を設定してください。
   - 主要な環境変数（必須は README 内で明記）:
     - JQUANTS_REFRESH_TOKEN (必須) — J-Quants の refresh token
     - KABU_API_PASSWORD (必須) — kabuステーション API 用パスワード
     - SLACK_BOT_TOKEN (必須) — Slack 通知用 Bot トークン
     - SLACK_CHANNEL_ID (必須) — Slack チャンネル ID
     - OPENAI_API_KEY — OpenAI API キー（score_news/score_regime で使用）
     - KABU_API_BASE_URL — kabu API ベース URL（デフォルト http://localhost:18080/kabusapi）
     - DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH — SQLite（監視用）パス（デフォルト data/monitoring.db）
     - KABUSYS_ENV — environment: development / paper_trading / live（デフォルト development）
     - LOG_LEVEL — DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト INFO）
   - 自動 .env ロードを無効化するには:
     - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

5. データベース初期化（監査ログなど）
   - 例: 監査用 DB を作る
     - python -c "import duckdb, pathlib; from kabusys.data.audit import init_audit_db; init_audit_db('data/audit.duckdb')"

使い方（主な API・実行例）
-------------------------

- Settings（環境変数取得）
  - from kabusys.config import settings
  - settings.jquants_refresh_token, settings.duckdb_path, settings.is_live などで参照

- DuckDB 接続例
  - import duckdb
    from kabusys.config import settings
    conn = duckdb.connect(str(settings.duckdb_path))

- 日次 ETL 実行
  - from datetime import date
    from kabusys.data.pipeline import run_daily_etl
    conn = duckdb.connect(str(settings.duckdb_path))
    result = run_daily_etl(conn, target_date=date(2026,3,20))
    print(result.to_dict())

- ニューススコア（LLM を用いた銘柄別スコア）
  - from datetime import date
    from kabusys.ai.news_nlp import score_news
    conn = duckdb.connect(str(settings.duckdb_path))
    n_written = score_news(conn, target_date=date(2026,3,20), api_key="sk-...")
    print("written:", n_written)

  - score_news は OPENAI_API_KEY 環境変数を参照します。空文字列も未設定扱いです。

- 市場レジーム判定
  - from datetime import date
    from kabusys.ai.regime_detector import score_regime
    conn = duckdb.connect(str(settings.duckdb_path))
    score_regime(conn, target_date=date(2026,3,20), api_key="sk-...")

  - LLM 呼び出し失敗時はマクロセンチメントを 0 にフォールバックし、処理を継続します。

- 監査スキーマ初期化（既存接続に対して）
  - from kabusys.data.audit import init_audit_schema
    conn = duckdb.connect(str(settings.duckdb_path))
    init_audit_schema(conn, transactional=True)

- 研究用ユーティリティ例
  - from kabusys.research import calc_momentum, calc_value, calc_volatility
    records = calc_momentum(conn, target_date=date(2026,3,20))

注意点・設計上のポイント
-----------------------
- Look-ahead バイアス回避:
  - 多くのモジュール（ETL / news / regime / research）は datetime.today()/date.today() を内部で参照しないよう設計されており、必ず target_date を明示して使用することが推奨されています。
- LLM 呼び出し:
  - OpenAI SDK（gpt-4o-mini）を使います。レスポンスのパース失敗や API エラーはフェイルセーフで処理を続ける設計です（スコアは 0 にフォールバック）。
- 環境変数の自動ロード:
  - パッケージはプロジェクトルート（.git または pyproject.toml）を探索して .env / .env.local を自動読み込みします。テストなどで無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB の executemany に対する注意:
  - 一部の場所（ai_scores 置換など）で DuckDB 0.10 の仕様に合わせて空リストの executemany を回避する実装になっています。

ディレクトリ構成（概要）
----------------------
src/kabusys/
- __init__.py
- config.py                      — 環境変数／設定管理（.env 自動ロード含む）
- ai/
  - __init__.py
  - news_nlp.py                   — ニュース NLP（score_news）
  - regime_detector.py            — マクロ + ETF MA による市場レジーム判定（score_regime）
- data/
  - __init__.py
  - calendar_management.py        — JPX カレンダー管理、営業日判定
  - etl.py / pipeline.py          — ETL パイプラインと ETLResult
  - jquants_client.py             — J-Quants API クライアント（取得・保存）
  - news_collector.py             — RSS 収集・前処理（SSRF 対策等）
  - quality.py                    — データ品質チェック（欠損・スパイク等）
  - stats.py                      — 統計ユーティリティ（zscore 等）
  - audit.py                      — 監査ログ（テーブル定義・初期化）
  - etl.py (公開エントリ)         — ETLResult の再エクスポート
- research/
  - __init__.py
  - factor_research.py            — モメンタム/バリュー/ボラ計算
  - feature_exploration.py        — 将来リターン, IC, 統計サマリー等

サンプル .env（必要最低限）
------------------------
# J-Quants
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here

# KabuAPI
KABU_API_PASSWORD=your_kabu_api_password_here
# KABU_API_BASE_URL=http://localhost:18080/kabusapi  # 必要なら上書き

# Slack
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567

# OpenAI（LLM）
OPENAI_API_KEY=sk-...

# DB
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db

# 実行環境
KABUSYS_ENV=development
LOG_LEVEL=INFO

サポート・拡張
---------------
- 本リポジトリはデータ基盤・研究・監査のコア機能を提供するための土台です。戦略（strategy）、約定（execution）、モニタリング（monitoring）等の上位レイヤは別モジュール／実装として追加してください（パッケージ __all__ にこれらが想定されています）。
- OpenAI の呼び出し部分はテストのために差し替え（モック）可能な構造になっています。

最終メモ
--------
この README はコードベースに含まれる docstring と実装に基づいて要点をまとめたものです。実行前に .env を正しく設定し、必要な外部ライブラリ（duckdb, openai, defusedxml など）をインストールしてください。質問や追加のドキュメント（使い方の細かい例など）が必要であればお知らせください。