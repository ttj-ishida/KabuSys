# KabuSys

日本株向け自動売買／データプラットフォームライブラリ

KabuSys は日本株に特化したデータ収集（ETL）・品質チェック・特徴量計算・ニュースNLP（OpenAI）・市場レジーム判定・監査ログ管理などを備えた内部ライブラリ群です。主にバックエンドバッチや研究環境、ペーパートレード実行での利用を想定しています。

バージョン: 0.1.0

---

## 概要

このパッケージは以下の機能を持ち、DuckDB を内部データストアとして利用します。

- J-Quants API からの株価／財務／カレンダーデータの差分取得（レート制御・リトライ・トークン自動更新）
- ETL パイプライン（差分取得／保存／品質チェック）の実装
- 市場カレンダー管理（営業日判定、next/prev trading day など）
- ニュース収集（RSS）と前処理、銘柄紐付け
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント判定（銘柄別 ai_score、マクロセンチメント）
- 市場レジーム判定（ETF 1321 の MA とマクロセンチメントの合成）
- ファクター計算（Momentum / Volatility / Value 等）と特徴量解析ユーティリティ（forward returns、IC、統計サマリ等）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（signal_events / order_requests / executions）用スキーマと初期化ユーティリティ
- 環境変数・設定管理（.env 自動ロード機能）

設計上のポイント:
- ルックアヘッドバイアスを避ける明確な日時設計（関数は内部で datetime.today()/date.today() を参照しない／引数で日付を受け取る）
- API 呼び出しはフェイルセーフで部分失敗を許容（可能な範囲で継続）
- DuckDB に対する冪等保存（ON CONFLICT / INSERT ... DO UPDATE）

---

## 主な機能一覧

