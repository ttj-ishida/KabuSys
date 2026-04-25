# Changelog

すべての注目すべき変更点をこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠します。

全体方針:
- セマンティックバージョニングを意識して記載しています。
- 重大な設計/挙動（デフォルト値や環境変数の重要な扱い）については注記します。

## [0.1.0] - 2026-04-25

### Added
- 初期リリース: KabuSys 自動売買システムのコアユーティリティと起動スクリプト群を追加。
- 起動スクリプト
  - run_execution.py
    - ExecutionEngine を起動するエントリポイントを提供。
    - KABUSYS_ENV=paper_trading の場合はペーパートレード用 MockBrokerClient を使用し、データは data/paper_trading.db（環境変数で上書き可）に分離して記録する。
    - 起動時にプロセス優先度を "high" に設定し、停止フラグ（data/stop_requested.flag）に応答して安全にシャットダウンする。
  - run_monitoring.py
    - SystemMonitor のポーリングループを起動。デフォルトポーリング間隔は 60 秒で、環境変数 MONITOR_POLL_INTERVAL で上書き可能。不正な値はデフォルトにフォールバックして警告を出す。
    - 監視は環境にかかわらず本番用の sqlite_path を使用する点を明示。
- 設定管理
  - config.py
    - .env ファイルの自動読み込み機能を提供（プロジェクトルートに基づく .env / .env.local の読み込み、OS 環境変数保護機能を実装）。
    - .env の行パーサはクォート（' "）、エスケープ、export プレフィックス、コメント処理等を堅牢に処理。
    - Settings クラスにより環境変数を型／意味付きプロパティとして扱う（DB パス、ログレベル、Paper Trading 周り、監視閾値など）。
  - config_setup.py
    - 対話式ウィザードで .env を初期作成・更新する CLI を追加。入力補助、既存 .env 読込、シークレットのマスク表示、確認プロンプト付き。
- 設定検証
  - validate_config.py
    - 起動前に環境変数や config/*.yaml の有無・内容をチェックする CLI を追加。--strict オプションで警告を FAIL 扱いにできる。
    - PyYAML がない場合は YAML 検証をスキップし、警告を出力。
- ロギング / プロセス制御ユーティリティ
  - utils/logging_setup.py
    - stdout への StreamHandler（標準出力）と日次ローテーション（TimedRotatingFileHandler）を用いたファイル出力をルートロガーに設定する共通ユーティリティを追加。
    - LOG_DIR / app_name / LOG_LEVEL で挙動を制御。ログディレクトリ作成失敗時はファイル出力をスキップして stdout のみで継続。
  - utils/process_priority.py
    - プラットフォーム差（Windows / POSIX）を吸収してプロセス優先度（high/normal/low）を設定するユーティリティを追加。
    - CPU affinity 設定ヘルパーも提供（set_cpu_affinity）。
- ポートフォリオ構築モジュール（純粋関数群、DB参照なし）
  - portfolio/portfolio_builder.py
    - 候補選定（select_candidates）、等重配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を追加。
  - portfolio/risk_adjustment.py
    - セクター上限チェック（apply_sector_cap）、市場レジームに基づく投下資金乗数（calc_regime_multiplier）を追加。未知レジームはフォールバックで 1.0。
  - portfolio/position_sizing.py
    - position sizing ロジック（risk_based / equal / score）を実装。単元株（lot_size）で丸め、個別上限・全体投下キャップ、cost_buffer を考慮したスケーリングロジックを実装。
    - aggregate cap 超過時のスケールダウンと残余キャッシュを用いた端数補正のアルゴリズムを実装。
- Paper Trading 検証ツール
  - tools/paper_verification_report.py
    - ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）から各種指標（稼働率、注文成功率、送信率、P95レイテンシ等）を集計し、PASS/FAIL 判定を行うレポート生成 CLI を追加。
    - デフォルトの閾値（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200ms）を定義。
- 研究用ファクター計算（初期実装）
  - research/factor_research.py
    - モメンタム等のファクター計算のための定数と、DuckDB を用いて計算を行う calc_momentum の枠組みを追加（実装は部分的 / 継続中）。

### Changed
- パッケージ初期化
  - __init__.py にてバージョンを "0.1.0" に設定。

### Fixed
- （該当する明示的なバグ修正はなし／初期リリースのため該当なし）

### Notes / Important behavior
- 監視（run_monitoring.py）は KABUSYS_ENV にかかわらず settings.sqlite_path（本番監視 DB）を使用します。環境による自動切り替えを期待している場合は注意してください。
- Execution 起動時は paper_trading 環境なら settings.paper_sqlite_path を使い、本番 DB と完全に分離してログを保持します。
- .env 自動読み込みはデフォルトで有効。自動ロードが不要なテスト等では環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して無効化できます。
- process_priority の設定は権限不足や未対応 OS の場合に失敗することがあり、その際は警告を出して処理を続行します。
- logging_setup はログディレクトリの作成に失敗した場合でも stdout ログは必ず出力します（ファイル出力のみ無効化）。

### Developers
- validate_config.py と config_setup.py により起動前の設定チェックと対話的セットアップが可能になりました。運用前はこれらを利用して .env と config/*.yaml の整合性を確認してください。
- portfolio モジュールは純粋関数で副作用がなくユニットテストが容易に書ける設計です。lot_size や cost_buffer 等のパラメータで動作を調整できます。

---

（将来のリリースでは各ファイルの変更差分・バグ修正・最適化を個別に記載します。）