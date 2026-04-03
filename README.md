README — KabuSys（日本株自動売買システム）
======================================

本ドキュメントは、ソースツリー（src/kabusys）に含まれるモジュール群の概要、セットアップ手順、基本的な使い方、ディレクトリ構成をまとめた README です。

プロジェクト概要
---------------
KabuSys は日本株向けのデータプラットフォーム／リサーチ／自動売買基盤のプロジェクトです。主要な機能群は以下の通りです。

- ETL（J-Quants からの株価・財務・マーケットカレンダー取得）と品質チェック
- ニュース収集（RSS）・ニュース NLP による銘柄センチメント算出（OpenAI を利用）
- 市場レジーム判定（ETF 1321 の MA とマクロニュースの LLM センチメントを統合）
- ファクター計算（モメンタム、バリュー、ボラティリティ等）と特徴量解析（IC 等）
- 監査ログ（signal → order → execution のトレーサビリティ）を DuckDB に保存
- J-Quants API クライアント（レート制限・リトライ・トークン自動リフレッシュ対応）
- ニュース収集における SSRF 対策・XML の安全パースなどセキュリティ考慮

設計上の注力点：
- ルックアヘッドバイアスの排除（内部で datetime.today() を直接参照しない設計）
- DuckDB を用いた冪等的なデータ保存（ON CONFLICT / executemany の扱いに注意）
- フェイルセーフ（API 失敗時はスコアを中立にする、部分失敗で他データを破壊しない等）
- テスト容易性（関数へ明示的に API キー注入可能、内部 HTTP 呼び出しをモック可能）

主な機能一覧
-------------
- data
  - jquants_client: J-Quants API からのデータ取得・保存（株価・財務・カレンダー等）
  - pipeline: 日次 ETL 実行（差分取得・保存・品質チェック）
  - calendar_management: JPX カレンダーの管理と営業日判定ユーティリティ
  - news_collector: RSS を安全に取得して raw_news に保存（SSRF対策・正規化）
  - quality: データ品質チェック（欠損・スパイク・重複・日付不整合）
  - audit: 監査ログ（signal/order/execution）用スキーマ初期化・ユーティリティ
  - stats: 汎用統計ユーティリティ（z-score 等）
- ai
  - news_nlp.score_news: 銘柄ごとのニュースセンチメントを OpenAI に送り ai_scores に保存
  - regime_detector.score_regime: ETF(1321) MA とマクロニュース LLM スコアを合成して market_regime に保存
- research
  - factor_research: モメンタム / ボラティリティ / バリュー等のファクター算出
  - feature_exploration: 将来リターン計算、IC、統計サマリ等
- config: 環境変数管理（.env 自動読み込みの仕組み・必須値チェック）
- __init__.py: パッケージ初期化（公開 API の整理）

依存関係（代表）
----------------
以下は本プロジェクトで使用される主要パッケージの例です（実際の requirements は別途管理してください）。

- Python 3.10+
- duckdb
- openai
- defusedxml
- その他: 標準ライブラリ（urllib, json, logging, datetime 等）

セットアップ手順
----------------

1. リポジトリをクローン
   - git clone ...

2. 仮想環境を作成・有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - pip install duckdb openai defusedxml
   - （プロジェクトを editable install する場合）pip install -e .

4. 環境変数の準備
   - プロジェクトルートに .env を置くことで自動読み込みされます（config モジュールが .git または pyproject.toml を起点に探します）。
   - 自動ロードを無効にする: 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定
   - 重要な環境変数（例）:
     - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
     - KABU_API_PASSWORD: kabu API パスワード（発注機能を使う場合）
     - OPENAI_API_KEY: OpenAI API キー（ai 関連を利用する場合）
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: 通知用（任意）
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
     - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
     - LOG_LEVEL: DEBUG/INFO/...（デフォルト: INFO）

   - 簡易 .env 例:
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     OPENAI_API_KEY=sk-...
     KABU_API_PASSWORD=your_kabu_password
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development

