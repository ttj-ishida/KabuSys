KabuSys — 日本株向けデータプラットフォーム & 自動売買ユーティリティ
=============================================================================

概要
----
KabuSys は日本株のデータ取得・ETL、ニュースの収集・NLP スコアリング、マーケットレジーム判定、リサーチ用ファクター計算、監査トレース（発注／約定ログ）などを包含したライブラリ群です。J-Quants API / DuckDB / OpenAI（gpt-4o-mini）などを組み合わせ、バッチ ETL → 品質チェック → AI スコアリング → 監査ログ保存 といったワークフローをサポートします。設計上、ルックアヘッド・バイアスを避けること、DB 保存の冪等性、外部 API のリトライ・レート制御、安全対策（SSRF 対策など）に配慮しています。

主な機能
--------
- J-Quants API クライアント（差分取得・ページネーション・トークン自動リフレッシュ、レート制御）
- ETL パイプライン（prices / financials / market calendar の差分取得・保存・品質チェック）
- 市場カレンダー管理（営業日判定 / next/prev / 範囲取得 / 夜間更新ジョブ）
- ニュース収集（RSS → raw_news、SSRF・サイズ制限・トラッキング除去）
- ニュース NLP（OpenAI を用いた銘柄別センチメントスコアのバッチ取得）
- 市場レジーム判定（ETF 1321 の MA200 とマクロニュースセンチメントの合成判定）
- 研究用モジュール（モメンタム/バリュー/ボラティリティなどのファクター計算、forward returns、IC、統計サマリー）
- データ品質チェック（欠損・重複・スパイク・日付整合性）
- 監査ログスキーマの初期化・管理（signal_events / order_requests / executions）
- DuckDB を想定した DB 操作ユーティリティ群

セットアップ手順
----------------

前提
- Python 3.10 以上（コードで型演算子 "|" を使用）
- ネットワークアクセス（J-Quants / OpenAI / RSS フィード）
- DuckDB（Python パッケージで利用）

1) リポジトリをクローン / パッケージをインストール
- 開発中はプロジェクトルートで editable install が便利です。
  pip install -e . が使えるように pyproject.toml / setup を用意してください。
- 最小依存パッケージ例:
  pip install duckdb openai defusedxml

（プロジェクトに requirements.txt / pyproject.toml があればそちらを使用してください）

2) 環境変数 / .env の準備
- プロジェクトルート（.git または pyproject.toml のあるディレクトリ）に .env を置くと自動で読み込まれます。
- 自動ロードを無効化したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

必須（代表）
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
- OPENAI_API_KEY: OpenAI API キー（score_news / regime_detector 実行時に必要）
- KABU_API_PASSWORD: kabu ステーション API のパスワード（実行環境で発注等行う場合）
- SLACK_BOT_TOKEN, SLACK_CHANNEL_ID: Slack 通知を使う場合

（詳しい変数一覧は「環境変数」節を参照）

3) DuckDB / 監査 DB 初期化（例）
- DuckDB ベース DB に対して監査スキーマを作成する:
  python
  >>> import duckdb
  >>> from kabusys.data.audit import init_audit_schema
  >>> conn = duckdb.connect("data/kabusys.duckdb")
  >>> init_audit_schema(conn)

- 監査専用 DB を作る場合:
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")

使い方（簡易サンプル）
---------------------

まず DuckDB 接続と設定を読み込み:

python
>>> import duckdb
>>> from kabusys.config import settings
>>> conn = duckdb.connect(str(settings.duckdb_path))

ETL（日次）
- 日次 ETL を実行して prices / financials / calendar を差分取得・保存・品質チェック:

python
>>> from datetime import date
>>> from kabusys.data.pipeline import run_daily_etl
>>> result = run_daily_etl(conn, target_date=date(2026,3,20))
>>> print(result.to_dict())

ニューススコアリング（OpenAI）
- 前日 15:00 JST ～ 当日 08:30 JST のウィンドウを対象に銘柄ごとのスコアを ai_scores に保存:

python
>>> from kabusys.ai.news_nlp import score_news
>>> from datetime import date
>>> n_written = score_news(conn, target_date=date(2026,3,20))
>>> print("scored:", n_written)

市場レジーム判定（MA200 + マクロセンチメント）
- ETF 1321 の MA200 突合とマクロニュースを組み合わせて market_regime テーブルへ保存:

python
>>> from kabusys.ai.regime_detector import score_regime
>>> from datetime import date
>>> score_regime(conn, target_date=date(2026,3,20))

ファクター計算（研究用途）
- モメンタム等を計算:

