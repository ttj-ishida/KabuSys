# KabuSys

KabuSys は日本株を対象としたデータプラットフォーム兼自動売買基盤のライブラリです。  
DuckDB をデータレイク／一時保存に使い、J-Quants / JPY マーケットカレンダー / RSS ニュース / OpenAI（LLM）などを組み合わせて、データの ETL、品質チェック、ニュース NLP、マーケットレジーム判定、ファクター計算、監査ログ管理を行います。

主な設計方針：
- ルックアヘッドバイアス（look-ahead bias）を避ける設計
- 冪等性（idempotency）を重視した DB 書き込み
- API 呼び出しはリトライ・レート制御・フェイルセーフ付き
- 標準ライブラリ中心の実装で運用・テストを容易に

---

## 機能一覧

- データ取得・ETL
  - J-Quants から株価（日次 OHLCV）、財務データ、JPX マーケットカレンダーを差分フェッチして DuckDB に保存
  - ETL の差分取得・バックフィル・品質チェック（欠損、重複、スパイク、日付不整合）
- ニュース収集
  - RSS フィード収集、URL 正規化、前処理、raw_news / news_symbols への冪等保存
  - SSRF や XML 攻撃、巨大レスポンス対策有り
- ニュース NLP（LLM）
  - 銘柄別に記事を集約して OpenAI（gpt-4o-mini）でセンチメントスコアを算出し ai_scores テーブルへ保存（score_news）
  - レスポンス検証・リトライ・スコアクリップ実装
- マーケットレジーム判定
  - ETF 1321 の 200 日移動平均乖離とマクロニュースの LLM センチメントを合成して日次でレジーム判定（score_regime）
- 研究・ファクター計算
  - Momentum / Volatility / Value 等のファクター計算（calc_momentum, calc_volatility, calc_value）
  - 将来リターン計算、IC（Information Coefficient）計算、Zスコア正規化など
- 監査ログ（トレーサビリティ）
  - signal_events / order_requests / executions の監査テーブルを DuckDB に初期化・管理（init_audit_schema / init_audit_db）
- ユーティリティ
  - 環境変数管理（自動 .env ロード）、設定ラッパー（kabusys.config.settings）
  - J-Quants クライアント（レート制御・リトライ・トークンリフレッシュ）

---

## 動作要件

- Python 3.10+
- duckdb
- openai（OpenAI SDK）
- defusedxml
- その他標準ライブラリ

（パッケージ依存はプロジェクトの pyproject.toml / requirements.txt を参照してください）

---

## セットアップ手順

1. リポジトリをクローン／取得して Python 仮想環境を作成・有効化
   - 例:
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - 例（pip）:
     - pip install -r requirements.txt
     - もし requirements.txt がない場合、最低限次を入れてください:
       - pip install duckdb openai defusedxml

3. 環境変数（.env）を準備
   - プロジェクトルートに `.env` または `.env.local` を置くと自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセットすると自動読み込みを無効化できます）。
   - 必須環境変数（主なもの）:
     - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD — kabuステーション API パスワード（発注等を使う場合）
     - SLACK_BOT_TOKEN — Slack 通知用 Bot token（通知を使う場合）
     - SLACK_CHANNEL_ID — Slack チャネル ID
     - OPENAI_API_KEY — OpenAI API キー（news_nlp / regime_detector を使う場合）
     - DUCKDB_PATH（任意） — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH（任意） — 監視 DB 等（デフォルト data/monitoring.db）
     - KABUSYS_ENV（任意） — development | paper_trading | live（デフォルト development）
     - LOG_LEVEL（任意） — DEBUG | INFO | WARNING | ERROR | CRITICAL（デフォルト INFO）

   - .env の例:
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxx
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development
     LOG_LEVEL=INFO

4. データベース格納ディレクトリ作成（必要に応じて）
   - デフォルトの DUCKDB_PATH の親ディレクトリを作成:
     - mkdir -p data

---

## 使い方（主要 API と実行例）

以下は Python REPL / スクリプトからの呼び出し例です。

- 設定アクセス
  - from kabusys.config import settings
  - settings.duckdb_path などでパス、settings.env, settings.is_live などを参照可能

- DuckDB 接続
  - import duckdb
  - conn = duckdb.connect(str(settings.duckdb_path))

