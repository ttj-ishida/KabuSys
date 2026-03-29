# KabuSys — 日本株自動売買プラットフォーム（README）

KabuSys は日本株のデータ取得・品質管理・ファクター研究・AI ベースのニュース解析・監査ログ等を含む自動売買基盤の Python ライブラリ群です。本リポジトリはデータパイプライン、研究用ユーティリティ、戦略・発注の監査基盤、そして OpenAI を利用したニュースセンチメント／市場レジーム判定などのコンポーネントを提供します。

目次
- プロジェクト概要
- 主な機能
- 前提・依存関係
- セットアップ手順
- 環境変数と設定
- 使い方（簡単なコード例）
- ディレクトリ構成
- 運用上の注意点

プロジェクト概要
- 日本株を対象にしたデータプラットフォームと研究／実行コンポーネント群。
- J-Quants API から株価・財務・カレンダーを差分取得して DuckDB に保存する ETL。
- RSS ベースのニュース収集と、OpenAI（gpt-4o-mini 等）を用いた銘柄別／マクロのセンチメントスコアリング。
- ファクター計算（モメンタム／バリュー／ボラティリティ等）と特徴量評価ツール。
- 発注から約定まで追跡できる監査（audit）テーブル定義と初期化ユーティリティ。
- データ品質チェック（欠損、重複、スパイク、日付不整合）機能。

主な機能
- ETL: daily / financials / calendar の差分取得と DuckDB への冪等保存（ON CONFLICT）。
- カレンダー管理: 営業日判定、次営業日/前営業日の取得、カレンダー更新ジョブ。
- ニュース収集: RSS 取得・前処理、raw_news への冪等保存、SSRF/サイズ上限対策。
- AI スコアリング:
  - news_nlp.score_news: 銘柄ごとのニュースセンチメントを ai_scores に書き込み。
  - regime_detector.score_regime: ETF（1321）200日MA乖離とマクロニュースを合成して market_regime に記録。
- 研究ツール:
  - ファクター計算（calc_momentum / calc_value / calc_volatility）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリ、Zスコア正規化
- 監査ログ: signal_events / order_requests / executions テーブル定義と初期化（init_audit_schema / init_audit_db）。
- データ品質チェック（quality.run_all_checks）で ETL 後の健全性検査。

前提・依存関係
- Python 3.10 以上（型記法・Union 演算子等を使用）
- ライブラリ（主なもの）:
  - duckdb
  - openai
  - defusedxml
- 標準ライブラリ：urllib, json, datetime, logging など

（パッケージ化時に requirements.txt / pyproject.toml を用意してください。上記は最低限の依存です）

セットアップ手順（開発環境）
1. Python のインストール（3.10+）
2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  または .venv\Scripts\activate
3. パッケージのインストール（プロジェクトルートで）
   - pip install -e .            # editable インストール（プロジェクトがパッケージ化済みの場合）
   - あるいは必要パッケージを個別にインストール:
     - pip install duckdb openai defusedxml
4. 環境変数の設定:
   - プロジェクトルートに .env または .env.local を置くと自動的に読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）
   - 必要な環境変数（後述）を設定してください。

環境変数と設定（主なキー）
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector に必要）
- SLACK_BOT_TOKEN: Slack Bot トークン（通知等に利用する場合）
- SLACK_CHANNEL_ID: Slack チャンネル ID
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV: 実行環境（development, paper_trading, live）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）

.env の自動ロードについて
- .env と .env.local はプロジェクトルート（.git または pyproject.toml を起点）から自動読み込みされます。
- テストや明示的制御をしたい場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロードを無効化できます。

使い方（簡単なコード例）
- DuckDB 接続を作り ETL を実行する例:

  from datetime import date
  import duckdb
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")  # データベースファイルパス
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())

- ニューススコアリング（OpenAI API キーが設定されている前提）:

  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  n_written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"書き込んだ銘柄数: {n_written}")

- 市場レジーム判定:

  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20))

- 監査ログ用 DB 初期化（監査専用 DB または 既存コネクションに適用）:

  from kabusys.data.audit import init_audit_db, init_audit_schema
  import duckdb

  # 監査専用ファイルを初期化して接続を得る
  audit_conn = init_audit_db("data/kabusys_audit.duckdb")

  # 既存 conn に監査スキーマだけ追加したい場合
  conn = duckdb.connect("data/kabusys.duckdb")
  init_audit_schema(conn, transactional=True)

設計上の注記（運用時に知っておくべきポイント）
- Look-ahead バイアス対策:
  - 多くのモジュールは datetime.today() / date.today() を内部参照せず、呼び出し側が target_date を渡す設計です。バックテストや再現性のため必ず明示的に日付を渡してください。
- API リトライ/レート制御:
  - J-Quants クライアントはレート制限（120 req/min）を守る実装、リトライ/トークン自動リフレッシュを備えています。
  - OpenAI 呼び出し部分は 429/ネットワーク/5xx に対する指数バックオフのリトライを行います（フェイルセーフとして失敗時は中立スコア 0.0 を採用する箇所があります）。
- データ品質チェック:
  - ETL 後に quality.run_all_checks を呼ぶことで欠損・重複・スパイク・日付不整合を検出できます。エラーの有無は ETLResult に格納されます。
- セキュリティ:
  - news_collector は SSRF 対策（リダイレクト先検査、プライベートアドレス拒否）、XML パースの defusedxml 使用、受信サイズ上限などを実施しています。

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py                      — 環境変数 / 設定管理（.env 自動読み込み）
  - ai/
    - __init__.py
    - news_nlp.py                   — 記事センチメントの LLM スコアリング
    - regime_detector.py            — ETF MA とマクロニュースを用いた市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py             — J-Quants API クライアント（取得・保存ロジック）
    - pipeline.py                   — ETL パイプラインと run_daily_etl
    - etl.py                        — ETL の公開インターフェース（ETLResult）
    - calendar_management.py        — マーケットカレンダー管理（営業日判定等）
    - news_collector.py             — RSS 収集・前処理
    - stats.py                      — 統計ユーティリティ（zscore_normalize 等）
    - quality.py                    — データ品質チェック
    - audit.py                      — 監査ログテーブル定義と初期化
  - research/
    - __init__.py
    - factor_research.py            — momentum/value/volatility のファクター計算
    - feature_exploration.py        — forward returns, IC, factor summary, rank
  - research/*.py、ai/*.py、data/*.py の各モジュールは互いに結合度を下げる設計（例: LLM 呼び出しを別関数で扱う）で実装されています。

追加情報 / 開発メモ
- テストの際は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動 .env ロードを抑制できます。
- OpenAI の JSON mode（response_format）を利用して厳密な JSON 応答を期待する設計になっていますが、レスポンスパースでのフォールバックロジックも備えています。
- DuckDB の executemany に関する互換性（空リスト不可）を考慮した実装が含まれます。

サポート
- この README はコードベースの主要な使い方と設計意図をまとめたものです。個別の関数や API の詳細は各モジュールの docstring を参照してください。

以上。必要であれば、README に含めるサンプル .env.example や requirements.txt、利用フロー図（ETL -> quality -> research -> strategy -> execution）を追記できます。どの情報を追加したいか教えてください。