python
>>> from kabusys.research.factor_research import calc_momentum
>>> from datetime import date
>>> records = calc_momentum(conn, target_date=date(2026,3,20))

監査スキーマ初期化（別 DB）
python
>>> from kabusys.data.audit import init_audit_db
>>> audit_conn = init_audit_db("data/monitoring.duckdb")

設計上の注意事項（要点）
-----------------------
- ルックアヘッドバイアス対策: 多くの関数は内部で今日の日付を参照せず、引数に与えた target_date を基準に処理します。DB クエリも date < target_date 等でルックアヘッドを防止します。
- 冪等性: ETL 保存処理は ON CONFLICT DO UPDATE を用いて冪等的に保存します（部分失敗時に他データを保護する工夫あり）。
- リトライ / レート制御: J-Quants クライアントは固定間隔のスロットリングと指数バックオフリトライを実装しています。OpenAI 呼び出しもリトライロジックを持ちます。
- セキュリティ: RSS 収集では SSRF 対策、XML の defusedxml 使用、最大レスポンスバイト制限を行っています。
- テスト性: OpenAI 呼び出しなどは内部関数を monkeypatch / mock で差し替えてテストしやすい設計です。
- DuckDB 互換性注意: 一部 executemany の空リスト禁止等、DuckDB のバージョンに依存する振る舞いを回避するチェックがあります。

環境変数（主要）
----------------
- JQUANTS_REFRESH_TOKEN (必須): J-Quants の refresh token
- OPENAI_API_KEY (必須 for AI): OpenAI API キー
- KABU_API_PASSWORD (必須 if using kabu): kabu API パスワード
- KABU_API_BASE_URL (任意): kabu API ベース URL（デフォルト http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN, SLACK_CHANNEL_ID (任意): Slack 通知用
- DUCKDB_PATH (任意): DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH (任意): SQLite（監視用）ファイルパス（デフォルト data/monitoring.db）
- KABUSYS_ENV (任意): development | paper_trading | live（default: development）
- LOG_LEVEL (任意): DEBUG | INFO | WARNING | ERROR | CRITICAL
- KABUSYS_DISABLE_AUTO_ENV_LOAD (任意): 自動 .env ロードを無効化（値が存在すれば無効化）

ディレクトリ構成（主要ファイル）
-------------------------------
src/kabusys/
- __init__.py — パッケージ初期化、公開サブモジュール列挙
- config.py — 環境変数 / .env 自動読み込み、Settings API

src/kabusys/data/
- __init__.py
- jquants_client.py — J-Quants API クライアント（取得 / 保存ロジック）
- pipeline.py — ETL パイプライン（run_daily_etl 等）
- etl.py — ETL 結果型のエクスポート
- calendar_management.py — 市場カレンダー管理（営業日判定 / 更新ジョブ）
- news_collector.py — RSS 収集・前処理・保存処理（SSRF 対策あり）
- quality.py — データ品質チェック群
- stats.py — 共通統計ユーティリティ（zscore等）
- audit.py — 監査ログスキーマ初期化 / 監査 DB ユーティリティ

src/kabusys/ai/
- __init__.py — score_news のエクスポート
- news_nlp.py — 銘柄別ニュースセンチメントスコア取得（OpenAI）
- regime_detector.py — 市場レジーム判定（MA200 + マクロセンチメント）

src/kabusys/research/
- __init__.py — 研究用 API エクスポート
- factor_research.py — モメンタム / バリュー / ボラティリティ等
- feature_exploration.py — 将来リターン, IC, 統計サマリー 等

その他
- data/* — 既定の DB 保存先（例: data/kabusys.duckdb, data/monitoring.db）

開発 / テスト時のヒント
----------------------
- テストで .env 自動読み込みを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI 呼び出しや外部 HTTP は unittest.mock で内部関数（_call_openai_api, _urlopen 等）を差し替えることで簡単に分離テスト可能です。
- DuckDB のスキーマ作成・マイグレーションはアプリ側で一度実行しておくと ETL がスムーズに動作します（audit.init_audit_schema などを利用）。

ライセンス / 貢献
-----------------
（このリポジトリにライセンスが無ければ追記してください）

最後に
------
この README はコードベースからの抜粋的な利用方法と設計方針の概要を示しています。個々の関数や引数の詳細、例外仕様については該当モジュール（kabusys/data/pipeline.py、kabusys/ai/news_nlp.py など）の docstring を参照してください。追加でサンプルスクリプトや CI 設定、requirements の追記が必要であれば教えてください。