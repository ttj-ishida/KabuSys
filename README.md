KabuSys — README
=================

概要
----
KabuSys は日本株向けのデータプラットフォーム / 研究・自動売買基盤の骨組みを提供する Python パッケージです。  
主な目的は以下です。

- J-Quants からのデータ取得（株価・財務・マーケットカレンダー）
- DuckDB を使ったデータ保存・ETL パイプライン
- ニュースを用いた LLM ベースのセンチメント算出（銘柄別・マクロ）
- 市場レジーム判定（ETF + マクロセンチメントの合成）
- 研究用ファクター計算・特徴量探索（モメンタム・バリュー・ボラティリティ等）
- 監査ログ（シグナル→発注→約定のトレーサビリティ）用スキーマ初期化

主な利用シナリオは「データ収集（ETL）→品質チェック→特徴量作成→戦略生成→監査ログ／発注」のワークフローになります。

機能一覧
--------
- 環境設定管理
  - .env / .env.local / OS 環境変数の自動読み込み（プロジェクトルート検出）
  - 必須値の取得（J-Quants トークン等）
- データ収集（jquants_client）
  - 日次株価（OHLCV）、財務データ、JPX マーケットカレンダーの取得・保存
  - レート制限・リトライ・トークン自動リフレッシュ対応
- ETL パイプライン（data.pipeline）
  - 差分取得・バックフィル・品質チェック（quality）を含む日次 ETL run_daily_etl
  - ETL 結果を ETLResult オブジェクトで返却
- データ品質チェック（data.quality）
  - 欠損、重複、スパイク、日付不整合などを検出し QualityIssue を返す
- カレンダー管理（data.calendar_management）
  - 営業日判定、next/prev 営業日取得、カレンダー更新ジョブ
- ニュース収集（data.news_collector）
  - RSS 取得・前処理・SSRF 対策・トラッキングパラメータ除去・冪等保存
- LLM ベースの NLP（ai.news_nlp / ai.regime_detector）
  - 銘柄ごとのニュースセンチメント（batch 処理、JSON Mode）
  - マクロセンチメントと ETF 200 日 MA 乖離を合成した市場レジーム判定
  - OpenAI 呼び出しはリトライ・パースフォールバックを備える
- 研究（research）
  - モメンタム / バリュー / ボラティリティ等のファクター計算
  - 将来リターン計算・IC（Information Coefficient）等の統計ツール
- 監査（data.audit）
  - signal_events / order_requests / executions 等の監査テーブル DDL と初期化関数

セットアップ手順
----------------
前提
- Python 3.10 以上（typing の | 演算子を使用）
- 必要な外部ライブラリ（主要なもの）:
  - duckdb
  - openai
  - defusedxml

一般的な手順例:

1) 仮想環境の作成（例）
   $ python -m venv .venv
   $ source .venv/bin/activate

2) 依存パッケージのインストール（最低限）
   $ pip install duckdb openai defusedxml

   プロジェクト配布で requirements.txt / pyproject.toml があればそちらを利用してください。

3) 環境変数設定
   - プロジェクトルート（.git または pyproject.toml のあるディレクトリ）に .env を置くと自動で読み込まれます。
   - 読み込み順序: OS 環境 > .env.local > .env
   - 自動読み込みを無効にする場合:
     KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を環境変数で設定してください。

   主に必要な環境変数（最低限）:
   - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（必須）
   - OPENAI_API_KEY        : OpenAI API キー（score_news / score_regime 実行時に必要）
   - KABU_API_PASSWORD     : kabu ステーション API のパスワード（発注連携がある場合）
   オプション・デフォルト:
   - KABUSYS_ENV (development | paper_trading | live) デフォルト: development
   - LOG_LEVEL (DEBUG|INFO|...) デフォルト: INFO
   - DUCKDB_PATH デフォルト: data/kabusys.duckdb
   - SQLITE_PATH デフォルト: data/monitoring.db

4) データベースディレクトリ作成
   DuckDB や監査 DB のパスに指定された親ディレクトリを作成しておきます（init 関数は自動作成する場合もありますが、権限等に注意）。

使い方（主要な操作例）
--------------------

- 設定値をコードから参照する
  from kabusys.config import settings
  token = settings.jquants_refresh_token
  is_live = settings.is_live

- 日次 ETL を実行する（例: Python スクリプト内で）
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())

  run_daily_etl は内部でカレンダー ETL → prices ETL → financials ETL → 品質チェック を順に実行します。ETLResult に各ステップの統計・検出された品質問題が含まれます。

