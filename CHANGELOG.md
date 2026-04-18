# CHANGELOG

すべての重要な変更を記録します。本ドキュメントは「Keep a Changelog」フォーマットに準拠します。  
初回リリース相当の内容を、コードベースから推測してまとめています。

※ バージョンは src/kabusys/__init__.py の __version__ を基準にしています。

## [0.1.0] - 2026-04-18

### Added
- 基本的なアプリケーション骨格を実装
  - パッケージ名: KabuSys（日本株自動売買システム）
  - バージョン: 0.1.0

- 実行エントリスクリプト
  - run_monitoring.py
    - SystemMonitor を用いたポーリング監視ループの起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` によりポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 起動時にプロセス優先度を High に設定するユーティリティを呼び出す。
    - 停止フラグファイル（data/stop_requested.flag）を監視して安全に終了。
    - 監視用 DB は実行環境にかかわらず本番 sqlite_path を使用する設計。

  - run_execution.py
    - ExecutionEngine を起動するスクリプトを追加。
    - `KABUSYS_ENV=paper_trading` の場合は MockBrokerClient を使用し、ペーパートレード用 DB（デフォルト: data/paper_trading.db）で本番と完全分離。
    - ExecutionEngine は別スレッドで実行され、停止フラグで停止可能。
    - 起動時にプロセス優先度を High に設定。

- 環境設定・検証関連 CLI
  - config_setup.py
    - 対話式ウィザードで .env ファイルを作成・更新する機能を追加。
    - 入力補助、マスク表示、デフォルト値・選択肢、保存確認などを実装。
  - validate_config.py
    - 起動前に .env と config/*.yaml の妥当性を検証する CLI を追加。
    - 必須環境変数のチェック、KABUSYS_ENV / LOG_LEVEL の妥当性、DB パスや YAML の存在／パース確認、本番向けの追加ガード（LINE 設定・KILL_FLAG_CLEAR_ON_START）を実装。
    - --strict オプションで警告も失敗扱いにできる。

- 設定管理モジュール
  - config.py
    - 自動 .env ロード機能（プロジェクトルート検出: .git または pyproject.toml）。
    - .env のパースはクォートやエスケープ、行内コメント処理に対応（export 形式も許容）。
    - Settings クラスを導入し、環境変数へのアクセスをラップ（型変換・検証を含む）。
    - PAPER_FILL_MODE 等の値検証・有効値チェックを実装。
    - デフォルトパス: DuckDB: data/kabusys.duckdb, SQLite: data/monitoring.db, Paper DB: data/paper_trading.db 等。

- モニタリング DB 初期化
  - monitoring_db 初期化が起動時に呼ばれる（冪等で存在を保証）。

- ポートフォリオ構築ロジック（純関数群）
  - portfolio/portfolio_builder.py
    - 候補選定 (select_candidates)、等金額配分 (calc_equal_weights)、スコア重み配分 (calc_score_weights) を提供。
  - portfolio/position_sizing.py
    - position サイズ決定ロジック（risk_based / equal / score）、lot_size 単元考慮、aggregate cap（利用可能現金でのスケールダウン）、コストバッファを実装。
  - portfolio/risk_adjustment.py
    - セクター集中制限の適用 (apply_sector_cap)。
    - マーケットレジームに応じた投下資金乗数 calc_regime_multiplier を実装（bull/neutral/bear）。

- 実行系コンポーネント（骨組み）
  - execution 以下に EngineConfig / ExecutionEngine、OrderManager、OrderRepository、Reconciler、RiskManager、BrokerClientFactory 等の呼び口を用意（エンジン起動フローを構成）。

- ユーティリティ
  - utils/process_priority.py
    - クロスプラットフォームでのプロセス優先度設定および CPU affinity 設定関数を実装（Windows / POSIX を吸収）。
    - 権限不足や未対応環境では警告を出してスキップする堅牢性。
  - utils パッケージ用の __init__ を追加。

- リサーチ / ファクター計算
  - research/factor_research.py
    - DuckDB を使ったモメンタム・ボラティリティ等のファクター計算を実装（prices_daily テーブルを参照）。
    - mom_1m/3m/6m、MA200 乖離、ATR20、20日平均出来高等を計算する関数を提供。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading の検証レポートを生成する CLI を追加。
    - システム稼働率、注文成功率・送信率、リスク却下数、レイテンシ（平均/最大/P95）などを集計し、閾値に基づいて PASS/FAIL を判定。
    - デフォルトの DB パスは環境変数 PAPER_TRADING_SQLITE_PATH（または data/paper_trading.db）。

- DB 利用
  - SQLite と DuckDB の併用を想定し、起動スクリプトでそれぞれ接続／クローズを管理。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- .env を自動でコミットしない旨を config_setup に明記（.env は秘密情報を含むため推奨事項を表示）。

### Documentation / UX
- コマンドラインからの利用方法やヘルプ文字列を主要スクリプトに実装:
  - python -m kabusys.config_setup
  - python -m kabusys.validate_config
  - python -m kabusys.tools.paper_verification_report
  - run_* スクリプトは直接実行可能（if __name__ == "__main__" を提供）

### Notes / Migration
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
  - 上記が未設定の場合、validate_config や Settings._require によりエラーとなる（起動前の検証を推奨）。
- 主な環境変数とデフォルト:
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - DUCKDB_PATH: data/kabusys.duckdb
  - SQLITE_PATH: data/monitoring.db
  - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
  - LOG_LEVEL: INFO（有効値: DEBUG, INFO, WARNING, ERROR, CRITICAL）
  - PAPER_FILL_MODE: instant | partial | never | reject（デフォルト: instant）
  - KILL_FLAG_CLEAR_ON_START: 0 | 1（本番での設定は注意）
  - MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト 60）
- 実行時の注意:
  - run_monitoring は監視用 DB に対して「常に」production 相当の sqlite_path を使う設計。環境切り替えの扱いに注意。
  - run_execution は paper_trading 環境時に paper DB を用いるため、本番 DB へ誤って書き込むリスクを低減。
  - process priority / cpu affinity の設定は実行環境の権限によって失敗する可能性がある。ログで警告が出るが処理は継続される。

### Known issues / TODO
- position_sizing: price が欠損（0.0）の場合のフォールバック価格ロジックは未実装（TODO コメントあり）。
- 銘柄ごとの lot_size を将来的にサポートする設計を検討中（現在は全銘柄共通の lot_size）。
- factor_research の計算は prices_daily / raw_financials に依存しており、データ未整備時の挙動を検討中。
- config/*.yaml のテンプレート生成スクリプト（scripts/generate_config.py）への言及があるが、スクリプト自体の有無は要確認。

---

今後のリリースでは、実際の ExecutionEngine 内部実装（発注ロジック・再整合性処理等）や詳細なモニタリング項目、テストカバレッジ、ドキュメント強化を予定してください。必要であれば、この CHANGELOG を英語版やセマンティックリリース用フォーマットに変換します。