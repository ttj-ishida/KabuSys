KabuSys — 日本株自動売買 / データプラットフォーム
======================================

概要
---
KabuSys は日本株向けのデータプラットフォーム兼自動売買基盤のプロトタイプ実装です。  
主に以下の機能群を含みます。

- データ ETL（J-Quants からの日次株価・財務・マーケットカレンダー取得、DuckDB への保存）
- データ品質チェック（欠損・重複・スパイク・日付不整合）
- ニュース収集（RSS → raw_news）およびニュース NLP（OpenAI を用いた銘柄センチメント）
- 市場レジーム判定（ETF の MA とマクロニュースの LLM センチメントを合成）
- 監査ログ（シグナル → 発注 → 約定のトレーサビリティ用テーブル定義）
- リサーチ用ファクター計算・特徴量解析ユーティリティ（モメンタム、ボラティリティ、バリュー 等）

設計ポリシー（抜粋）
- ルックアヘッドバイアスに注意（内部で datetime.today() や date.today() を直接参照しない実装方針が各モジュールに適用されています）
- DuckDB を主要なローカルデータレイヤとして利用し、保存は冪等に実行
- 外部 API 呼び出しはリトライ・バックオフ・レート制御やフェイルセーフ（失敗時はスキップ等）を組み込んでいる

主な機能一覧
---
- ETL:
  - run_daily_etl（market calendar / daily prices / financials の差分取得 + 品質チェック）
  - run_prices_etl / run_financials_etl / run_calendar_etl（個別ジョブ）
- J-Quants クライアント:
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - save_daily_quotes / save_financial_statements / save_market_calendar
  - get_id_token（自動リフレッシュ対応）
- News:
  - fetch_rss（SSRF 対策・サイズ制限・URL 正規化）
  - news NLP: score_news（OpenAI を使った銘柄別センチメント、バッチ・JSON Mode）
- AI:
  - score_regime（ETF 1321 の MA とマクロニュース LLM 評価を合成して market_regime に保存）
  - news_nlp.score_news（ai_scores テーブルへ書き込み）
- Data quality:
  - check_missing_data / check_duplicates / check_spike / check_date_consistency / run_all_checks
- Research:
  - calc_momentum / calc_volatility / calc_value / calc_forward_returns / calc_ic / factor_summary / zscore_normalize
- 監査ログ:
  - init_audit_schema / init_audit_db（監査用テーブル群・インデックス作成）

セットアップ手順
---
※ 以下は一例です。プロジェクトに pyproject.toml / requirements.txt があればそちらを優先してください。

1. Python 環境
   - Python 3.10 以上を推奨（typing の Union 型短縮表記などが使用されています）

2. 仮想環境の作成（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージのインストール（例）
   - pip install duckdb openai defusedxml
   - （必要に応じて）pip install requests など、追加 HTTP 補助ライブラリ

   推奨パッケージ（本コードベースで明示的に参照される主なもの）
   - duckdb
   - openai
   - defusedxml

4. パッケージのローカルインストール（開発時）
   - pip install -e .

5. 環境変数 / .env
   - プロジェクトルート（.git や pyproject.toml を基準）に .env を置くと、自動で読み込まれます。
   - 自動ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

推奨 .env（例）
- JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
- KABU_API_PASSWORD=your_kabu_api_password
- SLACK_BOT_TOKEN=xoxb-...
- SLACK_CHANNEL_ID=C01234567
- OPENAI_API_KEY=sk-...
- DUCKDB_PATH=data/kabusys.duckdb
- SQLITE_PATH=data/monitoring.db
- KABUSYS_ENV=development
- LOG_LEVEL=INFO

使い方（クイックスタート）
---

1) DuckDB 接続を開き ETL を実行する（Python REPL / スクリプト）
- 例:
  from datetime import date
  import duckdb
  from kabusys.config import settings
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())

- 説明:
  run_daily_etl は market calendar → 株価 → 財務 → 品質チェック の順で差分 ETL を実行し ETLResult を返します。内部で J-Quants API を呼びます（settings.jquants_refresh_token が必要）。

