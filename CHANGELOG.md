# CHANGELOG

すべての変更は Keep a Changelog 形式に従い、重要性の高い変更をカテゴリ別にまとめています。

全般: 初期パブリッシュ（バージョン 0.1.0）。日付はリリース作成日です。

## [0.1.0] - 2026-04-18

### 追加
- 基本フレームワークを初期実装しました。主要なコンポーネントと CLI を含みます。
  - 実行系 / 監視系
    - run_execution.py: ExecutionEngine 起動用スクリプトを追加。
      - KABUSYS_ENV=paper_trading 時は専用のペーパートレード用 SQLite（data/paper_trading.db、環境変数 PAPER_TRADING_SQLITE_PATH で上書き可）を使用し、MockBrokerClient を経由して発注を模擬可能。
      - エンジンはスレッドで実行され、data/stop_requested.flag の検出で安全に停止可能。実行 PID を data/execution.pid に記録する仕組み（設定からの pid_file_path 指定にも対応）。
      - RiskManager の既定設定（最大ポジション比率、利用率、レート制限、サーキットブレーカー、初期ポートフォリオ値等）を組み込み。
    - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
      - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバックし、警告ログを出力。
      - 監視は KABUSYS_ENV にかかわらず本番用 sqlite_path を使用する（monitoring データは単一の DB に集約）。
      - 停止フラグ（data/stop_requested.flag）検出でループを抜け、接続をクローズして終了。

  - 設定管理
    - config.py: 環境変数・設定管理を実装。
      - プロジェクトルート検出ロジック（.git または pyproject.toml）を採用し、.env / .env.local を自動読み込み（OS 環境変数は保護）。
      - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能。
      - .env パースは export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント（クォートなしの '#' の扱い）に対応。
      - Settings クラスを提供し、必須キー取得（_require）や各種設定プロパティ（duckdb/sqlite パス、PID/kill フラグパス、閾値、env/log_level 判定、paper_trading 用設定など）を実装。値検証（有効値チェック、例: KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE）を行う。
    - config_setup.py: 対話式 .env ウィザードを追加。
      - .env の初期作成・更新を補助。シークレット項目はマスクして表示。既存 .env の読み込みと Enter による再利用機能あり。
      - 最終確認後に .env を安全に書き込む。デフォルトや説明付きの項目を多数用意（KABUSYS_ENV、JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DUCKDB_PATH、SQLITE_PATH、LOG_LEVEL、KILL_FLAG_CLEAR_ON_START 等）。
    - validate_config.py: 起動前の設定検証 CLI を追加。
      - 必須環境変数の存在検査、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ確認、config/*.yaml の存在・パースチェック（PyYAML がある場合）、本番環境向けのガード（LINE 通知設定・KILL_FLAG_CLEAR_ON_START の注意喚起）を実装。
      - --strict オプションで警告も失敗扱いにできる。

  - ロギング / プロセス管理ユーティリティ
    - utils/logging_setup.py: 統一的なログ設定ユーティリティを追加。
      - StreamHandler（stdout）と TimedRotatingFileHandler（日次、デフォルト 30 日保持）をルートロガーに構成。既存ハンドラは再設定前に閉じる。
      - ログレベル・ログディレクトリの解決順を定義（引数 > 環境変数 > デフォルト）。
      - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで動作。
    - utils/process_priority.py: プロセス優先度 / CPU affinity 設定ユーティリティを追加。
      - Windows と POSIX（Linux/Mac/FreeBSD）向けの差分を吸収して set_process_priority を提供（"high"/"normal"/"low"）。
      - set_cpu_affinity により最初 N コアに固定する機能を提供。権限不足や未対応環境では警告を出してスキップ。

  - ポートフォリオ構築関連モジュール
    - portfolio/portfolio_builder.py: 候補選定と重み計算（score/equal）を実装。
      - select_candidates: スコア降順、signal_rank でのタイブレーク。
      - calc_equal_weights / calc_score_weights: 等金額配分・スコア正規化配分。スコア合計が 0 の場合は警告を出して等配分にフォールバック。
    - portfolio/risk_adjustment.py: セクター集中制限（apply_sector_cap）およびレジーム乗数（calc_regime_multiplier）を実装。
      - apply_sector_cap: 現在のポジション評価額と portfolio_value に基づきセクター上限を超える場合は当該セクターの新規候補を除外（"unknown" セクターは除外しない）。
      - calc_regime_multiplier: "bull"/"neutral"/"bear" に対する乗数を定義（未知のレジームは 1.0 でフォールバック、警告出力）。
    - portfolio/position_sizing.py: 発注株数計算を実装。
      - allocation_method に "risk_based"（リスクベース）と "equal"/"score" をサポート。
      - lot_size（単元株）丸め、1銘柄上限（max_position_pct）、全体利用率（max_utilization）、コストバッファを考慮した aggregate cap スケーリング処理を実装。
      - スケールダウン時は小数部分（lot 単位での端数）を残差に基づき追加配分するロジックを導入し、安定なソートで再現性を確保。

  - 解析・検証ツール
    - tools/paper_verification_report.py: Paper Trading の検証レポート生成ツールを追加。
      - sqlite の paper_trading DB からシステム稼働率、注文成功率、送信率、リスク却下数、API レイテンシ（平均/最大/P95）を集計し PASS/FAIL 判定を行う（デフォルト閾値を含む）。
      - 日付範囲フィルタ（--from/--to）と DB パス指定（--db / PAPER_TRADING_SQLITE_PATH）をサポート。
      - P95 の算出やデータ欠損時の N/A 取り扱い、SQL の実行失敗に対するフォールバック処理を実装。

  - 研究モジュール（基盤）
    - research/factor_research.py: ファクター計算モジュールの骨格を追加（モメンタム等の計算方針、定数定義、DuckDB を利用した prices_daily/raw_financials 参照ポリシーを導入）。
      - 設計方針、使用ファクター一覧、日数パラメータ等を明確化（関数 calc_momentum 等の実装開始）。

  - パッケージ情報
    - __init__.py によるバージョン定義 __version__ = "0.1.0"。

### 変更
- 初期リリースのため関連する設計仕様や README に基づく実装が行われています（詳細はソース内ドキュメント・コメント参照）。
- 環境変数の自動読み込み順序・保護ロジックを導入（OS 環境変数は上書きされないよう保護）。

### 修正
- 初期リリースのため既知のバグ修正は無し。今後の運用で実際の動作確認に基づくバグ修正が予定されています。

### 注意事項 / 既知の制約
- process_priority と CPU affinity の設定は OS 権限によって失敗する場合があり、その場合は警告ログを出して処理をスキップします。
- position_sizing の価格欠損（price が 0.0 の場合）に関する注記あり（現状はスキップするが将来的にフォールバック価格取得を検討）。
- .env 自動読み込みはプロジェクトルートの特定に依存する（.git または pyproject.toml が見つからない場合は自動ロードをスキップ）。
- config/*.yaml の検証は PyYAML インストールが必要（未インストール時はパース検証をスキップし警告を出す）。

---

今後の予定（ロードマップの一例）
- ExecutionEngine, SystemMonitor の追加ユニットテストと統合テスト。
- research/factor_research の各ファクター実装完了と検証。
- 発注・ブローカーまわりのフェイルオーバーと詳細なログ強化。
- 設定ウォーニングの改善とドキュメント整備。

（以上）