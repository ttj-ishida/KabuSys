KabuSys — 日本株自動売買プラットフォーム
====================================

概要
----
KabuSys は日本株向けのデータ基盤・リサーチ・AI評価・監査ログ・ETL を含む自動売買システムのコアライブラリです。  
主な目的は以下です。

- J-Quants から株価・財務・カレンダー等を差分取得して DuckDB に保存する ETL パイプライン
- ニュースを収集して LLM（OpenAI）で銘柄ごとのセンチメントを算出する NLP モジュール
- ETF の移動平均やマクロニュースを組み合わせて市場レジームを判定するモジュール
- ファクター計算・特徴量探索（リサーチ用）
- 監査ログ（signal → order_request → execution）のための DuckDB スキーマ初期化とユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付整合性）

機能一覧
--------
主要な機能と提供モジュール（抜粋）:

- kabusys.config
  - .env / 環境変数の自動読み込み（プロジェクトルート検出）と Settings（必須変数の検証）
  - 自動ロード無効化: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

- kabusys.data
  - pipeline: run_daily_etl などの ETL 実行
  - jquants_client: J-Quants API からの取得 / DuckDB への保存（差分・ページング・リトライ・レートリミット）
  - calendar_management: 営業日判定・カレンダー更新ジョブ
  - news_collector: RSS 収集・前処理・保存（SSRF対策・サイズ制限）
  - quality: データ品質チェック（missing, spike, duplicates, date consistency）
  - audit: 監査ログ用テーブル定義 / 初期化ユーティリティ（init_audit_db, init_audit_schema）
  - stats: zscore 正規化ユーティリティ

- kabusys.ai
  - news_nlp.score_news: ニュースをまとめて OpenAI に投げ、ai_scores テーブルへ書き込み
  - regime_detector.score_regime: ETF（1321）200日MA乖離とマクロニュースの LLM スコアを合成して market_regime に書込

- kabusys.research
  - factor_research: calc_momentum / calc_value / calc_volatility
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank
  - data.stats: zscore_normalize 再利用

セットアップ手順
----------------
1. リポジトリをクローン／取得
   - 例: git clone <repo-url>

2. Python 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存関係をインストール
   - requirements.txt / pyproject.toml がある想定です。プロジェクト仕様に合わせて下記いずれかを実行してください。
     - pip install -e .            （パッケージとしてローカルインストール）
     - pip install -r requirements.txt
     - poetry install

   必須パッケージの例（抜粋）:
   - duckdb
   - openai
   - defusedxml

4. 環境変数 / .env ファイルの準備
   プロジェクトルート（.git または pyproject.toml があるパス）に .env を置くと自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。

   .env の最低サンプル:
   ```
   # J-Quants
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here

   # OpenAI
   OPENAI_API_KEY=sk-...

   # kabuステーション（発注等を行う場合）
   KABU_API_PASSWORD=your_kabu_password
   KABU_API_BASE_URL=http://localhost:18080/kabusapi

   # Slack（通知用）
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C0123456789

   # DB パス等
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   PID_FILE_PATH=data/execution.pid

   # 環境 / ログ
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

   注意:
   - Settings クラスは JQUANTS_REFRESH_TOKEN / SLACK_BOT_TOKEN / SLACK_CHANNEL_ID / KABU_API_PASSWORD を必須としているプロパティがあります。実行する機能に応じて環境変数を設定してください。
   - 自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

使い方（基本例）
----------------

- DuckDB 接続と ETL 実行（日次 ETL）
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- 監査 DB の初期化（監査専用 DB を作る）
  ```python
  from kabusys.data.audit import init_audit_db

  conn = init_audit_db("data/audit.duckdb")
  # conn は DuckDB 接続。init_audit_schema は内部で実行済み。
  ```

- ニュースセンチメントのスコア生成
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  # API キーは環境変数 OPENAI_API_KEY か api_key 引数で指定
  count = score_news(conn, target_date=date(2026, 3, 20))
  print(f"scored stocks: {count}")
  ```

- 市場レジーム判定
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 簡単なリサーチ例（モメンタム計算）
  ```python
  from datetime import date
  import duckdb
  from kabusys.research.factor_research import calc_momentum

  conn = duckdb.connect("data/kabusys.duckdb")
  res = calc_momentum(conn, date(2026, 3, 20))
  print(len(res), "records")
  ```

