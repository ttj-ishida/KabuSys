# Changelog

すべての重要な変更をこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。

- 変更履歴は semantic versioning を意識して記載しています（可能な場合）。
- 日付はリリース日を示します。

[Unreleased]

[0.1.0] - 2026-04-21
----------------------------------------
Added
- 基本アーキテクチャとコアユーティリティ群を追加（初回リリース）。
- コマンドライン起動スクリプト
  - run_monitoring: SystemMonitor のポーリングループ起動スクリプトを追加。  
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止はプロジェクトの `data/stop_requested.flag` ファイルで制御。
    - Monitoring は環境（KABUSYS_ENV）にかかわらず本番用 `sqlite_path` を使用して監視データを記録。
  - run_execution: ExecutionEngine を起動するスクリプトを追加。  
    - `KABUSYS_ENV=paper_trading` の場合は MockBrokerClient を使用し、ペーパートレード用 DB（`data/paper_trading.db`）に記録して本番 DB と分離。
    - 起動前に停止フラグをチェックし、スレッド化されたエンジンを安全に停止可能。
- 設定管理
  - Settings クラスを追加し、環境変数（.env / .env.local を自動読み込み）を統一的に取得する機能を提供。
  - 自動ロードは `KABUSYS_DISABLE_AUTO_ENV_LOAD` で無効化可能。
  - `.env` の読み込みは OS 環境変数を保護（保護キーを上書きしない）する挙動を実装。
  - 多数の設定プロパティを公開（J-Quants / kabu API / DB パス / PID/Kill フラグ /閾値 等）。
  - `PAPER_FILL_MODE` の入力バリデーションを実装（有効値: "instant" / "partial" / "never" / "reject"）。
- 設定支援ツール
  - config_setup: 対話式の .env ウィザードを実装。主要項目（KABUSYS_ENV、API トークン、DB パス、ログレベルなど）を対話的に作成・更新可能。
  - validate_config: 起動前の設定検証 CLI を実装。必須環境変数の未設定検出、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パスや config/*.yaml の存在確認、`live` 環境向けの追加ガード（LINE 未設定や Kill Switch の自動クリア設定の警告）などを行う。`--strict` オプションで警告を FAIL 扱いにできる。
- ロギング
  - utils.logging_setup に統一ロギング設定を実装。  
    - StreamHandler は stdout に出力（cron 等で stdout/stderr をまとめて扱いやすくするため）。  
    - TimedRotatingFileHandler による日次ローテーション（既定 30 世代保持）をサポート。ログディレクトリは引数 / 環境変数 `LOG_DIR` / デフォルト `logs/` の順で解決。
    - 既存ハンドラをクリアして多重設定を防止。
- プロセス制御ユーティリティ
  - utils.process_priority によりプラットフォーム差分を隠蔽してプロセス優先度（high/normal/low）を設定可能。Windows/Linux/macOS に対応しつつ失敗時は警告でスキップ。
  - CPU affinity 設定関数 `set_cpu_affinity` を追加（指定コア数にプロセスをピン留め）。
- ポートフォリオ構築（純粋関数群）
  - portfolio.portfolio_builder: 候補選定（select_candidates）、等分配（calc_equal_weights）、スコア加重（calc_score_weights。全スコア 0 の場合は等分配にフォールバック）を実装。
  - portfolio.risk_adjustment: セクター集中抑制（apply_sector_cap）と市場レジームに応じた乗数（calc_regime_multiplier）を実装。未知レジームは警告を出してフォールバック。
  - portfolio.position_sizing: 発注株数算出ロジックを実装（risk_based / equal / score の配分方式をサポート）。  
    - lot_size（単元）丸め、1銘柄上限 / aggregate cap のスケーリング、cost_buffer を考慮した保守的見積り、残差処理による追加配分ロジック等を実装。
- ペーパートレード検証ツール
  - tools.paper_verification_report: ペーパートレードの検証レポート生成スクリプトを追加。  
    - 日付範囲フィルタ（--from / --to）と DB パス指定（--db / 環境変数）に対応。  
    - システム稼働率、注文成功率（Filled/Created）、送信率（Sent/Created）、リスク却下数、レイテンシ（avg/max/P95）を集計して判定（PASS/FAIL、閾値はコード内定義）。
    - P95 計算、データ欠損時の N/A 表示やクエリエラーのフォールバックを実装。
- データベース関連
  - monitoring_db 初期化（init_monitoring_db）を実行して監視テーブルの存在を保証（冪等）。
  - DuckDB 接続サポート（分析用）と SQLite（監視 / ペーパートレード用）を併用。
- 研究モジュール（基盤）
  - research.factor_research の基盤を追加（モメンタム等のファクター計算の設計と一部実装を含む）。DuckDB を用いた prices_daily/raw_financials 参照に基づく計算設計。

Changed
- ログ出力設計: コンソール出力を stderr ではなく stdout に統一（cron/タスクスケジューラとの互換性向上）。
- .env 自動読み込み: プロジェクトルートの検出を __file__ ベースで行うようにし、CWD 非依存での動作を可能に。OS 環境変数を保護しつつ `.env.local` を上書き読み込みできるようにした。

Fixed
- 環境変数パースの堅牢化:
  - export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ処理、インラインコメント扱いの改善を実装。
  - クォートなし値の '#' によるコメント判別をスペース前提で行い誤検出を防止。
- run_monitoring / run_execution の停止処理を改善:
  - stop flag ファイル検査と KeyboardInterrupt ハンドリングにより安全に終了するようにした。
  - run_execution はスレッド実行中に停止フラグ検知で engine.stop() を呼ぶことで安全にシャットダウン。

Notes / Misc
- バージョンはパッケージの __init__ にて "0.1.0" に設定。
- いくつかの箇所で TODO コメントが残っており、将来的な拡張（例: 銘柄ごとの lot_size マスタ、価格フォールバック等）を見越した設計になっています。
- config/*.yaml の内容検証は PyYAML の有無に依存するため、未インストール時はパース検証をスキップして警告を出します。

(参考) 関連ファイル
- スクリプト: src/kabusys/run_monitoring.py, src/kabusys/run_execution.py
- 設定: src/kabusys/config.py, src/kabusys/config_setup.py, src/kabusys/validate_config.py
- ユーティリティ: src/kabusys/utils/logging_setup.py, src/kabusys/utils/process_priority.py
- ポートフォリオ: src/kabusys/portfolio/*
- ペーパートレード検証: src/kabusys/tools/paper_verification_report.py
- 研究モジュール: src/kabusys/research/factor_research.py

----------------------------------------
リンク: [0.1.0]: https://example.com/compare/v0.0.0...v0.1.0 (必要に応じて差分リンクを設定してください)