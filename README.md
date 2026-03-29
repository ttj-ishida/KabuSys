# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ。  
データ収集（J-Quants）、品質チェック、ETL、ニュースセンチメント（OpenAI）、市場レジーム判定、監査ログなどを含むモジュール群を提供します。

---

## プロジェクト概要

KabuSys は日本株の自動売買システムやリサーチ環境向けの基盤ライブラリです。主な目的は以下です。

- J-Quants API からの株価・財務・カレンダー等データの差分取得と DuckDB への永続化（ETL）
- データ品質チェック（欠損・重複・スパイク・日付不整合）
- RSS ニュース収集と銘柄ごとの LLM ベースセンチメントスコアリング
- マクロニュースとテクニカル指標を組み合わせた市場レジーム判定
- 監査ログ（signal → order_request → execution）用スキーマの初期化と利用
- 研究用のファクター計算・特徴量解析ユーティリティ

設計上の特徴として、ルックアヘッドバイアス回避、API リトライ／レート制限対応、DuckDB を用いた冪等保存、LLM 呼び出しのフェイルセーフなどを重視しています。

---

## 主な機能一覧

- data/
  - ETL パイプライン: 日次 ETL（株価・財務・カレンダー）`run_daily_etl`
  - J-Quants クライアント: データフェッチ／保存（`fetch_*`, `save_*`）
  - カレンダー管理: 営業日判定・次営業日/前営業日取得・カレンダー更新ジョブ
  - ニュース収集: RSS フィード取得・前処理・raw_news への保存
  - 品質チェック: 欠損・スパイク・重複・日付不整合
  - 監査ログ: 監査スキーマ初期化＆監査用 DB ユーティリティ
  - 統計ユーティリティ: Z スコア正規化等
- ai/
  - ニュース NLP: gpt-4o-mini を用いた銘柄ごとのセンチメント（`score_news`）
  - レジーム検出: ETF(1321)の MA200 乖離とマクロセンチメント複合（`score_regime`）
  - 両モジュールは OpenAI の JSON mode を利用、リトライ・バリデーション・フェイルセーフ実装済
- research/
  - ファクター計算: Momentum / Value / Volatility 等（`calc_momentum`, `calc_value`, `calc_volatility`）
  - 特徴量探索: 将来リターン計算、IC（情報係数）、統計サマリー等

---

## セットアップ手順

前提: Python 3.10 以上を推奨（型ヒントにより）。以下は最小限の手順例です。

1. リポジトリをクローンし、開発モードでインストール（任意）
   - git clone ...
   - cd <repo>
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
   - pip install -U pip
   - pip install duckdb openai defusedxml  (必要な外部依存の一例)
   - pip install -e .

   注意: requirements.txt / pyproject.toml がある場合はそちらを利用してください。

2. 環境変数 / .env の準備
   - ルート（.git または pyproject.toml があるディレクトリ）に `.env` / `.env.local` を配置すると、自動で読み込まれます（`kabusys.config` が自動ロード）。
   - 必須の環境変数（少なくとも以下を設定してください）:
     - JQUANTS_REFRESH_TOKEN — J-Quants 用リフレッシュトークン
     - OPENAI_API_KEY — OpenAI API キー（`score_news` / `score_regime` 実行時に参照）
     - KABU_API_PASSWORD — kabu ステーション等を使う場合
     - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID — 通知連携を使う場合
   - 自動ロードを無効にする場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

3. データベースディレクトリを準備
   - デフォルトの DuckDB ファイルパス:
     - data/kabusys.duckdb （主 DB）
     - data/monitoring.db （監視用）
   - 必要に応じて `DUCKDB_PATH` / `SQLITE_PATH` を環境変数で上書きできます。

---

## 使い方（主要ユースケース）

以下は簡単な利用例（Python REPL で実行することを想定）。

1. DuckDB 接続を開いて日次 ETL を実行する
   - 例:
     - import duckdb
     - from datetime import date
     - from kabusys.data.pipeline import run_daily_etl
     - conn = duckdb.connect("data/kabusys.duckdb")
     - result = run_daily_etl(conn, target_date=date(2026,3,20))
     - print(result.to_dict())

   説明: `run_daily_etl` はカレンダー → 株価 → 財務 → 品質チェックの順で差分 ETL を行い、ETLResult を返します。

2. ニュースセンチメントを計算して `ai_scores` に書き込む
   - 例:
     - import duckdb
     - from datetime import date
     - from kabusys.ai.news_nlp import score_news
     - conn = duckdb.connect("data/kabusys.duckdb")
     - count = score_news(conn, target_date=date(2026,3,20))
     - print("scored:", count)

   説明: 前日 15:00 JST 〜 当日 08:30 JST の記事ウィンドウを対象に LLM で銘柄別スコアを生成します。API キーは引数で渡すか環境変数 `OPENAI_API_KEY` を利用します。失敗時はフェイルセーフでスキップします。

