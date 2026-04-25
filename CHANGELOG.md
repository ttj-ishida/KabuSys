# CHANGELOG

すべての変更履歴は Keep a Changelog の形式で記載します。  
このプロジェクトの初版リリース v0.1.0 に含まれる主な追加・変更・修正を日本語でまとめています。

※ 日付はソースコード内の記述・実装状況から推定しています。

## [Unreleased]

## [0.1.0] - 2026-04-25

### Added
- 初期リリースを追加（パッケージバージョン: 0.1.0）。
- 実行エントリスクリプトを追加
  - run_execution.py: ExecutionEngine 起動スクリプト。KABUSYS_ENV=paper_trading の場合はペーパートレード用 DB/モックブローカーを利用する挙動をサポート。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL によるポーリング間隔上書きをサポート。
- 環境設定関連 CLI を追加
  - config_setup.py: 対話式 .env 作成/更新ウィザード（.env のテンプレート出力・保存機能）。
  - validate_config.py: 起動前検証ツール。必須環境変数、パス、config/*.yaml の存在・パース等をチェック。`--strict` オプションで警告を失敗扱いにできる。
- Paper Trading 検証ツールを追加
  - tools/paper_verification_report.py: ペーパートレード用 SQLite を解析して稼働率・注文成功率・レイテンシ等のレポートを生成する CLI。
- 設定管理モジュールを追加
  - config.py: Settings クラス（環境変数アクセスラッパー、.env 自動読み込み、プロジェクトルート自動検出、各種設定のバリデーション）。
    - .env 自動読み込み: プロジェクトルート（.git または pyproject.toml を基準）を探索し .env/.env.local を読み込み（OS 環境変数は保護）。
    - .env の行パーサを実装（export 形式、引用符、エスケープ、インラインコメント対応）。
    - PAPER_FILL_MODE、KABUSYS_ENV、LOG_LEVEL 等の検証とデフォルト値を提供。
    - paper_trading 用 DB パス、pid/kill フラグパス、監視閾値等をプロパティとして提供。
- ポートフォリオ構築関連モジュールを追加（純粋関数群）
  - portfolio/portfolio_builder.py: 候補選定・等配分・スコア配分（score が全て 0 の場合のフォールバック）。
  - portfolio/risk_adjustment.py: セクター集中制限（apply_sector_cap）、レジームに応じた乗数計算（calc_regime_multiplier）。
  - portfolio/position_sizing.py: 発注株数算出（risk_based / equal / score）、単元株丸め、aggregate cap によるスケールダウン・端数処理（lot 単位での再配分）。
  - package export を portfolio/__init__.py にて公開。
- research/factor_research.py: ファクター計算モジュールの骨子（モメンタム・MA200・ATR 等の計算方針と定数群を定義）。
- ユーティリティを追加
  - utils/logging_setup.py: ルートロガーの統一設定ユーティリティ（stdout StreamHandler、日次ローテートのファイルハンドラ、ログディレクトリ解決）。
  - utils/process_priority.py: psutil を用いたプロセス優先度設定と CPU affinity 設定（Windows / POSIX を吸収）。
- モニタリング用 DB 初期化ユーティリティ（monitoring.monitoring_db 参照の初期化呼び出し）を起動スクリプトから呼ぶ実装を追加。
- __init__.py にプロジェクトバージョンと主要パッケージエクスポートを追加。

### Changed
- ロギング挙動
  - StreamHandler に stdout を使用（stderr ではなく）。cron/タスクスケジューラ等からのリダイレクト運用を考慮。
  - ログディレクトリ作成失敗時はファイルハンドラの作成をスキップしてコンソール出力のみ継続するフェイルセーフを導入。
  - 既存ハンドラをクリアしてから再設定することで二重ハンドラ設定を防止。
- run_execution の DB 接続ロジックを環境に応じて分離
  - paper_trading 環境では paper_sqlite_path（デフォルト data/paper_trading.db）を使用し、本番 DB と完全分離。
  - 監視テーブル初期化（init_monitoring_db）は冪等的に呼び出されるように実装。
- run_monitoring は環境にかかわらず本番 sqlite_path を使用する旨を明示（監視用データは本番 DB を参照）。
- .env の読み込み振る舞い
  - .env/.env.local の読み込み順序と上書きルールを明記（OS 環境変数を保護しつつ .env.local で上書き可能）。
- process_priority の挙動
  - Windows と POSIX（Linux/Mac 等）で適切な優先度値を選ぶ実装に。未対応 OS の場合はスキップして警告出力。

### Fixed / Robustness
- .env パーサの強化
  - export KEY=val 形式のサポート、シングル/ダブルクォート内のバックスラッシュエスケープ処理、インラインコメント処理の改善。
  - 無効行や空行、コメント行のスキップ等を安定化。
- _get_poll_interval（run_monitoring）の入力検証を追加
  - 環境変数 MONITOR_POLL_INTERVAL が不正（非整数・0 以下など）の場合にデフォルトにフォールバックして警告を出力。
- process_priority / set_cpu_affinity での例外処理強化
  - psutil.AccessDenied 等で失敗した場合に警告して処理を継続するようにした。
- run_execution / run_monitoring の停止制御
  - data/stop_requested.flag による外部停止フラグ検知を導入し、優雅なシャットダウン処理を実装。
- paper_verification_report の集計ロジックでデータ不足・テーブル未存在時に例外を吸収して N/A 相当を返すようにし、ツールの堅牢性を向上。
- position_sizing のスケーリング処理で端数配分ロジックを導入し、利用可能現金に合わせた再配分を実装。価格未取得時のスキップ処理を明確化。
- 設定検証ツール（validate_config）で YAML 未インストール時のフォールバックメッセージを追加（PyYAML 未導入でも実行可能）。

### Notes / Implementation details
- 多くのモジュールは「DB 参照を最小限にする」「純粋関数で計算する」という設計方針に基づき実装。特に portfolio/* モジュールは副作用を持たない純粋関数群として設計されています。
- run_execution / run_monitoring はプロセス優先度を高く設定する初期処理を行う実装になっており、起動直後に set_process_priority("high") を呼び出します（権限不足時は警告で継続）。
- config の自動読み込みはテストや特殊用途で KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数により無効化可能。

---

今後の予定（想定）
- research/factor_research の実装完了（SQL 実装によるファクター算出の具体化）。
- 監視データのスキーマ文書化、monitoring_db の詳細実装の公開。
- ブローカークライアントの具体実装（モック／実ブローカーの差分テスト）。
- 単体テスト・CI の追加による安定性向上。

---