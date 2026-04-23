# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。  
リリースはセマンティックバージョニングを想定しています。

## [Unreleased]

### Added
- 全体
  - パッケージ初期機能群を追加（自動売買システムのコアユーティリティ・モジュール群）。
- 実行/監視ランナー
  - run_execution.py: ExecutionEngine を起動するエントリポイントを追加。プロセス優先度設定、SQLite/DuckDB 接続、Broker クライアント生成、OrderManager/RiskManager/Reconciler の組立て、スレッド実行および停止フラグによる制御を実装。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL でポーリング間隔を制御可能、停止フラグ検出でループ終了。
- 設定管理
  - config.py: .env 自動読み込み（プロジェクトルート検出）、環境変数取得ユーティリティ、Settings クラスを実装。Paper Trading 用 DB パスや各種閾値/フラグをプロパティとして提供。
  - config_setup.py: .env を対話式に作成・更新するウィザードを追加（秘密値のマスク表示、保存機能）。
  - validate_config.py: 起動前に .env と config/*.yaml の妥当性を検証する CLI を追加（--strict オプションで警告をエラー扱いに）。
- ポートフォリオ構築
  - portfolio/portfolio_builder.py: 候補選定 select_candidates、等金額・スコア重み算出関数を追加。
  - portfolio/position_sizing.py: position sizing（リスクベース、等配分・スコア配分）および aggregate cap スケーリング、lot 単位丸めを実装。
  - portfolio/risk_adjustment.py: セクター集中制限 apply_sector_cap、マーケットレジームに応じた資金乗数 calc_regime_multiplier を実装。
  - portfolio/__init__.py: 上記 API を公開。
- ユーティリティ
  - utils/logging_setup.py: StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション）を用いた統一ログ設定ユーティリティを追加。ログディレクトリ作成に失敗した際のフォールバックやログレベル解決ロジックを備える。
  - utils/process_priority.py: Windows/Linux/Mac の差分を吸収するプロセス優先度設定、CPU affinity 設定ユーティリティを追加。アクセス権限や未対応 OS へのフォールバックに配慮。
- ツール
  - tools/paper_verification_report.py: Paper Trading 用の検証レポート生成スクリプトを追加。稼働率・注文成功率・送信率・P95 レイテンシ等を算出し PASS/FAIL を判定する（閾値はスクリプト内定義）。コマンドライン引数で期間と DB パスを指定可能。
- 研究用
  - research/factor_research.py: DuckDB を用いたファクター計算基盤（モメンタム等）を追加（モジュール構成・定数・calc_momentum 等の実装方針を含む）。（一部関数実装は継続中）

### Changed
- ログ出力の統一化
  - すべての起動スクリプトから utils.setup_logging を呼び出す想定にし、ログ挙動を統一。
- DB の扱い
  - run_execution.py は KABUSYS_ENV=paper_trading の場合に専用の paper_trading DB を使用し、本番 DB と分離するポリシーを導入。
  - run_monitoring.py は監視データ用の sqlite_path を環境にかかわらず参照することを明示。

### Fixed
- 環境読み込み・パースの堅牢化
  - config._parse_env_line においてシングル/ダブルクォートやエスケープ、コメントの扱いを細かく実装し、.env の多様な書式に対応。
- ポジションサイズ算出の安定化
  - position_sizing.calc_position_sizes で price の欠損やゼロ値、lot 単位での丸め、aggregate cap 超過時のスケーリングと残余分配ロジックを実装して極端なケースを扱えるようにした。

### Security
- 秘密情報の扱い
  - config_setup の対話でシークレット項目（J-Quants トークン、kabu API パスワード等）はマスク表示し、.env を直接コミットしない注意書きを明記。

---

## [0.1.0] - 2026-04-23

初回公開（ライブラリバージョン __version__ = "0.1.0" と一致）。
主要な初期機能を公開：
- 実行エンジン・監視の起動スクリプト（run_execution, run_monitoring）
- 設定管理・ウィザード・検証ツール（config, config_setup, validate_config）
- ロギング・プロセス優先度ユーティリティ（utils.logging_setup, utils.process_priority）
- ポートフォリオ構築（選定・重み付け・リスク調整・株数決定）
- Paper Trading 検証レポート生成ツール
- 研究用ファクター計算モジュール（基盤部分）
- パッケージメタデータ（kabusys.__init__）

注記:
- 一部モジュール（例: research/factor_research の一部関数）は実装途中の箇所があります。継続的な実装・テストを推奨します。
- .env 自動ロードにより OS 環境変数を上書きしない設計ですが、必要に応じて KABUSYS_DISABLE_AUTO_ENV_LOAD を設定して自動ロードを無効化できます。

---

過去バージョン履歴や将来の変更はここに逐次追加してください。仕様や CLI の振る舞いを変更する際は Breaking Change として明示することを推奨します。