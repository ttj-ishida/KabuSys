# KabuSys — 日本株自動売買システム README (日本語)

概要
----
KabuSys は日本株向けのデータ基盤・リサーチ・AI 支援・監査ログ・ETL を包括するライブラリ群です。  
J-Quants API からのデータ取得、DuckDB によるデータ保存、ニュースの収集と LLM を使ったニュースセンチメント評価、ファクター計算、品質チェック、監査ログ（発注〜約定のトレース）などを提供します。  
設計上、ルックアヘッドバイアス回避・冪等性（idempotency）・堅牢なリトライ・API レート制御・セキュリティ（SSRF 対策）に配慮しています。

主な特徴
---------
- データ取得 & ETL
  - J-Quants API から株価（日次）、財務、マーケットカレンダー等を差分取得（ページネーション対応）
  - ETL パイプライン（差分取得、保存、品質チェック）を一括実行可能
  - rate limiting / 再試行 / id token 自動リフレッシュを内蔵
- ニュース収集 & NLP
  - RSS からニュースを収集し raw_news に保存（URL 正規化・トラッキング除去、SSRF 対策、受信サイズ制限）
  - OpenAI（gpt-4o-mini）を用いた銘柄別ニュースセンチメントスコアリング（ai_scores テーブルへ保存）
- 市場レジーム判定
  - ETF（1321）200 日移動平均乖離とマクロニュース LLM スコアを合成して日次でレジーム(bull/neutral/bear) を判定
- 研究用ユーティリティ
  - モメンタム、ボラティリティ、バリュー等のファクター計算
  - 将来リターン計算、IC（情報係数）、ファクター統計サマリ
  - Zスコア正規化などの統計ユーティリティ
- データ品質チェック
  - 欠損・スパイク・重複・日付不整合の検出
  - QualityIssue オブジェクトで問題を集約
- 監査ログ（トレーサビリティ）
  - シグナル → 発注要求 → 約定 の階層的トレース用テーブル群（冪等キー・UTC タイムスタンプ）
  - init_audit_db で監査専用 DuckDB を初期化可能
- 設計ポリシー（抜粋）
  - ルックアヘッドバイアス回避（内部で date.today() 等に依存しない設計の関数多数）
  - DuckDB を中心としたローカル DB ストレージ（デフォルト data/kabusys.duckdb）
  - 冪等処理（ON CONFLICT / DELETE → INSERT）を重視

必要条件
--------
- Python 3.10+
- 主な依存候補（プロジェクトに requirements.txt がある前提で調整してください）
  - duckdb
  - openai (OpenAI Python SDK)
  - defusedxml
  - （ネットワークアクセス）
- J-Quants API と OpenAI API のアクセス権（トークン）

セットアップ手順
----------------
1. リポジトリをクローンしてインストール
   - 例:
     - git clone <repo>
     - python -m venv .venv
     - source .venv/bin/activate
     - pip install -e .    （プロジェクトがパッケージ化されている場合）
     - または pip install duckdb openai defusedxml など必要パッケージをインストール

2. 環境変数 / .env の準備
   - ルートに .env または .env.local を置くと自動読み込みされます（プロジェクトルートは .git または pyproject.toml を基準に探索）。
   - 自動ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。
   - 必須環境変数（主なもの）:
     - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（必須）
     - KABU_API_PASSWORD — kabuステーション API パスワード（必須）
     - SLACK_BOT_TOKEN — Slack 通知に用いる Bot Token（必須）
     - SLACK_CHANNEL_ID — Slack チャンネル ID（必須）
     - OPENAI_API_KEY — OpenAI API キー（score_news / regime_detector で使用）
   - 任意 / デフォルト:
     - KABUSYS_ENV — development / paper_trading / live（デフォルト development）
     - LOG_LEVEL — DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト INFO）
     - DUCKDB_PATH — デフォルト data/kabusys.duckdb
     - SQLITE_PATH — 監視用 SQLite（デフォルト data/monitoring.db）
   - .env の例:
     - JQUANTS_REFRESH_TOKEN="xxxxx"
     - OPENAI_API_KEY="sk-..."
     - KABU_API_PASSWORD="password"
     - SLACK_BOT_TOKEN="xoxb-..."
     - SLACK_CHANNEL_ID="C01234567"

3. データディレクトリ作成
   - デフォルトでは data/ 配下に DuckDB / SQLite を配置します。存在しない場合は作成してください。
     - mkdir -p data

使い方（利用例）
----------------

- DuckDB 接続の作成（例）
  - Python REPL / スクリプト内:
    - import duckdb
    - conn = duckdb.connect("data/kabusys.duckdb")