- ニュースセンチメントをスコア化する（銘柄別 ai_scores への書き込み）
  from kabusys.ai.news_nlp import score_news
  from datetime import date
  import duckdb

  conn = duckdb.connect("data/kabusys.duckdb")
  n_written = score_news(conn, target_date=date(2026,3,20), api_key="sk-...")
  print("書き込み銘柄数:", n_written)

  注意: OPENAI_API_KEY を環境変数に設定している場合、api_key 引数は省略可。

- 市場レジームを判定して書き込む
  from kabusys.ai.regime_detector import score_regime
  from datetime import date
  import duckdb

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026,3,20), api_key="sk-...")

- 監査ログ用 DB を初期化する
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  # これで signal_events, order_requests, executions 等のテーブルが作成されます

- 研究用ファクター計算の例
  from kabusys.research.factor_research import calc_momentum
  import duckdb
  from datetime import date

  conn = duckdb.connect("data/kabusys.duckdb")
  mom = calc_momentum(conn, target_date=date(2026,3,20))
  # mom は各銘柄ごとの dict のリストを返します

注意点・運用における設計ポリシー
-----------------------------
- ルックアヘッドバイアス防止
  - モジュール内の多くの関数は内部で datetime.today() を参照せず、必ず target_date を引数で受け取る設計です。バックテスト等で過去時点の再現が容易です。
- フェイルセーフ
  - LLM 呼び出しや外部 API 呼び出しで失敗した場合、多くの箇所でフェイルセーフ（0.0 にフォールバック、エラーをログ化して処理継続）を採用しています。
- 冪等性
  - DuckDB への保存は ON CONFLICT DO UPDATE / DO NOTHING を用い、再実行で重複を起こさないようにしています。
- セキュリティ
  - RSS の取得では SSRF 対策、defusedxml による XML パース保護などを実装しています。

主要な環境変数一覧（抜粋）
-------------------------
- JQUANTS_REFRESH_TOKEN (必須)
- OPENAI_API_KEY (score_news / score_regime 実行時に必要)
- KABU_API_PASSWORD (kabu API)
- KABUSYS_ENV (development | paper_trading | live) デフォルト: development
- LOG_LEVEL (DEBUG|INFO|...)
- DUCKDB_PATH デフォルト: data/kabusys.duckdb
- SQLITE_PATH デフォルト: data/monitoring.db
- KABUSYS_DISABLE_AUTO_ENV_LOAD = 1 自動 .env 読み込みの無効化

ディレクトリ構成（概要）
-----------------------
src/kabusys/
- __init__.py                — パッケージ定義（サブパッケージ公開）
- config.py                  — 環境変数 / .env ロード・Settings
- ai/
  - __init__.py
  - news_nlp.py              — ニュースセンチメント（銘柄別）
  - regime_detector.py      — ETF MA + マクロセンチメント合成による市場レジーム判定
- data/
  - __init__.py
  - jquants_client.py        — J-Quants API クライアント（取得＋保存）
  - pipeline.py             — ETL パイプライン（run_daily_etl 他）
  - quality.py              — データ品質チェック
  - stats.py                — zscore 等の統計ユーティリティ
  - calendar_management.py  — 市場カレンダー管理（営業日判定等）
  - news_collector.py       — RSS 収集・前処理
  - audit.py                — 監査テーブル DDL / 初期化
  - etl.py                  — ETLResult の再エクスポート
- research/
  - __init__.py
  - factor_research.py      — モメンタム/バリュー/ボラティリティ計算
  - feature_exploration.py  — 将来リターン / IC / 統計サマリー 等
- ai/、research/、data/ などのモジュール群は相互に明確な責務分離をしています（例: ai.regime_detector は news_nlp の内部関数を共有しない設計）。

ライセンス・貢献
----------------
本ドキュメントではライセンス・貢献ルールは明示していません。パッケージルートに LICENSE / CONTRIBUTING.md があればそちらを参照してください。

サポート
-------
問題点・バグ報告・改善提案は Issue を起票してください。使用時は常にログ（LOG_LEVEL）を INFO 以上にして動作を監視することを推奨します。

以上。必要であれば、インストール用の pyproject.toml / requirements.txt の例や CI 向けの実行手順（cron / systemd / Dockerfile）も作成できます。どの形式が必要か教えてください。