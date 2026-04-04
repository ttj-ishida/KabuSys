KabuSys
=======

日本株向けの自動売買 / データプラットフォーム用ライブラリ群です。  
DuckDB をバックエンドにしてデータ取得（J-Quants）、ETL、品質チェック、ニュースの NLP スコアリング、LLM を用いた市場レジーム判定、リサーチ用ファクター計算、監査ログ（発注→約定のトレーサビリティ）などを提供します。

特徴
----
- J-Quants API による株価・財務・カレンダーの差分 ETL（ページネーション・レート制御・自動トークンリフレッシュ付き）
- DuckDB を用いたローカル永続化（冪等保存、ON CONFLICT 処理）
- データ品質チェック（欠損・スパイク・重複・日付整合性）
- RSS ニュース収集（SSRF 対策、トラッキングパラメータ除去、前処理）
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント（銘柄別）およびマクロセンチメント（市場レジーム）評価（JSON Mode を利用）
- 研究用途のファクター計算（モメンタム・バリュー・ボラティリティ）と特徴量探索（将来リターン・IC・統計サマリ）
- 監査ログテーブル（signal_events / order_requests / executions）とイニシャライズユーティリティ
- 設定は環境変数（.env / .env.local）から自動読み込み（プロジェクトルートの検出あり、無効化も可能）

要求事項 / 推奨環境
-------------------
- Python 3.10 以上（typing の新記法を使用）
- 必須ライブラリ（例）
  - duckdb
  - openai
  - defusedxml
- 標準ライブラリで HTTP/URL 操作は urllib を利用（requests は不要）

インストール
------------
1. リポジトリをクローン
   - git clone <リポジトリURL>
2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  または  .venv\Scripts\activate
3. 必要パッケージをインストール（例）
   - pip install duckdb openai defusedxml
   - またはプロジェクトに requirements.txt / pyproject.toml があればそちらを利用
4. 開発インストール（パッケージとして使う場合）
   - pip install -e .

環境変数（.env）について
------------------------
- ルートディレクトリ（.git または pyproject.toml がある最上位）を探し、.env および .env.local を自動で読み込みます。
  - 読み込み優先度: OS 環境 > .env.local > .env
  - 自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定
- 主要な環境変数（例）
  - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
  - OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector で使用）
  - KABU_API_PASSWORD: kabu API のパスワード
  - KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
  - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: LINE 通知関連
  - DUCKDB_PATH: デフォルト DB パス（data/kabusys.duckdb）
  - SQLITE_PATH: 監視用 SQLite（data/monitoring.db）
  - KABUSYS_ENV: development / paper_trading / live
  - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL

簡単なセットアップ例 (.env)
---------------------------
例（プロジェクト直下の .env）:
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxx
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO

使い方（主要機能）
-----------------

1) DuckDB 接続を作る（例）
- Python REPL やスクリプトで:
  from pathlib import Path
  import duckdb
  from kabusys.config import settings
  db_path = settings.duckdb_path  # Path オブジェクト
  conn = duckdb.connect(str(db_path))

2) 日次 ETL（prices / financials / calendar / 品質チェック）
- run_daily_etl を使用:
  from kabusys.data.pipeline import run_daily_etl
  from datetime import date
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())

3) ニュースの NLP スコアリング（銘柄別 ai_scores への書込み）
- score_news:
  from kabusys.ai.news_nlp import score_news
  from datetime import date
  n_written = score_news(conn, target_date=date(2026,3,20), api_key=None)  # env OPENAI_API_KEY を使う

4) 市場レジーム判定（ma200 とマクロセンチメントを合成）
- score_regime:
  from kabusys.ai.regime_detector import score_regime
  from datetime import date
  res = score_regime(conn, target_date=date(2026,3,20), api_key=None)

