# Changelog

すべての重要な変更をこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠しています。  

現在のパッケージバージョン: 0.1.0

## [Unreleased]
- （なし）

## [0.1.0] - 2026-04-18
初回公開リリース。システム全体の起動スクリプト、設定管理、検証ツール、ポートフォリオ構築・ポジション決定ロジック、ユーティリティ類、およびペーパートレード検証レポート生成ツールを含む初期実装を追加しました。

### Added
- 基本パッケージ
  - パッケージメタ情報を追加（kabusys.__version__ = "0.1.0"）。
  - エクスポート用のモジュール集合を定義（data, strategy, execution, monitoring）。

- 起動スクリプト / 実行系
  - run_execution.py
    - ExecutionEngine を起動するエントリポイントを実装。
    - BrokerClientFactory によるブローカークライアント生成（KABUSYS_ENV=paper_trading 時は paper 専用 DB を使用／MockBroker の想定）。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み合わせてエンジンを構築。
    - PID ファイル管理、停止フラグ（data/stop_requested.flag）検出、スレッドでのエンジン実行・安全停止処理を実装。
    - paper_trading 環境では専用 SQLite（data/paper_trading.db をデフォルト）を使用して本番 DB と分離。

  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを実装。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視 DB 初期化（init_monitoring_db）、Monitoring は環境にかかわらず本番 sqlite_path を使用する旨の挙動を実装。
    - 停止フラグ検知および KeyboardInterrupt によるクリーンシャットダウン処理を実装。

- 設定管理 / 自動読み込み
  - config.py
    - .env 自動読み込み（プロジェクトルート判定: .git または pyproject.toml を基準）。
    - .env / .env.local の読み込み順を実装（OS 環境変数を保護する protected 機構あり）。
    - .env 行パーサーを実装（export 形式対応、シングル/ダブルクォート内のエスケープ処理、インラインコメント対応）。
    - Settings クラスを提供し、J-Quants・kabu API・DB パス・監視閾値・環境判定などのプロパティを型安全に取得可能。
    - PAPER_FILL_MODE（ペーパートレードの約定モード）、PAPER_TRADING_SQLITE_PATH、PID/kill flag パス等の設定プロパティを実装。

- 設定検証 / ウィザード
  - validate_config.py
    - .env と config/*.yaml の簡易検証 CLI を実装（必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パス・YAML ファイル存在とパース検証、live 環境向けガード）。
    - --strict モードで警告も失敗扱いにするオプションを提供。
  - config_setup.py
    - 対話式ウィザードで .env を初期生成・更新する CLI を実装。
    - シークレット値のマスク、デフォルト値提示、選択肢対応、既存値読み込み・そのまま利用をサポート。
    - 最終確認後に .env を安全に書き出す機能を提供。

- ポートフォリオ構築・リスク調整・ポジションサイジング
  - portfolio/portfolio_builder.py
    - select_candidates: スコア降順で候補抽出（タイブレーク: signal_rank）。
    - calc_equal_weights / calc_score_weights: 等配分・スコア加重の重み計算（スコア合計が0のとき等配分へフォールバック）。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター別の既存エクスポージャーに基づく候補除外（unknown セクターは除外対象外）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を返す（未知レジームは警告と共に 1.0 にフォールバック）。
  - portfolio/position_sizing.py
    - calc_position_sizes: risk_based / equal / score の各配置方式をサポート。
    - 単元株（lot_size）で丸め、per-position および aggregate のキャップ判定、利用可能現金に応じたスケーリングロジック、cost_buffer を使った保守的見積り、余剰配分の補正アルゴリズムを実装。

- 解析・リサーチ
  - research/factor_research.py（スケルトン実装・モメンタム等の計算ロジック準備）
    - DuckDB 接続を受けて prices_daily/raw_financials から各種ファクター（モメンタム、MA200乖離、ATR、ボリューム等）を計算する方針を実装。
    - P95 等の統計ユーティリティと日数定数を定義。

- ツール
  - tools/paper_verification_report.py
    - ペーパートレード用 SQLite を解析して検証レポート（稼働率、注文成功率、送信率、レイテンシ、リスク却下数）を生成する CLI を実装。
    - 閾値（稼働率 99% 等）に基づく PASS/FAIL 判定を出力。
    - 日付フィルタ（--from / --to）および --db オプションで DB パスを指定可能。

- ユーティリティ
  - utils/logging_setup.py
    - 統一的なロギングセットアップ関数 setup_logging を提供。
    - stdout への StreamHandler と日次ローテートする TimedRotatingFileHandler（デフォルト logs/<app_name>.log）をルートロガーへ設定。
    - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続するフェールセーフを実装。
    - 既存ハンドラのクリーンな再設定（重複防止）。
  - utils/process_priority.py
    - set_process_priority(level) により Windows/Linux/macOS の差分を吸収してプロセス優先度を設定。
    - set_cpu_affinity(cpu_count) でプロセスを最初の N コアへピン留めする機能を提供。
    - 権限不足や未対応 OS に対しては警告を出し処理をスキップする安全策を実装。

- 監視 DB 初期化
  - monitoring.monitoring_db.init_monitoring_db を呼び出して監視テーブルの存在を保証（冪等）。

### Changed
- ログ出力
  - ログは標準出力（stdout）へ出力するように設計。cron 等で stdout/stderr をまとめてリダイレクトする想定。
- .env 読み込みの優先順位
  - OS 環境変数 > .env.local > .env の優先順位で自動ロード。OS 環境変数は protected として上書き防止。
- 実行時優先度設定
  - 実行スクリプト起動直後に set_process_priority("high") を呼び出して優先度を向上させるように統一。

### Fixed
- ロバストネス向上
  - .env パーサーはクォート内のエスケープシーケンス、インラインコメント、export キーワードなどに対応し、より実運用向けの形式を受け入れるよう改善。
  - ログディレクトリ作成失敗やファイルハンドラ作成失敗時に処理継続するようフェールセーフを実装。
  - process_priority の設定で AccessDenied 等の例外をキャッチして警告に留めるようにし、起動の失敗を回避。
  - run_execution/run_monitoring での DB コネクションは finally ブロックで閉じるようにしてリソースリークを防止。

### Security
- シークレット管理
  - config_setup の対話式入力でシークレットは画面上マスク表示（確認時もマスク）され、.env 生成時にユーザーの手入力が必要である旨を明示。
  - .env は絶対に Git にコミットしない旨を README とテンプレートに注記。

### Notes / Known limitations
- research/factor_research.py はファクター計算ロジックの骨格を実装していますが、一部関数（calc_momentum 等）の実装継続が必要です（データ可用性のハンドリング等）。
- position_sizing の lot_size は現状グローバル固定（将来的に銘柄別単位対応を検討）。
- price 欠損時のエクスポージャー推定は現状脆弱（TODO コメントあり）。将来的にフォールバック価格の導入を検討。
- 本番（live）環境では設定を慎重に確認する必要があります（validate_config の live 用ガードを参照）。

---

今後の予定（例）
- research モジュールの完全実装（Value / Volatility / Liquidity 等のファクター実装）。
- ExecutionEngine / BrokerClient の統合テストと Paper Trading の自動検証パイプライン整備。
- 単体テスト・CI の整備、ドキュメント強化。

（以上）