# KabuSys

日本株向けの自動売買 / データプラットフォームライブラリです。  
ETL（J-Quants からの株価・財務・カレンダー取得）、ニュース収集・NLP（OpenAI）、市場レジーム判定、研究用ファクター計算、監査ログなどの機能を提供します。

## 主な特徴（プロジェクト概要）
- J-Quants API からの差分 ETL（株価 / 財務 / JPX カレンダー）をサポート。DuckDB に冪等的に保存。
- RSS ベースのニュース収集と前処理（SSRF 対策・トラッキング除去）。
- OpenAI（gpt-4o-mini）を利用したニュースセンチメント／マクロ評価（JSON Mode 対応、リトライ・フォールバック実装）。
- 市場レジーム判定（ETF 1321 の MA200 とマクロセンチメントの重み合成）。
- 研究支援モジュール（ファクター計算、将来リターン、IC、統計サマリー、Zスコア正規化）。
- データ品質チェック（欠損・スパイク・重複・日付不整合検出）。
- 監査ログ（signal -> order_request -> execution のトレーサビリティ）用スキーマ初期化ユーティリティ。

## 機能一覧
- データ取得 / 保存
  - ETL（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - J-Quants クライアント（fetch_* / save_*）
- ニュース
  - RSS 取得（fetch_rss）、前処理（preprocess_text）、記事ID生成
  - ニュース NLP（score_news）：銘柄単位にセンチメントを生成して ai_scores に保存
- AI / レジーム
  - マクロレジーム判定（score_regime）：MA200 と LLM マクロスコアを合成して market_regime に保存
  - ニュース NLP（score_news）を別モジュールで提供（テスト容易性を考慮）
- 研究（research）
  - ファクター計算（momentum / value / volatility）
  - 特徴量探索（calc_forward_returns / calc_ic / factor_summary / rank）
  - zscore_normalize（data.stats）
- データ品質（data.quality）
  - check_missing_data, check_spike, check_duplicates, check_date_consistency, run_all_checks
- カレンダー管理（data.calendar_management）
  - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day
  - calendar_update_job（J-Quants からの差分取得と保存）
- 監査ログ（data.audit）
  - init_audit_schema, init_audit_db（DuckDB 初期化・インデックス作成）
- ユーティリティ
  - 環境変数管理（kabusys.config.Settings）と自動 .env 読み込み（プロジェクトルート検出）

## セットアップ手順

前提
- Python 3.9 以上（タイプヒントに Union | を使っています。プロジェクト要件に合わせて適宜調整してください）
- OS 標準のネットワークアクセス（J-Quants / OpenAI / RSS に接続するため）

1. 仮想環境を作成・有効化（推奨）
   - venv 例:
     ```
     python -m venv .venv
     source .venv/bin/activate  # macOS / Linux
     .venv\Scripts\activate     # Windows
     ```

2. 必要パッケージをインストール
   - 代表的な依存（プロジェクトに pyproject.toml がある場合はそちらを使用してください）:
     ```
     pip install duckdb openai defusedxml
     ```
   - 他に標準ライブラリでまかなえる実装になっていますが、実行環境に合わせて追加で依存がある場合があります。

3. 環境変数の設定
   - 必須（Settings で _require として使われるもの）:
     - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
     - SLACK_BOT_TOKEN : Slack 通知を使う場合
     - SLACK_CHANNEL_ID : Slack チャンネル ID
     - KABU_API_PASSWORD : kabu API パスワード（発注等を行う場合）
   - 推奨 / 省略可:
     - KABUSYS_ENV : development / paper_trading / live（デフォルト: development）
     - LOG_LEVEL : DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
     - OPENAI_API_KEY : OpenAI API キー（score_news/score_regime 呼び出し時に引数で渡すことも可能）
     - DUCKDB_PATH : デフォルト data/kabusys.duckdb
     - SQLITE_PATH : 監視用 SQLite（default: data/monitoring.db）
   - .env 自動ロード:
     - プロジェクトルート（.git または pyproject.toml を基準）にある `.env` と `.env.local` を自動で読み込みます。
     - 読み込み優先度: OS 環境変数 > .env.local > .env
     - 自動ロードをオフにする場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

