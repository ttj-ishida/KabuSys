# KabuSys — 日本株自動売買プラットフォーム（README）

本リポジトリは日本株のデータパイプライン、リサーチ、AIによるニュースセンチメント解析、及び監査ログを含む自動売買基盤のライブラリ群です。DuckDB をデータ格納に用い、J-Quants API / OpenAI API / RSS を統合して、ETL → 品質チェック → ファクター計算 → シグナル／発注の監査までをサポートすることを目的としています。

## 主な特徴（機能一覧）
- データ収集（J-Quants API）
  - 株価日足（OHLCV）、財務諸表、上場銘柄情報、JPXマーケットカレンダー等の差分取得（ページネーション対応）
  - レート制限 / リトライ / トークン自動リフレッシュ処理
- ETL パイプライン
  - 差分取得（バックフィル対応）と DuckDB への冪等保存（ON CONFLICT）
  - 日次パイプライン run_daily_etl による一括実行（カレンダー→株価→財務→品質チェック）
- データ品質チェック
  - 欠損（OHLC）、重複、スパイク（前日比）、日付不整合（未来日/非営業日）を検出
  - QualityIssue オブジェクトで問題を収集
- ニュース収集＆NLP（RSS + OpenAI）
  - RSS フィード収集（SSRF 対策、URL 正規化、トラッキングパラメータ削除）
  - gpt-4o-mini を用いた銘柄ごとのニュースセンチメント score_news（結果を ai_scores テーブルへ保存）
  - レジーム判定 score_regime（ETF 1321 の MA200 とマクロニュースの LLM センチメントを合成）
- 監査ログ（Audit）
  - signal_events / order_requests / executions 等の監査テーブルを初期化するユーティリティ（冪等）
  - init_audit_schema / init_audit_db による DB 初期化
- 研究用ユーティリティ
  - モメンタム・ボラティリティ・バリュー等のファクター計算（research パッケージ）
  - クロスセクション正規化・将来リターン・IC・統計サマリー

## 前提条件
- Python 3.10 以上（typing construct の使用を想定）
- 外部ライブラリ（主要）
  - duckdb
  - openai（OpenAI の新しい Python SDK を想定）
  - defusedxml
- J-Quants API アクセス用トークン（refresh token）
- OpenAI API キー（ニュース/レジーム判定用）
- （オプション）kabuステーション連携用パスワード、Slack トークン等

## セットアップ手順

1. リポジトリをクローンして、パッケージをインストール（開発モード推奨）
   ```bash
   git clone <repo-url>
   cd <repo-root>
   pip install -e ".[dev]"  # もし setup.cfg/pyproject に extras があれば
   # もしくは最低限の依存を個別にインストール
   pip install duckdb openai defusedxml
   ```

2. 環境変数の用意
   - プロジェクトルートに `.env` または `.env.local` を作成すると、自動で読み込まれます（ただし自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定）。
   - 必須環境変数（最低限）
     - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
     - SLACK_BOT_TOKEN — Slack 通知を使う場合
     - SLACK_CHANNEL_ID — Slack 通知を使う場合
     - KABU_API_PASSWORD — kabuステーション API を使う場合
     - OPENAI_API_KEY — news_nlp / regime_detector 呼び出し時に明示的に渡すことも可能
   - その他（省略時デフォルトあり）
     - KABUSYS_ENV — development | paper_trading | live（デフォルト development）
     - LOG_LEVEL — DEBUG/INFO/...
     - DUCKDB_PATH — デフォルト data/kabusys.duckdb
     - SQLITE_PATH — デフォルト data/monitoring.db

   例 `.env`（サンプル）:
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
   OPENAI_API_KEY=sk-...
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C0123456789
   KABU_API_PASSWORD=your_kabu_password
   DUCKDB_PATH=./data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

3. データベース格納先ディレクトリ作成（必要に応じて）
   ```bash
   mkdir -p data
   ```

## 使い方（主要な API と実行例）

以下は Python スクリプト/REPL から利用する例です。プロジェクトは CLI を明示的には提供していないため、ライブラリ API を直接呼び出します。

