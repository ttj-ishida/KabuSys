# Changelog

すべての注目すべき変更点を記述します。フォーマットは Keep a Changelog に準拠しています。

## [0.1.0] - 2026-04-25

### Added
- パッケージ初期導入: KabuSys 自動売買フレームワークの初期実装を追加。
  - src/kabusys/__init__.py にバージョン情報とパッケージ公開モジュール一覧を追加（__version__ = 0.1.0）。
- 環境・設定管理
  - src/kabusys/config.py
    - .env / .env.local の自動読み込み（OS 環境変数 > .env.local > .env の優先順）。
    - _find_project_root により __file__ を基準にプロジェクトルートを探索し、自動ロードを CWD に依存せず実行。
    - .env パース機能を実装（export 形式、シングル/ダブルクォート、エスケープ、インラインコメント対応）。
    - Settings クラスを導入し、アプリケーション設定（J-Quants / kabu API / DB パス / Paper Trading 設定 / 監視閾値 / 実行環境 等）をプロパティとして提供。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロードを無効化可能。
- 対話式設定ウィザード CLI
  - src/kabusys/config_setup.py
    - .env の初期作成・更新を行うウィザード（対話入力、既存値の再利用、秘密値のマスク表示、確認後の保存）。
    - デフォルト値・選択肢を用意。生成ファイルのフォーマットを明確化（.env を Git にコミットしないことを注意書き）。
- 設定検証 CLI
  - src/kabusys/validate_config.py
    - 起動前に必須環境変数や設定ファイル（config/*.yaml）、DB パス、KABUSYS_ENV の妥当性を検査。
    - PyYAML が未インストールの場合は YAML 検証をスキップして警告。
    - --strict オプションで警告を FAIL 扱いにできる。
- 実行 / 監視ランナー
  - src/kabusys/run_execution.py
    - ExecutionEngine を起動するスクリプト。
    - KABUSYS_ENV=paper_trading の場合は paper_sqlite_path を使い、本番 DB と分離したペーパートレード用 DB を使用。
    - BrokerClientFactory 経由でブローカークライアントを生成、OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine をデーモンスレッドで実行。
    - 停止フラグ（data/stop_requested.flag）の検知、PID ファイル管理、スレッドの安全終了処理を実装。
  - src/kabusys/run_monitoring.py
    - SystemMonitor のポーリングループを起動するスクリプト。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値や 0/負数はデフォルトにフォールバックして警告を出力。
    - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する（監視データを一元管理）。
    - 停止フラグ検知でループ終了、KeyboardInterrupt のハンドリング、DB 接続のクローズを保証。
- ユーティリティ
  - src/kabusys/utils/logging_setup.py
    - 統一的なロギング設定関数 setup_logging を提供。
    - stdout への StreamHandler（標準出力）と日次ローテートの TimedRotatingFileHandler（logs/<app_name>.log、30日保持）をルートロガーに設定。
    - ログディレクトリの自動作成、失敗した場合はファイルハンドラをスキップしてコンソール出力のみ継続。
    - ログレベル決定順の明確化（引数 > LOG_LEVEL 環境変数 > デフォルト）。
  - src/kabusys/utils/process_priority.py
    - プロセス優先度（high/normal/low）および CPU affinity 設定ユーティリティ。
    - Windows と POSIX (Linux/Mac/FreeBSD) の違いを吸収し、権限不足や未対応環境では警告を出してスキップ。
- ポートフォリオ構築（純粋関数群）
  - src/kabusys/portfolio/portfolio_builder.py
    - 候補選定（select_candidates）、等金額配分（calc_equal_weights）、スコア比例配分（calc_score_weights）。スコアが全て 0 の場合は等配分にフォールバックして警告。
  - src/kabusys/portfolio/risk_adjustment.py
    - セクター集中上限の適用（apply_sector_cap）、市場レジームに基づく投下資金乗数（calc_regime_multiplier、'bull'/'neutral'/'bear' マップとフォールバック）。
  - src/kabusys/portfolio/position_sizing.py
    - ポジションサイズ計算（calc_position_sizes）。
    - allocation_method に応じた株数計算（risk_based / equal / score）、単元株（lot_size）丸め、1銘柄上限や aggregate cap（利用可能現金を超える場合のスケーリング）を実装。
    - cost_buffer を用いた保守的コスト見積り、スケーリング時の残差処理（fractional remainder を用いた再配分）。
  - src/kabusys/portfolio/__init__.py で上記関数を公開。
- リサーチ / ファクター計算（基盤）
  - src/kabusys/research/factor_research.py（モジュール骨格・モメンタム計算開始）
    - DuckDB を使ったファクター計算の設計方針と定数を追加（モメンタム / MA200 / ATR / 出来高など）。（モジュールは続きあり）
- ツール
  - src/kabusys/tools/paper_verification_report.py
    - ペーパートレード DB を解析して検証レポートを生成する CLI。
    - 稼働率・注文成功率・送信率・P95 レイテンシなどを計算し、閾値に基づき PASS/FAIL を判定。
    - デフォルト DB パス: data/paper_trading.db。--db で上書き可能。
    - P95 計算、SQL クエリによる集計（system_status, trade_logs, risk_logs テーブル想定）を実装。
- その他
  - package 内に空の __init__ ファイルや tools/__init__.py を追加してパッケージ構成を整備。
  - monitoring の DB 初期化ヘルパー init_monitoring_db（インポート参照）を run スクリプト側で使用して冪等にテーブル存在を保証。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- .env ファイルを生成する際、注意書きで「.env は絶対に Git にコミットしないこと」を明示。秘密系設定はウィザードでマスク表示。

Notes / 補足:
- 実行時のプロセス優先度やログディレクトリ作成などは OS 権限に依存します。権限不足時は警告を出して安全にスキップするよう設計されています。
- run_monitoring は監視データ用 DB を本番 sqlite_path に固定して使用します。環境分離が必要なケース（例えばペーパートレード監視を別 DB にしたい場合）は設定の見直しを推奨します。
- config の自動ロード動作は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で抑止可能です（テスト環境向け）。

今後の予定（例）
- factor_research の続き実装（各ファクターの SQL / DuckDB 実装完了）
- ExecutionEngine / BrokerClient の詳細実装やテストケースの追加
- 単元株別の lot_size 対応（銘柄マスタ導入）