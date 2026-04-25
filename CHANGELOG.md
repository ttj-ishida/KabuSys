# Changelog

すべての重要な変更をここに記録します。本ファイルは Keep a Changelog の形式に準拠しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]

## [0.1.0] - 2026-04-25
初回リリース。

### Added
- 全体
  - パッケージ初版をリリース（バージョン 0.1.0）。
  - コア機能群（実行エンジン、監視、ポートフォリオ構築、リサーチ、ユーティリティ、CLI ツール）を実装。
- 起動スクリプト
  - run_execution.py: ExecutionEngine を起動するスクリプトを追加。KABUSYS_ENV に応じて paper_trading 用 DB を分離して利用（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。停止は data/stop_requested.flag の存在検知で行う。
- 設定管理
  - config.py: 環境変数管理クラス Settings を実装。.env/.env.local の自動読み込み（プロジェクトルート検出）、KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化オプション。各種設定プロパティ（DB パス、ログレベル、KABUSYS_ENV 判定、paper_trading 関連など）を提供。
  - config_setup.py: 対話式ウィザードで .env を作成・更新する CLI を追加。
  - validate_config.py: 起動前に .env および config/*.yaml を検証する CLI を追加（--strict オプションで警告も fail 扱い）。
- ポートフォリオ（純粋関数）
  - portfolio.portfolio_builder: 候補選定（select_candidates）、等重配分（calc_equal_weights）、スコア重み配分（calc_score_weights）を実装。
  - portfolio.position_sizing: position sizing ロジック（risk_based / equal / score 対応）、単元株（lot_size）丸め、aggregate cap によるスケーリング処理を実装。
  - portfolio.risk_adjustment: セクター上限適用（apply_sector_cap）や市場レジームに応じた乗数（calc_regime_multiplier）を実装。未知レジーム時にフォールバックと警告を出す。
- リサーチ
  - research.factor_research: ファクター計算モジュールを追加（Momentum / Value / Volatility / Liquidity の計算を想定）。（一部実装が継続中）
- ツール
  - tools.paper_verification_report: Paper Trading の検証レポート生成スクリプトを追加。稼働率、注文成功率、送信率、レイテンシ（P95）などを集計し PASS/FAIL を判定。期間指定・DB 指定オプションあり。
- ユーティリティ
  - utils.logging_setup: StreamHandler（stdout）と日次ローテートの TimedRotatingFileHandler を組み合わせた統一ログ設定を追加。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
  - utils.process_priority: プロセス優先度（high/normal/low）および CPU affinity 設定ユーティリティを追加。Windows / POSIX の差異を吸収し、権限不足時には警告でフォールバック。
  - 複数のモジュールで DuckDB / SQLite 接続を利用（分析・監視用）。

### Changed
- ロギング
  - StreamHandler を stdout に出力するように既定化（cron / タスクスケジューラでのリダイレクトを考慮）。
  - 既存ハンドラがある場合は一旦 flush/close のうえ削除してから再設定（多重ハンドラ防止）。
- Execution / Monitoring の挙動
  - run_execution は paper_trading 環境時に MockBrokerClient を利用し、paper_trading 用 DB に完全分離して記録する設計（本番 DB と分離）。
  - run_monitoring は KABUSYS_ENV にかかわらず本番用 sqlite_path を使用する旨を明示（監視は本番監視対象として扱う）。
- .env ロードの挙動
  - .env の読み込み順を OS 環境 > .env.local > .env とし、.env.local は既存 OS 環境変数を上書きしないよう保護（protected 機構）。
  - .env パーサはシングル・ダブルクォート内のエスケープを考慮し、コメント検出をより厳密に処理するよう改善。
- ポジションサイズ計算
  - aggregate cap のスケーリングロジックを実装。スケール後の残余キャッシュで端数（lot 単位）を補完するアルゴリズムを採用し、再現性のため安定ソートを使用。

### Fixed
- 環境読み込み
  - .env 読み込み失敗時に警告を出してスキップするように安定化（ファイル読み込み失敗が起動を阻害しない）。
- ログディレクトリ作成
  - ログディレクトリ作成に失敗した際にファイルハンドラ作成をスキップしても実行継続するよう改善（例外で落ちない）。
- プロセス優先度
  - 未対応 OS や権限不足時に例外を投げず警告でスキップするように修正（set_process_priority/set_cpu_affinity）。

### Security
- .env 取り扱いの注意書きを config_setup に追加（.env を絶対にリポジトリにコミットしない旨）。
- 対話式ウィザードではシークレット項目（トークン・パスワード）をマスクして表示。

### Notes / Migration
- MONITOR_POLL_INTERVAL 環境変数で監視ポーリング間隔を調整できます。整数以外や 0/負の値が指定された場合はデフォルト 60 秒にフォールバックし、警告を出します。
- PAPER_FILL_MODE の有効値は "instant" | "partial" | "never" | "reject" です。不正値指定時は起動時に ValueError が発生します。
- run_monitoring は監視データに本番用 sqlite_path を使用するため、監視 DB の取り扱いに注意してください（監視目的で本番 DB を参照する設計）。
- process_priority / CPU affinity の適用には psutil が必要です。権限不足や未対応プラットフォームでは警告が出て設定がスキップされます。
- validate_config により起動前の設定チェックが可能です。本番環境（KABUSYS_ENV=live）では LINE の通知設定や KILL_FLAG_CLEAR_ON_START の値に対する注意喚起が行われます。

--- 

（今後のリリースでは research.factor_research の残り実装、ExecutionEngine の内部実装詳細、監視/アラートルールの追加等を予定しています。）