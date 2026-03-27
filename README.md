# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリです。  
DuckDB をデータ層に、J-Quants API で市場データを取得し、OpenAI（gpt-4o-mini）でニュースの NLP 評価を行う機能などを提供します。

主な用途例：
- 日次 ETL（株価・財務・カレンダー取得）と品質チェック
- RSS ニュース収集と銘柄ごとの LLM ベースセンチメントスコア算出
- 市場レジーム判定（ETF とマクロセンチメントを合成）
- 研究用ファクター計算・特徴量解析ユーティリティ
- 発注・約定の監査ログ用スキーマ初期化

----------------------------------------------------------------------
目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方（主要 API の例）
- ディレクトリ構成
- 環境変数一覧 / .env の自動読み込み
----------------------------------------------------------------------

## プロジェクト概要
KabuSys は日本株の自動売買システムやデータプラットフォーム構築を支援する Python ライブラリ群です。  
主要な機能はデータ ETL、品質チェック、ニュース NLP、レジーム判定、研究（ファクター計算）および監査ログスキーマ初期化など。DuckDB を中心に設計されており、Look-ahead bias を避ける設計や API 呼び出しの堅牢なリトライ・レート制御を備えています。

## 機能一覧
- データ取得 / ETL
  - J-Quants から株価（OHLCV）、財務データ、JPX カレンダーを差分取得（ページネーション対応）
  - DuckDB への冪等保存（ON CONFLICT DO UPDATE）
  - run_daily_etl による日次パイプライン（カレンダー→株価→財務→品質チェック）
- データ品質チェック
  - 欠損データ検出、スパイク（急騰/急落）検出、重複チェック、日付整合性チェック
- ニュース収集 / 前処理
  - RSS から記事収集（SSRF 対策・受信サイズ制限・URL 正規化等）
  - raw_news / news_symbols への保存処理（冪等）
- ニュース NLP（OpenAI）
  - 銘柄ごとのセンチメントスコア算出（gpt-4o-mini, JSON mode）
  - バッチ処理・リトライ・レスポンス検証を実装（score_news）
- 市場レジーム判定
  - ETF (1321) の 200 日 MA 乖離（重み 70%）とマクロニュースセンチメント（重み 30%）を合成して日次レジーム判定（bull/neutral/bear）
  - OpenAI 呼び出しと DB 書き込みを含む（score_regime）
- 研究支援
  - モメンタム / バリュー / ボラティリティ等のファクター計算
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー、Z スコア正規化
- 監査ログ（audit）
  - signal_events / order_requests / executions 等の監査用テーブル DDL と初期化ユーティリティ（init_audit_schema / init_audit_db）
- 設定管理
  - .env / .env.local の自動ロード（プロジェクトルート判定）
  - 必須設定の検証を提供する Settings クラス

## セットアップ手順（ローカル開発向け）
推奨 Python バージョン: 3.10+

1. リポジトリをクローン
   - git clone <repo-url>

2. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - ※requirements.txt がある場合はそれを利用してください。ない場合、最低限必要なパッケージ例:
     - pip install duckdb openai defusedxml

   - 開発時にパッケージとしてインストールするなら:
     - pip install -e .

