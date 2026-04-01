KabuSys — 日本株自動売買基盤（README）
====================================

概要
----
KabuSys は日本株のデータ取得・品質管理・特徴量計算・ニュース NLP / レジーム判定・監査ログなどを包含する自動売買プラットフォームのコアライブラリ群です。  
主に以下を目的とします。

- J-Quants API からの株価・財務・カレンダー取得（差分 ETL、ページネーション対応、冪等保存）
- ニュース収集と LLM（OpenAI）を使った銘柄別ニュースセンチメント算出
- 市場レジーム判定（ETF 1321 の MA とマクロニュースの合成）
- ファクター計算・特徴量探索（モメンタム / バリュー / ボラティリティ等）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（signal → order_request → execution のトレーサビリティ）
- DuckDB を用いたローカル DB 管理

主要機能一覧
-------------
- 環境設定管理（kabusys.config）
  - .env / .env.local の自動読み込み（プロジェクトルート検出）と必須項目チェック
- データ ETL（kabusys.data.pipeline / jquants_client / news_collector）
  - fetch / save（raw_prices / raw_financials / market_calendar 等）
  - run_daily_etl による一括 ETL（カレンダー→株価→財務→品質チェック）
- データ品質（kabusys.data.quality）
  - 欠損、スパイク、重複、日付整合性チェック
- 統計ユーティリティ（kabusys.data.stats）
  - Zスコア正規化など
- 研究用モジュール（kabusys.research）
  - calc_momentum, calc_value, calc_volatility, forward returns, IC, summary 等
- ニュース NLP（kabusys.ai.news_nlp）
  - OpenAI を使用した銘柄別センチメント（JSON Mode, バッチ, リトライ）
- レジーム判定（kabusys.ai.regime_detector）
  - ETF 1321 の MA200 乖離とマクロニュースセンチメントを合成して市場レジーム判定
- 監査ログ初期化（kabusys.data.audit）
  - 監査テーブル群の DDL/インデックスを冪等作成、専用 DuckDB 初期化ユーティリティ
- J-Quants クライアント（kabusys.data.jquants_client）
  - レートリミッタ、401 自動リフレッシュ、指数バックオフ、ページネーション対応

セットアップ手順
----------------
前提
- Python 3.10+（Union 型表記 `X | None` 等を使用しているため）
- ネットワーク（J-Quants / OpenAI）アクセス

1. 仮想環境作成（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - 推奨パッケージ（最低限）:
     - duckdb
     - openai
     - defusedxml
   例:
     - pip install duckdb openai defusedxml

   プロジェクトがパッケージとしてインストール可能なら:
     - pip install -e .

3. 環境変数（.env）を用意
   - プロジェクトルートに .env または .env.local を置くことで自動読み込みされます
   - 自動読み込みを無効にする場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

必須環境変数（代表例）
- JQUANTS_REFRESH_TOKEN=（J-Quants のリフレッシュトークン）
- OPENAI_API_KEY=（OpenAI API キー）
- KABU_API_PASSWORD=（kabu API パスワード、該当する機能を使う場合）
- SLACK_BOT_TOKEN=（監視/通知で Slack を使う場合）
- SLACK_CHANNEL_ID=（通知先チャンネル）
例 .env（参考）
  JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
  OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxx
  KABU_API_PASSWORD=your_kabu_pass
  SLACK_BOT_TOKEN=xoxb-...
  SLACK_CHANNEL_ID=C01234567

設定 API
- from kabusys.config import settings
- settings.jquants_refresh_token, settings.duckdb_path, settings.env などで参照可能

基本的な使い方（コード例）
-------------------------

準備: DuckDB 接続
- import duckdb
- from kabusys.config import settings
- conn = duckdb.connect(str(settings.duckdb_path))

ETL 実行（日次）
- from kabusys.data.pipeline import run_daily_etl
- from datetime import date
- res = run_daily_etl(conn, target_date=date(2026, 3, 20))
- print(res.to_dict())  # ETL 結果の概要

ニューススコア算出（LLM）
- from kabusys.ai.news_nlp import score_news
- from datetime import date
- count = score_news(conn, target_date=date(2026,3,20))
- print(f"scored {count} codes")

