KabuSys — 日本株自動売買プラットフォーム（README）
=================

概要
----
KabuSys は日本株向けのデータパイプライン、ファクター解析、ニュースNLP、マーケットレジーム判定、監査ログおよび J-Quants / kabu ステーション 等の外部 API と連携するためのライブラリ群です。本コードベースは ETL（J-Quants） → データ品質チェック → ファクター計算 → ニュースセンチメント評価 → 戦略／監視／監査ログ保存までを想定したモジュール設計になっています。

主な特徴（機能一覧）
------------------
- データ取得・ETL
  - J-Quants から株価日足 / 財務データ / 市場カレンダーを差分取得（ページネーション、レート制御、再試行、トークン自動更新）
  - DuckDB に対する冪等保存（ON CONFLICT DO UPDATE）
  - デイリー ETL パイプライン（run_daily_etl）

- データ品質チェック
  - 欠損（OHLC）検出、スパイク検出（前日比閾値）、重複チェック、日付不整合チェック
  - QualityIssue オブジェクトで結果を収集

- ニュース収集 / NLP
  - RSS フィード収集（SSRF 対策、URL 正規化、最大サイズ制限、トラッキングパラメータ除去）
  - OpenAI を使った銘柄別ニュースセンチメント（score_news）
  - ニュースウィンドウ（前日 15:00 JST 〜 当日 08:30 JST）設計でルックアヘッド回避

- 市場レジーム判定
  - ETF 1321 の 200 日 MA 乖離（70%）とマクロニュース LLM（30%）を合成して日次の市場レジーム（bull/neutral/bear）判定（score_regime）
  - OpenAI 呼び出しのリトライ・フォールバック実装

- 研究用ユーティリティ
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - 将来リターン計算、IC（Spearman）計算、ランク・正規化ユーティリティ

- 監査ログ（トレーサビリティ）
  - signal_events / order_requests / executions 等の監査テーブル作成ユーティリティ（init_audit_schema / init_audit_db）
  - すべての注文フローを UUID によるチェーンで追跡可能にする設計

セットアップ手順
--------------
前提
- Python 3.10 以上（型ヒントの union 型（|）を使用しています）
- システムに network access（J-Quants / OpenAI 等）可能であること

1. リポジトリをクローン
   - 例: git clone <リポジトリURL>

2. 仮想環境（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - requirements ファイルがある場合: pip install -r requirements.txt
   - 主要依存（参考）:
     - duckdb
     - openai
     - defusedxml
   - 開発インストール（パッケージとして利用する場合）:
     - pip install -e .

4. 環境変数 / .env の準備
   - プロジェクトルートに .env または .env.local を置くと自動読み込みされます（デフォルト）。
   - 自動ロードを無効化する場合は環境変数を設定:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

必須環境変数（主なもの）
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード
- SLACK_BOT_TOKEN — Slack 通知用ボットトークン
- SLACK_CHANNEL_ID — Slack 通知先チャンネルID
- OPENAI_API_KEY — OpenAI API キー（score_news / score_regime で使用）

任意（デフォルトあり）
- KABU_API_BASE_URL (default: http://localhost:18080/kabusapi)
- DUCKDB_PATH (default: data/kabusys.duckdb)
- SQLITE_PATH (default: data/monitoring.db)
- PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
- KABUSYS_ENV (development / paper_trading / live)
- LOG_LEVEL (DEBUG/INFO/...)

例 .env（抜粋）
- JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
- OPENAI_API_KEY=sk-...
- KABU_API_PASSWORD=your_kabu_pass
- SLACK_BOT_TOKEN=xoxb-...
- SLACK_CHANNEL_ID=C01234567
- DUCKDB_PATH=data/kabusys.duckdb

使い方（サンプル）
-----------------

基本的な DuckDB 接続と ETL 実行（対話 or スクリプト）
- Python スクリプト例:

  from datetime import date
  import duckdb
  from kabusys.config import settings
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect(str(settings.duckdb_path))
  # ETL 実行（target_date を省略すると今日）
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())

ニュースセンチメント（score_news）
- 前提: OpenAI API キーが設定されていること
  from datetime import date
  import duckdb
  from kabusys.config import settings
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect(str(settings.duckdb_path))
  count = score_news(conn, target_date=date(2026, 3, 20))
  print(f"scored {count} symbols")

市場レジーム判定（score_regime）
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect(str(settings.duckdb_path))
  score_regime(conn, target_date=date(2026, 3, 20))

監査DB 初期化（独立した監査用 DB）
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  # これで signal_events / order_requests / executions テーブルが作成される

ニュースRSS 取得（単体テストや収集処理）
  from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES
  articles = fetch_rss(DEFAULT_RSS_SOURCES["yahoo_finance"], source="yahoo_finance")

ログレベル・環境
- settings.log_level / settings.env を参照してアプリの挙動（本番/ペーパー）を切り替えます。
- settings.is_live / is_paper / is_dev で判定可能。

注意点（設計上の重要ポイント）
- ルックアヘッドバイアス対策: 各モジュールは内部で date.today() を使ってバックテストに混入しないよう設計されています。target_date を明示して使用してください。
- フェイルセーフ: 多くの外部 API 呼び出しは失敗時に例外で停止させずフォールバック値（例: macro_sentiment=0）で継続する実装になっています。
- DuckDB への executemany は空リストのときに問題となるバージョン差異を考慮しています（空時はスキップ）。

ディレクトリ構成（主要ファイル）
-----------------------------
src/kabusys/
- __init__.py
- config.py                 — 環境変数 / .env 自動読み込みと Settings
- ai/
  - __init__.py
  - news_nlp.py             — ニュースセンチメント（OpenAI 呼び出し・チャンク化）
  - regime_detector.py      — 市場レジーム判定（マクロ + MA200）
- data/
  - __init__.py
  - calendar_management.py  — 市場カレンダー管理・営業日判定
  - etl.py                  — ETL の公開インターフェース（ETLResult）
  - pipeline.py             — ETL パイプラインの実装（run_daily_etl 等）
  - stats.py                — zscore_normalize 等の統計ユーティリティ
  - quality.py              — データ品質チェック（QualityIssue）
  - audit.py                — 監査ログスキーマ作成 / init_audit_db
  - jquants_client.py       — J-Quants API クライアント（取得・保存）
  - news_collector.py       — RSS ニュース収集（SSRF 対策・正規化）
- research/
  - __init__.py
  - factor_research.py      — モメンタム / ボラティリティ / バリューの計算
  - feature_exploration.py  — forward returns / IC / summary / rank
- research/ 以下は研究用ユーティリティを再エクスポート

付記
----
- このリポジトリはデータ取得や外部API呼び出しが中心のため、公開 API（CLI や Web UI）は含まれていません。上記の関数群を組み合わせてジョブ（バッチ）や監視プロセスを実装して利用してください。
- OpenAI の呼び出し周りは SDK のバージョンに依存する場合があります。SDK の変更（response の構造等）に注意して下さい。
- 実運用では KABUSYS_ENV を適切に設定（paper_trading / live）し、ログ出力・監視設定を整えてください。

問題報告・貢献
----------------
バグ報告や機能提案は Issues を立ててください。プルリクエストは歓迎します。テストやドキュメントの追加も非常に助かります。

以上。必要であればサンプルスクリプト（より詳しい使用例）や .env.example を作成して追記します。どの部分を詳しく示しますか？