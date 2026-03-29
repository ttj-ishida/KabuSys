KabuSys
=======

バージョン: 0.1.0

概要
----
KabuSys は日本株向けのデータパイプライン・リサーチ・AI スコアリング・監査ログ・市場レジーム判定を含む自動売買支援ライブラリです。J-Quants API からのデータ取得、DuckDB を使った永続化、OpenAI（gpt-4o-mini）によるニュースセンチメント評価、ファクター計算／特徴量解析、ETL の品質チェック、監査テーブル（シグナル → 発注 → 約定のトレース）などを提供します。

主な機能
--------
- 環境設定管理（.env 自動読み込み / 必須項目チェック）
- J-Quants API クライアント（株価 / 財務 / 市場カレンダー取得、保存）
- ニュース収集（RSS → raw_news、SSRF 対策、テキスト前処理）
- OpenAI を用いたニュースセンチメント評価（銘柄別 ai_scores）
- 市場レジーム判定（1321 の MA200 乖離 + マクロニュースセンチメント）
- ETL パイプライン（差分取得、保存、品質チェック）
- データ品質チェック（欠損、スパイク、重複、日付不整合）
- 監査ログスキーマ初期化（signal_events / order_requests / executions）
- 研究用ユーティリティ（モメンタム／バリュー／ボラティリティ等のファクター計算、forward returns、IC、統計サマリー）
- 汎用統計ユーティリティ（Zスコア正規化など）

必要条件
--------
- Python 3.10+
- 依存パッケージ（主要なもの）:
  - duckdb
  - openai
  - defusedxml
- インターネット接続（J-Quants / OpenAI / RSS 取得時）
- J-Quants リフレッシュトークン（JQUANTS_REFRESH_TOKEN）
- OpenAI API キー（OPENAI_API_KEY） — AI スコアリング機能を使う場合

セットアップ手順
--------------
1. リポジトリをクローン／配置
   - pip パッケージとして開発インストールすることを想定:
     ```
     pip install -e .
     ```

2. Python 依存関係をインストール
   - 例:
     ```
     pip install duckdb openai defusedxml
     ```

3. 環境変数の準備
   - プロジェクトルート（.git または pyproject.toml のあるディレクトリ）に .env を配置すると自動で読み込まれます。
   - 自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト時など）。
   - 必須の環境変数（主なもの）
     - JQUANTS_REFRESH_TOKEN: J-Quants 用リフレッシュトークン（必須）
     - OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合）
     - KABU_API_PASSWORD: kabu ステーション API パスワード（発注連携を行う場合）
     - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID: Slack 通知連携（必要に応じて）
   - 任意 / デフォルト:
     - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト: data/monitoring.db）
     - KABUSYS_ENV（development / paper_trading / live、デフォルト development）
     - LOG_LEVEL（DEBUG/INFO/...、デフォルト INFO）

   - .env の例:
     ```
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     OPENAI_API_KEY=sk-...
     KABU_API_PASSWORD=your_kabu_password
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     ```

4. DuckDB 用ディレクトリ作成
   - settings.duckdb_path（または指定したパス）の親ディレクトリを作成しておきます（save メソッドも親ディレクトリを作成することがありますが念のため）。

基本的な使い方（コード例）
------------------------

- 設定の読み込み（settings オブジェクト）
  ```python
  from kabusys.config import settings

  print(settings.duckdb_path)
  print(settings.is_dev)
  ```

