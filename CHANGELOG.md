# Changelog

すべての変更は Keep a Changelog の形式に準拠しています。  
このファイルは、提供されたコードベースの内容から推測して作成した変更履歴です。実際のコミット履歴がある場合はそちらを優先してください。

全体方針:
- バージョン番号はパッケージ定義（kabusys.__version__ = "0.1.0"）に合わせています。
- 日付は本ファイル作成日 (2026-04-23) を使用しています。

## [Unreleased]
- なし

## [0.1.0] - 2026-04-23

### Added
- コア: 初期リリースとして自動売買システム「KabuSys」の主要モジュールを追加。
  - 実行系・監視系起動スクリプト
    - run_execution.py: ExecutionEngine 起動スクリプトを実装。KABUSYS_ENV に応じて paper_trading 用の MockBrokerClient を利用可能。本番 DB と paper_trading DB を分離（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）。
    - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを実装。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔をオーバーライド可能。監視は環境にかかわらず本番 sqlite_path を使用する設計。
  - 設定・ユーティリティ
    - config.py: 環境変数管理クラス Settings を提供。.env / .env.local の自動読み込み（プロジェクトルート検出）、クォートや export 形式を考慮したパーサ、PAPER_FILL_MODE 等の入力検証を実装。
    - config_setup.py: 対話式 .env 作成ウィザードを実装。シークレットマスク、既存値の再利用、.env テンプレート出力をサポート。
    - validate_config.py: 設定検証 CLI を実装。必須環境変数、DB パス、config/*.yaml の存在と YAML パース（PyYAML が無ければスキップ）、本番環境ガード等をチェック。--strict オプションをサポート。
  - ポートフォリオ構成
    - portfolio/portfolio_builder.py: 候補選定および等比率・スコア重み算出関数を実装（select_candidates, calc_equal_weights, calc_score_weights）。
    - portfolio/risk_adjustment.py: セクター集中制限（apply_sector_cap）と市場レジームに応じた資金乗数（calc_regime_multiplier）を実装。
    - portfolio/position_sizing.py: 株数計算ロジックを実装。allocation_method（risk_based / equal / score）対応、単元株（lot_size）丸め、1銘柄上限・アグリゲート上限・cost_buffer による保守的見積り、総額超過時のスケーリングと残差処理を実装。
  - 監視・検証ツール
    - tools/paper_verification_report.py: ペーパートレード用検証レポート生成スクリプトを実装。稼働率（uptime）、注文成功率（fill rate）、送信率、P95 レイテンシ等を集計し PASS/FAIL 判定を行う（閾値は定数で定義）。
  - ロギング / プロセス制御ユーティリティ
    - utils/logging_setup.py: stdout 出力 StreamHandler と 日次ローテーションする TimedRotatingFileHandler（デフォルト logs/、30日保持）を統一的に設定する setup_logging を実装。ログディレクトリ作成失敗時はファイル出力をスキップする安全設計。
    - utils/process_priority.py: Windows / POSIX の差分を吸収してプロセス優先度（high/normal/low）を設定する set_process_priority と CPU affinity 設定関数 set_cpu_affinity を実装。権限不足等の失敗は警告ログで無害にフォールバック。

### Changed
- 起動処理の安全性・運用性向上
  - 起動直後にプロセス優先度を「high」に設定する処理を実装（実行・監視の両スクリプト）。
  - 起動スクリプトは stop フラグファイル（data/stop_requested.flag）を監視し、検知時に安全終了する仕組みを導入。
  - run_execution は既に停止フラグが立っている場合、エンジンを起動せず終了する挙動を追加。
  - run_execution は ExecutionEngine を別スレッドで実行し、メインスレッドで停止フラグを監視して engine.stop() を呼ぶことでグレースフルシャットダウンを行う。
- 設定ロードの優先度整理
  - .env の自動ロード順を OS 環境 > .env.local > .env とし、既存 OS 環境変数を保護する protected 機能を導入。
- DB 周りの取り扱い
  - monitoring 用 DB テーブルの初期化（init_monitoring_db）を起動時に実行し、冪等に監視テーブルが存在することを保証。
  - run_monitoring は monitoring を常に本番 sqlite_path（Settings.sqlite_path）で操作する旨を明示（環境に依らない監視 DB を使用）。

### Fixed
- 環境変数パースの堅牢化
  - config._parse_env_line でシングル・ダブルクォート内のバックスラッシュエスケープ、export プレフィックス、インラインコメントの取り扱いを改善。
- ロギング初期化時に既存ハンドラを重複追加しないよう、既存ハンドラを flush/close の上でクリアする処理を追加。
- position_sizing のスケーリング処理で端数配分を再現性ある順序で行う（残差ソートにコードを二次キーとして利用）。

### Security
- .env ファイルは生成時に注意書きを付与し、Git にコミットしないよう明記（config_setup の出力テンプレートに記載）。

### Notes / Known limitations
- research/factor_research.py はモメンタム等ファクター計算の骨組みを実装中（ファイル末尾が途中で切れているため未完）。DuckDB を用いた prices_daily / raw_financials 参照設計だが、完全実装は保留。
- 一部の挙動はローカルファイル（data/stop_requested.flag, data/*.db, logs/）に依存するため、本番運用時はファイル配置権限やパス設定を確認してください。
- PAPER_FILL_MODE の受け入れ値は "instant" / "partial" / "never" / "reject" に固定。無効値は ValueError を送出します。
- process_priority / set_cpu_affinity はプラットフォームや権限によって失敗する可能性があり、その場合は警告ログでフォールバックします。

---

今後の改善候補（推奨）
- research/factor_research の完成（欠損部分の実装、ユニットテスト追加）。
- ExecutionEngine / BrokerClientFactory / OrderManager 等の統合テスト、そして paper_trading のモック挙動を検証するテストスイートの整備。
- ログの構造化（JSON 出力）やログ集約（外部ログ管理サービス）対応。
- 単体テスト・CI の導入（config の自動ロードを無効化するフラグ等を利用してテスト可能にする）。
- 単元株（lot_size）を銘柄別に設定できるよう stocks マスタの導入。