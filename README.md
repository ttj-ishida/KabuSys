# KabuSys

日本株向けの自動売買 / データ基盤ライブラリ群です。  
J-Quants API からデータを取得して DuckDB に格納・品質チェックを行い、ニュース NLP や LLM ベースの市場レジーム判定、研究用ファクター計算、監査ログ（発注〜約定トレース）などを提供します。

主な設計方針
- ルックアヘッドバイアス回避（内部で date.today() を直接参照しない設計）
- DuckDB をローカルデータレイヤに利用（高速分析とトランザクション制御）
- 外部 API 呼び出しはリトライ／レート制御／フェイルセーフを実装
- 冪等性（ETL / DB 保存は ON CONFLICT を利用）と監査性重視

---

## 機能一覧
- データ ETL（J-Quants）  
  - 日次株価（OHLCV）、財務データ、JPX カレンダーの差分取得と保存
  - レート制限・トークン自動リフレッシュ・ページネーション対応
- ニュース収集（RSS）および前処理（SSRF 対策、トラッキングパラメータ除去、サイズ制限）
- ニュース NLP（OpenAI）  
  - 銘柄ごとのニュースセンチメントを ai_scores に書き込む（gpt-4o-mini を想定）
  - バッチ送信・リトライ・レスポンス検証・スコアクリップ
- 市場レジーム判定（AI + 1321 ETF の MA200 乖離を合成）  
  - ma200 のウェイト 70%、マクロニュース（LLM）30% で 'bull' / 'neutral' / 'bear' を決定
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- マーケットカレンダー管理（営業日判定、next/prev/get_trading_days）
- 研究用モジュール（ファクター計算、将来リターン、IC、統計サマリー、Zスコア正規化）
- 監査ログ（signal_events / order_requests / executions）の初期化ユーティリティ
- 設定管理（.env 自動読み込み、環境変数保護）

---

## 動作環境 / 依存ライブラリ（例）
- Python 3.9+（型ヒントに合わせて）
- 必須パッケージ（代表例）:
  - duckdb
  - openai
  - defusedxml
- その他: 標準ライブラリの urllib / datetime / logging 等

（プロジェクトの pyproject.toml / requirements.txt があればそれに従ってください）

---

## インストール（開発環境例）
1. 仮想環境を作成
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. パッケージのインストール（開発環境の例）
   - pip install -e .
   - pip install duckdb openai defusedxml

（プロジェクトがパッケージとしてセットアップされている前提のコマンド例です。適宜 requirements ファイルや pyproject.toml を使ってください）

---

## 設定（環境変数 / .env）
プロジェクトルート（.git または pyproject.toml のある階層）に `.env` / `.env.local` を置くと、自動で読み込まれます（自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。

主要な環境変数:
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN / SLACK_CHANNEL_ID: Slack 通知用（必須）
- DUCKDB_PATH: デフォルト DuckDB ファイルパス（例: data/kabusys.duckdb）
- SQLITE_PATH: 監視系 SQLite（例: data/monitoring.db）
- KABUSYS_ENV: 環境 ("development" | "paper_trading" | "live")（デフォルト: development）
- LOG_LEVEL: "DEBUG" / "INFO" / "WARNING" / "ERROR" / "CRITICAL"

.sample .env の例:
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=your_openai_api_key
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C12345678
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO

注意:
- .env.local は .env より優先して上書きされます
- OS 環境変数は .env による上書きから保護されます

---

## セットアップ手順（データベース初期化例）
1. DuckDB ファイルを作成・接続（Python）
   - import duckdb
   - conn = duckdb.connect(str(path_to_duckdb))

2. 監査ログ用 DB 初期化（専用 DB に分離する場合）
   - from kabusys.data.audit import init_audit_db
   - conn_audit = init_audit_db("data/audit.duckdb")
   - これにより required DDL とインデックスが作成されます。

3. （必要に応じて）マイグレーションやスキーマ初期化ユーティリティをプロジェクト側で用意している場合はそちらを実行してください（本コードベースでは audit 用の初期化ユーティリティを提供）。

---

## 使い方（代表的な呼び出し例）

