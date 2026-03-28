# Changelog

すべての注目すべき変更をここに記録します。  
このファイルは Keep a Changelog のフォーマットに従います。  

格式: https://keepachangelog.com/ja/1.0.0/

## [0.1.0] - 2026-03-28

初回リリース — 日本株自動売買システム (KabuSys) のコアライブラリを公開します。  
主に以下の機能群を実装しています: 環境設定管理、データ ETL/カレンダー管理、研究用ファクター算出、AI ベースのニュースセンチメント/市場レジーム判定。

### 追加 (Added)
- パッケージ初期化
  - src/kabusys/__init__.py
    - パッケージバージョン __version__ = "0.1.0" を設定。
    - 公開サブパッケージ: data, strategy, execution, monitoring を __all__ で定義。

- 環境変数・設定管理
  - src/kabusys/config.py
    - .env / .env.local の自動ロード機構を実装（プロジェクトルートは .git または pyproject.toml を探索して決定）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート。
    - .env のパースは export KEY=val、シングル/ダブルクォート、エスケープ、行内コメント等に対応。
    - 上書き（override）と protected（OS 環境変数保護）を考慮したロード実装。
    - Settings クラスを提供（settings インスタンスを公開）。
      - J-Quants / kabu ステーション / Slack / データベースパス等のプロパティ（必須キーは未設定時に ValueError）。
      - KABUSYS_ENV（development / paper_trading / live）の検証。
      - LOG_LEVEL の検証、is_live/is_paper/is_dev のユーティリティプロパティ。

- AI: ニュース NLP（銘柄別センチメント）
  - src/kabusys/ai/news_nlp.py
    - score_news(conn, target_date, api_key=None)
      - raw_news と news_symbols を集約し、銘柄ごとに OpenAI (gpt-4o-mini) へバッチ送信してセンチメントを ai_scores テーブルへ書き込む。
      - タイムウィンドウは JST 基準で「前日 15:00 ～ 当日 08:30」（UTC に変換して DB 比較）。
      - バッチサイズ、トリム文字数、最大記事数などを制御する定数を実装。
      - JSON Mode を用いたレスポンス検証、スコアのクリップ（±1.0）。
      - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフのリトライ。
      - 部分成功に備え、ai_scores は該当コードのみ DELETE → INSERT（冪等性・既存スコア保護）。
      - テスト用に _call_openai_api を patch して差し替え可能。

  - src/kabusys/ai/__init__.py
    - score_news を公開。

- AI: 市場レジーム判定
  - src/kabusys/ai/regime_detector.py
    - score_regime(conn, target_date, api_key=None)
      - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）と、マクロニュースの LLM センチメント（重み 30%）を合成してレジーム（bull / neutral / bear）を判定。
      - マクロ記事はニュースタイトルをマクロキーワードでフィルタリングして取得、最大記事数を制限。
      - LLM 呼び出しは JSON レスポンスを期待、API 失敗時は macro_sentiment = 0.0 にフォールバック（フェイルセーフ）。
      - ma200_ratio はデータ不足時に 1.0（中立）にフォールバック。
      - market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）を行う。
      - テスト用に _call_openai_api を patch して差し替え可能。

  - 設計方針（両 AI モジュール共通）
    - OpenAI クライアント、モデルは gpt-4o-mini を採用。JSON Mode を用いて厳格な構造を期待。
    - API 呼び出し・レスポンスパースの失敗は致命的エラーとせずフォールバックまたはスキップで継続する（ロバストネス重視）。
    - LLM 呼び出しの内部実装はモジュール間で共有せず、各モジュールにテスト差し替えポイントを用意。

