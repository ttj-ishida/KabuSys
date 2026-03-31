KabuSys — 日本株自動売買プラットフォーム（README）
概要
本リポジトリは日本株向けのデータパイプライン、研究（リサーチ）、ニュースNLP／LLM を使った評価、監査ログ、監視・実行に必要なライブラリ群を含むモジュール群です。  
主に DuckDB をデータストアとして使い、J-Quants API からデータを取得・保存し、OpenAI（gpt-4o-mini 等）を用いてニュースやマクロセンチメントを評価する機能を提供します。

主な特徴（機能一覧）
- ETL（data.pipeline）
  - J-Quants から株価（日足）、財務、マーケットカレンダーを差分取得・保存
  - 品質チェック（欠損・スパイク・重複・日付不整合）
  - 日次パイプライン run_daily_etl による一括実行
- データ管理（data）
  - DuckDB 用の保存ユーティリティ（save_daily_quotes / save_financial_statements / save_market_calendar）
  - カレンダー管理（営業日判定 / next/prev_trading_day / calendar_update_job）
  - ニュース収集（RSS -> raw_news テーブル）
  - 監査ログ（audit）: signal / order_request / execution のテーブル定義と初期化ユーティリティ
- AI（ai）
  - news_nlp.score_news: ニュースを銘柄ごとに集約し OpenAI に投げてセンチメントを ai_scores に保存
  - regime_detector.score_regime: ETF（1321）の MA200 乖離とマクロニュースの LLMセンチメントを合成して market_regime を作成
- 研究（research）
  - factor_research: モメンタム / ボラティリティ / バリューなどのファクター計算
  - feature_exploration: 将来リターン計算、IC（スピアマン）や統計サマリー、ランク化
  - data.stats.zscore_normalize による Z スコア正規化ユーティリティ
- セキュリティと堅牢性
  - J-Quants クライアントにレートリミッタ・リトライ・401 自動リフレッシュ実装
  - ニュース収集に SSRF 対策、XML パースに defusedxml、レスポンスサイズ制限
  - OpenAI 呼出しはリトライやレスポンス検証を実装（JSON mode 想定）

セットアップ手順
前提
- Python 3.10+（typing の union | を想定）
- DuckDB が Python パッケージで利用可能
- OpenAI API（ニュース / レジーム判定で使用）および J-Quants API の資格情報

1) 仮想環境作成（任意）
- python -m venv .venv
- source .venv/bin/activate (Windows: .venv\Scripts\activate)

2) 必要パッケージをインストール
本 README は requirements.txt を同梱していないため、少なくとも以下をインストールしてください：
- duckdb
- openai
- defusedxml

例:
pip install duckdb openai defusedxml

（実際のプロジェクトではその他ロギング等を requirements に含めることを推奨します）

3) 環境変数の設定
プロジェクトは .env / .env.local（プロジェクトルート）を自動で読み込みます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。必要な環境変数の主な一覧:

必須:
- JQUANTS_REFRESH_TOKEN  — J-Quants リフレッシュトークン
- SLACK_BOT_TOKEN        — Slack 通知を使う場合の Bot トークン
- SLACK_CHANNEL_ID       — Slack チャンネル ID
- KABU_API_PASSWORD      — kabuステーション API のパスワード（本モジュールでは参照のみ）
- OPENAI_API_KEY         — OpenAI API キー（ai.score_news / score_regime に必要）

任意（デフォルト値あり）:
- KABUSYS_ENV            — development / paper_trading / live（default: development）
- LOG_LEVEL              — DEBUG, INFO, WARNING, ERROR, CRITICAL（default: INFO）
- KABUS_API_BASE_URL     — kabu API のベース URL（default: http://localhost:18080/kabusapi）
- DUCKDB_PATH            — DuckDB ファイルパス（default: data/kabusys.duckdb）
- SQLITE_PATH            — 監視等に使う SQLite パス（default: data/monitoring.db）

.env 例:
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
SLACK_BOT_TOKEN=xoxb-xxxxxxxxxxxxxxxx
SLACK_CHANNEL_ID=C0123456789
KABU_API_PASSWORD=your_kabu_password
KABUSYS_ENV=development
LOG_LEVEL=INFO

4) DuckDB の初期化（監査DB 等）
監査用 DB を初期化する例:
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# conn は duckdb.DuckDBPyConnection

