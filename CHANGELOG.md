# Keep a Changelog — 日本語版

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) の形式に準拠しています。  
バージョン番号はパッケージの __version__（src/kabusys/__init__.py）に合わせています。

全般的な注記
- 本リリースは初期公開（初版）を想定したまとめです。コードベースから仕様・挙動を推測して記載しています。
- 環境変数やファイルパスのデフォルト値はコード内のコメント・実装に基づいています。実運用前に `python -m kabusys.validate_config` 等で検証してください。

## [Unreleased]
（現在なし）

## [0.1.0] - 2026-04-18
初回リリース

### Added
- 実行エントリ / 起動スクリプト
  - run_execution.py: ExecutionEngine を起動するコマンドラインスクリプトを追加。
    - KABUSYS_ENV が `paper_trading` の場合は専用のペーパートレード用 SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB と完全分離します。
    - エンジンは別スレッドで run_session() を実行し、data/stop_requested.flag を検知すると安全停止します。PID ファイル（data/execution.pid）を扱います。
    - 起動時にプロセス優先度を "high" に設定（utils.process_priority.set_process_priority）。
    - BrokerClientFactory を用いて実際のブローカーまたはモックを切り替えます（設定に依存）。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能（デフォルト 60 秒）。不正値は警告を出してデフォルトにフォールバックします。
    - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path（data/monitoring.db がデフォルト）を使用して状態を記録します。
    - 停止フラグ（data/stop_requested.flag）を監視し、フラグ検出でループを終了します。
    - 起動時にプロセス優先度を "high" に設定。

- 設定管理 / 検証ツール
  - config.py: 環境変数の取り扱いと Settings クラスを追加。
    - .env/.env.local の自動ロードを実装（プロジェクトルートを `.git` または `pyproject.toml` で探索）。OS 環境変数は保護され、.env.local は上書き優先。
    - 複雑な .env 行のパースに対応（export プレフィックス、シングル/ダブルクォート内のエスケープ、インラインコメント処理）。
    - 各種設定プロパティ（J-Quants、kabu API、DB パス、監視しきい値、環境判定メソッド等）を提供。PAPER_FILL_MODE のバリデーション実装。
  - config_setup.py: 対話式 .env 作成ウィザードを追加。
    - 複数の設定項目を対話的に入力・既存値の再利用・マスク表示（機密値）などをサポート。
    - 保存前の確認と .env への書き込みを実装（保存フォーマットのテンプレートあり）。
  - validate_config.py: 起動前設定検証 CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV の妥当性、LOG_LEVEL、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在・パースチェック（PyYAML が未インストール時はスキップ）など。
    - --strict オプションで警告を FAIL 扱いに可能。

- ロギング / プロセス管理ユーティリティ
  - utils/logging_setup.py:
    - StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション、デフォルト 30 日保持）をルートロガーへ設定する共通ユーティリティを追加。
    - ログディレクトリの自動作成、多重ハンドラ設定の回避、LOG_LEVEL/LOG_DIR の解決ルールを実装。
  - utils/process_priority.py:
    - プラットフォーム差分を吸収するプロセス優先度設定（Windows の priority class / POSIX の nice）を追加。
    - CPU affinity 設定のユーティリティも提供（set_cpu_affinity）。
    - psutil の権限や未対応 OS でのフォールバック処理・警告を実装。

- ポートフォリオ構築関連（純関数群）
  - portfolio/portfolio_builder.py:
    - 銘柄候補選定（select_candidates: スコア降順、タイブレークに signal_rank）。
    - 等金額配分（calc_equal_weights）とスコア加重配分（calc_score_weights、全スコアが 0 の場合は等配分にフォールバック）を実装。
  - portfolio/risk_adjustment.py:
    - セクター集中制限（apply_sector_cap）を実装。既存保有のセクター別時価を計算し、max_sector_pct を超えるセクターの新規候補を除外。
    - レジームに応じた投下資金乗数（calc_regime_multiplier: bull/neutral/bear、未知レジームは警告して 1.0 フォールバック）。
    - 注意点として "unknown" セクターは上限適用対象外。
  - portfolio/position_sizing.py:
    - position size 計算（calc_position_sizes）を実装。allocation_method に応じて "risk_based"（リスクベース）/ "equal" / "score" をサポート。
    - 単元株（lot_size）丸め、per-position 上限（max_position_pct）、aggregate cap（available_cash）に基づくスケーリング、cost_buffer による保守的見積り、端数処理（残差に基づく lot 単位での追加配分）を実装。
    - price が欠損する場合のスキップとログ出力、将来の拡張（銘柄別 lot_size）を示す TODO コメントあり。

- 分析・レポートツール
  - tools/paper_verification_report.py:
    - ペーパートレード検証レポート生成ツールを追加。PAPER_TRADING_SQLITE_PATH 環境変数（または --db オプション）から DB を読み、期間フィルタでレポートを生成。
    - 指標: 稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、レイテンシ（avg/max/P95）、リスク却下数 等。
    - P95 計算実装、閾値を用いた PASS/FAIL 判定（稼働率 >= 99%、fill_rate >= 90% 等）。
    - DB テーブルが存在しない場合に例外を拾ってフォールバックする堅牢性を実装。

- 研究用モジュール（骨組み）
  - research/factor_research.py:
    - モメンタム等のファクター計算モジュールの骨組みを追加。DuckDB 接続を受け取り prices_daily / raw_financials を参照して計算する方針を採用。
    - モメンタム指標（1M/3M/6M、MA200 乖離）等を計算する設計の開始。実装は途中（ファイル末尾が切れているため一部未完）。

- パッケージメタ
  - パッケージバージョンを 0.1.0 に設定（src/kabusys/__init__.py）。

### Changed
- （初版のため特記なし）

### Fixed
- （初版のため特記なし）

### Deprecated
- （初版のため特記なし）

### Removed
- （初版のため特記なし）

### Security
- （初版のため特記なし）

### Notes / 実運用時の注意点・既知の制限
- .env 自動読み込みはプロジェクトルートが特定できない場合はスキップされます（テスト環境などで KABUSYS_DISABLE_AUTO_ENV_LOAD を使って無効化可能）。
- config.PAPER_FILL_MODE の値は "instant" / "partial" / "never" / "reject" のみ許容。設定ミスは起動時に ValueError を発生させます。
- run_monitoring は「監視用 DB を本番 DB（SQLITE_PATH）で常に使用」する仕様です。テスト目的で監視だけを分けたい場合は実装を変更してください。
- position_sizing 内で price が欠損（0.0）だとエクスポージャーが過小評価される可能性があり、TODO コメントでフォールバック価格の導入が示唆されています。実運用では価格データの完全性を確保してください。
- process_priority や cpu_affinity の設定は psutil の権限に依存します。権限不足時は警告を出して処理をスキップします。
- research/factor_research.py は未完の箇所があります。ファクター計算の完全実装・テストを行ってください。

---

今後の推奨作業（短期）
- research/factor_research.py の未実装部分を完成させる（テストと DuckDB クエリの最適化）。
- テストカバレッジの追加（特に position_sizing のスケール・端数処理、apply_sector_cap の挙動）。
- 実運用向けの運用ドキュメント（デプロイ手順、ログ保守、kill/stop フラグの運用ルール）を整備。
- ブローカークライアントのモック挙動の明文化（paper_trading の再現性確保）。

[0.1.0]: /tag/v0.1.0