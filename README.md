# KabuSys

日本株向けの自動売買 / データ基盤ライブラリ。J-Quants API からデータを取得して DuckDB に保存し、ニュースの NLP スコアリングや市場レジーム判定、ファクター計算・探索、監査ログ（発注〜約定のトレーサビリティ）などの機能を提供します。

---

## プロジェクト概要

KabuSys は以下の用途を想定した Python パッケージです。

- J-Quants から株価・財務・上場情報・マーケットカレンダーを ETL で取得して DuckDB に保存
- RSS ニュース収集と前処理（SSRF 対策・追跡パラメータ除去）
- OpenAI（gpt-4o-mini）を使ったニュースのセンチメント解析（銘柄別 ai_score / マクロセンチメント）
- ETF（1321）200日移動平均乖離とマクロセンチメントを合成した市場レジーム判定
- ファクター計算（モメンタム/バリュー/ボラティリティ等）と特徴量探索（将来リターン計算、IC、統計サマリー）
- データ品質チェック（欠損・重複・スパイク・日付不整合）
- 監査ログテーブル（signal_events / order_requests / executions）を DuckDB に初期化・管理

設計上の特徴:
- ルックアヘッドバイアス対策（内部で date.today() を不用意に参照しない等）
- 冪等性を意識した DB 書き込み（ON CONFLICT / DELETE→INSERT 等）
- 外部 API 呼び出しに対するリトライ・レート制御・フェイルセーフ（失敗時にゼロやスキップで継続）
- 外部ライブラリへの過度な依存を避け、標準ライブラリと duckdb / openai 等を利用

---

## 主な機能一覧

- data
  - ETL パイプライン（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - J-Quants API クライアント（fetch/save の実装・レートリミット・トークン自動リフレッシュ）
  - 市場カレンダー管理（is_trading_day, next_trading_day, prev_trading_day, get_trading_days）
  - ニュース収集（RSS → raw_news、トラッキングパラメータ削除、SSRF 防止）
  - データ品質チェック（欠損 / スパイク / 重複 / 日付不整合）
  - 監査ログ初期化（init_audit_schema / init_audit_db）
  - 汎用統計ユーティリティ（zscore_normalize）
- ai
  - ニュース NLP スコアリング（score_news）
  - 市場レジーム判定（score_regime）
- research
  - ファクター計算（calc_momentum / calc_value / calc_volatility）
  - 特徴量探索（calc_forward_returns / calc_ic / factor_summary / rank）
- config
  - 環境変数 / .env 読み込みと設定ラッパー（settings オブジェクト）

---

## セットアップ手順

以下はローカル開発 / 実行のための一般的な手順です。プロジェクトの pyproject.toml / requirements.txt がある前提で調整してください。

1. Python 環境
   - Python 3.10+ を推奨（ソースは型ヒントで | を使っているため 3.10 以上が好ましい）。
   - 仮想環境を作成して有効化（例: python -m venv .venv && source .venv/bin/activate）。

2. 依存ライブラリをインストール
   - 代表的に必要なパッケージ:
     - duckdb
     - openai
     - defusedxml
   - 例:
     - pip install duckdb openai defusedxml

   （プロジェクトに requirements.txt や pyproject.toml があればそれに従ってください）
   - パッケージを editable インストールする場合:
     - pip install -e .

3. 環境変数 / .env
   - ルートの .env / .env.local を自動で読み込みます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動読み込みを無効化可能）。
   - 必須環境変数（例）
     - JQUANTS_REFRESH_TOKEN — J-Quants 用リフレッシュトークン（必須）
     - OPENAI_API_KEY — OpenAI API キー（score_news / score_regime 実行時に必要）
     - KABU_API_PASSWORD — kabuステーション API のパスワード（発注機能等で使用）
     - SLACK_BOT_TOKEN — Slack 通知用トークン（通知機能を使う場合）
     - SLACK_CHANNEL_ID — Slack チャンネル ID
   - 任意 / デフォルト値を持つ項目
     - KABU_API_BASE_URL — デフォルト: http://localhost:18080/kabusapi
     - DUCKDB_PATH — デフォルト: data/kabusys.duckdb
     - SQLITE_PATH — デフォルト: data/monitoring.db
     - PID_FILE_PATH — デフォルト: data/execution.pid
     - CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT — 監視閾値（パーセンテージ）
     - KABUSYS_ENV — development / paper_trading / live（デフォルト development）
     - LOG_LEVEL — DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト INFO）

   - 簡易 .env.example 例:
     - JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     - OPENAI_API_KEY=sk-...
     - KABU_API_PASSWORD=your_kabu_password
     - SLACK_BOT_TOKEN=xoxb-...
     - SLACK_CHANNEL_ID=C12345678

4. DB 初期化（監査ログ等）
   - 監査ログ専用 DB を初期化する例:
     - Python REPL / スクリプト:
       - from kabusys.data.audit import init_audit_db
         conn = init_audit_db("data/audit.duckdb")
     - または、既存の DuckDB 接続に対して init_audit_schema(conn) を呼ぶことも可能。

---

## 使い方（主要な関数例）

以下は Python から直接利用するシンプルな例です。日時は date 型を使用します。

- DuckDB 接続の作成例:
  - import duckdb
    conn = duckdb.connect("data/kabusys.duckdb")

