# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠しています。  
フォーマット: https://keepachangelog.com/（日本語訳に準拠）

注: 以下は提示されたコードベースから推測してまとめた変更履歴です。

## [Unreleased]
- （なし）

## [0.1.0] - 2026-04-25
初回リリース

### Added
- 起動スクリプト / CLI
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。  
    - 環境変数 MONITOR_POLL_INTERVAL によるポーリング間隔上書き（既定 60 秒）。  
    - 停止フラグファイル (data/stop_requested.flag) により安全にループ終了。  
    - Monitoring は環境に関わらず本番用 sqlite_path を使用して監視テーブルを初期化。
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。  
    - KABUSYS_ENV=paper_trading 時は paper_trading 用の SQLite（デフォルト data/paper_trading.db）を使用し、本番 DB と分離。  
    - 起動時に停止フラグが立っていれば起動を中止。スレッドで実行して停止フラグ検出時に安全停止。  
    - PID ファイル管理とプロセス優先度設定を実装。
  - validate_config.py: .env と config/*.yaml の事前検証 CLI を追加（--strict オプション対応）。  
  - config_setup.py: 対話式 .env 作成・更新ウィザードを追加。

- 設定管理
  - config.Settings クラスを追加。各種環境変数をプロパティで取得し、妥当性チェック（例: KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE）を実施。  
  - 自動 .env ロード機能を追加（プロジェクトルート検出: .git または pyproject.toml を基準）。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。  
  - .env パーサーは export プレフィックス、シングル/ダブルクォート、エスケープ、コメント処理に対応。

- ロギング・プロセス管理ユーティリティ
  - utils.logging_setup.setup_logging: stdout への StreamHandler と日次ローテーションの TimedRotatingFileHandler をルートロガーに設定。既存ハンドラのクリア、ログディレクトリ作成失敗時のフォールバック対応。  
  - utils.process_priority: set_process_priority/set_cpu_affinity を追加。Windows/Linux/macOS 向けの差分吸収と例外処理を実装。

- ポートフォリオ構築関連（純粋関数群）
  - portfolio.portfolio_builder: select_candidates, calc_equal_weights, calc_score_weights を追加（DB 非依存、メモリ計算）。スコアが全て 0 の場合のフォールバック警告を含む。  
  - portfolio.risk_adjustment: apply_sector_cap（セクター集中制御）、calc_regime_multiplier（市場レジームに応じた乗数）を追加。  
  - portfolio.position_sizing: calc_position_sizes を追加。risk_based / equal / score の各配分方式をサポートし、単元株（lot_size）丸め、aggregate cap（利用可能現金に応じたスケールダウン）、cost_buffer を考慮した安全な株数算出ロジックを備える。

- リサーチ / ファクター計算
  - research.factor_research: Momentum 等ファクター計算モジュールの骨組みを追加（DuckDB 接続を受け、prices_daily / raw_financials を参照する設計）。

- ツール
  - tools.paper_verification_report: Paper Trading 用検証レポート生成スクリプトを追加。  
    - 稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）などの指標を集計・判定。  
    - 日付フィルタ（--from / --to）と DB 指定（--db / 環境変数）に対応。P95 計算の実装を含む。  
    - 既存のテーブルが無い場合や SQL 実行エラーに対するフォールバック処理あり。

- データベース初期化
  - 監視用テーブルの初期化関数（init_monitoring_db）を監視・実行両方の起動コードで呼び出して、起動時に監視テーブルが存在することを保証（冪等性）。

### Changed
- ロギングの挙動
  - ログ出力の StreamHandler を stderr ではなく stdout に設定（cron/task scheduler と併用しやすくするため）。  
  - setup_logging は既存のハンドラを全て flush/close してから再設定することで二重記録を防止。

- 環境変数読み込みの挙動
  - .env と .env.local の読み込み順を明確化（OS 環境 > .env.local > .env）。OS 環境変数は protected として上書き保護。

- 安全性・堅牢性
  - process_priority/set_cpu_affinity はアクセス権限や非対応 OS の場合に例外を吸収して警告出力するようにして、起動失敗を防止。  
  - ログディレクトリ作成に失敗した場合はファイルハンドラをスキップしてコンソール出力のみで継続。  
  - run_monitoring のポーリング間隔取得で不正値を検出した場合はデフォルトにフォールバックし警告を出力。

- ExecutionEngine の起動フロー
  - Engine は別スレッドで実行し、メインスレッド側で停止フラグを監視して安全に engine.stop() を呼ぶ設計に変更（停止時のタイムアウト join を含む）。

### Fixed
- 環境変数の妥当性チェック追加
  - PAPER_FILL_MODE の受け入れ値を限定し、不正値時は ValueError を発生させることで誤設定を早期に検出。  
  - KABUSYS_ENV / LOG_LEVEL について許容値チェックを実装し、無効な値は例外（Settings）またはエラー/警告（validate_config）として通知。

- モニタリングループの強靭化
  - monitor.check_once() が例外を投げても監視ループを止めず、例外をログ出力して次ポーリングへ継続するように改善。

- DB パス・ファイルパス周りの警告改善
  - validate_config で DB パス等の親ディレクトリが存在しない場合に警告を出して起動時自動作成を想定した案内を追加。

### Documentation / Comments
- 各モジュールに詳細な docstring および使用例を追加。設計上の注意点（例: price 欠損時の TODO、レジーム判定ポリシーの説明、lot_size 将来的拡張案など）を明記。

---

（備考）  
- 上記はリポジトリ内のソースコード・docstrings・定数・ログメッセージ等から推測して作成した CHANGELOG です。テスト結果や実際の運用上の変更履歴はリリース時に合わせて追記してください。