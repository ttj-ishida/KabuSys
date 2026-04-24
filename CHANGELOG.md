CHANGELOG
=========

すべての注記は Keep a Changelog の記法に準拠しています。
タグ付け前の開発中の変更は [Unreleased] に記載します。

[Unreleased]
-------------

- ドキュメント整備・軽微なリファクタ
- テスト・デバッグ用メッセージやログ出力の改善

[0.1.0] - 2026-04-11
-------------------

Added
- 初回公開リリース。
- 実行スクリプト:
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV=paper_trading の場合は専用の paper_trading DB を使用し、MockBrokerClient 経由でペーパートレードを実行する（本番 DB と完全分離）。停止用フラグファイルや実行 PID ファイルのサポートを追加。
  - run_monitoring.py: SystemMonitor をポーリング実行する監視ループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能。停止フラグ検知で安全に終了。
- 設定・環境管理:
  - config.py: 環境変数読み込み・ラッパ（Settings クラス）を実装。.env 自動ローディング（プロジェクトルート検出）と環境値の取得ユーティリティを提供。
  - config_setup.py: 対話式ウィザードで .env を生成・更新する CLI を追加（シークレット入力・既存値の再利用・保存確認）。
  - validate_config.py: 起動前検証 CLI を追加。必須環境変数、KABUSYS_ENV、DBパス、config/*.yaml の存在とパースを検査。--strict オプションで警告を FAIL 扱いにできる。
- ロギング・プロセス制御ユーティリティ:
  - utils/logging_setup.py: ルートロガーの統一設定。コンソール出力（stdout）と日次ローテーションのファイル出力を設定。ログレベル/ディレクトリは環境変数や引数で上書き可能。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソール出力のみで継続。
  - utils/process_priority.py: マルチプラットフォーム（Windows / POSIX）でプロセス優先度設定と CPU affinity 設定を提供。権限不足などの失敗は警告ログにより安全にスキップ。
- ポートフォリオ構築:
  - portfolio/portfolio_builder.py: シグナル選定（score 降順 + tie-breaker）と等分配/スコア加重配分の関数を実装。スコア合計が 0 の場合は等分配へフォールバックして警告を出力。
  - portfolio/risk_adjustment.py: セクター集中制限適用関数（apply_sector_cap）と市場レジームに基づく資金乗数（calc_regime_multiplier）を実装。Unknown セクターの扱いやレジームのデフォルトフォールバックを明示。
  - portfolio/position_sizing.py: 発注株数決定ロジックを実装（allocation_method: risk_based / equal / score）。単元株（lot_size）丸め、1銘柄上限、aggregate cap（利用可能現金）に基づくスケールダウン、残差分の優先配分ロジックを実装。コストバッファを考慮した保守的な見積りに対応。
- 分析・レポート:
  - tools/paper_verification_report.py: Paper Trading 用検証レポートを追加。システム稼働率、注文成立率・送信率、リスク却下数、API レイテンシ（平均/最大/P95）を算出し、閾値に基づく PASS/FAIL 判定を行う。P95 計算、日付フィルタ、DB パス指定オプションをサポート。
  - research/factor_research.py: ファクター計算モジュール（Momentum 等）を追加（DuckDB 接続による prices_daily/raw_financials の参照を想定）。モメンタム指標（1M/3M/6M、MA200乖離）などの計算インターフェースを提供（実装途中の箇所あり）。
- DB / 分析基盤:
  - DuckDB 連携を追加（duckdb 接続を各処理で利用）。監視テーブル初期化ユーティリティ（init_monitoring_db）により監視用テーブルを冪等に準備。

Changed
- .env 自動読み込みの挙動を明文化: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロードを無効化。プロジェクトルート検出に .git または pyproject.toml を使用し、CWD に依存しない方式に改善。
- run_monitoring: Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path（監視 DB）を利用する旨を明示（運用上の設計決定）。
- run_execution: 起動時にプロセス優先度を最初に High に設定するよう順序を調整。ペーパートレード時の DB パス分離を明確化。
- ロギング: StreamHandler は stdout を使う（stderr と分離してリダイレクト運用しやすくした）。
- .env パースロジックを強化: export プレフィックス、クォート（シングル／ダブル）内のエスケープ、インラインコメントの扱い、空行/コメント行のスキップをサポート。

Fixed
- MONITOR_POLL_INTERVAL の不正な値（0 以下や非数）に対してデフォルト（60秒）へフォールバックするバリデーションを追加。ログで警告を出力。
- calc_score_weights: 全銘柄のスコア合計が 0 の場合に等金額配分へフォールバックし、警告ログを出すようにして division-by-zero を回避。
- logging_setup: ログディレクトリ作成に失敗した場合でもアプリが致命的に停止しないようにハンドリングを改善（ファイルハンドラの作成失敗を警告してコンソール出力にフォールバック）。
- process_priority: 権限不足や未サポートプラットフォームでの例外をキャッチして安全にスキップ（警告ログ）するよう改良。

Security
- .env の秘密情報は config_setup の対話でマスク表示（既存値は **** で表示）し、.env を絶対に Git にコミットしない旨の注意を出力。

Notes / Operational details
- 停止制御: data/stop_requested.flag（プロジェクトルート配下）を設置することで実行中の監視・実行ループを安全に停止できる仕組みを提供。
- PID ファイル: 実行エンジンは data/execution.pid を使用し、外部からプロセスの管理が可能。
- Paper Trading 運用: PAPER_FILL_MODE（instant/partial/never/reject）や PAPER_TRADING_SQLITE_PATH により挙動や DB を制御可能。
- validate_config による事前チェックを利用することで、本番環境（KABUSYS_ENV=live）での誤設定リスクを低減できる（LINE 通知設定の未設定や Kill Switch の自動クリア設定などは警告対象）。

Credits
- 初期実装および設計はプロジェクト内部実装に基づく推測を元に作成されています。実際の変更履歴を厳密に反映していない箇所がある可能性があります。必要であれば、コミット履歴から正確な CHANGELOG を生成できます。