# CHANGELOG

すべての重要な変更を記録します。本ファイルは「Keep a Changelog」仕様に準拠しています。

注意: 本 CHANGELOG は提供されたコードベースからの実装内容を元に推測して作成しています。実際のコミット履歴とは異なる場合があります。

## [Unreleased]

- なし

## [0.1.0] - 2026-04-25

### 追加 (Added)
- 基本パッケージ初期実装を追加
  - パッケージメタ情報: kabusys.__version = "0.1.0" を定義。

- 実行スクリプト
  - run_execution.py: ExecutionEngine 起動用のエントリポイントを実装。
    - KABUSYS_ENV が `paper_trading` の場合は paper_trading 用 SQLite DB を使用して本番 DB と分離（デフォルト: data/paper_trading.db）。
    - BrokerClientFactory 経由でブローカークライアントを作成。
    - OrderRepository, OrderManager, RiskManager, Reconciler を組み立てて ExecutionEngine を起動。
    - 実行中は data/execution.pid を利用。停止制御は data/stop_requested.flag により行う。
    - スレッドで engine.run_session を実行し、停止フラグ検知で安全に停止を指示する。

  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを実装。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバック。
    - 監視実行時は環境にかかわらず本番の sqlite_path を使用して監視 DB を初期化。
    - duckdb にも接続して SystemMonitor に渡す。
    - 停止フラグ (data/stop_requested.flag) の存在を監視し、検知時にループを終了。
    - KeyboardInterrupt を考慮したクリーンな終了処理を実装。

