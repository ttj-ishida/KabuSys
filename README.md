# KabuSys

KabuSys は日本株のデータ基盤・リサーチ・AI 評価・監査ログ・ETL を含む自動売買システムのライブラリ群です。本リポジトリはデータ取得（J-Quants）、ニュース収集、AI によるニュースセンチメント評価、ファクター計算、ETL パイプライン、監査ログスキーマなどを提供します。

---

## 概要

- データ取得: J-Quants API から株価（OHLCV）、財務、カレンダー等をページネーション対応で取得し DuckDB に保存するクライアント/保存関数を備えています。
- ETL パイプライン: 差分取得、バックフィル、品質チェック（欠損・重複・スパイク・日付不整合）を含む日次 ETL。
- ニュース収集: RSS から記事を収集し前処理した上で raw_news テーブルへ保存。SSRF や XML 攻撃対策を実装。
- AI モジュール: OpenAI（gpt-4o-mini）を用いたニュースセンチメント（銘柄別）と市場レジーム判定（ETF + マクロニュース合成）。
- 研究ユーティリティ: モメンタム・バリュー・ボラティリティ等のファクター計算、将来リターンや IC 計算、Z スコア正規化等。
- 監査ログ（Audit）: シグナル→発注→約定までのトレーサビリティ用スキーマ（DuckDB）と初期化関数を提供。

---

## 主な機能一覧

- 環境変数 / .env 自動読み込み（プロジェクトルート検出）
- J-Quants API クライアント（レートリミット制御、リトライ、トークンリフレッシュ）
- ETL: run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl
- データ品質チェック: check_missing_data / check_duplicates / check_spike / check_date_consistency / run_all_checks
- ニュース収集: fetch_rss、記事正規化・ID 生成・SSRF 対策
- AI: score_news（銘柄別ニュースセンチメント）, score_regime（市場レジーム判定）
- 研究: calc_momentum / calc_value / calc_volatility / calc_forward_returns / calc_ic / factor_summary / zscore_normalize
- 監査ログ初期化: init_audit_schema / init_audit_db

---

## 必要な環境変数

以下は本パッケージが参照する主な環境変数（必須は明示）。.env または OS 環境変数で設定してください。

必須（少なくとも実行する機能に応じて設定が必要）:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（jquants_client.get_id_token で使用）
- SLACK_BOT_TOKEN — Slack 通知用（Slack を使用する場合）
- SLACK_CHANNEL_ID — Slack 通知用チャネル ID
- KABU_API_PASSWORD — kabu ステーション API パスワード（実際の発注連携を行う場合）
- OPENAI_API_KEY — OpenAI API キー（AI 機能を利用する場合）

任意 / デフォルトあり:
- KABU_API_BASE_URL — kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite 監視 DB パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 環境 ("development" / "paper_trading" / "live")（デフォルト: development）
- LOG_LEVEL — ログレベル ("DEBUG"/"INFO"/"WARNING"/"ERROR"/"CRITICAL")
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 にすると .env 自動ロードを無効化

例（.env）:
JQUANTS_REFRESH_TOKEN=your_refresh_token
OPENAI_API_KEY=sk-...
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
KABU_API_PASSWORD=your_kabu_password

設定はプロジェクトルートの .env / .env.local から自動読み込みされます（環境変数優先）。自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## セットアップ手順

1. Python のインストール
   - 推奨: Python 3.10 以上（typing 機能を利用しているため）

2. 仮想環境の作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate （Windows: .venv\Scripts\activate）

3. 依存ライブラリをインストール
   - pip install -U pip
   - pip install duckdb openai defusedxml

   （プロジェクトに requirements.txt がある場合はそれを利用してください。開発用依存に pytest などを追加する場合もあります。）

4. パッケージのインストール（編集可能モード）
   - pip install -e .

5. 環境変数の設定
   - .env をプロジェクトルートに作成して上記の必須変数を設定します。

---

## 使い方（基本例）

以下の例は Python REPL やスクリプト内での利用法の一例です。DuckDB に接続し、ETL や AI 評価を実行できます。

- DuckDB 接続を作る:
  from datetime import date
  import duckdb
  conn = duckdb.connect('data/kabusys.duckdb')

