CHANGELOG
=========

すべての重要な変更は「Keep a Changelog」フォーマットに準拠して記載しています。

Unreleased
----------

- ドキュメント・内部整理
  - リポジトリ内のモジュール構成や CLI の使い方をコード内 docstring で充実させました（各種起動スクリプト、設定ウィザード、検証ツール、レポートツールなど）。
  - 一部モジュールでログ出力や警告メッセージを改善し、運用時の診断を容易にしています。

0.1.0 - 2026-04-20
-----------------

Added
- 起動スクリプト
  - run_execution.py: ExecutionEngine を起動するエントリポイントを追加。KABUSYS_ENV に応じて paper_trading 用の専用 SQLite を使う（本番 DB と分離）。実行用の PID ファイルと停止フラグを扱い、別スレッドでエンジンを実行・監視します。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。停止フラグ検知時に安全に終了します。Monitoring は環境にかかわらず本番の sqlite_path を使用する仕様です。

- 設定関連ユーティリティ
  - config.py: 環境変数／.env 自動ロード機能を実装。プロジェクトルート（.git または pyproject.toml）を探索して .env/.env.local を読み込みます。値のパースは引用符・エスケープやインラインコメントに対応。Settings クラスで環境変数を型変換・検証して提供します（env, log_level, paper_fill_mode 等の検証含む）。
  - config_setup.py: 対話式 .env 作成ウィザードを追加。必須／任意／シークレット項目を扱い、既存 .env の読み込み・更新をサポートします（.env 書き出し時のテンプレート化）。
  - validate_config.py: 起動前の設定検証 CLI を追加。必須環境変数の存在確認、KABUSYS_ENV / LOG_LEVEL 検証、DB パスの親ディレクトリ確認、config/*.yaml の存在チェックおよび PyYAML があればパース検証を行います。--strict オプションで警告を FAIL 扱いにできます。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py: シグナル選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を実装。スコアが全て 0 の場合は等金額にフォールバックします。
  - portfolio/risk_adjustment.py: セクター集中制限を適用する apply_sector_cap と市場レジームに応じた資金乗数 calc_regime_multiplier を実装。未知レジームは警告を出してフォールバックします。
  - portfolio/position_sizing.py: 銘柄ごとの発注株数決定ロジックを実装（allocation_method: risk_based / equal / score）。単元株（lot_size）丸め、1銘柄上限・aggregate cap（利用可能現金に基づくスケーリング）、cost_buffer を考慮した保守的見積り、残差処理による追加配分を行います。

- ユーティリティ
  - utils/logging_setup.py: 統一的なロギング設定を提供する setup_logging を追加。コンソール（stdout）と日次ローテーションのファイルハンドラ（TimedRotatingFileHandler）をルートロガーに設定。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
  - utils/process_priority.py: Windows / POSIX（Linux, macOS 等）の差分を吸収してプロセス優先度（nice / Windows 優先度）を設定するユーティリティを追加。CPU affinity 設定関数も提供。権限不足や未対応 OS の場合は警告を出して安全にスキップします。

- 監視・運用関連
  - monitoring_db 初期化が idempotent に呼べるように、起動スクリプトから呼び出して監視テーブルの存在を保証する仕様を導入。
  - 停止フラグ（data/stop_requested.flag 等）と PID ファイル（data/execution.pid）を用いた手動停止・監視管理を実装。

- Paper Trading 用ツール
  - tools/paper_verification_report.py: ペーパートレード DB を参照して検証レポートを生成する CLI を追加。稼働率、注文成功率／送信率、P95 レイテンシ等を集計して PASS/FAIL を判定します。閾値はソース内で定義（稼働率 >= 99%、成立率 >= 90% 等）。--from/--to/--db オプションをサポート。

- 研究用モジュール
  - research/factor_research.py: DuckDB を利用したファクター計算フレームワークを追加（モメンタム、ボラティリティ、バリュー、流動性等の仕様と定数を定義）。（実装の一部は継続開発対象）

Changed
- 実行環境の分離
  - KABUSYS_ENV に応じた paper_trading の DB 分離を明確化。paper_trading 実行時は paper_sqlite_path（デフォルト data/paper_trading.db）を使用し、本番監視 DB とは完全に分離されます。

- ログ出力の標準化
  - 全起動スクリプトから setup_logging を呼び出す前提でログ出力を統一。StreamHandler は stdout を使用（cron 等でリダイレクトしやすくするため）。

- 設定読み込みの優先度
  - .env 自動ロード順を OS 環境変数 > .env.local > .env とし、既存の OS 環境変数を保護する仕組みを導入（protected set）。

Fixed
- 環境変数パースの堅牢化
  - .env 読み込み時にクォート文字内のエスケープや export プレフィックス、行内コメントの扱いを改善。無効行・空行・コメント行を安全にスキップするようにしました。

- 監視ループの堅牢化
  - run_monitoring の poll 間隔設定で負の値や不正入力を検出してデフォルトへフォールバックする処理を追加（MONITOR_POLL_INTERVAL の検証と警告）。

Notes / Known issues
- factor_research.calc_momentum など研究系の関数群は計算ロジックの実装が継続中の箇所があります。DuckDB のテーブル構造（prices_daily / raw_financials 等）に依存するため、実データでの確認・チューニングが必要です。
- run_execution / run_monitoring はローカルファイル（data/ 以下）を前提とした停止フラグ・PID 管理を行います。コンテナ運用やクラウド環境での使用時はパス調整や外部プロセス管理との連携が必要になる場合があります。

開発・リリース方針
- この初期リリースでは「起動スクリプト」「設定管理」「ポートフォリオ計算」「監視・検証ツール」「共通ユーティリティ」を一通り揃え、ローカル〜ペーパートレードまでのワークフローを想定しています。
- 今後は研究系ファクター計算の実装完了、Strategy/Execution の統合テスト、自動化・CI 設定、運用向けの監視／アラート機能強化を優先して進める予定です。