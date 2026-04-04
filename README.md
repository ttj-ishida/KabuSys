# KabuSys

日本株向けの自動売買／データ基盤ライブラリ群です。  
ETL（J-Quants → DuckDB）、ニュース収集・NLPスコアリング、研究用ファクター計算、監査ログ（発注→約定トレーサビリティ）、マーケットカレンダー管理、AIを用いた市場レジーム判定などの機能を提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は日本株のデータパイプラインとリサーチ／自動売買のための共通ユーティリティ群です。  
主な役割は以下の通りです：

- J-Quants API からの差分ETL（株価・財務・マーケットカレンダー）
- RSS ベースのニュース収集と銘柄紐付け
- OpenAI を使ったニュース（銘柄）センチメントスコアリング
- マーケットレジーム判定（ETF とマクロニュースの融合）
- ファクター計算（モメンタム・バリュー・ボラティリティ等）と探索用ユーティリティ
- データ品質チェック
- 監査ログ（signal → order_request → execution）用スキーマ初期化ユーティリティ
- DuckDB を中心とした軽量なローカルデータストア

設計方針として、ルックアヘッドバイアス回避、APIの堅牢なリトライ/レート制御、冪等性・監査性の確保が重視されています。

---

## 機能一覧

- データETL
  - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl（kabusys.data.pipeline）
  - J-Quants API クライアント（kabusys.data.jquants_client）
  - 差分取得・ページネーション・リトライ・トークン自動更新
- ニュース収集
  - RSS フィード取得、記事正規化、SSRF 対策、raw_news への冪等保存（kabusys.data.news_collector）
- ニュースNLP（OpenAI）
  - 銘柄別ニュースのまとめ → ai_scores テーブルへ保存（kabusys.ai.news_nlp）
  - 市場マクロセンチメントを含めたレジーム判定（kabusys.ai.regime_detector）
- 研究／ファクター
  - calc_momentum / calc_volatility / calc_value（kabusys.research.factor_research）
  - 将来リターン計算・IC・統計サマリー（kabusys.research.feature_exploration）
  - 共通統計ユーティリティ zscore_normalize（kabusys.data.stats）
- データ品質
  - 欠損・重複・スパイク・日付不整合チェック（kabusys.data.quality）
- カレンダー管理
  - 営業日判定、next/prev_trading_day、calendar_update_job（kabusys.data.calendar_management）
- 監査ログ
  - audit スキーマ初期化 / 専用 DB 初期化（kabusys.data.audit）

---

## 必要条件（推奨）

- Python 3.10+
- 依存パッケージ（抜粋）
  - duckdb
  - openai (v1 SDK を想定)
  - defusedxml
  - その他: 標準ライブラリで賄える部分が多いですが、実行環境によって urllib 等が必要です

具体的な requirements ファイルはプロジェクトに応じて用意してください。

---

## 環境変数 / .env

パッケージは .env（および .env.local）から自動読み込みします（プロジェクトルートに .git か pyproject.toml がある場合）。自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

主要な環境変数:

- J-Quants / データ取得
  - JQUANTS_REFRESH_TOKEN (必須)
- kabuステーション API
  - KABU_API_PASSWORD
  - KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- OpenAI / AI
  - OPENAI_API_KEY (news_nlp / regime_detector で使用)
- LINE 通知（任意）
  - LINE_CHANNEL_ACCESS_TOKEN
  - LINE_USER_ID
- DB / ファイルパス
  - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
  - SQLITE_PATH (デフォルト: data/monitoring.db)
  - PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START
- システム設定
  - KABUSYS_ENV (development / paper_trading / live) — 有効値が制約されます
  - LOG_LEVEL (DEBUG / INFO / WARNING / ERROR / CRITICAL)

.env.example を用意し、そこから .env を作成して設定してください。

---

## セットアップ手順（例）

1. リポジトリをクローン
   - git clone <repo-url>
2. 仮想環境作成（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存パッケージをインストール
   - pip install duckdb openai defusedxml
   - （プロジェクトに requirements.txt があれば pip install -r requirements.txt）
4. .env を作成して必要な環境変数を設定
   - cp .env.example .env
   - 編集して JQUANTS_REFRESH_TOKEN, OPENAI_API_KEY 等を設定
