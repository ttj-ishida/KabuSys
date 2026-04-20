# Changelog

すべての注目すべき変更をこのファイルに記録します。  
このプロジェクトは [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) の慣例に従います。  
配布バージョンは semver を想定します。

## [Unreleased]
（今後の変更をここに記載）

---

## [0.1.0] - 2026-04-20

初回公開リリース。自動売買システム KabuSys の基盤的なモジュール群と CLI ツールを追加しました。

### Added
- パッケージ基盤・バージョン情報
  - src/kabusys/__init__.py にて __version__ = "0.1.0" を定義。

- 起動スクリプト
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading 時に専用の paper_trading DB を使用する処理を含む。
    - BrokerClientFactory を用いたブローカークライアントの生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、ExecutionEngine の実行ループ（停止フラグ・PID ファイル管理）。
    - Execution 用のプロセス優先度設定（high）。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視 DB は環境に依らず本番 sqlite_path を参照して初期化。
    - 停止フラグ検出でループ終了、例外時はログ出力して次ポーリングへ継続。

- 設定管理・ウィザード・検証
  - config.py: Settings クラスを追加。環境変数読み込み、自動 .env ロード（.env / .env.local、OS 環境変数保護）や各種プロパティを提供。
    - J-Quants / kabu API / DB パス / Paper Trading 用設定 / 監視閾値 / KABUSYS_ENV / LOG_LEVEL 等。
    - PAPER_FILL_MODE 等の値検証を実装。
  - config_setup.py: 対話式 .env 作成・更新ウィザードを追加（items 定義、既存 .env 読み込み、保存）。
  - validate_config.py: 起動前設定検証 CLI を追加（必須環境変数、KABUSYS_ENV、ログレベル、DB パス、config/*.yaml 存在チェック、live 向けガード等）。--strict オプションで警告も失敗扱いにできる。

- ロギング / プロセス制御ユーティリティ
  - utils/logging_setup.py: 統一的なログ設定ユーティリティを追加。
    - stdout (StreamHandler) と 日次ローテートファイルハンドラ (TimedRotatingFileHandler) をルートロガーに設定。
    - LOG_DIR / LOG_LEVEL の解決順をサポート。ファイルハンドラ作成失敗時はコンソールのみで継続。
  - utils/process_priority.py: プロセス優先度設定と CPU affinity ユーティリティを追加。
    - Windows/Linux/macOS 対応（psutil を利用）。優先度レベル: high/normal/low。
    - CPU affinity 固定機能 (set_cpu_affinity)。

- ポートフォリオ構築関連（純粋関数）
  - portfolio/portfolio_builder.py
    - select_candidates: BUY シグナルの上位選定（スコア降順、同点は signal_rank）。
    - calc_equal_weights, calc_score_weights: 等配分・スコア加重配分（全スコア 0 の場合はフォールバック）。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中上限チェック（既存保有比率に基づく候補除外）。"unknown" セクターは除外対象外。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数 (bull/neutral/bear、未知は 1.0 でフォールバック)。
  - portfolio/position_sizing.py
    - calc_position_sizes: 各銘柄の発注株数算出（risk_based / equal / score）。単元株（lot_size）丸め、per-stock と aggregate の上限、cost_buffer（手数料・スリッページ想定）を考慮したスケーリング。

- リサーチ（骨組み）
  - research/factor_research.py: ファクター計算モジュールを追加（Momentum / Value / Volatility / Liquidity を想定）。
    - DuckDB 接続を受け取り prices_daily / raw_financials を参照して計算する設計。
    - モメンタム計算の定義・定数を追加（1M/3M/6M、MA200、ATR 等）。
    - （注意）ファイルの実装が途中の箇所あり（以降の実装は継続予定）。

- ツール
  - tools/paper_verification_report.py: Paper Trading 検証レポート生成スクリプトを追加。
    - PAPER_TRADING_SQLITE_PATH（または --db オプション）で DB 指定、期間フィルタ指定可。
    - system_status / trade_logs / risk_logs から稼働率、注文成功率、送信率、レイテンシ（avg/max/P95）などを集計し PASS/FAIL 判定を出力。
    - 判定閾値（稼働率 99% 等）を定義。

- DB 統合
  - duckdb を利用する接続箇所（Execution/Monitoring/Research 用）。
  - monitoring_db 初期化ヘルパー（呼び出し箇所あり、冪等に監視テーブル作成を保証）。

### Changed
- （新規リリースのため該当なし）

### Fixed
- （新規リリースのため該当なし）

### Notes / Known limitations
- position_sizing.calc_position_sizes:
  - 将来的に銘柄ごとの lot_size を受け取る拡張予定（現在は全銘柄共通の lot_size を使用）。TODO コメントあり。
- risk_adjustment.apply_sector_cap:
  - price_map に価格が欠損（0.0）の場合の挙動注記あり（過小見積りの可能性）。フォールバック価格を使う改善が検討中。
- research/factor_research.py:
  - ファイル末尾で実装が途中（トランケーション）になっている箇所が存在。完全なファクター計算の実装は継続作業が必要。
- run_monitoring/run_execution:
  - 停止はファイルフラグ（data/stop_requested.flag）と PID / kill flag に依存する設計。運用時のオペレーション手順をドキュメント化することを推奨。
- サードパーティ依存:
  - duckdb, psutil, PyYAML（optional） などのパッケージに依存。validate_config は PyYAML 未インストール時に YAML 検証をスキップする。

---

開発／運用側へのヒント:
- .env 自動ロードはデフォルトで有効。テストなどで自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- ログディレクトリ作成に失敗した場合はコンソール出力のみで継続します。運用環境では LOG_DIR を適切に設定し、書き込み権限を確認してください。

（以上）