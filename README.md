KabuSys — 日本株自動売買システム
================================

プロジェクト概要
----------------
KabuSys は日本株向けのデータ基盤・リサーチ・戦略評価・監査（トレーサビリティ）を含む
自動売買支援ライブラリです。主に以下を提供します。

- J-Quants API からのデータ取得（株価日足、財務、上場情報、マーケットカレンダー）
- DuckDB を利用した ETL パイプライン（差分取得、保存、品質チェック）
- ニュースの収集・NLP による銘柄センチメント評価（OpenAI を用いたスコアリング）
- 市場レジーム判定（ETF + マクロニュースによる合成）
- ファクター計算・特徴量探索（モメンタム、バリュー、ボラティリティ、IC 等）
- 監査ログ（signal → order_request → execution のトレーサビリティ）用スキーマ初期化

設計上のポイント:
- DuckDB を中心に SQL + 最小限の Python で実装（外部 heavy ライブラリに依存しない方針）
- ルックアヘッドバイアス対策（関数は内部で date.today() 等に依存しない設計）
- 各種 API 呼び出しはリトライ／レート制御を備えフェイルセーフを重視

機能一覧
--------
主要な機能（モジュール別）:

- kabusys.config
  - .env / 環境変数読み込み、自動読み込みの仕組み（.env / .env.local）
  - settings オブジェクトで設定を参照（J-Quants トークン、OpenAI、DB パス等）

- kabusys.data
  - jquants_client: J-Quants API のラッパー（取得・保存・認証・レートリミット）
  - pipeline: run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl
  - news_collector: RSS 取得と raw_news への保存（SSRF 対策、正規化、重複回避）
  - quality: データ品質チェック（欠損・重複・スパイク・日付不整合）
  - calendar_management: 営業日判定・next/prev_trading_day 等
  - audit: 監査ログ用テーブル定義と初期化ユーティリティ（init_audit_db 等）
  - stats: zscore_normalize（研究用ユーティリティ）

- kabusys.ai
  - news_nlp.score_news: 銘柄ごとにニュースを集約して OpenAI でスコア化、ai_scores へ保存
  - regime_detector.score_regime: ETF（1321）MA 乖離 + マクロニュースセンチメントで市場レジーム判定

- kabusys.research
  - factor_research: calc_momentum / calc_value / calc_volatility
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank
  - research 用の統計解析ユーティリティ群

セットアップ手順
----------------

1. リポジトリをクローン
   - git clone ...（リポジトリ URL）

2. Python 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Unix/macOS)
   - .venv\Scripts\activate     (Windows)

3. 依存パッケージをインストール
   - pip install duckdb openai defusedxml
   - 必要に応じて開発用依存やその他ライブラリを追加してください。
   - （パッケージ化されている場合は pip install -e . でインストール可能）

4. 環境変数 / .env の準備
   - プロジェクトルート（.git または pyproject.toml のあるディレクトリ）に .env を置くと自動で読み込まれます。
   - 自動読み込みを無効化する場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

主要な環境変数（.env 例）
- JQUANTS_REFRESH_TOKEN=...
- KABU_API_PASSWORD=...
- KABU_API_BASE_URL=http://localhost:18080/kabusapi  (省略可)
- SLACK_BOT_TOKEN=...
- SLACK_CHANNEL_ID=...
- OPENAI_API_KEY=... (news_nlp / regime_detector の既定)
- DUCKDB_PATH=data/kabusys.duckdb
- SQLITE_PATH=data/monitoring.db
- KABUSYS_ENV=development|paper_trading|live
- LOG_LEVEL=INFO|DEBUG|...

例 (.env.example):
JQUANTS_REFRESH_TOKEN=your_refresh_token
OPENAI_API_KEY=sk-...
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO

使い方（簡易サンプル）
--------------------

以下は簡単な Python からの使い方例です。多くの関数は DuckDB の接続オブジェクトを受け取ります。

- DuckDB 接続と ETL 実行（日次 ETL）:

from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())

- ニューススコアリング（OpenAI API を環境変数で指定）:

from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
n = score_news(conn, target_date=date(2026,3,20))  # ai_scores へ書き込み
print(f"scored {n} codes")

- 市場レジーム判定（OpenAI API を環境変数で指定）:

from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026,3,20))

- 監査ログ DB の初期化:

from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")  # ファイルなければ作成され、スキーマ初期化される

注意点
- 多くの関数は OpenAI API (gpt-4o-mini) を利用します。api_key を引数で渡すか、環境変数 OPENAI_API_KEY を設定してください。
- DuckDB の一部操作（executemany の空リスト等）に注意して実装されています。API の戻り値が空の場合は関数が安全に早期リターンします。
- 設計上「date を明示して呼ぶ」ことでルックアヘッドバイアスを防ぐ実装になっています。バックテスト等では適切に date を管理してください。

ディレクトリ構成
----------------
（主要ファイルのみ抜粋）

src/kabusys/
- __init__.py
- config.py                      -- 環境変数・設定読み込み
- ai/
  - __init__.py
  - news_nlp.py                  -- ニュース集約・OpenAI による銘柄スコア
  - regime_detector.py           -- ETF MA + マクロニュースでレジーム判定
- data/
  - __init__.py
  - jquants_client.py            -- J-Quants API クライアント（取得/保存/認証）
  - pipeline.py                  -- ETL パイプライン（run_daily_etl 等）
  - etl.py                       -- ETLResult の再エクスポート
  - news_collector.py            -- RSS 取得と raw_news 保存
  - quality.py                   -- データ品質チェック
  - calendar_management.py       -- 営業日判定、カレンダー更新ジョブ
  - stats.py                     -- zscore_normalize
  - audit.py                     -- 監査ログ（スキーマ初期化）
- research/
  - __init__.py
  - factor_research.py           -- ファクター計算（momentum/value/vol）
  - feature_exploration.py       -- 将来リターン・IC・統計サマリ
- research/...                    -- その他リサーチユーティリティ

ローカルでの開発・テスト
-----------------------
- 自動環境変数読み込みはプロジェクトルートの .env / .env.local から行われます。テスト時に自動読み込みを避ける場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI 呼び出し等はテストでモック可能（各モジュール内部の _call_openai_api を patch する設計になっています）。

ライセンス / 貢献
-----------------
- この README にライセンス記載がない場合、リポジトリのルートにある LICENSE を参照してください。
- バグ報告・機能提案は issue を立ててください。Pull Request は歓迎します。

補足
----
- ここに記載したコマンドやサンプルは最小限の使用例です。実運用ではロギング、監視、エラーハンドリング、資格情報の安全管理（シークレット管理）を適切に行ってください。