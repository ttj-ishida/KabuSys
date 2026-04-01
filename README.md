KabuSys
=======

概要
----
KabuSys は日本株向けのデータプラットフォームおよび自動売買支援ライブラリです。  
J-Quants API を用いたデータ ETL、ニュースの NLP スコアリング（OpenAI）、市場レジーム判定、ファクター計算、データ品質チェック、監査ログなど運用に必要な主要機能を提供します。

主な用途の例:
- 日次 ETL（株価・財務・マーケットカレンダー）の自動収集と保存
- ニュース記事のセンチメント評価（銘柄ごとの ai_score 作成）
- マクロ＋テクニカルを使った市場レジーム判定（bull / neutral / bear）
- ファクター（モメンタム・バリュー・ボラティリティ）計算と研究用ユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付整合性）
- 発注フローの監査ログ（audit スキーマ）初期化

機能一覧
--------
- データ収集 / ETL
  - J-Quants API から株価（日足）、財務、上場情報、マーケットカレンダーを差分取得・保存（DuckDB）
  - 差分更新・ページネーション対応・レート制御・トークン自動リフレッシュ
- ニュース収集 / NLP
  - RSS から記事収集（SSRF 対策・トラッキング除去・前処理）
  - OpenAI（gpt-4o-mini）を用いた銘柄別センチメントスコアリング（JSON Mode）
  - マクロニュースの LLM 評価による市場レジーム判定機能
- 研究（Research）
  - モメンタム、ボラティリティ、バリューなどのファクター計算
  - 将来リターン、IC（Information Coefficient）、統計サマリー、Zスコア正規化
- データ品質チェック
  - 欠損・スパイク・重複・日付不整合検出（QualityIssue）
- 監査（Audit）
  - シグナル→発注→約定までの監査テーブル定義と初期化ユーティリティ
- 設定管理
  - .env / 環境変数の自動ロード（プロジェクトルート検出）と Settings API

前提 / 必要環境
---------------
- Python 3.10+
- DuckDB（Python パッケージ）
- OpenAI Python SDK（OpenAI API を利用する機能を使う場合）
- defusedxml（RSS パースの安全化）
- 追加の標準ライブラリ（urllib, json 等）

インストール（開発）
------------------
1. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 必要パッケージをインストール
   - pip install -r requirements.txt
   （プロジェクトに requirements.txt が無ければ主に次を入れてください）
   - pip install duckdb openai defusedxml

3. パッケージを editable インストール（任意）
   - pip install -e .

環境変数
--------
KabuSys は .env ファイル（プロジェクトルート）または OS 環境変数を参照します。自動読み込みはデフォルトで有効です（無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。

主な必須環境変数:
- JQUANTS_REFRESH_TOKEN : J-Quants API のリフレッシュトークン
- OPENAI_API_KEY        : OpenAI API キー（news_nlp / regime_detector 使用時）
- KABU_API_PASSWORD     : kabu ステーション API パスワード（実行・発注関連）
- SLACK_BOT_TOKEN       : Slack 通知用 Bot トークン（通知機能を使う場合）
- SLACK_CHANNEL_ID      : Slack チャネル ID

任意 / デフォルト設定:
- KABUSYS_ENV (development|paper_trading|live) — デフォルト development
- LOG_LEVEL (DEBUG|INFO|...) — デフォルト INFO
- DUCKDB_PATH — デフォルト data/kabusys.duckdb
- SQLITE_PATH — デフォルト data/monitoring.db
- PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT など監視設定

参考: config.Settings からプログラム的にアクセスできます。
例:
from kabusys.config import settings
print(settings.duckdb_path)

セットアップ手順（例）
--------------------
1. .env を作る（プロジェクトルートに .env / .env.local）
   - .env.example を参考に必要なキーを設定してください。

2. データベース（DuckDB）用ディレクトリを準備
   - settings.duckdb_path の親ディレクトリが無ければ作成してください（多くの初期化関数は自動作成しますが明示しておくと安心です）。

3. 監査スキーマの初期化（必要な場合）
   - from kabusys.data.audit import init_audit_db
     conn = init_audit_db(settings.duckdb_path)
   - これにより監査テーブル群が作成されます。

使い方（主要 API）
-----------------

