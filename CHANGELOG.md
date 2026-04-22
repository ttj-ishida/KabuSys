# Changelog

すべての変更は Keep a Changelog の形式に準拠しています。  
安定版リリースのスナップショットとして、今回の初回リリースを以下に記録します。

## [0.1.0] - 2026-04-22

### Added
- 起動スクリプトを追加
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。停止フラグファイル（data/stop_requested.flag）検知によるグレースフル終了をサポートし、sqlite3 と DuckDB を使用した DB 初期化/接続を行う。
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV=paper_trading 時は専用の paper_trading DB（data/paper_trading.db）と MockBrokerClient を使用する挙動をサポート。停止フラグと PID ファイル管理、スレッド起動／停止処理を実装。

- 設定管理と初期化ツールを追加
  - config.py: Settings クラスを実装し、環境変数や .env/.env.local の自動ロード（プロジェクトルート検出）をサポート。多くのプロパティ（DB パス、PID/kill フラグ、閾値、env 判定、paper_trading 関連設定など）を提供。PAPER_FILL_MODE のバリデーション等を実装。
  - config_setup.py: 対話式ウィザードで .env を初期作成/更新する CLI を追加（python -m kabusys.config_setup）。J-Quants、kabu API、DB パスやログレベル、Kill Switch 設定などを簡単に生成可能。
  - validate_config.py: 起動前の設定検証 CLI を追加（python -m kabusys.validate_config）。必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスや config/*.yaml の存在チェック（PyYAML が無ければ YAML 検証をスキップ）等を行い、エラー/警告/情報を出力。--strict オプションで警告を FAIL 扱いにできる。

- モニタリング・検証ユーティリティを追加
  - monitoring 起動・DB 初期化フロー（init_monitoring_db 呼び出し）を run_* スクリプトで統一。
  - tools/paper_verification_report.py: Paper Trading の検証レポート生成スクリプトを追加（python -m kabusys.tools.paper_verification_report）。稼働率・注文成功率・送信率・P95 レイテンシ等を集計して PASS/FAIL を判定する。閾値はスクリプト内で定義（稼働率 99% など）。期間フィルタ（--from / --to）や DB パス指定（--db / 環境変数）をサポート。

- ポートフォリオ構築ライブラリを追加（pure function）
  - portfolio/portfolio_builder.py: シグナルの候補選定（スコア降順、signal_rank でタイブレーク）、等重み・スコア重み算出を実装。スコアが全て 0 の場合は等金額配分へフォールバックし警告を出す。
  - portfolio/risk_adjustment.py: セクター集中制限（apply_sector_cap）とマーケットレジームに応じた投下資金乗数（calc_regime_multiplier）を実装。未知レジームはフォールバックで 1.0 を返し警告を出力。
  - portfolio/position_sizing.py: 各種配分方式（risk_based / equal / score）に基づく株数計算を実装。単元株丸め(lot_size)、ポジション上限、利用可能現金に応じた aggregate cap スケーリング、cost_buffer を考慮した保守的評価などのロジックを提供。細かなログ出力で価格欠損等をデバッグ可能にした。

- ユーティリティを追加/改善
  - utils/logging_setup.py: 統一的なロギング設定ユーティリティを追加。ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次・30日保持）を設定。ログディレクトリ自動作成、LOG_LEVEL / LOG_DIR の解決順定義、既存ハンドラのクリア処理を実装。ファイル出力作成失敗時はコンソール出力のみで継続。
  - utils/process_priority.py: クロスプラットフォームでのプロセス優先度設定（Windows の priority class と POSIX の nice 値の差分吸収）と、CPU affinity 固定ユーティリティを追加。アクセス権限不足や未対応 OS の場合は警告出力で安全にフォールバック。

- パッケージ版情報
  - __init__.py にバージョン情報 __version__ = "0.1.0" を追加。

- リサーチ用モジュール（着手）
  - research/factor_research.py: DuckDB を利用したファクター計算モジュールを追加（モメンタム等の計算方針と定数定義を含む）。calc_momentum 等の実装が開始され、ドキュメントと設計方針が含まれる（実装途中ファイルあり）。

### Changed
- ログ出力の標準化
  - 全スクリプトは setup_logging を呼び出すことでコンソールと日次ファイルの両方にログを出す共通仕様になった（app_name によるログファイル名分離）。

- DB パス運用の明確化
  - run_execution は paper_trading と本番で SQLite DB を分離して扱う（settings.is_paper に依存）。monitoring は環境にかかわらず本番 sqlite_path を使うという仕様を明確化。

### Fixed
- 環境変数パースの堅牢化
  - config._parse_env_line: export プレフィックス対応、クォートとバックスラッシュエスケープ処理、インラインコメントの扱いなどを取り扱い、.env の多様な記法に対して堅牢にパースするようにした。

- ポジションサイズ計算の端数処理
  - position_sizing.calc_position_sizes: aggregate スケールダウン後の端数処理を改善し、lot_size 単位での配分を残差の大きい順に追加配分するアルゴリズムを導入（再現性のためコードを二次キーに使用）。

### Internal
- validate_config のチェックリスト整備（config/*.yaml の存在チェック、PyYAML 有無でのフォールバック）。
- 設定自動ロードの保護機構: OS 環境変数を保護する protected set を導入し .env.local の上書き挙動を制御。
- ログディレクトリ作成失敗時の挙動改善（標準エラー出力で警告し、ファイルハンドラをスキップ）。

### Documentation
- 各モジュールに詳細な docstring と使用例、CLI の使い方を追加。config_setup と validate_config、tools/paper_verification_report などの実行手順を明記。

### Security
- 機密情報取り扱い: config_setup の対話入力では secret フラグをサポートし、表示時はマスク化を行う設計。さらに .env の生成時に「絶対に Git にコミットしないこと」を明記。

---

注: 本 CHANGELOG は現状のコードベースから推測して作成したもので、実際のコミット履歴や issue には基づいていません。必要であれば、機能ごとにさらに細分化した変更履歴や既知の制限・ TODO を追記します。