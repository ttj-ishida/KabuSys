CHANGELOG
=========

すべての注目すべき変更点をこのファイルに記録します。
フォーマットは「Keep a Changelog」（https://keepachangelog.com/ja/1.0.0/）に準拠しています。

バージョン番号はパッケージの __version__（src/kabusys/__init__.py）に合わせています。

なお、本 CHANGELOG は与えられたコードベースの内容から推測して作成しています。実際のコミット履歴とは異なる可能性があります。

Unreleased
----------

- （なし）

0.1.0 - 2026-04-18
------------------

Added
- 基本アプリケーション初版を追加。
  - パッケージバージョン: 0.1.0
- 起動スクリプト / CLI
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数（デフォルト 60 秒）に対応。停止は data/stop_requested.flag により検出。
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV=paper_trading の場合は専用の paper_trading DB（data/paper_trading.db）を使用し、本番 DB と分離して動作。
  - validate_config.py: .env と config/*.yaml の設定検証 CLI を追加（--strict オプションあり）。
  - config_setup.py: .env 初期作成・更新の対話式ウィザードを追加。
  - tools/paper_verification_report.py: Paper Trading 検証レポート生成ツールを追加（期間指定・DB パス指定対応）。稼働率、注文成功率、送信率、レイテンシ (P95) などの指標を出力。
- 設定管理
  - src/kabusys/config.py: Settings クラスを追加。.env の自動ロード（.env / .env.local）、KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み抑止、export 形式やクォート付き値、インラインコメントの処理に対応。
  - 各種設定プロパティ（DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH, PAPER_FILL_MODE, PID/KILL フラグ関連、閾値等）を提供。
- ロギング / プロセスユーティリティ
  - utils/logging_setup.py: 統一的なログ設定ユーティリティを追加。stdout（StreamHandler）と日次ローテートのファイルハンドラ（TimedRotatingFileHandler）をルートロガーに設定。ログディレクトリ作成失敗時はファイル出力をスキップして継続。
  - utils/process_priority.py: プラットフォーム差分を吸収したプロセス優先度設定ユーティリティを追加（Windows / POSIX 対応）。CPU affinity 設定用の set_cpu_affinity を実装。失敗時は警告を出してスキップ。
- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py: 候補選定（select_candidates）、等金額配分（calc_equal_weights）、スコア重み配分（calc_score_weights）を実装。スコアが全て 0 の場合は等金額配分にフォールバック。
  - portfolio/risk_adjustment.py: セクター集中制限を適用する apply_sector_cap、および市場レジームに応じた投資乗数 calc_regime_multiplier を実装（未知のレジームはフォールバック動作）。
  - portfolio/position_sizing.py: 発注株数算出ロジックを実装（risk_based / equal / score の allocation_method 対応）。単元株（lot_size）丸め、1銘柄上限、aggregate cap（available_cash に収めるためのスケーリング）、cost_buffer を考慮した保守的見積りを実装。
- データ / 解析
  - research/factor_research.py: ファクター計算の枠組みを追加（モメンタム、ボラティリティ、バリュー、流動性を想定）。calc_momentum の実装開始（prices_daily / raw_financials を DuckDB で参照する設計）。

Changed
- なし（初版のため）

Fixed
- .env 読み込みの堅牢化:
  - export KEY=val 形式、クォートされた値のエスケープ処理、インラインコメント処理を追加して実用性を向上。
  - .env.local を .env より優先して上書き（OS 環境変数は保護）する挙動を採用。
- ログ設定の堅牢化:
  - ログディレクトリ作成に失敗した場合にファイルハンドラを静かにスキップし、コンソール出力のみで動作を継続するように改善。
- プロセス優先度設定のフェイルセーフ:
  - サポートされていない OS や権限不足時に例外を投げず警告でスキップする実装に修正。

Security
- なし

Deprecated
- なし

Removed
- なし

Notes / 実装上の注意（推測）
- ExecutionEngine はブローカークライアント（BrokerClientFactory）を介して実行され、paper_trading モードでは MockBrokerClient により data/paper_trading.db に記録される想定。risk_manager の初期設定値（max_position_pct, max_utilization, rate_limit, circuit_breaker 等）がデフォルトとして設定されている。
- run_monitoring は常に Settings.sqlite_path（本番監視 DB）を使う実装になっている点に留意。環境にかかわらず監視 DB は production パスを参照する設計。
- stop/kill フラグ（data/stop_requested.flag、data/kill.flag）や PID ファイル（data/execution.pid）でプロセスの制御・監視を行う設計。
- research モジュールは未完（スニペットが途中で終了）に見えるため、ファクター計算の完全実装は今後の作業が必要。
- Paper Trading 検証レポートは P95 計算や各種閾値（稼働率 99%、注文成功率 90% など）を使った PASS/FAIL 判定を行う。

今後の改善提案（所見）
- research のファクター関数群の実装完了および単体テスト追加。
- 各 CLI/エンジンの統合テスト（paper_trading と live のシナリオ）。
- .env の secret 値の取り扱い（マスキングや対話的入力の強化）。
- 銘柄ごとの lot_size をサポートする拡張（コメントで TODO 指定あり）。

--- 

（この CHANGELOG はコード内容から推測して作成しています。実際の変更履歴に合わせて編集してください。）