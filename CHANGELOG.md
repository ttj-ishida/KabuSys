# CHANGELOG

すべての重要な変更を記録します。形式は「Keep a Changelog」に準拠しています。  
リリースはコードベースの内容から推測して作成しています。

## [Unreleased]

- なし

## [0.1.0] - 2026-04-23

### Added
- 初期リリース: KabuSys 自動売買フレームワークの基本機能群を追加。
- 設定管理
  - 環境変数 / .env の自動ロード機構を追加（プロジェクトルートから .env / .env.local を読み込み、.env.local は上書き）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化オプションを実装。
  - .env パーサが export プレフィックス、シングル/ダブルクォート、およびエスケープシーケンスをサポート。
  - Settings クラスを提供し、各種設定（DB パス、API トークン、環境種別、ログレベル、Paper Trading の挙動など）をプロパティで取得可能に。
  - PAPER_FILL_MODE の妥当性チェック、PAPER_TRADING_SQLITE_PATH（Paper Trading 用 DB パス）などの設定項目を実装。
- 設定関連 CLI
  - 対話式 .env 作成/更新ウィザード（python -m kabusys.config_setup）を追加。
  - 起動前設定検証ツール（python -m kabusys.validate_config）を追加。必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスや config/*.yaml の存在・パースチェック、--strict モードをサポート。
- 実行コンポーネント起動スクリプト
  - run_execution: ExecutionEngine を起動する CLI スクリプトを追加。
    - KABUSYS_ENV=paper_trading 時は本番 DB と分離された Paper Trading 用 SQLite（data/paper_trading.db を既定）を使用する設計。
    - BrokerClientFactory を用いて実行環境に応じたブローカークライアントを生成（paper_trading ではモックを想定）。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み合わせて ExecutionEngine を起動。スレッドで実行し、外部停止フラグ（data/stop_requested.flag）を監視して安全終了。
    - PID ファイルの吐き出し（data/execution.pid）をサポート。
  - run_monitoring: SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバックして警告出力。
    - 監視は環境にかかわらず本番用の sqlite_path を使用する挙動（設計上の注意として明示）。
    - 停止フラグ（data/stop_requested.flag）を検知してループを終了。
- 監視（Monitoring）
  - 監視用 DB 初期化用のヘルパ（init_monitoring_db）と SystemMonitor を利用する設計を導入（run_monitoring / run_execution で呼び出し、監視テーブルの冪等な準備を行う）。
- ロギングと実行環境ユーティリティ
  - 統一ログ設定ユーティリティ setup_logging を追加。
    - コンソールは stdout に出力（cron 等で stdout/stderr をまとめてリダイレクトするケースに対応）。
    - 日次ローテーションのファイルハンドラ（TimedRotatingFileHandler）を用意し 30 日分保持。
    - 既存ハンドラをクリアしてから再設定することで二重出力を防止。
    - ログディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソールのみで継続。
  - プロセス優先度 / CPU affinity 設定ユーティリティ（set_process_priority / set_cpu_affinity）を追加。
    - Windows と POSIX（Linux, macOS, FreeBSD）で差分を吸収する実装。
    - 権限不足などによる失敗は警告を出して安全にスキップ。
- ポートフォリオ構築（純粋関数群）
  - portfolio.portfolio_builder: シグナル選定（select_candidates）、等配分/スコア加重の重み計算（calc_equal_weights / calc_score_weights）を実装。
  - portfolio.risk_adjustment: セクター集中制限（apply_sector_cap）と市場レジームに基づく投下資金乗数（calc_regime_multiplier）を実装。
  - portfolio.position_sizing: 株数決定ロジックを実装（risk_based / equal / score の割当方式、単元株丸め、per-stock 上限、aggregate cap のスケーリング、cost_buffer を考慮した保守的評価など）。
  - portfolio パッケージのエクスポートを整備。
- 解析/検証ツール
  - tools.paper_verification_report: Paper Trading の検証レポート生成スクリプトを追加。
    - 稼働率、注文成功率（fill rate）、送信率（send rate）、レイテンシ（avg/max/P95）などの集計と PASS/FAIL 判定を実行。
    - CLI 引数で期間指定（--from / --to）および DB パス指定（--db）をサポート。
    - デフォルト閾値（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200ms）を定義。
- 研究用モジュール（骨組み）
  - research.factor_research: DuckDB を使ったファクター計算の枠組みを追加（モメンタム、MA、ATR、流動性、バリュー等を想定）。関数 calc_momentum などの雛形を含む（実装は継続中）。

### Changed
- 主要起動スクリプト（run_monitoring / run_execution）で起動直後にプロセス優先度を "high" に設定するようにした（set_process_priority 呼び出し）。
- run_execution は paper_trading モード時に Paper 用 DB を使用して本番 DB とデータを分離する方針を明確化。

### Fixed
- ログ設定で既存ハンドラを一度クリアすることで、多重ハンドラ登録による重複出力を防止。
- .env 読み込み失敗時に警告を出して安全に継続する挙動を実装（読み込み失敗でクラッシュしない）。

### Notes / Design decisions
- .env の自動ロードはプロジェクトルートの検出に依存する（.git もしくは pyproject.toml を探索）。プロジェクトルートが不明な場合は自動ロードをスキップ。
- run_monitoring は運用上の安全策として MONITOR_POLL_INTERVAL の不正値を無効化しデフォルトにフォールバックする。
- position sizing の設計では lot_size を全銘柄共通の前提にしており、将来的に銘柄別の lot_map を導入する余地を残している。
- research.factor_research は計算方針・定数を定義しているが、一部実装が未完（継続開発対象）。

### Security
- .env は決してリポジトリにコミットしない旨の注意を config_setup に明記。

---

今後の予定（将来的なリリース案）
- factor_research の完全実装（DuckDB を用いた各種ファクター計算と正規化）。
- ExecutionEngine / Broker クライアントの追加テスト、および paper_trading の自動検証強化。
- 単体テスト・統合テスト、CI ワークフローの整備。
- 銘柄ごとの lot_size / 取引ルール対応や手数料モデルの明確化。