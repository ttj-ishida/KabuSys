# KabuSys

日本株向けのデータ基盤・リサーチ・自動売買補助ライブラリです。  
DuckDB を中心としたローカルデータベースと J-Quants / OpenAI 等の外部 API を組み合わせ、ETL、ニュース NLP、市場レジーム判定、ファクター計算、監査ログ（オーディット）などを提供します。

---

## 主要特徴（ハイライト）

- ETL パイプライン
  - J-Quants から株価（OHLCV）、財務データ、JPX カレンダーを差分取得して DuckDB に保存
  - 品質チェック（欠損・重複・スパイク・日付不整合）
- ニュース NLP
  - RSS 収集（SSRF 対策・トラッキングパラメータ除去）
  - OpenAI（gpt-4o-mini）を使った銘柄ごとのニュースセンチメント算出（ai_scores へ書き込み）
- 市場レジーム判定
  - ETF（1321）200 日 MA 乖離とマクロニュース LLM センチメントを合成してレジーム判定（bull / neutral / bear）
- 研究（Research）ユーティリティ
  - ファクター計算（モメンタム、バリュー、ボラティリティ等）
  - 将来リターン計算、IC（Information Coefficient）、ファクター統計サマリー
- 監査ログ（Audit）
  - シグナル → 発注 → 約定のトレーサビリティテーブル（監査テーブル）を DuckDB に初期化・管理
- 設計方針
  - ルックアヘッド（look-ahead）バイアス防止の徹底（内部で date.today() 等の参照を避ける箇所あり）
  - DB 書き込みは冪等（ON CONFLICT / DELETE→INSERT 等）を意識
  - 外部 API 呼び出しはリトライ／バックオフやフェイルセーフ（失敗時はスキップ or 中立値）

---

## 機能一覧（モジュール別）

- kabusys.config
  - .env 自動ロード（プロジェクトルート検出）と環境変数取得ラッパー（Settings）
- kabusys.data
  - ETL パイプライン: pipeline.run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl
  - J-Quants クライアント: jquants_client.fetch_* / save_*（rate limiter / token refresh / retry 実装）
  - カレンダー管理: calendar_management (is_trading_day, next_trading_day, get_trading_days, calendar_update_job 等)
  - ニュース収集: news_collector.fetch_rss / preprocess_text（SSRF 対策・サイズ制限）
  - データ品質チェック: quality.run_all_checks, check_missing_data, check_spike, check_duplicates, check_date_consistency
  - 統計ユーティリティ: stats.zscore_normalize
  - 監査ログ: audit.init_audit_db / init_audit_schema
  - ETL 結果型: pipeline.ETLResult
- kabusys.ai
  - news_nlp.score_news: 銘柄ごとのニュースセンチメントを OpenAI で算出して ai_scores テーブルへ書き込む
  - regime_detector.score_regime: ETF マクロ指標 + LLM を合成して market_regime テーブルへ書き込む
- kabusys.research
  - factor_research.calc_momentum / calc_value / calc_volatility
  - feature_exploration.calc_forward_returns / calc_ic / factor_summary / rank

---

## 前提・必要要件

- Python 3.10+
  - 型記法（| union）を使用しているため Python 3.10 以上を想定
- 外部パッケージ（主なもの）
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス先
  - J-Quants API（認証トークン必要）
  - OpenAI API（OpenAI API key が必要）
  - RSS フィード取得のための外部 HTTP(S)

必要パッケージはプロジェクトに requirements.txt / pyproject.toml があればそちらを参照してください。簡易的には次をインストールします:

pip install duckdb openai defusedxml

（追加で logging や標準ライブラリで賄える実装です）

---

## 環境変数（主要）

