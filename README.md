# KabuSys

日本株向けの自動売買・データプラットフォームライブラリです。  
ETL（J-Quants 経由の株価・財務・カレンダー取得）、ニュース収集・NLP（OpenAI を利用したセンチメント解析）、市場レジーム判定、ファクター計算、データ品質チェック、監査ログ（トレーサビリティ）など、アルゴリズムトレーディングのデータ基盤と解析ツールを提供します。

バージョン: 0.1.0

---

## 主な特徴（機能一覧）

- データ取得 / ETL
  - J-Quants API クライアント（差分取得・ページネーション・トークン自動リフレッシュ・レート制御）
  - 日次 ETL パイプライン（株価 / 財務 / カレンダーの差分取得・保存）
  - DuckDB へ冪等保存（ON CONFLICT を使用）

- ニュース収集・前処理
  - RSS フィード取得（SSRF 対策、トラッキングパラメータ除去、gzip 対応）
  - 記事ID の SHA-256 ベースによる冪等登録
  - raw_news / news_symbols への保存ロジック

- ニュース NLP / LLM 連携
  - OpenAI（gpt-4o-mini）の JSON Mode を使ったバッチセンチメント解析（銘柄別）
  - チャンク処理、リトライ、レスポンスバリデーション、スコアの ±1.clip

- 市場レジーム判定
  - ETF 1321（日経225連動）200日 MA 乖離 + マクロニュース LLM センチメントを合成して日次で 'bull' / 'neutral' / 'bear' を判定
  - LLM 呼び出しのフォールバック・リトライ実装あり

- 研究用ユーティリティ（research）
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー、Zスコア正規化

- データ品質チェック
  - 欠損・スパイク・重複・日付不整合の検出（QualityIssue を返す）

- カレンダー管理
  - market_calendar テーブルを使った営業日判定、next/prev_trading_day、期間内営業日取得、夜間バッチ更新ジョブ

- 監査ログ（Audit / Tracing）
  - signal_events / order_requests / executions の監査スキーマ定義と初期化ユーティリティ
  - UUID ベースの冪等鍵・完全なトレーサビリティ設計

---

## セットアップ手順

前提
- Python 3.9+（ソースは typing の union 表記などを使用）を推奨
- ネットワーク経由の API 呼び出しを行うため、必要な API キーを準備してください（J-Quants / OpenAI / kabuステーション / Slack など）

1. 仮想環境作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. パッケージのインストール
   - ソースルートで:
     - pip install -e .
   - 使用する外部ライブラリ（プロジェクトに requirements.txt がない場合の例）
     - pip install duckdb openai defusedxml

   （実際のプロジェクトでは requirements.txt や pyproject.toml を参照してください。）

3. 環境変数 / .env
   - 必須（最低限）環境変数:
     - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD : kabuステーション API パスワード（発注系を使う場合）
     - SLACK_BOT_TOKEN : Slack 通知を行う場合の Bot トークン
     - SLACK_CHANNEL_ID : Slack 通知先チャンネル ID
     - OPENAI_API_KEY : OpenAI API キー（news_nlp / regime_detector で使用）
   - 任意:
     - KABUSYS_ENV : development / paper_trading / live（デフォルト: development）
     - LOG_LEVEL : DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）
     - DUCKDB_PATH : DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH : SQLite (monitoring) のパス（デフォルト data/monitoring.db）
   - .env の自動ロード:
     - パッケージ起動時にプロジェクトルート（.git または pyproject.toml を探索）から `.env` → `.env.local` を順に読み込みます。
     - 自動ロードを無効にする: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

4. データベース初期化（監査ログ等）
   - 監査 DB 初期化例:
     - from kabusys.data.audit import init_audit_db
     - conn = init_audit_db("data/audit.duckdb")
   - ETL などで使用する DuckDB ファイルはデフォルトで data/kabusys.duckdb を想定します。必要に応じて環境変数 DUCKDB_PATH を設定してください。

---

## 使い方（代表的な API / 実行例）

以下は Python REPL / スクリプト内での利用例です。各関数は DuckDB の接続オブジェクトを受け取ります（duckdb.connect(...) を使ってください）。

1. DuckDB 接続
   - import duckdb
   - conn = duckdb.connect("data/kabusys.duckdb")

2. 日次 ETL の実行
   - from kabusys.data.pipeline import run_daily_etl
   - from datetime import date
   - result = run_daily_etl(conn, target_date=date(2026, 3, 20))
   - print(result.to_dict())

   run_daily_etl は ETLResult を返します。内部でカレンダー ETL → 価格 ETL → 財務 ETL → 品質チェックを順に実行します。

