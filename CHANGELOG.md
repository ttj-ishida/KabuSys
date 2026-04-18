# Changelog

すべての変更は Keep a Changelog 準拠で記載しています。  
https://keepachangelog.com/ja/1.0.0/

## [Unreleased]

## [0.1.0] - 2026-04-18
初回リリース

### Added
- 実行用スクリプトを追加
  - run_execution.py
    - ExecutionEngine を起動するエントリポイント。
    - KABUSYS_ENV が `paper_trading` の場合は paper_trading 用の SQLite（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）を使用して本番 DB と完全分離。
    - BrokerClientFactory を用いて適切なブローカークライアント（実口座 / Mock）を生成。
    - Engine の起動・停止をデーモンスレッドで実行し、 data/stop_requested.flag による外部停止に対応。
    - 起動直後にプロセス優先度を "high" に設定。
  - run_monitoring.py
    - SystemMonitor のポーリングループを起動するエントリポイント。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバック。
    - 監視は環境に依らず本番の sqlite_path を使用する設計（monitoring 用テーブルを本番 DB に保存）。
    - data/stop_requested.flag を検知して安全にループを終了。
- 設定管理・初期化ツール
  - config.py
    - 環境変数管理を集中化した `Settings` クラスを実装。
    - プロジェクトルート（.git または pyproject.toml）を基準に自動で .env/.env.local を読み込む自動ロード機能（`KABUSYS_DISABLE_AUTO_ENV_LOAD` で無効化可能）。
    - 多数の環境変数プロパティ化（J-Quants, kabuAPI, DB パス, Paper Trading 関連, 監視閾値, PID/kill フラグパス, ログレベルなど）。
    - `PAPER_FILL_MODE` 等の値検証（不正値は ValueError）。
  - config_setup.py
    - .env を対話式に作成・更新するウィザード。
    - シークレット項目はマスク表示、既存値の再利用、選択肢/デフォルトのサポート、保存前の確認を提供。
  - validate_config.py
    - 起動前に .env と config/*.yaml を検証する CLI。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ確認、config/*.yaml の存在・パース検証（PyYAML が無ければパース検証をスキップして警告）。
    - `--strict` モードで警告も失敗として扱う。
- ロギング / プロセス制御ユーティリティ
  - utils/logging_setup.py
    - 全起動スクリプトで共通利用できるログ設定ユーティリティを追加。
    - stdout へ StreamHandler、日次ローテートの TimedRotatingFileHandler（デフォルト logs/<app_name>.log、30 日保持）を設定。
    - ログディレクトリ作成失敗時にはファイル出力をスキップしてコンソール出力のみで動作。
    - ログレベルの解決順（引数 > 環境変数 LOG_LEVEL > デフォルト）。
  - utils/process_priority.py
    - Windows と POSIX を吸収するプロセス優先度設定 API（`set_process_priority`）。
    - CPU アフィニティ固定用 `set_cpu_affinity` を追加。
    - 権限不足や未対応 OS の場合は安全に警告を出してスキップ。
- ポートフォリオ構築関連（純粋関数群）
  - portfolio/portfolio_builder.py
    - BUY シグナル選定関数 `select_candidates`（スコア降順、同点は signal_rank でブレーク）。
    - `calc_equal_weights`, `calc_score_weights`（スコアが全て 0 の場合は等金額配分にフォールバックして警告）。
  - portfolio/risk_adjustment.py
    - `apply_sector_cap`：既存保有のセクター比率が上限を超える際に同セクターの新規候補を除外。
      - "unknown" セクターは上限適用対象外。
      - 当日売却予定銘柄をエクスポージャー計算から除外可能。
    - `calc_regime_multiplier`：市場レジーム（bull/neutral/bear）に応じた投下資金乗数（不明な値は警告して 1.0 にフォールバック）。
  - portfolio/position_sizing.py
    - `calc_position_sizes`：複数の配分方式（risk_based / equal / score）に対応して発注株数を計算。
    - 単元株（lot_size）丸め、1銘柄上限 (max_position_pct)、aggregate cap（available_cash）によるスケーリング、cost_buffer を加味した保守的なコスト見積りを実装。
    - スケールダウン時に残差を考慮した lot 単位の追加配分ロジックを導入して再現性確保。
- Paper Trading 検証ツール
  - tools/paper_verification_report.py
    - ペーパートレード用 SQLite（PAPER_TRADING_SQLITE_PATH）から各種指標（稼働率、注文成功率、送信率、リスク却下数、レイテンシ（平均/最大/P95））を集計してレポートを出力する CLI を追加。
    - デフォルト閾値（稼働率 99%, 成立率 90% 等）と Pass/Fail 形式の判定を実装。
    - 日付フィルタ（--from/--to）と DB パス指定（--db）をサポート。
- monitoring と DB 初期化
  - init_monitoring_db の呼び出しをスクリプト起動時に行い、監視テーブル群が存在することを冪等的に保証。

### Changed
- パッケージ情報
  - パッケージバージョンを __version__ = "0.1.0" として定義。
- ログ出力先のポリシー
  - StreamHandler を stdout に固定（stderr ではない）――cron/Task Scheduler の運用を意識した設計。

### Fixed
- （該当なし／初回リリースのため特定のバグ修正履歴はなし）

### Deprecated
- （該当なし）

### Removed
- （該当なし）

### Security
- （該当なし）

注:
- 各モジュールの実装は大部分が純粋関数あるいは DI（依存注入）設計に基づき、テスト容易性と本番/ペーパートレード分離を意識して実装されています。
- 設定の自動ロード・検証機能により、デプロイ前に環境変数や設定ファイルの不備を検出しやすくなっています。