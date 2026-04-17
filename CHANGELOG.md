# Changelog

すべての変更は Keep a Changelog の形式に従っています。  
重要度別に分けて記載しています（Added / Changed / Fixed / Deprecated / Removed / Security）。各項目には関連ファイル/モジュールを併記しています。

## [Unreleased]

### Added
- 全体
  - パッケージ初期版からの機能拡張・整備を行いました。主要サブモジュール（execution / monitoring / portfolio / research / ai / tools / utils）の機能がまとまり、運用・検証用のスクリプトやユーティリティが追加されています。

- 実行・監視
  - 実行エンジン起動スクリプトを追加（src/kabusys/run_execution.py）。
    - KABUSYS_ENV=paper_trading 時は MockBroker を使用して paper_trading 用の SQLite DB（data/paper_trading.db 等）に記録する動作をサポート。
    - 起動前に停止フラグを確認し、フラグが立っている場合は起動しない安全機能を実装。
  - 監視ループ起動スクリプトを追加（src/kabusys/run_monitoring.py）。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト: 60秒）。
    - 監視は環境にかかわらず本番 sqlite_path を使用する運用方針を明示。

- ツール
  - Paper Trading 検証レポート生成ツールを追加（src/kabusys/tools/paper_verification_report.py）。
    - 期間指定や DB パス指定が可能。稼働率・注文成功率・送信率・レイテンシ(P95等) 等の指標を算出し PASS/FAIL 判定を出力。

- ポートフォリオ構築関連
  - 銘柄候補選定・重み計算（select_candidates, calc_equal_weights, calc_score_weights）を実装（src/kabusys/portfolio/portfolio_builder.py）。
    - スコア降順・同点時の signal_rank によるタイブレーク等の仕様を反映。
  - セクター集中チェックとレジーム乗数（apply_sector_cap, calc_regime_multiplier）を実装（src/kabusys/portfolio/risk_adjustment.py）。
    - 売却予定銘柄をエクスポージャー計算から除外するオプションを追加。
    - 未知のレジームはフォールバック（警告ログ）して multiplier=1.0 を採用。
  - ポジションサイズ計算（calc_position_sizes）を実装（src/kabusys/portfolio/position_sizing.py）。
    - risk_based / equal / score の配分方式をサポート。
    - 単元株（lot_size）で丸め、aggregate cap（available_cash）を超える場合のスケールダウンと端数処理を実装。
    - cost_buffer（手数料・スリッページ見積）を考慮して保守的に計算。

- 研究（research）
  - ファクター計算モジュールを追加（src/kabusys/research/factor_research.py）。
    - Momentum / Volatility / Value 等の定量ファクターを DuckDB 経由で計算。
  - 特徴量探索ユーティリティを追加（src/kabusys/research/feature_exploration.py）。
    - 将来リターン計算、IC（Spearman）計算、ファクター統計サマリ等を提供。
  - research パッケージ向けに公開 API を整備（src/kabusys/research/__init__.py）。

- AI ニューススコアリング（実験的）
  - raw_news を OpenAI（gpt-4o-mini）でスコアリングするモジュールを追加（src/kabusys/ai/news_nlp.py、実装途中）。
    - バッチ処理、トークン肥大対策、リトライ戦略、レスポンス検証、結果の ai_scores テーブル反映方針などを設計。
    - ニュースの集計ウィンドウ（JST基準→UTC変換）関数を実装。

- 環境設定・ローダ
  - .env ファイル自動ロード機能を改善（src/kabusys/config.py）。
    - プロジェクトルート検出（.git または pyproject.toml）に基づく自動読み込み。
    - .env および .env.local を適切な優先度で読み込む処理を実装。
    - export 形式、クォート（エスケープ対応）、インラインコメント等に堅牢に対応。

- プロセス制御ユーティリティ
  - プロセス優先度設定ユーティリティを追加（src/kabusys/utils/process_priority.py）。
    - Windows / POSIX を吸収して set_process_priority(level) を提供。
    - set_cpu_affinity() を追加し、プロセスの CPU アフィニティを制御可能（利用権限がない場合は警告を出してスキップ）。

