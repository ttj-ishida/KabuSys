# Changelog

すべての注記は Keep a Changelog の仕様に準拠しています。  
このファイルでは重要な変更点、追加機能、運用上の注意点を日本語でまとめています。

## [Unreleased]

## [0.1.0] - 2026-04-17
初回リリース — 基本機能群と運用用 CLI/ツールを実装。

### Added
- 基本パッケージ情報
  - パッケージのバージョンを `src/kabusys/__init__.py` にて `__version__ = "0.1.0"` として定義。

- 環境設定・ローディング
  - .env および .env.local の自動読み込み機能を実装（プロジェクトルート自動検出、KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
  - 複雑な .env パースロジックを実装（コメント、クォート、export プレフィックス、エスケープ対応）。
  - Settings クラスを実装し、環境変数から設定値を型安全に取得可能にした（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, PAPER_FILL_MODE など）。
  - 環境関連のバリデーション（KABUSYS_ENV, LOG_LEVEL 等の妥当性チェック）を組み込み。

- 設定ウィザード CLI
  - `kabusys.config_setup`:
    - 対話式ウィザードで .env を初期作成/更新する機能を提供。
    - J-Quants、kabu API、DB パス、ログレベル、Kill Switch の設定項目をサポート。
    - 秘匿項目はマスク表示。保存前の確認プロンプトを実装。

- 設定検証 CLI
  - `kabusys.validate_config`:
    - .env と config/*.yaml の存在・基本整合性を事前検証する CLI を提供。
    - 必須環境変数の未設定検出、プレースホルダ検知、DB パスの親ディレクトリ存在チェック、PyYAML が無い場合の挙動、KABUSYS_ENV=live に対する注意喚起等を実装。
    - `--strict` オプションで警告を失敗扱いにできる。

- 実行/監視用起動スクリプト
  - `kabusys.run_execution`:
    - ExecutionEngine 起動用スクリプトを実装。
    - 起動時にプロセス優先度を上げる処理を実行（utils.process_priority を使用）。
    - KABUSYS_ENV=paper_trading 時に Paper 用専用 SQLite（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）を使用して本番 DB と分離。
    - BrokerClientFactory を通じたブローカクライアントの生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、ExecutionEngine の起動と停止フラグ（data/stop_requested.flag）監視を実装。
    - エンジンはバックグラウンドスレッドで実行し、停止フラグ検知で安全に停止する。

  - `kabusys.run_monitoring`:
    - SystemMonitor のポーリングループ起動スクリプトを実装。
    - 環境にかかわらず監視は本番用 sqlite_path を使用する（監視 DB は本番パスを参照する設計）。
    - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（デフォルト 60 秒）で上書き可能（不正値はデフォルトにフォールバック）。
    - 起動時にプロセス優先度を上げ、停止フラグ（data/stop_requested.flag）を検出してループを終了する。

- プロセス優先度 / CPU affinity ユーティリティ
  - `kabusys.utils.process_priority`:
    - Windows / POSIX の差分を吸収してプロセス優先度を設定する `set_process_priority(level)` を実装（"high"|"normal"|"low"）。
    - 指定コア数にプロセスをピン留めする `set_cpu_affinity(cpu_count)` を実装。
    - 権限不足や未対応プラットフォーム時には警告を出して安全にスキップ。

- ポートフォリオ構築ライブラリ（純粋関数群）
  - `kabusys.portfolio.portfolio_builder`:
    - 候補選定 `select_candidates`（スコア降順 / signal_rank によるタイブレーク）、等重み `calc_equal_weights`、スコア重み `calc_score_weights` を実装。
    - スコア合計が 0 の場合は等重みへフォールバックし WARNING を出力。

  - `kabusys.portfolio.risk_adjustment`:
    - セクター集中制限を行う `apply_sector_cap`（既存保有を考慮して当日の売却予定銘柄を除外可能）。
    - 市場レジームに応じた投下資金乗数を返す `calc_regime_multiplier`（"bull"/"neutral"/"bear" 対応、未知レジームは 1.0 でフォールバック）。

  - `kabusys.portfolio.position_sizing`:
    - 発注株数を計算する `calc_position_sizes` を実装（allocation_method: "risk_based" / "equal" / "score"）。
    - 単元株（lot_size）丸め、ポジション・集計上限、コストバッファを考慮したスケーリングロジックを実装。
    - 価格欠損時のスキップ、available_cash を超過した場合のスケールダウンと端数の配分アルゴリズムを搭載。

- 研究用ファクター計算
  - `kabusys.research.factor_research`:
    - DuckDB を使ったファクター計算モジュールを実装（prices_daily / raw_financials を参照）。
    - モメンタム（1M/3M/6M、MA200乖離）、ボラティリティ（ATR20 等）、流動性指標を計算する関数を追加（例: calc_momentum, calc_volatility）。
    - 計算は純粋関数的に実装され、外部 API にはアクセスしない設計。

- 運用ツール
  - `kabusys.tools.paper_verification_report`:
    - Paper Trading の検証レポート生成スクリプトを実装。
    - 指標: 稼働率、注文成功率（Filled/Created）、送信率（Sent/Created）、リスク却下数、レイテンシ（avg/max/P95）。
    - しきい値による PASS/FAIL 判定を行う（デフォルト閾値: 稼働率99%、注文成功率90%、送信率95%、P95レイテンシ200ms）。
    - 引数で期間（--from/--to）や DB パス（--db）を指定可能。デフォルトの DB は PAPER_TRADING_SQLITE_PATH または data/paper_trading.db。

- DB 初期化
  - `init_monitoring_db` を呼び出して監視用テーブルの存在を保証（冪等的に実行）。

### Changed
- アーキテクチャ的設計
  - 監視（monitoring）コンポーネントは環境に依存せず本番監視 DB を参照する挙動をドキュメント化（run_monitoring）。一方、Execution は paper_trading では DB を完全に分離（paper 用 DB を使用）するようにした。
  - 起動スクリプトは起動直後に process priority を set することで他プロセスとの競合を軽減。

### Fixed
- （初版リリースのため該当なし）

### Deprecated
- （初版リリースのため該当なし）

### Removed
- （初版リリースのため該当なし）

### Security
- 環境変数の取り扱いに注意:
  - .env は絶対に Git にコミットしないことを README/生成スクリプト注釈で明示（config_setup でヘッダを出力）。
  - 秘匿値は対話ウィザードでマスク表示。設定検証で未設定のまま本番環境に進まないよう注意喚起（KABUSYS_ENV=live 時のチェックあり）。

---

運用上の主な注意点
- .env の自動読み込みはデフォルトで有効。テストや CI 等で自動読み込みを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- 監視起動スクリプトは MONITOR_POLL_INTERVAL（秒）でポーリング間隔を制御可能。0 や負の値を与えるとデフォルト（60 秒）にフォールバックします。
- 停止フラグ: data/stop_requested.flag（プロジェクトルート配下の data ディレクトリ）を用いて外部から安全にプロセスを停止できます。
- Paper Trading と本番 DB は設計上分離されています（paper_trading 実行時は PAPER_TRADING_SQLITE_PATH を利用）。監視は別途本番監視 DB を参照する点に注意してください。
- process priority / cpu affinity は権限やプラットフォーム制限により失敗する可能性があり、その際は警告ログを出力してスキップします。

問い合わせ / 貢献
- 初版リリースに関するバグ報告や改善提案は issue を作成してください。