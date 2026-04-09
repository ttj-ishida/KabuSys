# CHANGELOG

すべての変更は Keep a Changelog の慣例に準拠して記載しています。  
このプロジェクトはセマンティックバージョニングを採用しています。

## [0.1.0] - 2026-04-09

### Added
- 初回リリース。
- パッケージの基本情報を追加
  - パッケージバージョン: `kabusys.__version__ = "0.1.0"`
  - public モジュール群を __all__ でエクスポート（data, strategy, execution, monitoring 等）。
- 環境変数・設定管理 (`src/kabusys/config.py`)
  - .env ファイルまたは環境変数から設定を自動読み込みする機能を実装。
  - プロジェクトルートの自動検出（.git または pyproject.toml を起点）を実装し、CWD に依存しない読み込みを実現。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で自動ロードを無効化可能。
  - .env パーサを実装:
    - コメント行 / 空行を無視。
    - `export KEY=val` 形式対応。
    - シングル/ダブルクォート内のバックスラッシュエスケープ対応。
    - クォートなし値のインラインコメント処理（直前がスペース/タブの場合に # をコメントと扱う）。
  - Settings クラスを提供し、主要設定項目（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、KABU_API_BASE_URL、LINE 関連、DB パス、paper_trading 関連、監視閾値、環境/ログレベル等）をプロパティとして取得可能。
  - バリデーション付き設定:
    - PAPER_FILL_MODE（instant/partial/never/reject）検証。
    - KABUSYS_ENV（development/paper_trading/live）検証。
    - LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL）検証。
- ポートフォリオ構築（純粋関数群）
  - `kabusys.portfolio.portfolio_builder`
    - select_candidates: スコア降順、同点は signal_rank 昇順で候補選定。
    - calc_equal_weights: 等金額配分を計算。
    - calc_score_weights: スコアに応じた配分（全銘柄スコアが 0 の場合は等配分にフォールバックし WARNING を出力）。
  - `kabusys.portfolio.risk_adjustment`
    - apply_sector_cap: 既存ポジションのセクター比率がしきい値を超える場合にそのセクターの新規候補を除外（"unknown" セクターは制限対象外）。売却予定銘柄をエクスポージャー計算から除外可。
    - calc_regime_multiplier: market regime（bull/neutral/bear）に基づく投下資金乗数を提供（未知レジームはフォールバックで 1.0、警告ログ）。
  - `kabusys.portfolio.position_sizing`
    - calc_position_sizes: 各銘柄の発注株数を計算（allocation_method: "risk_based"/"equal"/"score" をサポート）。
    - risk_based: 損切り率・リスク許容率から算出。
    - equal/score: weight に基づく配分。lot_size による丸め、単銘柄上限・総投下上限（aggregate cap）、cost_buffer を用いた保守的なコスト見積りとスケーリング、端数の分配ロジックを実装。
    - price 欠損時のスキップやログ出力を考慮。
- リサーチ / ファクター計算（DuckDB ベース、外部 API 不使用）
  - `kabusys.research.factor_research`
    - calc_momentum: 1M/3M/6M リターン、200 日移動平均乖離を計算。データ不足時は None。
    - calc_volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率を計算。true_range の NULL 伝播を適切に制御。
    - calc_value: raw_financials と prices_daily を組み合わせて PER / ROE を計算（EPS 欠損時は None）。
    - 実装は DuckDB SQL を主体とし、ターゲット日ベースのスキャン範囲を最小化。
  - `kabusys.research.feature_exploration`
    - calc_forward_returns: target_date から各ホライズン先のリターンを一括 SQL（LEAD）で取得。horizons 引数に対する入力検証あり（1〜252）。
    - calc_ic: ファクター値と将来リターンから Spearman ランク相関（IC）を算出。有効レコード数が 3 未満の場合は None。
    - rank: 同順位は平均ランクで処理し、丸め誤差対策として round(v, 12) を使用。
    - factor_summary: count/mean/std/min/max/median を計算するユーティリティ。
    - zscore_normalize を data.stats から再エクスポート（kabusys.research パッケージレベル）。
- AI 関連機能（OpenAI 統合、フェイルセーフ実装）
  - `kabusys.ai.news_nlp`
    - 生ニュースを LLM によるセンチメント解析で銘柄ごとの ai_score を計算して ai_scores テーブルへ書き込み。
    - ニュース収集ウィンドウ（JST ベースの前日 15:00 〜 当日 08:30）を計算する calc_news_window を提供（UTC naive datetime を返す）。
    - 記事集約: news_symbols 経由で銘柄ごとに最新記事を最大件数/文字数でトリムして結合。
    - バッチ送信（最大 20 銘柄 / リクエスト）、OpenAI クライアント生成、JSON Mode を利用した堅牢なレスポンス検証。
    - リトライ戦略（429/接続断/タイムアウト/5xx に対して指数バックオフ、最大リトライ回数指定）。
    - レスポンス検証により未知銘柄や非数値スコアを除外、スコアは ±1.0 にクリップ。
    - DB 書き込みは冪等性を保つ（対象コードのみ DELETE → INSERT）。DuckDB executemany の空パラメータ制約を考慮。
    - エラー時は例外を投げず可能な範囲で継続するフェイルセーフ設計。
  - `kabusys.ai.regime_detector`
    - ETF 1321 の 200 日 MA 乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次レジーム（bull/neutral/bear）を判定。
    - マクロニュースの抽出はキーワードベース、LLM 呼び出しは独立実装で news_nlp と意図的に分離。
    - ma200_ratio のデータ不足時や API 失敗時は安全側フォールバック（ma200_ratio = 1.0 / macro_sentiment = 0.0）。
    - 合成スコアに閾値を適用して label を決定し、market_regime テーブルへ冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）。
- 監視 DB 永続化層（SQLite）
  - `kabusys.monitoring.monitoring_db`
    - init_monitoring_db により監視用テーブル群（system_status, trade_logs, positions, risk_logs, ...）と主要インデックスを冪等的に作成するスクリプトを実装。
    - テーブル定義はログ時間・CPU/MEM/DISK 指標、トレードログ、ポジション永続化等を含む。

### Changed
- （初回リリースにつき該当なし）

### Fixed
- （初回リリースにつき該当なし）

注記:
- AI 機能（news_nlp, regime_detector）は OpenAI API キーの提供が必須（引数または環境変数 OPENAI_API_KEY）。API 呼び出し周りはテストしやすいように内部呼び出し関数を外部モック可能に設計。
- DuckDB / SQLite を用いた実装は外部ネットワーク（取引 API 等）へのアクセスを行わない設計方針を採用。
- 本 CHANGELOG はソースコードから推測した主要な追加機能・設計意図をまとめたものです。実装の細部や追加のサブ機能は各ファイルのドキュメント（docstring）を参照してください。