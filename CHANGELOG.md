# Changelog

すべての注目すべき変更をこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠し、セマンティックバージョニングを意識しています。

## [0.1.0] - 2026-04-18

### Added
- 基本アプリケーションの初回公開。
- 実行用エントリポイントを追加:
  - run_execution.py: ExecutionEngine を起動するスクリプトを追加。  
    - KABUSYS_ENV=paper_trading の場合は専用のペーパートレード用 SQLite（data/paper_trading.db、環境変数 PAPER_TRADING_SQLITE_PATH で上書き可）を使用して本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント選択、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、ExecutionEngine のデーモンスレッド起動と停止フラグ監視を実装。
    - PID ファイル管理（data/execution.pid）と停止フラグ（data/stop_requested.flag）に対応。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。  
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバックして警告を出力。
    - 監視は常に本番用 sqlite_path を使用する（環境に関係なく監視 DB を一元化）。
- 設定管理:
  - config.py: .env 自動読み込み（プロジェクトルート検出 .git / pyproject.toml 基準）、環境変数パーサ、Settings クラスを実装。多数の設定プロパティ（DB パス、KABUSYS_ENV、ログレベル、Paper Trading の設定など）を提供。
    - PAPER_FILL_MODE の値チェック・例外処理を実装（instant/partial/never/reject）。
    - env 判定（development/paper_trading/live）と便利なフラグ（is_live / is_paper / is_dev）。
- 設定関連 CLI:
  - config_setup.py: .env の対話式ウィザードを追加（.env の初期作成・更新を支援）。複数の設定項目を対話で入力・保存する機能を提供。
  - validate_config.py: 起動前検証 CLI を追加。必須環境変数、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在確認、config/*.yaml の存在とパースチェック（PyYAML が存在する場合）などを検証。--strict モードをサポート（警告をエラー扱いにする）。
- ロギング / プロセス管理ユーティリティ:
  - utils/logging_setup.py: ルートロガーを統一的に設定するユーティリティを追加。stdout への StreamHandler と日次ローテーションのファイルハンドラ（TimedRotatingFileHandler）を組み合わせ、ログディレクトリ自動作成、ログレベル解決ロジックを提供。
  - utils/process_priority.py: psutil を用いたクロスプラットフォームのプロセス優先度（high/normal/low）および CPU affinity 設定ユーティリティを追加。Windows / POSIX の差分吸収と失敗時のフォールバックログを備える。
- ポートフォリオ構築モジュール:
  - portfolio/portfolio_builder.py: 候補選定（select_candidates）、等重配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を実装。スコアが全て 0 の場合は等金額にフォールバックして警告を出力。
  - portfolio/risk_adjustment.py: セクター集中制限を適用する apply_sector_cap と市場レジームに基づく資金乗数 calc_regime_multiplier を実装。unknown セクターはセクター上限の対象外とする。
  - portfolio/position_sizing.py: position sizing ロジックを実装（allocation_method: risk_based / equal / score）。ロット単位（lot_size）で丸め、単銘柄上限・合計キャッシュ（available_cash） に対するスケールダウン、cost_buffer（手数料/スリッページ見積り）を考慮した安全な割付を提供。
- 解析 / 検証ツール:
  - tools/paper_verification_report.py: ペーパートレードの検証レポート生成ツールを追加。system_status / trade_logs / risk_logs を参照して稼働率、注文成功率、送信率、P95 レイテンシ等を集計し、PASS/FAIL 判定を行う。閾値はソース内定義（稼働率 99% 等）で判定。
- リサーチ基盤:
  - research/factor_research.py: DuckDB を用いたファクター計算基盤を追加（モメンタム等の計算方針・ユーティリティを実装）。（注: ファイルの末尾に未完成の関数（calc_momentum の冒頭で切れている箇所あり）あり。）
- パッケージ情報:
  - __init__.py にてバージョン __version__ = "0.1.0" を設定。

### Changed
- （初回リリースのため該当なし）

### Fixed
- run_monitoring / run_execution 等の起動スクリプトで、外部例外発生時にログ出力してループ継続する等の堅牢性を確保。
- .env 読み込みの失敗時に警告を出すようにし、環境依存性を低減（config._load_env_file がファイル読み込み失敗を警告）。

### Deprecated
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Security
- セキュリティに関する既知の変更はなし。ただし .env は絶対に Git にコミットしない旨をウィザードで明記。

### Notes / Known issues
- research/factor_research.py の calc_momentum 実装が途中で切れている（ファイル末尾が未完）。本番利用前に該当関数の完成とテストが必要。
- position_sizing.py の価格欠損（price が 0.0）によりエクスポージャーが過小評価される可能性がある旨を TODO コメントで指摘。将来的に前日終値や取得原価でのフォールバック実装を推奨。
- セクター適用ロジックでは sector_map に存在しないコードを "unknown" とみなして除外しない方針をとっている（設計上の仕様）。
- process_priority と set_cpu_affinity は権限不足やプラットフォーム非対応時に警告を出してスキップする実装。期待する効果を得るには実行環境での権限確認が必要。
- ログディレクトリ作成に失敗した場合はファイルロギングを無効化し、コンソール出力のみで継続する仕様。

---

今後のリリースでは以下を予定しています:
- research/factor_research の完成とユニットテスト追加
- 銘柄別 lot_size 対応（stocks マスタ導入）
- 監視/実行エンジンの統合テストおよび運用監視の強化
- config の型検証・YAML 設定のより詳細なバリデーション

（この CHANGELOG はコードを解析して記載しています。実際のコミット履歴が存在する場合は合わせて参照してください。）