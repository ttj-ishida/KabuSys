# KabuSys

KabuSys は日本株のデータプラットフォームと自動売買（研究・シグナル生成・監査・発注）を支える内部ライブラリ群です。本リポジトリはデータ取得（J-Quants）、ETL、ニュース収集・NLP（OpenAI を利用したセンチメント解析）、リサーチ用ファクター計算、監査ログ（約定トレーサビリティ）などの主要機能を提供します。

注意: この README はコードベース（src/kabusys 以下）から抽出した設計方針・使い方をまとめたものです。実運用では API キーの管理・実際の発注ロジック等に十分注意してください。

---

目次
- プロジェクト概要
- 主な機能一覧
- 必須環境変数（.env）
- セットアップ手順
- 使い方（主要 API の例）
- ディレクトリ構成（概要）
- 補足・設計上の注意点

---

プロジェクト概要
- 日本株向けのデータ取得・品質管理・研究・NLP・監査ログを包括するライブラリ群。
- データ取得は J-Quants API を利用（rate-limit とリトライ制御付き）。
- ニュースは RSS で収集し、OpenAI（gpt-4o-mini 等）で銘柄ごとのセンチメントやマーケットレジームを評価。
- すべての ETL / 保存処理は冪等を意識して実装（DuckDB に ON CONFLICT 相当の更新を行う）。
- バックテストでのルックアヘッドバイアスを意識した設計（datetime.today() を直接参照しない等）。

---

主な機能一覧
- data:
  - jquants_client: J-Quants API からの日足・財務・カレンダー取得と DuckDB への保存（冪等）
  - pipeline / etl: 日次 ETL パイプライン（差分取得・バックフィル・品質チェック）
  - news_collector: RSS 収集・前処理・SSRF 対策・raw_news 保存
  - quality: データ品質チェック（欠損・スパイク・重複・日付不整合）
  - calendar_management: JPX カレンダー管理・営業日判定
  - audit: 監査ログ（signal_events / order_requests / executions）スキーマ作成と初期化
  - stats: 汎用統計ユーティリティ（Z スコア正規化など）
- ai:
  - news_nlp.score_news: 銘柄ごとのニュースセンチメントを OpenAI でスコア化して ai_scores に保存
  - regime_detector.score_regime: ETF（1321）の MA200 とマクロニュース（LLM）を合成して市場レジームを判定・保存
- research:
  - factor_research: momentum / value / volatility 等のファクター算出
  - feature_exploration: 将来リターン計算、IC（Spearman）計算、統計サマリー、ランク化ユーティリティ
- 設定:
  - config.Settings: 環境変数読み込み（.env 自動ロード機能を備える）

---

必須環境変数（主要）
config.Settings と各モジュールから参照される主な環境変数の一覧（.env または OS 環境で設定）:

必須:
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（データ取得に必須）
- KABU_API_PASSWORD: kabuステーション API のパスワード（発注等に利用）
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID: Slack 通知チャンネル ID
- OPENAI_API_KEY: OpenAI API を利用する場合に必須（ai.score_news / regime_detector 等）

任意（デフォルトあり）:
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL（デフォルト: INFO）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite（モニタリング用）パス（デフォルト: data/monitoring.db）
- PID_FILE_PATH: 実行監視用 PID ファイルパス（デフォルト: data/execution.pid）
- CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT: 監視閾値
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると src/kabusys/config.py による .env 自動読込を抑止できます（テスト時に有用）。

サンプル .env（最小）
```
JQUANTS_REFRESH_TOKEN=xxx
OPENAI_API_KEY=sk-xxx
KABU_API_PASSWORD=your_kabu_pass
SLACK_BOT_TOKEN=xoxb-xxx
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
```

---

セットアップ手順（開発環境想定）
前提: Python 3.10 以上を推奨（型ヒントに PEP 604 union 型を利用）

1. リポジトリをクローン
   - git clone <repo-url>

2. 仮想環境を作成・有効化（例: venv）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - 主要依存（コードベースから必要になるもの）:
     - duckdb
     - openai
     - defusedxml
   - 例:
     - pip install duckdb openai defusedxml

   （プロジェクトが pyproject.toml / requirements.txt を持つ場合はそちらを使ってください）

4. 環境変数を設定
   - リポジトリルートに .env を作成するか、CI / 実行環境で環境変数を設定してください。
   - 自動ロード機能は .git または pyproject.toml をプロジェクトルートとして探索し、.env / .env.local を読み込みます。

