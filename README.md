KabuSys — 日本株自動売買プラットフォーム（README）
=================================

概要
----
KabuSys は日本株向けのデータプラットフォームと自動売買／リサーチ用ライブラリ群です。  
主に以下の役割を担います:

- J-Quants API からのデータ ETL（株価・財務・市場カレンダー）
- ニュース収集と LLM によるニュースセンチメント算出
- 市場レジーム判定（MA と LLM を組み合わせた判定）
- ファクター計算・特徴量探索（Research 用）
- データ品質チェック、監査ログ（発注〜約定のトレーサビリティ）
- DuckDB を主体としたローカルデータ管理

主な機能一覧
--------------
- ETL パイプライン（kabusys.data.pipeline）
  - 日次 ETL（run_daily_etl）で calendar / prices / financials を差分取得・保存
  - 個別 ETL ジョブ（run_prices_etl, run_financials_etl, run_calendar_etl）
  - ETL 実行結果を ETLResult で返却
- データクライアント（kabusys.data.jquants_client）
  - J-Quants API からの取得・保存（ページネーション、リトライ、レート制御）
- ニュース収集（kabusys.data.news_collector）
  - RSS 取得、正規化、raw_news への冪等保存、銘柄紐付け
  - SSRF 対策、サイズ制限、トラッキングパラメータ除去などの安全策を備える
- ニュース NLP（kabusys.ai.news_nlp）
  - gpt-4o-mini を用いた銘柄ごとのニュースセンチメント算出（score_news）
  - バッチ処理、リトライ、レスポンス検証、ai_scores への保存
- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF 1321 の 200 日 MA 乖離（70%）とマクロニュース LLM センチメント（30%）を合成して日次レジーム判定（bull/neutral/bear）
- 研究・ファクター（kabusys.research）
  - momentum/volatility/value 等のファクター計算
  - forward returns / IC / 統計サマリ等のユーティリティ
- データ品質チェック（kabusys.data.quality）
  - 欠損・重複・スパイク・日付不整合チェック
- 監査ログ（kabusys.data.audit）
  - signal / order_request / executions 等の監査テーブル作成・初期化

セットアップ手順
----------------
前提:
- Python 3.10+（typing | match 機能などを利用）
- duckdb インストール済み
- OpenAI API キー、J-Quants のリフレッシュトークン 等の外部サービス資格情報

1. リポジトリをクローン / パッケージをインストール
   - 開発中はソースを直接参照する想定:
     - pip install -e . などでローカルインストールしてください。

2. 必要な環境変数（.env）を作成
   - プロジェクトルートに .env または .env.local を置くと自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 主なキー（プロジェクトで参照される必須設定）:
     - JQUANTS_REFRESH_TOKEN … J-Quants のリフレッシュトークン（ETL 用）
     - KABU_API_PASSWORD … kabuステーション API 接続パスワード（実運用での発注用）
     - SLACK_BOT_TOKEN … Slack 通知用 Bot トークン
     - SLACK_CHANNEL_ID … Slack 通知先チャンネル ID
     - OPENAI_API_KEY … OpenAI 呼び出しに使用（news_nlp / regime_detector）
   - 例（.env）:
     JQUANTS_REFRESH_TOKEN=xxx
     OPENAI_API_KEY=sk-...
     KABU_API_PASSWORD=...
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567

3. データベース用ディレクトリを作成（任意）
   - デフォルトの DuckDB パスは data/kabusys.duckdb（settings.duckdb_path）
   - 必要に応じてディレクトリを作成：mkdir -p data

4. 依存ライブラリ
   - OpenAI SDK、duckdb、defusedxml などが必要です。requirements.txt を用意している場合はそれを使ってください。
   - 例:
     pip install duckdb openai defusedxml

使い方（簡易例）
----------------

- 設定確認
  from kabusys.config import settings
  print(settings.duckdb_path, settings.env, settings.is_live)

- DuckDB 接続作成と日次 ETL 実行
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())

- ニュースセンチメント算出（score_news）
  from datetime import date
  from kabusys.ai.news_nlp import score_news
  conn = duckdb.connect(str(settings.duckdb_path))
  n_written = score_news(conn, target_date=date(2026,3,20), api_key=None)  # api_key None なら環境変数 OPENAI_API_KEY を使用
  print("scored:", n_written)

- 市場レジーム判定（score_regime）
  from datetime import date
  from kabusys.ai.regime_detector import score_regime
  conn = duckdb.connect(str(settings.duckdb_path))
  score_regime(conn, target_date=date(2026,3,20), api_key=None)

- 監査 DB 初期化（発注/約定の監査テーブルを作る）
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")  # ":memory:" も可

- 研究向けユーティリティ（例: momentum）
  from kabusys.research.factor_research import calc_momentum
  conn = duckdb.connect(str(settings.duckdb_path))
  records = calc_momentum(conn, target_date=date(2026,3,20))

注意事項・トラブルシューティング
--------------------------------
- 環境変数の自動ロード:
  - パッケージ起点の親ディレクトリから .env / .env.local を自動ロードします（.git または pyproject.toml をプロジェクトルート判定に使用）。
  - 自動ロードを無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト用途など）。
- OpenAI 呼び出し:
  - API 呼び出しはリトライ / バックオフを備えますが、API キーや使用制限に注意してください。
- J-Quants API:
  - rate-limit（120 req/min）を想定した制御が実装されていますが、運用時はアカウント制限に注意してください。
- DuckDB 用 SQL 注意:
  - DuckDB のバージョン差異で executemany の空リストバインドや配列バインドが不安定な場合があるため、モジュール内で互換性対策が施されています。

ディレクトリ構成（主要ファイル）
------------------------------
src/kabusys/
- __init__.py
- config.py                       — 環境変数 / 設定管理
- ai/
  - __init__.py
  - news_nlp.py                    — ニュース NLP / score_news
  - regime_detector.py             — 市場レジーム判定 / score_regime
- data/
  - __init__.py
  - jquants_client.py              — J-Quants API クライアント & 保存関数
  - pipeline.py                    — ETL パイプライン（run_daily_etl 等）
  - etl.py                         — ETL の公開型（ETLResult）
  - news_collector.py              — RSS ニュース収集
  - calendar_management.py         — 市場カレンダー関連ユーティリティ
  - quality.py                     — データ品質チェック
  - stats.py                       — 共通統計ユーティリティ（zscore_normalize 等）
  - audit.py                       — 監査ログスキーマ初期化
- research/
  - __init__.py
  - factor_research.py             — ファクター計算（momentum/value/volatility）
  - feature_exploration.py         — forward returns / IC / summary
- ai/、data/、research/ 以下に関連するユーティリティ群が含まれます。

開発者向けメモ
--------------
- look-ahead bias を避ける設計:
  - 多くの関数（ETL / scoring / regime 判定 / feature 計算）は内部で date.today() を直接参照せず、caller が target_date を明示的に渡す設計です。バックテストや過去検証で安全に使えます。
- テストしやすさ:
  - OpenAI やネットワーク部分は内部でラッパー関数を用意しており、unittest.mock.patch で差し替えてテストが可能です。
- 冪等性:
  - ETL の保存処理は ON CONFLICT DO UPDATE（冪等）を多用しています。部分失敗時の被害を最小化する設計がされてます。

ライセンス・貢献
----------------
この README はコードベースから生成されたドキュメントの概要です。実運用や公開時はライセンスやセキュリティポリシーを整備してください。

以上。必要であれば、各モジュールの詳細な API リファレンス（関数シグネチャ・戻り値例・DB スキーマ）を別ドキュメントとして作成します。どのモジュールの詳細が必要か教えてください。