- 設定管理
  - config.py: 環境変数・設定管理クラス Settings を実装。
    - .env 自動ロード機能:
      - プロジェクトルート (.git または pyproject.toml を探索) を基準に .env と .env.local を自動読み込み（環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
      - .env ローダは既存 OS 環境変数を保護しつつ .env.local で上書き可能。
    - .env パーサーは export KEY=val、クォート、エスケープ、行内コメントなどに対応。
    - Settings は JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD 等の必須項目、DUCKDB_PATH / SQLITE_PATH 等のパス、各種監視閾値、環境判定（is_live/is_paper/is_dev）などのプロパティを提供。
    - PAPER_FILL_MODE, PAPER_TRADING_SQLITE_PATH 等の paper_trading 向け設定を提供し、無効値は ValueError で通知。

  - config_setup.py: 対話式 .env 作成ウィザードを実装。
    - 複数の設定項目（KABUSYS_ENV、JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DB パス、LINE トークン等）を対話的に入力可能。
    - 既存 .env の読み込み&表示、シークレット項目はマスク表示、保存確認後に .env を生成。
    - デフォルト・選択肢・説明付きでユーザフレンドリーなウィザードを提供。

  - validate_config.py: 起動前設定検証 CLI を実装。
    - 必須環境変数の存在チェック、KABUSYS_ENV の妥当性、LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在確認、config/*.yaml の存在とパース検証（PyYAML がインストールされていない場合はスキップし警告）。
    - 本番環境向けの追加ガード（LINE 通知未設定や KILL_FLAG_CLEAR_ON_START の危険設定等）をチェック。
    - --strict オプションで警告も失敗扱いにできる。

- ロギング / プロセス管理ユーティリティ
  - utils/logging_setup.py:
    - ルートロガーに StreamHandler (stdout) と TimedRotatingFileHandler（日次、30日保持）を設定するユーティリティを提供。
    - ログレベルとログディレクトリの解決順（引数 > 環境変数 > デフォルト）を実装。
    - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソール出力のみで動作。
    - stdout を利用することで cron/Task Scheduler 等とのリダイレクト運用を想定。

  - utils/process_priority.py:
    - Windows / POSIX の差分を吸収してプロセス優先度を設定するユーティリティを提供（high/normal/low）。
    - psutil のプラットフォーム差分に対して安全にフォールバックし、権限不足・未実装機能時は警告を出してスキップ。
    - CPU affinity を最初の N コアに固定する set_cpu_affinity を実装（未指定時は何もしない）。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py:
    - select_candidates: BUY シグナルのスコア降順ソート（同点は signal_rank でタイブレーク）し上位 N 件を選定。
    - calc_equal_weights: 等金額配分（1/N）。
    - calc_score_weights: スコア重み配分（全スコアが 0 の場合は等分へフォールバックし warning）。

  - portfolio/risk_adjustment.py:
    - apply_sector_cap: セクターごとの既存保有比率が上限 (max_sector_pct) を超える場合に新規候補から除外するロジック。sell_codes（当日売却予定）を考慮してエクスポージャー計算を行う。
    - calc_regime_multiplier: market_regime に応じた投下資金乗数を提供（bull=1.0, neutral=0.7, bear=0.3）。未知レジームは 1.0 でフォールバック。

  - portfolio/position_sizing.py:
    - calc_position_sizes: allocation_method（"risk_based" / "equal" / "score"）に基づいて発注株数を計算。
      - risk_based: 許容リスク率（risk_pct）と stop_loss_pct に基づき株数算出。
      - equal/score: 各銘柄重みに対する割当を計算。
      - 単元株（lot_size）で丸め、1銘柄上限 (max_position_pct)、投下金額の aggregate cap（available_cash）に収まるよう縮小・再配分する。cost_buffer を使い手数料・スリッページを保守的に見積もる。
      - 端数の再配分は fractional remainder の大きい順に lot 単位で配る実装。

- Paper Trading 検証ツール
  - tools/paper_verification_report.py:
    - Paper Trading 用 SQLite（デフォルト data/paper_trading.db）から各種指標を集計しレポートを出力する CLI を実装。
    - 出力指標:
      - システム稼働率（system_status テーブル / process_ok）、総ポーリング数、エラー数
      - 注文成功率（Created / Filled / Sent の集計）
      - リスク却下数（risk_logs）
      - API レイテンシ（avg / max / P95、trade_logs.latency_ms を利用）
    - Pass/Fail 基準を定義（稼働率 99%、fill rate 90%、send rate 95%、P95 レイテンシ 200ms など）。
    - 日付フィルタ (--from / --to) と DB パス指定 (--db) 対応。

- 研究用ファクター計算（部分実装）
  - research/factor_research.py:
    - モメンタム、MA200乖離、ATR、流動性等の計算方針・定数を定義。DuckDB 接続を入力に取り prices_daily / raw_financials を参照してファクターを算出する設計。モジュールは計算用ユーティリティ群を実装中（一部関数は未完成）。

### 変更 (Changed)
- なし（初回リリースと想定）

### 修正 (Fixed)
- なし（初回リリースと想定）

### 注意事項 / 実装上のメモ
- .env ローディング:
  - 自動ロードはプロジェクトルートを基準に行うため、パッケージ配布後もカレントワーキングディレクトリに依存しない。
  - OS 環境変数を保護するため .env の上書きを制御（.env.local は上書き可能だが既存 OS 環境変数は保護される）。
- ロギング:
  - stdout に出力する設計（cron 等で stdout/stderr をまとめてリダイレクトする運用を想定）。
  - ログディレクトリ作成に失敗した場合はファイル出力を諦めてコンソール出力にフォールバックする。
- プロセス優先度:
  - プラットフォーム差分（Windows の PRIORITY_CLASS / POSIX の nice）を吸収し、権限不足等の例外は警告を出して継続する。
- Paper Trading の分離:
  - paper_trading 環境では発注処理がモック化され、DB も data/paper_trading.db に分離されるため本番 DB へ影響を与えない設計。

### 既知の課題 / TODO
- portfolio.position_sizing:
  - price が欠損（0.0）の場合、エクスポージャーや発注量が過少評価される問題がある旨コメントで記載。将来的に前日終値や取得原価でフォールバックすることを検討。
  - lot_size を銘柄ごとに扱う拡張（stocks マスタに lot_size を持たせる）を検討中。
- research/factor_research.py:
  - ファイル末尾の関数定義が途中で終わっている（未完）。ファクター計算の SQL/ロジックの実装を継続する必要あり。
- 監視/実行コンポーネント（SystemMonitor, ExecutionEngine 等）の内部実装（monitoring.monitoring_db, monitoring.system_monitor, execution.execution_engine 等）はここではインポートされているが、詳細実装の検証が必要。

---

（以降のリリースでは、各機能改善・バグ修正・互換性の変更をここに追記してください）