- data/jquants_client.py : J-Quants API クライアント（取得＋DuckDB保存）
- data/pipeline.py : 日次 ETL（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
- data/quality.py : データ品質チェック群（run_all_checks 等）
- data/calendar_management.py : 営業日判定・calendar 更新ジョブ
- data/news_collector.py : RSS 取得・前処理・保存ユーティリティ
- data/audit.py : 監査ログスキーマの作成・初期化（init_audit_schema / init_audit_db）
- ai/news_nlp.py : ニュースを銘柄別に集約して LLM でスコア化（score_news）
- ai/regime_detector.py : マクロニュース + ETF 1321 MA から日次の市場レジーム判定（score_regime）
- research/* : ファクター計算、特徴量探索、統計ユーティル
- config.py : 環境変数 / 設定の集中管理（settings オブジェクト）

---

## セットアップ手順（ローカル開発向け）

前提
- Python 3.10 以上（PEP 604 の型記法などを使用）
- DuckDB を利用するためのネイティブ依存（通常 pip install でインストール可）

1. リポジトリをクローン
   - 例: git clone <repo-url>

2. 仮想環境を作成・有効化
   - python -m venv .venv
   - Windows: .venv\Scripts\activate
   - macOS/Linux: source .venv/bin/activate

3. 必要パッケージをインストール
   - 典型的な依存例:
     - duckdb
     - openai
     - defusedxml
   - 例:
     - pip install duckdb openai defusedxml

   （実プロジェクトでは requirements.txt / pyproject.toml を用意している想定です。開発時は pip install -e . でインストールしてください）

4. 環境変数 / .env の用意
   - プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すれば無効化可能）。
   - 必須変数:
     - JQUANTS_REFRESH_TOKEN=<your_jquants_refresh_token>  # J-Quants 認証用
     - KABU_API_PASSWORD=<kabu_station_api_password>       # kabuステーション API パスワード（必要なら）
   - OpenAI を使う場合:
     - OPENAI_API_KEY=<your_openai_api_key>
   - 任意:
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（通知用）
     - DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH
     - KABUSYS_ENV (development|paper_trading|live)
     - PAPER_FILL_MODE (instant|partial|never|reject)
   - 例 `.env`:
     JQUANTS_REFRESH_TOKEN=abc...
     OPENAI_API_KEY=sk-...
     DUCKDB_PATH=data/kabusys.duckdb
     KABU_API_PASSWORD=secret
     KABUSYS_ENV=development

5. データベース・スキーマ初期化（監査DB 例）
   - Python REPL / スクリプトで:
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/monitoring.duckdb")
   - パッケージ内の関数 init_audit_schema も利用可能（既存接続へ適用）

---

## 使い方（簡単な例）

※ ここでは最小限の呼び出し例を示します。実運用ではログ設定や例外処理、認証トークン管理を追加してください。

1) DuckDB 接続と ETL（日次 ETL の実行）
- 例:
  from datetime import date
  import duckdb
  from kabusys.config import settings
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())

  - 戻り値は ETLResult オブジェクト（取得件数・保存件数・品質チェック結果・エラー等を含む）。

2) ニューススコアリング（AI）
- 例:
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  # OPENAI_API_KEY が環境変数に入っていれば api_key は None で可
  count = score_news(conn, target_date=date(2026,3,20))
  print(f"scored {count} codes")

3) 市場レジーム判定
- 例:
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026,3,20))  # OpenAI API キーは env または引数で指定可能

4) 監査DB 初期化（発注・約定ログ用）
- 例:
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/execution_audit.duckdb")
  # これで signal_events/order_requests/executions テーブルが作成される

5) ファクター計算／研究ユーティリティ
- 例:
  from datetime import date
  import duckdb
  from kabusys.research import calc_momentum, calc_value, calc_volatility, zscore_normalize

  conn = duckdb.connect("data/kabusys.duckdb")
  target = date(2026,3,20)
  mom = calc_momentum(conn, target)
  vol = calc_volatility(conn, target)
  val = calc_value(conn, target)
  mom_z = zscore_normalize(mom, ["mom_1m", "mom_3m", "mom_6m"])

6) RSS ニュース取得（news_collector）
- 例:
  from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES
  articles = fetch_rss(DEFAULT_RSS_SOURCES["yahoo_finance"], source="yahoo_finance")
  # 取得した記事は raw_news に保存する前に整形・DB挿入する処理を実装してください

---

## 環境 / 設定に関する注意点

- settings（kabusys.config.settings）から各種設定値が取得できます（例: settings.duckdb_path）。
- .env 自動ロード:
  - パッケージはプロジェクトルート（.git または pyproject.toml を探索）を検出して `.env` / `.env.local` を自動読み込みします。テスト時などで自動読み込みを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- PAPER_FILL_MODE（Paper Trading のモック約定挙動）は instant/partial/never/reject のいずれかを指定
- KABUSYS_ENV は development / paper_trading / live のいずれか
- OpenAI 呼び出しは gpt-4o-mini を前提とした JSON mode を使用しています。API の利用には OPENAI_API_KEY が必要です。

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py                      — 環境変数 / 設定管理（settings）
- ai/
  - __init__.py
  - news_nlp.py                   — ニュースを銘柄別に集約して LLM でスコアリング（score_news）
  - regime_detector.py            — ETF MA + マクロニュースで市場レジーム判定（score_regime）
- data/
  - __init__.py
  - jquants_client.py             — J-Quants API クライアント（取得・保存）
  - pipeline.py                   — ETL パイプライン（run_daily_etl 等）
  - etl.py                        — ETLResult の再エクスポート
  - quality.py                    — 品質チェック群（check_missing_data 等）
  - calendar_management.py        — 市場カレンダー管理（is_trading_day 等）
  - audit.py                      — 監査ログスキーマ定義・初期化
  - news_collector.py             — RSS 取得・前処理
  - stats.py                      — zscore_normalize 等の統計ユーティリティ
- research/
  - __init__.py
  - factor_research.py            — calc_momentum / calc_value / calc_volatility
  - feature_exploration.py        — calc_forward_returns / calc_ic / factor_summary / rank
- research/...                     — 研究用ユーティリティ群
- その他（strategy / execution / monitoring などのモジュールが将来追加想定）
  
（実際のリポジトリには上記以外のユーティリティ・テスト等が含まれる可能性があります）

---

## 推奨ワークフロー（運用例）

- バッチ（Cron）で nightly ETL を実行:
  - run_daily_etl を使って market calendar → prices → financials → 品質チェック を順に実行
- 毎朝のニューススコアリング:
  - score_news を target_date に対して実行し ai_scores を更新
- レジーム判定:
  - score_regime を呼んで market_regime テーブルを更新
- 発注フロー（監査）:
  - strategy が signal を生成したら signal_events に保存し、order_requests を作成、証券会社 API を呼び出して executions を記録
- 研究用:
  - research モジュールでファクターを計算しバックテスト・分析へ活用

---

## 開発上の留意点

- 外部 API（J-Quants / OpenAI）呼び出しはレート制御とリトライを実装していますが、実運用では API 利用料・スロットルを考慮した運用設計をしてください。
- AI 呼び出しは JSON mode を想定してレスポンスを厳密にパースしますが、LLM の挙動による応答不整合に備えたフォールバックロジックがあります。テストでは _call_openai_api をモックしてください。
- DuckDB に格納する前にデータのスキーマ整合性を確認してください（ETL は基本的に ON CONFLICT DO UPDATE を使用して冪等性を担保）。
- 日付・時刻の取り扱いについてはコード中に説明がある通りルックアヘッドバイアス防止の工夫があります。研究・バックテストでは target_date を明示的に設定してください。

---

## サポート / 貢献

- バグ報告や機能要望は Issue を作成してください。
- 貢献は Pull Request を通じてお願いします。テスト・ドキュメントを含めてください。

---

README に書かれている内容はコードベースの現状を要約したものです。実際の運用／導入にあたってはプロジェクト付属のドキュメント（.env.example, DataPlatform.md, StrategyModel.md 等）があれば併せて参照してください。