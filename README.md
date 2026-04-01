# KabuSys

日本株向けのデータプラットフォーム & 自動売買補助ライブラリ。  
DuckDB をデータ層に、J-Quants / OpenAI / kabuステーション 等と連携して、データ取得（ETL）、品質チェック、ニュースNLP、マーケットレジーム判定、監査ログ（発注トレーサビリティ）などを提供します。

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 主な機能
- 前提条件 / 依存関係
- セットアップ手順
- 環境変数（.env）サンプル
- 基本的な使い方
  - 日次 ETL 実行例
  - ニュースセンチメントスコア取得例
  - 市場レジーム判定例
  - 監査DB初期化例
- 主要モジュールとディレクトリ構成

---

プロジェクト概要
----------------
KabuSys は日本株データ基盤および研究 / 自動売買補助のための Python パッケージです。  
主に以下を目的としています。

- J-Quants API からの日足・財務・カレンダー等の差分 ETL と DuckDB への保存（冪等）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- ニュースの収集・前処理と OpenAI を使った銘柄別ニュースセンチメント評価
- マーケットレジーム判定（ETF + マクロニュースの合成）
- リサーチ向けファクター計算・特徴量解析ユーティリティ
- 監査ログ（signal → order_request → execution のトレーサビリティ）用スキーマと初期化ユーティリティ

主な機能
--------
- ETL: run_daily_etl による市場カレンダー / 日足 / 財務の差分取得と品質チェック
- J-Quants クライアント: レートリミット・リトライ・トークン自動更新対応
- ニュース収集: RSS 取得の保護（SSRF/サイズ制限/トラッキング除去）と raw_news への冪等保存（設計済）
- ニュース NLP: OpenAI（gpt-4o-mini）を使った銘柄単位センチメント評価（chunk/batch処理、リトライ）
- レジーム判定: ETF 1321 の 200 日 MA 乖離とマクロニュースの LLM スコアの重み合成
- 研究用: モメンタム / ボラティリティ / バリュー等のファクター算出、前方リターン、IC、サマリー
- データ品質チェック: 欠損、スパイク、重複、日付不整合の検出
- 監査ログ: 発注・約定を追跡するスキーマと DB 初期化ユーティリティ

前提条件 / 依存関係
-------------------
- Python 3.10+（ソースでの型ヒント（| union）を使用）
- 主要依存ライブラリ（一例）:
  - duckdb
  - openai (OpenAI の Python SDK、または互換クライアント)
  - defusedxml
  - その他標準ライブラリ（urllib, json, logging 等）
- ネットワークアクセス:
  - J-Quants API（認証トークンが必要）
  - OpenAI API（OpenAI API キーが必要）
  - RSS フィードへアクセス可能であること

セットアップ手順
----------------

1. リポジトリをクローン（またはパッケージを取り込み）
   - 例: git clone <repo-url>

2. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Unix/macOS)
   - .venv\Scripts\activate     (Windows)

3. パッケージと依存をインストール
   - pip install -e .            # ローカル開発インストール
   - pip install duckdb openai defusedxml

   （プロジェクトに requirements/dev.txt があればそれに従ってください）

4. 環境変数設定（.env ファイルをプロジェクトルートに置くと自動読み込みされます）
   - 自動ロードはデフォルトで有効（環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）
   - 必須環境変数は下記参照

5. DuckDB 用ディレクトリを作成（必要に応じて）
   - デフォルトでは data/kabusys.duckdb（settings.duckdb_path）

環境変数（.env）サンプル
------------------------
以下は主要な環境変数の一覧（必要に応じて .env に記載）。README の目的上の例です。

必須:
- JQUANTS_REFRESH_TOKEN=<your_jquants_refresh_token>
- OPENAI_API_KEY=<your_openai_api_key>
- SLACK_BOT_TOKEN=<your_slack_bot_token>
- SLACK_CHANNEL_ID=<your_slack_channel_id>
- KABU_API_PASSWORD=<kabu_station_api_password>

オプション / デフォルトあり:
- KABUSYS_ENV=development    # development | paper_trading | live
- LOG_LEVEL=INFO
- DUCKDB_PATH=data/kabusys.duckdb
- SQLITE_PATH=data/monitoring.db
- PID_FILE_PATH=data/execution.pid
- CPU_THRESHOLD_PCT=90.0
- MEMORY_THRESHOLD_PCT=85.0
- DISK_THRESHOLD_PCT=90.0
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1  # 自動 .env ロード無効化

