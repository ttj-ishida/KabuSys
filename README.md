# KabuSys

KabuSys は日本株向けの自動売買／データプラットフォーム用ライブラリ群です。  
データ ETL、ニュース NLP（LLM）による銘柄センチメント評価、市場レジーム判定、研究用ファクター計算、監査ログ（トレーサビリティ）などの機能を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

このパッケージは以下の主要コンポーネントを含みます。

- data: J-Quants からのデータ取得（株価・財務・市場カレンダー）、ETL パイプライン、データ品質チェック、ニュース収集、監査ログ用スキーマ等
- ai: ニュースの NL P／LLM スコアリング（gpt-4o-mini 想定）、市場レジーム判定ロジック
- research: ファクター計算（モメンタム / バリュー / ボラティリティ）や特徴量探索ユーティリティ
- config: 環境変数・設定管理（.env 自動読み込み機能含む）
- monitoring / execution / strategy 等（パッケージ公開インターフェースに含まれる想定）

設計における主な方針:
- ルックアヘッドバイアス防止（内部で date.today()/datetime.today() を無条件に参照しない）
- DuckDB をデータプラットフォームのローカル DB として利用
- OpenAI（LLM）呼び出しは冪等性・リトライ・フォールバック（失敗時の安全なデフォルト）を考慮
- ETL は差分更新・バックフィル・品質チェックを備える

---

## 機能一覧

主な機能（抜粋）:

- ETL
  - run_daily_etl: 株価（raw_prices）、財務（raw_financials）、市場カレンダーを差分取得して保存
  - run_prices_etl / run_financials_etl / run_calendar_etl: 個別ジョブ
  - jquants_client: API 呼び出し + 保存関数（save_*）・認証（get_id_token）
- データ品質チェック
  - 欠損、スパイク、重複、日付不整合の検出（quality.run_all_checks）
- ニュース収集
  - RSS フィード取得（fetch_rss）、前処理、raw_news への保存想定
  - SSRF やサイズ制限等の安全対策実装
- AI / NLP
  - score_news: OpenAI で銘柄ごとのニュースセンチメントを算出し ai_scores に保存
  - score_regime: ETF（1321）の MA200 乖離とマクロニュースセンチメントを合成し市場レジームを market_regime に保存
  - リトライ・エラーハンドリング・JSON モード利用（厳格な JSON 出力期待）
- 研究用ユーティリティ
  - calc_momentum / calc_value / calc_volatility: ファクター計算
  - calc_forward_returns / calc_ic / factor_summary: 特徴量探索・評価ツール
  - zscore_normalize: クロスセクション正規化
- 監査（Audit）
  - init_audit_db / init_audit_schema: signal / order_request / execution を格納する監査テーブルを初期化

---

## 前提条件

- Python 3.10+
  - タイプヒントで PEP 604（X | Y）を使用しているため 3.10 以上を推奨します
- 必要な主要ライブラリ（例）
  - duckdb
  - openai (v1 SDK など、OpenAI.OpenAI クライアントを提供するバージョン)
  - defusedxml
- ネットワークアクセス（J-Quants API、OpenAI、RSS）
- J-Quants / OpenAI の API キーなどの環境変数

（プロジェクト配布時には requirements.txt / pyproject.toml を参照してください）

---

## セットアップ手順

1. リポジトリをクローン
   - git clone <repo-url>

2. 仮想環境を作る（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install -U pip
   - pip install duckdb openai defusedxml

   ※実際のプロジェクトでは pip install -e . や pyproject.toml に基づくインストールを推奨

4. 環境変数 (.env) を準備
   - プロジェクトルート（.git または pyproject.toml のあるディレクトリ）に `.env` / `.env.local` を置くと自動読み込みされます
   - 自動ロードを無効化する場合: export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

必須環境変数（主なもの）
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（get_id_token に使用）
- OPENAI_API_KEY: OpenAI API キー（score_news / score_regime などで使用）
- KABU_API_PASSWORD: kabu ステーション API のパスワード（注文連携を行う場合）
- SLACK_BOT_TOKEN: Slack 通知を行う場合の Bot トークン
- SLACK_CHANNEL_ID: Slack 通知先チャンネル ID

オプション / 設定例（デフォルト値はコード参照）
- KABUSYS_ENV: development / paper_trading / live
- LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 で .env 自動読み込み無効化
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（監視用 DB、デフォルト: data/monitoring.db）
- PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT

