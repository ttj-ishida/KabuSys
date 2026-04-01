KabuSys — 日本株自動売買プラットフォーム
=================================

概要
----
KabuSys は日本株向けのデータ・リサーチ・AI支援・監査ログ・ETL を統合したライブラリ群です。本リポジトリは主に以下を提供します。

- J-Quants API を用いた市場データ（株価・財務・カレンダー）取得と DuckDB への ETL
- RSS ベースのニュース収集と LLM によるニュースセンチメント集約（gpt-4o-mini を想定）
- 市場レジーム判定（ETF 1321 の MA200乖離 + マクロニュースセンチメント）
- 研究用ファクター計算（モメンタム / ボラティリティ / バリュー 等）
- データ品質チェック・監査ログ（監査テーブルと初期化ユーティリティ）
- 環境変数管理（.env/.env.local の自動読み込み機能）

主な特徴
--------
- DuckDB ベースのオンプレ／ローカルデータストアを想定した ETL パイプライン
- J-Quants API クライアント（レートリミット・リトライ・トークン自動刷新対応）
- OpenAI（gpt-4o-mini 等）を使ったバッチ型ニュースセンチメント評価（JSON Mode）
- Look-ahead bias を避ける設計（内部で datetime.today()/date.today() に依存しない）
- 冪等保存（ON CONFLICT を利用）・トランザクション制御・フェイルセーフ設計
- ニュース収集に対する SSRF/サイズ/パース対策（defusedxml 等を利用）

セットアップ
-----------

前提
- Python 3.10+（typing 機能や Union 表記を使用）
- ネットワーク接続（J-Quants / OpenAI / RSS ソース）

依存関係（代表例）
- duckdb
- openai
- defusedxml
- （必要に応じて）その他 HTTP/DB ユーティリティ

例: 仮想環境を作成してインストールする
- Unix/macOS:
  python -m venv .venv
  source .venv/bin/activate
  pip install -U pip
  pip install duckdb openai defusedxml
  # パッケージを開発インストールする場合（リポジトリルートに pyproject.toml があることを想定）
  pip install -e .

.env / 環境変数
- 本パッケージは起動時にプロジェクトルート（.git または pyproject.toml を基準）を探索し、
  .env → .env.local を順に読み込みます（OS 環境変数が優先）。自動ロードを無効化するには:
  KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

主要な環境変数（例）
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- OPENAI_API_KEY: OpenAI の API キー（score_news / score_regime で使用）
- KABU_API_PASSWORD: kabuステーション API のパスワード（本コードベースでは設定参照のみ）
- SLACK_BOT_TOKEN, SLACK_CHANNEL_ID: 監視・通知で使用予定の Slack 情報
- DUCKDB_PATH: デフォルトの DuckDB ファイルパス（例: data/kabusys.duckdb）
- SQLITE_PATH: 監視用途の sqlite パス（例: data/monitoring.db）
- PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT: 監視設定
- KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL

簡易 .env 例
- .env.example を参考に作成してください。必要最低限は JQUANTS_REFRESH_TOKEN と OPENAI_API_KEY。

使い方（代表例）
----------------

共通準備
- DuckDB 接続を用意して操作することを想定しています（duckdb.connect）。

例: 日次 ETL を実行する
- data.pipeline.run_daily_etl を呼び出して、カレンダー・株価・財務の差分ETL と品質チェックを実行します。

Python スニペット:
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str("/path/to/kabusys.duckdb"))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())

ニュースセンチメント（銘柄ごと）
- kabusys.ai.news_nlp.score_news を使用して、raw_news と news_symbols を元に各銘柄の ai_score を ai_scores テーブルへ書き込みます。

Python スニペット:
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026, 3, 20))
print("written:", n_written)

市場レジーム判定
- kabusys.ai.regime_detector.score_regime は ETF 1321 の MA200 乖離とマクロニュースの合成で市場レジームを計算し market_regime テーブルへ保存します。

Python スニペット:
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))

監査ログ DB 初期化
- 監査テーブル（signal_events / order_requests / executions）を作成するユーティリティがあります。

