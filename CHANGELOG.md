# Changelog

すべての変更は Keep a Changelog の慣例に従って記載しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

注: コードベースから推測して記載しています（実装上の注記や TODO も含む）。

## [Unreleased]

### Added
- calc_momentum の実装が途中（ヘッダと定数を追加）。DuckDB を使ったファクター計算モジュール（research/factor_research.py）を導入。Momentum / Value / Volatility / Liquidity などのファクターを想定した設計。
- settings, .env 自動読み込み周りの堅牢化:
  - プロジェクトルート検出ロジックを追加（.git または pyproject.toml を探索）。
  - .env パーサ実装を改善（export 形式、クォート内エスケープ、インラインコメントの扱い）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化機能。
- コンフィグウィザード（config_setup.py）の UX 強化（対話式ウィザード、既存 .env の読み込み・マスク表示、保存時の確認、.env のテンプレート出力）。
- validate_config CLI（設定検証ツール）を拡張:
  - 必須環境変数チェック、KABUSYS_ENV の妥当性検証、DB パスと YAML ファイルの存在/パースチェック、live 環境向けの追加警告。
  - --strict オプションで警告を FAIL 扱いにできる。
- 実行／監視起動スクリプトを追加:
  - run_execution.py:
    - ExecutionEngine 起動ロジック、BrokerClientFactory によるブローカークライアント生成、paper_trading 用に本番 DB と分離する paper_sqlite_path のサポート。
    - 停止フラグ（data/stop_requested.flag）検知による安全停止、実行用 PID ファイル出力。
    - デフォルトでプロセス優先度を "high" に設定。
  - run_monitoring.py:
    - SystemMonitor ポーリングループ起動、MONITOR_POLL_INTERVAL 環境変数によるポーリング間隔上書き、監視 DB の初期化（本番 sqlite_path を常に使用）。
    - 停止フラグ検知でループ終了。
- ログ設定ユーティリティ（utils/logging_setup.py）を追加:
  - stdout 出力用 StreamHandler と日次ローテーションファイルハンドラ（TimedRotatingFileHandler）をルートロガーに設定。
  - ログディレクトリの解決順、LOG_LEVEL 解決順、既存ハンドラのクリア処理、ファイル出力失敗時のフォールバック。
  - 日次ローテーション・30日分保持。
- プロセス優先度・CPU affinity ユーティリティ（utils/process_priority.py）を追加:
  - Windows/Linux/macOS の差を吸収してプロセス優先度を設定（"high"/"normal"/"low"）。
  - CPU affinity を最初の N コアに固定する set_cpu_affinity を提供（権限や非対応環境では警告を出してスキップ）。
- ポートフォリオ構築関連の純粋関数群を追加（portfolio パッケージ）:
  - portfolio_builder.py: 候補選定 (select_candidates)、等金額配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights)。
  - risk_adjustment.py: セクター集中制限 (apply_sector_cap)、市場レジーム乗数 (calc_regime_multiplier)。
  - position_sizing.py: 各種配分方式（risk_based / equal / score）に基づく発注株数計算、単元株丸め、aggregate cap によるスケールダウンロジック、cost_buffer を使った保守的コスト見積り。
  - これらは DB 参照を行わない純粋関数として設計（単体テスト容易）。
- paper_trading 用検証レポートスクリプト（tools/paper_verification_report.py）を追加:
  - SQLite（paper_trading DB）から安定性・注文成功率・送信率・レイテンシを集計、P95 の算出、閾値判定による PASS/FAIL 判定。
  - CLI: --from / --to / --db オプション対応。環境変数 PAPER_TRADING_SQLITE_PATH とデフォルトパスをサポート。
  - デフォルトのパスや閾値（稼働率 99%、注文成功率 90%、送信率 95%、P95 レイテンシ 200ms）を定義。

### Changed
- DB 周りの扱いを明確化:
  - 監視 (monitoring) は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する方針を明記。
  - run_execution は paper_trading 環境時に paper_sqlite_path を使用して本番 DB と完全分離する実装に変更/設計。
- ロギング挙動: stdout（sys.stdout）を標準出力に用いることで cron/Task Scheduler 等でのリダイレクトを想定した設計に変更。
- .env パーサーの挙動を詳細に定義（クォート内エスケープ処理、インラインコメントの扱い、export プレフィックス対応など）。

### Fixed
- settings.paper_fill_mode の妥当性検証を追加（有効値チェック）。不正値は ValueError を送出するようにして安全性を向上。
- position_sizing のスケーリングロジックで残余の配分をより再現性のある方法で行うように改良（remainders ソートにコードを鍵にするなど）。

### Security
- .env の書き出しテンプレートに注意喚起コメントを追加（.env を Git にコミットしないよう明記）。

---

## [0.1.0] - 2026-04-19

初回リリース（推測）。以下の主要機能を含む。

### Added
- 基本的なフレームワークを提供:
  - 環境設定管理モジュール (kabusys.config) — .env 自動ロード、Settings クラス、必須変数チェックユーティリティ。
  - 環境設定ウィザード CLI (kabusys.config_setup) — 対話式 .env 生成/更新。
  - 設定検証 CLI (kabusys.validate_config) — 起動前チェックと --strict モード。
- 実行系 / 監視系の起動スクリプト:
  - run_execution.py — ExecutionEngine 起動、ブローカー抽象化（BrokerClientFactory）、OrderManager / RiskManager / Reconciler の組み立て、PID/stop flag 管理。
  - run_monitoring.py — SystemMonitor のポーリングループ、MONITOR_POLL_INTERVAL で間隔設定、監視 DB 初期化。
- ロギングとプロセス管理ユーティリティ:
  - utils/logging_setup.py — stdout + 日次ファイルローテーションの統合ログ設定。
  - utils/process_priority.py — プロセス優先度と CPU affinity の設定ユーティリティ。
- ポートフォリオ構築およびリスク調整:
  - portfolio_builder, risk_adjustment, position_sizing（等金額/スコア加重/リスクベースの配分、セクター上限、レジーム乗数、単元株丸め、aggregate cap）。
- Paper Trading 向け検証ツール:
  - tools/paper_verification_report.py — 検証レポート生成 CLI、稼働率/成功率/送信率/レイテンシの集計と PASS/FAIL 判定。
- research/factor_research.py（ファクター計算モジュール）の初期構成と定数群。

### Changed
- プロジェクトルート探索を導入し、.env の自動読み込みを robust に。
- run_execution が paper_trading の場合に mock ブローカ・専用 DB を使う仕様（本番 DB と分離）。
- ログのデフォルト保存場所とローテーションポリシーを明記（logs/、30日分保持）。

### Fixed
- .env 読み込みの文字列パースを改善（コメント・クォート・export 処理の不具合修正想定）。
- process_priority のプラットフォーム差分ハンドリングにより、非対応 OS でも安全に起動できるよう修正。

### Known issues / TODO
- research/factor_research.calc_momentum の実装が途中でファイル末尾が切れている（実装継続予定）。
- position_sizing の price が欠損（0.0）の場合にエクスポージャーが過小見積もられる旨の注記あり。将来的に前日終値や取得原価などのフォールバックを検討。
- 一部のファイルで外部ライブラリ（psutil, duckdb, PyYAML 等）に依存。利用環境でのインストールが必要。
- ファイル操作・DB 作成権限がない環境ではファイルハンドラや DB 関連処理が失敗し得るため、起動ログでの警告確認を推奨。

---

過去リリースやより詳細な変更履歴が必要であれば、対象コミットや差分の情報を提供してください。コード内の TODO や警告メッセージを元に、優先的に反映すべき改善点やリスクもまとめて提示できます。