自動でプロジェクトルートの `.env` / `.env.local` を読み込みます（CWD ではなくパッケージファイル位置からルートを探索）。自動ロード無効化は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`。

主要なキー（設定必須のものには注記）:

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants リフレッシュトークン（jquants_client.get_id_token に使用）
- KABU_API_PASSWORD — kabu ステーション API パスワード（発注系利用時）
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY — OpenAI API キー（ai.score_news / regime_detector で使用）
- SLACK_BOT_TOKEN (必須) — Slack 通知用 Bot トークン（必要な処理で使用）
- SLACK_CHANNEL_ID (必須) — Slack チャネル ID
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視などに使う SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 実行環境: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...、デフォルト: INFO）

例（.env）:

JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=DEBUG

---

## セットアップ手順（ローカル開発・実行）

1. リポジトリをクローン
   - git clone <repo-url>
2. 仮想環境を作る（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）
3. 必要パッケージをインストール
   - pip install -r requirements.txt  （プロジェクトにある場合）
   - または最低限: pip install duckdb openai defusedxml
4. 環境変数を用意
   - プロジェクトルートに `.env` を作成するか、環境変数を export。
   - 例は上記の「環境変数」節を参照。
5. DuckDB ファイルやデータディレクトリの作成（必要に応じて）
   - mkdir -p data

---

## 使い方（代表的な操作例）

以下は Python REPL やスクリプトから呼ぶ例です。適宜環境変数（OPENAI_API_KEY など）を設定してください。

- 日次 ETL を実行する（pipeline.run_daily_etl）
  ```python
  from datetime import date
  import duckdb
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュース NLP（OpenAI を使ってスコア算出）
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  # OPENAI_API_KEY 環境変数を設定しておく
  written = score_news(conn, target_date=date(2026, 3, 20))
  print("written:", written)
  ```

- 市場レジーム判定（regime_detector）
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログ DB 初期化（監査用 DuckDB を新規作成）
  ```python
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  # conn を使って order_requests / executions 等の操作が可能
  ```

- RSS フィードから記事取得（ニュースコレクタ）
  ```python
  from kabusys.data.news_collector import fetch_rss
  articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", "yahoo_finance")
  for a in articles:
      print(a["id"], a["datetime"], a["title"])
  ```

- ファクター計算（研究用）
  ```python
  from datetime import date
  import duckdb
  from kabusys.research.factor_research import calc_momentum

  conn = duckdb.connect("data/kabusys.duckdb")
  recs = calc_momentum(conn, target_date=date(2026,3,20))
  print(len(recs))
  ```

注意:
- OpenAI API 呼び出しはレートや料金を伴います。API キーは環境変数で管理してください。
- jquants_client は J-Quants のリフレッシュトークンが必要です（環境変数 JQUANTS_REFRESH_TOKEN）。

---

## ディレクトリ構成（主要ファイル）

（リポジトリの src/kabusys 以下を抜粋）

- src/kabusys/
  - __init__.py
  - config.py                      — 環境変数/設定管理
  - ai/
    - __init__.py
    - news_nlp.py                   — ニュース NLP（OpenAI を用いた銘柄別スコア）
    - regime_detector.py            — 市場レジーム判定（ETF MA + LLM）
  - data/
    - __init__.py
    - jquants_client.py             — J-Quants API クライアント（fetch/save）
    - pipeline.py                   — ETL パイプライン（run_daily_etl 等）
    - etl.py                        — ETLResult の再エクスポート
    - news_collector.py             — RSS 収集・前処理（SSRF 対策 等）
    - calendar_management.py        — 市場カレンダー管理（営業日判定等）
    - quality.py                    — データ品質チェック
    - stats.py                      — 統計ユーティリティ（zscore など）
    - audit.py                      — 監査ログ（テーブル初期化 / init_audit_db）
  - research/
    - __init__.py
    - factor_research.py            — Momentum/Value/Volatility の計算
    - feature_exploration.py        — 将来リターン / IC / サマリー
  - ai/、research/、data/ 内にテスト可能な関数群が収められています。

---

## 設計上の注意・ベストプラクティス

- ルックアヘッドバイアスに対する配慮
  - 多くの処理（news window / regime / ETL / research）は内部で date.today() に依存しないよう設計されています。外部から target_date を明示して実行してください。
- 冪等性
  - DB への保存関数は基本的に ON CONFLICT または DELETE→INSERT により冪等を考慮しています。ETL は再実行可能です。
- フェイルセーフ
  - 外部 API（OpenAI, J-Quants）失敗時は多くの箇所でフォールバック（中立値やスキップ）して処理継続を優先します。ログを確認してください。
- セキュリティ
  - news_collector は SSRF 対策（リダイレクト検査・プライベートアドレスのブロック）や XML の defusedxml 使用、受信サイズ制限を実装しています。

---

## トラブルシューティング

- .env が読み込まれない
  - パッケージはプロジェクトルート（.git または pyproject.toml を基準）を探索して `.env` を自動ロードします。テスト等で自動ロードを無効にしたい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してから環境変数を手動でセットしてください。
- OpenAI 呼び出し関連の失敗
  - API キーが正しく設定されているか、また OpenAI 側のレート制限やレスポンスフォーマットに注意してください。失敗時は関数内でログが出力され、フェイルセーフ（0.0 など）を返す設計です。
- J-Quants API の 401
  - jquants_client は 401 を検知すると自動でリフレッシュトークンから id_token を再取得して再試行しますが、refresh token（JQUANTS_REFRESH_TOKEN）が正しいか確認してください。
- DuckDB に関するエラー
  - バージョン差異（特に executemany の空リスト制約等）により一部の動作が異なる可能性があります。推奨は最新の安定版 duckdb。

---

この README はコードベースの主要モジュールと使用方法を簡潔にまとめたものです。詳しい設計文書（DataPlatform.md や StrategyModel.md に相当する参照）はソース内の docstring やコメントを参照してください。必要であれば API リファレンスや運用手順（cron / orchestration / Slack 通知の例など）を追加で作成します。