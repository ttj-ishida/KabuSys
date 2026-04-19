# Changelog

すべての注目すべき変更をここに記録します。  
フォーマットは「Keep a Changelog」に準拠します。  

現在のリリース情報はパッケージ版の初期公開としてまとめています。

## [Unreleased]

## [0.1.0] - 2026-04-19
初回リリース。日本株自動売買システム「KabuSys」のコアユーティリティ、実行/監視スクリプト、設定ツール、ポートフォリオ構築・サイズ計算ロジック、ペーパートレード検証ツールなどを追加。

### Added
- 基本メタ情報
  - パッケージバージョンを `__version__ = "0.1.0"` として追加。

- 起動スクリプト
  - `src/kabusys/run_execution.py`
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合はペーパートレード用 DB（既定: data/paper_trading.db）を使用し、MockBrokerClient を利用可能にする設計（BrokerClientFactory 経由）。
    - プロセス優先度を High に設定する処理を実行開始時に呼び出す。
    - 停止フラグ（data/stop_requested.flag）を監視し、検出時に安全にエンジンを停止する。
    - PID ファイル（data/execution.pid）を使用。

  - `src/kabusys/run_monitoring.py`
    - SystemMonitor 用ポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正な値はデフォルトにフォールバックし警告を出力。
    - 監視は環境に関わらず本番用の sqlite_path を使用して DB に接続する（Settings.sqlite_path）。
    - 停止フラグ（data/stop_requested.flag）を検知してループを終了。

- 設定・設定関連ユーティリティ
  - `src/kabusys/config.py`
    - .env 自動ロード機能を追加（プロジェクトルートを .git または pyproject.toml から検出）。
    - .env の読み込み順: OS 環境変数 > .env.local > .env。`KABUSYS_DISABLE_AUTO_ENV_LOAD` で自動読み込みを無効化可能。
    - .env パーサーは export プレフィックス、クォート値、インラインコメントなどに対応。
    - Settings クラスを導入し、環境変数に対するプロパティアクセスを提供（各種デフォルト、バリデーションを含む）。
      - J-Quants / kabu API 関連、DuckDB/SQLite パス、paper_trading 用 DB パス、PAPER_FILL_MODE の妥当性チェックなど。
      - 監視閾値（CPU/MEM/DISK）やログレベル、実行環境判定（development/paper_trading/live）等を提供。
  - `src/kabusys/config_setup.py`
    - 対話式 .env 作成ウィザードを追加。主要な環境変数を対話で入力・更新できる。
    - 既存 .env の読み込み、既存値の再利用、シークレット項目のマスク表示、最終確認の後ファイルを書き出す機能。
  - `src/kabusys/validate_config.py`
    - 起動前に .env や config/*.yaml を検証する CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV の妥当性、ログレベル、DB パスの親ディレクトリ存在確認、YAML パース（PyYAML があれば内容検証）などを実行。
    - `--strict` オプションで警告を FAIL 扱いにできる。

- ロギング / プロセス制御ユーティリティ
  - `src/kabusys/utils/logging_setup.py`
    - 全起動スクリプトで共通利用するログ設定ユーティリティを追加。
    - stdout 出力の StreamHandler と 日次ローテート（TimedRotatingFileHandler）をルートロガーに設定。ログディレクトリの自動作成、既存ハンドラのクリーンアップ、環境変数/引数からの設定をサポート。
  - `src/kabusys/utils/process_priority.py`
    - Windows / POSIX を抽象化したプロセス優先度設定ユーティリティを追加（set_process_priority, set_cpu_affinity）。
    - 権限エラー等は警告でフォールバックする実装。

- ポートフォリオ構築関連（純粋関数群）
  - `src/kabusys/portfolio/portfolio_builder.py`
    - 信号の候補選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を追加。
  - `src/kabusys/portfolio/risk_adjustment.py`
    - セクター集中制限を適用する apply_sector_cap、マーケットレジームに基づく投下資金乗数 calc_regime_multiplier を追加。
    - 未知レジーム時のフォールバック、"unknown" セクターの扱いなどの設計上の注意点をコメントで明記。
  - `src/kabusys/portfolio/position_sizing.py`
    - allocation_method ("risk_based", "equal", "score") に応じた発注株数計算ロジックを追加。
    - 単元株（lot_size）丸め、per-position および aggregate cap のスケーリング（available_cash に基づくスケールダウン）、cost_buffer（手数料・スリッページ見積）を考慮。
    - スケーリング時の remainder 分配アルゴリズムを実装（lot_size 単位での追加配分を残差順に行う）。
  - `src/kabusys/portfolio/__init__.py` で主要関数をエクスポート。

- ペーパートレード検証
  - `src/kabusys/tools/paper_verification_report.py`
    - ペーパートレード用 SQLite データベース（デフォルト: data/paper_trading.db）から各種指標を集計し、期間レポートを出力する CLI を追加。
    - 指標: 稼働率（system_status）、注文成功率・送信率（trade_logs）、リスク却下数（risk_logs）、API レイテンシ（平均/最大/P95）など。
    - パス/期間フィルタの指定、閾値（稼働率99%、成功率等）に基づく PASS/FAIL 判定ロジックを実装。
  - `src/kabusys/tools/__init__.py` を追加（tools パッケージ化）。

- リサーチ / ファクター計算（初期実装）
  - `src/kabusys/research/factor_research.py`
    - DuckDB 接続を受けてファクター（Momentum / Value / Volatility / Liquidity）を計算するための構造を追加。
    - モメンタム計算（1M/3M/6M、MA200乖離）の設計／定数を導入（関数 calc_momentum を実装開始）。
    - DuckDB の prices_daily / raw_financials テーブルを前提とした計算方針。

### Changed
- プロジェクトの設定読み込みポリシー
  - .env 自動読み込みをプロジェクトルート検出に基づいて行うように変更（CWD に依存しない）。

### Fixed
- （このリリースは初期追加のため修正履歴は無し）

### Removed
- （なし）

### Deprecated
- （なし）

### Security
- （なし）

---

## Notes / Known issues / TODO
- factor_research.calc_momentum の実装は途中（ソース末尾が途切れている・未完成）。リサーチ機能は今後の追加実装が必要。
- position_sizing.py:
  - 銘柄ごとの単元数（lot_size）を現状はグローバル固定（デフォルト 100）で扱っている。将来的には銘柄別 lot_map をサポートする予定（TODO コメントあり）。
  - open_prices に欠損（0.0）があると exposure が過少見積になる可能性あり。フォールバック価格（前日終値や取得原価）を検討する旨の TODO が残る。
- apply_sector_cap:
  - sector_map に存在しないコードは "unknown" 扱いで上限チェック対象外となるため、マスタ未整備時に期待どおりの制約にならないことがある。
- process_priority / set_cpu_affinity:
  - 実行プラットフォームや権限（root/管理者）により設定に失敗する可能性がある。失敗時は警告を出してスキップする実装になっている。
- run_monitoring:
  - MONITOR_POLL_INTERVAL に不正値（0 以下や数値以外）が設定された場合はログ警告のうえデフォルト（60 秒）にフォールバックする。
- validate_config:
  - PyYAML が未インストールの場合は YAML パースによる設定検証をスキップし警告を出す。

必要であれば、各セクション（起動方法、環境変数の一覧、CLI 使用例、今後のロードマップ等）を詳細に追記します。どの情報を優先して追加しますか？