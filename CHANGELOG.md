# Changelog

すべての変更は Keep a Changelog の形式に準拠します。  
現在のリリース: 0.1.0 — 2026-03-28

## [0.1.0] - 2026-03-28

初回リリース。

### 追加 (Added)
- パッケージ基盤
  - パッケージメタ情報を追加（kabusys.__version__ = "0.1.0"）。パッケージの公開エントリとして data, strategy, execution, monitoring を __all__ に設定。
- 設定管理 (kabusys.config)
  - .env ファイルおよび環境変数から設定を自動読み込みする機能を実装（プロジェクトルート検出: .git / pyproject.toml を基準）。
  - 自動ロードの無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート（テスト時の切り替え用）。
  - .env パーサ実装（コメント、export プレフィックス、クォートとエスケープ処理、インラインコメント処理などに対応）。
  - Settings クラスを提供し、アプリで利用する主要設定をプロパティで取得可能に：
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH, SQLITE_PATH
    - KABUSYS_ENV（development / paper_trading / live 検証）
    - LOG_LEVEL（DEBUG/INFO/... 検証）
    - is_live / is_paper / is_dev ヘルパー
  - 必須環境変数未設定時は ValueError を送出する _require 関数を採用。
- AI モジュール (kabusys.ai)
  - ニュースセンチメント解析: news_nlp.score_news を実装
    - 指定ウィンドウ（前日 15:00 JST 〜 当日 08:30 JST）で raw_news / news_symbols から記事を集約し、OpenAI（gpt-4o-mini, JSON mode）へバッチ送信して銘柄ごとのスコアを ai_scores テーブルへ書き込む。
    - バッチサイズ、1銘柄あたりの最大記事数・文字数トリムなどトークン肥大化対策を実装。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフおよびリトライ処理を実装。
    - レスポンスの堅牢なバリデーション（JSON復元ロジック、results 配列、コードとスコア検証、数値クリッピング ±1.0）。
    - 一括書き込みは部分失敗に耐えるように、取得済みコードのみ DELETE → INSERT で置換（冪等性確保）。DuckDB の executemany の仕様に配慮。
    - テスト容易性のため _call_openai_api を patch 可能にしている。
  - 市場レジーム判定: regime_detector.score_regime を実装
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定。
    - マクロニュース抽出はニュース NLP の窓計算を再利用（calc_news_window）。
    - OpenAI 呼び出しは独立実装。API エラーやパース失敗は macro_sentiment=0.0 にフォールバック（フェイルセーフ）。
    - DuckDB へは BEGIN / DELETE / INSERT / COMMIT の冪等書き込み。エラー時は ROLLBACK を試行。
- データ処理 / ETL (kabusys.data)
  - ETL パイプライン用の ETLResult データクラスを実装（pipeline.ETLResult を kabusys.data.etl から再エクスポート）。
  - pipeline モジュールを実装（差分更新、バックフィル、品質チェックとの連携を想定）。DuckDB を想定したユーティリティ関数を提供（テーブル存在チェック、最大日付取得など）。
- カレンダー管理 (kabusys.data.calendar_management)
  - market_calendar を用いた営業日判定ロジックを実装:
    - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day
    - DB 登録が無ければ曜日ベース（土日除外）でフォールバック。DB と曜日判定の振る舞いを一貫させる設計。
  - calendar_update_job を実装し、J-Quants から差分取得して market_calendar を冪等的に保存。バックフィル、先読み、健全性チェックを実装。
  - DuckDB 日付値の取り扱いユーティリティ（_to_date など）を実装。
- 研究用モジュール (kabusys.research)
  - factor_research モジュールを実装:
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離の計算。
    - calc_volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率の計算。
    - calc_value: PER / ROE の計算（raw_financials から最新財務を参照）。
    - 関数はすべて DuckDB の prices_daily / raw_financials を参照し、外部 API にはアクセスしない（研究用安全設計）。
  - feature_exploration モジュールを実装:
    - calc_forward_returns: 指定ホライズン（デフォルト 1,5,21 営業日）に対する将来リターン計算（LEAD を使用）。
    - calc_ic: スピアマン順位相関による IC 計算（ランク付け、欠損・同値処理含む）。
    - rank: 同順位は平均ランクとするランク関数（丸めによる ties の扱いに配慮）。
    - factor_summary: count/mean/std/min/max/median の基本統計量を計算。
  - kabusys.research パッケージで主要関数を __all__ 再エクスポート。
- ロギング・設計方針
  - 日付の扱いにおいてルックアヘッドバイアスを防ぐため、datetime.today()/date.today() を直接参照しない実装方針を多くの処理で採用（関数引数として target_date を受け取る）。
  - 外部 API 呼び出し失敗時はフェイルセーフで継続する設計（例: LLM エラーでゼロスコア化、ETL の品質問題は収集して呼び出し元に委ねる）。
  - テストのための差し替えポイント（_call_openai_api 等）を用意。

### 変更 (Changed)
- （初回リリースのため該当なし）

### 修正 (Fixed)
- （初回リリースのため該当なし）

### 削除 (Removed)
- （初回リリースのため該当なし）

### 非推奨 (Deprecated)
- （初回リリースのため該当なし）

### セキュリティ (Security)
- OpenAI API キーの取扱いは環境変数（OPENAI_API_KEY）または明示的引数で提供する方式を採用。キーの自動読み込みに関しては KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能。

---

注:
- 各 API 呼び出し（J-Quants、OpenAI 等）は実行環境のネットワーク設定や API キーの準備が必要です。README や .env.example を参照して環境変数を設定してください。
- 本リリースは機能実装を中心とした初期バージョンです。個別の API クライアント（jquants_client 等）は別モジュールとして想定され、実行環境で提供されることを前提としています。