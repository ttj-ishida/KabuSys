# CHANGELOG

すべての重要な変更点を記録します。本ファイルは「Keep a Changelog」形式に準拠しています。

## [0.1.0] - 2026-04-18

### 追加 (Added)
- コア CLI / 起動スクリプトを実装
  - run_execution.py: ExecutionEngine を起動するエントリポイントを追加。
    - KABUSYS_ENV=paper_trading 時は専用の Paper Trading SQLite（デフォルト: data/paper_trading.db）を使用して本番 DB と分離。
    - BrokerClientFactory 経由でブローカークライアントを生成。
    - OrderRepository, OrderManager, RiskManager, Reconciler を組み立てて ExecutionEngine を起動（スレッド実行、停止フラグ監視、execution.pid 管理）。
    - デフォルトでプロセス優先度を "high" に設定。
  - run_monitoring.py: システム監視ループの起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒、0 以下や不正な値はデフォルトにフォールバック）。
    - 監視は環境にかかわらず本番 sqlite_path を使用（監視テーブルの初期化を実行）。
    - 停止フラグ (data/stop_requested.flag) による終了検出。
    - プロセス優先度を "high" に設定。
- 設定管理とウィザード類
  - config.py: 環境変数/ .env 読み込み・Settings クラスを実装。
    - プロジェクトルートの検出 (.git または pyproject.toml 基準)。
    - .env / .env.local の自動読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
    - .env パースで export 形式・クォート・コメントを適切に扱う。
    - 各種設定プロパティ（DB パス、Paper Trading 周りの設定、監視閾値、環境判定など）を提供。値検証（例: PAPER_FILL_MODE, KABUSYS_ENV, LOG_LEVEL）。
  - config_setup.py: 対話式 .env 作成/更新ウィザードを追加。
    - 既存 .env 読み込み、シークレット値のマスク表示、保存確認、テンプレート書き出し。
  - validate_config.py: 起動前設定検証 CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在/パースチェック（PyYAML がない場合は警告）、KABUSYS_ENV=live 時の追加ガード。
    - --strict オプションで警告を失敗扱いに可能。
- ロギング / プロセス制御ユーティリティ
  - utils/logging_setup.py: 統一的なログ設定ユーティリティを追加。
    - stdout 出力（StreamHandler）と日次ローテートファイル出力（TimedRotatingFileHandler）をルートロガーに設定。
    - LOG_DIR の作成に失敗した場合はファイル出力をスキップして stdout のみで継続。
    - デフォルト保管日数 30 日。
  - utils/process_priority.py: クロスプラットフォームのプロセス優先度・CPU affinity 設定を追加（psutil 必須）。
    - set_process_priority(level): Windows / POSIX の差分を吸収。権限不足などはログ警告でスキップ。
    - set_cpu_affinity(cpu_count): 指定コア数に固定。未対応 OS や権限不足は警告でスキップ。
- ポートフォリオ構築関連（純粋関数）
  - portfolio/portfolio_builder.py: 候補選定と重み計算を追加。
    - select_candidates: スコア降順、同点は signal_rank でタイブレーク。
    - calc_equal_weights / calc_score_weights（スコア合計が 0 の場合は等分にフォールバック）。
  - portfolio/risk_adjustment.py:
    - apply_sector_cap: セクター集中の上限チェック（既存保有の時価を算出して上限超過セクターの候補除外）。
    - calc_regime_multiplier: market regime に応じた資金乗数（bull/neutral/bear）を返す。未知レジームは警告のうえ 1.0 をフォールバック。
  - portfolio/position_sizing.py:
    - calc_position_sizes: allocation_method ("risk_based", "equal", "score") をサポート。
    - 単元（lot_size）丸め、1 銘柄上限、aggregate cap によるスケールダウン（残差処理で lot 単位の追加配分）、cost_buffer を考慮。
- ツール
  - tools/paper_verification_report.py: Paper Trading の検証レポート生成ツールを追加。
    - システム稼働率、注文成功率（fill_rate）、送信率（send_rate）、P95 レイテンシ等を集計・評価し PASS/FAIL を出力。
    - CLI から期間指定（--from/--to）と DB パス指定（--db）可能。PAPER_TRADING_SQLITE_PATH 環境変数を優先。
    - P95 計算、閾値定義（稼働率 99%、fill_rate 90%、send_rate 95%、P95 latency 200ms）。
- research モジュールのスケルトンを追加
  - research/factor_research.py: ファクター計算（Momentum/Value/Volatility/Liquidity）設計およびモメンタム計算の骨子（定数と calc_momentum のドキュメント開始）を追加。
- パッケージメタ
  - パッケージバージョンを __version__ = "0.1.0" として設定。

### 変更 (Changed)
- 監視 (monitoring) 初期化は明示的に init_monitoring_db を呼び出して監視テーブルの存在を保証（冪等）。
- ログ出力は stdout を利用（stderr ではない） — シェルやスケジューラからのリダイレクトを想定。
- 設定ファイル読み込みの優先順位を明文化: OS 環境 > .env.local > .env。

### 修正 (Fixed)
- .env パーサーが export 形式やクォート内のエスケープを正しく扱うように実装（以前の単純パースでの破壊的な解析を回避）。
- calc_score_weights の全スコア 0.0 時に適切に等金額配分へフォールバックするよう明示。

### 注意事項 / 互換性に関する情報 (Notes / Breaking changes)
- 重要: run_monitoring（監視）は KABUSYS_ENV にかかわらず settings.sqlite_path（デフォルト: data/monitoring.db）を使用します。開発・ペーパートレード環境で監視データを完全に分離したい場合は sqlite_path を明示的に別パスに設定してください。
- run_execution は KABUSYS_ENV=paper_trading の場合に paper_sqlite_path（PAPER_TRADING_SQLITE_PATH）を使用して本番 DB と分離します。paper_trading を使う際は PAPER_TRADING_SQLITE_PATH を適切に設定してください。
- set_process_priority は OS 権限に依存します。権限不足時は警告が出力され設定をスキップします。
- validate_config の config/*.yaml のパース検証は PyYAML に依存します。PyYAML 未インストール時は YAML 検証をスキップして警告を出します。
- logging_setup はログディレクトリ作成に失敗した場合、ファイル出力を無効化して stdout のみで稼働します。ログが残らない可能性があるため運用時は LOG_DIR を確認してください。
- 本リリースでは research/factor_research.py の実装は未完（calc_momentum の実装途中）。今後のリリースで機能拡充予定。

### セキュリティ (Security)
- .env ファイルは絶対にリポジトリにコミットしない旨の注意を config_setup.py に明記。
- シークレット値は対話式ウィザードでマスク表示され、.env ファイル作成時も平文で保存されるため、運用時はファイル権限に注意。

---

今後のリリースでは以下を予定しています（未実装・改善点の例）:
- research/factor_research の完全実装（ファクター計算ロジックの完成）。
- ExecutionEngine / BrokerClient の詳細なエラーハンドリングとリトライ戦略。
- モニタリング・アラート（LINE 通知等）機能の追加。
- 単体テスト・CI の整備、型注釈の厳格化。