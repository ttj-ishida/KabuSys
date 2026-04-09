# CHANGELOG

すべての変更は Keep a Changelog の仕様に準拠しています。  
タグ付けされたリリースは semver に従います。

## [Unreleased]

### 注意事項
- 本リリースは初期実装に相当します。以下の既知の制約・ TODO を参照してください:
  - 一部関数内で price が欠損（0.0）だとエクスポージャーやサイズ計算が過少見積りされる旨の TODO コメントあり（将来的な価格フォールバックの導入予定）。
  - 単元株 (lot_size) は現状すべての銘柄で共通の値を仮定。将来的に銘柄別単元対応を想定。
  - DuckDB / SQLite のスキーマやテーブル前提があるため、実行前にデータベースに必要なテーブルを準備してください。
  - news_nlp / regime_detector の OpenAI 呼び出しは実環境で動作するために API キーが必要。テスト時は _call_openai_api をモック可能。

---

## [0.1.0] - 2026-04-09

初回公開リリース。主要機能の実装を含みます。

### Added
- 全体
  - パッケージメタ情報を追加（kabusys.__version__ = "0.1.0"）。パッケージの主要サブモジュールを __all__ で公開。

- 設定 / 環境変数管理 (src/kabusys/config.py)
  - .env ファイルおよび環境変数から設定を読み込む自動ローダを実装（プロジェクトルートを .git または pyproject.toml から探索）。
  - .env のパース機能を実装（コメント、export プレフィックス、シングル/ダブルクォート、エスケープ対応、インラインコメント処理）。
  - 自動読み込みは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - Settings クラスを実装し、以下の環境変数をプロパティで提供（必須/デフォルト/検証を含む）:
    - JQUANTS_REFRESH_TOKEN（必須、未設定時は ValueError）
    - KABU_API_PASSWORD（必須、未設定時は ValueError）
    - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
    - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID（デフォルト: 空文字列）
    - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
    - SQLITE_PATH（デフォルト: data/monitoring.db）
    - PAPER_FILL_MODE（検証済み。有効値: instant|partial|never|reject、デフォルト: instant）
    - PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）
    - PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START（監視用）
    - CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT（閾値、float）
    - KABUSYS_ENV（有効値: development|paper_trading|live、デフォルト: development）
    - LOG_LEVEL（有効値: DEBUG|INFO|WARNING|ERROR|CRITICAL、デフォルト: INFO）
  - 環境変数に関する入力検証とエラーメッセージを実装。

- ポートフォリオ構築 (src/kabusys/portfolio/)
  - portfolio_builder:
    - select_candidates: BUY シグナルを score 降順、signal_rank によるタイブレークでソートし上位 N を選択。
    - calc_equal_weights: 等金額配分の重みを計算。
    - calc_score_weights: スコア加重配分を計算。全銘柄スコアが 0 の場合は等金額配分にフォールバックし WARNING を出力。
  - risk_adjustment:
    - apply_sector_cap: セクター集中上限を評価し、上限を超えるセクターの新規候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: market regime（'bull'/'neutral'/'bear'）に基づき投下資金乗数を返す（未知レジームは警告後 1.0 でフォールバック）。
  - position_sizing:
    - calc_position_sizes: 株数決定ロジックを実装。
      - allocation_method: "risk_based" | "equal" | "score" をサポート。
      - risk_based: 許容リスク率(risk_pct)、損切り率(stop_loss_pct) に基づいてサイズ算出。
      - equal/score: 重み・利用可能資金・max_utilization 等を考慮。
      - 単元丸め（lot_size）と per-stock 上限、aggregate cap（available_cash）によるスケーリングを実装。
      - cost_buffer により手数料/スリッページを保守的に見積もり、スケールダウンと端数配分（lot 単位）を行う。

