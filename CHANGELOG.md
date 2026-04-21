# CHANGELOG

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) の形式に従います。  
このファイルはリポジトリ内の現行コードベースから推測して作成しています。

## [Unreleased]
（未リリースの変更はここに記載します）

## [0.1.0] - 2026-04-21
初回リリース。本リリースでは自動売買システム KabuSys のコアユーティリティ、起動スクリプト、構成管理、ポートフォリオ構築、検証ツールなどを実装しました。

### Added
- 基本版パッケージとメタ情報
  - パッケージ初期化とバージョン情報を追加（kabusys.__version__ = "0.1.0"）。

- 起動スクリプト
  - run_execution.py
    - ExecutionEngine を起動するための CLI スクリプトを追加。
    - KABUSYS_ENV が `paper_trading` の場合、専用のペーパートレード用 SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB と完全分離する挙動を実装。
    - BrokerClientFactory を用いたブローカークライアント生成、OrderRepository/OrderManager/ RiskManager/Reconciler の組み立て、ExecutionEngine の起動制御（スレッド実行・停止フラグ監視）を実装。
    - 起動時にプロセス優先度を "high" に設定する処理を追加。
    - 停止フラグ（data/stop_requested.flag）や pid ファイル管理（data/execution.pid）に対応。

  - run_monitoring.py
    - SystemMonitor をポーリングで定期実行する起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL によるポーリング間隔のオーバーライド（デフォルト 60 秒、無効値はデフォルトにフォールバック）。
    - Monitoring は環境設定に関わらず本番 sqlite_path を使用する設計（監視データは環境を跨いで本番 DB に記録される）。
    - 起動時にプロセス優先度を "high" に設定、停止フラグの検出でループ終了、例外時のログ出力とリトライを実装。

- 設定（環境変数・ファイル）管理
  - config.py
    - .env 自動読込機能を追加（プロジェクトルートを .git / pyproject.toml で検出）。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応（テスト用）。
    - .env パース処理を実装（export プレフィックス対応、シングル/ダブルクォート・バックスラッシュエスケープ、インラインコメント処理等）。
    - Settings クラスを追加し、主要な設定プロパティを環境変数から取得（J-Quants / kabu API / DB パス / PID ファイル / 監視閾値 / 環境判定等）。
    - PAPER_FILL_MODE の妥当性チェック（instant/partial/never/reject）を追加。
    - env 値（KABUSYS_ENV, LOG_LEVEL）の妥当性検証を実装。
    - settings = Settings() をモジュールレベルで提供。

  - config_setup.py
    - 対話式 .env 作成・更新ウィザードを追加。
    - 入力補助、既存 .env の読み込み、シークレット項目のマスク表示、確認プロンプト、.env 書き込み機能を実装。
    - デフォルト値・選択肢・説明付きの複数項目をサポート（KABUSYS_ENV、JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DB パス、LOG_LEVEL、KILL_FLAG_CLEAR_ON_START 等）。

  - validate_config.py
    - 起動前の設定検証 CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在・パースチェック（PyYAML がない場合は警告でスキップ）、KABUSYS_ENV=live 時の追加ガード（LINE 通知設定や Kill Flag 設定の注意喚起）を実装。
    - --strict オプションで警告を FAIL 扱いにする機能を追加。

- ロギング・プロセス制御ユーティリティ
  - utils/logging_setup.py
    - 統一的なログ初期化関数 setup_logging を追加。
    - StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション、デフォルト logs/、30日保持）をルートロガーに設定。
    - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続するフォールバック処理を実装。
    - ログレベル解決順（明示引数 > 環境変数 > デフォルト）を実装。

  - utils/process_priority.py
    - クロスプラットフォーム（Windows / POSIX）でプロセス優先度を設定するユーティリティを追加。
    - CPU affinity を最初 N コアに固定する set_cpu_affinity を追加（エラーは警告で無視）。
    - 権限不足や未対応環境時の安全なフォールバック（警告ログ）を実装。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - シグナル選定（select_candidates）、等配分重み（calc_equal_weights）、スコア加重（calc_score_weights）を追加。
    - スコアが全て 0 の場合等、警告して等配分にフォールバック。

  - portfolio/risk_adjustment.py
    - セクター集中制限を適用する apply_sector_cap を追加（当日売却予定銘柄を除外、"unknown" セクターは制限除外）。
    - 市場レジームに基づく資金乗数 calc_regime_multiplier を追加（bull/neutral/bear、未知レジームは警告の上 1.0 にフォールバック）。

  - portfolio/position_sizing.py
    - 発注株数計算 calc_position_sizes を追加。
    - allocation_method に応じた計算（risk_based, equal, score）をサポート。
    - 単元株（lot_size）丸め、1銘柄上限、aggregate cap（available_cash を超える場合のスケーリング）、cost_buffer（保守的見積）や残差配分ロジックを実装。
    - 価格欠損時のスキップやログ出力などの安全措置を実装。

  - portfolio/__init__.py によるエクスポートを追加。

- ペーパートレード検証ツール
  - tools/paper_verification_report.py
    - ペーパートレード用 SQLite から稼働率・注文成功率・送信率・レイテンシ等を集計して標準出力でレポートを出力するスクリプトを追加。
    - デフォルト閾値（稼働率 99%、注文成功率 90%、送信率 95%、P95 レイテンシ 200 ms）を定義し PASS/FAIL 判定を行う。
    - 日付フィルタ、DB パス指定オプション（--from, --to, --db）をサポート。
    - latency の P95 計算、欠損データへの N/A 表示や SQL 実行エラー時の保護処理を実装。

- 研究用ファクター計算（骨格）
  - research/factor_research.py
    - DuckDB を用いた定量ファクター群（Momentum/Value/Volatility/Liquidity）計算モジュールの骨格を追加。各種窓長や計算方針の定数を定義。
    - 関数 calc_momentum の docstring と設計方針の一部を追加（実装継続予定）。

- データベース初期化
  - 監視用 DB 初期化関数 init_monitoring_db を参照して、起動時に監視テーブルの存在を保証する呼び出しを実装（monitoring 側に実装されていることを前提）。

### Changed
- （初版のため特筆すべき「変更」はありません。設計上の重要点を記載）
  - .env の自動読み込みはプロジェクトルートを基準に行い、OS の既存環境変数は保護される（.env/.env.local による上書き制御）。
  - logging_setup は stdout を StreamHandler に使用する設計（stderr ではなく stdout を用いることでジョブスケジューラ等での出力リダイレクトを容易にする）。

### Fixed
- （初版のため既存バグ修正の履歴はありませんが、堅牢化のための例外処理やフォールバック動作を各所に実装）
  - ログディレクトリ作成失敗やファイルハンドラ生成失敗時にプロセスが停止しないようフォールバック（コンソールのみ）を追加。
  - .env パース時のクォート内エスケープとインラインコメント、export プレフィックスなどを正しく処理するよう改善。

### Security
- 機密情報の取り扱いに関する配慮
  - config_setup の対話入力ではシークレット項目をマスク表示。
  - .env を生成するテンプレート内に「.env は絶対に Git にコミットしないこと」との注意書きを明記。

---

注:
- 本 CHANGELOG はソースコードからの推測に基づき作成されています。実際の変更履歴や運用上の決定と異なる可能性があります。必要に応じて修正・追記してください。