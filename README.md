KabuSys
=======

概要
----
KabuSys は日本株向けのデータプラットフォームとリサーチ・自動売買支援ライブラリ群です。  
主に以下を提供します。

- J-Quants API からの差分 ETL（株価・財務・市場カレンダー）と品質チェック
- ニュース収集（RSS）と LLM によるニュースセンチメント（ai_score）生成
- 市場レジーム判定（ETF とマクロニュースの組合せ）
- ファクター計算・特徴量探索（モメンタム / バリュー / ボラティリティ 等）
- 発注・約定の監査ログ（監査テーブル初期化ユーティリティ）
- 各種ユーティリティ（カレンダー管理、統計関数、J-Quants クライアント等）

主な用途は、データ ETL・品質管理・リサーチ用の基盤処理および自動売買システムの基礎コンポーネント提供です。

機能一覧
--------
- data.jquants_client
  - J-Quants API から日足、財務、上場情報、マーケットカレンダーを取得・DuckDB に保存
  - 自動リトライ、レートリミット管理、トークンリフレッシュ対応
- data.pipeline / etl
  - 日次 ETL（run_daily_etl）でカレンダー → 株価 → 財務 → 品質チェックを順次実行
  - 差分取得、バックフィル対応、ETL 結果を ETLResult で返却
- data.quality
  - 欠損、重複、スパイク、日付不整合などデータ品質チェック
- data.news_collector
  - RSS フィード収集、前処理、SSRF 対策、raw_news / news_symbols への保存を想定
- data.calendar_management
  - market_calendar を用いた営業日判定、next/prev_trading_day 等のユーティリティ
- data.audit
  - 発注・約定の監査テーブル DDL と初期化（冪等）/ インデックス作成
- ai.news_nlp
  - ニュースを銘柄ごとに纏めて OpenAI（gpt-4o-mini）に送りセンチメントを取得し ai_scores に保存
- ai.regime_detector
  - ETF 1321 の 200 日 MA 乖離とマクロニュースの LLM センチメントを合成して market_regime を判定
- research.factor_research / feature_exploration
  - モメンタム、ボラティリティ、バリュー等のファクター計算
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー、ランク処理
- config
  - 環境変数 / .env 読み込み、各種設定値（トークン、DB パス、監視閾値、環境名など）の提供

必須環境変数（代表例）
----------------------
主に Settings で参照される環境変数（一部はデフォルトあり）:

- JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID — Slack 通知先チャンネル ID（必須）
- OPENAI_API_KEY — OpenAI（LLM）を使う場合に必要
- KABUSYS_ENV — "development" / "paper_trading" / "live"（デフォルト: development）
- LOG_LEVEL — "DEBUG" / "INFO" / ...（デフォルト: INFO）

.env の自動読み込み
- プロジェクトルート（.git または pyproject.toml があるディレクトリ）から .env と .env.local を自動で読み込みます。
  読み込み順序: OS 環境変数 > .env.local > .env
- 自動読み込みを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

セットアップ手順
--------------
前提:
- Python 3.10 以上（PEP 604 の型表記や union 型を利用）
- DuckDB（Python パッケージ）、openai、defusedxml などの依存ライブラリ

例: 仮想環境作成とインストール
1. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 必要パッケージをインストール
   - pip install duckdb openai defusedxml

   （プロジェクトに requirements.txt があれば:
    pip install -r requirements.txt）

3. パッケージを開発モードでインストール（オプション）
   - pip install -e .

4. 環境変数 / .env を準備
   - リポジトリルートに .env を作成（.env.example を参考に）
   - 例:
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     OPENAI_API_KEY=sk-...
     KABU_API_PASSWORD=your_kabu_password
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     DUCKDB_PATH=data/kabusys.duckdb

使い方（主要な利用例）
--------------------

1) 日次 ETL を実行する（Python スクリプト内で）
- run_daily_etl に DuckDB 接続を渡して実行します。

例:
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())

2) ニュースの NLP スコア付け
- ai.news_nlp.score_news(conn, target_date, api_key=None)
- api_key を渡さない場合は環境変数 OPENAI_API_KEY を利用

例:
from datetime import date
from kabusys.ai.news_nlp import score_news
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
n = score_news(conn, date(2026, 3, 20))
print(f"scored {n} codes")

3) 市場レジーム判定
- ai.regime_detector.score_regime(conn, target_date, api_key=None)

例:
from datetime import date
from kabusys.ai.regime_detector import score_regime
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, date(2026, 3, 20))

4) 研究用ファクター計算
- research.calc_momentum / calc_volatility / calc_value 等は DuckDB 接続と target_date を渡して結果リストを受け取ります

例:
from kabusys.research.factor_research import calc_momentum
from datetime import date
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
rows = calc_momentum(conn, date(2026, 3, 20))
print(len(rows), rows[:3])

5) 監査 DB の初期化
- data.audit.init_audit_db(db_path) で監査用 DuckDB を初期化して接続を取得できます

例:
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/monitoring_audit.duckdb")

注意点 / 実運用のヒント
- LLM 呼び出し（OpenAI）には API キーが必要です。API 呼び出しはリトライとフェイルセーフを備えていますが、コストやレートに注意してください。
- J-Quants API はレート制限があるため jquants_client は内部でスロットリングとリトライを行います。JQUANTS_REFRESH_TOKEN を必ず設定してください。
- データベースファイル（DuckDB）のバックアップやバージョン管理を検討してください。
- .env やシークレットはリポジトリに含めないでください。

ディレクトリ構成（主要ファイル）
------------------------------
src/kabusys/
- __init__.py
- config.py                       — 環境変数 / .env 読み込みと Settings
- ai/
  - __init__.py
  - news_nlp.py                    — ニュースセンチメント（ai_scores）
  - regime_detector.py             — 市場レジーム判定
- data/
  - __init__.py
  - jquants_client.py              — J-Quants API クライアント + 保存ロジック
  - pipeline.py                    — ETL パイプラインと run_daily_etl / run_*_etl
  - etl.py                         — ETLResult の再エクスポート
  - calendar_management.py         — market_calendar 関連ユーティリティ
  - stats.py                       — zscore_normalize 等の統計関数
  - quality.py                     — データ品質チェック
  - audit.py                       — 監査テーブル DDL / 初期化
  - news_collector.py              — RSS 収集 / 前処理
- research/
  - __init__.py
  - factor_research.py             — Momentum / Value / Volatility 計算
  - feature_exploration.py         — 将来リターン / IC / サマリー 等

その他
- data/ (既定のデータ保存先: data/kabusys.duckdb, data/monitoring.db 等)
- .env.example（無ければ config.py のコメントを参考に作成）

開発・テスト
------------
- config._find_project_root は .git または pyproject.toml を基準に .env を自動ロードします。ユニットテストや CI では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動ロードを無効化できます。
- AI 関連の外部 API 呼び出しは個別関数（_call_openai_api 等）をモックしてテストできます（コード内に差し替え用のコメントあり）。

ライセンス / 貢献
----------------
- 本リポジトリのライセンス情報・貢献ガイドはリポジトリルートの LICENSE / CONTRIBUTING を参照してください（存在しない場合はプロジェクト管理者に確認してください）。

最後に
------
この README はコードベースの主要コンポーネントと使い始めの手順をまとめたものです。詳細な API（関数の引数・返り値）や DB スキーマ、運用手順は各モジュールのドキュメント文字列（docstring）を参照してください。README の補足や実行例が必要であれば、どのユースケースを優先して説明するか教えてください。