- リサーチ / ファクター計算 (src/kabusys/research/)
  - factor_research:
    - calc_momentum: mom_1m/mom_3m/mom_6m と 200日移動平均乖離 (ma200_dev) を計算。必要データ不足時は None を返す。
    - calc_volatility: 20日 ATR（atr_20）、相対ATR(atr_pct)、20日平均売買代金(avg_turnover)、出来高変化率(volume_ratio) を計算。
    - calc_value: raw_financials と prices_daily を組み合わせて PER（EPS に基づく）と ROE を計算。財務データは target_date 以前の最新を使用。
  - feature_exploration:
    - calc_forward_returns: 任意ホライズン（デフォルト [1,5,21]）に対する将来リターンをまとめて取得。horizons の検証を実装。
    - calc_ic: スピアマンのランク相関（IC）を計算（同順位は平均ランク処理）。有効レコード < 3 の場合は None。
    - rank: 同順位を平均ランクで扱うランク変換ユーティリティ（浮動小数点丸めで ties 検出誤差低減）。
    - factor_summary: count/mean/std/min/max/median の統計要約を実装。
  - research パッケージは zscore_normalize（kabusys.data.stats から）を re-export。

- AI 関連 (src/kabusys/ai/)
  - news_nlp:
    - calc_news_window: target_date に対するニュース収集ウィンドウ（JST→UTC 変換）を提供。
    - score_news: raw_news と news_symbols から銘柄別記事を集約し、OpenAI（gpt-4o-mini）の JSON Mode を用いて銘柄ごとのセンチメント ai_score を ai_scores テーブルへ保存する処理を実装。
      - バッチサイズ、記事数・文字数上限、JSON バリデーション、スコアクリップ（±1.0）、API リトライ（429/ネットワーク/5xx に対する指数バックオフ）を実装。
      - API キーは api_key 引数または環境変数 OPENAI_API_KEY から解決。未設定時は ValueError を送出。
      - DuckDB への書き込みは冪等性のため DELETE → INSERT の手順で実行。部分失敗時に既存スコアを消さない設計。
      - テスト容易性のため _call_openai_api をモック可能。
  - regime_detector:
    - 市場レジーム判定ロジックを実装（ETF 1321 の ma200 乖離 + マクロニュース LLM センチメントを加重合成）。
    - マクロキーワードに基づく raw_news の抽出、LLM 呼び出し（JSON 解析、リトライ、失敗時は macro_sentiment=0.0 にフォールバック）および最終スコアの DB への冪等書き込みを実装。
    - API キーは api_key 引数または OPENAI_API_KEY 環境変数から解決。未設定時は ValueError。
    - 内部で calc_news_window を利用。

- モニタリング永続化 (src/kabusys/monitoring/monitoring_db.py)
  - init_monitoring_db: SQLite を用いた監視ログ永続化のための初期スキーマ作成（冪等）を実装。
    - system_status, trade_logs, positions, risk_logs 等（インデックス含む）を作成。
    - ビジネスロジックを持たない薄い永続化層として実装。

- パッケージエクスポート
  - portfolio, research, ai パッケージの主要関数を __all__ で公開（外部からの利用を想定）。

### Changed
- （新規リリースのため該当なし）

### Fixed
- （新規リリースのため該当なし）

### Security
- OpenAI API キーや各種シークレットは環境変数で管理する設計。自動 .env ロードは任意で無効化可能（KABUSYS_DISABLE_AUTO_ENV_LOAD）。

### Notes / Breaking changes
- JQUANTS_REFRESH_TOKEN と KABU_API_PASSWORD は必須環境変数です。settings.jquants_refresh_token / settings.kabu_api_password を参照すると未設定時に ValueError を送出します。
- DuckDB / SQLite の必要テーブル（prices_daily / raw_financials / raw_news / news_symbols / ai_scores / market_regime 等）は事前に用意してください。
- AI モジュールは外部 API（OpenAI）に依存します。利用時は API キーの設定とネットワーク接続が必要です。
- 時刻の扱いについてはルックアヘッドバイアス防止のため現在時刻 (date.today / datetime.today) を参照しない設計になっています。すべて target_date に基づく処理です。

---
もしこの CHANGELOG に追加してほしい項目（特定コミットの記載、より詳細な既知の問題リスト、リリースノートの英語版など）があれば指示ください。