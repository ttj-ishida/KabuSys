KabuSys
=======

概要
----
KabuSys は日本株向けのデータプラットフォーム・リサーチ・自動売買の基盤ライブラリです。  
J-Quants からの市場データ取得・ETL、ニュース収集と LLM を用いたニュース NLP、マーケットレジーム判定、ファクタ算出、データ品質チェック、監査ログ（トレーサビリティ）などを提供します。  
主に DuckDB を用いたローカルデータベースと OpenAI（gpt-4o-mini）を組み合わせた分析ワークフローを想定しています。

主な特徴
--------
- J-Quants API からの差分取得（株価・財務・カレンダー）と冪等保存
- 日次 ETL パイプライン（差分取得・保存・品質チェック）
- RSS ベースのニュース収集と前処理（SSRF / Gzip / トラッキングパラメータ対策）
- OpenAI を用いたニュースセンチメント評価（バッチ処理・リトライ制御）
- 市場レジーム判定（ETF 1321 の MA200 とマクロニュースを合成）
- 研究用ファクター計算（モメンタム / バリュー / ボラティリティ等）
- データ品質チェック（欠損・重複・スパイク・日付不整合）
- 監査ログ（signal → order_request → execution のトレーサビリティ）の初期化ユーティリティ
- 設定管理（.env 自動ロード、環境変数経由）

必要条件
--------
- Python 3.10+
- ネットワークアクセス（J-Quants / OpenAI / RSS）
- 以下 Python パッケージ（代表例）:
  - duckdb
  - openai
  - defusedxml
  - （標準ライブラリ以外は pip でインストールしてください）

インストール
------------
1. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate (macOS / Linux)
   - .venv\Scripts\activate (Windows)

2. 必要パッケージをインストール（例）
   - pip install duckdb openai defusedxml

   ※ 本リポジトリに setup.py / pyproject.toml がある場合は pip install -e . で開発インストールできます。

環境変数（.env）と自動読み込み
------------------------------
プロジェクトルートに .env / .env.local を置くと、自動的に読み込まれます（OS 環境変数が優先）。自動読み込みを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

主な必須環境変数（例）
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
- KABU_API_PASSWORD: kabuステーション API パスワード（発注系で使用）
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID: 通知先 Slack チャンネル ID
- OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector で使用）

任意 / デフォルト設定
- KABUSYS_ENV: development | paper_trading | live （デフォルト development）
- LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL （デフォルト INFO）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト data/monitoring.db）

サンプル .env
--------------
例（プロジェクトルートに .env として保存）:

JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=your_openai_api_key
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db

使い方（主なワークフロー）
------------------------

1) DuckDB 接続の準備
- 基本的には settings.duckdb_path を利用します。

Python 例:
from kabusys.config import settings
import duckdb
conn = duckdb.connect(str(settings.duckdb_path))

2) 日次 ETL 実行
- データ取得（カレンダー・株価・財務）と品質チェックを行います。

from kabusys.data.pipeline import run_daily_etl
from datetime import date
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())

3) ニュースのスコアリング（AI）
- 前日の 15:00 JST ～ 当日 08:30 JST を対象にニュースを集約し銘柄別スコアを ai_scores に保存します。

from kabusys.ai.news_nlp import score_news
from datetime import date
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key="YOUR_OPENAI_KEY")

4) 市場レジームの判定（AI + 技術指標）
- ETF 1321 の MA200 とマクロニュースを合成して market_regime に書き込みます。

from kabusys.ai.regime_detector import score_regime
score_regime(conn, target_date=date(2026, 3, 20), api_key="YOUR_OPENAI_KEY")

5) 監査ログ DB 初期化
- 監査用 DuckDB を別ファイルで初期化して接続を取得できます。

from kabusys.data.audit import init_audit_db
audit_conn = init_audit_db("data/audit.duckdb")

6) 研究用ファクター計算
- Python から直接呼び出して結果を取得できます（DuckDB 接続を渡す）。

from kabusys.research.factor_research import calc_momentum
records = calc_momentum(conn, target_date=date(2026,3,20))

7) データ品質チェック
- run_all_checks で一括チェックが実行できます。

from kabusys.data.quality import run_all_checks
issues = run_all_checks(conn, target_date=date(2026,3,20))

動作上の注意
------------
- AI 関連は OpenAI API（gpt-4o-mini）を利用します。API レートや課金に注意してください。
- ETL / API 呼び出しはネットワーク依存です。実運用ではリトライ・監視を組み合わせてください。
- DuckDB に対する多数の executemany/大規模 INSERT はパフォーマンスに影響します。運用スクリプトではバッチサイズやトランザクションを調整してください。
- .env の自動読み込みはプロジェクトルートを .git または pyproject.toml を基準に探します。パッケージ配布環境では CWD とは独立して動作します。

ディレクトリ構成（主なファイル）
------------------------------
src/kabusys/
- __init__.py
- config.py                       -- 環境変数 / 設定管理（.env 自動読み込み）
- ai/
  - __init__.py
  - news_nlp.py                    -- ニュースの LLM スコアリング
  - regime_detector.py             -- 市場レジーム判定
- data/
  - __init__.py
  - jquants_client.py              -- J-Quants API クライアント（取得・保存）
  - pipeline.py                    -- ETL パイプライン（run_daily_etl 等）
  - etl.py                         -- ETLResult の公開
  - calendar_management.py         -- マーケットカレンダー管理
  - news_collector.py              -- RSS ニュース収集
  - quality.py                     -- データ品質チェック
  - stats.py                       -- 汎用統計ユーティリティ
  - audit.py                       -- 監査ログ（テーブル初期化）
- research/
  - __init__.py
  - factor_research.py             -- ファクター計算（momentum/value/volatility）
  - feature_exploration.py         -- 特徴量探索・IC・統計サマリ
- research/*（補助モジュール）
- その他（strategy, execution, monitoring 等のパッケージが想定されるインターフェース）

開発 / テスト
--------------
- 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env 自動読み込みを無効化できます（ユニットテスト等で便利）。
- AI 呼び出し部分は内部の _call_openai_api をモックする設計になっています（ユニットテスト容易性を考慮）。

ライセンス / コントリビューション
--------------------------------
- 本 README にはライセンス情報を含めていません。実プロジェクトでは LICENSE を追加してください。  
- コントリビューション方法（PR / issue の流れなど）はプロジェクトポリシーに従ってください。

補足
----
この README はコードベースから抽出された設計・利用方法の概要です。実運用時は各モジュール内のドキュメント（docstring）を参照して、引数や返り値、例外の扱いを確認してください。必要であれば README にサンプルスクリプトや CI/CD 設定、運用 runbook（監視/ロギング/エラーハンドリング）を追加することを推奨します。