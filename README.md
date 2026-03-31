# KabuSys

KabuSys は日本株のデータプラットフォームと研究・自動売買基盤のための Python ライブラリです。J-Quants / kabuステーション / OpenAI 等と連携して、データ ETL、ニュース NLP、市場レジーム判定、ファクター計算、監査ログ（トレーサビリティ）などを提供します。

---

## 主な機能

- データ ETL（J-Quants からの株価・財務・市場カレンダー取得）
  - 差分取得、バックフィル、冪等保存（DuckDB への ON CONFLICT 更新）
  - 品質チェック（欠損・スパイク・重複・日付不整合）
- ニュース収集・前処理（RSS → raw_news）
  - SSRF 対策、トラッキングパラメータ除去、記事 ID のハッシュ化
- ニュース NLP（OpenAI を用いた銘柄別センチメント）
  - gpt-4o-mini を JSON mode で呼び出し、ai_scores テーブルへ保存
- 市場レジーム判定（ETF 1321 の MA200 乖離 と マクロニュースセンチメントの合成）
- ファクター計算・リサーチユーティリティ
  - Momentum / Volatility / Value 等の定量ファクター
  - 将来リターン計算、IC（スピアマン）計算、統計サマリー、Zスコア正規化
- 監査ログ（signal → order_request → executions のトレーサビリティ）
  - 監査テーブル初期化ユーティリティ（DuckDB）
- 設定管理（.env / 環境変数自動読み込み）

---

## 必要条件

- Python 3.10 以上（`Path | None` 等の構文を使用）
- 主要依存パッケージ（例）
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants API、OpenAI、RSS ソース 等）

（プロジェクトに requirements.txt があればそちらを利用してください。無ければ上記パッケージをインストールしてください。）

---

## セットアップ手順（ローカル開発用）

1. リポジトリをクローン
   - git clone <repo-url>
2. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）
3. 必要パッケージをインストール
   - pip install duckdb openai defusedxml
   - （開発用に editable インストールが可能なら）pip install -e .
