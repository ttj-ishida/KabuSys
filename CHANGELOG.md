# Changelog

すべての重要な変更点を記録します。  
フォーマットは「Keep a Changelog」に準拠しています。  

全般: コードベースから推測して記載しています。実装ファイル名・挙動に基づく機能追加・修正点を中心にまとめています。

## [0.1.0] - 2026-04-20

### Added
- 初期リリース相当の機能群を追加。
- 環境設定/設定読み込み:
  - .env/.env.local 自動読み込み機構を実装（プロジェクトルートを .git または pyproject.toml から検出）。
  - .env パーサーを実装。export 文、シングル/ダブルクォート、エスケープ、インラインコメントの扱いをサポート。
  - Settings クラスを実装し、環境変数から各種設定（J-Quants トークン、kabu API、DB パス、Paper Trading 設定、監視閾値、ログレベルなど）を取得可能に。
  - config_setup.py に対話式ウィザードを実装し、.env の初期作成・更新を支援（秘密値のマスク表示、既存値の再利用、保存確認など）。
  - validate_config.py に設定検証 CLI を実装。必須環境変数、KABUSYS_ENV 値、ログレベル、DB パス、config/*.yaml の存在と YAML パース（PyYAML があれば）等をチェック。--strict モードで警告を失敗扱いにできる。
- 実行・監視ランナー:
  - run_execution.py を追加して ExecutionEngine を起動するスクリプトを提供。KABUSYS_ENV が paper_trading の場合は paper-trading 用 DB を使用し、Broker クライアントを切り替える設計（BrokerClientFactory を利用）。
  - run_monitoring.py を追加して SystemMonitor のポーリングループを起動するスクリプトを提供。ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能（デフォルト 60 秒）。監視は環境にかかわらず本番 sqlite_path を使用する旨の実装。
  - 両スクリプトとも「停止フラグ（data/stop_requested.flag）」の検知で安全に停止する仕組みを実装。
  - run_execution はエンジンを別スレッドで実行し、停止フラグ検知時に engine.stop() を呼ぶことで安全停止を図る。
- ロギング・プロセス管理ユーティリティ:
  - utils/logging_setup.py に統一ロギング設定ユーティリティを実装。コンソール出力（stdout）と日次ローテーション（TimedRotatingFileHandler）をルートロガーへ設定し、既存ハンドラの重複防止やログディレクトリ作成失敗時のフォールバックを備える。
  - utils/process_priority.py にプロセス優先度設定と CPU affinity 設定ユーティリティを実装。Windows / POSIX を吸収する実装で、権限不足や未対応 OS の場合は警告を出してスキップする。
- ポートフォリオ構築関連（純粋関数群、DB参照なし）:
  - portfolio/portfolio_builder.py:
    - シグナル選定（select_candidates）: スコア降順、同点は signal_rank でタイブレーク。
    - 等重配分（calc_equal_weights）・スコア加重配分（calc_score_weights）。全スコアが 0 の場合は等重へフォールバック。
  - portfolio/risk_adjustment.py:
    - セクター上限適用（apply_sector_cap）: 既存ポジションからセクター別エクスポージャ算出し上限超過セクターの新規候補を除外。unknown セクターは上限適用から除外。
    - レジーム乗数（calc_regime_multiplier）: "bull"/"neutral"/"bear" に対応する乗数を返す（未知レジームは警告の上 1.0 でフォールバック）。
  - portfolio/position_sizing.py:
    - position sizing ロジックを実装。allocation_method に応じた株数計算（"risk_based", "equal", "score"）。単元（lot_size）丸め、1 銘柄上限・aggregate cap（available_cash）スケールダウン、cost_buffer（手数料・スリッページ保守見積）対応、残差処理による追加配分ロジック等を備える。
- 分析・レポート:
  - tools/paper_verification_report.py を追加。Paper Trading の検証レポートを生成（指定期間フィルタ対応）。システム稼働率、注文成功率（fill/send）、リスク却下数、レイテンシ指標（avg/max/P95）を算出し PASS/FAIL 判定（閾値はファイル内定数として定義）を出力。P95 計算実装、SQL 抽出時の日付フィルタ付与などに対応。
- データベース接続:
  - 複数箇所で sqlite3 と DuckDB を利用する設計を導入（duckdb 接続を受け渡して分析処理を行う想定）。monitoring_db の初期化ユーティリティ（init_monitoring_db）を参照して起動時に監視テーブルの存在を保証。
- パッケージ情報:
  - パッケージバージョン __version__ を 0.1.0 に設定。

### Changed
- なし（初回リリースのため）。

### Fixed
- なし（初回リリースのため）。ただし、実装上考慮しているエラーハンドリング等:
  - run_monitoring のポーリング内で monitor.check_once() が例外を投げてもループを継続し、例外時はログ出力して次回ポーリングへ（堅牢性向上）。
  - run_monitoring/run_execution 共に KeyboardInterrupt を捕捉して適切にクリーンアップ。

### Notes / Implementation details（補足）
- run_execution は paper_trading 環境時に paper_sqlite_path（デフォルト data/paper_trading.db）を使用することで紙運用と本番 DB を完全に分離する設計になっています。
- logging_setup は stdout に出力することで cron / scheduler からの起動時のリダイレクト運用を想定しています。
- process_priority の設定は実行直後に呼び出され、優先度変更に失敗した際は警告でスキップします（管理者権限不要で安全に動作するよう配慮）。
- config_setup のウィザードは秘密値をマスクして表示し、ユーザの操作で .env を安全に生成・更新できます。
- research モジュール（factor_research.py）はファクター計算の実装を開始しており（モメンタム等の定義と定数が追加されている）未完の箇所が見られます（ファイル末尾で切れているため、継続実装が必要）。

---

今後のリリース案（例）
- 0.1.x: research のファクター計算完成、Engine / Broker の統合テスト、追加のユニットテスト導入
- 0.2.0: strategy 実装、運用ダッシュボード／アラート強化、CSV/バックテスト機能追加

（この CHANGELOG はコードの現在の状態から推測して作成しています。実際のコミット履歴やリリースノートと差異がある可能性があります。）