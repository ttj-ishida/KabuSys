# Changelog

すべての変更は Keep a Changelog のフォーマットに従います。  
発行済みバージョン: 0.1.0（初回リリース）

## [Unreleased]
（なし）

## [0.1.0] - 2026-04-25

### Added
- 基本アプリケーションパッケージを追加（kabusys v0.1.0）。
  - パッケージメタ情報: src/kabusys/__init__.py に __version__ = "0.1.0" を追加。

- 実行用スクリプト
  - run_execution: 実行エンジン起動スクリプトを追加（src/kabusys/run_execution.py）。
    - プロセス優先度を最初に "high" に設定。
    - KABUSYS_ENV が `paper_trading` の場合、Paper Trading 用の専用 SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler を組み立て ExecutionEngine を起動。
    - 停止フラグ（data/stop_requested.flag）検知で安全に停止。PID ファイル管理（data/execution.pid）。
  - run_monitoring: 監視ポーリングループ起動スクリプトを追加（src/kabusys/run_monitoring.py）。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - Monitoring は常に本番用 sqlite_path を使用して監視データを記録。
    - 停止フラグ検知でループを終了。例外はログに残して次ポーリングへ継続。

- 環境設定・検証 CLI
  - config_setup: .env 初期作成・更新の対話式ウィザードを追加（src/kabusys/config_setup.py）。
    - .env テンプレート生成、既存値の読み込み、シークレットマスク、確認後の保存処理を提供。
  - validate_config: 起動前の設定検証 CLI を追加（src/kabusys/validate_config.py）。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL 検証、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在・パース検証（PyYAML の有無に応じて処理）。
    - --strict モードで警告を FAIL 扱いにするオプション。

- 環境設定管理
  - Settings クラス（src/kabusys/config.py）を追加:
    - 自動 .env 読み込み機能（プロジェクトルート検出: .git または pyproject.toml を基準）。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。自動ロードを無効にする KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
    - .env パーサ実装（クォートやバックスラッシュのエスケープ、コメント処理、export 形式対応）。
    - 多数のプロパティを提供（DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH / PAPER_FILL_MODE / PID ファイル等）、環境値の妥当性チェックを実施。

- ロギングユーティリティ
  - setup_logging を追加（src/kabusys/utils/logging_setup.py）。
    - stdout への StreamHandler と 日次ローテーションの TimedRotatingFileHandler（logs/<app_name>.log）をルートロガーに設定。
    - ログレベル・ログディレクトリは引数または環境変数で指定可能。ディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソール出力のみで継続。

- プロセス優先度・CPU 固定ユーティリティ
  - set_process_priority / set_cpu_affinity を追加（src/kabusys/utils/process_priority.py）。
    - Windows / POSIX（Linux, Darwin, FreeBSD）での差分を吸収する実装。
    - 設定失敗時は警告を出してスキップする安全設計。

- ポートフォリオ構築モジュール（純粋関数群）
  - portfolio_builder: 候補選定・重み付け（select_candidates / calc_equal_weights / calc_score_weights）（src/kabusys/portfolio/portfolio_builder.py）。
  - risk_adjustment: セクター集中制限・レジーム乗数（apply_sector_cap / calc_regime_multiplier）（src/kabusys/portfolio/risk_adjustment.py）。
  - position_sizing: 株数決定・リスク制限・単元株丸め（calc_position_sizes）（src/kabusys/portfolio/position_sizing.py）。
  - 上記をパッケージとして公開（src/kabusys/portfolio/__init__.py）。
  - 設計上、全関数は DB を参照しない純粋関数でありテスト容易性を重視。

- Paper Trading 検証レポートツール
  - tools/paper_verification_report.py を追加（src/kabusys/tools/paper_verification_report.py）。
    - paper_trading SQLite DB（既定: data/paper_trading.db）からシステム稼働率・注文成功率・送信率・レイテンシ等を集計し、PASS/FAIL 判定とレポートを出力。
    - P95 レイテンシ計算、各閾値（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200ms）を定義。
    - コマンドラインで期間指定（--from / --to）および DB パス指定（--db）可能。

- リサーチ・ファクター計算の骨組み
  - research/factor_research.py を追加（計算設計・定数定義とモメンタム計算インターフェースの導入）。DuckDB 接続を使った因子計算の方針を実装予定。

### Changed
- .env 読み込みの挙動
  - 自動ロードはデフォルトで有効だが、KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により無効化可能。プロジェクトルートが検出できない場合は自動ロードをスキップするように設計。

- ログ出力の挙動
  - StreamHandler は stdout に出力（stderr ではなく）することで、cron 等でのリダイレクト運用に対応。

### Fixed
- なし（初回リリース）

### Security
- 秘匿情報取り扱いの注意を README/.env に明記（.env を絶対に Git にコミットしない旨を config_setup の生成ヘッダに追加）。

---

## 互換性・運用上の注意（Migration / Usage Notes）
- 環境変数
  - 必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD
  - 監視ポーリング間隔: MONITOR_POLL_INTERVAL（正の整数、デフォルト 60 秒）。不正値はデフォルトにフォールバックして警告を出力。
  - Paper Trading 関連:
    - KABUSYS_ENV=paper_trading のとき、PAPER_TRADING_SQLITE_PATH（または Settings.paper_sqlite_path のデフォルト data/paper_trading.db）が使用され、発注記録は本番 SQLite と分離されます。
    - PAPER_FILL_MODE の有効値: "instant" | "partial" | "never" | "reject"。不正値は ValueError を発生させます。
  - Kill Switch:
    - 停止フラグ: data/stop_requested.flag を検出すると run_* スクリプトは安全終了します。
    - KILL_FLAG_CLEAR_ON_START が "1" の場合、設定によっては起動時に Kill Flag を自動クリアする挙動があるため本番では "0" を推奨します。
- ログ
  - デフォルトログディレクトリ: logs/
  - ファイルローテーション: 日次、30世代保持。ログディレクトリ作成に失敗した場合はコンソール出力のみで継続するため、起動失敗にはなりません。
- プロセス優先度
  - set_process_priority("high") を呼び出します。権限不足や未対応 OS の場合は警告を出して続行します。
- CLI
  - .env 作成ウィザード: python -m kabusys.config_setup
  - 設定検証: python -m kabusys.validate_config [--strict]
  - Paper レポート: python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - 実行/監視スクリプトは直接実行可能: python -m kabusys.run_execution / python -m kabusys.run_monitoring（用途に応じて適切な環境変数を設定のこと）

---

署名:
- 初回リリースのため、主な機能追加を中心にまとめています。今後のリリースではバグ修正、テスト追加、因子計算の完成等を予定しています。