4. 環境変数を用意
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env` として必要な環境変数を配置します。
   - 自動ロードは既定で有効（詳細は後述）。一時的に無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

5. DuckDB ファイルやディレクトリの作成（必要に応じて）
   - デフォルトの DuckDB パスは data/kabusys.duckdb（settings.duckdb_path）
   - 例: mkdir -p data

## 環境変数（主要）
このライブラリで期待される代表的な環境変数:

- JQUANTS_REFRESH_TOKEN (必須)  
  J-Quants API のリフレッシュトークン（get_id_token に使用）

- OPENAI_API_KEY (必須 for LLM 呼び出し)  
  OpenAI API キー（score_news / score_regime で使用可能。関数呼び出し時に api_key を渡すことも可）

- KABU_API_PASSWORD  
  kabuステーション API 用パスワード

- KABU_API_BASE_URL (任意)  
  デフォルト: http://localhost:18080/kabusapi

- SLACK_BOT_TOKEN, SLACK_CHANNEL_ID  
  Slack 通知用トークン / チャンネル ID

- DUCKDB_PATH (任意)  
  デフォルト: data/kabusys.duckdb

- SQLITE_PATH (任意)  
  デフォルト: data/monitoring.db

- KABUSYS_ENV (任意)  
  有効値: development / paper_trading / live（デフォルト development）

- LOG_LEVEL (任意)  
  有効値: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト INFO）

設定は .env/.env.local から自動ロードされます（OS 環境変数が優先、.env.local は .env を上書き）。自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

## 使い方（主要 API の例）
以下はライブラリの主要機能を呼び出す最小例です。実行前に必要な環境変数（JQUANTS_REFRESH_TOKEN、OPENAI_API_KEY など）を設定してください。

- DuckDB 接続準備（例）
  - Python REPL / スクリプト内で:
    - import duckdb
    - conn = duckdb.connect(str(<path_to_duckdb>))  # 例: "data/kabusys.duckdb"

- 日次 ETL を実行する
  - from datetime import date
    from kabusys.data.pipeline import run_daily_etl
    import duckdb
    conn = duckdb.connect("data/kabusys.duckdb")
    res = run_daily_etl(conn, target_date=date(2026, 3, 20))
    print(res.to_dict())

- ニュースのスコア算出（score_news）
  - from datetime import date
    import duckdb
    from kabusys.ai.news_nlp import score_news
    conn = duckdb.connect("data/kabusys.duckdb")
    n_written = score_news(conn, date(2026, 3, 20))  # OpenAI API キーは環境変数か api_key 引数で指定
    print("written:", n_written)

- 市場レジーム判定（score_regime）
  - from datetime import date
    import duckdb
    from kabusys.ai.regime_detector import score_regime
    conn = duckdb.connect("data/kabusys.duckdb")
    score_regime(conn, date(2026, 3, 20))  # OpenAI API キーは環境変数か api_key 引数で指定

- 監査 DB の初期化（audit スキーマ）
  - from kabusys.data.audit import init_audit_db
    conn = init_audit_db("data/audit.duckdb")
    # conn を使って監査テーブルへアクセス可能

- ファクター計算（research）
  - from datetime import date
    import duckdb
    from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
    conn = duckdb.connect("data/kabusys.duckdb")
    momentum = calc_momentum(conn, date(2026, 3, 20))

注意点:
- OpenAI API 呼び出しや外部 API 呼び出しはネットワーク依存・レート制限に注意してください。関数内でリトライ・バックオフが実装されていますが、クォータ管理は利用者側でも配慮してください。
- 各関数は Look-ahead bias を避けるため、内部で date.today() を参照しない設計になっています。必ず target_date を指定して過去方向のデータのみを参照するようにしてください。

## ディレクトリ構成（主要ファイル）
リポジトリのトップに `src/kabusys` パッケージがあり、主なサブモジュールは次の通りです。

- kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py            — ニュース NLP（score_news）
    - regime_detector.py     — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント + DuckDB 保存関数
    - pipeline.py            — ETL パイプライン（run_daily_etl 等）
    - etl.py                 — ETL 結果クラス再エクスポート
    - calendar_management.py — マーケットカレンダー処理
    - news_collector.py      — RSS ニュース収集、前処理
    - quality.py             — データ品質チェック
    - stats.py               — 統計ユーティリティ（zscore_normalize 等）
    - audit.py               — 監査ログスキーマ初期化
  - research/
    - __init__.py
    - factor_research.py     — モメンタム / バリュー / ボラティリティ計算
    - feature_exploration.py — 将来リターン / IC / 統計サマリー 等
  - (他: strategy / execution / monitoring のプレースホルダモジュールが __all__ に含まれます)

各モジュールは docstring に機能説明や設計方針、想定される DB テーブル（raw_prices, raw_financials, raw_news, ai_scores, market_regime, market_calendar 等）を明示しています。

## 注意事項 / 運用上のヒント
- .env 自動読み込み: プロジェクトルート（.git または pyproject.toml のあるディレクトリ）から .env / .env.local を読み込みます。OS 環境変数が優先されます。テスト時など自動読み込みを止めたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB に対する executemany の挙動（空リストの渡し方）等、実行環境の DuckDB バージョンに依存する実装上の注意があります（コード内に回避ロジックあり）。
- LLM 呼び出しは JSON モードを想定していますが、外部サービスの応答が必ずしも正確ではないためレスポンス検証とフェイルセーフ（0.0 フォールバック）を実装しています。
- API キーやトークンは秘匿情報です。`.env` に保存する場合はリポジトリにコミットしないよう .gitignore を設定してください。

---

README の内容はコードベースの docstring をもとに作成しています。必要であれば、実際の運用手順（systemd / cron / Airflow などでの ETL スケジューリング例）やテーブル DDL（schema 初期化スクリプト）を追加で記載できます。追加したい項目があれば教えてください。