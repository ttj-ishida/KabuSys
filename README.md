# KabuSys

日本株向け自動売買プラットフォームのライブラリ群です。データ収集（J-Quants）、データ品質チェック、ニュース収集、AIベースのニュースセンチメント評価／市場レジーム判定、ファクター計算、監査ログ（注文→約定トレース）など、システム全体の基盤機能を提供します。

主な用途は「データプラットフォーム（ETL）」「リサーチ（ファクター探索）」「AI 支援のニュース解析／レジーム判定」「監査ログと発注追跡」「DuckDB を用いたローカルデータ管理」です。

---

## 主な機能一覧

- ETL（デイリー）パイプライン
  - 市場カレンダー / 株価日足 / 財務データの差分取得と DuckDB 保存（冪等）
  - 品質チェック（欠損・重複・スパイク・日付整合性）
- J-Quants API クライアント
  - 株価（日次OHLCV）、財務データ、JPXカレンダー等の取得（ページネーション・リトライ・レート制御・トークンリフレッシュ対応）
- ニュース収集
  - RSS フィード取得、前処理、raw_news / news_symbols への保存（SSRF対策・トラッキングパラメータ除去・サイズ制限）
- ニュース NLP（AI）
  - gpt-4o-mini を使った銘柄別ニュースセンチメント算出（JSON Mode を想定）
  - タイムウィンドウとバッチ処理、リトライ・検証ロジック付き
- 市場レジーム判定
  - ETF 1321 の 200 日移動平均乖離（70%）とマクロニュースセンチメント（30%）を合成して日次レジーム（bull/neutral/bear）判定
  - OpenAI API 呼び出しのフェイルセーフ（失敗時は 0.0 にフォールバック）とリトライ対応
- 研究用ユーティリティ
  - モメンタム / ボラティリティ / バリュー 等のファクター計算
  - 将来リターン計算、IC（Spearman）計算、ファクター統計サマリ、Z スコア正規化
- 監査ログ（Audit）
  - signal_events / order_requests / executions テーブルを定義・初期化
  - 発注から約定までのトレース用スキーマ（冪等キー・index あり）
- 設定・環境管理
  - .env/.env.local の自動読み込み（プロジェクトルート検出）と Settings API
  - 必須環境変数の検証機能

---

## セットアップ手順（開発向け）

前提:
- Python 3.10+（typing の union 記法などに依存）
- DuckDB を利用（パッケージとしてインストール）

1. リポジトリをクローン／ワークツリーへ移動

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージをインストール
   - 代表的な依存例（実プロジェクトで requirements.txt を整備してください）:
     - pip install duckdb openai defusedxml
   - 追加で監視や Slack 送信、テスト用パッケージが必要な場合は適宜追加

4. 環境変数を準備
   - プロジェクトルート（.git または pyproject.toml のあるディレクトリ）に `.env` または `.env.local` を配置すると自動読み込みされます（自動読み込みを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。
   - 必須項目（少なくとも次を設定してください。AI / J-Quants / Slack 機能を使う場合はそれぞれ必須）:
     - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD — kabuステーション API パスワード（発注連携時）
     - SLACK_BOT_TOKEN — Slack Bot Token（通知機能用）
     - SLACK_CHANNEL_ID — Slack チャンネル ID（通知先）
   - 任意 / デフォルト有り:
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト development
     - LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL) — デフォルト INFO
     - DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH — 監視用 SQLite（デフォルト data/monitoring.db）
     - PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT など

5. データディレクトリ作成（必要に応じて）
   - mkdir -p data

---

## 使い方（代表的なサンプル）

以下はいくつかの代表的な呼び出し例です。実行はプロジェクトの Python 環境で行ってください。

- 日次 ETL の実行例
  - Python スクリプトから:
    ```
    import duckdb
    from datetime import date
    from kabusys.data.pipeline import run_daily_etl

    conn = duckdb.connect("data/kabusys.duckdb")
    result = run_daily_etl(conn, target_date=date(2026, 3, 20))
    print(result.to_dict())
    ```

- ニュースセンチメント（銘柄別）を算出して ai_scores に書き込む
  - score_news は OpenAI API キーを引数で渡すか環境変数 OPENAI_API_KEY を参照します。
    ```
    from datetime import date
    import duckdb
    from kabusys.ai.news_nlp import score_news

    conn = duckdb.connect("data/kabusys.duckdb")
    n_written = score_news(conn, target_date=date(2026,3,20), api_key="sk-...")
    print("written:", n_written)
    ```

- 市場レジーム判定（market_regime テーブルへ書き込み）
    ```
    from datetime import date
    import duckdb
    from kabusys.ai.regime_detector import score_regime

    conn = duckdb.connect("data/kabusys.duckdb")
    score_regime(conn, target_date=date(2026,3,20), api_key="sk-...")
    ```

