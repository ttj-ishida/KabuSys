# CHANGELOG

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) に準拠しています。  
フォーマットは主に「Added / Changed / Fixed」カテゴリを使用しています。

## [0.1.0] - 2026-04-18 (Initial release)

初回リリース。ローカル開発からペーパートレード／本番運用までを想定した自動売買システムの基盤機能群を追加しました。

### Added
- 全体
  - パッケージ初期バージョン (kabusys v0.1.0) を追加。
  - パッケージ公開用の __version__ を設定。

- 設定管理 (`src/kabusys/config.py`)
  - .env 自動読み込み機能を導入（プロジェクトルートを .git または pyproject.toml で検出）。
  - .env パーサーの実装（export 付き行、クォート／エスケープ、行末コメントの取り扱いに対応）。
  - 環境変数保護（OS 環境変数を上書きしない）と上書きオプションのサポート。
  - Settings クラスを提供し、J-Quants / kabu API / DB パス / ログ設定 / 監視閾値等のプロパティを型付きで取得・検証する API を追加。
  - PAPER_FILL_MODE のバリデーション（許容値: "instant" | "partial" | "never" | "reject"）。
  - KABUSYS_ENV / LOG_LEVEL の検証ロジックを実装（不正値で ValueError）。

- 環境設定ウィザード (`src/kabusys/config_setup.py`)
  - 対話式 CLI による .env の初期作成・更新ウィザードを追加。
  - シークレット項目のマスク表示、デフォルト値の提示、生成される .env のテンプレート出力をサポート。
  - `--env-file` オプションで出力先指定可能。