1) 日次 ETL を実行する
- ETL のエントリポイントは run_daily_etl（kabusys.data.pipeline）です。
- DuckDB 接続を作成して呼び出します。

例:
from datetime import date
import duckdb
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026,3,20))
print(result.to_dict())

2) ニュースのスコアリング（銘柄別 ai_scores 書き込み）
- news_nlp.score_news を使用します（OpenAI API キー必須）

例:
from datetime import date
import duckdb
from kabusys.config import settings
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect(str(settings.duckdb_path))
n_written = score_news(conn, target_date=date(2026,3,20))
print(f"書込銘柄数: {n_written}")

- api_key を関数に直接渡すこともできます（テストやキー分離に便利）。
  score_news(conn, date(2026,3,20), api_key="sk-...")

3) 市場レジーム判定
- kabusys.ai.regime_detector.score_regime を使用すると market_regime テーブルに結果を書き込みます。

例:
from datetime import date
from kabusys.ai.regime_detector import score_regime
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026,3,20))

4) 監査スキーマ初期化
- kabusys.data.audit.init_audit_db を使い監査用 DB を初期化できます（別 DB ファイルでも可）。

例:
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")  # 親ディレクトリは自動作成

5) 研究用ユーティリティ
- ファクター計算等は kabusys.research 以下を参照
  - calc_momentum, calc_volatility, calc_value
  - calc_forward_returns, calc_ic, factor_summary, rank
- データ正規化: kabusys.data.stats.zscore_normalize

ディレクトリ構成（抜粋）
----------------------
src/kabusys/
- __init__.py
- config.py                       -- 環境変数 / 設定管理
- ai/
  - __init__.py
  - news_nlp.py                    -- ニュース NLP（銘柄別スコア）
  - regime_detector.py             -- 市場レジーム判定
- data/
  - __init__.py
  - jquants_client.py              -- J-Quants API クライアント（fetch / save）
  - pipeline.py                    -- ETL パイプライン（run_daily_etl 他）
  - etl.py                         -- ETLResult 等の公開インターフェース
  - news_collector.py              -- RSS 収集
  - calendar_management.py         -- マーケットカレンダー管理
  - quality.py                     -- データ品質チェック
  - stats.py                       -- 統計ユーティリティ（zscore）
  - audit.py                       -- 監査スキーマ初期化
- research/
  - __init__.py
  - factor_research.py             -- Momentum/Value/Volatility 計算
  - feature_exploration.py         -- 将来リターン / IC / summary
- monitoring/ (未表示ファイル群)
- strategy/ (未表示ファイル群)
- execution/ (未表示ファイル群)

（上記はコードベースの主要ファイルのみ抜粋）

設計上の注意点 / トラブルシュート
---------------------------------
- Look-ahead bias 回避: 多くの関数は target_date を明示的に受け取り、内部で date.today() を直接参照しない設計です。バックテスト・過去検証時は target_date を明確に与えてください。
- OpenAI / J-Quants API キーが未設定だと該当機能は ValueError を出します。テスト時は api_key 引数で注入できます。
- .env 自動ロード: プロジェクトルートは .git または pyproject.toml を基準に検出します。自動ロードを抑制したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を 1 にしてください。
- ニュース収集は外部ネットワークおよび RSS のフォーマットに依存します。SSRF 対策や最大受信サイズチェックを実装済みですが、外部ソースの信頼性には注意してください。
- DuckDB への executemany の仕様に依存する箇所があるため（空リストの扱いなど）、空データを渡さないように注意してください。

開発・テスト時のヒント
--------------------
- OpenAI 呼び出しは内部で専用関数をラップしているため、ユニットテストではそれらの内部ヘルパー（_call_openai_api 等）を patch して外部 API を呼ばないように差し替えられます。
- J-Quants API 呼び出しも _request を中心に実装されているため、HTTP 呼び出しをモックして ETL ロジックをテストできます。
- DuckDB はインメモリ(":memory:") での接続も可能なので、テスト用 DB として便利です。

ライセンス / 貢献
----------------
（このリポジトリにライセンス表記がある場合は追記してください。）

問い合わせ
----------
使い方や不具合報告はリポジトリの Issues またはプロジェクトのドキュメントを参照してください。

--- 

必要であれば README に実際の .env.example のサンプルやよくある実行コマンド（cron / systemd / Docker の例）を追記できます。どの部分を詳しく追加しますか？