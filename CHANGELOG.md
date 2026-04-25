# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠しています。

## [0.1.0] - 2026-04-25

初回リリース — コア機能の実装と各種ユーティリティ、CLI を追加。

### Added
- 基本パッケージ構成（kabusys）とバージョン属性を追加。
- 環境設定読み込み・管理
  - .env ファイル自動ロード機能（プロジェクトルートの検出: .git または pyproject.toml を基準）。
  - 安全性を考慮したロード順: OS 環境変数 > .env.local > .env。
  - 環境変数のパース機能を実装（export 形式、シングル/ダブルクォート、インラインコメント対応）。
  - Settings クラスによりアプリケーション設定をプロパティで提供（DB パス、J-Quants・kabu API トークン、Paper Trading 設定、監視しきい値等）。
  - PAPER_FILL_MODE の妥当性検証、KABUSYS_ENV や LOG_LEVEL の検証。
- 設定作成ウィザード CLI（python -m kabusys.config_setup）
  - 対話形式で .env を初期作成・更新。シークレット値のマスク表示、選択肢/デフォルト対応。
  - .env 書き出しテンプレートを生成。
- 設定検証 CLI（python -m kabusys.validate_config）
  - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL 検証、DB パスの存在確認、config/*.yaml の存在チェック（PyYAML がなければパース検証をスキップ）。
  - --strict オプションで警告を失敗扱いにする機能を追加。
- 起動スクリプト
  - 実行エンジン起動スクリプト: src/kabusys/run_execution.py
    - ExecutionEngine の起動ロジック、paper_trading 環境では専用 SQLite(DB: data/paper_trading.db) を使用して本番 DB と分離。
    - BrokerClientFactory 経由で本物または Mock ブローカーを切り替え。
    - 停止フラグ（data/stop_requested.flag）検知による安全停止、PID ファイル管理。
  - 監視ループ起動スクリプト: src/kabusys/run_monitoring.py
    - SystemMonitor をポーリングで実行。ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能（デフォルト 60 秒）。
    - 監視は環境に関わらず本番用 sqlite_path を使用する設計。
- ロギング・プロセス管理ユーティリティ
  - logging_setup: ルートロガーに StreamHandler（stdout）と日次ローテートの FileHandler を設定。ログディレクトリ自動生成と失敗時のフォールバック処理。
  - process_priority: Windows / POSIX 差分を吸収してプロセス優先度（high/normal/low）設定と CPU affinity 設定のユーティリティを実装。権限不足・未対応環境でも安全にスキップ。
- ポートフォリオ構築ライブラリ（純粋関数群）
  - portfolio_builder: シグナル選定（select_candidates）、等金額（calc_equal_weights）、スコア重み（calc_score_weights）。
  - risk_adjustment: セクター集中制限の適用（apply_sector_cap）、市場レジームに応じた投下資金乗数（calc_regime_multiplier）。
  - position_sizing: 各銘柄の発注株数算出（risk_based / equal / score）、単元株丸め、aggregate cap（利用可能現金に応じたスケールダウン）やコストバッファ考慮。
- Paper Trading 向け検証ツール
  - tools/paper_verification_report.py: SQLite（paper_trading DB）を解析して稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）などを集計・レポート出力。合否基準（閾値）を定義。
- 研究用モジュール（スケルトン）
  - research/factor_research.py にファクター計算の骨組み（モメンタム、ボラティリティ等）を実装。DuckDB を使用して prices_daily / raw_financials を参照する設計。
  - （注）ファイル末尾に calc_momentum の実装開始の痕跡あり（実装途中の可能性あり）。

### Changed
- ログ出力の標準出力先を stderr ではなく stdout に統一（cron / Task Scheduler からのリダイレクトを想定）。
- logging_setup の既存ハンドラがある場合は一度 flush/close してから削除し再設定することで二重ハンドラ設定を回避。
- run_execution/run_monitoring 起動時にプロセス優先度を最初に high に設定するように統一。

### Fixed
- process_priority と logging の例外発生時に処理を中断しないようにハンドリングを実装（権限不足や未サポート環境で警告を出してスキップ）。

### Security
- .env ファイル生成時に「絶対に Git にコミットしないこと」を明記（config_setup にヘッダを追加）。
- config_setup の対話でシークレット項目はコンソール表示でマスク。

### Notes / Known issues
- research/factor_research.py の calc_momentum 実装が途中で終端（ファイル末尾に不完全な行あり）。研究モジュールは今後の追加実装・テストが必要。
- 一部のコメントに将来の改善案（銘柄別単元対応、価格フォールバックなど）が残っており、今後の拡張ポイントとなる。
- Paper Trading の MockBrokerClient の挙動（fill_mode 等）は設定に依存するため、実運用前に PAPER_FILL_MODE 等の環境変数確認を推奨。

---

今後の予定（例）
- research モジュールの完全実装とユニットテスト追加
- Execution / Monitoring の E2E テストと運用ドキュメント整備
- strategy モジュール（シグナル生成）とデータ取得パイプラインの追加

以上。