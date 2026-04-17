# Changelog

すべての重要な変更を記録します。フォーマットは「Keep a Changelog」準拠です。

なお、本CHANGELOGは与えられたソースコード（機能実装・コメント・TODO など）から推測して作成しています。実際のコミット履歴ではなく「機能的な差分説明」として参照してください。

## [Unreleased]

### 追加
- news_nlp モジュールの処理フロー設計を実装中（OpenAI API を用いたニュースの銘柄別センチメント集約・バッチ送信・リトライ・レスポンス検証・テーブル書き換えロジックの設計を導入、実装ファイルは途中まで記述）。
- 各モジュールの挙動や挙動上の注意を明示するコメント／ドキュメントを多数追加（設計方針、想定データ欠損時のフォールバック方針、制約など）。
- 一部の TODO を明記（例: position_sizing の銘柄別 lot_size 保持拡張、risk_adjustment の価格フォールバック）。

### 既知の問題 / 作業予定
- news_nlp の実装が途中で切れている（ファイル末尾が欠落）。OpenAI 呼び出し周り・DB 書込の最終処理が未完。
- position_sizing の単元株（lot_size）を銘柄別に扱うための拡張が未実装（コメントで将来的拡張を提案）。
- risk_adjustment.apply_sector_cap で price が欠損（0.0）の場合のエクスポージャー過小見積りに関する注意喚起。補完価格の導入検討が必要。

---

## [0.1.0] - 2026-04-17

### 追加
- プロジェクト初期リリース（バージョン 0.1.0）。
- 実行用スクリプト
  - run_execution.py
    - ExecutionEngine の起動エントリポイントを実装。
    - KABUSYS_ENV=paper_trading のときは paper_sqlite_path を使用して本番 DB と分離する設計。
    - BrokerClientFactory を用いたブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler 組立て、ExecutionEngine のスレッド実行と停止フラグ（data/stop_requested.flag）監視を実装。
    - エンジン用 PID ファイル管理（data/execution.pid）と停止フラグ検知による安全停止処理を実装。
  - run_monitoring.py
    - SystemMonitor ポーリングループ起動スクリプトを実装。
    - 環境変数 MONITOR_POLL_INTERVAL によるポーリング周期上書き（デフォルト 60 秒）に対応。
    - Monitoring は環境に関係なく本番 sqlite_path を使用する設計（監視データは共通化）。
    - 停止フラグ（data/stop_requested.flag）検知でループを終了。

- 設定 / 環境変数管理
  - config.Settings クラスを実装（プロパティベースで各種設定を取得）。
  - .env / .env.local の自動読み込み機能を追加（プロジェクトルートを .git または pyproject.toml で検出）。
  - 自動ロードを無効化する環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD を追加。
  - .env パーサ実装（export プレフィックス対応、クォート・エスケープ・コメント処理など）。
  - 必須環境変数未設定時に ValueError を送出する _require 関数の導入。
  - 環境関連のバリデーション（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE の妥当性チェック）を追加。
  - PAPER_TRADING_SQLITE_PATH, PAPER_FILL_MODE, PID_FILE_PATH など運用に必要な設定キーを用意。

- Portfolio 構築機能（純粋関数群）
  - portfolio.portfolio_builder
    - select_candidates（スコア降順・同点タイブレーク処理）
    - calc_equal_weights（等金額配分）
    - calc_score_weights（スコア加重配分、全スコア 0 の場合は等配分にフォールバック）
  - portfolio.risk_adjustment
    - apply_sector_cap（セクター集中制限ロジック。既存保有のセクター別時価計算、上限超過セクターの候補除外）
    - calc_regime_multiplier（market regime に応じた投下資金乗数。bull/neutral/bear をサポート、未知レジームはフォールバック）
  - portfolio.position_sizing
    - calc_position_sizes（allocation_method: "risk_based" / "equal" / "score" に対応）
    - リスクベースの株数計算、単元株丸め（lot_size）、最大ポジション上限、aggregate cap によるスケールダウン／端数処理ロジックを実装
    - cost_buffer を用いた保守的なコスト見積りとスケーリングアルゴリズム
    - aggregate スケールダウン時の fractional remainder を考慮した再配分ロジック