4. DB 初期化（監査ログ用など）
   - 監査 DB を作るサンプル:
     ```python
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")  # ":memory:" も可
     ```
   - 既存の DuckDB 接続に監査スキーマを追加する:
     ```python
     from kabusys.data.audit import init_audit_schema
     init_audit_schema(conn, transactional=True)
     ```

## 使い方（簡単な例）

- DuckDB 接続を作成して ETL を実行する（日次 ETL の例）:
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメントを評価して ai_scores に書き込む:
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  n_written = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
  print(f"wrote {n_written} scores")
  ```

- 市場レジームを判定して market_regime に保存する:
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")
  ```

- 研究用ファクター計算:
  ```python
  import duckdb
  from datetime import date
  from kabusys.research.factor_research import calc_momentum

  conn = duckdb.connect("data/kabusys.duckdb")
  records = calc_momentum(conn, date(2026, 3, 20))
  ```

- データ品質チェック:
  ```python
  from kabusys.data.quality import run_all_checks
  issues = run_all_checks(conn, target_date=date(2026,3,20))
  for i in issues:
      print(i)
  ```

## 環境変数（主なもの）
- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabu ステーション API のパスワード
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack 通知用ボットトークン
- SLACK_CHANNEL_ID (必須) — Slack チャンネル ID
- OPENAI_API_KEY — OpenAI API キー（score_news/score_regime で使用）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite（監視用）パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 環境: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — ログレベル（デフォルト: INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env 読み込みを無効化するには 1 を設定

※ .env.example を作成してチームで共有することを推奨します。

## ディレクトリ構成（主要ファイル）
（パッケージは src/kabusys 以下に配置されています）

- src/kabusys
  - __init__.py
  - config.py                 — 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py             — ニュースの NLP スコアリング（score_news）
    - regime_detector.py      — マクロ + MA200 による市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py       — J-Quants API クライアント（fetch / save）
    - pipeline.py             — ETL パイプライン（run_daily_etl 他）
    - etl.py                  — ETLResult エクスポート
    - stats.py                — zscore_normalize 等ユーティリティ
    - quality.py              — データ品質チェック
    - news_collector.py       — RSS 収集 / 前処理
    - calendar_management.py  — 市場カレンダー管理（is_trading_day 等）
    - audit.py                — 監査ログスキーマ初期化（init_audit_schema / init_audit_db）
  - research/
    - __init__.py
    - factor_research.py      — モメンタム / バリュー / ボラティリティ計算
    - feature_exploration.py  — 将来リターン / IC / 統計サマリー 等
  - monitoring/ (ディレクトリが含まれる想定: 監視関連モジュールなど)
  - execution/ (発注実装 / ブローカー連携のためのモジュールを想定)
  - strategy/ (戦略定義・シグナル生成用モジュールを想定)

（上記はコードベースの主要モジュールを抜粋した構成です）

## テスト・開発時の注意点 / 設計上のポイント
- Look-ahead バイアス対策:
  - 多くの関数は date.today() や datetime.today() を直接参照せず、target_date を受け取る実装になっています。バックテスト時は必ず過去の target_date を指定してください。
- AI 呼び出しのフェイルセーフ:
  - OpenAI API エラーやパースエラー時はフォールバック（スコア = 0.0）する設計で、処理全体が中断しないようにしています。
- ETL の冪等性:
  - save_* 関数は ON CONFLICT DO UPDATE を利用しているため、再実行してもデータを上書きして整合性を保ちます。
- DuckDB の executemany に空リストを渡すと問題になるバージョンがあるため、実装は空チェックをしています。
- テスト容易性:
  - OpenAI 呼び出しなどをモックしやすいように内部呼び出し関数を分離しています（unittest.mock.patch で差し替え可能）。

## ライセンス・貢献
- 本 README ではライセンスは明示していません。公開する際は LICENSE ファイルを追加してください。
- 貢献の際は機能単位で PR を分け、テストケース・ドキュメントを添付してください。

---

質問・補足の要望があれば、導入方法の詳細（pyproject.toml に合わせたインストール手順、実運用でのデプロイ手順、監視 / ロギング構成例 等）を追記します。