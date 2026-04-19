# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。  

全体方針:
- バージョンはパッケージの __version__ を基準にしています（現行: 0.1.0）。
- 記載はコードベース（src/kabusys 以下）から推測してまとめています。

## [Unreleased]

### Added
- 監視・実行の起動スクリプトを追加/整理
  - run_monitoring.py
    - SystemMonitor のポーリングループを起動するエントリポイント。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止判定はリポジトリ直下 data/stop_requested.flag を参照。
    - 監視は KABUSYS_ENV に関係なく本番用 sqlite_path を使用する仕様を明記。
    - SQLite と DuckDB の接続を作成し、正常終了時にクローズする。
  - run_execution.py
    - ExecutionEngine を起動するエントリポイント。
    - KABUSYS_ENV=paper_trading 時は専用の paper_trading SQLite(DB) を使用する（本番 DB と分離）。
    - BrokerClientFactory により本番/モックのブローカークライアントを選択。
    - スレッドで実行エンジンを起動し、stop flag 検知でエンジン停止を行う。
    - 実行中の PID 管理用の pid ファイルパスを指定。

### Added (設定・ユーティリティ)
- config.py
  - Settings クラスを追加し、環境変数から各種設定を提供。
  - .env 自動読み込み機能を実装（プロジェクトルート判定: .git / pyproject.toml を基準）。
  - .env パースは export prefix、クォート、エスケープ、インラインコメント等に対応。
  - 各種設定プロパティ（DBパス、ログレベル、Paper Trading の設定、監視閾値など）を用意。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート。
- config_setup.py
  - .env 作成・更新のための対話式ウィザードを追加。
  - デフォルトテンプレート生成、既存 .env の読み込み、確認後の保存を実装。
- validate_config.py
  - 起動前検証ツールを追加（必須環境変数、KABUSYS_ENV、ログレベル、DBパス、config/*.yaml の存在とパース検証など）。
  - --strict オプションで警告を失敗扱いにするモードを提供。
  - PyYAML 未インストール時の挙動を明記し、存在確認とパース検証を条件付きで行う。
- utils/logging_setup.py
  - 統一的なログ設定ユーティリティを追加。
  - stdout 出力（StreamHandler） + 日次ローテートファイル（TimedRotatingFileHandler）をルートロガーに設定。
  - LOG_LEVEL / LOG_DIR / app_name を解決して使う。ログディレクトリ作成失敗時はファイル出力をスキップして警告。
- utils/process_priority.py
  - クロスプラットフォームのプロセス優先度設定（Windows / POSIX）および CPU affinity 設定を実装。
  - 権限不足や未対応 OS の場合は警告を出してスキップする堅牢性を確保。
- portfolio パッケージ
  - portfolio_builder.py: 候補選定・等金額／スコア加重配分を実装。
  - risk_adjustment.py: セクター集中除外（apply_sector_cap）とレジーム乗数（calc_regime_multiplier）を実装。
  - position_sizing.py: 各種配分方式（risk_based / equal / score）に基づく株数計算、単元株丸め、aggregate cap によるスケーリングロジックを実装。
  - package __init__ を通じて主要関数をエクスポート。
- tools/paper_verification_report.py
  - Paper Trading 用の検証レポート生成スクリプトを追加。
  - 稼働率・注文成功率・送信率・レイテンシ（P95）等を集計して PASS/FAIL を判定する閾値を定義。
  - コマンドライン引数 --from / --to / --db をサポート。

### Added (monitoring / DB)
- monitoring_db 初期化呼び出し（init_monitoring_db）を起動フローで行い、監視テーブルが存在することを保証（冪等）。
- DuckDB を分析用 DB として導入し、各種モジュールで接続を受け取って使用する設計を採用。

### Added (research)
- research/factor_research.py を追加（ファクター計算基盤）。
  - Momentum / Value / Volatility / Liquidity を想定した設計と定数を用意。
  - DuckDB 接続を利用する方針を明確化。
  - （注）ファイルの途中で未実装箇所があるため、現在は開発途中（WIP）。

### Changed / Behavioral notes
- ログ出力の標準化: すべての起動スクリプトは setup_logging を最初に呼ぶ想定でログ設定が統一される。
- 実行/監視プロセスは起動直後にプロセス優先度を "high" に設定しようとする（権限がない場合は警告）。
- run_monitoring は MONITOR_POLL_INTERVAL の不正値を検出してデフォルトにフォールバックする安全処理を実装。

### Fixed / Robustness
- .env 読み込み時のパースロジックを強化（クォート・エスケープ・コメント処理）。
- ログディレクトリ作成やファイルハンドラ初期化失敗時でも動作を継続するフェイルセーフを導入。
- process priority / cpu affinity の失敗ケース（AccessDenied 等）を警告に留めることで起動失敗を回避。

### Removed / Deprecated
- （現状コードからは削除や廃止対象は検出できず）

### Security
- 機密値は .env に記載する想定。config_setup の出力でシークレットはマスク表示する等の配慮あり。
- 本番（live）モード時の注意喚起（validate_config のワーニング）を追加。

---

## [0.1.0] - 2026-04-19

初回リリース（推定）。上記 Unreleased の主要機能を含む初期公開版。

### Added
- 基本アーキテクチャと主要モジュールを実装:
  - 実行エンジン起動スクリプト (run_execution.py)
  - 監視起動スクリプト (run_monitoring.py)
  - 設定管理 (config.py)、対話式設定ウィザード (config_setup.py)、設定検証ツール (validate_config.py)
  - ロギング / プロセスユーティリティ (utils.logging_setup, utils.process_priority)
  - ポートフォリオ構築（選定、重み付け、ポジションサイズ計算、リスク調整）
  - Paper Trading 検証レポートツール
  - DuckDB/SQLite を用いたデータ保存・分析基盤の導入
  - monitor DB 初期化ユーティリティ連携
  - 起動時の stop/kill フラグ / pid 管理

### Changed
- N/A（初回リリース）

### Fixed
- N/A（初回リリース）

### Known issues / TODO
- research/factor_research.py の一部（calc_momentum 等）が未完了 / WIP。
- position_sizing の price 欠損時の挙動について TODO コメントあり（前日終値等によるフォールバックを検討）。
- 今後の拡張候補: 銘柄別単元サイズ対応、より細かなコスト推定、テスト向けのモック注入強化。

---

注: 上記はソースコードの実装内容から推測して作成した変更履歴です。リリース日付は本ファイル作成日（2026-04-19）を使用しています。実際のリリース履歴やバージョニング方針に応じて適宜調整してください。