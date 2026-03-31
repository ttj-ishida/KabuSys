KabuSys
=======

日本株向けのデータプラットフォーム兼自動売買基盤のコアライブラリです。
本リポジトリは以下の機能群を提供します：J-Quants からのデータ ETL、ニュース収集と LLM によるニュースセンチメント付与、ファクター計算やリサーチ補助、監査ログ（発注→約定トレース）機能、マーケットカレンダー管理、及び市場レジーム判定など。

プロジェクト概要
--------------
KabuSys は日本株の自動売買システムを支えるライブラリ群です。主に以下を目的としています：

- J-Quants API からの株価・財務・カレンダーデータ取得と DuckDB への冪等保存（ETL）
- RSS ベースのニュース収集、前処理、LLM（OpenAI）を使った銘柄単位のニュースセンチメント付与
- 市場レジーム判定（ETF の MA とマクロニュースの LLM スコアを合成）
- ファクター計算（モメンタム・ボラティリティ・バリュー等）とリサーチユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 発注から約定までを辿れる監査ログ（DuckDB）
- 市場カレンダーの管理と営業日判定

主な特徴
--------
- DuckDB を中核にしたローカル DB ベースのデータプラットフォーム
- J-Quants API との連携（レート制御・トークン自動リフレッシュ・リトライ）
- OpenAI（gpt-4o-mini 等）を利用したニュース NLP（JSON Mode を想定）
- Look-ahead バイアスを防ぐ設計（内部で date.today()/datetime.today() を直接参照しない等）
- 各種処理は冪等に設計（ON CONFLICT 等）されており再実行に強い
- テスト容易性を考慮した設計（環境変数自動ロードの無効化フラグ等）

セットアップ手順
----------------

前提
- Python 3.10 以上（typing の新しい記法を使用しているため）
- ネットワークアクセス（J-Quants / OpenAI / RSS）

1) 仮想環境の作成（推奨）
- python -m venv .venv
- source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2) 依存パッケージのインストール
必要な主要パッケージは以下です（プロジェクトの requirements.txt がある場合はそれを使用してください）。

- duckdb
- openai
- defusedxml

例:
- pip install duckdb openai defusedxml

（実際のプロジェクトでは logging, requests 等の追加依存があるかもしれません）

3) ソースコードを editable インストール（開発時）
- pip install -e .

環境変数 / .env
----------------
KabuSys は .env / .env.local をプロジェクトルートから自動読み込みします（優先順位: OS 環境 > .env.local > .env）。自動ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト時に便利）。

主な環境変数（必須と既定値）
- JQUANTS_REFRESH_TOKEN (必須) : J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) : kabuステーション API 用パスワード
- SLACK_BOT_TOKEN (必須) : Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID (必須) : Slack チャネル ID
- OPENAI_API_KEY (任意だが score_news/score_regime を使う場合は必須)
- KABUSYS_ENV (development | paper_trading | live) : デプロイ環境（デフォルト: development）
- LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL) : ログレベル（デフォルト: INFO）
- DUCKDB_PATH : DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH : SQLite（monitoring 等）パス（デフォルト data/monitoring.db）

例 (.env):
JQUANTS_REFRESH_TOKEN=xxxxxxxxxx
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=secret
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C12345678
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb

使い方（基本的な呼び出し例）
---------------------------

以下は主要ユーティリティの簡単な使い方例です。全て Python スクリプト/REPL から実行します。

1) 設定取得
from kabusys.config import settings
print(settings.jquants_refresh_token)
print(settings.duckdb_path)

2) DuckDB 接続の取得
import duckdb
from kabusys.config import settings
conn = duckdb.connect(str(settings.duckdb_path))

3) 監査 DB（発注/約定トレース）を初期化
from kabusys.data.audit import init_audit_db
audit_conn = init_audit_db(settings.duckdb_path)  # または ":memory:"
# あるいは既存 conn に対してスキーマを追加:
from kabusys.data.audit import init_audit_schema
init_audit_schema(conn)

4) 日次 ETL（J-Quants からの差分取得 → DuckDB 保存 → 品質チェック）
from kabusys.data.pipeline import run_daily_etl
from kabusys.config import settings
conn = duckdb.connect(str(settings.duckdb_path))
res = run_daily_etl(conn)  # target_date を指定可能
print(res.to_dict())

