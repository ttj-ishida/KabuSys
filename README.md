# KabuSys

KabuSys は日本株のデータプラットフォームと自動売買／リサーチ基盤を提供する Python パッケージです。J-Quants API や RSS、OpenAI（LLM）を用いてデータ取得・品質チェック・NLP による記事センチメント評価・ファクター計算・監査ログ管理などを行えるよう設計されています。

バージョン: 0.1.0

---

## 概要

主な目的は以下です。

- J-Quants から株価・財務・市場カレンダーを差分取得して DuckDB に保存する ETL パイプライン
- RSS からニュースを収集して記事を保存・銘柄紐付けするニュースコレクタ
- OpenAI（gpt-4o-mini 等）によるニュースセンチメント評価（銘柄毎の ai_score、マクロセンチメント）
- ETF の移動平均乖離とマクロセンチメントからの日次市場レジーム判定（bull/neutral/bear）
- 監査ログ（シグナル→発注→約定のトレーサビリティ）用スキーマ初期化ユーティリティ
- ファクター計算・特徴量探索・統計ユーティリティ（Research 用）

設計上の特徴：
- ルックアヘッドバイアスを避ける（date の扱いに注意）
- DuckDB を中核データストアとして利用
- API 呼び出しはリトライ・レート制御・フェイルセーフを備える
- 冪等（idempotent）での DB 書き込みを重視

---

## 機能一覧

- データ取得 / ETL
  - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl（kabusys.data.pipeline）
  - J-Quants クライアント（kabusys.data.jquants_client）: fetch / save 関数一式
- データ品質チェック（kabusys.data.quality）
  - 欠損、スパイク、重複、日付不整合の検出
- マーケットカレンダー管理（kabusys.data.calendar_management）
  - 営業日判定 / next/prev_trading_day / calendar_update_job
- ニュース収集（kabusys.data.news_collector）
  - RSS 取得・正規化・SSRF 対策・raw_news への保存（冪等）
- NLP / LLM
  - 銘柄ごとのニュースセンチメント（kabusys.ai.news_nlp.score_news）
  - マクロセンチメントと MA 乖離を合成した市場レジーム判定（kabusys.ai.regime_detector.score_regime）
- 監査ログ（kabusys.data.audit）
  - audit テーブル（signal_events / order_requests / executions）DDL 作成、init_audit_db
- リサーチ用ユーティリティ（kabusys.research）
  - ファクター計算（momentum / value / volatility）、forward returns、IC、統計サマリー
- 共通ユーティリティ
  - 設定管理（kabusys.config: .env 自動ロード／settings）
  - 統計ユーティリティ（kabusys.data.stats.zscore_normalize）

---

## セットアップ手順

前提:
- Python 3.10 以上（型注釈で `X | None` などを使用）
- ネットワークアクセス（J-Quants / OpenAI / RSS）

推奨手順:

1. リポジトリをクローンして作業用仮想環境を作成
   - git clone ...
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .\.venv\Scripts\activate)

2. パッケージを編集可能インストール
   - pip install -e .

3. 必要な外部依存パッケージ（代表例）
   - duckdb
   - openai
   - defusedxml
   - （その他 標準ライブラリ以外のライブラリはプロジェクトの requirements を確認してください）

   例:
   - pip install duckdb openai defusedxml

4. 環境変数 / .env の準備
   - プロジェクトルート（.git や pyproject.toml があるディレクトリ）に `.env` / `.env.local` を置くと自動で読み込まれます。
   - 自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

   主要な環境変数（例）:
   - JQUANTS_REFRESH_TOKEN=（必須: J-Quants リフレッシュトークン）
   - OPENAI_API_KEY=（LLM を使う場合は必須）
   - KABU_API_PASSWORD=（kabuステーションを利用する場合）
   - KABU_API_BASE_URL=http://localhost:18080/kabusapi
   - LINE_CHANNEL_ACCESS_TOKEN=（通知を使う場合）
   - LINE_USER_ID=（通知先）
   - DUCKDB_PATH=data/kabusys.duckdb
   - SQLITE_PATH=data/monitoring.db
   - PID_FILE_PATH=data/execution.pid
   - KILL_FLAG_PATH=data/kill.flag
   - KABUSYS_ENV=development|paper_trading|live
   - LOG_LEVEL=INFO|DEBUG|...

   （.env の雛形はプロジェクトに .env.example がある想定です）

5. データベースの初期化（監査ログ等）
   - 監査用 DB を初期化する例（Python REPL / スクリプト）:
     from kabusys.config import settings
     import duckdb
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db(settings.duckdb_path)

   - 既存接続に対してスキーマを追加する場合:
     conn = duckdb.connect(str(settings.duckdb_path))
     from kabusys.data.audit import init_audit_schema
     init_audit_schema(conn, transactional=True)

---

## 使い方（基本例）

以下は主要なユースケースの最小実行例です。詳細は各モジュールの docstring を参照してください。

- ETL（日次パイプライン）の実行
  - 例: 日次 ETL を実行して得られた結果を確認する
    from datetime import date
    import duckdb
    from kabusys.config import settings
    from kabusys.data.pipeline import run_daily_etl

    conn = duckdb.connect(str(settings.duckdb_path))
    result = run_daily_etl(conn, target_date=date.today())
    print(result.to_dict())

