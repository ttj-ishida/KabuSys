# CHANGELOG

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠しています。

- リリース日付はコードベースの現状から推測して記載しています。
- 記載内容はソースコードの実装・コメントから推測してまとめています。

## [0.1.0] - 2026-04-18 (初回公開想定)

### Added
- 初期リリース: KabuSys 基本コンポーネントを実装。
- 実行用スクリプト
  - run_execution.py: ExecutionEngine 起動スクリプト。  
    - KABUSYS_ENV=paper_trading 時は paper_trading 用 SQLite（デフォルト: data/paper_trading.db）を使用し、MockBrokerClient を利用する設計（BrokerClientFactory により生成）。  
    - エンジンはデーモンスレッドで実行され、 data/execution.pid に PID を書き出す仕組みを想定。data/stop_requested.flag により安全停止可能。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプト。  
    - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能（デフォルト 60 秒）。  
    - 監視用 DB は環境に関わらず本番用 sqlite_path を使用する（設計上の注意点）。
- 設定関連
  - config.py: Settings クラスによる環境変数アクセスラッパーを実装。  
    - .env / .env.local の自動ロード機構を提供（プロジェクトルートを .git または pyproject.toml で検出）。  
    - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。  
    - .env パーサは export KEY=val、クォート値、行内コメントなどを考慮した堅牢な実装。  
    - デフォルト値や検証付きプロパティ（env, log_level, PAPER_FILL_MODE 等）を用意。
  - config_setup.py: インタラクティブな .env 作成/更新ウィザードを実装（対話式 CLI）。
  - validate_config.py: 起動前チェック CLI を実装。  
    - 必須環境変数の未設定検出、パスの親ディレクトリ確認、config/*.yaml の存在/パースチェック（PyYAML がインストール済の場合）など。  
    - --strict オプションで警告も失敗扱いにできる。
- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py: 候補選定 (select_candidates)、等重配分 (calc_equal_weights)、スコア加重 (calc_score_weights) を実装。  
    - スコア全てが 0 の場合は等分配にフォールバック。
  - portfolio/risk_adjustment.py: セクター集中制限 (apply_sector_cap)、レジーム乗数 (calc_regime_multiplier) を実装。  
    - レジームに応じた投下資金乗数マップを提供（bull/neutral/bear）。未知レジームは 1.0 にフォールバック。
  - portfolio/position_sizing.py: 発注株数計算ロジックを実装（allocation_method: "risk_based" / "equal" / "score"）。  
    - 単元株（lot_size）丸め、1銘柄上限、aggregate cap（available_cash を超える場合のスケールダウン）や cost_buffer（手数料/スリッページ見積り）を考慮。
- ユーティリティ
  - utils/logging_setup.py: ルートロガーの統一設定。  
    - stdout への StreamHandler と日次ローテーションの TimedRotatingFileHandler（logs/<app_name>.log、30 日分保持）を設定。  
    - LOG_LEVEL / LOG_DIR の解決ルール、ディレクトリ作成失敗時のフォールバックを実装。
  - utils/process_priority.py: プロセス優先度設定と CPU affinity 設定ユーティリティ。  
    - Windows / POSIX の差分吸収（psutil を使用）、失敗時は警告としてスキップ。
- モニタリング関連
  - monitoring の DB 初期化呼び出し（init_monitoring_db）を組み込み、SystemMonitor の単発チェック check_once() をポーリングで実行するループを実装。  
  - 停止フラグ（data/stop_requested.flag）検出によるループ終了をサポート。
- Paper Trading 検証ツール
  - tools/paper_verification_report.py: Paper Trading 用 SQLite を読み、システム稼働率、注文成功率、送信率、API レイテンシ（平均/最大/P95）等を算出してレポートを出力。  
    - P95 の算出、期間フィルタ、閾値（稼働率 99% 等）に基づく PASS/FAIL 判定を実装。
- research/factor_research.py: ファクター計算モジュールの骨組みとモメンタム計算の定数定義（calc_momentum の実装開始を示唆するドキュメント）を追加。
- パッケージ情報
  - __init__.py にてバージョン __version__ = "0.1.0" を設定。

### Changed
- (設計) Paper Trading と本番データの明確な分離を採用。ExecutionEngine は paper_trading の場合に専用 SQLite（PAPER_TRADING_SQLITE_PATH）を使用するよう実装。
- ログ出力: stdout を主要ストリームとして使用する方針（cron/Task Scheduler との親和性を考慮）。

### Fixed
- なし（初回リリース想定のためバグ修正履歴はなし）。ただし、各所で失敗時のフォールバック（ファイルハンドラ作成失敗や psutil エラー等）を丁寧に扱う実装あり。

### Security
- 必須機密情報（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD）は Settings にて必須チェックを行い、未設定時に ValueError を送出して起動を防止する設計。
- .env ファイル生成ウィザードは「.env を絶対に Git にコミットしない」旨をヘッダに明記。

### Known issues / TODO（コード内コメントより）
- portfolio/risk_adjustment.apply_sector_cap:
  - price が欠損（0.0）の場合にエクスポージャーが過少見積りされる可能性があり、将来的に前日終値や取得原価などのフォールバック価格導入を検討する旨の TODO がある。
- portfolio/position_sizing:
  - lot_size は現在グローバル固定（デフォルト 100）。将来的には銘柄別 lot_map を導入する拡張予定。
- research/factor_research.calc_momentum: 実装が途中で切れている（ファイル末尾が断片的）。ファクター計算関連の追加実装が必要。
- run_monitoring: 監視は「環境にかかわらず本番 sqlite_path 使用」のため、テスト用途でのデータ分離に注意が必要（意図的設計だが運用時の取り扱い注意）。
- process_priority / set_cpu_affinity: OS 権限不足（psutil.AccessDenied）や未対応 OS の場合はログ警告でスキップする仕様。期待する効果を得るには適切な実行権限が必要。

---

この CHANGELOG はソースコード中のコメント・実装から推測して記載しています。実際のリリースノート作成時は、リリース日やマイナー/パッチの分割、影響範囲の追記（breaking changes 等）をプロジェクトの方針に合わせて確定してください。