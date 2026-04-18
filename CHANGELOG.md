# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠しています。  
非破壊的なバージョンは semver を想定します。

現在のバージョン: 0.1.0 — 初期リリース（2026-04-18）

## [Unreleased]

（未リリースの変更はここに記載します）

---

## [0.1.0] - 2026-04-18

初回リリース。日本株自動売買システム KabuSys の基盤となる CLI、設定管理、監視・実行ランナー、ポートフォリオ構成ロジック、ユーティリティ、分析ツール等を追加しました。

### Added
- 基本パッケージ情報
  - パッケージバージョンを `src/kabusys/__init__.py` にて `0.1.0` として追加。

- 実行・監視ランナー
  - run_execution: `src/kabusys/run_execution.py`
    - ExecutionEngine の起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は専用の paper_trading SQLite DB（既定: data/paper_trading.db）を使用し、本番 DB と分離。
    - BrokerClientFactory を用いたブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組立てと実行スレッド管理を実装。
    - 停止制御はプロジェクト root の data/stop_requested.flag による（停止フラグ検知で安全に停止）。
    - PID ファイル管理（data/execution.pid）とプロセス優先度設定を実行開始時に行う。
  - run_monitoring: `src/kabusys/run_monitoring.py`
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番用 sqlite_path を使用（監視 DB 初期化処理を実行）。
    - 停止フラグ（data/stop_requested.flag）でループ終了。

- 設定管理
  - Settings クラス: `src/kabusys/config.py`
    - .env 自動読み込み機能（プロジェクトルートを .git / pyproject.toml で検出）。
    - OS 環境変数優先、.env / .env.local の読み込み順序と上書きポリシー（.env.local は上書き可能だが OS 環境変数は保護）。
    - 強力な .env パーサを実装（export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、行内コメントの扱いを考慮）。
    - 多数の設定プロパティ（J-Quants / kabuステーション / DB パス / 監視閾値 / 環境種別判定など）。
    - PAPER_FILL_MODE のバリデーション（instant/partial/never/reject）。
  - 設定ウィザード CLI: `src/kabusys/config_setup.py`
    - 対話式ウィザードで .env の初期作成・更新を支援。
    - デフォルト値、選択肢、秘密値マスク、保存確認機能を実装。
    - .env の読み書き（既存値の読み込みと上書き制御）。

- 設定検証ツール
  - validate_config CLI: `src/kabusys/validate_config.py`
    - .env と config/*.yaml の検証を行うコマンドラインツールを追加。
    - 必須環境変数チェック、KABUSYS_ENV の妥当性、LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在確認、YAML パース（PyYAML がある場合）を実施。
    - 本番環境向けの追加警告（LINE 設定、KILL_FLAG_CLEAR_ON_START の危険性など）。
    - --strict モード（警告も失敗扱いで exit(1)）。

- ポートフォリオ構成モジュール
  - portfolio_builder: `src/kabusys/portfolio/portfolio_builder.py`
    - シグナルのソーティング（score 降順、tie-break に signal_rank）と候補選定機能 select_candidates。
    - 等配分 calc_equal_weights、スコア加重 calc_score_weights（全スコア 0 の場合は等配分にフォールバック）。
  - risk_adjustment: `src/kabusys/portfolio/risk_adjustment.py`
    - セクター集中制限を適用する apply_sector_cap（売却予定銘柄の除外、unknown セクターは制限を適用しない）。
    - 市場レジームに応じた投下資金乗数 calc_regime_multiplier（bull/neutral/bear のマッピング、未知レジームは警告の上で 1.0 フォールバック）。
  - position_sizing: `src/kabusys/portfolio/position_sizing.py`
    - allocation_method ("risk_based", "equal", "score") に基づく株数計算機能 calc_position_sizes を実装。
    - 単元株（lot_size）丸め、個別上限（max_position_pct）、投下資金合計の aggregate cap、cost_buffer（手数料・スリッページ見積り）によるスケーリングをサポート。
    - risk_based 方式では risk_pct / stop_loss_pct に基づくポジションサイズ計算。
    - 価格欠損時のログとスキップ処理、スケールダウン時の残差処理（lot 単位での追加配分）を実装。

- 研究・因子計算
  - factor_research: `src/kabusys/research/factor_research.py`
    - DuckDB 接続を利用したモメンタム / ボラティリティ等のファクター計算を実装。
    - calc_momentum、calc_volatility（ATR / 20日平均売買代金 / ボラティリティ指標など）を実装。ウィンドウ不足時は None を返す設計。

- ツール
  - paper_verification_report: `src/kabusys/tools/paper_verification_report.py`
    - ペーパートレード用 SQLite DB を参照して検証レポートを生成する CLI を追加。
    - システム稼働率、注文成功率・送信率、リスク却下数、レイテンシ（平均・最大・P95）等を算出し、Pass/Fail 判定（閾値はソースに定義）を出力。
    - 日付フィルタ（--from / --to）と DB パス指定オプションをサポート。

- ユーティリティ
  - process_priority: `src/kabusys/utils/process_priority.py`
    - Windows / POSIX（Linux, macOS, FreeBSD）間の差分を吸収するプロセス優先度設定ユーティリティを追加。
    - set_process_priority(level) で high/normal/low を設定可能。権限不足等の失敗は警告でスキップ。
    - set_cpu_affinity(cpu_count) によりプロセスを最初の N コアにピン留め（サポートのない OS は警告）。
  - パッケージ初期化やツール __init__ を追加（tools, utils など）。

- DB 初期化
  - 監視用 DB 初期化呼び出し `init_monitoring_db` を monitoring 起動時・実行起動時に冪等に実行。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- 環境ファイル生成時に .env を Git にコミットしないよう明示（config_setup の出力ヘッダ）。
- シークレット値入力時は表示をマスク。

### Notes / Implementation details / 動作上の重要点
- run_monitoring は「監視専用」に設計されており、KABUSYS_ENV にかかわらず監視用 DB 初期化で指定された sqlite_path を使用します（監視が必ず本番監視 DB を対象とする設計を意図）。
- run_execution は paper_trading と live を明確に分離。paper_trading は MockBrokerClient と paper_trading.db により本番 DB と完全分離された動作を行います。
- .env 自動読み込みはデフォルトで有効。自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD を 1 に設定してください（テスト用途など）。
- 設定検証ツールは PyYAML が未インストールでも動作し、YAML 内容検証はスキップされます（警告を出力）。
- position_sizing のスケーリング処理や price の欠損時挙動には注意（ログに TODO コメントあり）。将来的な拡張（銘柄別 lot_size 等）を想定。

---

開発・利用に関する問い合わせやバグ報告はリポジトリの Issue にお願いします。