3. 市場レジーム判定（1321 の MA200 とマクロセンチメントの合成）
   - 例:
     - from kabusys.ai.regime_detector import score_regime
     - score_regime(conn, target_date=date(2026,3,20))

   説明: OpenAI を使ったマクロセンチメント（最大 20 記事）を取得し、MA200 乖離と合成して `market_regime` テーブルに冪等書き込みします。

4. 監査ログ（audit DB）の初期化
   - 例:
     - from kabusys.data.audit import init_audit_db
     - conn_audit = init_audit_db("data/audit.duckdb")
   - 説明: 監査テーブル（signal_events, order_requests, executions）を作成しタイムゾーンを UTC に設定します。

5. 研究用ユーティリティ
   - ファクター計算:
     - from kabusys.research.factor_research import calc_momentum
     - recs = calc_momentum(conn, date(2026,3,20))
   - 将来リターン / IC / 統計:
     - from kabusys.research.feature_exploration import calc_forward_returns, calc_ic, factor_summary

---

## 環境変数（主要）

- JQUANTS_REFRESH_TOKEN  (必須) — J-Quants リフレッシュトークン
- OPENAI_API_KEY         (必須 for AI functions) — OpenAI API キー
- KABU_API_PASSWORD      (kabu API 利用時)
- KABUSYS_ENV            = development | paper_trading | live（デフォルト: development）
- LOG_LEVEL              = DEBUG | INFO | WARNING | ERROR | CRITICAL
- DUCKDB_PATH            デフォルト: data/kabusys.duckdb
- SQLITE_PATH            デフォルト: data/monitoring.db
- KABUSYS_DISABLE_AUTO_ENV_LOAD = 1 で .env の自動ロードを停止

設定は `.env` / `.env.local` に記載しておくことが可能（`kabusys.config` が自動読み込み）。

---

## 実装上の注意点 / 設計メモ

- ルックアヘッドバイアス対策: AI・リサーチ関連（news_nlp, regime_detector, research/*）は内部で `date.today()` や `datetime.today()` を参照しないよう設計されています。常に呼び出し側が `target_date` を明示してください。
- OpenAI 呼び出し: JSON mode + レスポンスバリデーションを行い、429/ネットワーク/5xx に対して指数バックオフでリトライします。失敗時はフォールバック値（0.0）やスキップで継続する実装です。
- J-Quants クライアント: 固定間隔スロットリング（120 req/min）とトークン自動リフレッシュ、ページネーション対応、リトライ戦略を備えています。
- DuckDB 保存は基本的に冪等（ON CONFLICT DO UPDATE / DO NOTHING）で行います。
- ニュース収集は SSRF 対策、gzip/サイズ制限、XML インジェクション対策（defusedxml）などを実施しています。
- 監査ログは削除されない前提で設計（FK は ON DELETE RESTRICT）。order_request_id を冪等キーとして利用可能。

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py
  - config.py                    - 環境変数 / .env の自動読み込み・設定アクセス
  - ai/
    - __init__.py
    - news_nlp.py                - ニュースセンチメントの計算（score_news）
    - regime_detector.py         - 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py          - J-Quants API クライアント（fetch/save）
    - pipeline.py                - ETL パイプライン（run_daily_etl 等）
    - etl.py                     - ETL 用型エクスポート（ETLResult）
    - news_collector.py          - RSS フィード収集・前処理
    - calendar_management.py     - 市場カレンダー管理
    - quality.py                 - データ品質チェック
    - stats.py                   - 統計ユーティリティ（zscore_normalize）
    - audit.py                   - 監査スキーマ初期化 / audit DB ユーティリティ
    - (その他) jquants_client の補助関数等
  - research/
    - __init__.py
    - factor_research.py         - ファクター計算
    - feature_exploration.py     - 将来リターン / IC / 統計
  - research/*, ai/*, data/* にテスト対象ロジックが実装されています

---

## トラブルシューティング / よくある質問

- .env が読み込まれない
  - `KABUSYS_DISABLE_AUTO_ENV_LOAD` が設定されていないか、プロジェクトルート（.git または pyproject.toml）が検出できる位置に .env を置いてください。
- OpenAI エラーでスコアが取得できない
  - API キーが正しいか、レートリミットに達していないか確認してください。実装側で自動リトライやフォールバック（0.0）を行いますが、ログを確認して原因を特定してください。
- DuckDB にテーブルがない / ETL がエラーになる
  - 初回はスキーマ初期化を行う必要がある箇所があります（audit 用など）。ETL は既存のテーブル有無をチェックする実装になっていますが、エラー時はログを参照してください。

---

## ライセンス / 貢献

（この README にはライセンスや貢献手順は明記されていません。必要に応じてプロジェクトルートに LICENSE / CONTRIBUTING を追加してください。）

---

必要であれば、README に「実行サンプル（スクリプト）」「requirements.txt」「データスキーマのサンプル」などの追加セクションを作成します。どの部分を詳しく追加しますか？