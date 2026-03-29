KabuSys — 日本株自動売買 / データプラットフォーム
================================

概要
----
KabuSys は日本株のデータ収集・品質チェック・ファクター計算・AI（LLM）を用いたニュースセンチメント評価・市場レジーム判定・監査ログ管理を行うライブラリ群です。  
主に ETL（J-Quants などからのデータ取得）、データ品質検査、研究用ファクター計算、ニュースセンチメント（OpenAI）連携、監査（発注→約定のトレーサビリティ）を想定したモジュール群を含みます。

想定用途の例:
- 日次 ETL（株価・財務・カレンダー）を自動実行して DuckDB に保存
- ニュースから銘柄別センチメントを生成し ai_scores に書き込み
- 市場レジーム（bull/neutral/bear）を判定して market_regime に保存
- 研究用途におけるファクター計算・IC/前方リターン分析
- 発注〜約定までを追跡可能にする監査テーブルの初期化

主な機能一覧
-------------
- 環境設定管理（.env/.env.local の自動読み込み、Settings API）
- J-Quants API クライアント（差分取得・ページネーション・トークン自動リフレッシュ・DuckDB へ冪等保存）
- ETL パイプライン（run_daily_etl / 個別 ETL ジョブ）
- データ品質チェック（欠損・重複・スパイク・日付不整合検出）
- ニュース収集（RSS, SSRF 対策, 前処理, raw_news 保存）
- ニュース NLP（OpenAI を用いた銘柄別センチメント / ai_scores への書き込み）
- 市場レジーム判定（ETF 1321 の MA とマクロ記事の LLM 評価を合成）
- 研究モジュール（モメンタム / バリュー / ボラティリティ等のファクター、前方リターン、IC、統計サマリー）
- 監査ログ（signal_events, order_requests, executions テーブルとインデックス、初期化ユーティリティ）

動作環境・依存
---------------
- Python 3.10+
  - 理由: 型ヒントに X | Y 形式や typing の機能を利用しています。
- 主要依存パッケージ（最小限）:
  - duckdb
  - openai
  - defusedxml
- 標準ライブラリで HTTP は urllib を使用（追加パッケージは必須ではありません）。

セットアップ手順
----------------

1. リポジトリをクローン（あるいはプロジェクト配布を取得）
   - 例: git clone <repo-url>

2. 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate（Windows: .venv\Scripts\activate）

3. 必要パッケージをインストール
   - 例（最小）:
     - pip install duckdb openai defusedxml
   - プロジェクトに requirements.txt があれば:
     - pip install -r requirements.txt
   - 開発インストール（ソース配布を利用する場合）:
     - pip install -e .

4. 環境変数 / .env の設定
   - プロジェクトルート（.git または pyproject.toml がある位置）に .env を置くと自動で読み込まれます。
   - 自動ロードを無効化する場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
   - 必須の環境変数（少なくとも開発・実行に必要なもの）:
     - JQUANTS_REFRESH_TOKEN  — J-Quants のリフレッシュトークン（ETL 用）
     - KABU_API_PASSWORD     — kabuステーション API パスワード（発注連携など）
     - SLACK_BOT_TOKEN       — Slack 通知用 Bot トークン
     - SLACK_CHANNEL_ID      — Slack 通知先チャンネル ID
     - OPENAI_API_KEY        — OpenAI 呼び出し時に必要（ai/news/regime）
   - 任意 / デフォルト:
     - KABU_API_BASE_URL     — kabu API のベース URL（デフォルト http://localhost:18080/kabusapi）
     - DUCKDB_PATH           — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH           — 監視用 SQLite パス（デフォルト data/monitoring.db）
     - KABUSYS_ENV           — development / paper_trading / live（デフォルト development）
     - LOG_LEVEL             — ログレベル（DEBUG/INFO/...、デフォルト INFO）
   - .env の例（.env.example を参考に作成してください）:
     - JQUANTS_REFRESH_TOKEN=xxxx
     - OPENAI_API_KEY=sk-xxxx
     - DUCKDB_PATH=data/kabusys.duckdb
     - KABUSYS_ENV=development

使い方（簡単な例）
-----------------

以下は主要ユーティリティの呼び出し例です。実行前に settings（環境変数）が正しく設定されていることを確認してください。

- DuckDB 接続の作成:
  - import duckdb
  - from kabusys.config import settings
  - conn = duckdb.connect(str(settings.duckdb_path))