- 日次 ETL 実行（J-Quants → DuckDB、品質チェック含む）
  - from datetime import date
  - import duckdb
  - from kabusys.data.pipeline import run_daily_etl
  - conn = duckdb.connect("data/kabusys.duckdb")
  - result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  - print(result.to_dict())

- ニュースセンチメントスコアの作成（ai_scores へ書き込み）
  - from datetime import date
  - import duckdb
  - from kabusys.ai.news_nlp import score_news
  - conn = duckdb.connect("data/kabusys.duckdb")
  - n_written = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
  - print("書込件数:", n_written)

- 市場レジーム判定（market_regime テーブルへ書き込み）
  - from datetime import date
  - import duckdb
  - from kabusys.ai.regime_detector import score_regime
  - conn = duckdb.connect("data/kabusys.duckdb")
  - score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")

- 監査ログ DB 初期化（専用ファイル）
  - from kabusys.data.audit import init_audit_db
  - conn_audit = init_audit_db("data/audit.duckdb")

- 研究系関数例（ファクター・IC 等）
  - from datetime import date
  - import duckdb
  - from kabusys.research import calc_momentum, calc_value, calc_volatility, calc_forward_returns, calc_ic
  - conn = duckdb.connect("data/kabusys.duckdb")
  - fm = calc_momentum(conn, date(2026,3,20))
  - fv = calc_value(conn, date(2026,3,20))
  - fr = calc_forward_returns(conn, date(2026,3,20))
  - ic = calc_ic(fm, fr, "mom_1m", "fwd_1d")

注意点:
- OpenAI を使う関数（score_news / score_regime）は OPENAI_API_KEY または api_key 引数が必要です。
- DuckDB のテーブルスキーマ（raw_prices, raw_financials, raw_news, news_symbols, ai_scores, market_regime, market_calendar など）は ETL / 他のモジュールに依存します。実行前に必要テーブルが存在していることを確認してください（audit モジュールは初期化ユーティリティを提供しています）。

---

## 主要ディレクトリ構成（src 配下）
- src/kabusys/
  - __init__.py
  - config.py                        — 環境変数 / .env 自動ロード、Settings
  - ai/
    - __init__.py
    - news_nlp.py                     — ニュース NLP（score_news）
    - regime_detector.py              — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - pipeline.py                     — ETL パイプライン（run_daily_etl 等）
    - jquants_client.py               — J-Quants API クライアント（fetch/save 系）
    - news_collector.py               — RSS 収集・前処理
    - calendar_management.py          — 市場カレンダー管理 / カレンダー ETL
    - quality.py                      — データ品質チェック
    - stats.py                        — 汎用統計ユーティリティ（zscore）
    - audit.py                        — 監査ログ（DDL・初期化ユーティリティ）
    - etl.py                          — ETLResult 再エクスポート
  - research/
    - __init__.py
    - factor_research.py              — Momentum / Value / Volatility 計算
    - feature_exploration.py          — 将来リターン / IC / 統計サマリー / rank

---

## 運用上の注意 / ベストプラクティス
- 自動ロードされる .env はプロジェクトルートを .git / pyproject.toml から探索します。テスト時や一部環境では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動ロードを抑制できます。
- OpenAI / J-Quants の API 呼び出しはコスト・レート制限の対象です。バックテストやローカル検証時は mock を使うことを推奨します（score_news 等は内部 _call_openai_api を patch 可能）。
- ETL は部分失敗を想定し一部処理が失敗しても他処理を継続する設計です。ETLResult で問題の有無を確認してください。
- DuckDB の executemany に空リストを渡すと例外となるバージョンがあるため、空チェックが実装されています。独自処理を追加する際は同点に注意してください。
- 監査ログは削除しない方針（ON DELETE RESTRICT 等）です。消去は慎重に。

---

## 開発・コントリビュート
- コードのスタイルやテストはプロジェクトの既存ルールに従ってください。AI / API 呼び出し部分は外部依存があるため、ユニットテストでは外部クライアント（OpenAI / J-Quants 呼び出し）をモックしてください。
- .env.example をリポジトリに含め、機密情報は絶対にコミットしないでください。

---

必要であれば、README にユニットテストの実行方法、CI 設定、詳細な DB スキーマ定義やサンプル .env.example を追記できます。どの情報を追加しますか？