- リサーチ用ファクター計算
  - src/kabusys/research/factor_research.py
    - calc_momentum(conn, target_date)
      - 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）を計算。データ不足時は None。
    - calc_volatility(conn, target_date)
      - 20 日 ATR（atr_20）、相対 ATR（atr_pct）、20 日平均売買代金、出来高比率などを計算。データ不足時は None。
    - calc_value(conn, target_date)
      - raw_financials から最新財務データを取得し PER（EPS 基準）・ROE を算出。
    - DuckDB を用いた SQL ベース計算で、外部 API にはアクセスしない。結果は (date, code) 単位の辞書リストで返却。
  - src/kabusys/research/feature_exploration.py
    - calc_forward_returns(conn, target_date, horizons=None)
      - 指定ホライズン（デフォルト [1,5,21]）の将来リターンを計算。horizons の妥当性検証あり。
    - calc_ic(factor_records, forward_records, factor_col, return_col)
      - スピアマンのランク相関（IC）を計算。サンプル不足時は None。
    - rank(values)
      - 同順位は平均ランクとするランク付け実装（丸めで ties 回避）。
    - factor_summary(records, columns)
      - count/mean/std/min/max/median を計算する統計サマリー。
  - src/kabusys/research/__init__.py
    - 主要関数と zscore_normalize をエクスポート。

- データ管理 / カレンダー
  - src/kabusys/data/calendar_management.py
    - JPX 市場カレンダー管理（market_calendar）。
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days 等の営業日ユーティリティを実装。
    - DB にカレンダーが不整備な場合は曜日ベース（平日）でフォールバック。
    - calendar_update_job(conn, lookahead_days) による J-Quants からの差分取得・保存の夜間バッチ処理を実装。バックフィル、健全性チェックあり。
    - max search 範囲を設け無限ループ防止。

- データ ETL とパイプライン
  - src/kabusys/data/pipeline.py
    - ETL の骨格、差分取得・保存・品質チェックフローの実装方針。
    - ETLResult dataclass を定義（target_date, fetched/saved カウント、quality_issues, errors 等）。
    - 内部ユーティリティ: テーブル存在チェック、最大日付取得、取扱い方針（バックフィル、初回ロード開始日等）。
  - src/kabusys/data/etl.py
    - pipeline.ETLResult を再エクスポート。

- サンプル/内部ユーティリティ
  - DuckDB を前提とした SQL 実装が多数（prices_daily, raw_news, ai_scores, market_regime, raw_financials 等）。
  - 各 DB 書き込みは冪等を意識（DELETE→INSERT、ON CONFLICT 想定の保存関数呼び出し等）。
  - ログ出力（logger）を適切に配置し、失敗時は例外の伝搬または WARN/INFO での継続を選択。

### 変更 (Changed)
- 初回リリースのため該当なし。

### 削除 (Removed)
- 初回リリースのため該当なし。

### 修正 (Fixed)
- 初回リリースのため該当なし。

### セキュリティ (Security)
- 初回リリースのため該当なし。

---

注記 / 実装上の重要ポイント
- ルックアヘッドバイアス防止:
  - AI、リサーチ、ニュース集約等のモジュールは内部で datetime.today() / date.today() を参照せず、必ず呼び出し側から target_date を受け取る設計です。
- フェイルセーフ設計:
  - LLM 呼び出し失敗・レスポンスパース失敗はスコアに中立値を代入するか該当コードのみスキップして処理を継続します（全体処理停止を回避）。
- テストフレンドリー:
  - OpenAI 呼び出しはモジュールごとに _call_openai_api を用意し、unit test で patch 可能。
- 環境変数:
  - 必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID（Settings のプロパティを参照）。
  - DB パス等はデフォルト値あり（DUCKDB_PATH= data/kabusys.duckdb, SQLITE_PATH= data/monitoring.db）。
  - 自動 .env ロードの挙動や上書きポリシーは config.py のコメントを参照。

公開 API（主な関数／クラス）
- config.settings (Settings)
- ai.news_nlp.score_news(conn, target_date, api_key=None)
- ai.regime_detector.score_regime(conn, target_date, api_key=None)
- research.calc_momentum(conn, target_date)
- research.calc_volatility(conn, target_date)
- research.calc_value(conn, target_date)
- research.calc_forward_returns(conn, target_date, horizons=None)
- research.calc_ic(...)
- research.factor_summary(...)
- data.calendar_management.is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day / calendar_update_job
- data.pipeline.ETLResult
- data.etl.ETLResult (再エクスポート)

今後の予定（例）
- strategy / execution / monitoring の実装拡張（現状はパッケージエントリを用意）。
- 追加の品質チェックルール、より細かいメトリクスの収集。
- OpenAI モデルやプロンプトの改良、スコアのキャリブレーション。

ご要望やバグ報告、改善提案があれば Issue を作成してください。