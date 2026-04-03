KabuSys
=======

概要
----
KabuSys は日本株向けのデータプラットフォーム兼リサーチ / 自動売買支援ライブラリです。  
J-Quants API からのデータ収集（OHLCV・財務・市場カレンダー）、RSS ニュース収集、LLM を用いたニュースセンチメント評価、ファクター計算、ETL パイプライン、監査ログ（発注/約定トレース）などを含むモジュール群を提供します。

主な特徴
--------
- J-Quants API クライアント：株価日足 / 財務 / 市場カレンダーの取得・保存（ページネーション・リトライ・レート制御）
- ETL パイプライン：差分取得・バックフィル・品質チェック（欠損・スパイク・重複・日付整合性）
- ニュース収集：RSS 収集・前処理・raw_news への冪等保存（SSRF 対策・XML 安全パース）
- ニュース NLP：OpenAI（gpt-4o-mini）を使った銘柄別センチメントスコアリング（バッチ処理・リトライ）
- 市場レジーム判定：ETF(1321)の MA とマクロニュースを合成して日次でレジーム判定
- 研究用ユーティリティ：モメンタム / ボラティリティ / バリューなどのファクター計算、将来リターン計算、IC / 統計サマリー
- 監査ログスキーマ：signal → order_request → execution のトレーサビリティ用テーブルと初期化ユーティリティ
- 環境設定管理：.env 自動読み込み（プロジェクトルート検出）、必須設定チェック、環境別フラグ

セットアップ手順
----------------

前提
- Python 3.10+（typing の Union | などの構文を使用）
- ネットワークアクセス（J-Quants / OpenAI / RSS）

1. 仮想環境作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要なパッケージをインストール（代表例）
   - pip install duckdb openai defusedxml

   （プロジェクトに requirements.txt がある場合はそちらを使用してください。）

3. 環境変数の設定
   推奨はプロジェクトルートに .env を置くことです（.git または pyproject.toml を起点に自動検出します）。
   .env の例（必須/推奨項目）:
   - JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token     # 必須（J-Quants 認証用）
   - OPENAI_API_KEY=your_openai_api_key                  # LLM 呼び出しに必要
   - KABU_API_PASSWORD=your_kabu_station_password        # kabuステーション API を使う場合
   - KABU_API_BASE_URL=http://localhost:18080/kabusapi   # 任意（デフォルト値あり）
   - DUCKDB_PATH=data/kabusys.duckdb                     # デフォルト: data/kabusys.duckdb
   - SQLITE_PATH=data/monitoring.db                      # 監視用（デフォルト）
   - KABUSYS_ENV=development|paper_trading|live          # 環境（デフォルト development）
   - LOG_LEVEL=INFO                                      # ログレベル（DEBUG/INFO/...）
   - その他監視関連設定（PID_FILE_PATH, KILL_FLAG_PATH, CPU_THRESHOLD_PCT 等）

   補足:
   - 自動 .env 読み込みを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します（テスト等で使用）。
   - settings オブジェクト経由で設定値にアクセスできます（kabusys.config.settings）。

4. データベース初期化（監査ログなど）
   監査ログ用のテーブルを作成する例:
   - Python スニペット:
     from kabusys.config import settings
     import duckdb
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db(settings.duckdb_path)
     # conn を使って他処理も行えます

使い方（よく使うユースケース）
-----------------------------

1) 日次 ETL を実行して J-Quants データを取り込む
- 簡単なスクリプト例:
  from datetime import date
  import duckdb
  from kabusys.config import settings
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())

- run_daily_etl は市場カレンダー → 株価 → 財務 → 品質チェック の順に実行し ETLResult を返します。

2) ニュースセンチメント（銘柄別）をスコアリングする
- 例:
  from datetime import date
  import duckdb
  from kabusys.config import settings
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect(str(settings.duckdb_path))
  n_written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"書き込み銘柄数: {n_written}")

- OPENAI_API_KEY が環境変数に設定されている場合、api_key 引数は不要です。

3) 市場レジーム判定を行う
- 例:
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  score_regime(conn, target_date=date(2026, 3, 20))