5) ニュースのスコア付け（LLM）
from kabusys.ai.news_nlp import score_news
from datetime import date
conn = duckdb.connect(str(settings.duckdb_path))
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # env の OPENAI_API_KEY を使用
print(f"scored {n_written} codes")

6) 市場レジーム判定
from kabusys.ai.regime_detector import score_regime
from datetime import date
conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20))  # OpenAI key は環境変数で解決

7) ファクター計算 / リサーチユーティリティ
from kabusys.research import calc_momentum, calc_value, calc_volatility, zscore_normalize
results = calc_momentum(conn, target_date=date(2026, 3, 20))
normalized = zscore_normalize(results, ["mom_1m", "mom_3m"])

機能一覧（モジュール別）
---------------------
- kabusys.config
  - 環境変数・設定読み込み（.env 自動ロード、Settings オブジェクト）

- kabusys.data
  - jquants_client: J-Quants API クライアント（認証、取得、DuckDB 保存）
  - pipeline / etl: 日次 ETL パイプライン（差分取得、保存、品質チェック）
  - news_collector: RSS 取得・前処理・raw_news 保存
  - calendar_management: 市場カレンダーの管理・営業日判定
  - quality: データ品質チェック（欠損・スパイク・重複・日付不整合）
  - stats: z-score 正規化など統計ユーティリティ
  - audit: 監査ログテーブル（signal_events / order_requests / executions）定義・初期化

- kabusys.ai
  - news_nlp: 銘柄ごとのニュースを LLM でスコア化して ai_scores に保存
  - regime_detector: ETF MA とマクロニュース LLM を組み合わせて市場レジーム判定

- kabusys.research
  - factor_research: モメンタム / ボラティリティ / バリューの計算
  - feature_exploration: 将来リターン計算、IC（Information Coefficient）、統計サマリー等

設計上の注意点 / 実運用のヒント
--------------------------------
- Look-ahead バイアス防止: 関数の多くは target_date を明示的に引数で受け取り、内部で date.today() などを参照しないように設計されています。バックテストや再現性を重視する場合は target_date を明示してください。
- OpenAI 呼び出し: news_nlp と regime_detector は JSON Mode を前提としたパーシング・バリデーションを実装しています。API の失敗やレスポンス不整合時はフォールバック（スコア 0.0 を使う等）する設計です。
- J-Quants API: レート制限（120 req/min）を尊重する内部 RateLimiter と、401 時のトークン自動リフレッシュ、一定のリトライロジックが組み込まれています。
- DuckDB の executemany に空リストは渡せないバージョン（0.10 系）を想定した安全処理があります。
- テスト時に .env 自動ロードを無効にする場合:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してからモジュールインポートしてください。

ディレクトリ構成（主要ファイル）
------------------------------
src/kabusys/
- __init__.py
- config.py

src/kabusys/ai/
- __init__.py
- news_nlp.py
- regime_detector.py

src/kabusys/data/
- __init__.py
- jquants_client.py
- pipeline.py
- etl.py
- news_collector.py
- calendar_management.py
- quality.py
- stats.py
- audit.py

src/kabusys/research/
- __init__.py
- factor_research.py
- feature_exploration.py

（上記は本リポジトリの主要モジュール構成を抜粋しています）

開発・貢献
-----------
- コードは可読性・ロバストネスを重視しており、関数単位でのテストが可能です。外部 API 呼び出し部分はモックしやすい設計になっています（例: _call_openai_api / _urlopen の差し替え）。
- PR では、ユニットテスト・docstring・型注釈を追加してください。
- 敏感情報（API キー等）は .env.local や CI シークレットで管理してください。

ライセンス・免責
----------------
本ドキュメントはソースコードに基づく概要説明です。実運用時は各 API プロバイダの利用規約、金融関連の法規制、及び自動売買リスクを十分に理解した上でご利用ください。

補足
----
- README に記載のコマンドやサンプルはあくまで利用例です。実行前に必ず環境変数・DB スキーマ（必要なテーブル）の初期化を行ってください。
- 追加で知りたい使い方（例: ETL の具体的な cron 設定、Slack 通知の使い方、kabu API 経由の発注フローなど）があれば教えてください。サンプルコードや運用手順を追記します。