5. 初期 DB 構造（監査ログなど）を準備
   - 監査専用 DB を初期化する例:
     ```python
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")
     # conn を使ってさらに操作可能
     ```

---

使い方（主要 API の例）

- 日次 ETL を実行する（データ取得・品質チェック含む）
  ```python
  from datetime import date
  import duckdb
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースのセンチメントスコアを生成する（OpenAI API キーが必要）
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  n_written = score_news(conn, target_date=date(2026, 3, 20))
  print("書き込み銘柄数:", n_written)
  ```

- 市場レジーム判定（ETF 1321 の MA200 とマクロニュースの合成）
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- ファクター計算（リサーチ）
  ```python
  from datetime import date
  import duckdb
  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

  conn = duckdb.connect("data/kabusys.duckdb")
  mom = calc_momentum(conn, date(2026, 3, 20))
  val = calc_value(conn, date(2026, 3, 20))
  vol = calc_volatility(conn, date(2026, 3, 20))
  ```

- 監査スキーマを追加する（既存接続に対して）
  ```python
  from kabusys.data.audit import init_audit_schema
  import duckdb

  conn = duckdb.connect("data/kabusys.duckdb")
  init_audit_schema(conn, transactional=True)
  ```

設計上の便利なポイント
- OpenAI 呼び出しは内部でリトライ・エラーハンドリングを実装しているため、API の一時障害に対する耐性があります。テスト時は _call_openai_api をモックして挙動を差し替え可能です。
- J-Quants クライアントは内部でトークンキャッシュとレートリミッタを持っています。ID トークンの自動リフレッシュ（401）にも対応します。
- ETL は差分更新・バックフィルをサポートし、品質チェック（quality.run_all_checks）を実行して問題を収集します。
- ニュース収集（news_collector）は SSRF 対策、トラッキングパラメータ除去、受信サイズ制限といった安全対策を実装しています。

---

ディレクトリ構成（src/kabusys の主要ファイル）
- __init__.py
- config.py
  - 環境変数と自動 .env 読み込み、Settings クラス
- ai/
  - __init__.py
  - news_nlp.py: ニュースを銘柄ごとに集約し OpenAI でセンチメントを算出して ai_scores に保存
  - regime_detector.py: ETF 1321 の MA200 とマクロニュースを組み合わせて market_regime に書き込み
- data/
  - __init__.py
  - jquants_client.py: J-Quants API クライアント（取得 + DuckDB 保存）
  - pipeline.py: ETL の主要実装（run_daily_etl 他）
  - etl.py: ETLResult のエクスポート
  - calendar_management.py: 市場カレンダー管理と営業日判定ユーティリティ
  - news_collector.py: RSS 取得と raw_news への保存ロジック（SSRF 対策等）
  - quality.py: 品質チェック（欠損・スパイク・重複・日付整合性）
  - stats.py: zscore_normalize 等の統計ユーティリティ
  - audit.py: 監査ログスキーマ（signal_events / order_requests / executions）と初期化関数
- research/
  - __init__.py
  - factor_research.py: モメンタム・ボラティリティ・バリュー等のファクター計算
  - feature_exploration.py: 将来リターン / IC / 統計サマリー等

（上記に加え、実運用では execution（ブローカー接続）・strategy・monitoring 等のモジュールが存在する想定ですが、README に記載のコードベース側を優先しています）

---

補足・注意点
- セキュリティ:
  - API キーは .env に平文で置かないか適切にアクセス制限してください。
  - news_collector は SSRF 対策や受信制限を実装していますが、運用環境での追加制約（プロキシ・ファイアウォール等）が必要な場合があります。
- テスト:
  - 自動 .env ロードはテスト時に副作用を与える可能性があるため、KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して無効化できます。
  - OpenAI 呼び出しや外部 HTTP 呼び出しはモック化が可能な設計です（モジュール内 _call_openai_api や _urlopen 等を patch）。
- ルックアヘッドバイアス対策:
  - AI モジュールや ETL はバックテストでのルックアヘッドバイアスを避ける設計になっています（target_date 未満/以前のデータのみ利用する等）。

---

問題・改善案・拡張
- 発注実装（kabu ステーションとの実際の注文送信ロジック）や Slack 通知、監視ジョブの CLI スクリプトは本リポジトリの別モジュールや上位アプリケーション側で実装する想定です。
- テストカバレッジを高めるために、外部 API のモックテストケースを整備してください。

---

この README はコード内ドキュメンテーションから作成されています。さらに具体的な使い方（例: CI ジョブ、cron スケジュール、発注パイプライン）を追加したい場合は、必要なユースケースを教えてください。