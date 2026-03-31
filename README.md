# KabuSys

日本株向けの自動売買・データ基盤ライブラリです。  
ETL（J-Quants → DuckDB）、ニュース収集・NLP（OpenAI）、リサーチ用ファクター計算、監査ログ（オーダー・約定トレーサビリティ）などを含むモジュール群を提供します。

- パッケージ名: kabusys
- バージョン: 0.1.0

---

## 概要

KabuSys は日本株のデータ収集・品質管理・特徴量生成・AI を用いたニュースセンチメント評価・市場レジーム判定・監査ログ管理などを実装したライブラリ群です。  
主な設計方針として以下を重視しています。

- DuckDB を中心としたローカルデータプラットフォーム（ETL の冪等保存）
- Look-ahead bias を避ける設計（内部で date.today() 等を不用意に参照しない）
- API 呼び出しに対するリトライ／フェイルセーフの実装（J-Quants / OpenAI）
- ニュース収集に対する SSRF 保護、XML パースの安全化
- 監査ログによるシグナル → 発注 → 約定のトレーサビリティ確保

---

## 主な機能一覧

- data
  - ETL（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - J-Quants クライアント（取得・保存・トークンリフレッシュ・レート制御）
  - カレンダー管理（営業日判定、next/prev/get_trading_days）
  - データ品質チェック（欠損、スパイク、重複、日付不整合）
  - ニュース収集（RSS → raw_news、SSRF 保護、前処理）
  - 監査ログスキーマ初期化（init_audit_schema / init_audit_db）
  - 汎用統計ユーティリティ（zscore 正規化）
- ai
  - ニュースセンチメント（score_news） — OpenAI を用いた銘柄別スコア化
  - 市場レジーム判定（score_regime） — ETF（1321）200日MA とマクロニュースを統合
- research
  - ファクター計算（momentum / volatility / value）
  - 特徴量探索（forward returns / IC / summary / rank）
- config
  - 環境変数読み込みと Settings（.env 自動ロード、必須値チェック）
- audit / execution / monitoring（監査・発注・監視のためのユーティリティ群）

---

## セットアップ手順

以下は開発・実行環境の最小構成例です。

1. リポジトリを取得（例）
   - git clone … && cd <repo>

2. Python 仮想環境を作成・有効化
   - python3 -m venv .venv
   - source .venv/bin/activate  # macOS / Linux
   - .venv\Scripts\activate     # Windows（PowerShell / cmd による）

3. 必要パッケージをインストール
   - 一般的に必要なパッケージ（抜粋）:
     - duckdb
     - openai
     - defusedxml
   - 例:
     - pip install duckdb openai defusedxml

   （プロジェクトに requirements.txt / pyproject.toml があればそちらを使用してください）
4. パッケージをインストール（編集可能モード）
   - pip install -e .

5. 環境変数を用意
   - プロジェクトルート（.git のあるディレクトリ）に `.env` を置くと自動でロードされます（デフォルト）。
   - 自動ロードを無効化する場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

必須と思われる環境変数（README 用サンプル）：
- JQUANTS_REFRESH_TOKEN=...
- OPENAI_API_KEY=...
- KABU_API_PASSWORD=...（kabu ステーション関連）
- SLACK_BOT_TOKEN=...
- SLACK_CHANNEL_ID=...

その他設定（デフォルトあり）：
- KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
- LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL) — デフォルト: INFO
- DUCKDB_PATH（デフォルト data/kabusys.duckdb）
- SQLITE_PATH（監視 DB、デフォルト data/monitoring.db）
- PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT

例 .env（参考）
- JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
- OPENAI_API_KEY=sk-xxxxx
- KABU_API_PASSWORD=your_kabu_password
- SLACK_BOT_TOKEN=xoxb-...
- SLACK_CHANNEL_ID=C0123456789
- KABUSYS_ENV=development
- LOG_LEVEL=INFO

---

## 使い方（代表的な例）

（以下は Python スクリプト / インタラクティブで実行する例）

1) DuckDB に接続して日次 ETL を実行する
- 例:
  - from datetime import date
    import duckdb
    from kabusys.data.pipeline import run_daily_etl
    conn = duckdb.connect("data/kabusys.duckdb")
    result = run_daily_etl(conn, target_date=date(2026, 3, 20))
    print(result.to_dict())

2) ニュースセンチメントをスコア化（OpenAI API キーが必要）
- 例:
  - from datetime import date
    import duckdb
    from kabusys.ai.news_nlp import score_news
    conn = duckdb.connect("data/kabusys.duckdb")
    count = score_news(conn, target_date=date(2026,3,20))  # OpenAI API キーは環境変数 OPENAI_API_KEY で解決
    print(f"scored {count} codes")

