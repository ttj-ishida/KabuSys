KabuSys — 日本株データパイプライン & リサーチ/AIユーティリティ
=============================================================================

概要
----
KabuSys は日本株向けのデータパイプライン、ファクター研究、ニュースNLP（LLMベースのセンチメント解析）、市場レジーム判定、および監査ログ初期化等のユーティリティを提供するライブラリ群です。本リポジトリは ETL（J-Quants 連携）、ニュース収集、品質チェック、リサーチ用ファクター計算、LLM を用いたニューススコアリング等を含みます。実際の注文送信（ブローカー連携）機能は本コードベースの一部（audit 用スキーマ等）は含みますが、運用前に十分なレビューと安全対策が必要です。

主な機能
--------
- 環境設定管理
  - .env / .env.local を自動読み込み（プロジェクトルート検出）
  - 必須環境変数取得時の検証

- データ ETL（J-Quants 連携）
  - 株価日足（OHLCV）・財務データ・JPX カレンダー取得（ページネーション・レート制御・リトライ対応）
  - DuckDB への冪等保存（ON CONFLICT）
  - 日次 ETL パイプライン（差分取得 / バックフィル / 品質チェック）

- ニュース収集
  - RSS フィード取得（SSRF 対策・サイズ制限・前処理）
  - raw_news / news_symbols への冪等保存ロジック

- データ品質チェック
  - 欠損（OHLC）検出、スパイク検知、重複検出、日付不整合検出
  - QualityIssue を返し、呼び出し元で扱える設計

- 研究用ユーティリティ
  - ファクター計算（モメンタム、ボラティリティ、バリュー等）
  - 将来リターン計算、IC（情報係数）計算、ファクター統計サマリ
  - Zスコア正規化ユーティリティ

- LLM（OpenAI）連携
  - ニュース毎の銘柄単位センチメント（gpt-4o-mini など、JSON mode を期待）
  - マクロニュースから市場レジーム判定（ma200 と LLM センチメントの合成）
  - 再試行・フォールバック挙動を明示（API失敗時はフォールバック値で継続）

- 監査ログスキーマ初期化
  - signal_events / order_requests / executions の監査テーブル作成ユーティリティ
  - init_audit_db: 監査用 DuckDB DB 初期化（UTC タイムゾーン固定）

動作環境（推奨）
----------------
- Python 3.10 以上（PEP 604 の型合成 (A | B) を使用）
- 主要依存パッケージ:
  - duckdb
  - openai (OpenAI の Python SDK、API 呼び出しに使用)
  - defusedxml (RSS パースの安全化)
- 標準ライブラリ: urllib, json, logging, datetime 等

セットアップ手順
----------------
1. リポジトリをクローン / 展開
   - プロジェクトルートに .git または pyproject.toml が存在すると自動で .env を読み込みます。

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Linux/macOS)
   - .venv\Scripts\activate     (Windows)

3. 依存パッケージのインストール
   - pip install duckdb openai defusedxml
   - （プロジェクトに pyproject.toml / requirements.txt がある場合はそちらを利用）

4. 環境変数 (.env) の準備
   - プロジェクトルートに .env または .env.local を配置できます（.env.local は .env を上書き）。
   - 必須サンプル（.env.example を参考にしてください）:
     - JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     - KABU_API_PASSWORD=your_kabu_api_password
     - SLACK_BOT_TOKEN=your_slack_token
     - SLACK_CHANNEL_ID=your_slack_channel
     - OPENAI_API_KEY=your_openai_api_key
   - DB パスのデフォルト:
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db

5. 自動 .env 読み込みの無効化（テスト時など）
   - 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロードをスキップします。

使い方（簡単な例）
------------------

1) 設定取得（環境変数）
   - from kabusys.config import settings
   - token = settings.jquants_refresh_token

   未設定の必須環境変数を参照すると ValueError が発生します。

2) DuckDB 接続を作成して日次 ETL を実行
   - import duckdb
     from kabusys.data.pipeline import run_daily_etl
     from kabusys.config import settings
     from datetime import date

     conn = duckdb.connect(str(settings.duckdb_path))
     result = run_daily_etl(conn, target_date=date.today())
     print(result.to_dict())

   run_daily_etl は ETLResult を返します。内部で市場カレンダー、株価、財務を差分取得し、品質チェックを実行します。