例 (.env):
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxx
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxx
SLACK_BOT_TOKEN=xoxb-xxxxxxxxxxxx
SLACK_CHANNEL_ID=C0123456789
KABU_API_PASSWORD=your_password
KABUSYS_ENV=development
LOG_LEVEL=DEBUG

基本的な使い方
--------------

Python スクリプトや REPL から直接利用できます。以下は代表的な利用例です。

- DuckDB 接続例:
  from pathlib import Path
  import duckdb
  conn = duckdb.connect(str(Path("data/kabusys.duckdb")))

- 日次 ETL 実行（市場カレンダー / 日足 / 財務 / 品質チェック）
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl
  result = run_daily_etl(conn, target_date=date(2026,3,20))
  print(result.to_dict())

- ニュースセンチメントのスコア取得
  from datetime import date
  from kabusys.ai.news_nlp import score_news
  # OpenAI API キーは環境変数 OPENAI_API_KEY に設定するか、api_key 引数で渡す
  n_written = score_news(conn, target_date=date(2026,3,20))
  print(f"scored stocks: {n_written}")

- マーケットレジーム判定（1321 の MA200 とマクロニュースを合成）
  from kabusys.ai.regime_detector import score_regime
  score_regime(conn, target_date=date(2026,3,20))

- 監査DB の初期化（監査用 DuckDB を別 DB ファイルで用意）
  from kabusys.data.audit import init_audit_db
  audit_conn = init_audit_db("data/audit.duckdb")
  # 以降、order_events 等の監査テーブルが使用可能

- 研究向けファクター計算
  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
  mom = calc_momentum(conn, date(2026,3,20))

注意点 / 実運用の考慮
- OpenAI / J-Quants の API 呼び出しは課金やレートリミットに注意してください。
- ETL / API 呼び出し部分はリトライ・レート制御を実装していますが、運用環境での監視（ログ、アラート）を推奨します。
- Look-ahead バイアス対策がコード全体に組み込まれています（内部で date.today() を無条件に使用しない等）。バックテスト用途ではデータの取り扱い（取得日時・fetched_at）に注意してください。
- DuckDB executemany に関する互換性（空リスト渡せない等）にも配慮しています。

ディレクトリ構成（主要ファイル）
-------------------------------
以下はパッケージ src/kabusys の主要ファイル群（抜粋）です。README に含まれているコードベースに基づく構成を示します。

- src/kabusys/
  - __init__.py                       (パッケージ定義, __version__ = "0.1.0")
  - config.py                         (環境変数 / .env ローダー / Settings)
  - ai/
    - __init__.py
    - news_nlp.py                      (ニュースセンチメントの集約・OpenAI 呼び出し)
    - regime_detector.py               (市場レジーム判定)
  - data/
    - __init__.py
    - pipeline.py                      (ETL パイプライン run_daily_etl 等)
    - etl.py                           (ETL インターフェースエクスポート)
    - jquants_client.py                (J-Quants API クライアント + 保存ロジック)
    - news_collector.py                (RSS 収集・前処理・SSRF対策)
    - calendar_management.py           (マーケットカレンダー管理・営業日判定)
    - stats.py                         (zscore 正規化ユーティリティ)
    - quality.py                       (データ品質チェック)
    - audit.py                         (監査ログスキーマ初期化)
  - research/
    - __init__.py
    - factor_research.py               (モメンタム/ボラティリティ/バリュー)
    - feature_exploration.py           (forward returns, IC, factor summary)
  - ai/ (上記)
  - その他ユーティリティ群（logging, エラー処理等）

ファイル群の設計方針（概要）
-------------------------
- 冪等性: DB への保存は ON CONFLICT / DELETE+INSERT 等で冪等に設計
- フェイルセーフ: API 失敗時は例外を投げすぎず（必要箇所は再試行／フォールバック）処理継続を優先
- Look-ahead バイアス防止: 取得ウィンドウや DB クエリは target_date 未満・以前のみ参照することを基本とする
- テスト容易性: OpenAI やネットワークアクセス部は差し替え可能な設計（モックが可能）

ライセンス / 貢献
----------------
（この README ではライセンス情報は省略されています。実際のリポジトリでは LICENSE を記載してください。）  
バグ報告・プルリクエストは GitHub 上で受け付けてください。

---

問い合わせ・補足
----------------
具体的な実行方法（systemd ジョブ化、スケジューリング、Slack 通知連携、kabuステーションの発注連携等）は運用要件により異なります。必要であれば運用手順（デプロイ手順、cron/systemd サービス定義、ロギング設定、監視設計）についても README を拡張できます。必要な場合は用途を教えてください。