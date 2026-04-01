# KabuSys

日本株向けの自動売買 / データパイプライン用ライブラリ。  
データ取得（J-Quants）、ETL、ニュースNLP（OpenAI）、市場レジーム判定、リサーチ用ファクター計算、監査ログ（DuckDB）などの主要機能を含むモジュール群を提供します。

主な設計方針：
- ルックアヘッドバイアスを避ける（内部で date.today()/datetime.today() に依存しない設計）
- DuckDB を用いたローカル永続化、ETL は差分＆冪等保存
- 外部API呼び出しはリトライ・バックオフ・レート制御を実装
- OpenAI を用いた JSON Mode による安定した NLP スコアリング
- 監査ログ（signal → order → execution）を完全トレース可能に設計

---

## 機能一覧

- データ収集 / ETL
  - J-Quants からの株価日足、財務、JPX カレンダー取得（差分更新、ページネーション対応、再試行）
  - ETL パイプライン（run_daily_etl）でカレンダー→株価→財務→品質チェックを実行
  - データ品質チェック（欠損、重複、スパイク、日付整合性）

- ニュース収集 / NLP
  - RSS からニュースを収集し raw_news に保存（SSRF対策、トラッキングパラメータ除去、前処理）
  - OpenAI（gpt-4o-mini）を使って銘柄ごとのセンチメントを ai_scores に書込む（score_news）

- 市場レジーム判定
  - ETF(1321) の 200 日 MA 乖離とマクロニュースセンチメントを合成して日次レジーム判定（score_regime）

- リサーチ（ファクター計算 / 特徴評価）
  - Momentum / Volatility / Value ファクター計算（prices_daily / raw_financials ベース）
  - 将来リターン計算、IC（Spearman）計算、統計サマリー、Zスコア正規化ユーティリティ

- 監査ログ（トレーサビリティ）
  - signal_events / order_requests / executions の監査テーブルと初期化ユーティリティ（init_audit_schema / init_audit_db）

- 設定管理
  - .env ファイル自動ロード（プロジェクトルート判定）と環境変数ラッパ（kabusys.config.settings）

---

## 必須設定 / 環境変数

主に以下を環境変数または .env に設定してください（READMEでは主要なものを抜粋）。

必須（未設定時はエラー）:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（ETL 用）
- SLACK_BOT_TOKEN — Slack 通知用（必要に応じて）
- SLACK_CHANNEL_ID — Slack チャンネル ID
- KABU_API_PASSWORD — kabuステーション API パスワード（発注周りを利用する場合）

OpenAI 関連（score_news / score_regime を使う場合）:
- OPENAI_API_KEY — OpenAI API キー（関数呼び出し時に引数で渡すことも可能）

オプション（デフォルト値あり）:
- KABUSYS_ENV — development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT など監視設定

自動 .env ロードの無効化（テスト等）:
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1

.env の読み込み順序:
- OS 環境 > .env.local > .env

---

## セットアップ手順

1. Python 環境の準備（推奨: venv）
   - python -m venv .venv
   - source .venv/bin/activate

2. 依存パッケージをインストール
   - requirements ファイルは本サンプルに含まれていませんが、主な依存は以下です:
     - duckdb
     - openai
     - defusedxml
   - 例: pip install duckdb openai defusedxml

   もしパッケージ化されている場合:
   - pip install -e .

3. 環境変数の設定
   - プロジェクトルートに .env（または .env.local）を作成して上記の必須変数を指定。
   - 例 (.env):
     JQUANTS_REFRESH_TOKEN=xxxx
     OPENAI_API_KEY=sk-xxxx
     SLACK_BOT_TOKEN=xoxb-xxx
     SLACK_CHANNEL_ID=CXXXXXXX

4. データディレクトリ作成（必要に応じて）
   - mkdir -p data

5. DuckDB スキーマ初期化（必要に応じて）
   - 監査DB を初期化する場合:
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/kabusys_audit.duckdb")

---

## 使い方（コード例）

以下は代表的な利用例。すべて Python から呼び出す形です。

- DuckDB 接続を作って日次 ETL を実行する
  from datetime import date
  import duckdb
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())

- ニュースセンチメントをスコアして ai_scores に書き込む
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  n = score_news(conn, target_date=date(2026, 3, 20))
  print(f"scored {n} codes")

  ※ OPENAI_API_KEY を環境変数に入れておくか、api_key 引数で渡せます:
  score_news(conn, date(2026,3,20), api_key="sk-...")

- 市場レジーム判定を実行する
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20))  # OpenAI APIキーは環境変数または引数で

- リサーチ用ファクター計算
  from datetime import date
  import duckdb
  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

  conn = duckdb.connect("data/kabusys.duckdb")
  mom = calc_momentum(conn, date(2026,3,20))
  vol = calc_volatility(conn, date(2026,3,20))
  val = calc_value(conn, date(2026,3,20))

- 監査スキーマ初期化（既存接続へ）
  from kabusys.data.audit import init_audit_schema
  import duckdb

  conn = duckdb.connect("data/kabusys.duckdb")
  init_audit_schema(conn, transactional=True)

テスト用：
- OpenAI 呼び出しをモックするために、kabusys.ai.news_nlp._call_openai_api や kabusys.ai.regime_detector._call_openai_api を unittest.mock.patch で差し替える設計になっています。

---

## ディレクトリ構成（主要ファイル）

（src/kabusys 以下の主要モジュール一覧）

- src/kabusys/
  - __init__.py
  - config.py          — 環境変数 / .env 読込と Settings
  - ai/
    - __init__.py
    - news_nlp.py      — ニュース NLP スコアリング（score_news）
    - regime_detector.py — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント（取得/保存）
    - pipeline.py      — ETL パイプライン（run_daily_etl, run_prices_etl 等）
    - etl.py           — ETL 結果データクラス再エクスポート
    - news_collector.py— RSS ニュース収集
    - calendar_management.py — 市場カレンダー管理・営業日ユーティリティ
    - quality.py       — データ品質チェック
    - stats.py         — 共通統計ユーティリティ（zscore_normalize）
    - audit.py         — 監査ログのDDL / 初期化
  - research/
    - __init__.py
    - factor_research.py — Momentum / Volatility / Value など
    - feature_exploration.py — 将来リターン / IC / 統計サマリー
  - research/ と data/ はリサーチ・データ処理向けユーティリティを分離

（上記は主要ファイルのみ抜粋。細部はソースツリーを参照してください）

---

## 実装上の注意 / ベストプラクティス

- ルックアヘッドバイアス防止:
  - 内部処理は target_date を明示的に受け取り、datetime.today() などの暗黙的現在時刻参照を避けています。バッチやバックテストで target_date を明示的に渡してください。

- 冪等性:
  - J-Quants データの保存は ON CONFLICT DO UPDATE により冪等に実装されています。ETL は差分取得＋バックフィルを行います。

- エラーハンドリング:
  - OpenAI / J-Quants 呼び出しはリトライ・エクスポネンシャルバックオフを実装。API エラー時はフェイルセーフ設計（必要に応じてスキップして続行）です。

- セキュリティ:
  - news_collector は SSRF 対策、XML 脆弱性対策（defusedxml）、レスポンスサイズ制限などの対策を実装しています。

---

必要であれば README に以下を追加できます：
- 具体的なスキーマ定義（テーブル DDL）
- テスト方法（ユニットテスト・モック例）
- CI/CD やデプロイ手順
- Slack 通知や実行スケジュール例（cron / systemd など）

ほかに追加したいセクションがあれば教えてください。