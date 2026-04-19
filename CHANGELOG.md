# CHANGELOG

すべての注目すべき変更点を記録します。本ファイルは「Keep a Changelog」形式に準拠します。

注: この CHANGELOG はリポジトリ内のコードから推測して作成しています。実際のコミット履歴と差異がある可能性があります。

## [Unreleased]

## [0.1.0] - 2026-04-19

初回リリース。本リリースで追加された主要機能とユーティリティを記載します。

### 追加 (Added)
- 全体
  - パッケージ初期バージョンを公開（kabusys/__init__.py: __version__ = "0.1.0"）。
  - プロジェクトルートの自動検出機能（.git または pyproject.toml を起点）を実装し、.env 自動読み込みに利用（kabusys.config）。
  - .env ファイルの対話式作成／更新ウィザードを追加（kabusys.config_setup）。
  - 設定検証 CLI を追加（kabusys.validate_config）。必須環境変数や config/*.yaml の存在・パース検証、KABUSYS_ENV や LOG_LEVEL の妥当性チェックを行う。--strict オプションで警告を失敗扱いにできる。

- 実行・監視ランナー
  - 実行エンジン起動スクリプトを追加（kabusys.run_execution）。
    - 起動時にプロセス優先度を "high" に設定。
    - 環境に応じて本番用 / Paper Trading 用 SQLite を使い分ける（KABUSYS_ENV=paper_trading では PAPER_TRADING_SQLITE_PATH の値またはデフォルト data/paper_trading.db を使用）。
    - BrokerClientFactory によりブローカークライアントを生成（paper_trading の場合は MockBrokerClient を使用する想定）。
    - ExecutionEngine をスレッドで起動し、data/stop_requested.flag による停止制御、実行用 PID ファイルをサポート。
  - 監視ポーリングループ起動スクリプトを追加（kabusys.run_monitoring）。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバックし警告を出力。
    - 監視は環境にかかわらず本番 sqlite_path を使用して監視テーブルを初期化。
    - 停止フラグ（data/stop_requested.flag）検知でループを終了、KeyboardInterrupt もハンドルしてクリーンに終了。

- ユーティリティ
  - 統一的なロギング初期化ユーティリティを追加（kabusys.utils.logging_setup）。
    - stdout への StreamHandler と日次ローテートの TimedRotatingFileHandler（デフォルト logs/、30 日保持）をルートロガーへ設定。
    - ログディレクトリ作成失敗時はファイル出力をスキップし、コンソールのみで継続。
    - ログレベルの決定順序: 引数 > 環境変数 LOG_LEVEL > "INFO"。
  - クロスプラットフォームなプロセス優先度／CPU affinity ユーティリティを追加（kabusys.utils.process_priority）。
    - Windows・POSIX(Linux/Mac/FreeBSD) を吸収して nice / priority を設定。権限不足や未対応 OS は警告を出してスキップ。
    - CPU affinity を最初の N コアに固定する関数も提供。
  - 設定読み込み・パースの堅牢化（kabusys.config）:
    - .env のパースは export プレフィックス、シングル/ダブルクォート内のバックスラッシュエスケープ、行内コメント取り扱いなどに対応。
    - 自動読み込み順序: OS 環境変数 (保護) > .env (未設定キーのみセット) > .env.local (.env.local は上書き可)。自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - Settings クラスを提供し、アプリケーションで typed なプロパティ経由で設定値へアクセス可能（DB パス、PID/kill flag、閾値、環境識別など）。
  - Paper Trading 検証レポート生成ツールを追加（kabusys.tools.paper_verification_report）。
    - SQLite（デフォルト data/paper_trading.db）から各種指標（稼働率、注文成功率・送信率、リスク却下数、API レイテンシの avg/max/P95）を算出し、PASS/FAIL 判定を出力。
    - CLI オプションで期間・DB パスを指定可能。
  - リサーチ用ファクター計算モジュールの追加（kabusys.research.factor_research）。
    - Momentum 等の定量ファクター計算関数（DuckDB を利用）を設計・一部実装（モメンタム計算ロジックの導入、設定定数の導入）。（実装は継続中の箇所あり）
  - ポートフォリオ構築モジュールを追加（kabusys.portfolio）。
    - portfolio_builder: 候補選定 (select_candidates)、等重配分・スコア加重配分 (calc_equal_weights, calc_score_weights)。
    - risk_adjustment: セクターキャップ適用 (apply_sector_cap)、マーケットレジームに応じた乗数計算 (calc_regime_multiplier)。不明なレジームは 1.0 でフォールバックし警告を出力。
    - position_sizing: 発注株数計算 (calc_position_sizes)。allocation_method として "risk_based"/"equal"/"score" をサポート。ロット（lot_size）丸め、ポジション上限・aggregate cap、cost_buffer による保守的見積り、スケーリングと残余配分ロジックを実装。

### 変更 (Changed)
- なし（初回リリースのため該当なし）

### 修正 (Fixed)
- なし（初回リリースのため該当なし）

### 注意点 / 互換性 (Notes / Migration)
- 環境変数とファイルパス
  - デフォルトの DB/ログパス等:
    - DUCKDB_PATH: data/kabusys.duckdb
    - SQLITE_PATH: data/monitoring.db
    - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
    - LOG_DIR: logs/
  - MONITOR_POLL_INTERVAL を使用して監視ポーリング間隔を調整可能（秒）。不正値や 0 以下はデフォルト 60 秒にフォールバックして警告。
  - KABUSYS_ENV は "development" | "paper_trading" | "live" のみ許容。Settings の .env 読み込みと validate_config のチェックは一致しているので、環境値不正時は起動前に検出される。
- 実行と監視の DB 分離
  - 実行エンジン（run_execution）は paper_trading 環境時に paper_sqlite_path（デフォルト data/paper_trading.db）を用い、本番監視 DB と分離する設計。監視コンポーネントは環境にかかわらず sqlite_path（本番監視 DB）を使用するため取り扱いに注意。
- ログ出力
  - ログディレクトリ作成に失敗するとファイル出力は無効化され、コンソールのみでの出力になります（エラーで停止しない）。
- パーミッション
  - プロセス優先度・CPU affinity の設定は権限が必要です。設定できない環境では警告を出して続行します。

### セキュリティ (Security)
- なし

----

今後の予定（想定）
- research.factor_research の追加ファクター/最終実装・テスト完了
- ExecutionEngine / RiskManager / Reconciler 等の詳細実装と統合テスト
- 監視（monitoring_db 等）周りのドキュメント整備とアラート連携（LINE 等）の追加検証

---

（この CHANGELOG はコードから推測して記載しているため、実際のコミットやリリースノートとは差異があり得ます。）