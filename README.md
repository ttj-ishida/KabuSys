KabuSys — 日本株自動売買 / データプラットフォーム
=================================

概要
----
KabuSys は日本株向けのデータプラットフォーム兼リサーチ／自動売買補助ライブラリです。  
主に以下を提供します：

- J-Quants からの株価・財務・マーケットカレンダーの差分 ETL（DuckDB に保存）
- RSS ベースのニュース収集と前処理（SSRF 対策、トラッキング除去）
- OpenAI（gpt-4o-mini）を用いたニュース NLP（銘柄ごとのセンチメント）と市場レジーム判定
- 研究用ファクター計算（モメンタム、バリュー、ボラティリティ等）と統計ユーティリティ
- 監査ログ（signal → order_request → execution のトレース用スキーマ）
- データ品質チェック（欠損・スパイク・重複・日付不整合検出）

主な特徴
--------
- DuckDB ベースで高速なローカル分析と ETL を実現
- J-Quants API 用クライアント（レートリミット・リトライ・トークン自動更新対応）
- ニュース収集時の SSRF/サイズ攻撃対策と冪等保存
- OpenAI の JSON Mode を使った堅牢な LLM 呼び出し（リトライ・レスポンス検証）
- 監査テーブルは冪等で初期化可能（UTC タイムスタンプ、インデックス付き）
- ルックアヘッドバイアス対策：内部では date を明示して過去データのみ参照

導入 & 前提
----------
- Python 3.10+
- 必須パッケージ（例）
  - duckdb
  - openai
  - defusedxml
- （推奨）仮想環境（venv / poetry / pipx 等）

pip でのインストール（開発ソースから）
- リポジトリのルートで：
  - pip install -e ".[dev]" など（pyproject.toml がある想定）
  - または最低限： pip install duckdb openai defusedxml

環境変数（主要）
- JQUANTS_REFRESH_TOKEN : J-Quants リフレッシュトークン（必須：ETL）
- KABU_API_PASSWORD : kabu ステーション API パスワード（発注等がある場合）
- OPENAI_API_KEY : OpenAI 呼び出しに使用（news_nlp / regime_detector）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID : 通知用（任意）
- DUCKDB_PATH : デフォルト data/kabusys.duckdb
- SQLITE_PATH : 監視系 DB（デフォルト data/monitoring.db）
- PAPER_FILL_MODE : paper_trading 模擬約定の挙動（instant/partial/never/reject）
- KABUSYS_ENV : development / paper_trading / live
- LOG_LEVEL : DEBUG / INFO / ...

.env 自動読み込み
- パッケージはプロジェクトルート（.git または pyproject.toml）を検出して .env と .env.local を自動ロードします。
- 自動ロードを無効化したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

セットアップ手順（例）
-------------------
1. リポジトリをクローンして仮想環境を作る
   - git clone ... && cd <repo>
   - python -m venv .venv && source .venv/bin/activate

2. 依存パッケージをインストール
   - pip install -e .        # ローカルパッケージとしてインストール（もし pyproject があれば）
   - または： pip install duckdb openai defusedxml

3. .env を作成
   - .env.example を参考に JQUANTS_REFRESH_TOKEN, OPENAI_API_KEY 等を設定
   - プロジェクトルートに .env / .env.local を置く（自動読み込み対象）

4. データディレクトリを作成（必要に応じて）
   - mkdir -p data

基本的な使い方（コード例）
-------------------------

- DuckDB 接続を作って日次 ETL を実行する

  from datetime import date
  import duckdb
  from kabusys.data.pipeline import run_daily_etl
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  # target_date を省略すると今日の日付で実行する
  res = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(res.to_dict())

- ニュースのセンチメントをスコア化（OpenAI 必須）

  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  n_written = score_news(conn, target_date=date(2026,3,20))
  print(f"scored {n_written} codes")

- 市場レジーム判定（ETF 1321 の MA200 とマクロニュースの合成）

  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect(str(settings.duckdb_path))
  score_regime(conn, target_date=date(2026,3,20))

- 監査データベース初期化

  from pathlib import Path
  import duckdb
  from kabusys.data.audit import init_audit_db
  from kabusys.config import settings

  audit_conn = init_audit_db(settings.duckdb_path)  # 監査用 DB を初期化して接続を返す