4) RSS の収集（ニュース収集）
- fetch_rss 関数で RSS を取得して raw_news に保存するワークフローを実装できます（保存ロジックは別実装想定）。
- 注意: fetch_rss は SSRF・サイズ上限・XML 安全パースなどの保護を含んでいます。

設定の参照方法
--------------
コードからは kabusys.config.settings を通して設定を取得します。例:
from kabusys.config import settings
print(settings.duckdb_path, settings.env, settings.is_live)

主要な環境変数（抜粋）
- JQUANTS_REFRESH_TOKEN (必須): J-Quants のリフレッシュトークン
- OPENAI_API_KEY (必須 for LLM): OpenAI API キー（news_nlp / regime_detector）
- KABU_API_PASSWORD: kabuステーション API パスワード
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB のファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（デフォルト data/monitoring.db）
- KABUSYS_ENV: development / paper_trading / live（必須値の検証あり）
- LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 自動 .env 読み込みを無効化する場合に 1 を設定

ディレクトリ構成（主要ファイル）
------------------------------
以下は src/kabusys 以下の主な構造（抜粋）です:

- kabusys/
  - __init__.py                 : パッケージのエントリポイント（__version__ 等）
  - config.py                   : 環境変数 / 設定管理（.env 自動読み込み等）
  - ai/
    - __init__.py
    - news_nlp.py               : ニュースセンチメントスコアリング（OpenAI）
    - regime_detector.py        : マーケットレジーム判定（ETF MA + マクロセンチ）
  - data/
    - __init__.py
    - jquants_client.py         : J-Quants API クライアント（取得 + DuckDB 保存）
    - pipeline.py               : ETL パイプライン（run_daily_etl 等）
    - etl.py                    : ETLResult の再エクスポート
    - calendar_management.py    : 市場カレンダー管理（営業日判定 / 更新ジョブ）
    - news_collector.py         : RSS フィード収集（SSRF 対策・XML 安全パース）
    - quality.py                : データ品質チェック（欠損 / スパイク / 重複 / 日付不整合）
    - stats.py                  : 共通統計ユーティリティ（zscore_normalize）
    - audit.py                  : 監査ログスキーマ初期化（signal/order_requests/executions）
  - research/
    - __init__.py
    - factor_research.py        : モメンタム / ボラティリティ / バリュー等
    - feature_exploration.py    : 将来リターン / IC / 統計サマリー等

設計上のポイント / 注意事項
-------------------------
- ルックアヘッドバイアス回避: 多くのモジュールは内部で date.today() を直接参照せず、target_date 引数で明示的に日付を与えて使用します。
- 冪等性: DuckDB への保存は ON CONFLICT DO UPDATE 等で冪等動作を目指しています。
- LLM 呼び出し: OpenAI の API 呼び出しにはリトライやレスポンスバリデーションが実装されていますが、APIキー管理やコストに注意してください。
- セキュリティ: RSS の URL 正規化、SSRF / プライベートアドレス検査、defusedxml による XML パース等の対策を実装しています。
- 自動 .env 読み込みはプロジェクトルート（.git または pyproject.toml を起点）を探索します。テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能です。

開発・テスト
-------------
- モジュール内の多くの外部呼び出し（OpenAI, J-Quants, ネットワーク）には差し替え可能な内部関数やモックポイントがあり、ユニットテスト作成がしやすく設計されています（例: news_nlp._call_openai_api をパッチしてテスト）。
- ローカルでの開発は DUCKDB のインメモリモード(":memory:") を使うと高速です。

ライセンス / 貢献
-----------------
（ライセンス情報がリポジトリに含まれていない場合はプロジェクトのルートに LICENSE ファイルを追加してください。）  
貢献手順やコントリビューションガイドラインはリポジトリに合わせて追記してください。

お問い合わせ / サポート
----------------------
- バグ報告や機能要求はリポジトリの Issue に投稿してください。
- 機密情報（APIキー等）は公開 Issue に含めないでください。

以上が KabuSys の概要と導入・利用ガイドです。初期セットアップや実装の補足が必要であれば、どのユースケースについて詳しく知りたいか教えてください。