# Changelog

すべての重要な変更を記録します。  
このファイルは「Keep a Changelog」スタイルに準拠しています。  

フォーマットの意味:
- Added: 新機能
- Changed: 既存機能の変更
- Fixed: バグ修正
- Deprecated: 非推奨
- Removed: 削除
- Security: セキュリティ修正

## [Unreleased]

- Added
  - SystemMonitor と ExecutionEngine の起動用スクリプトを追加/整備
    - run_monitoring.py: 監視用ポーリングループを起動するスクリプト。環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を指定可能（デフォルト 60 秒）。監視は常に本番用 sqlite_path を使用して monitoring DB を初期化する。
    - run_execution.py: ExecutionEngine を起動するスクリプト。KABUSYS_ENV=paper_trading の場合は paper_trading 専用の DB を使用し、MockBrokerClient を利用する（本番 DB と分離）。停止用フラグファイル（data/stop_requested.flag）や PID ファイルをサポート。
  - データ分析・研究用モジュールを追加
    - research.factor_research: Momentum / Volatility / Value ファクター計算を DuckDB 上の SQL と Python で実装（mom_1m/3m/6m、MA200乖離、ATR20、avg_turnover 等）。
    - research.feature_exploration: 将来リターン算出、IC（Spearman）計算、ファクター統計サマリー、ランク変換ユーティリティを追加。外部依存を使用せず標準ライブラリで実装。
  - ポートフォリオ構築関連の純粋関数群を追加
    - portfolio.portfolio_builder: シグナル選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）。
    - portfolio.risk_adjustment: セクター集中制限（apply_sector_cap）、市場レジームに応じた資金乗数（calc_regime_multiplier）。
    - portfolio.position_sizing: 各銘柄の発注株数算出（risk_based / equal / score）、lot 単位丸め、aggregate cap によるスケールダウンロジック、cost_buffer を考慮した保守見積り。
  - ユーティリティを追加
    - utils.process_priority: クロスプラットフォームでプロセス優先度と CPU affinity を設定するユーティリティ。Windows / POSIX を吸収し、権限不足や未対応環境では警告でスキップ。
  - Paper Trading 検証用ツールを追加
    - tools.paper_verification_report: paper_trading DB を読み、稼働率・注文成功率・送信率・レイテンシ（P95 等）に基づく検証レポートを生成する CLI ツール。閾値による PASS/FAIL 判定を出力。
  - ニュース NLP スコアリング基盤（AI モジュール）を追加
    - ai.news_nlp: raw_news を OpenAI（gpt-4o-mini 想定）でスコアリングし、ai_scores テーブルへ書き込む処理を実装。タイムウィンドウ計算、銘柄ごと記事集約、バッチ送信（最大 20 銘柄）、リトライ（429/5xx/ネットワーク）とエクスポネンシャルバックオフ、レスポンス検証、スコアのクリップ（±1.0）などの設計方針を実装（API キー必須、フェイルセーフ設計）。※実装は一部ファイル末尾で継続中の箇所があり、補完が必要な部分があります。

- Changed
  - 設定ロードと環境変数処理を強化（config.py）
    - プロジェクトルートの自動検出を .git または pyproject.toml を基準に実行。これにより CWD に依存しない .env 自動読み込みを実現。
    - .env/.env.local の読み込み順を明確化（OS 環境変数 > .env.local > .env）。override/protected の概念で OS 環境変数の保護を実装。
    - .env パーサを強化して、export 形式、クォート文字、バックスラッシュエスケープ、インラインコメント処理に対応。
  - DB 周りの振る舞い統一
    - init_monitoring_db を用いて監視テーブルの存在を起動時に保証（冪等）。monitoring は常に本番 sqlite_path を使用する設計に明確化。
    - run_execution は paper_trading 環境では paper_sqlite_path を使用して本番 DB と完全分離。
  - ログ・プロセス管理
    - 起動スクリプトでプロセス優先度を最初に設定するよう変更（set_process_priority("high")）。
    - 停止フラグ検知により安全にループ/スレッドを終了するフローを追加。
  - research / analysis 関数の SQL 実行範囲にスキャン用バッファを導入（営業日とカレンダー日の差を考慮）。