- ETL（日次パイプライン）
  - from datetime import date
    from kabusys.data.pipeline import run_daily_etl
  - conn = duckdb.connect(str(settings.duckdb_path))
  - result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  - print(result.to_dict())

  run_daily_etl は以下を実行します：
    1. 市場カレンダー ETL（lookahead）
    2. 日次株価 ETL（差分 + backfill）
    3. 財務データ ETL（差分 + backfill）
    4. 品質チェック（run_all_checks）

- ニュースセンチメント算出（AI）
  - from datetime import date
    from kabusys.ai.news_nlp import score_news
  - conn = duckdb.connect(str(settings.duckdb_path))
  - n_written = score_news(conn, target_date=date(2026, 3, 20))
  - print(f"scored {n_written} tickers")

  引数 api_key を渡さない場合は環境変数 OPENAI_API_KEY を使用します。記事がない場合はスキップされます。

- マーケットレジーム判定
  - from datetime import date
    from kabusys.ai.regime_detector import score_regime
  - conn = duckdb.connect(str(settings.duckdb_path))
  - score_regime(conn, target_date=date(2026, 3, 20))
  - 解析結果は market_regime テーブルに冪等的に書き込まれます。

- 監査ログ DB 初期化
  - from kabusys.data.audit import init_audit_db
  - conn_audit = init_audit_db("data/audit.duckdb")
  - これにより signal_events, order_requests, executions テーブルとインデックスが作成されます。

- 研究系関数（ファクター計算）
  - from kabusys.research import calc_momentum, calc_value, calc_volatility, zscore_normalize
  - conn = duckdb.connect(str(settings.duckdb_path))
  - results = calc_momentum(conn, target_date=date(2026, 3, 20))
  - 正規化例: normalized = zscore_normalize(results, ["mom_1m", "mom_3m", "mom_6m"])

- カレンダーユーティリティ
  - from kabusys.data.calendar_management import is_trading_day, next_trading_day
  - is_trading_day(conn, date(2026,3,20))

- ニュース収集（RSS）
  - from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES
  - articles = fetch_rss(DEFAULT_RSS_SOURCES["yahoo_finance"], source="yahoo_finance")
  - raw_news への挿入はプロジェクト側の収集ジョブで行います（fetch と保存を組み合わせる）

---

## 注意事項 / 運用メモ

- 環境変数の自動ロード:
  - パッケージロード時にプロジェクトルート（.git または pyproject.toml を持つ）を探索して `.env` / `.env.local` を自動読み込みします。テストなどで自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI / J-Quants の API 呼び出しにはレート制限やコストが伴います。運用時は API 使用量・コストに注意してください。
- DuckDB への大量データ投入は executemany の挙動や行数で制約が出ることがあります（コード内で注意喚起あり）。
- LLM のレスポンスは検証（JSON パース等）を行いますが、外部 API の変化に備えて例外・フォールバックが設定されています（API失敗時は 0.0 で代替するケース等）。
- 本リポジトリの関数はバックテストループから直接呼び出す場合にルックアヘッドバイアスを生じさせないような設計がされています（target_date 引数を明示する等）。

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py                      — 環境変数 / 設定管理
- ai/
  - __init__.py
  - news_nlp.py                   — ニュースセンチメント（LLM）
  - regime_detector.py            — マーケットレジーム判定
- data/
  - __init__.py
  - jquants_client.py             — J-Quants API クライアント + 保存ロジック
  - pipeline.py                   — ETL パイプライン（run_daily_etl 等）
  - etl.py                        — ETLResult の再エクスポート
  - news_collector.py             — RSS ニュース収集
  - calendar_management.py        — 市場カレンダー管理
  - quality.py                    — データ品質チェック
  - stats.py                      — 統計ユーティリティ（zscore_normalize 等）
  - audit.py                      — 監査ログ定義・初期化
- research/
  - __init__.py
  - factor_research.py            — Momentum / Value / Volatility 計算
  - feature_exploration.py        — 将来リターン / IC / 統計サマリー 等

（README は主要モジュールを抜粋しています。詳細は各モジュールの docstring を参照してください）

---

## 開発・テスト時のヒント

- 自動 .env ロードを無効化してユニットテスト用の環境を構築する:
  - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- OpenAI への実際の呼び出しは unittest.mock.patch で _call_openai_api を差し替える実装が各モジュールで想定されています（テスト容易性）。
- DuckDB のインメモリ DB を使うとテストが速くなります:
  - conn = duckdb.connect(":memory:")

---

問題があれば、どの機能の README を詳しくするか（ETL、ニュース収集、LLM 部分、監査 DB 初期化など）を指定してください。必要ならサンプルスクリプトや .env.example の完全テンプレートも作成します。