- 日次 ETL を実行（target_date を省略すると今日）:
  from kabusys.data.pipeline import run_daily_etl
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())

- ニュースセンチメントを算出（OpenAI API キーが必要）:
  from kabusys.ai.news_nlp import score_news
  from datetime import date
  count = score_news(conn, target_date=date(2026, 3, 20))
  print(f"scored {count} symbols")

- 市場レジームを判定:
  from kabusys.ai.regime_detector import score_regime
  from datetime import date
  score_regime(conn, target_date=date(2026, 3, 20))

- 監査ログ DB を初期化:
  from kabusys.data.audit import init_audit_db
  audit_conn = init_audit_db('data/audit.duckdb')

- ファクター計算（研究）:
  from kabusys.research.factor_research import calc_momentum
  records = calc_momentum(conn, target_date=date(2026, 3, 20))

- J-Quants から銘柄一覧を取得:
  from kabusys.data.jquants_client import fetch_listed_info
  infos = fetch_listed_info()
  print(len(infos))

注意:
- AI 機能を利用する場合は OPENAI_API_KEY を環境変数か引数で指定してください。
- ETL/取得系は外部 API を呼ぶためネットワーク環境と認証情報が必須です。
- DuckDB のスキーマは ETL 実行・初期化コードで作成される想定です（必要に応じてスキーマ初期化処理を用意してください）。

---

## ディレクトリ構成

主要ファイル / モジュール一覧（src/kabusys 以下を抜粋）:

- kabusys/
  - __init__.py
  - config.py                      — 環境変数/.env の自動読み込みと Settings クラス
  - ai/
    - __init__.py
    - news_nlp.py                   — ニュースセンチメント（銘柄別）評価
    - regime_detector.py            — 市場レジーム判定（ETF MA + マクロ NEWS）
  - data/
    - __init__.py
    - jquants_client.py             — J-Quants API クライアント + DuckDB 保存関数
    - pipeline.py                   — ETL（run_daily_etl / run_*_etl）
    - etl.py                        — ETLResult の再エクスポート
    - news_collector.py             — RSS 取得・前処理・保存ロジック
    - calendar_management.py        — 市場カレンダー管理・営業日判定
    - stats.py                      — Zスコア等の統計ユーティリティ
    - quality.py                    — データ品質チェック
    - audit.py                      — 監査ログスキーマ/初期化
  - research/
    - __init__.py
    - factor_research.py            — Momentum/Value/Volatility 計算
    - feature_exploration.py        — forward returns / IC / 統計サマリー
  - ai/ (上記)
  - research/ (上記)

このパッケージはモジュール単位に機能が分かれており、データ収集・保存・品質管理・AI 解析・研究解析・監査ログの各層を分離して実装しています。

---

## 注意点 / 設計上の留意事項

- ルックアヘッドバイアス対策: 多くの関数は date.today() や datetime.today() を直接参照せず、外部から target_date を渡す設計です。バックテストでは開始日以前のデータのみを読み込むなどの運用に注意してください。
- 冪等性: J-Quants 保存関数や監査ログ初期化は冪等になるよう設計されています（ON CONFLICT / IF NOT EXISTS 等）。
- フォールバック: market_calendar が未取得の場合は曜日ベースのフォールバック（平日を営業日）で処理します。
- セキュリティ: RSS 取得は SSRF 対策（リダイレクトチェック、プライベート IP 拒否）を実装、XML は defusedxml を使用して安全にパースします。
- エラーハンドリング: 外部 API 呼び出しはリトライと指数バックオフを実施し、致命的でない場合はフェイルセーフ（ゼロまたは既存値を維持）で継続するように設計されています。

---

## 貢献 / 開発

- コードはモジュール単位で責務を分離しています。新しい ETL ジョブや品質チェック、AI 実験を追加する際は既存のインターフェース（DuckDB 接続を受け取る設計）に従ってください。
- テストは各モジュールの外部依存（ネットワーク・OpenAI）をモックして実行する想定です。config の自動 .env ロードはテスト時に KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化できます。

---

必要であれば README にサンプル .env.example、CI 用のセットアップ手順、実運用（paper/live）切替方法、よくあるトラブルシューティング項目等を追記します。どの情報を追加したいか教えてください。