市場レジーム判定
- from kabusys.ai.regime_detector import score_regime
- from datetime import date
- score_regime(conn, target_date=date(2026,3,20))

監査ログ DB 初期化（専用 DB）
- from kabusys.data.audit import init_audit_db
- conn_audit = init_audit_db("data/audit.duckdb")
- # 必要に応じて conn_audit を使用して監査操作

研究用関数の呼び出し例
- from kabusys.research import calc_momentum, calc_value, calc_volatility
- res = calc_momentum(conn, target_date=date(2026,3,20))
- # res は [{ "date": ..., "code": ..., "mom_1m": ..., ...}, ...]

注意点 / 運用メモ
----------------
- Look-ahead バイアス対策:
  - 各モジュールは内部で date 引数による参照を採用し、datetime.today() を直接参照しない設計です。
  - ETL/スコアリングは「対象日」を明示して呼び出してください。
- J-Quants API:
  - レート制限 120 req/min を守るため固定間隔の RateLimiter を使用。
  - 401 はリフレッシュ → 再試行処理あり。
- OpenAI 呼び出し:
  - gpt-4o-mini を利用する想定。JSON mode を利用して厳密な JSON を受け取る設計です。
  - リトライ・バックオフ・パースフォールバックの実装あり（失敗時は安全側の値を用いる）。
- ニュース収集:
  - RSS の SSRF や XML アンセーフ処理を想定して防御（defusedxml, ホスト判定等）。
  - MAX_RESPONSE_BYTES 等で DoS 対策を行っています。
- 自動 .env ロード:
  - .git または pyproject.toml を探索してプロジェクトルートを決定。見つからない場合は自動ロードをスキップ。

ディレクトリ構成（主なファイル）
------------------------------
以下は src/kabusys 配下の主なモジュール（抜粋）と簡単な説明です。

- src/kabusys/__init__.py
  - パッケージメタ（version, export）

- src/kabusys/config.py
  - 環境変数 / .env 読み込み、Settings クラス（jquants / kabu / slack / DB path / 監視閾値 等）

- src/kabusys/ai/
  - news_nlp.py       : ニュースを LLM でスコア化して ai_scores へ保存
  - regime_detector.py: ETF 1321 の MA200 とマクロニュースを合成して market_regime を書き込み
  - __init__.py       : score_news 等の公開

- src/kabusys/research/
  - factor_research.py: calc_momentum, calc_value, calc_volatility
  - feature_exploration.py: forward returns, IC, factor_summary, rank
  - __init__.py

- src/kabusys/data/
  - pipeline.py           : ETL パイプライン（run_daily_etl 等）
  - jquants_client.py     : J-Quants API クライアント（fetch/save 等）
  - news_collector.py     : RSS 取得・前処理・raw_news への保存
  - calendar_management.py: market_calendar 更新・営業日判定ユーティリティ
  - stats.py              : zscore_normalize 等の統計ユーティリティ
  - quality.py            : データ品質チェック（QualityIssue）
  - audit.py              : 監査ログ DDL / 初期化ユーティリティ
  - etl.py                : ETLResult の再エクスポート
  - __init__.py

その他
-----
- ロギング: 各モジュールは logging を利用。運用環境ではログ設定を行ってください（レベル・ハンドラ）。
- トランザクション管理: 各 DB 書き込みは冪等性を意識して実装（ON CONFLICT / DELETE→INSERT パターン）。監査スキーマ初期化は transactional オプションあり。
- テスト: 各種外部呼び出し（OpenAI, J-Quants, ネットワーク）はモックしやすいように分離実装されています（内部の _call_openai_api などを patch してテスト可能）。

サポート / 開発
----------------
- バグ報告や機能要望はプロジェクトの issue トラッカーへお願いします（該当リポジトリに依存）。
- 開発時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して .env 自動ロードを無効化できます（ユニットテスト等で便利です）。

以上が本リポジトリの概要と基本的な使い方の説明です。必要があればサンプルスクリプトや運用手順書（cron / systemd の例、監視ルール、Slack 通知設定など）を追加で作成できます。どの部分をより詳細に書くか指定してください。