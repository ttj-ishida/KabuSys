KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株向けのデータプラットフォーム・リサーチ・AI スコアリング・監査・ETL を含む
ライブラリ群です。J-Quants API からのデータ取得、DuckDB ベースのローカル DB 管理、ニュースの
NLP スコアリング（OpenAI）や市場レジーム判定、ファクター計算・探索などを提供します。
バックテストや自動売買システムの基盤として利用できるよう設計されています。

主な特徴
--------
- J-Quants API クライアント（株価日足・財務データ・JPX カレンダー取得、トークン自動リフレッシュ・リトライ・レート制御）
- ETL パイプライン（差分フェッチ、バックフィル、品質チェック）
- ニュース収集（RSS）とニュース NLP（OpenAI）による銘柄別センチメントスコア生成
- 市場レジーム判定（ETF 1321 の MA とマクロ記事センチメントの合成）
- ファクター計算（モメンタム、バリュー、ボラティリティ等）と特徴量探索（将来リターン、IC、統計サマリ）
- データ品質チェック（欠損/重複/スパイク/日付不整合）
- 監査ログ・トレーサビリティ（signal -> order_request -> executions の監査テーブルと初期化ユーティリティ）
- DuckDB を利用したローカル永続化（監査 DB 初期化ユーティリティあり）
- 設定管理は環境変数（.env 自動ロード機能あり）

要求事項（想定）
---------------
- Python 3.10 以上（typing の構文に合わせているため）
- 必要な主な Python パッケージ（例）:
  - duckdb
  - openai
  - defusedxml
- 標準ライブラリの urllib / json / datetime 等を使用

（プロジェクト配布時には requirements.txt / pyproject.toml を参照してください）

環境変数（必須 / 推奨）
---------------------
最低限設定が必要なもの:
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（ETL 用）
- OPENAI_API_KEY: OpenAI API キー（ニュース・レジーム判定で使用）

その他（必要に応じて設定）:
- KABU_API_PASSWORD: kabuステーション API のパスワード
- KABU_API_BASE_URL: kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: LINE 通知用
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite DB パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV: environment（development | paper_trading | live）
- LOG_LEVEL: ログレベル（DEBUG|INFO|WARNING|ERROR|CRITICAL）
- PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START, CPU_THRESHOLD_PCT など監視関連

.env の自動読み込み
------------------
- パッケージ初期化時にプロジェクトルート（.git または pyproject.toml があるディレクトリ）を探索して
  .env → .env.local の順で自動読み込みします（OS 環境変数を上書きしない／.env.local は上書き可）。
- 自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト時に便利）。

セットアップ手順
--------------
1. リポジトリをクローン（例）
   - git clone <repo-url>

2. 仮想環境の作成（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージのインストール
   - pip install -U pip
   - pip install duckdb openai defusedxml
   （プロジェクトの pyproject.toml / requirements.txt があればそれを使用してください）
   - 開発環境として editable install:
     - pip install -e .

4. 環境変数を設定
   - プロジェクトルートに .env または .env.local を作成するか、環境変数をエクスポートしてください。
   - 最低例 (.env):
     ```
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     OPENAI_API_KEY=your_openai_api_key
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     ```
   - 注意: 実運用（live）では各種シークレットの管理に十分注意してください。

使い方（主なユースケース）
------------------------

