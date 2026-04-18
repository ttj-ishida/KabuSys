# CHANGELOG

すべての重要な変更をここに記録します。フォーマットは「Keep a Changelog」に準拠します。

## [0.1.0] - 2026-04-18

初回リリース。KabuSys の基本コンポーネント（設定管理、起動スクリプト、ロギング/プロセス制御、ポートフォリオ構築、ペーパートレード検証ツール、監視等）を実装・提供します。

### 追加 (Added)
- 全体
  - パッケージ初期バージョンを設定（__version__ = "0.1.0"）。
  - プロジェクト内の主要機能をモジュール化して公開（kabusys パッケージのエクスポート設定）。
- 起動スクリプト
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading のときは paper_trading 用の SQLite DB を使用し、本番 DB と分離。
    - BrokerClientFactory を利用してブローカークライアントを生成。
    - ストップフラグ（data/stop_requested.flag）検知、PID ファイル管理、デーモンスレッドでエンジン実行。
    - デフォルトでプロセス優先度を "high" に設定。
    - RiskManager のデフォルト構成値を定義（例: max_position_pct=0.20, max_utilization=0.80, rate_limit_per_sec=5, 等）。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒、0 以下や不正な値はデフォルトにフォールバック）。
    - 監視は環境にかかわらず production の sqlite_path（data/monitoring.db のデフォルト）を使用。
    - 停止フラグ検知で正常終了し、例外はログに出力して次ポーリングへ継続。
- 設定管理
  - config.py: Settings クラスを実装。
    - .env/.env.local の自動読み込み（プロジェクトルート検出に基づく）。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - 必須/任意の環境変数、各種パス（DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH など）や運用フラグをプロパティとして提供。
    - PAPER_FILL_MODE の検証、有効値チェック。
    - env/log_level の妥当性検証（許容値チェック）。
  - config_setup.py: .env 作成・更新の対話式ウィザードを追加。
    - CSV ではなく対話式プロンプトで設定を生成し .env に書き出すユーティリティ（秘密値はマスク表示）。
    - .env に関する注意（コミットしない等）をファイルヘッダに出力。
  - validate_config.py: 設定検証 CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスの親ディレクトリ確認、config/*.yaml の存在・パース検証（PyYAML がある場合）。
    - KABUSYS_ENV=live 向けの追加警告（LINE 設定、KILL_FLAG_CLEAR_ON_START の注意など）。
    - --strict オプションで警告も FAIL 扱いにできる。
- ユーティリティ
  - utils/logging_setup.py: 統一的なロギング設定ユーティリティを追加。
    - コンソール (stdout) 出力用 StreamHandler と 日次ローテート（TimedRotatingFileHandler、30日保持）のファイル出力をルートロガーへ設定。
    - ログレベル・ログディレクトリの解決順序（引数 > 環境変数 > デフォルト）を実装。ログディレクトリ作成失敗時はファイルハンドラをスキップしてコンソールのみで継続。
  - utils/process_priority.py: プロセス優先度・CPU affinity 設定ユーティリティを追加。
    - Windows / POSIX を吸収した set_process_priority(level) 実装（"high"/"normal"/"low"）。
    - set_cpu_affinity(cpu_count) により最初の N コアに固定可能（未指定時は設定しない）。
    - 権限不足や未対応 OS の場合は警告ログでスキップ。
- ポートフォリオ構築（純粋関数）
  - portfolio/portfolio_builder.py:
    - select_candidates: BUY シグナルのスコアで上位 N 件を選定（同点は signal_rank でタイブレーク）。
    - calc_equal_weights: 等金額配分を計算。
    - calc_score_weights: スコアに比例した重みを計算（全スコアが 0 の場合は等金額にフォールバック）。
  - portfolio/risk_adjustment.py:
    - apply_sector_cap: 既存保有のセクター比率が上限を超える場合に同セクターの新規候補を除外するロジック（"unknown" セクターは除外しない）。
    - calc_regime_multiplier: market レジームに応じた投下資金乗数を返す（bull/neutral/bear のマッピングと未知レジームのフォールバック）。
  - portfolio/position_sizing.py:
    - calc_position_sizes: 複数の allocation_method に対応して発注株数を計算（"risk_based"/"equal"/"score"）。
    - 単元株（lot_size）丸め、1銘柄上限・aggregate cap（available_cash を超えた場合のスケールダウン）を実装。
    - cost_buffer を考慮した保守的見積りと残差に基づく追加配分ロジックを実装。
    - TODO: 将来的な銘柄別 lot_size の拡張に関する注記を記載。
- 監視・検証ツール
  - monitoring/ 初期 DB 初期化ユーティリティ（init_monitoring_db）が呼び出されるように起動スクリプトを連携。
  - tools/paper_verification_report.py: ペーパートレード検証レポート生成スクリプトを追加。
    - 指標: 稼働率（uptime）、注文成功率（fill rate）、送信率（send rate）、API レイテンシ（avg/max/P95）。
    - デフォルト閾値: 稼働率 >= 99.0%、成立率 >= 90.0%、送信率 >= 95.0%、P95 レイテンシ <= 200 ms。
    - --from/--to/--db オプションで期間・DB を指定可能。PAPER_TRADING_SQLITE_PATH 環境変数をサポート。
- リサーチ
  - research/factor_research.py: ファクター計算モジュールを追加（モメンタム等の計算方針を実装）。DuckDB 接続で prices_daily / raw_financials を参照する設計。

### 変更 (Changed)
- （初回リリースにつき該当なし）

### 修正 (Fixed)
- （初回リリースにつき該当なし）

### 注記 (Notes / Known limitations)
- config.py / position_sizing.py 等にいくつかの TODO を含み、将来的な拡張（銘柄別 lot_size、価格フォールバック等）が想定されています。
- run_monitoring は監視用 DB として常に sqlite_path（本番向けパス）を使用します。開発用に別 DB を使いたい場合は設定またはコードの変更が必要です。
- config/*.yaml の内容検証は PyYAML のインストール有無に応じてスキップされます（validate_config.py）。
- process_priority の設定は OS/権限に依存し、失敗時は警告を出してスキップします。
- research/factor_research.py は DuckDB を想定した実装であり、データ準備（prices_daily/raw_financials）が前提です。ファイルは部分的に長い計算ロジックを含みます（リリース版では必要な関数を順次完成予定）。

### 開発者向けドキュメント参照
- 各モジュール内の docstring に使用例・挙動・パラメータ説明が含まれています。特に:
  - run_execution.py / run_monitoring.py: 起動手順と停止フラグの扱い。
  - config_setup.py: .env ウィザードの使い方。
  - validate_config.py: 起動前チェックの流れと --strict オプション。
  - utils/logging_setup.py: ログ設定の優先順位とハンドラ構成。
  - portfolio/*: PortfolioConstruction.md / StrategyModel.md に準じた実装注記（ソース内コメント参照）。
  - tools/paper_verification_report.py: 検証閾値とレポート出力形式。

今後のリリースでは、ExecutionEngine/Strategy 実行部分の追加実装・統合テスト・運用時の監視強化（アラート送信等）を予定しています。