CHANGELOG
=========

All notable changes to this project will be documented in this file.
This project adheres to "Keep a Changelog" (https://keepachangelog.com/ja/1.0.0/).
変更は互換性が破壊的かどうか（Breaking Changes）を明記します。

Unreleased
----------

（なし）

0.1.0 - 2026-04-17
-----------------

Added
- 初期リリース — 基本機能を実装。
- 実行エントリ:
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV=paper_trading 時は paper_trading 専用の SQLite(DB) を使用して本番 DB と分離する挙動を実装。停止フラグ/実行 PID 管理とスレッドでのエンジン実行制御を含む。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト60秒）。Monitoring は環境に関わらず本番 sqlite_path を使用する旨を明記。
- 設定管理:
  - config.py: 環境変数読み込み機能を追加（.env / .env.local の自動読み込み、読み込み順序の制御、KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化）。.env の行パーサはクォートやエスケープ、export プレフィックス、コメントルールに対応。各種設定プロパティ（DB パス、PID/kill flag パス、 paper_trading 関連、監視閾値、環境/ログレベルの検証）を提供。
- ポートフォリオ構築:
  - portfolio/portfolio_builder.py: 銘柄選定（select_candidates）、等分配（calc_equal_weights）、スコア加重配分（calc_score_weights、全て0スコア時は等分配へフォールバック）を実装。
  - portfolio/risk_adjustment.py: セクター集中抑制（apply_sector_cap）、市場レジームに応じた投下資金乗数（calc_regime_multiplier）を実装。
  - portfolio/position_sizing.py: 株数決定ロジック（risk_based / equal / score モード）、単元株丸め、個別/全体キャップ、コストバッファを考慮したスケーリングを実装。
- 監視・ユーティリティ:
  - utils/process_priority.py: プロセス優先度設定と CPU affinity 固定ユーティリティを追加（Windows / POSIX を吸収、権限不足や未対応プラットフォーム時は警告でスキップ）。
- リサーチ／ファクター:
  - research/factor_research.py: Momentum / Volatility / Value ファクター計算を DuckDB を用いた SQL クエリ実装で追加（MA200, ATR20 等）。
  - research/feature_exploration.py: 将来リターン計算(calc_forward_returns)、IC（calc_ic）、ランク変換(rank)、要約統計(factor_summary) を純粋関数で追加。外部依存を使用せず実装。
  - research/__init__.py: 主要関数群をエクスポート。
- ツール:
  - tools/paper_verification_report.py: Paper Trading 検証レポート生成ツールを追加。稼働率/注文成功率/送信率/レイテンシ(P95) などを計算し PASS/FAIL を判定。CLI 引数で期間指定や DB パス指定が可能。DB テーブルが存在しない場合の安全処理（OperationalError のキャッチ）を含む。
- AI:
  - ai/news_nlp.py: ニュースに対する OpenAI を用いた NLP スコアリング基盤を実装（ニュースウィンドウ計算、バッチ送信、リトライ戦略、スコアクリップ、ai_scores への書き込み方針などの設計・実装）。gpt-4o-mini を想定した設計。※（注記: このファイルのスナップショットは途中で切れているため、完全実装は続きあり）
- パッケージ情報:
  - __init__.py: バージョンを 0.1.0 に設定し、主要サブパッケージを __all__ に追加。

Changed
- 設定読み込みの挙動を明確化:
  - OS 環境変数 > .env.local > .env の優先順序で自動ロードする実装を追加。既存の OS 環境変数は .env によって上書きされない（.env.local は override=True だが protected OS 変数は上書き不可）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化を導入（テスト用途向け）。
- 監視処理:
  - run_monitoring は環境に関わらず production 用 sqlite_path を使用する仕様を明記（モニタリングはデータ分離しない意図）。
- run_execution:
  - paper_trading 環境時は paper_sqlite_path を用いることで発注系データを本番と完全分離する仕様を追加。

Fixed
- 環境変数の堅牢性向上:
  - MONITOR_POLL_INTERVAL の不正値（0 以下や非整数）を検出して警告し、デフォルトにフォールバックする挙動を実装（run_monitoring）。
  - PAPER_FILL_MODE の値検証を追加（不正値は ValueError を送出）。
  - KABUSYS_ENV / LOG_LEVEL の許容値チェックを追加（不正値は ValueError）。
- ポートフォリオ・ポジションサイズ:
  - スケーリング後のラウンド処理、単元（lot_size）丸め、残差の扱い（fractional_remainder に基づく追加配分）を実装し、合計投下金額が利用可能現金を超える場合に保守的に縮小するロジックを改善。
  - price が欠損（0 または None）の場合のスキップや警告を追加して過小見積りやゼロ除算を回避。
- utils:
  - set_process_priority / set_cpu_affinity は権限不足や未対応環境で例外を握り、警告ログを出すようにして安定性を向上。

Deprecated
- なし

Removed
- なし

Security
- なし

Known issues / Notes
- ai/news_nlp.py のスナップショットは途中で切れている（ファイル末尾が欠けている）。設計と多くの実装は含まれますが、このチェックアウト時点では score_news の続きが存在しないため、完全動作させるには残り実装の追加が必要です。
- run_monitoring が「環境にかかわらず本番 sqlite_path を使用する」点は意図的な仕様（モニタリングデータを paper_trading と共有しないなどの要件がある場合は設計変更が必要）。

その他
- 各モジュールはできる限り外部副作用を避け、DuckDB / SQLite の接続や渡された引数のみで動作する純粋関数スタイルを採用する箇所が多く見られます（テスト容易性を意識した設計）。

--- 
今後の予定:
- ai/news_nlp の残り実装補完と統合テスト。
- ドキュメントの追加（API 使用例・設定例・運用手順）。
- 単体テスト・CI の整備。