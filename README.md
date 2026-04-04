# KabuSys

KabuSys は日本株向けの自動売買・データプラットフォーム向けライブラリです。  
ETL（J-Quants からの株価・財務・カレンダー取得）、ニュース収集・NLP スコアリング、研究用ファクター計算、監査ログ（シグナル→発注→約定トレーサビリティ）、および市場レジーム判定などのユーティリティを提供します。

主な設計方針：
- ルックアヘッドバイアスを避けるため、内部で現在日時を直接参照する処理を最小化しています（関数に target_date を渡す方式）。
- DuckDB を主要な永続ストアとして利用します（オンディスク / :memory: の両方に対応）。
- J-Quants / OpenAI など外部 API 呼び出しには堅牢なリトライ・レート制御を組み込んでいます。
- ETL / 品質チェックは失敗しても他の処理に影響を与えない設計（全件収集型のエラーハンドリング）。

---

## 機能一覧

- データ取得・ETL
  - J-Quants からの日足（OHLCV）、財務情報、JPX カレンダー取得（ページネーション・リトライ・レート制御）
  - 差分取得・バックフィル・品質チェック（欠損・スパイク・重複・日付整合性）
  - ETL の総合エントリ（run_daily_etl）
- ニュース収集・前処理
  - RSS 取得、URL 正規化、トラッキングパラメータ除去、SSRF 対策、記事保存（raw_news）
- ニュースNLP（OpenAI）
  - 銘柄別ニュースをまとめて LLM に投げてセンチメント/ai_score を ai_scores に保存（score_news）
  - マクロニュースを用いた市場レジーム判定（score_regime）
- リサーチ / ファクター計算
  - Momentum / Value / Volatility 等のファクター計算（calc_momentum, calc_value, calc_volatility）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー（feature_exploration）
  - Zスコア正規化ユーティリティ（data.stats.zscore_normalize）
- 監査ログ（トレーサビリティ）
  - signal_events / order_requests / executions などの監査テーブル定義と初期化（init_audit_schema / init_audit_db）
- カレンダー管理
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / calendar_update_job

---

## セットアップ手順

前提
- Python 3.10+（型ヒントに | 記法を使用）
- Git がインストールされていること（プロジェクトルート自動検出に使用）

1. リポジトリをクローン（パッケージルートが .git または pyproject.toml を持つ構成を想定）
   - 例: git clone <repo-url>

2. 仮想環境の作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate (Linux/macOS) または .venv\Scripts\activate (Windows)

3. 依存パッケージのインストール
   - pip install -U pip
   - 必須パッケージ例:
     - duckdb
     - openai
     - defusedxml
   - 開発環境から editable install:
     - pip install -e .  # setup/pyproject を用意している場合

   （プロジェクトに requirements.txt や pyproject.toml がある場合はそちらに従ってください）

4. 環境変数設定
   - ルートに .env / .env.local を置けば自動で読み込まれます（自動ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。
   - 主要な環境変数（例）:
     - JQUANTS_REFRESH_TOKEN=<your_jquants_refresh_token>  -- 必須（ETL/jquants_client）
     - OPENAI_API_KEY=<your_openai_api_key>                -- 必須（AI モジュールを使う場合）
     - KABU_API_PASSWORD=<kabu_station_password>          -- 必須（発注系を使う場合）
     - KABUSYS_ENV=development|paper_trading|live         -- 環境（デフォルト development）
     - DUCKDB_PATH=data/kabusys.duckdb                     -- DuckDB ファイルパス（Path で解決）
     - SQLITE_PATH=data/monitoring.db                      -- 監視用 SQLite パス
     - その他: LOG_LEVEL, PID_FILE_PATH, KILL_FLAG_PATH など（config.Settings 参照）

   - .env のフォーマットはシンプルな KEY=VALUE 形式に対応。export KEY=val も許容します。

5. データディレクトリ作成（必要に応じて）
   - mkdir -p data

---

## 使い方（主要な例）

下記は代表的な操作例です。各関数の詳細はモジュールの docstring を参照してください。

- DuckDB 接続準備（ディスク DB を使用する例）
  - from kabusys.config import settings
    import duckdb
    conn = duckdb.connect(str(settings.duckdb_path))

- 日次 ETL を実行する
  - from kabusys.data.pipeline import run_daily_etl
    from datetime import date
    res = run_daily_etl(conn, target_date=date(2026, 3, 20))
    print(res.to_dict())

- ニュースセンチメントのスコアを生成（OpenAI API 必須）
  - from kabusys.ai.news_nlp import score_news
    from datetime import date
    count = score_news(conn, target_date=date(2026, 3, 20))
    print(f"scored {count} codes")

  - api_key を引数で渡すことも可能:
    score_news(conn, date(2026,3,20), api_key="sk-...")