- DuckDB に接続して日次 ETL を実行する（run_daily_etl）
  ```python
  import duckdb
  from kabusys.data.pipeline import run_daily_etl
  from kabusys.config import settings
  from datetime import date

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

- ニュースセンチメントを評価して ai_scores に保存（score_news）
  ```python
  from kabusys.ai.news_nlp import score_news
  import duckdb
  from datetime import date

  conn = duckdb.connect("data/kabusys.duckdb")
  # OPENAI_API_KEY が env に設定されているか、api_key 引数で明示する
  n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
  print("書き込んだ銘柄数:", n_written)
  ```

- マーケットレジーム判定（score_regime）
  ```python
  from kabusys.ai.regime_detector import score_regime
  import duckdb
  from datetime import date

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
  ```

- 監査ログスキーマの初期化 / 監査専用 DB の初期化
  ```python
  from kabusys.data.audit import init_audit_db, init_audit_schema
  import duckdb
  # 監査専用 DB ファイルを初期化して接続を取得
  conn = init_audit_db("data/audit.duckdb")
  # 既存接続に対してスキーマを追加したい場合
  conn2 = duckdb.connect("data/kabusys.duckdb")
  init_audit_schema(conn2, transactional=True)
  ```

- RSS フェッチ単体（ニュース収集モジュール）
  ```python
  from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES

  url = DEFAULT_RSS_SOURCES["yahoo_finance"]
  articles = fetch_rss(url, source="yahoo_finance")
  for a in articles[:5]:
      print(a["id"], a["datetime"], a["title"])
  ```

注意点（実行時の設計方針）
- Look-ahead バイアス防止のため、日付計算や DB クエリは target_date 未満・以前のみを参照する実装が多く含まれています。バックテスト等では取扱いに注意してください。
- OpenAI / J-Quants API の呼び出しはリトライやフェイルセーフが組み込まれていますが、APIキーが未設定だと一部関数は ValueError を投げます。
- 全てのタイムスタンプは設計上 UTC を前提とします（監査ログ初期化時には SET TimeZone='UTC' を実行）。

## 典型的なワークフロー
1. .env を整備して J-Quants / OpenAI のキーを配置
2. DuckDB を初期化（必要なテーブルは ETL 実行時に作成される想定）
3. run_daily_etl をスケジューラ（cron 等）で日次実行
4. ニューススコア / レジーム判定を ETL 後または別スケジュールで実行
5. 生成された ai_scores / market_regime / raw_prices を研究・戦略層で利用
6. 監査ログは order_requests 等を通じて発注→約定のトレースに使用

## ディレクトリ構成
（主要なファイル・モジュールを抜粋）

- src/kabusys/
  - __init__.py
  - config.py                              — 環境変数 / 設定読み込みロジック
  - ai/
    - __init__.py
    - news_nlp.py                           — ニュースセンチメント評価（score_news）
    - regime_detector.py                    — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py                     — J-Quants API クライアント（fetch / save）
    - pipeline.py                           — ETL パイプライン（run_daily_etl 等）
    - etl.py                                — ETLResult の公開エイリアス
    - news_collector.py                     — RSS 収集（fetch_rss 等）
    - calendar_management.py                — 市場カレンダー管理（is_trading_day 等）
    - quality.py                            — データ品質チェック
    - stats.py                              — 共通統計ユーティリティ（zscore_normalize）
    - audit.py                              — 監査ログテーブル初期化ユーティリティ
  - research/
    - __init__.py
    - factor_research.py                    — Momentum/Value/Volatility 等
    - feature_exploration.py                — forward returns / IC / summary / rank
  - research/*, ai/*, data/* ... その他ユーティリティ群

（実際のリポジトリではさらに細かいモジュールが存在します。README は上位層の利用例とアーキテクチャを示しています。）

## 開発・テストに関する補足
- 自動的に .env ファイルをプロジェクトルートから読み込む仕組みがあります。テスト時に自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- OpenAI 呼び出しや外部 API 呼び出しは個別にモック可能（モジュール内の _call_openai_api 等を unittest.mock.patch で差し替え）です。
- DuckDB の executemany に空リストを渡すとエラーになるバージョン依存の対処がコード内に盛り込まれています。

## ライセンス / 貢献
（この README では省略しています。プロジェクトのルートに LICENSE または CONTRIBUTING.md があればそちらを参照してください。）

---

何か追加したい操作（例えば CLI のサンプル、より詳細な .env.example、または特定モジュールの API ドキュメント化）があれば教えてください。README を拡張して具体的なコマンドや運用手順を追記します。