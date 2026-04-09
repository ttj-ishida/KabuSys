KabuSys
======

日本株向けのデータ基盤・リサーチ・自動売買支援ライブラリです。DuckDB をデータ層に、J-Quants / kabu ステーション等の外部 API と連携してデータ取得・品質チェック・ファクター計算・ニュース NLP・監査ログなどの機能を提供します。

概要
---
KabuSys は以下の主要コンポーネントを含む Python パッケージです：

- data: データ ETL、カレンダー管理、J-Quants クライアント、ニュース収集、データ品質チェック、監査ログ（トレーサビリティ）
- research: ファクター計算・特徴量解析ユーティリティ（モメンタム、ボラティリティ、バリュー、IC、統計サマリー等）
- ai: ニュースの NLP（OpenAI を用いたセンチメント算出）や市場レジーム判定
- config: 環境変数／設定の読み込み（.env 自動ロード、必須値チェック）
- その他: 実行・監視・発注まわりのモジュール（将来的に拡張）

主な機能一覧
---
- J-Quants API 経由での株価（日足）・財務データ・市場カレンダー取得（rate limit と retry 実装）
- 日次 ETL パイプライン（差分取得、バックフィル、品質チェック）
- データ品質チェック（欠損、スパイク、重複、将来日付/非営業日チェック）
- ニュース収集（RSS、URL 正規化、SSRF 対策、前処理）と銘柄紐付け
- OpenAI を使ったニュースセンチメント（銘柄別）およびマクロセンチメントを用いた市場レジーム判定
- 監査ログ（signal_events, order_requests, executions）スキーマの初期化ユーティリティ
- 研究向けユーティリティ（ファクター計算、Zスコア正規化、将来リターン計算、IC 計算 等）
- 設定管理：.env/.env.local の自動読み込み（OS 環境変数 > .env.local > .env）、必要なキーの明示化

セットアップ手順
---
前提:
- Python 3.10+（型注釈で | を使うため）
- DuckDB（Python パッケージとしてインストール）
- OpenAI SDK（OpenAI API を使う場合）
- defusedxml（RSS パース用、安全対策）

例: 仮想環境作成とパッケージインストール
1. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (または Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール（プロジェクトに requirements.txt がある想定）
   - pip install duckdb openai defusedxml

   （プロジェクトに setup.py / pyproject.toml があれば `pip install -e .` を使えます）

3. データディレクトリ作成（例）
   - mkdir -p data

環境変数（.env）設定
プロジェクトは .env / .env.local を自動的にプロジェクトルートから読み込みます（OS 環境変数が優先）。自動ロードを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

代表的な環境変数（README のサンプル）:
- JQUANTS_REFRESH_TOKEN=あなたのJ-Quantsリフレッシュトークン
- KABU_API_PASSWORD=kabu API のパスワード
- KABU_API_BASE_URL=http://localhost:18080/kabusapi
- OPENAI_API_KEY=sk-...
- LINE_CHANNEL_ACCESS_TOKEN=（任意）
- LINE_USER_ID=（任意）
- DUCKDB_PATH=data/kabusys.duckdb
- SQLITE_PATH=data/monitoring.db
- PAPER_FILL_MODE=instant   # instant|partial|never|reject
- PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
- KABUSYS_ENV=development   # development|paper_trading|live
- LOG_LEVEL=INFO

例 .env（簡易）
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=DEBUG

使い方（簡易チュートリアル）
---
ここでは Python REPL / スクリプトでの代表的な利用例を示します。

1) DuckDB 接続の作成
from datetime import date
import duckdb
conn = duckdb.connect("data/kabusys.duckdb")

2) 監査ログ用スキーマ初期化
from kabusys.data.audit import init_audit_schema
# 既存 conn に監査テーブル群を追加（トランザクション管理は引数で制御）
init_audit_schema(conn, transactional=True)

もしくは監査専用 DB を作成:
from kabusys.data.audit import init_audit_db
audit_conn = init_audit_db("data/monitoring.db")

3) 日次 ETL を実行（J-Quants からの差分取り込み・品質チェック）
from kabusys.data.pipeline import run_daily_etl
result = run_daily_etl(conn)  # 引数で target_date/id_token を渡せる
print(result.to_dict())

4) ニュース NLP スコアリング
from kabusys.ai.news_nlp import score_news
from datetime import date
n_written = score_news(conn, target_date=date(2026,3,19))
print(f"書き込み銘柄数: {n_written}")

5) 市場レジーム判定（ETF 1321 の MA200 とマクロセンチメントを合成）
from kabusys.ai.regime_detector import score_regime
score_regime(conn, target_date=date(2026,3,19))

6) ニュース収集（RSS を取得して raw_news に入れる処理はアプリ側で組む）
from kabusys.data.news_collector import fetch_rss
articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", "yahoo_finance")
# 取得した記事の保存処理はアプリ側で raw_news テーブルへ実装する

設定参照（コード内での利用）
- アプリ設定は kabusys.config.settings で参照できます。
  例: from kabusys.config import settings; settings.jquants_refresh_token

注意点・運用上のヒント
- OpenAI や J-Quants 呼び出しは API キーが必須です。API キーは環境変数か関数引数で与えてください。
- news_nlp / regime_detector は外部 API 呼び出しでコストとレイテンシが発生します。バッチ化やレート制御を考慮してください。
- .env の自動読み込みはプロジェクトルート（.git や pyproject.toml があるディレクトリ）から行われます。テスト等で自動読み込みを無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- Paper Trading / モックブローカー挙動は settings.paper_fill_mode により制御できます（instant|partial|never|reject）。

ディレクトリ構成（主要ファイル）
---
以下は src/kabusys 以下の主要モジュールとファイルの抜粋です（実際の全ファイルはリポジトリを参照）：

- src/kabusys/
  - __init__.py
  - config.py                       # 環境変数 / .env の読み込みと Settings クラス
  - ai/
    - __init__.py
    - news_nlp.py                    # ニュースセンチメント（OpenAI 連携）
    - regime_detector.py             # マクロ+MA200 による市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py              # J-Quants API クライアント（取得 + DuckDB 保存）
    - pipeline.py                    # 日次 ETL パイプライン（run_daily_etl 等）
    - etl.py                         # ETLResult のエクスポート
    - calendar_management.py         # 市場カレンダー管理、営業日判定
    - news_collector.py              # RSS 収集・前処理（SSRF 対策等）
    - quality.py                     # データ品質チェック群
    - stats.py                       # zscore_normalize 等の統計ユーティリティ
    - audit.py                       # 監査ログ（schema 定義・初期化）
  - research/
    - __init__.py
    - factor_research.py             # モメンタム / ボラティリティ / バリュー 等
    - feature_exploration.py         # 将来リターン / IC / 統計サマリ等

依存関係（代表）
---
必要な主要ライブラリの例：
- duckdb
- openai
- defusedxml

その他標準ライブラリ（urllib, json, logging, datetime, math, hashlib など）を多用します。詳しいバージョンや追加依存はプロジェクトの pyproject.toml / requirements.txt を参照してください。

ライセンス / 貢献
---
（この README にはライセンス情報は含めていません。リポジトリの LICENSE ファイルを参照してください）

補足
---
- この README はコードベース内の docstring・設計コメントを元に要約しています。個々の関数には利用上の注意（ルックアヘッドバイアス回避、リトライ方針、トランザクションの扱いなど）が記載されていますので、実運用時は該当ソースの docstring を参照してください。
- 実際の運用では API キー管理（Vault 等）、監査ログの保存方針、バックテストと本番データの分離に十分注意してください。