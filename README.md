# KabuSys

日本株向け自動売買 / データプラットフォーム用ライブラリ群

概要
- KabuSys は日本株のデータ収集（J-Quants）、ニュース収集・NLP、ファクター算出、ETL、監査ログ、研究用ユーティリティ、さらに市場レジーム判定や AI を使ったニュースセンチメント評価を含むコンポーネント群を提供する Python パッケージ群です。
- プロダクション運用を念頭に置き、DuckDB を用いたローカルデータベース、冪等な保存・ETL、API リトライ・レート制御、Look-ahead バイアス防止の設計方針が各モジュールに反映されています。

主な機能
- J-Quants API クライアント（差分取得・ページネーション・トークンリフレッシュ・レート制御）
  - 日足（OHLCV）、財務データ、JPX マーケットカレンダー、上場銘柄情報
- ETL パイプライン（run_daily_etl）
  - カレンダー → 日足 → 財務データの順で差分取得・保存・品質チェック
- データ品質チェック（欠損・重複・スパイク・日付不整合）
- ニュース収集（RSS）と前処理（SSRF 対策・トラッキング除去・ID生成）
- ニュース NLP（OpenAI を用いた銘柄ごとのセンチメント算出）
- 市場レジーム判定（ETF 1321 の MA200 乖離 + マクロニュース LLM センチメント合成）
- 監査ログ（signal_events / order_requests / executions）スキーマ定義と初期化
- 研究用ユーティリティ（ファクター計算、将来リターン、IC、統計サマリー、Z スコア正規化）
- 汎用統計ユーティリティ（zscore_normalize など）

前提・動作環境
- Python 3.10+
  - typing で | 記法が使われているため 3.10 以上を想定しています。
- 主な Python 依存パッケージ（例）
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants API、OpenAI、RSS フィード等）

セットアップ手順（開発環境向け）
1. リポジトリをクローン
   ```bash
   git clone <repository-url>
   cd <repository>
   ```

2. 仮想環境を作成して有効化（推奨）
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

3. 依存パッケージをインストール
   - 最低限必要なパッケージを手動でインストールする例:
   ```bash
   pip install duckdb openai defusedxml
   ```
   - 開発用に pyproject.toml / requirements.txt がある場合はそれを利用してください:
   ```bash
   pip install -e .
   # または
   pip install -r requirements.txt
   ```

4. 環境変数の準備
   - プロジェクトルートに `.env` と `.env.local` を置くことで、パッケージ読み込み時に自動で環境変数が読み込まれます（自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください）。
   - 必須の環境変数（主なもの）
     - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
     - OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector 用）
     - KABU_API_PASSWORD: kabu ステーション API パスワード（注文実行等で使用）
     - SLACK_BOT_TOKEN / SLACK_CHANNEL_ID: Slack 通知に使用
   - その他オプション（デフォルトあり）
     - KABUSYS_ENV (development | paper_trading | live)
     - LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL)
     - DUCKDB_PATH (例: data/kabusys.duckdb)
     - SQLITE_PATH (監視用 DB, 例: data/monitoring.db)
   - サンプル `.env`（例）:
     ```
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     OPENAI_API_KEY=sk-...
     KABU_API_PASSWORD=your_kabu_password
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     DUCKDB_PATH=data/kabusys.duckdb
     LOG_LEVEL=INFO
     KABUSYS_ENV=development
     ```

使い方（簡単な例）
- DuckDB 接続を作って ETL を実行する
  ```python
  from datetime import date
  import duckdb
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュース NLP（日次）を実行して ai_scores を作る
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"書き込んだ銘柄数: {written}")
  ```

- 市場レジーム判定を実行
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログ用 DuckDB を初期化
  ```python
  import duckdb
  from kabusys.data.audit import init_audit_db

  conn = init_audit_db("data/audit.duckdb")
  # これで signal_events / order_requests / executions テーブルが作成されます
  ```

- モジュール設定参照
  ```python
  from kabusys.config import settings
  print(settings.kabu_api_base_url)
  print(settings.is_live)
  ```

注意点・運用メモ
- OpenAI / J-Quants の API 呼び出しは外部サービスに依存します。テスト時は各モジュールの _call_openai_api 等をモックしてテストすることを推奨します（コード内にもモック例を差し替えやすい設計が反映されています）。
- DuckDB の SQL 実行中は executemany に空リストを渡せない等の実装依存を考慮した記述があるため、アップグレード時は互換性に注意してください。
- ニュース収集モジュールは SSRF 対策（プライベートアドレス拒否、リダイレクト検査）や最大受信サイズ制限を備えています。RSS ソースの追加は DEFAULT_RSS_SOURCES を編集するか、fetch_rss を利用してください。
- 自動環境変数読み込みはプロジェクトルート（.git または pyproject.toml）を基準に行われます。配布時やテスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化できます。

ディレクトリ構成（主なファイル・モジュール）
- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数・設定管理（settings オブジェクト）
  - ai/
    - __init__.py
    - news_nlp.py
      - raw_news から銘柄ごとに記事を集約、OpenAI でセンチメントを算出して ai_scores に保存
    - regime_detector.py
      - ETF 1321 の MA200 乖離とマクロニュース LLM スコアを合成して market_regime を生成
  - data/
    - __init__.py
    - jquants_client.py
      - J-Quants API 取得・保存ユーティリティ（fetch / save 系）
    - pipeline.py
      - run_daily_etl 等の ETL パイプライン、ETLResult 定義
    - etl.py
      - ETLResult のエイリアス公開
    - calendar_management.py
      - market_calendar 管理、営業日判定、calendar_update_job
    - stats.py
      - zscore_normalize 等の統計ユーティリティ（研究モジュールで利用）
    - quality.py
      - データ品質チェック（欠損・スパイク・重複・日付不整合）
    - audit.py
      - 監査ログスキーマと初期化ロジック（signal_events / order_requests / executions）
    - news_collector.py
      - RSS 取得・前処理・raw_news への保存補助（SSRF 対策、ID 生成）
  - research/
    - __init__.py
    - factor_research.py
      - Momentum / Volatility / Value 等のファクター算出
    - feature_exploration.py
      - 将来リターン計算、IC（Spearman）計算、統計サマリー、ランク化ユーティリティ

貢献・開発
- バグ修正、テスト追加、機能拡張は歓迎します。PR の際は既存の設計方針（冪等性・Look-ahead バイアス防止・外部 API の保護）を尊重してください。
- テストを書く際は外部 API 呼び出しをモックすること（OpenAI / J-Quants / ネットワーク系）。

ライセンス
- プロジェクトルートにある LICENSE を参照してください（このリポジトリに付随するライセンスに従ってください）。

以上。README の内容やサンプルコードの追加説明が必要であれば、用途（開発・運用・デプロイ）に合わせて追記します。