- DuckDB 接続と ETL の実行
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメントを生成して ai_scores に書き込む
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  written = score_news(conn, target_date=date(2026, 3, 20))
  print("written:", written)
  ```
  - api_key を明示的に渡すことも可能（テストやマルチアカウント時）:
    ```python
    score_news(conn, date(2026, 3, 20), api_key="sk-...")
    ```

- 市場レジーム判定（regime）を実行
  ```python
  from kabusys.ai.regime_detector import score_regime
  written = score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 研究用ファクター計算（例: momentum）
  ```python
  from kabusys.research.factor_research import calc_momentum
  records = calc_momentum(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログ DB 初期化（監査用 DuckDB を別ファイルで用意する場合）
  ```python
  from kabusys.data.audit import init_audit_db
  conn_audit = init_audit_db("data/audit.duckdb")
  # これで監査用テーブルが作成されます
  ```

注意点・運用上のポイント
----------------------
- .env 自動読み込みはプロジェクトルート（.git または pyproject.toml）を基準に行われます。環境変数の取り扱いに注意してください。
- AI 呼び出し（OpenAI）はネットワークエラーやレート制限を考慮したリトライ実装がありますが、APIキーや利用制限に注意してください。
- J-Quants API はレート制限を想定しており、モジュール内部でスロットリング・リトライを実装しています。大量取得は配慮してください。
- DuckDB の executemany に空リストを渡すと失敗するバージョンがあるため、このコードは空チェックを行っています。
- 日付（target_date 等）は内部で date.today() に頼らない設計です。バックテストや再現性が必要な処理では明示的に日付を渡してください。
- テスト時や特殊な環境で自動 .env 読み込みを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

ディレクトリ構成（主要ファイル）
------------------------------
（パッケージルート: src/kabusys/）

- __init__.py
- config.py
- ai/
  - __init__.py
  - news_nlp.py
  - regime_detector.py
- data/
  - __init__.py
  - jquants_client.py
  - pipeline.py
  - etl.py (ETLResult 再エクスポート)
  - news_collector.py
  - calendar_management.py
  - quality.py
  - stats.py
  - audit.py
  - (その他: pipeline で参照する quality 等)
- research/
  - __init__.py
  - factor_research.py
  - feature_exploration.py

各モジュールの役割（抜粋）
- kabusys.config
  - 環境変数の読み込み・検証。settings オブジェクトを通じて設定値を参照。
- kabusys.data.jquants_client
  - J-Quants API の取得／保存／認証（get_id_token）を実装。
- kabusys.data.pipeline / etl
  - run_daily_etl: 市場カレンダー → 株価 → 財務 → 品質チェック を順に実行。
- kabusys.data.news_collector
  - RSS 取得・前処理・保存のユーティリティ（SSRF/サイズ制限/トラッキング除去等）。
- kabusys.ai.news_nlp
  - OpenAI を用いたニュースセンチメントのバッチ評価（銘柄単位で ai_scores へ書き込み）。
- kabusys.ai.regime_detector
  - ETF 1321 の MA200 乖離とマクロニュースセンチメントを合成して market_regime を更新。
- kabusys.research.*
  - ファクター計算・特徴量探索・IC 計算など研究用のユーティリティ群。
- kabusys.data.audit
  - シグナル → 発注 → 約定を追跡する監査テーブル定義と初期化ユーティリティ。

トラブルシューティング
---------------------
- 環境変数が足りない / _require() による ValueError が出る:
  - .env を確認し必須値（JQUANTS_REFRESH_TOKEN など）を設定してください。
- OpenAI 呼び出しに関連するエラー:
  - OPENAI_API_KEY を正しく設定しているか確認。API のレート制限やモデル名（gpt-4o-mini）が利用できるかも確認してください。
- DuckDB 周りのエラー:
  - executemany の引数が空になっていないか等、呼び出し側のパラメータを確認してください。
- RSS 取得でリダイレクトや接続に失敗する:
  - news_collector は SSRF 防止検査を行います。内部アドレスへの接続や非 http/https スキームは拒否されます。

開発 / テスト
--------------
- 自動 .env 読み込みを無効にしたいテストでは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- AI 呼び出しや外部 API は unittest.mock.patch で _call_openai_api や _urlopen、jquants_client._request 等をモックするとテストしやすくなります。
- 型注釈は Python 3.10 以降の構文（X | Y）を使用しています。テスト環境の Python バージョンにご注意ください。

ライセンス・貢献
----------------
- ここにはライセンス情報や貢献方法（PR / Issue の出し方）を追記してください（現状 README テンプレートには含まれていません）。

最後に
------
この README はコードベースの主要機能・利用方法に焦点を当てた概要です。詳細な運用手順やプロダクション構成（監視・再試行・CI/CD・シークレット管理等）は別途運用ドキュメントを用意することを推奨します。必要があれば運用手順や具体的な設定ファイルのテンプレートも作成しますのでリクエストしてください。