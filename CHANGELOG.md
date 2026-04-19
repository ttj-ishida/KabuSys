# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠して記載しています。  
このログは提供されたコードベースの内容から推測して作成したものであり、実際のコミット履歴とは異なる場合があります。

## [Unreleased]

- なし

## [0.1.0] - 2026-04-19

Added
- 基本パッケージとバージョン
  - パッケージメタ情報を追加: `kabusys.__version__ = "0.1.0"`。

- 起動スクリプト / デーモン類
  - run_monitoring: SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` によるポーリング間隔上書きをサポート（デフォルト 60 秒）。
    - 停止制御に `data/stop_requested.flag` を利用。
    - Monitoring は環境にかかわらず本番用 `sqlite_path` を使用する設計。
    - プロセス優先度を起動直後に "high" に設定。
    - SQLite（監視 DB）と DuckDB の接続確立とクローズ処理を実装。
    - check_once() 実行時の例外をログに残して次ポーリングへ継続する堅牢化処理を追加。
  - run_execution: ExecutionEngine 起動スクリプトを追加。
    - `KABUSYS_ENV=paper_trading` の場合、MockBrokerClient を利用して paper_trading 用 DB（`data/paper_trading.db` がデフォルト）に完全分離して記録する。
    - プロセス優先度を "high" に設定。
    - 停止フラグ検知で安全にエンジン停止するロジックを追加（`data/stop_requested.flag`, `data/execution.pid` 管理）。
    - 各種依存コンポーネント（Broker, OrderRepository, OrderManager, RiskManager, Reconciler, ExecutionEngine）の組み立てと起動フローを実装。

- 設定管理・CLI
  - config: 環境変数/ .env 読み込みと Settings クラスを追加。
    - プロジェクトルート検出（.git または pyproject.toml）に基づく自動 .env ロード（`.env` → `.env.local`、OS 環境変数優先）。自動ロードは `KABUSYS_DISABLE_AUTO_ENV_LOAD` で無効化可能。
    - `.env` パーサはコメント、`export` プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント等に対応。
    - Settings クラスで J-Quants / kabuAPI / DB パス / Paper Trading 設定 / 監視閾値 / 環境判定などをプロパティとして提供。バリデーション（例: PAPER_FILL_MODE, KABUSYS_ENV, LOG_LEVEL）を含む。
    - `settings` インスタンスをエクスポート。
  - config_setup: 対話式 `.env` 作成・更新ウィザードを追加。
    - 必須/任意項目の定義、既存 `.env` 読み込み、シークレットマスク、選択肢・デフォルト提示、確認後ファイル出力を実装。
    - `.env` 書き込みテンプレートを用意（Git へコミットしない旨のコメント含む）。
  - validate_config: 起動前の設定検証 CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV 値チェック、LOG_LEVEL チェック、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在・パースチェック（PyYAML 未導入時は警告）および本番環境用ガード（LINE 通知/ Kill Switch 設定）を実施。
    - `--strict` オプションで警告を FAIL 扱いにできる。

- ユーティリティ
  - logging_setup: 統一ロギング設定ユーティリティを追加。
    - ルートロガーに stdout への StreamHandler と日次ローテーションの TimedRotatingFileHandler（デフォルト logs/, 30 日保持）を設定。
    - 既存ハンドラをクリアして二重設定を防止、ログレベルとログディレクトリの解決順を実装。ファイルハンドラ作成失敗時はコンソールのみで継続。
  - process_priority: クロスプラットフォームなプロセス優先度 / CPU affinity 設定ユーティリティを追加。
    - Windows / POSIX (Linux, Darwin, FreeBSD) に対応する `set_process_priority(level)`（"high"/"normal"/"low"）。権限不足や未対応環境は警告ログでスキップ。
    - `set_cpu_affinity(cpu_count)` による最初 N コアへのピン留め機能（エラー時は警告でスキップ）。

- ポートフォリオ構築（純粋関数群）
  - portfolio_builder:
    - select_candidates: BUY シグナルをスコア降順（同点は signal_rank 小）でソートして上位 N を選択。
    - calc_equal_weights: 等金額配分（各重み 1/N）。
    - calc_score_weights: スコア加重配分。全スコアが 0 の場合は等金額へフォールバックして警告ログ。
  - risk_adjustment:
    - apply_sector_cap: 既存保有のセクター別エクスポージャーを計算し、1セクターの上限（max_sector_pct）を超える場合に当該セクターの新規候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: market regime に応じた投下資金乗数を返す（"bull":1.0, "neutral":0.7, "bear":0.3）。未知レジームは警告の上 1.0 にフォールバック。
  - position_sizing:
    - calc_position_sizes: allocation_method に応じて発注株数を計算（"risk_based", "equal", "score" をサポート）。
      - risk_based: リスク許容率（risk_pct）と stop_loss_pct に基づく単銘柄ベースの算出と単元（lot_size）丸め。
      - equal/score: ウェイトに基づく配分、max_position_pct、max_utilization を考慮。
      - aggregate cap: 合計投資額が available_cash を超える場合はスケールダウンして lot_size 単位で再配分（端数制御による再割当ロジックを実装）。
      - cost_buffer による保守的コスト見積りを考慮。
    - 上記関数群はいずれも純粋関数（DB参照なし、メモリ計算）として設計。

- 監視/解析ツール
  - tools.paper_verification_report: Paper Trading の検証レポート生成スクリプトを追加。
    - Paper Trading 用 SQLite（環境変数 `PAPER_TRADING_SQLITE_PATH` またはデフォルト `data/paper_trading.db`）から
      - システム稼働率（uptime）
      - 注文成功率（fill rate）・送信率（send rate）
      - リスク却下数
      - API レイテンシ（avg, max, P95）
      を集計・表示。
    - P95 計算ロジックを実装（パーセンタイルインデックス算出）、期間フィルタ（--from/--to）をサポート。
    - 判定基準（デフォルト閾値）を定義し、PASS/FAIL 判定を表示（稼働率、成功率、送信率、P95 レイテンシ等）。

- 研究用モジュール（骨格）
  - research.factor_research: ファクター計算モジュールの骨格を追加（Momentum / Value / Volatility / Liquidity を想定）。
    - DuckDB 接続を受けて prices_daily / raw_financials テーブルを参照する方針を明記。
    - モメンタム計算関数 calc_momentum の開始（関数説明と定数定義）を含む（ソースは途中で切れている箇所あり）。

Other
- パッケージのエクスポート整理
  - portfolio パッケージの __init__.py で上位APIを集約して公開（select_candidates, calc_equal_weights, calc_score_weights, calc_position_sizes, apply_sector_cap, calc_regime_multiplier）。

Security
- なし

Deprecated
- なし

Removed
- なし

Notes / Implementation Remarks（コードから推測される挙動）
- .env 自動読み込みはプロジェクトルートが特定できない場合はスキップするため、配布後の利用時に挙動が安定するよう配慮されている。
- ログは stdout を主要出力先とし、ファイル出力は可能な場合のみ有効化する設計（コンテナ/ジョブスケジューラでの運用を想定）。
- process priority / cpu affinity は権限不足や非対応プラットフォームでスキップし、堅牢にフォールバックする実装になっている。
- 一部関数やモジュール（例: factor_research の一部、コメントにある TODO）については今後の拡張の余地を残す設計。

もし特定ファイルごとにより詳細な変更点や説明（例: 各 CLI の使用例、想定される .env のテンプレート、position_sizing の数式の導出など）を追記したい場合は、どのファイル／機能について詳細に記載するかを指定してください。