5. データディレクトリ等を作成
   - mkdir -p data

データベース初期化（監査ログなど）
-------------------------------
監査ログ用スキーマを初期化する例：

python スニペット例：
- DuckDB を使って監査 DB を作る
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  # conn は duckdb 接続オブジェクト

- 既存接続へスキーマ追加
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")
  from kabusys.data.audit import init_audit_schema
  init_audit_schema(conn, transactional=True)

基本的な使い方（コード例）
------------------------

- 設定値参照
  from kabusys.config import settings
  print(settings.duckdb_path)  # Path オブジェクト

- 日次 ETL を実行（pipeline.run_daily_etl）
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())

- ニュース NLP スコアリング（OpenAI キーは環境変数 OPENAI_API_KEY、または引数で指定可能）
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect(str(settings.duckdb_path))
  written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"written: {written}")

- 市場レジーム判定
  from kabusys.ai.regime_detector import score_regime
  written = score_regime(conn, target_date=date(2026,3,20))
  print("ok", written)

- ファクター算出（research）
  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
  mom = calc_momentum(conn, date(2026,3,20))
  vol = calc_volatility(conn, date(2026,3,20))

注意点 / 実運用に向けた補足
--------------------------
- API キーやパスワードは平文でコミットしないでください。.env を利用し、.gitignore で除外してください。
- OpenAI 呼び出しは課金対象です。バッチ単位でコストを確認してください。
- J-Quants の API レート制限（120 req/min）に合わせた制御が組み込まれていますが、大量取得や短期間に繰り返す呼び出しは注意してください。
- news_collector は SSRF / XML 攻撃対策を実装していますが、外部フィードを扱う際はソースの監査を推奨します。
- データ品質チェック（quality.run_all_checks）を ETL 後に実行し、重大な問題（欠損・重複・未来日など）がないか確認してください。
- 本リポジトリのコードはバックテスト目的のユーティリティと運用用 ETL を含みます。バックテスト時は Look-ahead Bias に注意し、テスト対象時点で利用可能なデータのみを使用してください（本コード群はその点に配慮した設計です）。

ディレクトリ構成（主要ファイル）
------------------------------
src/kabusys/
- __init__.py
- config.py                       — 環境設定 / .env 自動ロード
- ai/
  - __init__.py
  - news_nlp.py                    — ニュース NLP スコアリング（OpenAI）
  - regime_detector.py             — 市場レジーム判定
- data/
  - __init__.py
  - jquants_client.py              — J-Quants API クライアント（取得・保存）
  - pipeline.py                    — ETL パイプライン（run_daily_etl 等）
  - calendar_management.py         — JPX カレンダー管理 / 営業日判定
  - news_collector.py              — RSS 収集（SSRF 対策、正規化）
  - quality.py                     — 品質チェック
  - audit.py                       — 監査ログスキーマ / 初期化
  - stats.py                       — 統計ユーティリティ
  - etl.py                         — ETLResult の再エクスポート
- research/
  - __init__.py
  - factor_research.py             — ファクター計算（momentum/value/volatility）
  - feature_exploration.py         — 将来リターン、IC、統計サマリ 等
- research/...（他モジュール）
- (strategy, execution, monitoring 等のサブパッケージが想定される）

ライセンス・コントリビュート
-----------------------------
- この README にはライセンス情報を含めていません。リポジトリルートに LICENSE がある場合はそちらに従ってください。
- コントリビュートする際は、機密情報（鍵・トークン等）をコミットしないようご注意ください。

追加情報 / 問い合わせ
--------------------
- 実行時にエラーが出る場合はログレベルを DEBUG にして詳細ログを確認してください（環境変数 LOG_LEVEL=DEBUG）。
- テスト用に .env の自動ロードを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

以上。必要に応じて README に追記・拡張しますので、知りたい項目（例: 具体的な ETL のスキーマ、テーブル定義、テストの実行方法など）があれば教えてください。