設定 / 環境変数一覧（主なもの）
----------------------------
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須：データ ETL や listed info などで使用）
- OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector で必須）
- KABU_API_PASSWORD: kabuステーション API のパスワード（発注機能を使う場合）
- KABU_API_BASE_URL: kabu API ベース URL（デフォルト http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN / SLACK_CHANNEL_ID: Slack 通知用
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: sqlite（監視用）パス（デフォルト data/monitoring.db）
- PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT: 監視用設定
- KABUSYS_ENV: 開発/紙取引/本番 ("development" | "paper_trading" | "live")
- LOG_LEVEL: ログレベル ("DEBUG" | "INFO" | ...)

運用上の注意
-------------
- Look-ahead バイアス防止:
  - AI / リサーチモジュールはいずれも内部で date を引数で受け取り、datetime.today() を直接参照しない設計になっています。バッチ / バックテストで target_date を明示して使用してください。
- OpenAI 呼び出し:
  - gpt-4o-mini を想定した JSON Mode を利用しています。API のレートやコストに注意してください。エラーや不正応答時はフェイルセーフ（多くの場合スコア0.0 を利用）で動作します。
- J-Quants API:
  - モジュール側でレートリミット（120 req/min）制御・リトライ・トークン自動リフレッシュを実装しています。ID トークンは内部キャッシュされるため、ページネーション間で再利用されます。
- セキュリティ:
  - news_collector では SSRF 対策・レスポンスサイズ制限・トラッキングパラメータ除去等を実施しています。
- DuckDB executemany の空リスト挙動に注意（コード内でガードされています）。

ディレクトリ構成（主要ファイル）
-------------------------------
src/kabusys/
- __init__.py
- config.py                  — 環境変数・設定管理
- ai/
  - __init__.py
  - news_nlp.py              — ニュース NLP（score_news）
  - regime_detector.py       — 市場レジーム判定（score_regime）
- data/
  - __init__.py
  - pipeline.py              — ETL パイプライン（run_daily_etl 等）
  - etl.py                   — ETL インターフェース（ETLResult 再エクスポート）
  - jquants_client.py        — J-Quants API クライアント + 保存関数
  - calendar_management.py   — 市場カレンダー管理
  - news_collector.py        — RSS 収集・前処理
  - quality.py               — データ品質チェック
  - stats.py                 — zscore_normalize 等
  - audit.py                 — 監査ログスキーマ定義 / 初期化
- research/
  - __init__.py
  - factor_research.py       — ファクター計算（momentum/value/volatility）
  - feature_exploration.py   — 将来リターン・IC・サマリー等
- monitoring/ (想定: 監視/実行モジュールは別に実装)
- execution/ (想定: 発注・ブローカー連携モジュール)
- strategy/ (想定: 戦略モデル・シグナル生成)
- monitoring/（別途モジュール）

FAQ / よくある質問
------------------
Q: .env を自動で読み込ませたくない
A: 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。load を抑制します。

Q: OpenAI / J-Quants が途中でエラーになるが処理は中断されない？
A: 多くの箇所でフェイルセーフが組み込まれており（例: LLM 失敗時は 0.0 フォールバック、ETL ステップは個別に例外処理）、部分失敗でも他処理を継続します。ログを参照して問題を確認してください。

Q: DuckDB のスキーマはどこで定義されている？
A: audit.py に監査用スキーマ定義があり、ETL / jquants_client の保存先テーブルはプロジェクト内ドキュメント（DataPlatform.md 想定）に従って設計されています。初期化関数を実行してスキーマを作成してください。

ライセンス / 貢献
-----------------
（ここにライセンスや貢献方法を記載してください。例: MIT / コントリビュート方法）

最後に
------
この README はコードベースの主要な機能とセットアップ／利用方法の概要を示しています。詳細な API 仕様や実運用の手順（監視、ログローテーション、バックテストでのデータスナップショット保持など）はプロジェクト内のドキュメント（DataPlatform.md, StrategyModel.md 等）やコードコメントを参照してください。必要なら README を拡張して CI/CD、デプロイ手順、モニタリングの具体例を追加できます。