# Changelog

すべての変更は Keep a Changelog 準拠で記載します。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

現在のパッケージバージョン: 0.1.0 — 2026-04-18

## [0.1.0] - 2026-04-18

### Added
- 基本アプリケーション構成を実装し、初期リリースを作成。
  - パッケージメタ情報: `__version__ = "0.1.0"` を設定。
- 実行用スクリプトを追加。
  - run_execution.py
    - ExecutionEngine を起動する CLI スクリプト。
    - KABUSYS_ENV が `paper_trading` の場合は専用のペーパートレーディング用 SQLite（data/paper_trading.db）を使用し、本番 DB と完全分離。
    - BrokerClientFactory により環境に応じたブローカークライアントを生成（Mock を含む想定）。
    - Engine の PID ファイル管理、停止フラグ（data/stop_requested.flag）監視、デーモンスレッドでの実行制御を実装。
    - RiskManager、OrderManager、Reconciler の組み立てと ExecutionEngine 起動ロジックを実装。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は KABUSYS_ENV にかかわらず本番用の sqlite_path を使用する仕様。
    - 停止フラグ検出、例外ハンドリング、KeyboardInterrupt での正常終了処理を実装。
- 設定管理・検証・セットアップツールを追加。
  - config.py
    - .env 自動読み込み（プロジェクトルート検出: .git または pyproject.toml）。
    - .env/.env.local の読み込み順序、OS 環境変数保護（上書き禁止）を実装。
    - 複雑な .env 行パースに対応（export プレフィックス、クォート文字列、バックスラッシュエスケープ、インラインコメント処理）。
    - Settings クラスでアプリケーション設定をラップ（各種パス、閾値、フラグ、env 判定など）。
    - PAPER_FILL_MODE のバリデーション（"instant"|"partial"|"never"|"reject"）。
  - config_setup.py
    - 対話式ウィザードで .env の初期作成/更新を支援。
    - 入力ガイド、デフォルト、シークレットマスキング、保存確認を実装。
  - validate_config.py
    - 起動前の設定検証 CLI。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パスや config/*.yaml の存在・パース検証（PyYAML 利用時）。
    - KABUSYS_ENV=live の場合の追加警告（LINE 通知設定、KILL_FLAG_CLEAR_ON_START の危険性）。
    - --strict モードで警告を fail 扱いにできる機能を実装。
- ロギング・プロセス管理ユーティリティを追加。
  - utils/logging_setup.py
    - ルートロガーに対して StreamHandler（stdout）と TimedRotatingFileHandler（日次、30 日保持）を設定。
    - ログディレクトリ自動作成、作成失敗時はファイル出力をスキップしてコンソールのみで継続。
    - ログレベル・ログディレクトリの解決優先度を実装（引数 > 環境変数 > デフォルト）。
  - utils/process_priority.py
    - Windows/Linux/macOS を吸収したプロセス優先度設定（high/normal/low）。
    - CPU affinity を最初の N コアに固定する set_cpu_affinity を実装。
    - 権限エラーや未対応 OS では安全にスキップし、警告を出力。
- ポートフォリオ構築関連の純粋関数群を実装（データベース参照なし、メモリ内演算）。
  - portfolio/portfolio_builder.py
    - select_candidates: スコア降順で上位 N を選出（タイブレークは signal_rank）。
    - calc_equal_weights / calc_score_weights（スコア合計が 0 の場合は等金額配分にフォールバック）。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクターごとの既存エクスポージャーに基づき新規候補を除外。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear）を提供。未知レジームは警告の上 1.0 でフォールバック。
  - portfolio/position_sizing.py
    - calc_position_sizes: risk_based / equal / score の allocation_method をサポート。
    - 単元株（lot_size）丸め、per-position 上限、aggregate cap（利用可能現金でのスケールダウン）、cost_buffer を用いた保守的見積り、端数処理ロジックを実装。
    - 複雑なスケーリング時に残余キャッシュを用いて lot 単位で追加配分するアルゴリズムを実装。
    - TODO コメントで将来の拡張（銘柄別 lot_size など）を明記。
- 分析 / 検証ツールを追加。
  - tools/paper_verification_report.py
    - ペーパートレード用 SQLite を読み、システム稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）、リスク却下数を集計してレポート出力。
    - P95 計算、期間フィルタ（ISO8601 UTC への変換）、閾値による PASS/FAIL 判定ロジックを実装（閾値はスクリプト内定義）。
- 研究用ファクター計算モジュールの開始実装。
  - research/factor_research.py
    - モメンタム / MA200 / ATR / 流動性などのファクター設計と定数を定義。DuckDB 接続を受け取り prices_daily / raw_financials を参照する方針で実装を開始（モジュールは部分実装）。
- 監視 DB 初期化ユーティリティ（monitoring.monitoring_db）や SystemMonitor/ExecutionEngine 等の参照を組み込むスクリプト化（run_* スクリプトで利用）。

### Changed
- ログ出力挙動の統一化:
  - 全起動スクリプトから共通の setup_logging を呼ぶ設計にして、コンソール（stdout）とファイル（日次ローテーション）でのログ管理を統一。
- .env 自動読み込みの挙動を安全化:
  - プロジェクトルートが検出できない場合は自動ロードをスキップ。
  - OS 環境変数は protected として .env による上書きを防止。
- run_monitoring のポーリング間隔を環境変数で設定可能に（MONITOR_POLL_INTERVAL、0 以下は無効扱いでデフォルトにフォールバック）。

### Fixed
- .env パースの改善:
  - export プレフィックス、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメント対応など、より実用的な .env パースを実装して誤認識を低減。
- ログファイルへの書き込み失敗時にプロセスがクラッシュしないよう処理を改善（ディレクトリ作成失敗時はファイルハンドラをスキップしてコンソールログのみで継続）。
- run_execution/run_monitoring における DB 接続の finally ブロックで確実に接続を閉じるようにしてリソースリークを防止。

### Known issues / Notes
- position_sizing.calc_position_sizes:
  - price が欠損（0.0）の場合にエクスポージャーが過小見積りされ、結果的にブロックが外れる可能性がある旨を TODO コメントで明記。将来的に前日終値や取得原価でのフォールバックを検討。
- research/factor_research.py:
  - モジュールは設計と定数を含めて部分実装。calc_momentum 等の関数は実装が途中（スニペットが途中で切れている）であり、完全な計算ロジックは今後追加予定。
- run_monitoring は監視用 DB として常に Settings.sqlite_path（本番想定）を使用する仕様。開発/テスト時は意図的な分離が必要。
- 実行時のプロセス優先度設定は管理者権限やプラットフォームによっては無効化される可能性がある（警告でスキップ）。

### Security
- 本リポジトリは .env に API トークン等のシークレットを保存する設計だが、config_setup.py のヘッダに「.env は絶対に Git にコミットしないこと」を明記。シークレット管理は運用上の注意が必要。

---

今後のリリース案（予定）
- research モジュールの完遂（ファクター計算の完全実装とテスト）
- ExecutionEngine / SystemMonitor の統合テスト、MockBroker 強化
- ポートフォリオ構築の検証・チューニング、銘柄別 lot_size サポート
- モニタリング・アラート（LINE 通知）実装の拡充

もし特定のファイルや機能に関して、より詳細な変更履歴（例えばコミット単位の想定差分）を生成したい場合は、その旨を教えてください。コードからさらに細かい推測を行って追記します。