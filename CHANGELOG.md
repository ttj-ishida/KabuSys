# Changelog

すべての重要な変更はこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠しています。

## [0.1.0] - 2026-04-17

### Added
- 初回リリース。KabuSys のコアユーティリティ、CLI、ポートフォリオ構築ロジック、実行/監視ランナー、リサーチ機能、および各種ツールを追加。
- 環境/設定管理
  - .env 自動ロード機能を追加（OS環境変数 > .env.local > .env の優先順位）。自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` により無効化可能。
  - robust な .env パーサーを実装（`export KEY=...`、シングル/ダブルクォート、エスケープ、行内コメント処理をサポート）。
  - Settings クラスを実装し、アプリケーション設定をプロパティ経由で取得できるように（DB パス、API トークン、環境種別、閾値、PID/kill フラグパス等）。
  - `paper_fill_mode` 等の設定で値検証を行い、不正値は例外で通知。
- 環境設定ウィザード CLI
  - `kabusys.config_setup` により対話式で .env を作成/更新するウィザードを提供。秘密情報はマスク表示、保存テンプレートの生成を行う。
- 設定検証 CLI
  - `kabusys.validate_config` により起動前に必須環境変数や config/*.yaml の存在・基本パースチェックを実行。`--strict` オプションで警告を失敗扱いにできる。
  - 本番環境向けのガード（LINE 通知設定未設定、KILL_FLAG_CLEAR_ON_START 設定の危険性等）を実装。
- 実行・監視ランナー
  - `run_execution.py`：ExecutionEngine 起動スクリプトを追加。`KABUSYS_ENV=paper_trading` の場合は Paper Trading 用の専用 SQLite（`data/paper_trading.db` デフォルト）を使用し、Mock ブローカーを用いて本番 DB と分離可能。
  - `run_monitoring.py`：SystemMonitor ポーリングループ起動スクリプトを追加。ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL`（デフォルト 60 秒）で上書き可能。不正な値はデフォルトにフォールバック。
  - 両スクリプトとも起動時にプロセス優先度を "high" に設定する呼び出しを行う（`set_process_priority`）。
  - 停止管理はプロジェクト内の `data/stop_requested.flag`（停止フラグ）や PID ファイルを利用して行う実装。
- 実行コンポーネントの組立て
  - BrokerClientFactory、OrderRepository、OrderManager、RiskManager、Reconciler、ExecutionEngine の連携呼び出しを組み込んだ起動フローを実装（リスク設定のデフォルト値や初期ポートフォリオの取得等を含む）。
- ポートフォリオ構築ライブラリ（純粋関数群）
  - 銘柄選定: `select_candidates`（スコア降順、タイブレークルールあり）。
  - 重み計算: `calc_equal_weights`, `calc_score_weights`（スコア合計が 0 の場合は等配分にフォールバックして警告）。
  - セクターキャップ: `apply_sector_cap`（既存保有のセクター比率が上限を超える場合に新規候補を除外）。
  - レジーム乗数: `calc_regime_multiplier`（"bull"/"neutral"/"bear" に対する乗数を提供、未知レジームは 1.0 でフォールバックし警告を出す）。
  - 株数決定: `calc_position_sizes`（`risk_based`/`equal`/`score` の割当方式をサポート、lot size による丸め、per-stock 上限・aggregate cap スケーリング、コストバッファ考慮、単元株での端数処理アルゴリズムを実装）。
- リサーチ（ファクター計算）
  - `research.factor_research` にモメンタム、ボラティリティ、流動性等のファクター計算関数を追加（DuckDB 接続を受けて prices_daily / raw_financials を参照）。MA200 や ATR 等の計算を提供。
- ツール
  - `tools.paper_verification_report`：Paper Trading 用の検証レポート生成スクリプトを追加。稼働率、注文成功率、送信率、P95 レイテンシ等を算出し、閾値に基づく PASS/FAIL 判定を行う。デフォルト DB パスは `data/paper_trading.db`、コマンドラインで期間・DB を指定可能。
- ユーティリティ
  - `utils.process_priority`：クロスプラットフォーム（Windows / POSIX）でプロセス優先度を設定する `set_process_priority`、および CPU affinity を設定する `set_cpu_affinity` を追加。権限不足や未対応プラットフォームは警告でスキップ。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Notes / Implementation details
- 監視 DB（monitoring）については、run_monitoring が「環境にかかわらず本番 sqlite_path を使用する」実装になっている点に注意。Paper Trading 時は run_execution が専用の paper_trading DB を使用して本番 DB とデータ分離を行う。
- `MONITOR_POLL_INTERVAL` に 0 以下や整数以外を設定した場合は警告を出し、デフォルト（60 秒）にフォールバックする。
- .env ウィザードは秘密情報をマスク表示し、生成される .env を Git 等にコミットしないよう注意書きを出力する。
- ExecutionEngine はデーモンスレッドでセッションを実行し、停止フラグ検知時に安全に停止処理を行うよう実装されている。
- DuckDB は解析用ストアとして統合され、リサーチ機能や ExecutionEngine の一部で使用。

---

今後の予定（例）
- 更なるユニットテストの追加、YAML ベースの設定パース強化、銘柄別単元サイズ対応、エラー監視の詳細化、CLI UX の改善など。

（初回リリース: 0.1.0）