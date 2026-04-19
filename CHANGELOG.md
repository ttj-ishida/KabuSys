# Changelog

すべての注目すべき変更点をここに記載します。形式は「Keep a Changelog」に準拠しています。

注意: 下記は提示されたコードベースの内容から推測・要約した変更履歴（初回リリース向けの記述）です。実際のコミット履歴がある場合は差分に応じて調整してください。

## [Unreleased]

（なし）

## [0.1.0] - 2026-04-19

初回リリース。日本株自動売買システム「KabuSys」の基本コンポーネント群を導入します。

### Added
- コア設定・環境読み込み
  - Settings クラスを提供する `kabusys.config`（環境変数のラップ、デフォルト値・バリデーションを含む）。
  - プロジェクトルート自動検出と `.env` 自動読み込み機能（`.env` / `.env.local`、OS 環境変数保護付き）。
  - `.env` の厳密なパース機能（`export KEY=val` 対応、クォート/エスケープ/インラインコメント処理）。
- 設定ユーティリティ CLI
  - `kabusys.config_setup`：対話式ウィザードで `.env` を作成・更新するツール（シークレットマスク表示、保存確認含む）。
  - `kabusys.validate_config`：起動前の設定検証 CLI（必須環境変数チェック、DB パス確認、config/*.yaml の存在・パースチェック、--strict オプション対応）。
- 実行・監視ランナー
  - `run_execution.py`：ExecutionEngine 起動スクリプト。KABUSYS_ENV に応じて paper_trading 用 DB を分離して使用（paper_trading 時は MockBrokerClient を想定）。
  - `run_monitoring.py`：SystemMonitor ポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。停止フラグ（data/stop_requested.flag）検知で安全に終了。
- ロギング・プロセス制御ユーティリティ
  - `kabusys.utils.logging_setup.setup_logging`：標準出力（stdout）と日次ローテーションファイルハンドラをルートロガーに設定する共通ユーティリティ。ログディレクトリ自動作成、失敗時はファイル出力をスキップしてコンソールのみで継続。
  - `kabusys.utils.process_priority`：プラットフォーム差異を吸収したプロセス優先度設定（Windows / POSIX 対応）および CPU アフィニティ設定。アクセス権限がない場合は警告を出してフォールバック。
- ポートフォリオ構築ライブラリ（純粋関数群、DB 非依存）
  - `kabusys.portfolio.portfolio_builder`：シグナル選定（score 降順・タイブレーク）、等金額／スコア重み計算。
  - `kabusys.portfolio.risk_adjustment`：セクター集中制限（apply_sector_cap）、市場レジームに基づく投下資金乗数（calc_regime_multiplier）。
  - `kabusys.portfolio.position_sizing`：株数決定ロジック（risk_based / equal / score）、単元株丸め、aggregate cap によるスケーリングと余剰配分ロジック。
  - `kabusys.portfolio.__init__` で上記を公開。
- 分析・検証ツール
  - `kabusys.tools.paper_verification_report`：Paper Trading の SQLite DB（PAPER_TRADING_SQLITE_PATH 指定可）から稼働率、注文成功率、送信率、レイテンシ（avg/max/P95）等を集計し PASS/FAIL レポートを生成する CLI。基準値（稼働率 99% 等）を組み込み。
- データ / リサーチ（一部実装）
  - `kabusys.research.factor_research`：DuckDB 接続を受けてモメンタム等のファクターを計算するモジュール（設計方針と定数を定義、モメンタム算出関数実装開始）。
- パッケージ初期化
  - `kabusys.__init__` にバージョン __version__ = "0.1.0" を追加。

### Changed / Behavior
- DB 分離ポリシー
  - 監視（monitoring）は環境にかかわらず production 想定の sqlite_path を使用する設計（run_monitoring）。
  - 実行エンジン（run_execution）は KABUSYS_ENV=paper_trading の場合に paper_sqlite_path（デフォルト data/paper_trading.db）を使用し、本番 DB と完全分離する。
- ログ出力
  - コンソール出力は stdout を使用（cron 等で stdout/stderr を一本化する運用を想定）。
  - 日次ローテーション・30 日保持のファイルハンドラをデフォルトで設定。ログディレクトリ作成に失敗した場合はファイル出力をスキップしても起動を継続する。
- 環境変数読み込み順序
  - OS 環境変数 > .env.local > .env の優先順位で自動ロード。テスト用に自動ロードを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
- 停止・PID 管理
  - 実行・監視プロセスはプロジェクト内 data ディレクトリの stop_requested.flag を監視して安全に停止する仕組みを持つ。ExecutionEngine は PID ファイルの取り扱いを行う（設定で path 指定）。

### Fixed / Robustness
- .env パーサ改善
  - export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ処理、インラインコメント取り扱い等を実装してより堅牢に。
  - _load_env_file の override/protected ロジックで OS 環境変数を保護（既に設定されているキーを上書きしない / protected を指定して強制上書き防止）。
- 監視ポーリングの不正間隔対策
  - MONITOR_POLL_INTERVAL が不正（整数変換不能、0 以下など）な場合にデフォルト（60 秒）へフォールバックし、警告ログを出すようにした。
- プロセス優先度・CPU アフィニティの例外処理
  - 設定に失敗した場合（アクセス拒否等）は警告出力してスキップするフォールバックを導入。
- DB 初期化の冪等性
  - run_execution/run_monitoring が起動時に監視用テーブルを保証するため init_monitoring_db を呼ぶ（存在確認/作成を想定、冪等処理）。

### Security / Privacy
- config_setup の対話表示ではシークレット項目をマスク（"****"）表示して漏洩リスクを低減。
- README 的注意書きとして .env を絶対に Git にコミットしない旨を出力するテンプレートを実装。

### Known issues / TODO
- `kabusys.research.factor_research` は途中で切れている（実装継続が必要）。完全なファクター算出パイプラインの検証が未完。
- 一部の価格欠損時のフォールバック（apply_sector_cap の price が欠けている場合の扱い）について TODO コメントあり。将来的に前日終値等のフォールバック実装を検討。
- 単元株（lot_size）や銘柄ごとの単元情報は固定（現状は共通 lot_size=100）。将来的に銘柄マスタを取り込む拡張を想定。

---

References:
- 本 CHANGELOG はソースコードの内容（モジュール構成・ドキュメント文字列・コメント）から推測して作成しています。実際のコミット履歴・リリースノートがある場合はそちらに従ってください。