# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。  
遡及的にコードベースから機能追加・動作仕様を推測して記載しています。

※ 本ドキュメントはリポジトリに含まれるソースコード（src/kabusys 以下）から推定した変更履歴です。実際のコミット履歴とは異なる場合があります。

## [Unreleased]

### 追加
- 監視用・実行用の起動スクリプトを追加
  - run_monitoring.py
    - MONITOR_POLL_INTERVAL 環境変数によるポーリング間隔の上書き対応（デフォルト60秒）。
    - 停止フラグファイル (data/stop_requested.flag) による安全停止。
    - 監視ループ内の例外をログ出力して次のポーリングへフォールバック。
    - Monitoring は環境にかかわらず本番の sqlite_path を使用する設計。
  - run_execution.py
    - KABUSYS_ENV=paper_trading 時に専用の SQLite（data/paper_trading.db）を使用する、paper/live の分離。
    - BrokerClientFactory によるブローカークライアント抽象化。
    - ExecutionEngine の起動・停止制御（PID ファイル、停止フラグ監視、スレッド実行）。
    - RiskManager、OrderManager、Reconciler 等の組み立てとデフォルトリスク設定の導入。

- 設定管理・CLI を追加
  - config.py
    - プロジェクトルート検出（.git または pyproject.toml を基準）に基づく .env 自動読み込み。
    - .env ファイルの堅牢なパース機能（export 形式、クォート内のエスケープ、コメント処理など）。
    - Settings クラスでアプリケーション設定をプロパティとして提供。環境値のバリデーションと既定値の取り扱いを行う。
    - PAPER_FILL_MODE、PAPER_TRADING_SQLITE_PATH、KILL_FLAG_CLEAR_ON_START 等の設定項目を追加。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能（テスト向け）。
  - config_setup.py
    - .env の対話式ウィザード（生成・更新）を追加。シークレットのマスク表示、デフォルト/選択肢サポート、.env の書き出しテンプレートを提供。
  - validate_config.py
    - .env と config/*.yaml の事前検証 CLI を追加。必須環境変数のチェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在確認、PyYAML 未インストール時のスキップなど。
    - --strict オプションで警告を失敗扱いにできる。

- ロギング・プロセス制御ユーティリティを追加
  - utils/logging_setup.py
    - stdout 出力（StreamHandler）と日次ローテーションのファイル出力（TimedRotatingFileHandler）をルートロガーへ設定する共通ユーティリティ。
    - LOG_LEVEL / LOG_DIR / app_name によるファイル名決定、ログディレクトリ作成失敗時はファイル出力をスキップし stdout のみで継続。
  - utils/process_priority.py
    - Windows / POSIX (Linux, macOS 等) を吸収するプロセス優先度設定（set_process_priority）。
    - CPU affinity を最初の N コアに固定する set_cpu_affinity。
    - psutil の権限不足や未対応 OS での安全なフォールバックとログ警告。

- ポートフォリオ構築（純粋関数群）を追加
  - portfolio/portfolio_builder.py
    - シグナル選定（score 降順 + signal_rank によるタイブレーク）、等金額配分、スコア重み配分を実装。
  - portfolio/risk_adjustment.py
    - セクター集中制限の適用（apply_sector_cap）。
    - 市場レジームに応じた投下資金乗数 calc_regime_multiplier（bull/neutral/bear をマップ）。
  - portfolio/position_sizing.py
    - position sizing ロジック（risk_based / equal / score）、単元株（lot_size）丸め、aggregate cap によるスケーリング、コストバッファ考慮などを実装。

- 解析・検証用ツールを追加
  - tools/paper_verification_report.py
    - Paper Trading 用の検証レポート生成スクリプト。
    - 稼働率、注文成功率、送信率、P95 レイテンシ等を算出・閾値比較して PASS/FAIL を判定。
    - デフォルト閾値（稼働率99%、成功率90% 等）を定義。

- 研究モジュール（ファクター計算）を追加（進行中）
  - research/factor_research.py
    - モメンタムなどのファクターを計算するための基盤を実装（DuckDB 接続想定）。
    - 設計上は prices_daily / raw_financials 参照、Zスコア等へ連携する想定。
    - 一部実装（calc_momentum）が未完（コード末尾が途切れているため作業中の状態）であることを注記。

### 変更
- DB の扱い
  - 監視（monitoring）は KABUSYS_ENV にかかわらず本番の sqlite_path を参照する設計に明示。これにより監視データの一元化を想定。
  - 実行（execution）は paper_trading 環境時に専用の SQLite（PAPER_TRADING_SQLITE_PATH）を使用し、本番 DB と完全分離する設計を導入。

- 起動時のプロセス優先度
  - run_monitoring/run_execution 起動時に set_process_priority("high") を呼び出すことで重要プロセスの優先度を上げるよう変更。

- env ファイル読み込み順と保護
  - 自動ロードの優先順位を OS 環境変数 > .env.local > .env とし、.env.local は既存の OS 環境変数を上書きしないよう保護セットを導入。

### 修正（挙動改善）
- .env パーサーの堅牢化
  - export プレフィックス対応、シングル/ダブルクォート内でのバックスラッシュエスケープ処理、コメント扱いの厳密化などを導入。
- ログ設定の堅牢化
  - 既存ハンドラを安全にクローズしてから再登録する処理を実装（重複ハンドラ防止）。
  - ログディレクトリ作成失敗時はファイルハンドラをスキップしつつ警告出力するように変更。
- プロセス優先度・CPU affinity 設定で、権限不足や未対応プラットフォームに対して警告してスキップする堅牢な挙動に改善。

### ドキュメント／テンプレート
- .env 書き出しテンプレートに注意喚起コメントを追加（".env は絶対に Git にコミットしないこと" など）。
- config_setup ウィザードにより初期設定フローを明確化（対話式入力、既存値の再利用、保存確認）。

### 既知の問題 / 注意点
- research/factor_research.calc_momentum の実装が途中で途切れている（ファイル末尾に不完全な行が存在）。続きの実装が必要。
- apply_sector_cap 内で price_map が欠損（0.0）を返す場合にエクスポージャーが過少見積りされる可能性がある旨の TODO コメントあり。将来的に価格フォールバックの導入を検討。
- process_priority の一部処理は権限に依存する（psutil.AccessDenied が発生する可能性がある）。

## [0.1.0] - 2026-04-18

初期リリース（コードベースのスナップショット）。以下の主要機能を含む。

### 追加
- 基本パッケージ情報
  - パッケージバージョン __version__ = "0.1.0"
- 実行系
  - run_execution.py: ExecutionEngine 起動スクリプト、paper_trading 分離、PID/stop フラグ対応。
- 監視系
  - run_monitoring.py: SystemMonitor ポーリングループ、MONITOR_POLL_INTERVAL 環境変数対応、停止フラグ対応。
- 設定・運用
  - config.py: .env 自動ロード、Settings クラスによる設定管理とバリデーション。
  - config_setup.py: .env 対話式生成ウィザード。
  - validate_config.py: 起動前チェック CLI（--strict サポート、YAML パースチェック）。
- ユーティリティ
  - utils/logging_setup.py: 共通ログ設定（stdout + 日次ローテーションファイル）。
  - utils/process_priority.py: クロスプラットフォーム優先度設定、CPU affinity。
- ポートフォリオ構築
  - portfolio/portfolio_builder.py, risk_adjustment.py, position_sizing.py: 選定・重み付け・ポジションサイズ・セクター制限等のアルゴリズム実装。
- ツール
  - tools/paper_verification_report.py: Paper Trading の検証レポート生成。
- 研究（進行中）
  - research/factor_research.py: ファクター計算基盤（モメンタムなど、未完部分あり）。

### 既知の注意点
- research/factor_research の一部未実装箇所あり。
- 一部機能は外部ライブラリ（psutil, duckdb, PyYAML）が存在することを前提としている。存在しない場合は警告や機能限定が行われるが、実行環境での依存関係確認が必要。

---

追記・補足（運用メモ）
- 環境変数の重要なキー:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD （必須）
  - KABUSYS_ENV = development | paper_trading | live
  - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB）
  - MONITOR_POLL_INTERVAL（監視ポーリング秒数）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD（自動 .env ロードを無効化する場合は 1）
  - KILL_FLAG_CLEAR_ON_START（本番で 1 にすると危険。デフォルト 0 推奨）
- 監視・実行プロセスは起動直後にプロセス優先度を "high" に上げようとします。権限がない場合は警告が出ますが動作は継続します。

（以上）