Python スニペット:
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/audit.duckdb")  # 親ディレクトリを自動作成
# 以後 conn に対して監査テーブルが利用可能

研究・ファクター計算
- kabusys.research にモジュールを集約しています。例: calc_momentum, calc_volatility, calc_value

Python スニペット:
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum

conn = duckdb.connect("data/kabusys.duckdb")
records = calc_momentum(conn, target_date=date(2026, 3, 20))
# records は [{ "date": ..., "code": ..., "mom_1m": ..., ... }, ...]

データ品質チェック
- data.quality.run_all_checks を使って ETL 後の品質チェックを行います（QualityIssue のリストが返る）。

Python スニペット:
from kabusys.data.quality import run_all_checks
issues = run_all_checks(conn, target_date=date(2026,3,20))
for i in issues:
    print(i)

ディレクトリ構成（主要ファイル）
------------------------------
src/kabusys/
- __init__.py
- config.py
  - 環境変数読み込み・Settings クラス（.env 自動読み込み・必須キー検査）
- ai/
  - __init__.py
  - news_nlp.py           # ニュースを銘柄ごとに集約して OpenAI でスコア化
  - regime_detector.py    # 市場レジーム判定ロジック（MA200 + マクロセンチメント）
- data/
  - __init__.py
  - jquants_client.py     # J-Quants API クライアント（取得＋DuckDB 保存）
  - pipeline.py           # 日次 ETL パイプラインと個別ジョブ
  - etl.py                # ETLResult の再エクスポート
  - calendar_management.py# 市場カレンダー管理・営業日判定
  - news_collector.py     # RSS 収集・前処理・DB 保存（SSRF/サイズ対策あり）
  - stats.py              # 共通統計ユーティリティ（zscore_normalize 等）
  - quality.py            # データ品質チェック（欠損・スパイク・重複・日付整合性）
  - audit.py              # 監査ログテーブル DDL と初期化
- research/
  - __init__.py
  - factor_research.py    # モメンタム/ボラティリティ/バリュー計算
  - feature_exploration.py# forward returns / IC / factor summary / rank 等

設計上の注意点
--------------
- Look-ahead bias の防止:
  多くのモジュール（news_nlp, regime_detector, pipeline）は内部で datetime.today() を参照せず、
  呼び出し側から target_date を明示的に与える設計です。バックテストでは必ず過去データのみを与えてください。
- 自動 .env ロード:
  .env/.env.local のロードはプロジェクトルートの探索に依存します。パッケージ配布後やテスト実行時に問題があれば、
  KABUSYS_DISABLE_AUTO_ENV_LOAD を設定して手動で環境を用意してください。
- リトライ・レート制限:
  J-Quants クライアントは API レート制限（120 req/min）と 5xx/429 等への指数バックオフを実装しています。
- DuckDB の互換性:
  一部の executemany / リストバインドについては DuckDB のバージョンにより挙動差があるため、実装で回避策を入れています。

拡張と運用
-----------
- 実運用で発注（kabuステーション等）を行う際は、監査ログを必ず有効にして order_request_id を冪等キーとして利用してください。
- Slack 通知や監視エージェントは config.Settings で設定を管理できます（実装は別途追加）。
- OpenAI の呼び出しはレートとコストが関係するためバッチ単位（news_nlp の _BATCH_SIZE）を適切に調整してください。

ライセンス / コントリビューション
---------------------------------
- 本 README ではライセンスは明示していません。実際のリポジトリでは LICENSE ファイルを参照してください。
- コントリビューション規約（PR/Issue の出し方・コードスタイル等）がある場合はリポジトリの CONTRIBUTING.md を参照してください。

問い合わせ
----------
- 実装や利用についての質問はリポジトリの Issue を利用してください。具体的なログ・再現コードを添えていただけると対応が早まります。

補足
----
ここに示した使い方は代表的な呼び出しパターンです。各関数の詳細な挙動・引数・例外については対応するモジュール（src/kabusys/**.py）の docstring を参照してください。