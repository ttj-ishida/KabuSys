CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠して記載しています。  
慣例:
- 追加: 新機能や公開 API
- 変更: 既存挙動の変更や改善
- 修正: バグ修正や堅牢性向上
- 注意: 既知の制限や作業中の箇所

[Unreleased]
------------

- ドキュメント化・小改善
  - 内部関数やCLIの出力メッセージをより明確にしました（ログ・標準出力のメッセージ改善）。
  - 一部モジュールのログレベル設定や警告メッセージを調整しました。

0.1.0 - 2026-04-24
------------------

Added
- 実行/監視用の起動スクリプトを追加
  - run_execution.py: ExecutionEngine を起動するスクリプト。KABUSYS_ENV=paper_trading の場合は Paper Trading 用の専用 SQLite（data/paper_trading.db 既定）を使用し、MockBrokerClient を利用できる設計になっています。停止フラグ（data/stop_requested.flag）と PID ファイル（data/execution.pid）に対応。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境にかかわらず本番 sqlite_path を使用するよう設計。

- 設定管理と CLI ツール
  - config.py: 環境変数 / .env 自動読み込み機能を実装（プロジェクトルート検出: .git / pyproject.toml を基準）。自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能。export 形式・クォート・インラインコメントのパース対応を実装。Settings クラスを提供し、各種設定（DB パス、ログレベル、閾値、paper_trading 関連設定など）をプロパティとして取得可能に。
  - config_setup.py: 対話式ウィザードで .env を生成/更新する CLI を追加。秘密項目はマスク表示、既存 .env 読み込み・デフォルト表示に対応。
  - validate_config.py: 起動前に .env と config/*.yaml を検証する CLI を追加。必須環境変数チェック、パスの存在チェック、YAML のパースチェック（PyYAML が存在する場合）や本番時のガードチェックを実装。--strict オプションで警告を FAIL 扱いにする機能を追加。

- ロギング/プロセス管理ユーティリティ
  - utils/logging_setup.py: StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション、30 日保持）をルートロガーに設定する共通ユーティリティを追加。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソール出力のみで継続する堅牢な実装。
  - utils/process_priority.py: Windows / POSIX の差分を吸収したプロセス優先度設定ユーティリティと CPU affinity 設定関数を追加。権限不足や未サポート環境では警告を出してスキップする安全設計。

- ポートフォリオ構築ライブラリ（純粋関数群）
  - portfolio/portfolio_builder.py: 候補選定（select_candidates）、等配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を実装。スコアが全て 0 の場合は等配分にフォールバック。
  - portfolio/risk_adjustment.py: セクター集中制限を適用する apply_sector_cap、レジームに応じた投下資金乗数 calc_regime_multiplier を実装（"bull"/"neutral"/"bear" に対応。未知レジームは警告後 1.0 でフォールバック）。
  - portfolio/position_sizing.py: 発注株数計算ロジックを実装。allocation_method（"risk_based" / "equal" / "score"）に対応、単元株丸め、per-position 上限、aggregate cap（available_cash を超えた場合のスケールダウンと残差配分ロジック）を含む。cost_buffer による保守的見積りもサポート。

- 検証 / レポートツール
  - tools/paper_verification_report.py: Paper Trading の SQLite データを解析して検証レポートを生成するスクリプトを追加。稼働率、注文成功率、送信率、リスク却下数、API レイテンシ（平均/最大/P95）を算出し、閾値に基づく PASS/FAIL 判定を出力。コマンドラインで期間指定や DB パス指定が可能。

- データ分析/リサーチ基盤（骨組み）
  - research/factor_research.py: ファクター計算モジュールの骨組みを追加。DuckDB 接続を受けて prices_daily / raw_financials を参照し、Momentum / Value / Volatility / Liquidity ファクターを算出する設計（モジュール内定数、計算方針、インターフェイス設計を含む）。（一部実装は進行中）

Changed
- run_execution / run_monitoring の起動フロー
  - どちらのスクリプトでも起動直後に set_process_priority("high") を呼び出してプロセス優先度を上げるようにし、重要プロセスの応答性を改善。
  - run_execution は paper_trading 時に別 DB を使用することで本番 DB と完全分離を確保。init_monitoring_db を呼び出して監視テーブルが存在することを冪等に保証。

- .env 自動読み込みの優先度
  - OS 環境変数 > .env.local > .env の順で読み込む実装。既存 OS 環境変数を保護するため protected オプションを導入。

- ログ出力の統一
  - StreamHandler を stdout に固定し、cron 等で stdout/stderr を統合して扱う運用を想定。

Fixed
- 環境変数パースの強化
  - export プレフィックス、クォート内のバックスラッシュエスケープ、インラインコメントの扱いなど、.env パースの頑健性を向上。

- 監視ループの安全性向上
  - MONITOR_POLL_INTERVAL のパースで不正な値（0 以下や数値でない文字列）に対して警告を出し、デフォルト（60 秒）にフォールバックするようにした（time.sleep に負の値を渡すリスクを回避）。
  - SystemMonitor.check_once() 呼び出しで例外が発生しても監視ループが停止せず、例外ログを残して次のポーリングに進むように保護。

- 起動時の停止フラグ対応
  - run_execution は起動前に停止フラグを確認して既に停止が要求されている場合は起動を中止するようにした。実行中も停止フラグ検出で ExecutionEngine.stop() を呼び出して安全に停止を試みる。

Notes / Known issues
- research/factor_research.py はファイル末尾付近で実装が途中のまま（ソースの途中で切れている）。ファクター計算の SQL/実装は今後の実装・テストが必要。
- 実運用での安全性（API キーの扱い、PID/flag ファイルの権限、単体テスト）は別途運用ガイド／テスト追加を推奨。
- position_sizing の lot_size は現状全銘柄共通の想定。将来的に銘柄別単元対応の拡張を予定。

Security
- 環境変数ファイル（.env）の生成スクリプトは .env を絶対に Git にコミットしないよう注記を出力。秘密項目は UI 上でマスク表示しますが、ファイルの保存・配布は運用で注意が必要です。

以上。必要であれば、バージョンごとの変更をもっと細かく分ける（例: run_monitoring の独立リリースなど）か、未実装箇所のタスクリスト化を作成します。どの形式を優先しますか？