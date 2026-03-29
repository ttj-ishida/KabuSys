KabuSys — 日本株自動売買プラットフォーム
=====================================

概要
----
KabuSys は日本株のデータプラットフォーム、リサーチ、AI（ニュースNLP / レジーム判定）、ETL、監査ログ、品質チェック、および注文監視/実行の基盤機能を提供する Python パッケージです。  
設計方針として「ルックアヘッドバイアス防止」「冪等性」「API リトライとレート制御」「DuckDB を使ったローカルデータベース運用」「外部 API 呼び出しのフェイルセーフ化」を重視しています。

主な機能
--------
- データ ETL
  - J-Quants API から株価日足（OHLCV）、財務データ、JPX マーケットカレンダーを差分取得して DuckDB に保存
  - 差分更新・バックフィル・ページネーション対応・トークン自動リフレッシュ・レート制御・冪等保存
- データ品質チェック
  - 欠損、主キー重複、前日比スパイク、日付不整合（未来日/非営業日）等を検出
- ニュース収集
  - RSS フィードの収集・前処理・SSRF 防御・トラッキングパラメータ除去・raw_news への冪等保存
- ニュース NLP（AI）
  - OpenAI（gpt-4o-mini）で銘柄別ニュースセンチメントを算出し ai_scores に保存（バッチ、JSON Mode、再試行ロジックあり）
- 市場レジーム判定
  - ETF（1321）の 200 日 MA 乖離 + マクロニュース LLM センチメントを合成して日次で bull/neutral/bear を判定し market_regime に保存
- 監査ログ（トレーサビリティ）
  - signal_events / order_requests / executions 等の監査テーブル定義と初期化ユーティリティ（DuckDB）
- 研究用ユーティリティ
  - ファクター計算（モメンタム／バリュー／ボラティリティ）、将来リターン、IC 計算、Z スコア正規化等

セットアップ手順
----------------

1. リポジトリをクローン（またはパッケージソースを取得）
   - 例: git clone <repo-url>

2. Python 仮想環境を作成して有効化
   - Unix/macOS:
     - python -m venv .venv
     - source .venv/bin/activate
   - Windows (PowerShell):
     - python -m venv .venv
     - .\.venv\Scripts\Activate.ps1

3. 依存パッケージをインストール
   - 本リポジトリに requirements.txt / pyproject.toml がある想定ですが、最小で以下をインストールしてください:
     - pip install duckdb openai defusedxml
   - 実運用では Slack クライアント等（必要に応じて）も追加してください。

4. 環境変数（.env）を準備
   - プロジェクトルートに .env または .env.local を置くと自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 必須の環境変数（例）
     - JQUANTS_REFRESH_TOKEN=...
     - KABU_API_PASSWORD=...
     - SLACK_BOT_TOKEN=...
     - SLACK_CHANNEL_ID=...
     - OPENAI_API_KEY=...  （AI 関連機能を使う場合）
   - 任意 / デフォルト
     - KABU_API_BASE_URL=http://localhost:18080/kabusapi
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - KABUSYS_ENV=development  （development / paper_trading / live）
     - LOG_LEVEL=INFO

   - 例 (.env)
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     OPENAI_API_KEY=sk-...
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C0123456
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development

5. DuckDB ファイル作成（任意）
   - パッケージ関数で自動作成されます。監査 DB を明示的に初期化する例は下記。

基本的な使い方（コード例）
--------------------------

- 共通準備（DuckDB 接続取得）
  - import duckdb
  - from kabusys.config import settings
  - conn = duckdb.connect(str(settings.duckdb_path))

- ETL（日次パイプライン実行）
  - from kabusys.data.pipeline import run_daily_etl
  - from datetime import date
  - result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  - print(result.to_dict())

- ニュースのスコアリング（AI）
  - from kabusys.ai.news_nlp import score_news
  - from datetime import date
  - n_written = score_news(conn, target_date=date(2026, 3, 20))  # OPENAI_API_KEY は設定済みであること
  - print("書き込んだ銘柄数:", n_written)

- 市場レジーム判定
  - from kabusys.ai.regime_detector import score_regime
  - from datetime import date
  - score_regime(conn, target_date=date(2026, 3, 20))  # market_regime に書き込む

- 監査ログ DB 初期化（専用 DB）
  - from kabusys.data.audit import init_audit_db
  - audit_conn = init_audit_db("data/audit.duckdb")  # 親ディレクトリを自動作成
  - # 必要に応じて専用接続を使って order/exec のログを書く

- データ品質チェックを実行
  - from kabusys.data.quality import run_all_checks
  - issues = run_all_checks(conn, target_date=date(2026, 3, 20))
  - for i in issues: print(i)

運用時の注意点
--------------
- OpenAI 呼び出しは API キーとレート、料金に注意してください。API の失敗はフェイルセーフでスコア 0.0 にフォールバックする等の処理が入っていますが、コストと応答時間を考慮してください。
- DuckDB のバージョン相違により executemany の挙動やリストバインドに差がある場合があります（コード中で対応済みの箇所があります）。
- .env 自動ロードはプロジェクトルート（.git または pyproject.toml を探索）を基準に行います。テストなどで無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- 本パッケージは実際の発注 API との接続を含み得ます（kabuステーション用のパスワード等）。本番運用前に paper_trading 環境で十分に検証してください。

ディレクトリ構成（主要ファイル）
--------------------------------
以下は src/kabusys 配下の主要モジュールと役割の概要です。

- kabusys/
  - __init__.py
  - config.py
    - .env の読み込み、settings（環境変数経由の設定）を提供
  - ai/
    - __init__.py
    - news_nlp.py        — ニュースの LLM ベースセンチメント解析・ai_scores 書き込み
    - regime_detector.py — 市場レジーム判定（MA 乖離 + マクロニュース）
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント、取得・保存ユーティリティ
    - pipeline.py           — ETL パイプライン（run_daily_etl 等）
    - etl.py                — ETLResult 再エクスポート
    - news_collector.py     — RSS 取得・前処理・raw_news への保存
    - calendar_management.py— マーケットカレンダー操作（営業日判定、next/prev 等）
    - stats.py              — zscore_normalize 等の統計ユーティリティ
    - quality.py            — データ品質チェック
    - audit.py              — 監査ログテーブル定義・初期化ユーティリティ
  - research/
    - __init__.py
    - factor_research.py    — モメンタム/ボラティリティ/バリュー等のファクター計算
    - feature_exploration.py— 将来リターン / IC / 統計サマリー等
  - (その他)
    - research パッケージは data.stats を利用してファクター分析を行います

補足（テスト・開発）
-------------------
- テスト時に外部 API 呼び出しをモックすることを強く推奨します。コード中に _call_openai_api や _urlopen 等、モック可能な内部関数が用意されています。
- settings は Settings クラス経由で環境変数を取得します。不足する必須値は ValueError を発生させます。
- KABUSYS_ENV は development / paper_trading / live のいずれかを指定してください。is_live / is_paper / is_dev プロパティで環境フラグを参照できます。

ライセンス / コントリビューション
--------------------------------
- 本リポジトリのライセンス情報や貢献ガイドラインはリポジトリルートに LICENSE / CONTRIBUTING ファイルを置いて管理してください（ここでは省略しています）。

お問い合わせ
----------
不明点や実運用での相談がある場合はリポジトリの issue を立てるか、開発チームの連絡先に問い合わせてください。

以上が本コードベースの README 相当の要約です。必要であれば README に含める具体的な .env.example やコマンド例、CI 用の設定例（GitHub Actions）なども追記できます。どの情報を追記しますか？