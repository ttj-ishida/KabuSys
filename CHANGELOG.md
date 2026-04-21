CHANGELOG
=========

すべての注目すべき変更はこのファイルに記録します。  
フォーマット: Keep a Changelog 準拠（セマンティックバージョニングに従います）。

Unreleased
----------

注: 現時点では未リリースの変更や既知の TODO をここに記載します。

Added
- research/factor_research.py: ファクター計算モジュールを追加（Momentum / Value / Volatility / Liquidity を想定）。DuckDB を使った prices_daily / raw_financials に依存する設計（ただしファイルは途中実装、未完了の部分あり）。
- run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
  - 監視は環境にかかわらず本番の sqlite_path を使用する設計。
  - 停止フラグ（data/stop_requested.flag）検出で安全に終了。
- run_execution.py: ExecutionEngine 起動スクリプトを追加。
  - KABUSYS_ENV=paper_trading 時は paper_trading 専用 SQLite を使用（data/paper_trading.db がデフォルト）して本番 DB と分離。
  - MockBroker を含む BrokerClientFactory 経由のブローカークライアント選択、OrderManager / OrderRepository / RiskManager / Reconciler を組み合わせて ExecutionEngine を起動。
  - 停止フラグ・PID ファイルの取り扱い、スレッド実行の安全シャットダウンを考慮。
- config.py: 環境設定管理を実装。
  - .env 自動読み込み（プロジェクトルートの判定: .git / pyproject.toml を探索）。
  - .env/.env.local の読み込み優先度、OS 環境変数の保護（上書き不可）を実装。
  - 多数の設定プロパティを提供（J-Quants、kabuAPI、DB パス、監視閾値、環境判定、paper_trading 用設定等）。
  - PAPER_FILL_MODE のバリデーション等の入力チェック。
- config_setup.py: 対話式 .env 作成/更新ウィザードを追加。
  - 必須 / 任意設定のヒント、シークレットのマスク表示、保存確認、.env ファイルの生成ロジックを提供。
  - .env を絶対に Git にコミットしない旨の注記を含む。
- validate_config.py: 起動前設定検証 CLI を追加。
  - 必須環境変数や KABUSYS_ENV の妥当性、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在とパース検証（PyYAML がない場合は警告）を実施。
  - --strict オプションで警告を FAIL 扱いにできる。
- utils/logging_setup.py: 共通ロギング初期化ユーティリティを追加。
  - stdout に出す StreamHandler と 日次ローテーション (TimedRotatingFileHandler、30 日分保存) をルートロガーに設定。
  - LOG_DIR/LOG_LEVEL の解決順やディレクトリ作成失敗時のフォールバックを実装。
- utils/process_priority.py: プロセス優先度・CPU affinity 設定ユーティリティを追加。
  - Windows/Linux(Mac,FreeBSD 含む) の差分を吸収。アクセス権限不足時は警告を出してスキップ。
  - set_process_priority(), set_cpu_affinity() を提供。
- portfolio/*: ポートフォリオ構築関連の純粋関数群を追加（DB 参照なし、メモリ内計算）。
  - portfolio_builder: select_candidates(), calc_equal_weights(), calc_score_weights()
  - position_sizing: calc_position_sizes() — risk_based / equal / score の配分方式、単元株（lot_size）丸め、aggregate cap のスケーリングを実装。
  - risk_adjustment: apply_sector_cap()（セクター集中制限ロジック）、calc_regime_multiplier()（レジーム乗数）。
- tools/paper_verification_report.py: Paper Trading 検証レポート生成ツールを追加。
  - 稼働率(uptime)、注文成功率(fill_rate)、送信率(send_rate)、P95 レイテンシ等を計算し PASS/FAIL 判定を出力。
  - 日付範囲フィルタ、DB パスのオーバーライド (--db) に対応。
- パッケージメタ: __version__ = "0.1.0" を設定。

Changed
- ログ周りを統一: 全起動スクリプトが setup_logging() を呼ぶことでログの挙動が一貫化。
- プロセス起動時に優先度を "high" に上げる振る舞いを実行スクリプト（monitoring/execution）で導入。

Fixed
- .env パーサーの改善:
  - export KEY=val 形式対応、シングル/ダブルクォート内でのバックスラッシュエスケープ対応、行内コメント取り扱いの改善。
  - .env.local を使った上書きルールや OS 環境変数保護の実装により、自動ロード時の上書き制御を堅牢化。

Security
- config_setup にて .env を生成する際、ファイルを Git にコミットしないよう明示的に注意喚起を追加。
- 環境変数の未設定時に明確にエラーを出す _require() 実装で起動前に問題を検出。

Known issues / TODO
- research/factor_research.py はファイル末尾が途中で切れており実装未完（calc_momentum 等が未完）。今後の作業で完成させる予定。
- apply_sector_cap(): price が 0.0（欠損）時にエクスポージャーが過少見積りされる旨の TODO コメントあり。前日終値等のフォールバック価格導入が望まれる。
- position_sizing.calc_position_sizes(): lot_size を銘柄毎に持たせる拡張（stocks マスタ）は未実装。将来対応予定。
- validate_config の YAML 検証は PyYAML が存在しない場合にスキップされる。CI/本番環境では PyYAML の導入を推奨。
- run_monitoring は設計上「環境にかかわらず本番 sqlite_path を使用」する（監視データは統一 DB に集約する意図）。テスト時は注意が必要。

-------------------------------------------------------

0.1.0 - 2026-04-21
------------------

Added
- 初回リリース: KabuSys のコア機能群を実装・公開。
  - 実行・監視スクリプト: run_execution.py, run_monitoring.py
  - 環境設定・管理: config.py（Settings クラス、自動 .env ロード）、config_setup.py（ウィザード）、validate_config.py（検証 CLI）
  - ロギング/プロセス制御ユーティリティ: utils/logging_setup.py, utils/process_priority.py
  - ポートフォリオ構築ライブラリ: kabusys.portfolio（選定・重み付け・リスク調整・ポジションサイズ計算）
  - Paper Trading 検証ツール: tools/paper_verification_report.py
  - リサーチ基盤（未完のファイルあり）: research/factor_research.py
  - パッケージ設定: __version__ = "0.1.0"

Changed
- ルートロガーの初期化を統一し、日次ログローテーション・stdout 出力を既定に設定。
- Execution/Monitoring 起動時にプロセス優先度を "high" に設定するよう変更（set_process_priority の導入）。

Fixed
- .env パーサーを堅牢化（export 形式・クォート・エスケープ・コメント処理の改善）。
- .env 自動ロードの上書き/保護ロジックを実装（OS 環境変数を保護）。

Security
- .env を生成する際に Git へコミットしない旨の注意を付記。

Notes
- 本リリースでは設計上の決定（例: 監視は本番 sqlite を参照、paper_trading は専用 DB を使用）が明確化されています。運用時は KABUSYS_ENV や各種パス設定に注意してください。

---

今後のロードマップ（予定）
- research/factor_research の完了（ファクター計算の完成とテスト）。
- ポートフォリオ構築の追加チューニング（銘柄別 lot_size、価格フォールバック処理）。
- 監視・検証の自動化（CI 連携、YAML パースの厳格化）。
- より詳細なドキュメント（PortfolioConstruction.md / StrategyModel.md の実装参照ガイド）を追加。

以上。必要であれば各リリースの差分（コミット単位）や英語版 CHANGELOG も作成します。どの形式で出力するか（README への要約追加、GitHub Releases 用テキスト等）を指示してください。