- Fixed
  - 環境変数パースの不整合や corner case を修正
    - _parse_env_line: クォート内のバックスラッシュエスケープ処理や、クォートなしの行でのコメント認識（'#' 前の空白判定）を改善。空行やコメント行、export プレフィックスに対応。
  - ポートフォリオ計算の安定化
    - calc_score_weights: 全銘柄スコアが 0.0 の場合に等金額配分へフォールバックし、警告出力するよう修正。
    - calc_position_sizes: lot 単位で丸める処理、aggregate cap によるスケーリングと端数処理（fractional 残差に基づく追加配分）を実装。価格欠損時はスキップして安全に動作するよう改善。
    - apply_sector_cap: "unknown" セクターは上限適用除外とし、既存保有の計算で売却予定銘柄を除外するオプションを追加。
  - analysis / reporting の堅牢性向上
    - paper_verification_report: P95 計算（_p95）の境界処理、DB のテーブル欠如時の例外ハンドリング（sqlite3.OperationalError をキャッチして N/A/0 を返す）を実装。
    - calc_forward_returns / calc_momentum / calc_volatility / calc_value: データ不足時に None を返す、及び SQL 側で必要行数をチェックするロジックを追加。
  - utils.process_priority: 未対応 OS の警告を出すようにし、権限不足等の例外を警告に変換して起動の失敗を防止。

- Security
  - OpenAI API キーの扱いについて明確化
    - ai.news_nlp: API キーは引数または環境変数 OPENAI_API_KEY で渡すようにし、未設定時は ValueError を送出して誤った動作を防止。

- Notes / Known issues
  - ai.news_nlp.py はニュース記事集約部分の実装がファイル末尾で途中となっているため、実運用前に未完成箇所の補完が必要です。
  - 一部の機能は本番データ依存（DuckDB の prices_daily/raw_financials、SQLite の各ログテーブル等）。初回実行前にデータベースとテーブルの初期化を行ってください。
  - process_priority や CPU affinity の設定はシステム権限に依存するため、権限がない環境では設定がスキップされます（警告ログのみ）。

---

## [0.1.0] - Initial release

- Added
  - プロジェクト基本構成をリリース（バージョン定義: __version__ = "0.1.0"）
  - 基本的なフォルダ構成とエントリポイント、以下を含む:
    - 設定管理モジュール（config.py）: .env 自動ロード、必須 env チェック、各種設定プロパティ（DB パス、API トークン、閾値等）
    - 実行用スクリプト（run_monitoring, run_execution）
    - 監視 DB 初期化ユーティリティ（monitoring_db 参照実装が利用される）
    - Execution / Order 管理の骨組み（ExecutionEngine, OrderManager, RiskManager 等の呼び出し/組立てを行うスクリプト）
    - ポートフォリオ構築・位置サイズ計算ロジック
    - 研究用ファクター計算モジュール
    - Paper Trading の検証レポート出力ツール
    - AI ニューススコアリングの基盤（OpenAI 連携の骨子）
    - プロセス優先度・CPU 固定のユーティリティ

- Changed
  - 初期実装のため各モジュールは DB スキーマや外部依存の初期化を前提としている（詳細は各モジュールの docstring を参照）。

- Known issues
  - 上述の ai.news_nlp の未完成箇所や、環境差分に起因する動作不良は修正予定。

---

作者: KabuSys チーム（コードベースから推測して自動生成）
注: この CHANGELOG は与えられたコードから推測して作成したものであり、実際のコミット履歴やリリース日とは一致しない可能性があります。実リリース用に利用する場合は、必要に応じて日付・詳細を調整してください。