- 日次 ETL の実行:
  - from kabusys.data.pipeline import run_daily_etl
  - from datetime import date
  - result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  - print(result.to_dict())

- ニュースセンチメントのスコアリング（ai_scores へ書き込み）:
  - from kabusys.ai.news_nlp import score_news
  - from datetime import date
  - n = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # api_key を None にすると環境変数 OPENAI_API_KEY を使います
  - print(f"scored {n} symbols")

- 市場レジーム判定:
  - from kabusys.ai.regime_detector import score_regime
  - from datetime import date
  - score_regime(conn, target_date=date(2026, 3, 20))  # 同様に OPENAI_API_KEY を利用

- 監査ログ DB を初期化 (専用 DB ファイル):
  - from kabusys.data.audit import init_audit_db
  - audit_conn = init_audit_db("data/audit.duckdb")  # ":memory:" も可

- 監査スキーマを既存接続に追加:
  - from kabusys.data.audit import init_audit_schema
  - init_audit_schema(conn, transactional=True)

- 市場カレンダーユーティリティ:
  - from kabusys.data.calendar_management import is_trading_day, next_trading_day
  - is_td = is_trading_day(conn, date(2026,3,20))
  - nxt = next_trading_day(conn, date(2026,3,20))

注意事項・設計上のポイント
-----------------------
- Look-ahead バイアス対策:
  - モジュールは内部で datetime.today()/date.today() を無闇に参照しないよう設計されています（関数に target_date を明示的に渡す方針）。
- LLM 呼び出し:
  - OpenAI の Chat Completions（gpt-4o-mini を想定）を使用します。API 失敗時はフェイルセーフ（スコア 0.0 を採用）で継続する挙動が多く組み込まれています。
- ETL の冪等性:
  - DuckDB への保存は ON CONFLICT を用いた冪等設計になっています。
- セキュリティ:
  - RSS 収集は SSRF 対策・gzip 容量制限・XML の defusedxml でのパースを行っています。
- ロガビリティ:
  - 各モジュールは詳細なログを出力します。LOG_LEVEL を環境変数で調整してください。

ディレクトリ構成（主なファイル）
-------------------------------
（src/kabusys 以下。README 用に抜粋）

- kabusys/
  - __init__.py
  - config.py               — 環境変数 / Settings 管理（.env 自動ロード）
  - ai/
    - __init__.py
    - news_nlp.py           — ニュースの LLM スコアリング（score_news）
    - regime_detector.py    — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py     — J-Quants API クライアント（fetch / save 系）
    - pipeline.py           — ETL パイプライン（run_daily_etl 等）
    - etl.py                — ETL 結果クラスの公開（ETLResult）
    - news_collector.py     — RSS 収集・前処理
    - quality.py            — データ品質チェック
    - calendar_management.py— 市場カレンダー管理（is_trading_day 等）
    - stats.py              — 汎用統計（zscore_normalize）
    - audit.py              — 監査ログスキーマ初期化
  - research/
    - __init__.py
    - factor_research.py    — モメンタム/ボラティリティ/バリュー計算
    - feature_exploration.py— 前方リターン / IC / 統計サマリー
  - monitoring/ (リポジトリ内にある想定のモジュール群; 省略可能)
  - execution/, strategy/ (発注・戦略ロジック用のプレースホルダモジュール)

（ファイル名は本 README に基づく抜粋です。実際のリポジトリのルートに pyproject.toml / setup.cfg 等がある想定です）

開発・テスト時のヒント
---------------------
- .env の自動読み込みはプロジェクトルート（.git または pyproject.toml がある場所）から行われます。テスト中に自動ロードを無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI / J-Quants へ大量アクセスする処理はレート制限や課金に注意してください。テスト時は外部 API 呼び出し関数をモックしてください（モジュールはテスト容易性を考慮して設計されています）。
- DuckDB の executemany に空リストを渡すとバージョン依存でエラーとなるケースがあるため、コード内で空チェックを行っています。ローカルの DuckDB バージョンとの互換性に注意してください。

ライセンス・貢献
----------------
- ライセンス情報や貢献ガイドラインはリポジトリのルートにある LICENSE / CONTRIBUTING.md を参照してください（存在する場合）。

問い合わせ
----------
不明点や不具合報告はリポジトリの Issue に登録するか、プロジェクトの連絡先へお願いします。

以上。