使い方（主要な使い方例）
- ETL（日次パイプライン）実行
from datetime import date
import duckdb
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())

- ニュースセンチメント（ニュース -> ai_scores）
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
# api_key を明示的に渡すか環境変数 OPENAI_API_KEY を設定
n_written = score_news(conn, target_date=date(2026, 3, 20))
print("書き込み銘柄数:", n_written)

- 市場レジーム判定
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20))

- 研究用ファクター計算（例: モメンタム）
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum

conn = duckdb.connect(str(settings.duckdb_path))
records = calc_momentum(conn, target_date=date(2026, 3, 20))
# records は各銘柄の辞書リスト

- 監査スキーマ初期化（既存接続へDDLを追加）
from kabusys.data.audit import init_audit_schema
init_audit_schema(conn, transactional=True)

環境変数による自動 .env 読み込み
- パッケージ読み込み時にプロジェクトルート（.git または pyproject.toml があるディレクトリ）を探索し、.env と .env.local を順に読み込みます。
- 既存 OS 環境変数は上書きされません。.env.local は override=True で上書きが許可されます（ただしすでに OS 環境変数があるキーはプロテクトされます）。
- 自動読み込みを無効化する場合:
export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

注意点・設計上のポリシー
- ルックアヘッドバイアス対策: モジュール内の関数は date.today()／datetime.today() を直接参照せず、target_date を明示して処理するように設計されています。バッチやバックテストで使用する際は target_date を明示してください。
- エラー耐性: OpenAI / J-Quants の呼び出しはリトライやフォールバックを備え、API エラー時も致命的に停止しないようにしています（ただし最終的にはログ・監視が必要です）。
- DuckDB に対する INSERT 操作は冪等性（ON CONFLICT DO UPDATE / DO NOTHING）を意識しています。
- ニュース収集は SSRF/サイズ攻撃・XML 攻撃等に対策を施しています。

ディレクトリ構成（主要ファイル）
src/kabusys/
- __init__.py  （パッケージ初期化、__version__）
- config.py    （環境変数 / Settings）
- ai/
  - __init__.py
  - news_nlp.py          （ニュース NLP スコアリング）
  - regime_detector.py   （市場レジーム判定）
- data/
  - __init__.py
  - jquants_client.py    （J-Quants API クライアント、保存ユーティリティ）
  - pipeline.py          （ETL パイプライン、run_daily_etl 等）
  - etl.py               （ETLResult の再エクスポート）
  - news_collector.py    （RSS 取得と raw_news 保存ロジック）
  - calendar_management.py （市場カレンダー管理）
  - quality.py           （データ品質チェック）
  - stats.py             （統計ユーティリティ: zscore_normalize）
  - audit.py             （監査ログテーブル定義・初期化）
- research/
  - __init__.py
  - factor_research.py   （モメンタム/ボラティリティ/バリュー計算）
  - feature_exploration.py （将来リターン / IC / summary / rank）
- ai, data, research 以下にはさらに細かな関数とロジックが含まれます。

ロギング・監視
- settings.log_level によってログレベルが検証されます。実運用ではログをファイルや外部集約（ELK / Datadog 等）へ出力する設定を追加してください。
- ETLResult を用いて ETL 実行の状態（品質問題やエラー）を監査・通知に使ってください（例: Slack 通知）。

開発・テスト
- config モジュールは自動で .env をロードしますが、ユニットテスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定するか settings をモックしてください。
- OpenAI 呼び出しは内部で _call_openai_api を使っています。テストでは unittest.mock.patch によりこの関数を差し替えて外部呼び出しをモックできます（news_nlp・regime_detector 両方で差し替え可能）。
- J-Quants クライアントの _request はネットワークアクセスを行うため、テストでは jq モジュール関数をモックしてください。

ライセンス・貢献
リポジトリに LICENSE ファイルがある場合はそれに従ってください。  
バグ報告・機能追加は Issue を立ててください。

---

この README はコードベースの仕様・利用方法の概略を示しています。実運用では運用手順書（デプロイ、バックアップ、監視、ロールバック）や詳細な schema 定義（テーブルカラム仕様）を併せて用意してください。必要に応じて README を拡張しますので、追加で記載したい内容（例えば具体的な SQL スキーマ、CI/CD 手順、requirements.txt の作成など）があれば教えてください。