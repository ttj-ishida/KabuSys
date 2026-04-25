# CHANGELOG

すべての変更は Keep a Changelog の形式に従います。  
このファイルはコードベースの現在の状態（ソースコードから推測）に基づいて作成したリリースノートです。

注意: 日付・カテゴリはソースコードのコメントや実装から推測したものです。実際のリリース管理ポリシーに合わせて調整してください。

## [Unreleased]

- なし

## [0.1.0] - 2026-04-25

### 追加 (Added)
- 全体
  - 初期リリースを公開。日本株自動売買システム「KabuSys」のコアモジュールを含む。
  - パッケージバージョンは `kabusys.__version__ = "0.1.0"`。

- 起動スクリプト / 実行系
  - run_execution: ExecutionEngine を起動する CLI スクリプトを追加。
    - KABUSYS_ENV が `paper_trading` の場合は Paper Trading 用の専用 SQLite DB（既定: data/paper_trading.db）を使用して本番 DB と完全に分離。
    - Broker クライアントの生成を `BrokerClientFactory` に委譲。
    - ExecutionEngine を別スレッドで実行し、プロジェクトルートの stop フラグ（data/stop_requested.flag）で安全に停止可能。
    - 起動時にプロセス優先度を "high" に設定する仕組みを導入。
    - 実行中の PID を data/execution.pid に書き込む仕組み（Engine 側で利用）をサポート。

  - run_monitoring: SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - Monitoring は実行環境に関わらず本番用の sqlite_path を使用（監視は本番データストアを想定）。
    - 停止フラグ（data/stop_requested.flag）検知による安全終了を実装。
    - 起動時にプロセス優先度を "high" に設定。

