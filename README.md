# KabuSys

日本株向けの自動売買・データプラットフォームのコアライブラリです。  
ETL（J-Quants からの日次データ取得）、ニュース収集、AI によるニュースセンチメント/市場レジーム判定、ファクター計算、監査ログ（発注・約定トレーサビリティ）などを提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下を目的とした Python モジュール群です。

- J-Quants API からの株価 / 財務 / 市場カレンダー等の差分 ETL
- RSS 等からのニュース収集と前処理（raw_news）
- OpenAI を使ったニュースのセンチメント解析（ai.news_nlp）
- マクロ + テクニカル指標からの市場レジーム判定（ai.regime_detector）
- 研究用のファクター計算・特徴量探索（research）
- 監査ログ（signal / order_request / execution）用のスキーマ初期化・DB 操作（data.audit）
- データ品質チェック（data.quality）
- DuckDB を中心としたローカルデータ処理基盤

設計方針として、バックテストでのルックアヘッドバイアス防止、ETL の冪等性、外部 API の堅牢なリトライ処理（指数バックオフ）などを重視しています。

---

## 機能一覧

主な機能（モジュール別）

- kabusys.config
  - 環境変数の自動ロード（.env / .env.local）と設定取得ユーティリティ
- kabusys.data.jquants_client
  - J-Quants API からのデータ取得（daily_quotes, financial_statements, trading_calendar）
  - DuckDB への冪等保存関数（save_*）
- kabusys.data.pipeline
  - run_daily_etl: 日次 ETL（カレンダー → 株価 → 財務 → 品質チェック）
  - ETLResult 型（実行結果）
- kabusys.data.news_collector
  - RSS 取得・正規化・前処理・raw_news 保存支援
  - SSRF 対策、受信サイズ上限、URL 正規化、記事ID生成 等
- kabusys.data.quality
  - 欠損、重複、スパイク、日付不整合などの品質チェック
- kabusys.data.audit
  - signal_events / order_requests / executions の DDL とインデックス初期化
  - init_audit_db / init_audit_schema
- kabusys.ai.news_nlp
  - raw_news を銘柄ごとにまとめ、OpenAI（gpt-4o-mini）でセンチメントを算出して ai_scores に書き込む（score_news）
- kabusys.ai.regime_detector
  - ETF（1321）の 200 日 MA 乖離とマクロニュースの LLM センチメントを合成して日次の市場レジームを判定（score_regime）
- kabusys.research
  - ファクター計算（momentum / volatility / value）、forward returns、IC 計算、統計サマリー等
- kabusys.data.stats
  - zscore_normalize 等の汎用統計ユーティリティ

---

## 前提条件 / 必要環境

- Python 3.10 以上（型ヒントに「|」を使用）
- 推奨パッケージ（例）
  - duckdb
  - openai
  - defusedxml
- ネットワーク接続（J-Quants / OpenAI / RSS ソース を使用する場合）
- DuckDB や SQLite を使うためのディスク領域

requirements.txt がある場合はそれを利用してください（本リポジトリに含まれる場合）。

例:
```
python -m pip install -U pip
python -m pip install duckdb openai defusedxml
# 追加の依存があれば pip でインストール
```

開発中は editable install:
```
python -m pip install -e .
```

---

## 環境変数

config.Settings クラスで参照される主な環境変数（必須は明記）:

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API のパスワード
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack 通知用 Bot トークン（将来の通知連携）
- SLACK_CHANNEL_ID (必須) — Slack チャンネル ID
- OPENAI_API_KEY — OpenAI API キー（ai モジュール実行時に必須）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト data/monitoring.db）
- PID_FILE_PATH — 実行プロセス PID ファイル（デフォルト data/execution.pid）
- CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT — 監視閾値（%）
- KABUSYS_ENV — 実行環境 (development | paper_trading | live)（デフォルト development）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）

.env 自動読み込み:
- パッケージはプロジェクトルート（.git または pyproject.toml を起点）を探索して
  OS > .env.local > .env の優先度で環境変数を読み込みます。
- 自動ロードを無効化するには: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

.env の書式やコメント、クォートの扱いは kabusys.config._parse_env_line に準拠します。

---

## セットアップ手順

1. リポジトリをクローン:
   - git clone <repo-url>

2. Python 仮想環境を作成・有効化（推奨）:
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール:
   - python -m pip install -U pip
   - python -m pip install duckdb openai defusedxml

   （プロジェクトに requirements.txt があれば python -m pip install -r requirements.txt）

