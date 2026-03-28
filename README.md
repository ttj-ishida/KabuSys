KabuSys
======

日本株向けの自動売買 / データパイプライン基盤ライブラリです。  
ETL（J-Quants からの市場データ取得）、ニュース収集・NLP スコアリング、ファクター計算、監査ログ（発注 → 約定トレース）、市場レジーム判定などの機能群を含みます。

主な特徴
--------
- J-Quants API からの差分 ETL（株価日足・財務・市場カレンダー）と品質チェック
- RSS を用いたニュース収集と OpenAI（gpt-4o-mini）を使った銘柄別センチメント scoring（ai_scores）
- 市場レジーム判定（ETF 1321 の MA200 とマクロニュースの LLM 評価を合成）
- ファクター計算（モメンタム / バリュー / ボラティリティ等）と研究用ユーティリティ（前方リターン、IC、統計サマリー）
- 監査ログ（signal_events / order_requests / executions）用の DuckDB スキーマ初期化ユーティリティ
- データ品質チェック（欠損・重複・スパイク・日付不整合）

導入（前提）
------------
- Python 3.10+
- 必要なパッケージ（例）
  - duckdb
  - openai
  - defusedxml
  - （標準ライブラリ以外は requirements.txt / pyproject.toml に合わせてインストールしてください）

例:
pip install duckdb openai defusedxml

環境変数（主要）
----------------
本プロジェクトは .env（および .env.local）または環境変数から設定を読み込みます。自動ロードはプロジェクトルート（.git または pyproject.toml）を基準に行われます。自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

必須（コードで _require されるもの）
- JQUANTS_REFRESH_TOKEN  — J-Quants 用リフレッシュトークン（ETL）
- KABU_API_PASSWORD      — kabuステーション API パスワード（実運用時）
- SLACK_BOT_TOKEN        — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID       — Slack 通知先チャネル ID

任意／デフォルト
- KABUSYS_ENV            — 稼働環境: development / paper_trading / live（デフォルト development）
- LOG_LEVEL              — ログレベル: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト INFO）
- DUCKDB_PATH            — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH            — SQLite（監視等）データベースパス（デフォルト data/monitoring.db）
- OPENAI_API_KEY         — OpenAI API キー（score_news / score_regime で未指定なら環境変数を参照）

簡易 .env.example
-----------------
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=your_openai_api_key
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb

セットアップ手順
----------------
1. リポジトリをクローン / コピー
2. Python 仮想環境作成・有効化
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
3. 依存パッケージをインストール
   pip install -r requirements.txt
   （requirements.txt がない場合は上記の主要パッケージを個別インストール）
4. .env をプロジェクトルートに作成し、必要な環境変数を設定
5. DuckDB ファイルを作成／準備（デフォルトは data/kabusys.duckdb）

基本的な使い方（コード例）
-------------------------

- DuckDB 接続を作って日次 ETL を実行する
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str("/path/to/kabusys.duckdb"))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())

- ニュースセンチメントを取得して ai_scores テーブルへ書き込む
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect(str("/path/to/kabusys.duckdb"))
written = score_news(conn, target_date=date(2026, 3, 20))
print(f"written: {written} codes")

- 市場レジームをスコアリングして market_regime テーブルへ書き込む
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect(str("/path/to/kabusys.duckdb"))
score_regime(conn, target_date=date(2026, 3, 20))

- 監査ログ用 DB を初期化する（監査専用 DB を別途作る場合）
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# これで signal_events / order_requests / executions テーブルが作成されます

- ファクター計算・研究ユーティリティの利用例
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
from kabusys.research.feature_exploration import calc_forward_returns, calc_ic, factor_summary
from kabusys.data.stats import zscore_normalize

conn = duckdb.connect("data/kabusys.duckdb")
target = date(2026, 3, 20)
mom = calc_momentum(conn, target)
fwd = calc_forward_returns(conn, target, horizons=[1,5,21])
ic = calc_ic(mom, fwd, factor_col="mom_1m", return_col="fwd_1d")
print("IC:", ic)

運用上の注意・設計方針
--------------------
- ルックアヘッドバイアス対策: 多くのモジュールは date を明示的に引数で受け取り、datetime.today()/date.today() を直接参照しない設計です。バックテストで過去日時を指定して利用できます。
- 冪等性: ETL の保存関数や監査スキーマ初期化は冪等的（ON CONFLICT / INSERT ... DO UPDATE 等）に実装されています。
- フェイルセーフ: 外部 API（OpenAI / J-Quants 等）呼び出しの失敗時は、可能な限りフェイルセーフな既定値にフォールバックし、プロセスを停止させない設計が採られています（ただし重要なキー未設定時は例外）。
- ログレベルや環境（development/paper_trading/live）は環境変数で切替可能です。

ディレクトリ構成（主要ファイル）
------------------------------
src/kabusys/
- __init__.py              - パッケージ定義（version 等）
- config.py                - 環境変数/設定管理
- ai/
  - __init__.py
  - news_nlp.py            - ニュース NLP（score_news）
  - regime_detector.py     - 市場レジーム判定（score_regime）
- data/
  - __init__.py
  - jquants_client.py      - J-Quants API クライアント（fetch/save）
  - pipeline.py            - ETL パイプライン / run_daily_etl / ETLResult
  - etl.py                 - ETL インターフェース再公開（ETLResult）
  - news_collector.py      - RSS ニュース収集
  - calendar_management.py - 市場カレンダー管理（is_trading_day 等）
  - quality.py             - データ品質チェック
  - stats.py               - zscore_normalize 等の統計ユーティリティ
  - audit.py               - 監査ログスキーマ初期化 / init_audit_db
- research/
  - __init__.py
  - factor_research.py     - ファクター計算（momentum / value / volatility）
  - feature_exploration.py - 前方リターン / IC / summary / rank

各モジュールの役割はコード内 docstring（日本語）に詳述されています。実装や拡張時はそれらを参照してください。

テスト・開発向けフラグ
--------------------
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると package import 時の .env 自動ロードを無効化できます（テスト時に便利）。
- OpenAI などの外部 API 呼び出しは内部関数をモックできるよう設計されています（例: kabusys.ai.news_nlp._call_openai_api をパッチするなど）。

ライセンス・貢献
----------------
（ここにプロジェクトのライセンス表記や貢献方法を追記してください）

補足
----
本 README はコードベースの主要機能・使い方を概説しています。より詳細な API 仕様や運用手順（cron / Airflow などでの ETL スケジューリング、監視設定、Slack 通知の実装）は別ドキュメントにまとめることを推奨します。質問や追加のドキュメント化が必要な箇所があれば教えてください。