- 設定検証 CLI (`src/kabusys/validate_config.py`)
  - .env と config/*.yaml の起動前検証ツールを追加。
  - 必須/任意環境変数チェック、KABUSYS_ENV の妥当性チェック、DB パスの親ディレクトリ確認、PyYAML が無い場合のスキップといった検証を実装。
  - KABUSYS_ENV=live 時の追加ガードチェック（LINE 通知の設定確認、KILL_FLAG_CLEAR_ON_START の警告）を追加。
  - `--strict` オプションで警告も失敗扱いにできる。

- 起動スクリプト
  - 実行エンジン起動 (`src/kabusys/run_execution.py`)
    - ExecutionEngine を起動するためのスクリプトを追加。
    - 起動時にプロセス優先度を "high" に設定する呼び出しを導入。
    - KABUSYS_ENV=paper_trading の場合は専用の SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB と分離。
    - BrokerClientFactory を用いたブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組立て、および ExecutionEngine のスレッド実行・停止ハンドリングを実装。
    - 停止フラグ (data/stop_requested.flag) と PID ファイル (data/execution.pid) を使用した制御を追加。

  - 監視ループ起動 (`src/kabusys/run_monitoring.py`)
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL によるポーリング間隔上書きをサポート（デフォルト 60 秒、無効値はデフォルトにフォールバック）。
    - 監視は環境に関わらず本番用 sqlite_path を使用する実装（監視 DB を分離しない設計の旨明記）。
    - 停止フラグによるループ終了と例外ハンドリングを実装。

- ロギングユーティリティ (`src/kabusys/utils/logging_setup.py`)
  - 共通化したログ設定関数 setup_logging を追加。
  - stdout への StreamHandler と日次ローテーションする TimedRotatingFileHandler（デフォルト logs/、30日保存）をルートロガーに設定。
  - LOG_LEVEL / LOG_DIR 環境変数との連携、既存ハンドラのクリーンアップ、ログディレクトリ作成失敗時のフォールバックを実装。

- プロセス優先度ユーティリティ (`src/kabusys/utils/process_priority.py`)
  - 複数プラットフォーム（Windows / POSIX）対応でプロセス優先度を設定する set_process_priority を追加。
  - CPU affinity を設定する set_cpu_affinity を追加。
  - psutil を利用し、権限不足や未対応プラットフォームでは警告を出してスキップする堅牢性を確保。

- ポートフォリオ構築モジュール (`src/kabusys/portfolio/`)
  - 銘柄選定と重み付け (`portfolio_builder.py`)
    - select_candidates: スコア降順＋タイブレークで上位 N を選択。
    - calc_equal_weights / calc_score_weights: 等金額配分とスコア比率配分（スコアが全て 0 の場合は等配分へフォールバック）。
  - セクター制限・レジーム調整 (`risk_adjustment.py`)
    - apply_sector_cap: 既存保有のセクター比率が上限を超える場合に当該セクターの新規候補を除外。
    - calc_regime_multiplier: market regime に基づく投下資金乗数（bull/neutral/bear）を実装。未知レジームはデフォルト 1.0 にフォールバック（警告出力）。
  - 株数決定ロジック (`position_sizing.py`)
    - 単元株（lot）丸め、risk_based / equal / score の割当方式対応。
    - 1銘柄上限、aggregate cap（利用可能現金を超える場合のスケールダウン）、cost_buffer を考慮した保守的コスト見積り。
    - スケールダウン後の端数処理（lot 単位）を残差優先で再配分するロジックを実装。
    - 設計上の注意点と将来の拡張（銘柄別 lot_size）に関する TODO コメントを追加。

- Paper Trading 検証ツール (`src/kabusys/tools/paper_verification_report.py`)
  - ペーパートレード用 SQLite を集計して検証レポートを生成するスクリプトを追加。
  - システム稼働率、注文成功率（fill/send）、リスク却下数、API レイテンシ（avg/max/P95）を算出。
  - P95 算出、日付フィルタ（--from / --to）、DB パスのオーバーライドオプション（--db / 環境変数）をサポート。
  - デフォルトの合格基準（稼働率 99% 等）を設定し、PASS/FAIL を出力。

- 研究用ファクター計算（着手） (`src/kabusys/research/factor_research.py`)
  - モメンタム等のファクター計算モジュールを追加（設計と定数の定義、calc_momentum の実装開始）。
  - DuckDB を使った prices_daily / raw_financials 参照前提での設計。現時点で calc_momentum の実装は途中（未完）である旨を注記。

### Changed
- ログ出力の統一
  - 各起動スクリプトから setup_logging を呼び出すことでログ出力設定を統一。
- 起動時プロセス優先度の標準化
  - 重要処理（monitoring / execution）の最初に set_process_priority("high") を呼び出すことで挙動を明示化。

### Fixed / Robustness
- 環境変数の安全性向上
  - .env の読み込みはプロジェクトルート検出に依存し、CWD に依存しないよう改善。
  - 自動読み込みを無効にする KABUSYS_DISABLE_AUTO_ENV_LOAD を追加（テスト用途）。
  - .env パーサーの不正な行やクォートの扱いについて堅牢化し、誤った .env によるクラッシュを回避。
- MONITOR_POLL_INTERVAL の不正値に対して警告しデフォルトにフォールバックする処理を実装（time.sleep の ValueError 回避）。
- logging_setup: ログディレクトリ作成失敗時にファイルハンドラをスキップしてコンソールのみで継続する保護処理追加。
- process_priority: 権限不足や未対応 OS の場合に例外を握り潰し警告を出すことで起動失敗を回避。

### Known issues / Notes
- research/factor_research.calc_momentum の実装は途中でファイル末尾が未完です。ファクター計算まわりは今後の実装・テストが必要です。
- 一部の TODO コメント（例: position_sizing の銘柄別 lot_size サポート、risk_adjustment の価格欠損時のフォールバック）は将来的な改善ポイントとして残っています。
- run_monitoring は「監視は本番 sqlite_path を使用する」と明記されています。監視データを完全に分離したい場合は設定上の工夫（別 sqlite パスを指定）を行ってください。
- Paper Trading と本番の DB 分離は run_execution 側で行われますが、その他コンポーネントでも誤って本番 DB にアクセスしないよう注意してください。

---

今後のリリースでは以下を予定しています（例）:
- factor_research の完実装とユニットテスト追加
- ExecutionEngine / SystemMonitor 周りの E2E テスト、モッククライアントの整備
- 監視とアラート（LINE）連携の実装強化
- 各モジュールの型注釈・ドキュメント拡充およびベンチマーク

（必要であれば、上記の各項目について変更差分の詳細や該当するソースファイル行の抜粋を付けて追記します。）