- 日次 ETL を実行する（市場カレンダー / 株価 / 財務 / 品質チェックを順に実行）
  - from datetime import date
    from kabusys.data.pipeline import run_daily_etl
    conn = duckdb.connect("data/kabusys.duckdb")
    result = run_daily_etl(conn, target_date=date(2026, 3, 20))
    print(result.to_dict())

- ニュース NLP スコアリングを実行（OpenAI API キー必須）
  - from datetime import date
    from kabusys.ai.news_nlp import score_news
    conn = duckdb.connect("data/kabusys.duckdb")
    count = score_news(conn, target_date=date(2026, 3, 20))
    print(f"scored {count} codes")

- 市場レジーム判定を実行（ETF 1321 の MA200 とマクロセンチメントを合成）
  - from datetime import date
    from kabusys.ai.regime_detector import score_regime
    conn = duckdb.connect("data/kabusys.duckdb")
    score_regime(conn, target_date=date(2026, 3, 20))

- 監査ログスキーマ初期化
  - from kabusys.data.audit import init_audit_db
    conn = init_audit_db("data/audit.duckdb")

- ファクター計算 / 研究系ユーティリティ
  - from kabusys.research.factor_research import calc_momentum, calc_value
    res = calc_momentum(conn, date(2026,3,20))
    # z-score 正規化
    from kabusys.data.stats import zscore_normalize
    normed = zscore_normalize(res, ["mom_1m", "mom_3m", "mom_6m"])

注意点:
- score_news / score_regime は OpenAI API を呼ぶため OPENAI_API_KEY（または api_key 引数）を必ず設定してください。
- ETL の J-Quants 呼び出しには JQUANTS_REFRESH_TOKEN が必要です（settings.jquants_refresh_token）。
- 多くの DB 操作は DuckDB を想定しています。事前にスキーマ / テーブルが作成されていることが前提の関数もあります（ETL 実行前に schema 初期化処理があるはずのスクリプトを参照してください）。

---

## ディレクトリ構成

主要なソースは src/kabusys 以下にあり、機能ごとにサブパッケージで整理されています（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                    — 環境変数 / .env 管理（settings オブジェクト）
  - ai/
    - __init__.py
    - news_nlp.py                — ニュース NLP（score_news）
    - regime_detector.py         — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py          — J-Quants API クライアント（fetch/save 等）
    - pipeline.py                — ETL パイプライン（run_daily_etl 等）
    - etl.py                     — ETLResult の公開（再エクスポート）
    - news_collector.py          — RSS 収集・前処理
    - calendar_management.py     — 市場カレンダー管理
    - quality.py                 — データ品質チェック
    - stats.py                   — 共通統計ユーティリティ（zscore_normalize）
    - audit.py                   — 監査ログテーブルの DDL / 初期化
  - research/
    - __init__.py
    - factor_research.py         — ファクター計算（momentum/value/volatility 等）
    - feature_exploration.py     — 将来リターン / IC / 統計サマリー

その他:
- .env / .env.local 自動読み込み（project root から探索）。CWD に依存せず __file__ ベースでプロジェクトルートを特定します。

---

## 環境変数一覧（主なもの）

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン（ETL）
- OPENAI_API_KEY — OpenAI API キー（AI モジュール）
- KABU_API_PASSWORD — kabuAPI パスワード（発注関連）
- SLACK_BOT_TOKEN — Slack 通知トークン（通知機能）
- SLACK_CHANNEL_ID — Slack チャンネル ID

オプション / デフォルトあり:
- KABU_API_BASE_URL — デフォルト: http://localhost:18080/kabusapi
- DUCKDB_PATH — デフォルト: data/kabusys.duckdb
- SQLITE_PATH — デフォルト: data/monitoring.db
- PID_FILE_PATH — デフォルト: data/execution.pid
- CPU_THRESHOLD_PCT — デフォルト: 90.0
- MEMORY_THRESHOLD_PCT — デフォルト: 85.0
- DISK_THRESHOLD_PCT — デフォルト: 90.0
- KABUSYS_ENV — development | paper_trading | live（デフォルト development）
- LOG_LEVEL — DEBUG|INFO|WARNING|ERROR|CRITICAL（デフォルト INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 を設定すると .env の自動読み込みを無効化

---

## 注意事項 / 開発上のヒント

- DuckDB の executemany に空リストを渡すとバージョン依存でエラーになるため、コード中で空チェックを行っています。スクリプトを編集する場合は注意してください。
- OpenAI 呼び出しはレスポンスの JSON パースや 5xx / rate limit に対するリトライを実装していますが、API コストとレート制限に注意して運用してください。
- news_collector は SSRF 対策（リダイレクト検査・プライベートホスト検知）や XML パースに defusedxml を利用しています。外部 RSS を扱う場合はホワイトリスト運用を推奨します。
- audit.init_audit_schema は transactional オプションを持ちます。DuckDB のトランザクション挙動（ネスト不可）に注意してください。

---

もし README に追加したい動作検証スクリプトや CI / デプロイ手順、より詳細な環境変数の例、あるいはテーブルスキーマの完全一覧が必要であれば、その旨を教えてください。README を具体的な実行例やスクリプトに合わせて拡張できます。