5) リサーチ用ファクター計算
- モメンタム / ボラティリティ / バリュー:
  from kabusys.research.factor_research import calc_momentum, calc_volatility, calc_value
  from datetime import date
  mom = calc_momentum(conn, date(2026,3,20))
  vol = calc_volatility(conn, date(2026,3,20))
  val = calc_value(conn, date(2026,3,20))

- 正規化ユーティリティ:
  from kabusys.data.stats import zscore_normalize
  normalized = zscore_normalize(mom, ["mom_1m","mom_3m","mom_6m"])

6) 監査ログ（監査DB初期化）
- 監査用 DuckDB を初期化:
  from kabusys.data.audit import init_audit_db
  conn_audit = init_audit_db("data/audit.duckdb")

注意点 / 実運用に関する補足
------------------------
- OpenAI 呼び出しは外部 API のため失敗やレート制限に備えたリトライやフォールバック（スコア 0.0）処理を実装しています。テストでは各モジュール内の _call_openai_api をモックできます。
- J-Quants API のリクエストはレート制御と 401 自動リフレッシュ対応を行います。refresh token の管理を正しく行ってください。
- DuckDB への一括書き込みでは executemany に空リストを渡すと不具合があることを考慮しています（モジュール内で対処済み）。
- ETL / スコアリング関数は内部で datetime.today() や date.today() を直接参照しない設計（ルックアヘッドバイアス対策）です。バックテストでは target_date を明示的に指定してください。
- .env のクォート・コメント処理はかなり厳密にパースされます。必要に応じて .env.local を使って上書きしてください。

ディレクトリ構成（主要ファイル）
-------------------------------
src/kabusys/
- __init__.py                         — パッケージ定義 (version)
- config.py                           — 環境変数・設定管理（.env 自動読込、Settings オブジェクト）
- ai/
  - __init__.py                       — ai モジュールの公開関数
  - news_nlp.py                       — ニュースセンチメント（銘柄別）スコアリング（OpenAI）
  - regime_detector.py                — 市場レジーム判定（ETF ma200 + マクロセンチメントの合成）
- data/
  - __init__.py
  - calendar_management.py            — 市場カレンダー管理（営業日判定 / カレンダー更新ジョブ）
  - etl.py                            — ETL の再エクスポート（ETLResult）
  - pipeline.py                       — ETL パイプライン（prices/financials/calendar / 品質チェック）
  - stats.py                          — 統計ユーティリティ（Zスコア等）
  - quality.py                        — データ品質チェック（欠損・スパイク・重複・日付不整合）
  - audit.py                          — 監査ログテーブル定義・初期化ユーティリティ
  - jquants_client.py                 — J-Quants API クライアント（取得 + 保存）
  - news_collector.py                 — RSS 取得・前処理・raw_news 保存
- research/
  - __init__.py
  - factor_research.py                 — ファクター計算（momentum/value/volatility）
  - feature_exploration.py             — 将来リターン / IC / 統計サマリ 等

トップレベルの利用例（まとめ）
-----------------------------
- ETL 実行（例）
  from kabusys.config import settings
  import duckdb
  from kabusys.data.pipeline import run_daily_etl
  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn)
  print(result.to_dict())

- ニューススコアリング
  from kabusys.ai.news_nlp import score_news
  score_news(conn, target_date=date(2026,3,20))

- レジーム判定
  from kabusys.ai.regime_detector import score_regime
  score_regime(conn, target_date=date(2026,3,20))

開発 / テスト
--------------
- OpenAI 呼び出しや外部 HTTP はユニットテストでモックしやすい設計（モジュール内の _call_openai_api や _urlopen などを patch 可能）。
- .env 自動読込をテストで無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

ライセンス / コントリビューション
----------------------------------
（ここにプロジェクトのライセンス情報やコントリビューション方法を追記してください）

以上。必要があれば README に例コマンドや詳しい schema 定義、SQL スキーマ（DDL）サンプル、運用手順（cron / systemd での ETL 実行、監視）などを追加できます。どの情報を優先して追加しますか？