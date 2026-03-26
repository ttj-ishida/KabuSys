# Changelog

すべての重要な変更は Keep a Changelog の仕様に従って記載しています。  
このファイルはコードベースから推測して作成したリリースノートです。

現在のパッケージバージョン: 0.1.0

## [Unreleased]
（このスナップショットでは未リリースの変更は含まれていません）

## [0.1.0] - 2026-03-26
初回公開リリース（推定）。以下の機能群と実装を含みます。

### Added
- パッケージ基盤
  - kabusys パッケージを追加。トップレベルで data, strategy, execution, monitoring を public にエクスポート。
  - パッケージバージョンを __version__ = "0.1.0" として定義。

- 環境変数 / 設定管理 (kabusys.config)
  - .env ファイルまたは環境変数から設定を読み込む Settings クラスを実装。
  - 自動 .env ロード機能:
    - プロジェクトルートは __file__ を起点に .git または pyproject.toml を探索して決定（CWD 非依存）。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - OS 環境変数は protected として上書きされない。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 による自動ロード無効化対応（テスト用途）。
  - .env パーサーは export プレフィックス、シングル／ダブルクォート、バックスラッシュエスケープ、コメント処理（クォートあり/なしの差異）に対応。
  - 必須変数未設定時は _require() が ValueError を送出。必要な環境変数例:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
  - 各種ユーティリティプロパティ:
    - duckdb_path, sqlite_path, kabu_api_base_url, env, log_level, is_live / is_paper / is_dev（env 検証あり）

- AI モジュール (kabusys.ai)
  - news_nlp モジュール:
    - raw_news と news_symbols からニュースを集約し、OpenAI（gpt-4o-mini）の JSON mode を用いて銘柄別センチメントを算出。
    - バッチ処理（最大 20 銘柄/チャンク）、1銘柄あたり最大記事数および文字長でトリム。
    - リトライ（429/ネットワーク断/タイムアウト/5xx）を指数バックオフで実行。失敗はログ出力してスキップ（フェイルセーフ）。
    - レスポンスの厳密なバリデーション実装（JSON 抽出、results 配列、code/score の検証、数値の有限性チェック）。
    - スコアは ±1.0 にクリップ。取得済み銘柄のみ ai_scores テーブルへ（DELETE→INSERT の冪等処理）。
    - テスト容易性: API 呼び出しは _call_openai_api を介しており patch 可能。
    - 公開 API: score_news(conn, target_date, api_key=None) → 書き込んだ銘柄数を返す。
  - regime_detector モジュール:
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とニュースベースのマクロセンチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定。
    - マクロニュース抽出はニュースタイトルをキーワードフィルタ（日本・米国関連キーワード群）して最大 N 件を使用。
    - OpenAI（gpt-4o-mini）を用いたマクロセンチメント評価（JSON レスポンス期待）。API 失敗時は macro_sentiment=0.0 で継続。
    - レジームスコアはクリップ処理、閾値に基づきラベル決定。結果を market_regime テーブルへ冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）し、DB 書き込み失敗時はロールバック。
    - 公開 API: score_regime(conn, target_date, api_key=None) → 1（成功）を返す。

- Data (kabusys.data)
  - calendar_management:
    - JPX カレンダー（market_calendar）を扱うユーティリティと夜間更新ジョブ (calendar_update_job) を実装。
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days 等の営業日判定と探索ロジックを提供。
    - market_calendar が未取得のときは曜日ベース（土日非営業）でフォールバックする設計。DB 登録値を優先し、未登録日は曜日フォールバックで補完。
    - 最大探索日数制限 (_MAX_SEARCH_DAYS) により無限ループ防止。
    - calendar_update_job は J-Quants クライアントから差分取得し idempotent に保存、バックフィルと健全性チェックを実施。
  - pipeline / etl:
    - ETL パイプラインの骨格と ETLResult データクラスを実装（kabusys.data.pipeline.ETLResult を kabusys.data.etl で再エクスポート）。
    - ETLResult は取得数・保存数・品質問題（quality.QualityIssue）・エラー一覧等を保持し、has_errors / has_quality_errors / to_dict を提供。
    - 差分更新、backfill、品質チェック（quality モジュール）を組み込む設計方針を反映。
    - DuckDB を用いたテーブル存在確認・最大日付取得ユーティリティを実装。

- Research (kabusys.research)
  - factor_research:
    - Momentum（1M/3M/6M リターン、200 日 MA 乖離）、Volatility（20 日 ATR、相対 ATR、20 日平均売買代金等）、Value（PER、ROE）の計算関数を実装。
    - DuckDB 上の prices_daily / raw_financials のみ参照し、結果は (date, code) キーの辞書リストを返す。
    - データ不足時の None 扱い、ログ出力等の堅牢性を確保。
    - 公開 API: calc_momentum, calc_volatility, calc_value。
  - feature_exploration:
    - 将来リターン計算（calc_forward_returns）: target_date 基準の複数ホライズン（デフォルト [1,5,21]）のリターンを計算。入力検証あり（horizons は 1..252 の整数）。
    - IC（Information Coefficient）計算（calc_ic）: factor_records と forward_records を code で結合し、Spearman の ρ（ランク相関）を計算。有効レコード不足時は None を返す。
    - ランク変換ユーティリティ（rank）: 同順位は平均ランク、浮動小数誤差対策の丸め処理あり。
    - 統計サマリー（factor_summary）: count/mean/std/min/max/median を標準ライブラリのみで計算。
    - 公開 API を __init__ で再エクスポート（zscore_normalize は data.stats から）。

- エラー処理 / トランザクション保護
  - DB 書き込みは明示的な BEGIN/COMMIT/ROLLBACK を使用。書き込み失敗時は ROLLBACK を行い、ROLLBACK 自体の失敗は警告ログ出力。
  - OpenAI API 呼び出し周りはリトライ・ログ記録・フォールバック値（0.0）を採用し、サービス障害に対してフェイルセーフを確保。

### Changed
- （初回リリースのため無し）

### Fixed
- （初回リリースのため無し）

### Deprecated
- （初回リリースのため無し）

### Removed
- （初回リリースのため無し）

### Security
- OpenAI API キーや各種トークンは Settings を通じて環境変数から取得。コード内でのハードコーディングは無し。
- .env 自動ロードは明示的に無効化できる設定を提供（KABUSYS_DISABLE_AUTO_ENV_LOAD）。

### Notes / 実装上の制約・設計判断
- ルックアヘッドバイアス防止:
  - news_nlp と regime_detector は内部で datetime.today() / date.today() を参照しない。target_date を明示的に渡す設計。
  - DB クエリは date < target_date / date BETWEEN 範囲等で将来データの混入を防止。
- 外部依存:
  - DuckDB を主要なデータストアとして利用。
  - OpenAI（gpt-4o-mini）を外部 LLM として利用（JSON mode を使用）。
  - J-Quants クライアント（kabusys.data.jquants_client）を経由してマーケットデータ/カレンダーを取得。
- テスト容易性:
  - OpenAI 呼び出しは内部の _call_openai_api を patch して差し替え可能。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD によりテスト時の環境副作用を制御可能。

もし特定モジュールについてより詳細な変更点やリリースノート向けの文言を追加したい場合は、対象モジュール名を指定してください。