# Changelog

すべての注目すべき変更点を記録します。フォーマットは「Keep a Changelog」に準拠しています。

なお、この CHANGELOG はリポジトリ内のソースコードから機能・挙動を推測して作成しています。

## [Unreleased]

（現在リリースされているバージョン以降の変更をここに記載します）

---

## [0.1.0] - 2026-04-18

初回リリース。日本株自動売買システム「KabuSys」の基礎機能を提供します。

### Added
- 実行用エントリースクリプトを追加
  - run_execution.py
    - ExecutionEngine を起動する CLI スクリプト。
    - KABUSYS_ENV が `paper_trading` の場合は Paper Trading 用の専用 SQLite を使用して本番 DB と完全に分離（デフォルト: data/paper_trading.db）。
    - 起動時にプロセス優先度を "high" に設定。
    - 停止フラグ (data/stop_requested.flag) と PID ファイル (data/execution.pid) を用いた安全な起動/停止制御をサポート。
    - 依存コンポーネント（BrokerClient, OrderRepository, OrderManager, RiskManager, Reconciler, ExecutionEngine）の組み立てと実行スレッド管理を実装。
- 監視用エントリースクリプトを追加
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。
    - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL` で上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバック。
    - 停止フラグ (data/stop_requested.flag) を検知して安全にループ終了。
    - Monitoring は環境にかかわらず本番 sqlite_path を使用して監視テーブルにアクセス。
- 設定管理
  - config.py
    - .env 自動読込機能（プロジェクトルートを .git または pyproject.toml から検出）。
    - .env / .env.local の読み込み順序（OS 環境変数を保護）と KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化。
    - 各種設定プロパティ（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DB パス、PID ファイルパス、監視閾値、環境判定プロパティ等）を提供。
    - PAPER_FILL_MODE のバリデーション（"instant"|"partial"|"never"|"reject"）。
    - KABUSYS_ENV / LOG_LEVEL のバリデーション。
- 設定関連 CLI
  - config_setup.py
    - .env を対話式に作成・更新するウィザード。
    - シークレット項目はマスク表示、デフォルトの反映、書き込みヘッダの生成をサポート。
  - validate_config.py
    - .env と config/*.yaml の事前検証ツール。
    - 必須環境変数チェック・KABUSYS_ENV の妥当性・DB パスや YAML ファイルの存在・本番環境に対する追加ガードを実装。
    - --strict フラグで警告も失敗扱いにできる。
- ログ/プロセスユーティリティ
  - utils/logging_setup.py
    - ルートロガーに StreamHandler (stdout) と TimedRotatingFileHandler（日次ローテーション、30日保持）を設定するユーティリティ。
    - ログディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソールのみで継続。
    - 既存ハンドラを一旦クリアして二重出力を防止。
  - utils/process_priority.py
    - Windows と POSIX（Linux/Mac 等）を吸収するプロセス優先度設定 (high/normal/low)。
    - CPU affinity を最初の N コアに固定する関数 set_cpu_affinity を提供。
    - 権限不足などの場合は警告を出してフォールバック。
- ポートフォリオ構築モジュール
  - portfolio/portfolio_builder.py
    - シグナルからの候補選定（スコア降順、タイブレークに signal_rank）。
    - 等金額配分、スコア加重配分（全銘柄スコアが 0 の場合は等配分にフォールバック）。
  - portfolio/risk_adjustment.py
    - セクター集中制限（apply_sector_cap）。既存ポジションおよび価格マップを元にセクター別エクスポージャーを算出して新規候補を除外。
    - レジーム乗数 calc_regime_multiplier（bull/neutral/bear に対応、未知は警告のうえ 1.0 にフォールバック）。
  - portfolio/position_sizing.py
    - 発注株数決定ロジック（risk_based / equal / score）。
    - 単元株（lot_size）で丸め、1 銘柄上限や aggregate cap に基づくスケーリング、残差処理（端数の優先配分）を実装。
    - cost_buffer による保守的コスト見積りを考慮。
- 研究用ファクターモジュール（計算ロジック）
  - research/factor_research.py
    - Momentum、MA200、ATR、出来高系などを計算するための定数と関数群（DuckDB 接続を受け取って prices_daily 等を参照する設計）。
    - （注）ファイルは途中まで含まれているが、設計方針と計算対象は明示。
- Paper Trading 検証ツール
  - tools/paper_verification_report.py
    - Paper Trading 用 SQLite から稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）などを集計してレポート出力。
    - デフォルト閾値（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200 ms）を定義し、PASS/FAIL 判定を行う。
    - 日付フィルタと --db オプションをサポート。
- パッケージ初期化
  - __init__.py にバージョン __version__ = "0.1.0" を追加。

### Changed
- ロギングの標準出力先を stderr ではなく stdout に統一
  - cron やタスクスケジューラで stdout/stderr のリダイレクトを想定した設計。
- .env 読み込みの挙動
  - export KEY=val 形式、クォート文字・エスケープ、インラインコメント（スペースの有無に応じた取り扱い）に対応した独自パーサを実装。
  - .env.local を .env より後に上書き読み込み（OS 環境変数は protected）。

### Fixed / Robustness
- DB 初期化の冪等性確保
  - run_execution.py/run_monitoring.py で起動時に init_monitoring_db を呼び出し、監視用テーブルの存在を保証（存在していれば安全にスキップ）。
- 監視ループの例外耐性
  - monitor.check_once() 実行時の未捕捉例外を logger.exception() で記録し、次ポーリングへ継続するように変更。
- ログハンドラ重複防止
  - setup_logging() が既存ハンドラを一度 flush/close してから削除することで、複数回呼び出した際の二重出力を防止。
- 設定検証のフォールバックメッセージ
  - validate_config.py は PyYAML 未インストール時に YAML 検証をスキップして警告を出すように変更（依存無しでも動く）。
- プロセス優先度／CPU affinity の失敗に対するフォールバック
  - 権限不足や未サポート OS の場合、例外ではなく警告を出してスキップするようにして起動を安定化。

### Documentation / Developer Notes
- config_setup.py のウィザードで生成される .env のヘッダに注意書きを追加（.env を絶対に Git にコミットしないこと）。
- portfolio モジュールの関数は副作用のない純粋関数として設計（DB 参照なし）。将来的な拡張箇所に TODO コメントを残す（例: 銘柄別 lot_size の導入、価格フォールバックの改善）。

---

今後の予定（例: 想定）
- factor_research.py の完全実装（ファクター計算ロジックの完成と単体テスト追加）
- ExecutionEngine / SystemMonitor の統合テスト、エンドツーエンドのペーパートレード検証
- CLI ドキュメントの拡充、example .env の追加

（必要であれば、この CHANGELOG を追記修正してリリース履歴を細分化できます。）
