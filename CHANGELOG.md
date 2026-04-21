# Changelog

すべての注目すべき変更をこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠し、セマンティックバージョニングを採用します。

最新の変更は一番上に記載します。

## [Unreleased]
- 今後の変更点をここに記載します。

## [0.1.0] - 2026-04-21
初回リリース。日本株自動売買システム "KabuSys" のコアユーティリティ、起動スクリプト、ポートフォリオ構築・ポジションサイジングロジック、各種 CLI ツールなどを追加しました。

### Added
- 起動スクリプト
  - run_execution.py
    - ExecutionEngine を起動するエントリポイントを追加。KABUSYS_ENV による動作分岐（paper_trading 時は専用 MockBrokerClient と paper_trading.db を使用）を実装。
    - プロセス優先度を高く設定して起動するフローを追加。
    - 実行中の停止制御に stop flag（data/stop_requested.flag）と pid ファイル（data/execution.pid）を利用。
    - スレッドで ExecutionEngine を実行し、停止フラグ検知で安全に停止処理を行う。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。デフォルトポーリング間隔は 60 秒で、環境変数 MONITOR_POLL_INTERVAL で上書き可能。
    - 監視用 DB（SQLite）と分析用 DuckDB への接続処理を実装。Monitoring は環境に関わらず本番 sqlite_path を使用。
    - 停止フラグ検出でループを終了、KeyboardInterrupt にも対応。

- 設定・環境管理
  - config.py
    - .env 自動読み込み機能（.env -> .env.local、OS 環境変数を保護して上書き）を実装。KABUSYS_DISABLE_AUTO_ENV_LOAD で自動読み込み無効化可能。
    - .env 行パーサを強化（export プレフィックス、シングル/ダブルクォート内のエスケープ、インラインコメントの取り扱い）。
    - Settings クラスを追加し、各種環境変数（API トークン、DB パス、Paper Trading 設定、監視閾値、実行環境判定など）をプロパティとして提供。無効値は ValueError を発生させ警告。
  - config_setup.py
    - 対話式ウィザードで .env を作成/更新する CLI を追加。既存値の再利用、シークレット項目のマスク表示、保存前の確認を実装。
  - validate_config.py
    - 起動前に .env と config/*.yaml の妥当性を検証する CLI を追加。必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性確認、DB パスの存在確認、YAML パース（PyYAML があれば実行）などを実装。
    - --strict オプションで警告も失敗扱いにできる機能を追加。

- ログ・プロセスユーティリティ
  - utils/logging_setup.py
    - 統一的なロギング設定ユーティリティを追加。stdout への StreamHandler と日次ローテート（30日保持）のファイルハンドラをルートロガーに設定。ログディレクトリ作成失敗時はファイル出力をスキップして stdout のみで継続。
  - utils/process_priority.py
    - クロスプラットフォーム（Windows / POSIX）でのプロセス優先度設定ユーティリティを追加。nice 値や Windows の優先度定数を抽象化し、権限不足などの場合は警告を出してスキップ。
    - CPU affinity を指定する set_cpu_affinity() を実装（存在しない場合は安全にスキップ）。

- ポートフォリオ構築・リスク調整・ポジションサイジング
  - portfolio/portfolio_builder.py
    - シグナル選別（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を追加。スコア全 0 の場合は等金額フォールバックと warn。
  - portfolio/risk_adjustment.py
    - セクター集中上限を適用して候補銘柄を除外する apply_sector_cap を追加。売却予定銘柄の除外や "unknown" セクターの扱いを考慮。
    - 市場レジームに応じた資金乗数 calc_regime_multiplier を追加（bull=1.0, neutral=0.7, bear=0.3、未知レジームはフォールバック）。
  - portfolio/position_sizing.py
    - ポジションサイズ決定ロジック calc_position_sizes を追加。allocation_method に応じて risk_based / equal / score をサポート。
    - 単元株丸め（lot_size）、1銘柄上限、aggregate cap（available_cash）によるスケーリング、コストバッファ（手数料・スリッページ係数）を考慮。
    - スケーリング時の端数処理（lot 単位での再配分）により再現性を意識した実装。

- 監視・解析・ツール
  - monitoring.monitoring_db の初期化（起動時に監視テーブルが存在することを保証する init_monitoring_db を各起動スクリプトから呼び出し）。
  - tools/paper_verification_report.py
    - Paper Trading 用の検証レポート生成スクリプトを追加。稼働率、注文成功率、送信率、P95 レイテンシなどを算出して PASS/FAIL 判定を出力。閾値はソース内定義（稼働率 99%、注文成功率 90%、送信率 95%、P95 レイテンシ 200ms）。
    - 日付フィルタ（--from / --to）と DB パス指定（--db / 環境変数）をサポート。

- リサーチ（ファクター算出）
  - research/factor_research.py（部分実装）
    - モメンタム等のファクター計算の骨子を追加（DuckDB 接続を受けて prices_daily 等のテーブルから算出する設計）。（モジュールは将来的な拡張を意図）

- パッケージメタ
  - kabusys/__init__.py に初期バージョン 0.1.0 を設定。

### Changed
- 初期リリースのため該当なし。

### Fixed
- 初期リリースのため該当なし。

### Removed
- 初期リリースのため該当なし。

### Security
- 必須トークン類（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等）は Settings 内で _require により未設定時に明示的にエラーとなるため、起動時に誤った設定で実行されるリスクを低減。

---

開発者向け注意:
- .env の自動ロードはプロジェクトルート（.git または pyproject.toml により判定）を基に行われます。配布後やテスト時に自動読み込みを無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。
- Paper Trading と本番用 SQLite はデフォルトで完全に分離されます（環境変数 PAPER_TRADING_SQLITE_PATH / is_paper ロジックを参照）。
- process_priority / CPU affinity の設定は権限や OS に依存するため、失敗時は警告を出して続行します。