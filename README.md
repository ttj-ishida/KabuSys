KabuSys
=======

日本株向けのデータプラットフォーム / 研究・自動売買ユーティリティ群です。  
DuckDB をデータレイクに利用し、J-Quants からのデータ取得（株価・財務・マーケットカレンダー）、ニュース収集・NLP スコアリング（OpenAI）、市場レジーム判定、ファクター計算・研究ユーティリティ、監査ログ（発注→約定トレース）などの機能を提供します。

主な機能
--------
- データ ETL
  - J-Quants API から株価（日足）、財務データ、JPX カレンダーを差分取得して DuckDB に保存
  - 差分取得 / バックフィル / 品質チェック（欠損・スパイク・重複・日付不整合）
- ニュース収集・NLP
  - RSS フィードからのニュース取得（SSRF 対策・サイズ制御・トラッキング除去）
  - OpenAI（gpt-4o-mini）を用いた銘柄別センチメントスコアリング（ai_scores）
  - マクロニュースを用いた市場レジーム判定（ma200 と LLM センチメントの合成）
- 研究用ユーティリティ
  - モメンタム / バリュー / ボラティリティ等のファクター計算
  - 将来リターン計算、IC（Information Coefficient）計算、ファクター統計サマリー
  - Zスコア正規化ユーティリティ
- カレンダー管理
  - market_calendar の取得・判定ロジック（営業日判定 / next/prev / SQ 判定）
- 監査ログ（Audit）
  - シグナル → 発注リクエスト → 約定 を UUID でトレースする監査テーブルの初期化ユーティリティ

前提・依存
----------
- Python >= 3.10（明示的な型合成演算子（|）や型ヒントを使用）
- 主要依存パッケージ（例）:
  - duckdb
  - openai
  - defusedxml
- OS 環境により追加で必要なパッケージがある場合があります（標準ライブラリ以外の HTTP / XML / 暗号等）。

セットアップ手順
----------------
1. リポジトリをクローン
   - git clone <repo-url>

2. 仮想環境を作成して有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - pip install -U pip
   - pip install duckdb openai defusedxml
   - またはローカル開発用: pip install -e .

4. 環境変数 / .env の準備
   - プロジェクトルートに .env（または .env.local）を置くと、自動で読み込まれます（デフォルト）。  
     自動読み込みを無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
   - 必須環境変数（examples を参考に .env を作成してください）:
     - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD     : kabuステーション API のパスワード（発注等を行う場合）
     - SLACK_BOT_TOKEN       : Slack 通知用 Bot トークン
     - SLACK_CHANNEL_ID      : Slack チャンネル ID
   - オプション:
     - KABUSYS_ENV           : development / paper_trading / live（デフォルト development）
     - LOG_LEVEL             : DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト INFO）
     - KABU_API_BASE_URL     : kabuAPI ベース URL（デフォルト http://localhost:18080/kabusapi）
     - DUCKDB_PATH           : DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH           : SQLite（Monitoring 用）パス（デフォルト data/monitoring.db）

使い方（基本例）
---------------

- 共通設定取得
  - from kabusys.config import settings
  - settings.jquants_refresh_token, settings.duckdb_path, settings.is_live などで参照できます。

- DuckDB 接続
  - import duckdb
  - conn = duckdb.connect(str(settings.duckdb_path))

- 日次 ETL の実行
  - from kabusys.data.pipeline import run_daily_etl
  - result = run_daily_etl(conn)  # target_date を指定可能
  - result は ETLResult オブジェクト（取得件数・保存件数・品質問題などを含む）

- ニュースセンチメントスコアリング（OpenAI 必須）
  - from kabusys.ai.news_nlp import score_news
  - from datetime import date
  - n = score_news(conn, target_date=date(2026, 3, 20))  # ai_scores に書き込む。戻り値は書き込んだ銘柄数

- 市場レジーム判定（MA200 + マクロセンチメント）
  - from kabusys.ai.regime_detector import score_regime
  - score_regime(conn, target_date=date(2026, 3, 20))  # market_regime に記録

- 監査ログ（Audit）スキーマ初期化
  - from kabusys.data.audit import init_audit_db
  - audit_conn = init_audit_db("data/audit.duckdb")  # 必要に応じてパスを作る

- ファクター計算・研究ユーティリティ
  - from kabusys.research import calc_momentum, calc_value, calc_volatility, calc_forward_returns, calc_ic, factor_summary
  - momentum = calc_momentum(conn, date(2026, 3, 20))
  - fwd = calc_forward_returns(conn, date(2026, 3, 20), horizons=[1,5,21])
  - ic = calc_ic(momentum, fwd, factor_col="mom_1m", return_col="fwd_1d")

- カレンダー操作
  - from kabusys.data.calendar_management import is_trading_day, next_trading_day, get_trading_days
  - is_trading_day(conn, date(2026,3,20))

注意点 / 実装上の設計方針
-----------------------
- Look-ahead バイアス防止:
  - バックテスト・指標計算で datetime.today()/date.today() を直接参照しない方針。
  - ETL / スコアリングいずれも target_date 引数を受け取り、過去データのみを参照します。
- フェイルセーフ:
  - OpenAI / J-Quants など外部 API に失敗が発生した場合、多くはフォールバック（例: 0.0）やスキップで継続し、例外を全体に伝播させない設計が採られています。ただし認証情報不足など明確な致命的条件は例外を投げます。
- 冪等性:
  - DuckDB へは ON CONFLICT DO UPDATE（保存系）や挿入前の重複チェック等で冪等性を確保するようになっています。
- セキュリティ/堅牢性:
  - RSS 取得は SSRF 対策・圧縮バッファ上限・トラッキング除去などを実装しています。
  - J-Quants クライアントはレート制御とリトライ・トークン自動リフレッシュを備えています。

ディレクトリ構成（主要ファイル）
-------------------------------
（src/kabusys 配下の主要モジュール抜粋）

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py             — ニュース NLP スコアリング（ai_scores）
    - regime_detector.py      — 市場レジーム判定（ma200 + macro sentiment）
  - data/
    - __init__.py
    - jquants_client.py       — J-Quants API クライアント + DuckDB 保存
    - pipeline.py             — ETL パイプライン（run_daily_etl, 個別 ETL）
    - etl.py                  — ETLResult 再エクスポート
    - calendar_management.py  — カレンダー管理 / 営業日判定
    - news_collector.py       — RSS 取得・前処理・保存
    - quality.py              — データ品質チェック
    - stats.py                — 汎用統計ユーティリティ（zscore_normalize）
    - audit.py                — 監査ログスキーマ初期化 / init_audit_db
  - research/
    - __init__.py
    - factor_research.py      — momentum / volatility / value 等のファクター
    - feature_exploration.py  — forward returns / IC / summary / rank

開発・テスト
------------
- テストを実行するためのユニットテストはリポジトリに含めてください（本 README にはテストコマンドは含まれていません）。  
- 外部 API 呼び出し（OpenAI, J-Quants, ネットワーク）はモックしてユニットテストを行うことを推奨します。実装内でもテスト用に関数差し替えができるよう留意しています（例: _call_openai_api の patch）。

その他
-----
- 自動環境読み込みが便利ですが、CI / テストで環境影響を制御したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して手動で環境を読み込んでください。
- .env.example をプロジェクトルートに置き、そこから .env を作成する運用を推奨します（config._require は未設定時にエラーを投げます）。

フィードバック・貢献
------------------
バグ報告・機能要望は Issue へお願いします。Pull Request は歓迎します。README に書かれていない実装詳細や設計判断について質問があればお知らせください。