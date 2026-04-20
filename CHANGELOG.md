# Keep a Changelog
すべての重要な変更をこのファイルに記録します。  
このプロジェクトは [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) の形式に概ね準拠しています。

注: 以下は提供されたコードベースの内容から推測して作成した変更履歴です。

## [Unreleased]
（現在のところ未リリースの変更はありません）

## [0.1.0] - 2026-04-20
初回公開リリース。システム構成、監視・実行エンジン、ポートフォリオ構築、ユーティリティ、検証/設定ウィザード、ペーパートレード検証ツールなどの基礎機能を実装。

### Added
- 全体
  - 初期バージョンを v0.1.0 として公開（パッケージバージョンは `kabusys.__version__ = "0.1.0"`）。
- 実行・監視スクリプト
  - `src/kabusys/run_execution.py`
    - ExecutionEngine を起動するエントリポイントを実装。
    - 環境に応じて paper_trading 用の専用 SQLite DB（デフォルト: `data/paper_trading.db`）を使用する切り替えを実装。
    - ブローカークライアント生成（`BrokerClientFactory.create`）／OrderRepository, OrderManager, RiskManager, Reconciler の組み立て。
    - スレッドでエンジンを起動し、`data/stop_requested.flag` による停止制御、実行 PID ファイル管理を実装。
    - 起動直後にプロセス優先度を "high" に設定。
  - `src/kabusys/run_monitoring.py`
    - SystemMonitor ポーリングループの起動スクリプトを実装。
    - ポーリング間隔を環境変数 `MONITOR_POLL_INTERVAL` で上書き可能（デフォルト 60 秒）。0 以下や不正値はデフォルトにフォールバックし警告を出力。
    - 監視用 DB は環境に依らず本番用 `sqlite_path` を使用する設計。
    - 停止フラグファイル検知によりループを終了する制御。
    - 起動時にプロセス優先度を "high" に設定。
- 設定管理
  - `src/kabusys/config.py`
    - プロジェクトルート自動検出（.git または pyproject.toml を起点）に基づく .env 自動読み込み機能を実装。
    - `.env` / `.env.local` の読み込み順（OS 環境変数 > .env.local > .env）と保護機構（OS 環境変数は上書き不可）を実装。
    - 複雑な .env パースを実装（export プレフィックス、単/二重クォート、エスケープ、インラインコメントに対応）。
    - `Settings` クラスを実装し、各種環境変数の取得および検証を提供（J-Quants、kabu API、DB パス、paper_trading の動作モード検証など）。
    - `PAPER_FILL_MODE` の検証（有効値: "instant" | "partial" | "never" | "reject"）を実装。
- 設定検証 / ウィザード
  - `src/kabusys/validate_config.py`
    - 起動前の設定検証 CLI を実装。必須環境変数のチェック、KABUSYS_ENV の妥当性、ログレベル、DB パスの親ディレクトリ存在確認、config/*.yaml の存在および PyYAML があればパース検証を行う。
    - `--strict` オプションで警告を失敗扱いにできる。
    - 本番環境用ガード（LINE 通知設定や KILL_FLAG_CLEAR_ON_START の危険性を警告）を実装。
  - `src/kabusys/config_setup.py`
    - .env の対話式ウィザードを実装。既存 .env の読み込み・再利用、入力プロンプト（選択肢・シークレット表示マスク）およびファイル書き込みを提供。
    - デフォルト値・説明付きの各設定項目を一覧化。
- ポートフォリオ構築
  - `src/kabusys/portfolio/portfolio_builder.py`
    - 候補選定（スコア降順、タイブレークに signal_rank）および等配分・スコア加重配分（スコア合計が 0 の場合は等配分にフォールバック）を実装。
  - `src/kabusys/portfolio/risk_adjustment.py`
    - セクター集中の上限適用（既存ポジションを考慮し、上限超過セクターの候補除外）を実装。
    - 市場レジームに応じた投下資金乗数 calc_regime_multiplier を実装（"bull"/"neutral"/"bear" => 1.0/0.7/0.3、未知レジームは警告して 1.0 にフォールバック）。
  - `src/kabusys/portfolio/position_sizing.py`
    - allocation_method（"risk_based"/"equal"/"score"）に基づく株数計算を実装。
    - 単元株（lot_size）に丸め、1銘柄上限・全体利用上限（max_utilization）の考慮、コストバッファ（cost_buffer）を踏まえた集約キャップ処理とスケールダウンロジックを実装。
- ツール
  - `src/kabusys/tools/paper_verification_report.py`
    - Paper Trading 用検証レポート生成ツールを実装（コマンドラインから利用可能）。
    - 稼働率、注文成功率、送信率、P95 レイテンシ等を集計し、閾値比較により PASS/FAIL 判定を出力（閾値はソース内定義）。
    - 日付範囲フィルタ、DB パス引数/環境変数対応、P95 計算実装を含む。
- ユーティリティ
  - `src/kabusys/utils/logging_setup.py`
    - アプリケーション向けの統一ロギングセットアップを実装。
    - stdout に出力する StreamHandler と、日次ローテーション（TimedRotatingFileHandler, 30日保持）のファイルハンドラをルートロガーに設定。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールにフォールバック。
    - ログレベル／ログディレクトリの解決順序を実装。
  - `src/kabusys/utils/process_priority.py`
    - クロスプラットフォーム（Windows / POSIX）でのプロセス優先度設定を実装（無権限時は警告してスキップ）。
    - CPU affinity を最初の N コアに固定するユーティリティを提供（無効な環境では警告）。
- リサーチ（開発中）
  - `src/kabusys/research/factor_research.py`（部分実装）
    - モメンタム等のファクター計算のための基礎を実装。DuckDB 接続を受け取って prices_daily 等のテーブルから計算する設計。ファイルは途中（切り出し途中の関数）だが主要定数とドキュメントが含まれる。

### Changed
- なし（初回リリース）

### Fixed
- なし（初回リリース）

### Deprecated
- なし（初回リリース）

### Removed
- なし（初回リリース）

### Security
- なし（特記事項なし）

---

補足:
- CLI 入口は各モジュールに __main__ を置くことで直接実行可能（例: `python -m kabusys.validate_config`, `python -m kabusys.config_setup`, `python -m kabusys.tools.paper_verification_report`）。
- .env の自動読み込みは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定することで無効化可能（テスト用途想定）。
- 提供されたコードは全体的に環境変数検証・ログ出力・DB パス管理・停止フラグを想定した安全な運用を考慮した実装になっています。