### Changed
- 設定（Settings）挙動の明確化（src/kabusys/config.py）
  - KABUSYS_ENV の許容値とバリデーションを明確化（development / paper_trading / live）。
  - PAPER_FILL_MODE の有効値チェックを追加（instant / partial / never / reject）。
  - 各種閾値やパス（duckdb/sqlite/paper_sqlite/pid/kill_flag）をプロパティ経由で取得できるよう整備。

- データベース接続方針
  - 監視用スクリプトは、環境にかかわらず本番 sqlite_path を使用することを明示（src/kabusys/run_monitoring.py）。
  - execution は paper_trading 環境であれば専用 DB を使って本番と分離（src/kabusys/run_execution.py）。

### Fixed
- MONITOR_POLL_INTERVAL の入力検証強化（src/kabusys/run_monitoring.py）
  - 0以下や数値以外の値が指定された場合はデフォルト（60秒）にフォールバックし、警告ログを出すように修正。time.sleep に渡せない値を防止。

- 環境ファイルパーサの堅牢化（src/kabusys/config.py）
  - export プレフィックス、クォート文字内のバックスラッシュエスケープ、インラインコメントの扱い等の不整合を修正。
  - .env.local を .env の上書き用途として扱い、OS 環境変数（protected）を上書きしないように保護。

- process_priority API のエラーハンドリング改善（src/kabusys/utils/process_priority.py）
  - サポート外 OS の場合はスキップして警告出力。権限不足や未実装機能発生時も例外を投げず警告でフォールバック。

- position_sizing の資金配分ロジック改善（src/kabusys/portfolio/position_sizing.py）
  - price が欠損/0 の銘柄をスキップすることでゼロ除算等の問題を回避。
  - aggregate cap を超えた場合のスケーリング、端数処理（lot_size 単位での再配分）を正しく実装。
  - cost_buffer を考慮して保守的に計算。

- calc_score_weights のゼロスコア全件対応（src/kabusys/portfolio/portfolio_builder.py）
  - 全銘柄のスコア合計が 0 の場合、等金額配分にフォールバックして警告ログを出すように修正。

- research / feature_exploration の堅牢化（src/kabusys/research/feature_exploration.py）
  - calc_forward_returns: horizons の検証を追加（正の整数かつ <=252）。
  - calc_ic: 有効レコードが 3 件未満の場合は None を返す仕様。ties を平均ランクで扱う rank 実装によりスピアマン計算安定化。

### Deprecated
- なし（現時点で非推奨 API は未定義）

### Removed
- なし

### Security
- OpenAI API キーの取り扱いに関する注意書きを追加（src/kabusys/ai/news_nlp.py）
  - api_key 引数または環境変数 OPENAI_API_KEY を必須としており、未設定時は ValueError を送出するようにして誤った公開を防止。

---

## [0.1.0] - 2026-04-17

初回公開（ベースライン実装）。以下を含みます。

### Added
- パッケージメタ情報（src/kabusys/__init__.py, __version__ = "0.1.0"）
- 実行・監視スクリプト（run_execution, run_monitoring）
- 設定管理および .env 自動ロード機能（src/kabusys/config.py）
- Portfolio コンポーネント（portfolio_builder, risk_adjustment, position_sizing）
- Research コンポーネント（factor_research, feature_exploration）
- AI ニューススコアリング（news_nlp）— 基本的な設計と一部実装
- ユーティリティ（process_priority set_process_priority / set_cpu_affinity）
- Paper Trading 検証レポートツール（tools/paper_verification_report.py）
- 各モジュールの公開 API を整備（パッケージ __init__ でのエクスポート）

### Fixed
- 基本的な入力検証やエラーハンドリングを各所で改善（詳細は Unreleased の Fixed 節参照）。

---

注記:
- ai/news_nlp.py は設計が先行しており、API 呼び出し周りや最終的なデータ永続化ロジックは継続して実装・テストが必要です（部分的に実装中）。
- Documentation（詳しい使用法やチュートリアル）は別途整備予定です（特に ExecutionEngine の起動フローと paper_trading モード、.env の扱いについて）。