5. データディレクトリ作成
   - mkdir -p data
6. 監査ログ用 DuckDB を初期化（任意 / 推奨）
   - Python から:
     - from kabusys.data.audit import init_audit_db
     - conn = init_audit_db("data/audit.duckdb")
   - これにより監査テーブル群（signal_events / order_requests / executions）を作成します

注意: ETL の実行や AI スコアリングを行うためには、必要なテーブルスキーマ（raw_prices, raw_financials, raw_news, news_symbols, ai_scores, prices_daily, market_regime, market_calendar など）が存在している必要があります。プロジェクトの schema 初期化スクリプト/マイグレーションが別途ある場合はそちらを使用してください。

---

## 使い方（例）

以下は Python REPL / スクリプトから主要機能を呼ぶサンプルです。

- DuckDB に接続して日次 ETL を実行（run_daily_etl）

  python -c の例:
  ```bash
  python - <<'PY'
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  PY
  ```

- ニュースセンチメントスコアを計算して ai_scores に保存

  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  # OPENAI_API_KEY は環境変数、もしくは第3引数で指定
  count = score_news(conn, target_date=date(2026, 3, 20))
  print(f"書き込み銘柄数: {count}")
  ```

- 市場レジームをスコアリングして market_regime に保存

  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 研究用ファクター計算（例: モメンタム）

  ```python
  from datetime import date
  import duckdb
  from kabusys.research.factor_research import calc_momentum

  conn = duckdb.connect("data/kabusys.duckdb")
  records = calc_momentum(conn, target_date=date(2026, 3, 20))
  print(len(records), records[:3])
  ```

- テスト／開発時の環境変数自動読み込みを抑制する
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を環境に設定すると .env の自動読み込みを無効化できます。

---

## 注意点 / 運用メモ

- OpenAI 呼び出しや外部 API はレートや失敗に対して堅牢なリトライ・フォールバックを実装していますが、API キーやネットワークの問題によりスコア取得に失敗することがあります。失敗時はフェイルセーフとしてゼロやスキップで継続する設計（例: macro_sentiment=0.0）です。
- DuckDB の executemany に関するバージョン依存の注意点がコード内にもあり（空リストの扱い等）、DuckDB バージョン差異に注意してください。
- 監査ログは削除しない前提です。運用ではディスク管理やバックアップ戦略を策定してください。
- KABUSYS_ENV が `live` の場合は特に注意してログレベル・実際の発注フロー（もし統合している場合）を確認してください。

---

## ディレクトリ構成（主要ファイル）

プロジェクトの主要モジュール配置（src/kabusys）:

- src/kabusys/
  - __init__.py
  - config.py                     — 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py                  — ニュース NLU / スコアリング
    - regime_detector.py           — マーケットレジーム判定
  - data/
    - __init__.py
    - jquants_client.py            — J-Quants API クライアント（取得・保存）
    - pipeline.py                  — ETL パイプライン（run_daily_etl 等）
    - etl.py                       — ETL 結果型 再エクスポート
    - news_collector.py            — RSS 収集
    - calendar_management.py       — マーケットカレンダー管理
    - quality.py                   — データ品質チェック
    - stats.py                     — 統計ユーティリティ（zscore_normalize）
    - audit.py                     — 監査ログスキーマ初期化
  - research/
    - __init__.py
    - factor_research.py           — モメンタム / バリュー / ボラティリティ
    - feature_exploration.py       — 将来リターン / IC / サマリー
  - research/（他）
  - monitoring / strategy / execution 等（システムの別モジュールと想定）

（注）一部ファイルは README 生成時点で切り出しや追加が想定されます。プロジェクト全体のツリーは実際のリポジトリを参照してください。

---

## 開発・テスト

- 自動環境変数ロードを無効化: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`
- OpenAI 呼び出し箇所はユニットテストでモック可能（各モジュールに _call_openai_api の注入箇所あり）
- ネットワーク依存の機能（J-Quants / RSS / OpenAI）はテスト時にモックすることを推奨

---

必要であれば、README に実行スクリプト例・SQL スキーマの初期化手順・requirements.txt の具体的内容・CI ワークフロー例などを追記します。どの情報が必要か教えてください。