KabuSys — 日本株自動売買プラットフォーム
=====================================

概要
----
KabuSys は日本株向けのデータパイプライン、ファクター計算、AIを使ったニュース解析、監査ログ管理、ETL・品質チェック等を備えた自動売買プラットフォームの基盤ライブラリです。  
主に以下を目的としています。

- J-Quants API からの株価・財務・カレンダーデータ取得（差分取得・ページネーション対応・冪等保存）
- RSS ニュース収集と LLM を用いた銘柄・マクロセンチメント評価（OpenAI）
- 日次 ETL パイプラインとデータ品質チェック
- ファクター計算・特徴量探索（リサーチ用途）
- 発注・約定まで追跡可能な監査テーブル（DuckDB ベース）

主な特徴
--------
- データ取得（J-Quants）: レート制御・トークン自動更新・リトライ実装
- ETL: 差分更新、バックフィル、品質チェックを統合
- ニュース NLP: gpt-4o-mini を用いた銘柄ごとのセンチメントとマクロセンチメント（JSON mode）
- レジーム判定: ETF（1321）MA200 乖離とマクロセンチメントを合成して市場レジームを日次判定
- 監査ログ: signal → order_request → executions までトレース可能なスキーマを提供
- DuckDB を中心とした軽量ローカル DB 運用

セットアップ手順
----------------

前提
- Python 3.10+（型注釈で | を使用しているため 3.10 以上を推奨）
- ネットワークアクセス（J-Quants / OpenAI / RSS）

1. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール
   必要なパッケージ（抜粋）:
   - duckdb
   - openai
   - defusedxml
   - （標準ライブラリ以外があれば pyproject.toml / requirements.txt を参照）
   例:
   - pip install duckdb openai defusedxml

   （プロジェクトがパッケージ化されている場合）
   - pip install -e .

3. 環境変数設定
   プロジェクトルート（.git または pyproject.toml がある場所）に .env または .env.local を置くことで自動読み込みされます（起動時、自動で読み込まれます）。自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

   必須環境変数（例）:
   - JQUANTS_REFRESH_TOKEN: J-Quants の refresh token
   - KABU_API_PASSWORD: kabuステーション API パスワード
   - SLACK_BOT_TOKEN: Slack 通知用 Bot トークン
   - SLACK_CHANNEL_ID: Slack 通知先チャンネル ID
   - OPENAI_API_KEY: OpenAI API キー（score_news / score_regime 実行時に使用）

   任意（デフォルトあり）:
   - KABUSYS_ENV: development / paper_trading / live （デフォルト: development）
   - LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL
   - DUCKDB_PATH: デフォルト data/kabusys.duckdb
   - SQLITE_PATH: デフォルト data/monitoring.db

   サンプル .env（プロジェクトルート）:
   ```
   JQUANTS_REFRESH_TOKEN=xxxxx
   OPENAI_API_KEY=sk-xxxx
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-xxxx
   SLACK_CHANNEL_ID=C01234567
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   ```

使い方（簡易例）
----------------

以下は Python REPL / スクリプトでの利用例です。実行前に環境変数（特に OPENAI_API_KEY, JQUANTS_REFRESH_TOKEN）を設定してください。

1) DuckDB 接続を作成して日次 ETL を実行する
- 例:
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

2) ニュースの AI スコアリング（銘柄単位）
- score_news は raw_news / news_symbols / ai_scores テーブルを参照して書き込みます。OpenAI API キーが必要です。
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  written = score_news(conn, target_date=date(2026, 3, 20))  # OPENAI_API_KEY は env に設定
  print(f"書き込み銘柄数: {written}")
  ```

3) 市場レジーム判定
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20))
  # market_regime テーブルに結果が書き込まれます
  ```

4) ファクター計算・リサーチ関数（例: モメンタム）
  ```python
  from datetime import date
  import duckdb
  from kabusys.research.factor_research import calc_momentum

  conn = duckdb.connect("data/kabusys.duckdb")
  records = calc_momentum(conn, target_date=date(2026, 3, 20))
  print(len(records), records[:3])
  ```

5) 監査 DB 初期化（監査専用の DuckDB を作る）
  ```python
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  # 必要に応じて transactional=True でスキーマ初期化を行う関数も提供
  ```

注意点・運用上のポイント
- OpenAI 呼び出しはリトライ・フェイルセーフを実装していますが、API キーの制限やコストに注意してください。
- データ品質チェック（kabusys.data.quality.run_all_checks）は ETL の結果を検査します。重大な品質問題はログ・issues を通して検出できます。
- .env の自動読み込みはプロジェクトルート探索に依存します（.git または pyproject.toml がある親ディレクトリを基準）。テスト時や別環境では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して手動で環境を制御してください。
- news_collector.fetch_rss には SSRF 対策や受信バイト数制限、トラッキングパラメータ排除などの安全対策が入っています。RSS 取得→DB 保存のワークフローを作成する際はこれらの関数を利用してください。

ディレクトリ構成（主要ファイル）
------------------------------
以下は src/kabusys 以下の主要モジュールと役割の概観です。

- kabusys/
  - __init__.py               — パッケージ初期化（version 等）
  - config.py                 — 環境変数 / 設定管理（.env 自動読み込み、Settings）
  - ai/
    - __init__.py
    - news_nlp.py             — ニュースの LLM スコアリング（score_news）
    - regime_detector.py      — マクロ + MA200 を使った市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - calendar_management.py  — 市場カレンダー管理・営業日判定・更新ジョブ
    - pipeline.py             — ETL パイプライン（run_daily_etl 等）
    - etl.py                  — ETLResult の再エクスポート
    - jquants_client.py       — J-Quants API クライアント（fetch / save 関数）
    - news_collector.py       — RSS ニュース取得・前処理・挿入ユーティリティ
    - quality.py              — データ品質チェック（欠損・スパイク・重複・日付不整合）
    - stats.py                — zscore_normalize 等の統計ユーティリティ
    - audit.py                — 監査ログテーブル定義・初期化（signal/order/execution）
  - research/
    - __init__.py
    - factor_research.py      — Momentum/Volatility/Value 等の計算
    - feature_exploration.py  — 将来リターン、IC、統計サマリーなど

開発・テスト
-------------
- 自動環境読み込みを無効にしてユニットテストを行うには:
  - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- OpenAI / 外部 API 呼び出しを含む関数はモック可能（コード内にテスト用差し替えポイントを想定）。
- DuckDB はインメモリ(":memory:") でテスト可能（data.audit.init_audit_db 等がサポート）。

ライセンス・貢献
----------------
（このリポジトリにライセンスファイルが含まれている想定で追記してください。具体的なライセンスがない場合は運用ポリシーに従ってください。）

付録: よく使う環境変数一覧
-------------------------
- JQUANTS_REFRESH_TOKEN (必須)
- OPENAI_API_KEY (必須: news scoring / regime)
- KABU_API_PASSWORD (必須 / 発注関連)
- SLACK_BOT_TOKEN, SLACK_CHANNEL_ID (必須 / 通知)
- DUCKDB_PATH (デフォルト data/kabusys.duckdb)
- SQLITE_PATH (デフォルト data/monitoring.db)
- KABUSYS_ENV (development | paper_trading | live)
- LOG_LEVEL (INFO 等)
- KABUSYS_DISABLE_AUTO_ENV_LOAD (1 で .env 自動ロード無効)

---

README の要点は以上です。必要であれば、実行スクリプト例（systemd / cron / CI 向け）や詳細なテーブル定義（DDL）、運用ガイド（バックフィル運用方法、監査運用）を別途追記できます。どの箇所を詳しく書き足しましょうか？