- 市場レジームスコアを計算して保存（OpenAI API 必須）
  - from kabusys.ai.regime_detector import score_regime
    from datetime import date
    score_regime(conn, target_date=date(2026, 3, 20))

- ファクター計算・研究用ユーティリティ
  - from kabusys.research import calc_momentum, calc_value, calc_volatility, calc_forward_returns, calc_ic
    mom = calc_momentum(conn, target_date=date(2026,3,20))
    vol = calc_volatility(conn, target_date=date(2026,3,20))
    val = calc_value(conn, target_date=date(2026,3,20))
    fwd = calc_forward_returns(conn, target_date=date(2026,3,20))
    ic = calc_ic(mom, fwd, "mom_1m", "fwd_1d")

- 監査ログ（監査 DB）の初期化・接続
  - from kabusys.data.audit import init_audit_db
    audit_conn = init_audit_db("data/audit.duckdb")  # :memory: も可

- カレンダー更新ジョブを実行
  - from kabusys.data.calendar_management import calendar_update_job
    saved = calendar_update_job(conn)
    print("saved calendar records:", saved)

注意:
- AI 関連（score_news, score_regime）は OpenAI API キーが必要です。api_key 引数を渡すか環境変数 OPENAI_API_KEY を設定してください。
- J-Quants へのアクセスは JQUANTS_REFRESH_TOKEN が必要です（settings で参照されます）。
- ETL / 保存関数は DuckDB スキーマを前提とします。初期スキーマ作成が必要な場合は別途スキーマ用関数や SQL を用意してください（プロジェクトに schema 初期化コードがあればそれを利用）。

---

## 環境変数（主なもの）

- JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン（必須: データ ETL）。
- OPENAI_API_KEY — OpenAI API キー（AI モジュールを使う場合必須）。
- KABU_API_PASSWORD — kabu ステーション API パスワード（発注機能を使う場合）。
- KABUSYS_ENV — environment: development / paper_trading / live（デフォルト development）。
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）。
- DUCKDB_PATH — デフォルトの DuckDB ファイルパス（settings.duckdb_path）。
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 を設定すると自動で .env を読み込まない。

（上記は一部抜粋。config.Settings のプロパティを参照してください）

---

## ディレクトリ構成（主要ファイル）

プロジェクトは src レイアウトを想定しています。主要モジュール:

- src/kabusys/
  - __init__.py
  - config.py                      -- 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py                   -- ニュース NLP スコアリング（score_news）
    - regime_detector.py            -- マクロ + MA200 合成による市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py             -- J-Quants API クライアント + DuckDB 保存関数
    - pipeline.py                   -- ETL パイプラインおよび run_daily_etl
    - etl.py                        -- ETL 結果型の公開（ETLResult）
    - news_collector.py             -- RSS 収集・前処理
    - calendar_management.py        -- JPX カレンダー管理 / calendar_update_job
    - quality.py                    -- データ品質チェック
    - stats.py                      -- 共通統計ユーティリティ（zscore_normalize）
    - audit.py                      -- 監査ログスキーマ定義・初期化
  - research/
    - __init__.py
    - factor_research.py            -- Momentum/Value/Volatility 等の計算
    - feature_exploration.py        -- forward returns / IC / summary / rank
  - ai/, data/, research/ はそれぞれの公開 API を持ちます。

詳細は各モジュールの docstring を参照してください。

---

## よくあるトラブルシューティング

- ValueError: OpenAI API キーが未設定です
  - OPENAI_API_KEY を .env または環境変数に設定するか、各 AI 関数に api_key を渡してください。

- J-Quants 認証失敗 / id_token 関連エラー
  - JQUANTS_REFRESH_TOKEN が正しく設定されているか、期限切れでないか確認してください。

- DuckDB への接続 / スキーマがない
  - 使用するテーブル（raw_prices / raw_financials / market_calendar / raw_news / news_symbols / ai_scores / market_regime / ...）が事前に作成されているか確認してください。プロジェクトにスキーマ初期化手順があればそれを実行してください。

- .env が読み込まれない
  - プロジェクトルートの検出は .git または pyproject.toml を基準に行います。自動ロードを無効化している場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を解除してください。

---

## 開発にあたってのメモ

- テスト時には自動的に外部 API を呼ばないようモックを利用することを想定しており、モジュール内で外部呼び出しを抽象化（関数差し替え）できるよう実装しています（例: kabusys.ai.news_nlp._call_openai_api を unittest.mock.patch で置換）。
- DuckDB の executemany に空リストを渡すとエラーになるバージョン対策が各所に実装されています。
- タイムスタンプは基本的に UTC を使用する設計です（監査テーブル初期化時に SET TimeZone='UTC' を実行します）。

---

README はここまでです。特定の利用例（ETL スケジューリング、発注モジュールとの統合、運用時の監視設定等）について詳しい手順やテンプレートが必要であれば、用途に合わせた追加ドキュメントを作成します。必要な箇所を教えてください。