2) ニュースセンチメント（OpenAI）を実行する
- 例:
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  written = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
  print(f"written {written} scores")

- 説明:
  score_news は指定日のニュースウィンドウ（前日15:00 JST ～ 当日08:30 JST）を対象に raw_news / news_symbols を集約し、OpenAI にバッチ送信して ai_scores テーブルに書き込みます。api_key を引数で渡すか環境変数 OPENAI_API_KEY を設定してください。

3) 市場レジームスコアを計算して保存する
- 例:
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20), api_key=None)  # 環境変数 OPENAI_API_KEY を利用

4) 監査ログ DB を初期化する
- 例:
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  # conn を使って order/exec テーブルへアクセス可能

環境変数一覧（主要）
---
- JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須 for ETL）
- KABU_API_PASSWORD: kabu ステーション API のパスワード
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN / SLACK_CHANNEL_ID: Slack 通知用
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト data/monitoring.db）
- KABUSYS_ENV: 開発環境フラグ（development, paper_trading, live）
- LOG_LEVEL: ログレベル（DEBUG, INFO, WARNING, ERROR, CRITICAL）
- OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector などで使用）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 を設定すると .env の自動ロードを無効化

ディレクトリ構成（主要ファイル）
---
src/kabusys/
- __init__.py              — パッケージ初期化、バージョン定義
- config.py                — 環境変数 / 設定読み込みロジック（.env 自動ロード等）
- ai/
  - __init__.py
  - news_nlp.py            — ニュースの LLM スコアリング（score_news）
  - regime_detector.py     — 市場レジーム判定（score_regime）
- data/
  - __init__.py
  - jquants_client.py      — J-Quants API クライアント（fetch/save, get_id_token）
  - pipeline.py            — ETL パイプライン（run_daily_etl 等）
  - etl.py                 — ETLResult の再エクスポート
  - calendar_management.py — マーケットカレンダー管理（is_trading_day 等）
  - news_collector.py      — RSS 収集・前処理・保存ロジック
  - quality.py             — データ品質チェック（QualityIssue, run_all_checks）
  - stats.py               — zscore_normalize 等の統計ユーティリティ
  - audit.py               — 監査ログテーブル定義 / 初期化
- research/
  - __init__.py
  - factor_research.py     — calc_momentum / calc_value / calc_volatility
  - feature_exploration.py — calc_forward_returns / calc_ic / factor_summary / rank
- ai, research, data ほかモジュールが含まれます

実装上の注記（重要）
---
- ルックアヘッドバイアス対策:
  - AI / リサーチ / ETL の多くの関数は target_date を引数に取り、内部で現在日時を参照しない設計になっています。バックテスト用途での誤用に注意してください。
- 冪等性:
  - save_* 関数は ON CONFLICT DO UPDATE を使い冪等に保存します。
- 外部 API 呼び出し:
  - J-Quants クライアントはレート制御（120 req/min）とリトライを実装しています。
  - OpenAI 呼び出しはリトライ戦略とレスポンス検証を行い、失敗時はフェイルセーフ（スコア 0 やスキップ）で継続します。
- セキュリティ / 安全性:
  - news_collector は SSRF 対策、XML の defusedxml 処理、レスポンスサイズ制限などを実装しています。

開発・テストのヒント
---
- .env の自動読み込みはプロジェクトルートの .env / .env.local を参照します。ユニットテスト等で自動ロードを無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI 呼び出しやネットワーク I/O 部分はモックしやすいように内部呼び出しを関数化してあり、unittest.mock.patch で差し替え可能です（例: kabusys.ai.news_nlp._call_openai_api のモック）。

ライセンス / 貢献
---
（プロジェクトのライセンス・コントリビューション方針をここに記載してください）

お問い合わせ
---
実装に関する質問やバグ報告はプロジェクトの Issue に記載してください。

以上。必要であれば README に実行例スクリプトやより詳細な .env.example、requirements.txt を追加して整備します。どの部分を優先して補足しましょうか？