1) DuckDB 接続を用意して日次 ETL を実行する（ETL 集約処理）
- サンプル:
  ```
  from datetime import date
  import duckdb
  from kabusys.config import settings
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- run_daily_etl は市場カレンダーの取得 → 株価 ETL → 財務 ETL → 品質チェック を順に実行し ETLResult を返します。

2) ニュースをスコアリングして ai_scores に書き込む
- サンプル:
  ```
  from datetime import date
  import duckdb
  from kabusys.config import settings
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect(str(settings.duckdb_path))
  n_written = score_news(conn, target_date=date(2026,3,20))
  print(f"written {n_written} scores")
  ```
- 注意: OPENAI_API_KEY が必要です。API 呼び出しはバッチ（最大20銘柄/コール）で実行され、リトライ・解析バリデーション付きです。

3) 市場レジーム判定を実行する
- サンプル:
  ```
  from datetime import date
  import duckdb
  from kabusys.config import settings
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect(str(settings.duckdb_path))
  score_regime(conn, target_date=date(2026,3,20))
  ```
- ETF 1321 の MA200 乖離（重み 70%）とマクロニュース LLM スコア（重み 30%）を合成します。

4) 監査ログテーブル（audit DB）を初期化する
- サンプル（専用ファイルを作る場合）:
  ```
  from kabusys.data.audit import init_audit_db

  conn = init_audit_db("data/audit.duckdb")
  # conn は監査テーブルが初期化された DuckDB 接続
  ```

5) カレンダー・営業日ユーティリティ
- 関数例:
  - is_trading_day(conn, d)
  - next_trading_day(conn, d)
  - prev_trading_day(conn, d)
  - get_trading_days(conn, s, e)
- これらは market_calendar テーブルがある場合は DB を優先し、無い場合は曜日
  ベースのフォールバック（週末を非営業日）を行います。

ディレクトリ構成（主要ファイル）
------------------------------
（src 配下を想定した主要モジュール一覧）
- src/kabusys/
  - __init__.py  -- パッケージ定義
  - config.py    -- 環境変数 / 設定管理（.env 自動ロード・設定プロパティ）
  - ai/
    - __init__.py
    - news_nlp.py      -- ニュース NLU / OpenAI 連携、ai_scores 書込み
    - regime_detector.py -- 市場レジーム判定ロジック
  - data/
    - __init__.py
    - pipeline.py      -- ETL パイプライン（run_daily_etl 等）
    - jquants_client.py -- J-Quants API クライアント（fetch / save / auth / rate limit）
    - news_collector.py -- RSS ニュース収集（SSRF 対策・前処理）
    - calendar_management.py -- 市場カレンダー管理・判定ロジック
    - quality.py       -- データ品質チェック
    - stats.py         -- 汎用統計（zscore_normalize）
    - etl.py           -- ETLResult 再エクスポート
    - audit.py         -- 監査ログスキーマの作成・初期化
  - research/
    - __init__.py
    - factor_research.py    -- ファクター計算（momentum, value, volatility）
    - feature_exploration.py-- 将来リターン / IC / 統計サマリ
  - monitoring/ (存在が想定されるがコードベースにより追加実装)
  - execution/ (同上)
  - strategy/ (戦略用モジュール配置想定)

設計上の注意点 / 重要な挙動
------------------------
- ルックアヘッドバイアス防止:
  - 多くのモジュール（news/NLP/regime/factor/forward returns 等）は datetime.today() を内部で参照せず、
    明示的な target_date 引数を受け取ることでバックテスト時のルックアヘッドを防止しています。
- レトライ・フェイルセーフ:
  - OpenAI 呼び出しや J-Quants API はリトライや 5xx の扱いが実装され、API 失敗時にはゼロスコアやスキップで継続する設計です（致命的例外は上位へ伝播）。
- DuckDB 互換性:
  - 一部処理は DuckDB の executemany の挙動やバインド制約に配慮した実装になっています（例: 空リストを executemany しない等）。
- セキュリティ:
  - news_collector は SSRF 対策（リダイレクト検証・プライベートアドレスブロック）・defusedxml を使った XML パース防御を実装しています。

トラブルシューティング
-----------------------
- .env が読み込まれない:
  - config._find_project_root は __file__ の親ディレクトリを起点に .git または pyproject.toml を探します。配布形態や実行コンテキストによって見つからない場合は自動ロードをスキップします。手動で環境変数を設定するか KABUSYS_DISABLE_AUTO_ENV_LOAD を利用してください。
- OpenAI または J-Quants の認証エラー:
  - 必要な環境変数（OPENAI_API_KEY, JQUANTS_REFRESH_TOKEN）が正しいか確認してください。J-Quants はトークン自動更新を試みますが、失敗すると例外になります。
- DuckDB のパスに書き込み権限がない:
  - settings.duckdb_path の親フォルダを作成するかパスを変更してください。

開発 / テスト時のヒント
-----------------------
- テストや CI で .env の自動読み込みを無効化するには:
  - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- OpenAI 呼び出しをユニットテストでモックする場合、モジュール内の _call_openai_api を patch して戻り値を制御することで外部コールを回避できます（news_nlp と regime_detector はそれぞれ別実装の _call_openai_api を持ちます）。

最後に
------
この README は提供されたコードベースの要点をまとめたものです。実運用時や拡張時は pyproject.toml / requirements.txt / CI 設定・運用ドキュメントを合わせて整備してください。追加で README の出力形式（より詳しい API リファレンス、CLI コマンド例、docker-compose 用の設定など）をご希望であれば教えてください。