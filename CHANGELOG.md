# Changelog

すべての変更は Keep a Changelog の形式に準拠して記載しています。  
このファイルはコードベースの内容から推測して作成しています（実装上の意図や設計を読み取って要約しています）。

## [0.1.0] - 2026-04-18

### Added
- 基本パッケージ初期実装を追加
  - パッケージバージョン: `__version__ = "0.1.0"`（src/kabusys/__init__.py）。
- 環境設定周り
  - Settings クラスを実装（src/kabusys/config.py）。環境変数から各種設定を取得し、値検証を実施。
    - J-Quants / kabuステーション / LINE / DB パス / 監視閾値などのプロパティを提供。
    - KABUSYS_ENV、LOG_LEVEL、PAPER_FILL_MODE 等の妥当性チェックを実装。
  - .env 自動ロード機構を実装（プロジェクトルートを .git / pyproject.toml で探索）。
  - `.env` ファイルのパースは引用符・エスケープ・`export KEY=val` に対応。
- 環境設定ユーティリティ
  - 対話式ウィザード `config_setup` を実装（src/kabusys/config_setup.py）。
    - .env 初期作成 / 更新を対話形式で支援し、テンプレート書き出し機能を提供。
- 設定検証 CLI
  - `validate_config` を実装（src/kabusys/validate_config.py）。
    - 必須環境変数や DB パス、config/*.yaml の存在・パース検証（PyYAML 未導入時はスキップの警告）。
    - `--strict` オプションで警告を失敗として扱う。
- 起動スクリプト
  - 実行エンジン起動スクリプト `run_execution`（src/kabusys/run_execution.py）。
    - 起動時にプロセス優先度を "high" に設定。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite（デフォルト: data/paper_trading.db）を使用して本番 DB と分離。
    - BrokerClientFactory によりブローカークライアントを生成し、OrderRepository / OrderManager / RiskManager / Reconciler / ExecutionEngine を組み立ててエンジンをスレッドで起動。
    - 停止フラグ（data/stop_requested.flag）と PID ファイルの取り扱いに対応。
  - 監視ループ起動スクリプト `run_monitoring`（src/kabusys/run_monitoring.py）。
    - `MONITOR_POLL_INTERVAL` 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒、無効値はフォールバック）。
    - 監視は環境変数にかかわらず監視用（本番）sqlite_path を使用する旨の設計になっている（ドキュメント化）。
    - SystemMonitor の 1 回チェック実行と例外ハンドリング、停止フラグ検知での安全終了対応。
- ロギング・プロセスユーティリティ
  - 統一ロギング初期化ユーティリティ `setup_logging` を追加（src/kabusys/utils/logging_setup.py）。
    - stdout 出力の StreamHandler と日次ローテーションの TimedRotatingFileHandler（デフォルト logs/、30日保持）をルートロガーに設定。
    - LOG_DIR 環境変数や引数でログ出力先を上書き可能。ディレクトリ作成失敗時はファイル出力をスキップして stdout のみで継続。
  - プロセス優先度 / CPU affinity 設定ユーティリティ `process_priority` を追加（src/kabusys/utils/process_priority.py）。
    - Windows / POSIX（Linux/macOS/FreeBSD）差分を吸収して `set_process_priority(level)` を提供。
    - `set_cpu_affinity(cpu_count)` によるコアピンニング機能も実装。権限不足等は警告でスキップ。
- ポートフォリオ構築ライブラリ（純粋関数群）
  - 銘柄選定・重み計算（src/kabusys/portfolio/portfolio_builder.py）
    - select_candidates（スコア降順、同点時は signal_rank でタイブレーク）
    - calc_equal_weights / calc_score_weights（スコア合計が 0 の場合はフォールバック）
  - セクター集中制限・レジーム乗数（src/kabusys/portfolio/risk_adjustment.py）
    - apply_sector_cap（既存ポジションを基にセクター上限をチェックして候補除外）
    - calc_regime_multiplier（"bull"/"neutral"/"bear" に対する乗数、未知時は警告して 1.0 にフォールバック）
  - 株数決定・リスク制限（src/kabusys/portfolio/position_sizing.py）
    - risk_based / equal / score ベースの発注株数計算、単元（lot_size）丸め、aggregate cap によるスケールダウン処理、cost_buffer を考慮した保守的見積り。
  - ポートフォリオ API をパッケージエクスポート（src/kabusys/portfolio/__init__.py）。
- Paper Trading 検証ツール
  - `tools/paper_verification_report.py` を追加
    - Paper Trading 用 SQLite（デフォルト data/paper_trading.db）から稼働率、注文成功率、送信率、レイテンシ（平均 / 最大 / P95）を算出してレポート出力。
    - PASS/FAIL 基準（閾値）を固定値で定義（稼働率 >= 99%、fill_rate >= 90% 等）。CLI オプションで期間指定・DB パス上書き可。
- 研究/ファクター計算（骨格）
  - `research/factor_research.py` を追加（モメンタム / MA200 / ATR / 流動性などの計算方針を実装する設計）。
    - DuckDB 接続を受け取り prices_daily / raw_financials を参照してファクターを返すことを想定。

### Changed
- ログ出力の標準化
  - 全起動スクリプトから `setup_logging(app_name=...)` を呼ぶ設計にしてログ出力を統一。
  - ログの StreamHandler は stdout を使用（cron / scheduler でのリダイレクト運用を考慮）。
- DB パスの取り扱い
  - run_execution は paper_trading 環境時に専用 SQLite（PAPER_TRADING_SQLITE_PATH）を使用して本番 DB と分離する設計に変更（安全設計）。
  - run_monitoring は「監視は本番 sqlite_path を使用する」旨が明示されている（環境に依存しない監視データの一元化を意図）。
- .env 読み込みの優先順位と保護
  - OS 環境変数 > .env.local > .env の優先順位で自動ロードを行い、既存の OS 環境変数は保護（上書きされない）。
  - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能（テスト等の用途を想定）。

### Fixed
- 環境変数パースの堅牢化
  - .env 行パーサはコメント、引用符、エスケープ、`export` プレフィックスに対応。無効行を無視することで誤った .env による起動失敗を軽減。
- 実行時の安全停止
  - run_execution / run_monitoring 共に data/stop_requested.flag を用いた外部停止制御を実装。KeyboardInterrupt も正しくハンドリングしてリソースをクローズするように調整。

### Notes / Known limitations
- research/factor_research.py はファクター計算の骨格・定数や設計方針を実装しているが、ファイル末尾が実装途中の状態（スニペットの切れ等）となっている箇所があるため、完全な関数実装は追加作業が必要です。
- 実際のブローカークライアント実装（BrokerClientFactory, ExecutionEngine 内部の詳細）は本変更でのファイル参照があるものの、本ログの対象スニペットに完全な実装が含まれていないため、外部モック / 実装との結合テストが必要です。
- ロギングディレクトリ作成やプロセス優先度設定は権限に依存し、失敗時は警告にフォールバックする設計です（安全なデフォルト動作を維持）。
- Paper Trading の検証閾値は現状ハードコード（スクリプト内定義）になっているため、将来的に設定ファイル化が望ましい。

## 0.1.0 より前
- 初期リリース（最初の公開バージョン）として上記機能をまとめてリリース。

---

この CHANGELOG はコード内容からの推測に基づいて作成しています。実際のリリース文書やリリース日、細かい変更履歴はリポジトリのコミット履歴やリリースノートに基づいて確定してください。必要であれば、各モジュールごとにより詳細な「変更点」「設計の説明」「使用例」なども作成できます。どの部分を詳述しますか？