- 監査ログ DB の初期化（監査専用 DB を作る）
    ```
    from kabusys.data.audit import init_audit_db
    conn = init_audit_db("data/audit.duckdb")
    # conn は DuckDB 接続。signal_events / order_requests / executions が作成される。
    ```

- J-Quants から日次株価を直接取得（テストやラボ向け）
    ```
    from kabusys.data.jquants_client import fetch_daily_quotes
    quotes = fetch_daily_quotes(date_from=date(2026,1,1), date_to=date(2026,1,31))
    print(len(quotes))
    ```

- 設定の参照
    ```
    from kabusys.config import settings
    print(settings.duckdb_path)
    print(settings.is_live)
    ```

---

## 主要モジュールとディレクトリ構成

（ソースは src/kabusys 以下に配置）

- kabusys/
  - __init__.py
  - config.py
    - 環境変数自動読み込み（.env / .env.local）、Settings クラスを提供
  - ai/
    - __init__.py
    - news_nlp.py         — ニュースセンチメント（銘柄別）スコアリング、OpenAI 呼び出し・検証・バッチ処理
    - regime_detector.py  — ETF 1321 MA200 とマクロニュースセンチメントを合成した市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py   — J-Quants API クライアント（取得・保存ロジック含む）
    - pipeline.py         — ETL パイプラインのメイン処理（run_daily_etl 等）
    - etl.py              — ETLResult 型の再エクスポート
    - calendar_management.py — 市場カレンダー管理（営業日判定、next/prev/get_trading_days、calendar_update_job）
    - stats.py            — zscore_normalize 等の統計ユーティリティ
    - quality.py          — データ品質チェック（欠損・重複・スパイク・日付整合性）
    - audit.py            — 監査ログスキーマ定義・初期化（signal/order/execution）
    - news_collector.py   — RSS 取得・前処理・保存（SSRF・サイズ検査・ID生成）
  - research/
    - __init__.py
    - factor_research.py  — momentum / volatility / value ファクター計算
    - feature_exploration.py — forward returns / IC / summary / rank 等
  - (その他)
    - research, ai, data 以下のユーティリティ群や補助関数

---

## 環境変数（主なもの）

必須（使用する機能により必要）:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（jquants_client.get_id_token で使用）
- KABU_API_PASSWORD — kabu ステーション API のパスワード（発注機能）
- SLACK_BOT_TOKEN — Slack 通知用トークン
- SLACK_CHANNEL_ID — Slack 通知用チャネル ID

任意 / デフォルトあり:
- KABUSYS_ENV — "development" / "paper_trading" / "live"（デフォルト "development"）
- LOG_LEVEL — ログレベル（デフォルト "INFO"）
- DUCKDB_PATH — デフォルト "data/kabusys.duckdb"
- SQLITE_PATH — デフォルト "data/monitoring.db"
- PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT — 監視設定
- OPENAI_API_KEY — OpenAI 呼び出しに使用（score_news / score_regime でも引数で指定可能）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env ロードを無効化（値が存在すれば無効）

自動読み込みの仕様:
- プロジェクトルート（.git または pyproject.toml を探索して検出）に `.env` を置くと自動で読み込みます。
- 読み込み順: OS 環境 > .env.local (override=True) > .env (override=False)
- テスト等で自動読み込みを抑止したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。

---

## 注意点 / 設計上の方針（抜粋）

- Look-ahead バイアスを避けるため、関数は内部で datetime.today()/date.today() を安易に参照しない設計です（target_date を明示的に渡します）。
- API 呼び出しはリトライ・バックオフ・RateLimit の考慮があるため、実運用での安定性を重視しています。
- DuckDB を中心にローカルでの分析・監査を行います（ETL は冪等保存）。
- OpenAI 呼び出しは JSON Mode を想定したレスポンス検証を行います（不正なレスポンスはスキップしてフェイルセーフで継続）。
- ニュース収集は SSRF 対策（リダイレクト含む）・受信サイズ制限・トラッキングパラメータ除去などセキュアに実装されています。

---

## テスト / モックについて

- AI 呼び出し関数（news_nlp, regime_detector）内の _call_openai_api はテスト時に patch/モック可能に設計されています（unittest.mock.patch を想定）。
- jquants_client の HTTP 呼び出しは urllib を使っており、ユニットテストでは _request をモック／パッチすることで外部依存を切り離せます。
- news_collector のネットワーク I/O は _urlopen をモックしてテスト可能です。

---

README は開発者向けの導入ガイドです。さらに具体的な運用手順（デプロイ / cron ワークフロー / Slack 通知設定 / kabuステーション連携フロー）は別途ドキュメント化することを推奨します。必要であれば、あなたの運用環境に合わせた「運用手順書」テンプレートも作成します。必要なら教えてください。