3) ニュースの LLM スコアリング（ai -> news_nlp）
   - from kabusys.ai.news_nlp import score_news
     from datetime import date

     count = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
     # api_key を None にすると環境変数 OPENAI_API_KEY を利用

   score_news は ai_scores テーブルへスコアを書き込み、書き込んだ銘柄数を返します。

4) 市場レジーム判定（ai -> regime_detector）
   - from kabusys.ai.regime_detector import score_regime
     from datetime import date

     res = score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
     # 成功時は 1 を返します（market_regime テーブルへ書き込み）

   OpenAI API失敗などはフォールバック（macro_sentiment=0.0）して継続しますが、APIキー未設定時は ValueError。

5) 監査用 DuckDB の初期化
   - from kabusys.data.audit import init_audit_db
     conn_audit = init_audit_db("data/audit.duckdb")
   - 上記で signal_events / order_requests / executions を含む監査スキーマが作成されます。

注意事項 / トラブルシューティング
---------------------------------
- 環境変数が不足している場合、Settings のプロパティが ValueError を送出します。必須値を .env に設定してください。
- OpenAI 関係:
  - API 呼び出しはリトライやバックオフを行いますが、APIキーが無いと ValueError になります。
  - LLM のレスポンスが期待フォーマットでない場合、その銘柄はスキップされる設計です。
- J-Quants API:
  - レート制御（120 req/min）や 401 の自動リフレッシュ等を実装しています。
  - get_id_token でリフレッシュトークンを利用します。refresh token を .env に設定してください。
- RSS フィード取得:
  - SSRF 対策、レスポンスサイズ制限、gzip 解凍後の上限検査などの防御を実装しています。
- DuckDB の executemany(): 一部コードで空リストを渡すと DuckDB のバージョン依存で失敗するため、空チェックを行っています。

ディレクトリ構成（主要ファイル）
-------------------------------
src/kabusys/
- __init__.py                — パッケージ初期化（version 等）
- config.py                  — 環境変数・設定管理
- ai/
  - __init__.py
  - news_nlp.py              — ニュースの LLM スコアリング（ai_scores 書込）
  - regime_detector.py       — マクロ + MA200 で市場レジーム判定（market_regime 書込）
- data/
  - __init__.py
  - calendar_management.py   — 市場カレンダー / 営業日判定 / 更新ジョブ
  - pipeline.py              — ETL パイプライン（run_daily_etl 他）
  - etl.py                   — ETLResult の再エクスポート
  - jquants_client.py        — J-Quants API クライアント / 保存ロジック
  - news_collector.py        — RSS 取得・前処理・記事ID生成
  - quality.py               — データ品質チェック（各種チェック）
  - stats.py                 — 汎用統計ユーティリティ（Zスコア等）
  - audit.py                 — 監査ログテーブル定義と初期化
- research/
  - __init__.py
  - factor_research.py       — Momentum/Value/Volatility 等のファクター計算
  - feature_exploration.py   — 将来リターン、IC、統計サマリー、ランク関数等
- (その他)
  - monitoring, strategy, execution 等は __all__ に定義がありますが、このコードベースに含まれる主要モジュールは上記です。

開発 / テストに関する補足
-------------------------
- .env の自動ロードはプロジェクトルート（.git または pyproject.toml）を基準に行います。テスト環境では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセットして自動ロードを無効化できます。
- LLM / 外部 API 呼び出し部分はテストでモック化しやすいように内部呼び出しを分離しています（例: _call_openai_api のパッチ）。
- DuckDB を用いているためローカルで簡単にデータベースを作成して単体検証できます（:memory: 接続もサポート）。

ライセンス
---------
（プロジェクト固有のライセンス情報をここに記載してください）

最後に
------
この README はコードベースの概要と主要な利用法をまとめたものです。実際の運用や自動売買にはさらなる安全対策（冪等性検証、注文監査、リスク管理、SLACK/外部通知の確認等）が必要です。追加ドキュメントや API 使用例が必要であれば、どの章を詳しくしたいか教えてください。