- ニュースの AI スコア付け（銘柄別）
  - 必要: OPENAI_API_KEY 環境変数または api_key 引数
    from datetime import date
    import duckdb
    from kabusys.config import settings
    from kabusys.ai.news_nlp import score_news

    conn = duckdb.connect(str(settings.duckdb_path))
    written = score_news(conn, target_date=date(2026, 3, 20))
    print(f"書き込み銘柄数: {written}")

- 市場レジーム判定（ETF 1321 の MA200 とマクロセンチメント）
  - 必要: OPENAI_API_KEY
    from datetime import date
    import duckdb
    from kabusys.ai.regime_detector import score_regime

    conn = duckdb.connect(str(settings.duckdb_path))
    score_regime(conn, target_date=date(2026, 3, 20))

- 監査スキーマ初期化（既に紹介した init_audit_db / init_audit_schema を参照）

- リサーチ機能（ファクター計算等）
    from datetime import date
    import duckdb
    from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

    conn = duckdb.connect(str(settings.duckdb_path))
    mom = calc_momentum(conn, target_date=date(2026, 3, 20))
    vol = calc_volatility(conn, target_date=date(2026, 3, 20))
    val = calc_value(conn, target_date=date(2026, 3, 20))

備考:
- LLM 呼び出し（score_news / score_regime）は API 呼び出し制限や失敗が発生するため、失敗時はフェイルセーフ（0.0 など）で継続する設計です。
- すべての関数は可能な限りルックアヘッドバイアスを避けるよう設計されています（内部で date.today() 等を直接参照しない）。

---

## 環境変数一覧（主要）

- JQUANTS_REFRESH_TOKEN （必須: J-Quants リフレッシュトークン）
- OPENAI_API_KEY （LLM を利用する場合は必須）
- KABU_API_PASSWORD
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- LINE_CHANNEL_ACCESS_TOKEN
- LINE_USER_ID
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db)
- PID_FILE_PATH (デフォルト: data/execution.pid)
- KILL_FLAG_PATH (デフォルト: data/kill.flag)
- KILL_FLAG_CLEAR_ON_START (1/0)
- CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
- KABUSYS_ENV (development | paper_trading | live)
- LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL)
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env の自動ロードを無効化します。

---

## ディレクトリ構成

概要（主要ファイル/モジュールのみ抜粋）:

- src/kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py          — ニュースの LLM スコアリング（score_news）
    - regime_detector.py   — マクロセンチメント + MA 乖離による market regime（score_regime）
  - data/
    - __init__.py
    - jquants_client.py    — J-Quants API クライアント（fetch / save / get_id_token）
    - pipeline.py          — ETL パイプライン（run_daily_etl 等）
    - etl.py               — ETLResult の再公開
    - news_collector.py    — RSS 収集・正規化
    - calendar_management.py — 市場カレンダー／営業日ロジック
    - quality.py           — データ品質チェック
    - stats.py             — 統計ユーティリティ（zscore_normalize）
    - audit.py             — 監査ログスキーマ初期化
  - research/
    - __init__.py
    - factor_research.py   — ファクター計算（momentum/value/volatility）
    - feature_exploration.py — forward returns / IC / summary / rank
  - ai, research, data の他に strategy, execution, monitoring 等のサブパッケージが想定（__all__ 等で公開）

各モジュールは docstring に設計方針や処理フロー・注意点が詳述されており、API の使い方も内部ドキュメントに沿って利用できます。

---

## 運用・注意点

- セキュリティ:
  - RSS の取得は SSRF 対策、response size 制限、defusedxml による XML パース保護を行っています。
  - OpenAI / J-Quants のキーは .env に保存する場合は適切に管理してください。
- レート制御・リトライ:
  - J-Quants は 120 req/min の制約を想定（内部で固定間隔レートリミッタを実装）。
  - OpenAI 呼び出しにはリトライ・バックオフを実装しています。
- データ一貫性:
  - DuckDB への書き込みは基本的に冪等（ON CONFLICT DO UPDATE / DO NOTHING）で行います。
- ロギング:
  - 設定は環境変数 LOG_LEVEL、アプリ環境は KABUSYS_ENV により制御されます。

---

## 開発・拡張

- テストやモック:
  - LLM / ネットワーク呼び出しを含む関数はテストで差し替えやすいよう内部 _call_openai_api / _urlopen などを抽象化してあります（unittest.mock.patch などで差し替え可能）。
- 追加 API や戦略モジュール:
  - strategy / execution / monitoring 層を実装することで実際の発注フローへ接続できます（kabuステーション等）。
- バックテスト:
  - データプラットフォームとリサーチモジュールを用い、外部のバックテストフレームワークに接続して利用できます。Look-ahead に注意してください（各モジュールは配慮済み）。

---

もし README に追加したい「実行スクリプト例」「.env.example の完全な雛形」「依存関係の requirements.txt」などがあれば、その内容を教えてください。必要に応じて具体的な README 版やサンプルスクリプトを作成します。