4. 環境変数設定:
   - プロジェクトルートに .env（または .env.local）を作成して必要なキーを設定。
   - 例 (.env):
     JQUANTS_REFRESH_TOKEN=xxxxx
     OPENAI_API_KEY=sk-xxxxx
     KABU_API_PASSWORD=...
     SLACK_BOT_TOKEN=...
     SLACK_CHANNEL_ID=...

5. データディレクトリ作成（デフォルトパスを使用する場合）:
   - mkdir -p data

6. 監査用 DB 初期化（必要に応じて）:
   - Python REPL またはスクリプトで次を実行して DuckDB を初期化:
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")

---

## 使い方（簡単な例）

以下は代表的なユースケースの最小例です。実際はログ設定や例外処理を追加してください。

- DuckDB 接続の準備:
  from datetime import date
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")

- 日次 ETL を実行:
  from kabusys.data.pipeline import run_daily_etl
  result = run_daily_etl(conn, target_date=date(2026,3,20))
  print(result.to_dict())

- ニュースセンチメントの算出（OpenAI API が必要）:
  from kabusys.ai.news_nlp import score_news
  from datetime import date
  # api_key を引数で渡すか、環境変数 OPENAI_API_KEY を設定
  n_written = score_news(conn, target_date=date(2026,3,20), api_key=None)
  print("書き込んだ銘柄数:", n_written)

- 市場レジーム判定:
  from kabusys.ai.regime_detector import score_regime
  from datetime import date
  score_regime(conn, target_date=date(2026,3,20), api_key=None)

- 監査ログスキーマ初期化:
  from kabusys.data.audit import init_audit_db, init_audit_schema
  conn_audit = init_audit_db("data/audit.duckdb")  # ファイル作成 + スキーマ作成
  # または既存 conn に対して init_audit_schema(conn, transactional=True)

- 研究用ファクター計算:
  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
  from datetime import date
  m = calc_momentum(conn, date(2026,3,20))
  v = calc_value(conn, date(2026,3,20))

注意:
- ai モジュールは OPENAI_API_KEY を要求します（引数 api_key でも指定可能）。
- ETL / news / regime 等の関数はルックアヘッドバイアスを避けるため target_date を明示的に受け取ります。date.today() を内部で参照しない設計です。

---

## ディレクトリ構成（主要ファイルと簡単な説明）

src/kabusys/
- __init__.py
  - パッケージのエクスポート（data, strategy, execution, monitoring 等を公開予定）
- config.py
  - 環境変数ロード・Settings（設定）クラス
- ai/
  - __init__.py
  - news_nlp.py : ニュースのセンチメント解析・ai_scores への書込み（score_news）
  - regime_detector.py : 市場レジーム判定（score_regime）
- data/
  - __init__.py
  - calendar_management.py : JPX カレンダー管理・営業日ロジック
  - etl.py : ETLResult の公開（エイリアス）
  - pipeline.py : 日次 ETL の実装（run_daily_etl 等）
  - stats.py : zscore_normalize 等汎用統計
  - quality.py : データ品質チェック（欠損・スパイク・重複・日付不整合）
  - audit.py : 監査ログ（signal / order / execution）スキーマ初期化
  - jquants_client.py : J-Quants API クライアント（取得・保存ロジック）
  - news_collector.py : RSS 収集・前処理・ID 正規化等
- research/
  - __init__.py
  - factor_research.py : Momentum/Value/Volatility 等のファクター計算
  - feature_exploration.py : forward returns / IC / factor summary / rank 等
- research や ai の補助モジュールは調査・開発用途のコードを含む

（プロジェクト全体には execution、monitoring、strategy などのサブパッケージが想定されますが、今回のスナップショットでは一部のみ実装されています。）

---

## 運用上の注意

- 環境変数や API キーは秘匿情報です。リポジトリにハードコーディングしないでください。
- OpenAI 呼び出しにはコストがかかります。バッチサイズやリトライポリシーを理解して運用してください。
- ETL / API 呼び出しはレート制限やネットワーク障害を考慮しており、内部でリトライ/バックオフを行いますが、運用側でも監視を設定してください。
- DuckDB の executemany に空配列を渡すとエラーになる点（pipeline 側で対策済み）など、DB のバージョン依存に注意してください。

---

必要であれば、CI 用の簡単なサンプルテスト、詳細な .env.example、requirements.txt、あるいは CLI スクリプト（etl_runner など）のテンプレートも作成します。どれを優先するか教えてください。