3) 市場レジームスコアの計算
- 例:
  - from datetime import date
    import duckdb
    from kabusys.ai.regime_detector import score_regime
    conn = duckdb.connect("data/kabusys.duckdb")
    score_regime(conn, target_date=date(2026,3,20))  # OPENAI_API_KEY が必要

4) 監査ログ DB 初期化（監査用 DuckDB）
- 例:
  - from kabusys.data.audit import init_audit_db
    conn = init_audit_db("data/audit.duckdb")
    # これで signal_events / order_requests / executions テーブルが作成されます

5) RSS を取得して記事一覧を返す（news_collector）
- 例:
  - from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES
    articles = fetch_rss(DEFAULT_RSS_SOURCES["yahoo_finance"], source="yahoo_finance")
    print(len(articles), articles[0])

注意点:
- OpenAI 呼び出しはリトライ・フェイルセーフ付きですが、API キーが必須です（引数で注入可）。
- J-Quants API 利用には refresh token が必要です。
- ETL 等はデータベースに書き込みを行います。実行前にバックアップや dev 用 DB を使用してください。

---

## 環境変数一覧（参照用）

主要な環境変数（config.Settings が参照します）：

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants 用リフレッシュトークン
- KABU_API_PASSWORD (必須) — kabu ステーション API パスワード
- KABU_API_BASE_URL (任意、デフォルト: http://localhost:18080/kabusapi)
- SLACK_BOT_TOKEN (必須) — Slack ボット用トークン
- SLACK_CHANNEL_ID (必須) — Slack チャンネル ID
- DUCKDB_PATH (任意、デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (任意、デフォルト: data/monitoring.db)
- PID_FILE_PATH (任意、デフォルト: data/execution.pid)
- CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT（監視設定）
- KABUSYS_ENV (development | paper_trading | live)
- LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL)
- OPENAI_API_KEY — OpenAI（news_nlp / regime_detector で使用）

自動 .env ロード:
- プロジェクトルート（.git または pyproject.toml があるディレクトリ）にある `.env` と `.env.local` が自動で読み込まれます。
- 自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## ディレクトリ構成（主要ファイル）

パッケージの主要な構成を抜粋します。

- src/kabusys/
  - __init__.py
  - config.py                     — 環境変数 / Settings
  - ai/
    - __init__.py
    - news_nlp.py                  — ニュースセンチメント（score_news）
    - regime_detector.py           — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - pipeline.py                  — ETL パイプライン（run_daily_etl 等）
    - jquants_client.py            — J-Quants API クライアント（fetch / save）
    - calendar_management.py       — マーケットカレンダー管理
    - news_collector.py            — RSS 収集・前処理（SSRF 対策あり）
    - quality.py                   — データ品質チェック（missing/spike/duplicates/日付不整合）
    - stats.py                     — zscore_normalize 等
    - etl.py                       — ETLResult の再エクスポート
    - audit.py                     — 監査ログスキーマ初期化（signal/order/execution）
  - research/
    - __init__.py
    - factor_research.py           — momentum / value / volatility
    - feature_exploration.py       — forward returns / IC / factor summary / rank
  - ai, research, data などのサブパッケージに多数のユーティリティと SQL ベースの処理を含む

---

## 設計上の注意事項 / ベストプラクティス

- Look-ahead bias を避けるため、関数の多くは明示的な target_date を受け取り、内部で現在時刻を参照しないよう設計されています。バックテストや日次バッチでは target_date を明示して使用してください。
- API キーやトークンは環境変数で管理し、 .env はプロダクションにコミットしないでください。
- J-Quants / OpenAI の API 呼び出しは料金・レート制限に注意して使用してください（ローカルでのテストはモックを推奨）。
- ニュース収集では SSRF・XML 攻撃対策を組み込んでいますが、独自の RSS ソース追加時は信頼性を確認してください。

---

## 補足

- ドキュメント内の関数や設定に関する詳細は、ソースコードの docstring（各モジュールの先頭にある説明）を参照してください。  
- 実運用での発注・約定処理はリスクを伴います。本リポジトリのコードはインフラ・ロジックの実装例を提供するものであり、実際に資金を投入する前に十分なテスト・レビューを行ってください。

---

ご要望があれば、README に CI/テスト手順、より具体的な使い方（サンプルスクリプト）や .env.example のテンプレート、よくあるトラブルシュート（FAQ）を追加します。どの内容を優先して追加しましょうか？