- 日次 ETL 実行
  - run_daily_etl を使って市場カレンダー・株価・財務を差分取得し保存、品質チェックまで実行します。
  - 例:
    - from kabusys.data.pipeline import run_daily_etl
      from datetime import date
      import duckdb
      conn = duckdb.connect("data/kabusys.duckdb")
      result = run_daily_etl(conn, target_date=date(2026,3,20))
      print(result.to_dict())

- ニュースのスコアリング（AI）
  - OpenAI API キー（環境変数 OPENAI_API_KEY）が必要です。
  - 例:
    - from kabusys.ai.news_nlp import score_news
      from datetime import date
      import duckdb
      conn = duckdb.connect("data/kabusys.duckdb")
      count = score_news(conn, target_date=date(2026,3,20))
      print(f"scored {count} codes")

- 市場レジーム判定
  - ETF (1321) の MA200 とマクロニュース LLM スコアを合成してレジームを書き込みます（market_regime テーブル）。
  - 例:
    - from kabusys.ai.regime_detector import score_regime
      from datetime import date
      import duckdb
      conn = duckdb.connect("data/kabusys.duckdb")
      score_regime(conn, target_date=date(2026,3,20))

- 監査ログ DB 初期化
  - 監査用テーブル群（signal_events / order_requests / executions）を作成します。
  - 例:
    - from kabusys.data.audit import init_audit_db
      conn = init_audit_db("data/audit.duckdb")
      # conn は初期化済みの DuckDB 接続

- ファクター計算 / 研究用ユーティリティ
  - 例: モメンタム計算
    - from kabusys.research.factor_research import calc_momentum
      conn = duckdb.connect("data/kabusys.duckdb")
      res = calc_momentum(conn, target_date=date(2026,3,20))

運用上のポイント / 設計上の注意
------------------------------
- ルックアヘッドバイアス防止:
  - 多くの関数は target_date を引数に取り、内部で現在時刻を勝手に参照しません。バックテスト用途では過去データだけで動作するよう設計されています。
- 冪等性:
  - ETL 保存処理は ON CONFLICT DO UPDATE や DELETE→INSERT を用いて冪等性を確保します。
- API 呼び出しの堅牢性:
  - J-Quants クライアント・OpenAI 呼び出しともにリトライ／バックオフ・レート制御を組み込んでいます。失敗時は（致命的でなければ）フェイルセーフで続行する設計箇所が多いです。
- セキュリティ:
  - RSS の取得では SSRF 対策（リダイレクト検査・ホストのプライベートアドレス判定）や XML 疑似攻撃対策（defusedxml）を実装しています。

ディレクトリ構成（主なファイル）
-------------------------------
（src/kabusys 以下を抜粋）

- kabusys/
  - __init__.py
  - config.py
    - 環境変数 / 自動 .env 読み込み / Settings クラス
  - ai/
    - __init__.py
    - news_nlp.py        — ニュースを LLM でスコアリングし ai_scores に書き込む
    - regime_detector.py — ETF MA とニュースで市場レジームを判定
  - data/
    - __init__.py
    - jquants_client.py  — J-Quants API クライアント（fetch / save）
    - pipeline.py        — ETL パイプライン実装（run_daily_etl 等）
    - etl.py             — ETLResult のエクスポート
    - news_collector.py  — RSS 収集（SSRF 対策・正規化）
    - calendar_management.py — 市場カレンダー管理（営業日判定など）
    - quality.py         — データ品質チェック
    - stats.py           — 統計ユーティリティ（zscore_normalize）
    - audit.py           — 監査ログテーブル初期化 / DB ヘルパ
  - research/
    - __init__.py
    - factor_research.py — モメンタム / バリュー / ボラティリティ等の計算
    - feature_exploration.py — 将来リターン計算 / IC / 各種統計
  - research/*, ai/*, data/* はそれぞれ上記機能を提供

貢献・テスト
-------------
- テストは各モジュールの設計に合わせてユニットテストを書くことを推奨します。OpenAI / ネットワーク呼び出し部分はモック化してテストしてください（ソース内に unittest.mock.patch で差し替えるコメントあり）。
- 自動 .env ロードの影響を避けたいテストでは KABUSYS_DISABLE_AUTO_ENV_LOAD を設定して無効化できます。

ライセンス / コード品質
---------------------
- リポジトリのルートに LICENSE がある想定で扱ってください。  
- ロギングは各モジュールで logger を使用。運用時はログレベル設定（LOG_LEVEL）やハンドラの設定を行ってください。

補足
----
この README はコードベースから抽出した設計・利用方法の概要です。実行時の詳細な引数や挙動は各モジュールの docstring を参照してください（例: kabusys/data/pipeline.py, kabusys/ai/news_nlp.py 等）。README の内容はプロジェクトの実装に応じて随時更新してください。