簡単な .env 例:
KABUSYS_ENV=development
OPENAI_API_KEY=sk-...
JQUANTS_REFRESH_TOKEN=xxxxxxxx
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C12345678
DUCKDB_PATH=data/kabusys.duckdb

---

## 使い方（簡単なコード例）

以下は Python REPL / スクリプト内から利用する例です。import パスはパッケージのインストール形態により調整してください。

- DuckDB 接続を作成して ETL を実行する
  - from datetime import date
  - import duckdb
  - from kabusys.data.pipeline import run_daily_etl
  - conn = duckdb.connect(str(<your_duckdb_path>))
  - result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  - print(result.to_dict())

- ニューススコアリング（score_news）
  - from datetime import date
  - import duckdb
  - from kabusys.ai.news_nlp import score_news
  - conn = duckdb.connect("data/kabusys.duckdb")
  - n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # None の場合環境変数 OPENAI_API_KEY を参照
  - print("written", n_written)

- 市場レジーム判定（score_regime）
  - from datetime import date
  - import duckdb
  - from kabusys.ai.regime_detector import score_regime
  - conn = duckdb.connect("data/kabusys.duckdb")
  - score_regime(conn, target_date=date(2026, 3, 20))

- 監査 DB の初期化
  - from kabusys.data.audit import init_audit_db
  - conn = init_audit_db("data/audit.duckdb")
  - # これで signal_events / order_requests / executions テーブルが作成されます

注意点:
- score_news / score_regime は OpenAI API を呼ぶためコストとレート制限に注意してください。API 呼び出しはリトライやフォールバック（失敗時は 0.0 を返す等）を備えていますが、キーは必須です。
- run_daily_etl は jquants_client を使って J-Quants API を呼びます。J-Quants トークン（JQUANTS_REFRESH_TOKEN）が必要です。
- 自動 .env ロード: パッケージロード時にプロジェクトルートの `.env` → `.env.local` を順に読み込みます。テストで無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD をセットしてください。

---

## よくある操作（CLI 風 / スクリプト化のヒント）

- 定期バッチ（cron / systemd timer）で day-end に run_daily_etl を呼ぶ
- ニュース収集は RSS ソースを定期的にフェッチして raw_news / news_symbols を更新 → score_news を実行
- market_regime は日次（営業日）で算出して market_regime テーブルへ保存
- 監視: PID ファイルや resource 閾値は config.Settings に設定（PID_FILE_PATH, CPU/MEM/DISK thresholds）

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py
- config.py                      — 環境変数 / 設定管理（.env 自動読み込み）
- ai/
  - __init__.py
  - news_nlp.py                   — ニュース NLP / score_news
  - regime_detector.py            — 市場レジーム判定 / score_regime
- data/
  - __init__.py
  - jquants_client.py             — J-Quants API クライアント（fetch/save）
  - pipeline.py                   — ETL パイプライン、run_daily_etl 等
  - etl.py                        — ETLResult の再エクスポート
  - quality.py                    — データ品質チェック
  - news_collector.py             — RSS 収集・前処理
  - calendar_management.py        — 市場カレンダー管理 / 営業日判定
  - stats.py                      — zscore_normalize 等の統計ユーティリティ
  - audit.py                      — 監査ログテーブル定義 / 初期化
- research/
  - __init__.py
  - factor_research.py            — calc_momentum / calc_value / calc_volatility
  - feature_exploration.py        — calc_forward_returns / calc_ic / factor_summary / rank

（上記はコードベースから抽出した主なファイル群です）

---

## 開発・テストに関するメモ

- .env の自動読み込みはプロジェクトルートを基準に行うため、パッケージ配布後も CWD に依存せず動作します。テスト時には KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自前で環境を制御できます。
- OpenAI 呼び出しやネットワーク依存部分はテストでモッキングしやすいように実装されています。例: kabusys.ai.news_nlp._call_openai_api を patch する等。
- DuckDB 接続を用いた関数は副作用を DB に書きます。単体テストでは ":memory:" 接続等を使用してください。

---

## 注意事項

- 実際の発注機能（証券会社 API 連携、実運用）は慎重に行ってください。本コードは研究・自動化のフレームワークを提供しますが、実口座で使う場合は十分なリスク管理・テストが必須です。
- OpenAI や J-Quants の API 利用にはそれぞれの利用規約・課金が適用されます。API キーは秘匿して運用してください。

---

必要があれば README をプロジェクトの pyproject.toml / setup に合わせて調整したり、実行例のスクリプト（cron 用ラッパーや systemd サービス定義）を追加で作成します。どの部分を優先してドキュメント化しましょうか？