4. 環境変数を用意
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env` / `.env.local` を置くと自動で読み込まれます（自動読み込みはデフォルトで有効）。
   - 自動ロードを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

### 推奨環境変数（.env に記載する例）
以下は主要な環境変数の例と説明です（必須は実行する機能により異なります）。

- JQUANTS_REFRESH_TOKEN=xxxxx
  - J-Quants API 用のリフレッシュトークン（ETL 実行時に必要）
- KABU_API_PASSWORD=xxxxx
  - kabuステーション API 用パスワード（自動売買やブローカー連携時）
- KABU_API_BASE_URL=http://localhost:18080/kabusapi
  - kabu API のベース URL（デフォルト）
- OPENAI_API_KEY=sk-...
  - OpenAI API キー（news_nlp / regime_detector 実行時に使用）
- SLACK_BOT_TOKEN=xoxb-...
  - Slack 通知用トークン（通知機能を利用する場合）
- SLACK_CHANNEL_ID=C...
  - Slack チャンネル ID
- DUCKDB_PATH=data/kabusys.duckdb
  - デフォルト DuckDB ファイルパス
- SQLITE_PATH=data/monitoring.db
  - SQLite（モニタリング）パス
- KABUSYS_ENV=development|paper_trading|live
  - 実行環境（development/paper_trading/live）
- LOG_LEVEL=INFO
  - ログレベル

---

## 使い方（プログラムからの呼び出し例）

以下は代表的なユーティリティの使い方サンプルです。プロジェクトのパスや環境変数を適切に設定した上で実行してください。

- DuckDB 接続を作って日次 ETL を実行する例
  - from datetime import date
  - import duckdb
  - from kabusys.data.pipeline import run_daily_etl
  - conn = duckdb.connect("data/kabusys.duckdb")
  - result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  - print(result.to_dict())

- ニュースセンチメント（1日分）を計算して ai_scores に書き込む
  - from datetime import date
  - import duckdb
  - from kabusys.ai.news_nlp import score_news
  - conn = duckdb.connect("data/kabusys.duckdb")
  - n_written = score_news(conn, target_date=date(2026, 3, 20))
  - print("written:", n_written)

- 市場レジーム判定を行う
  - from datetime import date
  - import duckdb
  - from kabusys.ai.regime_detector import score_regime
  - conn = duckdb.connect("data/kabusys.duckdb")
  - score_regime(conn, target_date=date(2026, 3, 20))

- 監査ログ用 DuckDB を初期化する
  - from kabusys.data.audit import init_audit_db
  - conn = init_audit_db("data/audit.duckdb")
  - # テーブルが作成されます

- RSS を取得して raw_news に保存する処理は news_collector の fetch_rss を用いて実装されています（保存ロジックはプロジェクト内で呼び出すか、自作のラッパーで利用してください）。

注意点:
- OpenAI 呼び出し（news_nlp, regime_detector）は API 呼び出しを行うため、`OPENAI_API_KEY` を設定するか、関数呼び出し時に api_key 引数を渡してください。
- J-Quants 呼び出しには `JQUANTS_REFRESH_TOKEN`（または get_id_token に渡す refresh_token）が必要です。

---

## よく使う API / 関数一覧

- kabusys.config.settings
  - 環境変数から各種設定を取得（自動的に .env/.env.local をロード）
- kabusys.data.pipeline
  - run_daily_etl(conn, target_date, ...)
  - run_prices_etl / run_financials_etl / run_calendar_etl
  - ETLResult クラス
- kabusys.data.jquants_client
  - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - save_daily_quotes, save_financial_statements, save_market_calendar
  - get_id_token
- kabusys.data.news_collector
  - fetch_rss(url, source, timeout)
  - preprocess_text 等のユーティリティ
- kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)
  - ニュース NLP による銘柄別スコアリング
- kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - 市場レジーム判定（1321 の MA200 とマクロニュースの合成）
- kabusys.research (ファクター関連)
  - calc_momentum, calc_volatility, calc_value
  - calc_forward_returns, calc_ic, factor_summary, rank
- kabusys.data.audit
  - init_audit_schema(conn, transactional=False)
  - init_audit_db(db_path)

---

## ディレクトリ構成（主要ファイル抜粋）

src/kabusys/
- __init__.py
- config.py                    # 環境変数 / .env 管理
- ai/
  - __init__.py
  - news_nlp.py                # ニュース NLP（OpenAI 連携）
  - regime_detector.py        # 市場レジーム判定
- data/
  - __init__.py
  - jquants_client.py         # J-Quants API クライアント + DuckDB 保存関数
  - pipeline.py               # ETL パイプライン（run_daily_etl 等）
  - quality.py                # データ品質チェック
  - stats.py                  # 統計ユーティリティ（zscore_normalize）
  - calendar_management.py    # マーケットカレンダー管理・営業日判定
  - news_collector.py         # RSS 収集・前処理
  - audit.py                  # 監査ログ（トレーサビリティ）初期化
  - etl.py                    # ETLResult のエクスポート
- research/
  - __init__.py
  - factor_research.py        # Momentum / Value / Volatility
  - feature_exploration.py    # forward returns / IC / summary
- ai/, research/ 等のパッケージはそれぞれユーティリティを公開

---

## 実運用上の注意事項

- 自動売買（kabuステーション連携）を行う場合は、KABU_API_PASSWORD や適切な安全対策を必ず行ってください。実口座（live）モードでは安全ガード（注文量制限、ドライラン、監査ログ確認等）を徹底してください。
- モデル呼び出しは API コストとレイテンシが発生します。バッチサイズやリトライ設定が組み込まれていますが、運用時はレートや課金に注意してください。
- DuckDB のファイルはバックアップ／パーミッション管理をしてください。監査ログは削除しない前提で設計されています。
- テスト時は環境変数の自動ロードを無効化できます: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

この README はコードベースの公開インターフェース・設計方針に基づく簡易ドキュメントです。各モジュールの詳細な使い方やスキーマ定義はソースコード（該当ファイルの docstring）を参照してください。必要であれば、README に実行スクリプト例や CLI、docker-compose、CI 設定などの追記を行います。必要項目を教えてください。