主要モジュール / 機能一覧
------------------------
- kabusys.config
  - 環境変数の読み込みと Settings 抽象（自動 .env ロード、必須キー検証）
- kabusys.data
  - etl.py / pipeline.py : 日次 ETL のエントリポイント（run_daily_etl 等）
  - jquants_client.py : J-Quants API クライアント（レート制御・リトライ・保存関数）
  - news_collector.py : RSS 取得・前処理・raw_news への保存（SSRF 対策）
  - calendar_management.py : 市場カレンダーの営業日判定・更新ロジック
  - quality.py : データ品質チェック（欠損・スパイク・重複・日付不整合）
  - audit.py : 監査ログ（signal / order_requests / executions）のDDLと初期化
  - stats.py : z-score 正規化等の統計ユーティリティ
  - pipeline.ETLResult : ETL 実行結果のデータクラス
- kabusys.ai
  - news_nlp.py : ニュースを銘柄ごとに集約し OpenAI でセンチメントを取得・ai_scores へ保存
  - regime_detector.py : ETF 1321 の MA200 とマクロニュース LLM スコアを合成して market_regime へ保存
- kabusys.research
  - factor_research.py : momentum / volatility / value ファクター計算（prices_daily / raw_financials）
  - feature_exploration.py : 将来リターン計算、IC（Spearman）、統計サマリーなど

ディレクトリ構成（抜粋）
-----------------------
src/kabusys/
- __init__.py
- config.py
- ai/
  - __init__.py
  - news_nlp.py
  - regime_detector.py
- data/
  - __init__.py
  - jquants_client.py
  - pipeline.py
  - etl.py
  - news_collector.py
  - calendar_management.py
  - quality.py
  - audit.py
  - stats.py
- research/
  - __init__.py
  - factor_research.py
  - feature_exploration.py
- research/*（その他ユーティリティ）

注意・運用上のポイント
---------------------
- OpenAI 呼び出しは API レート／コストに影響します。テストではモック（patch）して利用してください。
- LLM のレスポンス検証やリトライは実装済みですが、実運用ではログ監視と異常時のフェイルセーフを整備してください（score_news / score_regime は API 失敗時にスコア 0 やスキップで継続します）。
- ETL は差分取得・バックフィルを行いますが、最初の初期ロードや大規模再取得時は J-Quants のレート制限に注意してください。
- DuckDB のバージョン差異により executemany の空リスト扱い等で挙動差が出るため、運用時は依存バージョンを固定することを推奨します。
- audit.init_audit_schema は transactional=True を利用して原子的にスキーマ作成が可能ですが、DuckDB のトランザクション制限に注意してください（ネストトランザクション非対応）。

貢献・開発
----------
- テスト時は環境変数の自動読み込みを抑止できます：
  - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- OpenAI / ネットワークリクエストを含む機能はユニットテストでモック可能な設計にしています（_call_openai_api など）。
- バグや機能追加は issue / PR を作成してください。設計上の方針（ルックアヘッドバイアス対策・冪等性・フォールバック）に沿う実装をお願いします。

ライセンス
---------
（ここにライセンス情報を記載してください。例: MIT / Apache-2.0 等）

付録：よく使うクイックコマンド
----------------------------
- ETL（対話）:
  python -c "import duckdb; from kabusys.data.pipeline import run_daily_etl; from kabusys.config import settings; conn=duckdb.connect(str(settings.duckdb_path)); print(run_daily_etl(conn).to_dict())"
- ニューススコア:
  python -c "import duckdb; from kabusys.ai.news_nlp import score_news; from datetime import date; conn=duckdb.connect('data/kabusys.duckdb'); print(score_news(conn, date(2026,3,20)))"
- レジーム判定:
  python -c "import duckdb; from kabusys.ai.regime_detector import score_regime; from datetime import date; conn=duckdb.connect('data/kabusys.duckdb'); score_regime(conn, date(2026,3,20))"

以上。必要なら README にサンプル .env.example、開発用の Dockerfile / CI 設定、または API レートやコスト見積りの追記を行えます。どの部分を詳しく追記しますか？