3. ニューススコア（銘柄別センチメント）の取得
   - from kabusys.ai.news_nlp import score_news
   - from datetime import date
   - n = score_news(conn, date(2026, 3, 20), api_key="sk-...")
   - print(f"scored {n} symbols")

   api_key を省略すると環境変数 OPENAI_API_KEY が使われます。news_nlp はタイムウィンドウ（前日15:00 JST〜当日08:30 JST）に基づいて記事を集約しスコアを ai_scores テーブルに置換保存します。

4. 市場レジーム判定
   - from kabusys.ai.regime_detector import score_regime
   - from datetime import date
   - score_regime(conn, date(2026, 3, 20), api_key="sk-...")

   ETF 1321 の MA200 乖離とマクロニュース LLM スコアを合成して market_regime テーブルへ書き込みます。

5. 研究用ファクター計算例
   - from kabusys.research import calc_momentum, calc_value, calc_volatility
   - from datetime import date
   - mom = calc_momentum(conn, date(2026, 3, 20))
   - val = calc_value(conn, date(2026, 3, 20))
   - vol = calc_volatility(conn, date(2026, 3, 20))

6. データ品質チェック
   - from kabusys.data.quality import run_all_checks
   - issues = run_all_checks(conn, target_date=date(2026,3,20))
   - for i in issues: print(i)

7. カレンダー関連ユーティリティ
   - from kabusys.data.calendar_management import is_trading_day, next_trading_day, get_trading_days
   - is_trading_day(conn, date(2026,3,20))
   - next_trading_day(conn, date(2026,3,20))
   - get_trading_days(conn, date(2026,3,1), date(2026,3,31))

注意点:
- 多くの関数は外部 API（J-Quants / OpenAI）に依存します。テスト時は各モジュール内の _call_openai_api やネットワーク呼び出しをモックしてください（ドキュメント内の注記あり）。
- ルックアヘッドバイアス防止のため、各モジュールは基本的に date / target_date を外部から与える設計です。内部で datetime.today() を参照しないことが意識されています。

---

## 主な環境変数一覧

- JQUANTS_REFRESH_TOKEN (必須)
- OPENAI_API_KEY (score_news / score_regime 用)
- KABU_API_PASSWORD (kabuステーション API)
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- SLACK_BOT_TOKEN / SLACK_CHANNEL_ID (Slack 通知)
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db)
- KABUSYS_ENV (development | paper_trading | live) - 環境モード
- LOG_LEVEL (ログレベル)

.env をプロジェクトルートに置くことで自動的に読み込まれます（.env.local は上書き優先）。自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1。

---

## 主要ディレクトリ構成（抜粋）

- src/kabusys/
  - __init__.py
  - config.py                      — 環境変数/設定管理（.env 自動ロード含む）
  - ai/
    - __init__.py
    - news_nlp.py                   — ニュースセンチメント解析（OpenAI 経由）
    - regime_detector.py            — 市場レジーム判定（MA + マクロセンチメント）
  - data/
    - __init__.py
    - calendar_management.py        — 市場カレンダー管理・営業日判定
    - pipeline.py                   — ETL パイプライン（run_daily_etl 等）
    - jquants_client.py             — J-Quants API クライアント（fetch/save）
    - news_collector.py             — RSS ニュース収集・前処理
    - quality.py                    — データ品質チェック
    - stats.py                      — 共通統計ユーティリティ（zscore_normalize 等）
    - audit.py                      — 監査（signal/order/execution）スキーマ & 初期化
    - etl.py                        — ETLResult の再エクスポート
  - research/
    - __init__.py
    - factor_research.py            — ファクター計算（momentum, value, volatility）
    - feature_exploration.py        — 将来リターン, IC, 統計サマリー
  - (その他) strategy / execution / monitoring パッケージの想定エクスポートあり

---

## 開発・テストに関する補足

- 環境変数の自動ロードは config.py により .env / .env.local をプロジェクトルートから読み込みます。ユニットテストや CI では KABUSYS_DISABLE_AUTO_ENV_LOAD を設定して自動ロードを無効にできます。
- OpenAI 呼び出しや外部 HTTP 呼び出しは内部で個別のラッパー関数（例: _call_openai_api, _urlopen）を使っているため、これらを mock してテスト可能です。
- DuckDB に対する executemany の空リスト渡し等、バージョン依存の振る舞いに対する注意が各所にコメントとして残されています（テスト時は DuckDB バージョンに注意してください）。

---

## ライセンス / 貢献

この README はコードベースに基づく概要と利用法をまとめたものです。実運用・発注に使用する際は十分なレビューとテストを行ってください。外部 API キーや発注機能を有効にする前に、paper_trading モード等で安全に検証してください。

ご不明点や追加でほしいドキュメント（API リファレンス、データスキーマ一覧、運用手順など）があればお知らせください。