- 監視 / ユーティリティ
  - utils.process_priority
    - set_process_priority（Windows / POSIX の差分吸収、アクセス権限失敗時は警告でスキップ）
    - set_cpu_affinity（最初の N コアに固定。未対応環境や権限不足時は警告でスキップ）
    - 対応レベル: "high", "normal", "low"
    - OS 検出時の安全なフォールバックとログ出力

- 研究（research）モジュール
  - research.factor_research
    - calc_momentum（1M/3M/6M リターン、200日移動平均乖離率）
    - calc_volatility（20日 ATR、相対 ATR、平均売買代金、出来高比率）
    - calc_value（直近財務情報から PER / ROE を算出）
    - DuckDB を用いた SQL + Python 実装（prices_daily / raw_financials を参照）
  - research.feature_exploration
    - calc_forward_returns（任意ホライズンの将来リターンを一括取得）
    - calc_ic（Spearman ランク相関（IC）計算、3 レコード未満で None）
    - rank（同順位は平均ランクで処理）
    - factor_summary（count/mean/std/min/max/median を算出）
    - 外部ライブラリ非依存（標準ライブラリのみで実装）

- ツール
  - tools.paper_verification_report
    - Paper Trading の検証レポート生成 CLI（--from/--to/--db オプション対応）
    - 検証指標: 稼働率・注文成功率・送信率・リスク却下数・P95 レイテンシなど
    - 判定基準（デフォルト閾値）を導入（稼働率 99%, 成功率 90% など）
    - DB のテーブル欠如時に堅牢に N/A を返すフォールトトレラント実装
    - P95 計算、日付フィルタ組立、出力フォーマットを実装

- AI / ニュース NLP（設計および部分実装）
  - ai.news_nlp
    - OpenAI（gpt-4o-mini）を用いたニュースの銘柄別センチメントスコアリング設計を追加
    - バッチサイズ・トリム（記事数・文字数）・スコアクリッピング・リトライ方針（429/5xx/ネットワーク断）を定義
    - タイムウィンドウ計算（JST ベース → UTC 変換）ユーティリティを実装
    - API キー未設定時に ValueError を送出

### 変更
- パッケージメタ
  - パッケージ初期バージョンを __version__ = "0.1.0" として設定。
  - package __all__ に主要サブパッケージ名を明示（data, strategy, execution, monitoring）。

### 修正
- .env パーサの挙動向上
  - export プレフィックス対応、クォート内のバックスラッシュエスケープ処理、インラインコメントの扱い改善を実装。
  - override / protected オプションで OS 環境変数を保護しつつ .env.local を上書き可能にした。

### ドキュメント / ログ
- 各モジュールに詳細な docstring を追加（設計方針、引数・戻り値の仕様、注意点、例外条件など）。
- 主要処理は logging を使用して状態を出力（起動時環境、ポーリング開始、停止フラグ検知、エラー発生時の例外ログなど）。

### 既知の制約（リリース時点）
- news_nlp の最終パーツが未完成（この処理は次リリースで完了予定）。
- DuckDB / SQLite / OpenAI など外部リソース依存のため、実行環境のセットアップが必要。
- position_sizing の lot_size は全銘柄共通での扱い（将来的に銘柄別対応を予定）。
- process_priority の優先度設定は環境によっては権限不足で失敗する（警告でスキップ）。

---

## 参考（実装上の注記）
- run_monitoring は MONITOR_POLL_INTERVAL が 0 以下または不正な文字列だった場合、デフォルト 60 秒にフォールバックする堅牢な実装。
- run_execution は paper_trading 環境時に paper_sqlite_path を使用することで、実トレードデータと完全に分離する安全設計。
- position_sizing の aggregate スケールダウンアルゴリズムは、端数の配分に再現性を持たせるため残差ソート（fractional remainder）とコードを二次キーにした安定ソートを採用している。
- research モジュールは DuckDB 上でウィンドウ関数（LAG, LEAD, AVG OVER 等）を多用し、営業日ベースの計算を想定したバッファ日数で範囲スキャンを限定している（パフォーマンス配慮）。

---

（この CHANGELOG はコードから推測して作成した概要です。実際のコミットメッセージや差分が必要な場合は git 履歴の提供をお願いします。）