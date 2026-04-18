# CHANGELOG

すべての重要な変更をこのファイルに記録します。形式は Keep a Changelog に準拠します。
タグやバージョン番号はリリース時に更新してください。

なお、この CHANGELOG は提示されたコードベースの内容から推測して作成しています。

## [Unreleased]

### Added
- research モジュールにファクター計算の骨組みを追加（ファクター一覧、定数、calc_momentum の実装開始）。  
  - ファイル: src/kabusys/research/factor_research.py  
  - Momentum（1M/3M/6M、MA200乖離）、ATR/出来高系の計算方針や DuckDB ベースの実行設計を導入。
- 環境設定ウィザードの改善（対話式 .env 作成/更新の流れ整備）。  
  - ファイル: src/kabusys/config_setup.py  
  - 既存値再利用、シークレットマスク表示、保存前の確認プロンプトをサポート。

### Changed
- 環境変数の自動ロードの挙動を明確化（プロジェクトルート判定ロジック、.env/.env.local の読み込み順と保護ルール）。  
  - ファイル: src/kabusys/config.py、config_setup.py
- ロギング設定の扱いを改善（stdout 出力 / 日次ローテーションファイル出力 / ログディレクトリ作成失敗時のフォールバック）。  
  - ファイル: src/kabusys/utils/logging_setup.py

### Fixed / Notes
- .env パーサはシングル/ダブルクォートや export プレフィックス、行内コメント（特定ルール）を正しく扱うようになっています。  
  - ファイル: src/kabusys/config.py

---

## [0.1.0] - 2026-04-18

初回公開リリース。主要な機能と CLI/サービス起動スクリプトを含みます。

### Added
- 基本パッケージ情報
  - src/kabusys/__init__.py にバージョン情報を追加（__version__ = "0.1.0"）。

- 環境管理
  - 自動 .env 読み込み機能（プロジェクトルート検出: .git / pyproject.toml ベース）。  
    - ファイル: src/kabusys/config.py
  - .env の読み込みロジック（上書きルール、protected keys、行パース）を実装。
  - Settings クラスで主要設定をプロパティとして提供（DB パス、API トークン、環境種別、各種閾値等）。

- 設定支援ツール / 検証
  - 対話式環境設定ウィザードを追加（.env の初期作成・更新を支援）。  
    - ファイル: src/kabusys/config_setup.py
  - 設定検証 CLI を追加（必須環境変数、KABUSYS_ENV、ログレベル、DB パス、config/*.yaml の存在確認、live 時のガード）。  
    - ファイル: src/kabusys/validate_config.py

- 実行系 / 監視系プロセス起動スクリプト
  - ExecutionEngine 起動スクリプトを追加（Execution 用 DB の分離: paper_trading 時は専用 DB を使用）。  
    - ファイル: src/kabusys/run_execution.py  
    - 特徴: BrokerFactory によるブローカ切替、OrderRepository/OrderManager/RiskManager/Reconciler 組立、Engine のバックグラウンド実行・停止フラグ対応、PID ファイルの扱い
  - SystemMonitor ポーリングループ起動スクリプトを追加（MONITOR_POLL_INTERVAL 環境変数でポーリング間隔制御）。  
    - ファイル: src/kabusys/run_monitoring.py  
    - 特徴: 監視 DB 初期化、停止フラグ検知、例外安全な単一実行チェック

- Paper Trading / 検証ツール
  - Paper Trading 検証レポート生成スクリプトを追加（稼働率、注文成功率、送信率、レイテンシ、リスク却下数の集計と PASS/FAIL 判定）。  
    - ファイル: src/kabusys/tools/paper_verification_report.py  
    - 環境変数: PAPER_TRADING_SQLITE_PATH を使用可能

- ポートフォリオ構築ライブラリ
  - 銘柄選定と重み計算（等金額・スコア加重）を実装。  
    - ファイル: src/kabusys/portfolio/portfolio_builder.py
  - セクター集中制限とレジーム乗数を実装。  
    - ファイル: src/kabusys/portfolio/risk_adjustment.py
  - 発注株数決定ロジック（risk_based / equal / score）の実装（単元株丸め、aggregate cap スケーリング、コストバッファ考慮）。  
    - ファイル: src/kabusys/portfolio/position_sizing.py
  - 上記をパッケージとして再エクスポート。  
    - ファイル: src/kabusys/portfolio/__init__.py

- ユーティリティ
  - ロギング設定ユーティリティ（stdout + 日次ローテーションファイル、ログレベル解決、ログディレクトリ作成失敗時のフォールバック）。  
    - ファイル: src/kabusys/utils/logging_setup.py
  - プロセス優先度 / CPU affinity 設定ユーティリティ（Windows / POSIX の差分を吸収、Permission エラーは警告でスキップ）。  
    - ファイル: src/kabusys/utils/process_priority.py

- その他
  - 実行中の監視テーブル初期化ユーティリティ呼び出しの統一（monitoring DB の冪等初期化を実行スクリプトで保証）。
  - Execution 側で paper_trading 環境は本番 DB と完全分離（デフォルト data/paper_trading.db）。

### Changed
- 起動スクリプト共通で起動時にプロセス優先度を "high" に設定するように変更（set_process_priority を呼び出し）。  
  - ファイル: src/kabusys/run_monitoring.py、src/kabusys/run_execution.py

### Fixed / Robustness
- .env のパースでクォート中のバックスラッシュエスケープや行内コメント処理に対応（より堅牢に）。  
  - ファイル: src/kabusys/config.py
- ログディレクトリ作成失敗時でもプロセスは継続し、コンソール出力のみでログを残すフェールセーフ実装。  
  - ファイル: src/kabusys/utils/logging_setup.py
- process priority / cpu affinity の設定は権限不足や未対応 OS の場合に警告で安全にスキップするように。

### Known issues / Limitations
- research/factor_research.py の calc_momentum 実装が途中（ファイル末尾が未完の状態）。完全なファクター計算は次版で追加予定。
- 一部の TODO コメント（例: price 欠損時のフォールバック、銘柄別 lot_size のサポート等）が残っています。
- 本番運用上の安全装置（kill/stop flag の運用、KILL_FLAG_CLEAR_ON_START の設定）はドキュメントに従って慎重に運用してください。

---

(注) リリース日・バージョンはソースから推測したものです。実際のリリース管理時はタグ・日付を適宜修正してください。