- 設定・環境
  - config.py: 環境変数 / .env の読み込み・管理機能を追加。
    - プロジェクトルートを .git または pyproject.toml から探索して自動的に .env を読み込む（自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
    - .env のパースはシングル/ダブルクォートのエスケープ、export プレフィックス、行内コメント等に対応する堅牢な実装。
    - Settings クラスを提供し、各種設定（DB パス、API トークン、閾値、環境種別等）に型付きプロパティでアクセス可能に。
    - Paper Trading 関連設定（PAPER_FILL_MODE, PAPER_TRADING_SQLITE_PATH）をサポート。
    - 環境が不正な場合は ValueError を発生させる安全な検証ロジックを含む。

  - config_setup: 対話式ウィザードで .env の初期作成・更新を行う CLI を追加。
    - J-Quants / kabuステーション / DB パス / ログレベル / Kill Switch オプション等を対話的に設定し .env に書き出す。
    - 既存 .env の読み込みと既存値の再利用に対応。
    - 秘密値は画面表示時にマスク（****）して扱う。

  - validate_config: 設定検証 CLI を追加。
    - 必須環境変数の未設定チェック、KABUSYS_ENV や LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在確認、config/*.yaml の存在・パースチェック（PyYAML がある場合）を実行。
    - --strict オプションで警告を失敗扱いにできる。

- モニタリング / 運用ツール
  - monitoring モジュール用の DB 初期化（init_monitoring_db）へのフックを各起動スクリプトで使用。
  - tools/paper_verification_report: Paper Trading の検証レポート生成ツールを追加。
    - 指定期間（--from / --to）や DB (--db) を受け取ってレポートを出力。
    - 稼働率（uptime）、注文成功率（fill rate）、送信率、P95 レイテンシなどの指標を計算し PASS/FAIL を判定する基準 (閾値) を内蔵。
    - P95 の計算や各種集計を SQLite 上のテーブル（system_status, trade_logs, risk_logs 等）から取得。

- ポートフォリオ構築（純粋関数群）
  - portfolio モジュールを追加。DB 非依存の純粋関数を提供。
    - portfolio_builder
      - select_candidates: BUY シグナルのスコア降順選定（タイブレークに signal_rank を使用）。
      - calc_equal_weights: 等金額配分の重みを計算。
      - calc_score_weights: スコア比率で重みを計算。全スコアが 0 の場合は等配分にフォールバックして Warning を出力。
    - risk_adjustment
      - apply_sector_cap: セクター集中対策。既存保有を勘案して特定セクターの候補を除外するロジックを実装（"unknown" セクターは制約を適用しない）。
      - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投入資金の倍率を返す。
    - position_sizing
      - calc_position_sizes: allocation_method（"risk_based" / "equal" / "score"）に応じて発注株数を計算。
      - aggregate cap（利用可能現金を超える場合のスケールダウン）や単元株（lot_size）丸め、cost_buffer を考慮した保守的見積りを実装。
      - 各種パラメータ（risk_pct, stop_loss_pct, max_position_pct, max_utilization, lot_size, cost_buffer）を引数で柔軟に制御可能。

- ユーティリティ
  - utils/logging_setup: 統一的なロギング設定ユーティリティを追加。
    - stdout への StreamHandler（stdout を利用）と日次ローテーションの TimedRotatingFileHandler をルートロガーに設定。
    - LOG_DIR が作れない場合はファイル出力をスキップしてコンソールのみで継続する堅牢性を確保。
    - 既存ハンドラをクリアして二重設定を防止。
  - utils/process_priority: プロセス優先度（Windows の priority class / POSIX の nice）および CPU affinity 設定を吸収するユーティリティを追加。
    - プラットフォーム差分を隠蔽し、`set_process_priority("high"|"normal"|"low")` で優先度を設定可能（権限不足時は警告を出してスキップ）。
    - `set_cpu_affinity` で最初の N コアにプロセスをピン留め可能（権限や OS に依存する）。

- リサーチ
  - research/factor_research: ファクター計算モジュールを追加（Momentum, Value, Volatility, Liquidity を想定）。
    - DuckDB 接続を受け取り prices_daily / raw_financials テーブルを参照してファクターを計算する方針。
    - モメンタム計算関数（calc_momentum）の雛形を実装（実装の一部が未完の箇所あり）。

### 変更 (Changed)
- なし（初期リリースのため新規追加が主体）

### 修正 (Fixed)
- 環境変数パーサーを強化して以下に対応:
  - export プレフィックス、クォート内のバックスラッシュエスケープ、行内コメントの取り扱い、空行やコメント行のスキップ。
- logging_setup: ログディレクトリ作成に失敗した場合にファイルハンドラ作成をスキップし、標準出力のみで継続する耐障害性を強化。
- run_monitoring: MONITOR_POLL_INTERVAL に不正な値が設定された場合は警告を出してデフォルトにフォールバックする防御を追加。

### 警告 (Warnings)
- apply_sector_cap 内で価格が欠損（0.0）の場合、エクスポージャーが過少見積りされる可能性がある旨の TODO コメントを残している。将来的に前日終値や取得原価でのフォールバックが推奨される。
- calc_regime_multiplier: 未知のレジーム値は 1.0（Bull 相当）でフォールバックし警告を出す実装。

### 既知の問題 (Known issues)
- research/factor_research.calc_momentum がファイル末尾で途中で途切れている（実装未完）。実運用前に完成させる必要がある。
- position_sizing の lot_size 周りは現状グローバル固定（想定単元 100）。将来的に銘柄別の lot_map に対応する必要がある（TODO コメントあり）。
- 一部の外部依存（psutil, duckdb, PyYAML）が存在し、環境にない場合は機能が制限される（validate_config は PyYAML が無ければ YAML チェックをスキップする）。
- run_execution/run_monitoring はファイルベースの停止フラグ／PID ファイルを利用しているため、複数インスタンス運用やコンテナ環境での取り扱いに注意が必要。

### セキュリティ (Security)
- 特になし（このリリースでは機密情報の取り扱いに注意して .env を Git にコミットしない旨をドキュメント化）。

---

今後の提案（推奨タスク）
- factor_research の未完部分（calc_momentum 等）を完成させる。
- portfolio の lot_size を銘柄ごとに扱えるよう拡張し、stocks マスタとの連携を追加する。
- apply_sector_cap の price フォールバックロジックを実装して保守性を向上させる。
- 起動スクリプトのユニットテスト・統合テストを追加して停止フラグや PID 管理、DB 初期化の振る舞いを検証する。
- ドキュメントに運用手順（Kill Switch の取り扱い、paper_trading と live の DB 分離ポリシー等）を明示する。