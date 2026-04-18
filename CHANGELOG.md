# Changelog

すべての重要な変更は Keep a Changelog (https://keepachangelog.com/ja/1.0.0/) の形式に従って記載します。

以下はリポジトリの現状ソースコードから推測して作成した初期リリースの変更履歴です。

## [Unreleased]

(現時点で未リリースの変更はありません)

## [0.1.0] - 2026-04-18

### Added
- 全体
  - パッケージ初期リリース (バージョン 0.1.0)。
  - Python モジュール群を提供:
    - 実行・監視起動スクリプト: run_execution.py, run_monitoring.py
    - 環境設定・検証: config_setup.py, validate_config.py, config.py
    - ポートフォリオ構築: portfolio/*.py（銘柄選定、重み計算、リスク調整、株数決定）
    - 実行ユーティリティ: execution パッケージ（Engine / OrderManager 等を組み立てる起点）
    - 解析ツール: tools/paper_verification_report.py（ペーパートレード用検証レポート生成）
    - 研究用: research/factor_research.py（ファクター計算の骨格と定数）
    - 汎用ユーティリティ: utils/logging_setup.py, utils/process_priority.py

- 環境・設定
  - .env 自動読み込み機能を実装（プロジェクトルートを .git / pyproject.toml から検出）。
  - .env のパースは以下に対応:
    - export KEY=val 形式
    - シングル／ダブルクォート内でのバックスラッシュエスケープ処理
    - クォートなし行のインラインコメント（前にスペースがある `#` をコメントとして扱う）
  - 環境変数自動ロードを無効化するフラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - Settings クラスを提供し、アプリ設定をプロパティ経由で取得可能（DBパス、API設定、監視閾値、環境種別など）。
  - 対話式ウィザード (config_setup.py) により .env の生成・更新を支援。秘密値はマスク表示。

- 実行 / 監視
  - run_execution:
    - KABUSYS_ENV に応じて paper_trading 用 DB と Mock ブローカを利用し、本番 DB と分離。
    - ExecutionEngine の起動ロジック、スレッド化、停止フラグ (data/stop_requested.flag) による安全停止、PID ファイル管理を実装。
    - RiskManager のデフォルト設定 (max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker など) を組み込む。初期ポートフォリオ値は broker.get_available_cash() から取得。
  - run_monitoring:
    - SystemMonitor を定期実行するポーリングループを実装。MONITOR_POLL_INTERVAL 環境変数で間隔を上書き可能（デフォルト 60 秒）。ポーリング値が無効な場合はデフォルトにフォールバック。
    - 監視は環境にかかわらず本番の sqlite_path を使用する設計（監視データは共通 DB を想定）。
    - stop フラグ検知でループ終了。KeyboardInterrupt による終了処理も考慮。
  - 両スクリプトとも起動時にプロセス優先度を "high" に設定するユーティリティ呼び出しを行う。

- DB / 分析
  - SQLite と DuckDB の両接続を利用する実装（init_monitoring_db を呼び出し監視テーブルを冪等に初期化）。
  - duckdb の接続パスを Settings から取得。

- ロギング / プロセス制御
  - 統一ロギング設定ユーティリティ (utils/logging_setup.py):
    - stdout への StreamHandler と日次ローテートの TimedRotatingFileHandler（デフォルト logs/<app_name>.log、30日保持）を自動設定。
    - LOG_DIR/LOG_LEVEL の環境変数や引数で上書き可能。ログディレクトリ作成失敗時はファイル出力をスキップして警告。
    - 既存ハンドラを安全に閉じてから再設定することで二重設定を回避。
  - プロセス優先度 / CPU affinity ユーティリティ (utils/process_priority.py):
    - Windows, POSIX (Linux/Mac/FreeBSD) を抽象化して優先度設定を試行。権限や未対応プラットフォーム時には警告を発するフェイルセーフ。
    - CPU コアを限定する set_cpu_affinity の提供（利用可能コア数チェック、エラー時は警告）。

- ポートフォリオ構築ロジック
  - portfolio.portfolio_builder:
    - select_candidates: スコア降順かつ signal_rank によるタイブレークで候補選定。
    - calc_equal_weights / calc_score_weights: 等金額配分・スコア正規化配分（全スコアが 0 の場合は等金額にフォールバック）。
  - portfolio.risk_adjustment:
    - apply_sector_cap: セクター別既存保有比率が上限を超える場合に当該セクターの新規候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: market regime による投下資金乗数 (bull=1.0, neutral=0.7, bear=0.3)。未知レジームは 1.0 でフォールバック。
  - portfolio.position_sizing:
    - calc_position_sizes: risk_based / equal / score の各配分方式を実装。
    - 単元株（lot_size 単位）で切り捨て・上限（per-stock と aggregate）を考慮するアルゴリズム。
    - aggregate cap 超過時はスケーリングを行い、残余キャッシュで端数（lot 単位）の配分を分配する再現性のあるロジックを実装。
    - cost_buffer を加味して手数料・スリッページを保守的に見積もる。

- ペーパートレード検証ツール
  - tools/paper_verification_report.py:
    - ペーパー取引用 SQLite DB を解析して検証レポートを生成（期間指定可能）。
    - 指標: システム稼働率 (uptime)、注文成功率 (fill rate)、送信率 (send rate)、レイテンシ（avg/max/P95）など。
    - P95 計算補助、SQL クエリによる各種集計、閾値による PASS/FAIL 判定を実装。
    - デフォルト閾値を定義（稼働率 99%、成功率 90% 等）。

- 設定検証 CLI
  - validate_config.py:
    - 必須環境変数のチェック、KABUSYS_ENV / LOG_LEVEL の妥当性検査。
    - DUCKDB/SQLITE パスの親ディレクトリ存在チェック（起動時に自動作成される可能性は警告）。
    - config/*.yaml の存在確認と PyYAML があればパース検証（PyYAML がない場合はスキップして警告）。
    - KABUSYS_ENV=live の場合の追加ガード（LINE 通知設定確認、KILL_FLAG_CLEAR_ON_START の危険性警告）。
    - --strict オプションで警告もエラー扱いにできる。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- （初回リリースのため該当なし）

---

注記:
- 上記はソースコードの内容から推測した変更点・機能一覧です。実際のリリースノートに含める文言や日付はプロジェクト方針に合わせて調整してください。
- research/factor_research.py はファクター計算の骨格と定数を含んでいますが、ファイル末尾が途中で切れている（実装未完）ように見えます。用途に応じて追加実装が必要です。