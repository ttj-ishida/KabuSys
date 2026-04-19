# Changelog

すべての notable な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。  

なお、本履歴は提示されたソースコードの内容から推測して作成しています。

※ バージョン番号はパッケージの __version__（0.1.0）に合わせています。

## [Unreleased]
（現時点で未リリースの変更はありません）

## [0.1.0] - 2026-04-19
初回公開リリース。日本株自動売買システム「KabuSys」の基礎機能を実装。

### Added
- 基本設定・環境変数管理
  - `kabusys.config.Settings`：環境変数をラップして提供。J-Quants/Kabu API や DB パス、監視閾値、実行環境（development/paper_trading/live）などを取得するプロパティを実装。
  - 自動 `.env` ロード機能：プロジェクトルート（.git / pyproject.toml）検出時に `.env` と `.env.local` を読み込み。`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
  - `.env` パーサ：クォート、エスケープ、コメント処理、`export KEY=val` 形式へ対応（`_parse_env_line`）。

- 設定ユーティリティ・CLI
  - `kabusys.config_setup`：対話式ウィザードで `.env` を作成/更新する CLI。
  - `kabusys.validate_config`：起動前に必須環境変数や config/*.yaml、パスの妥当性や本番ガードをチェックする検証 CLI（`--strict` オプションあり）。

- 実行/監視起動スクリプト
  - `run_execution.py`：ExecutionEngine 起動スクリプト。プロセス優先度設定、DB 接続（paper_trading 環境では paper 用 DB に分離）、Broker クライアント生成、ExecutionEngine の起動・停止監視（stop flag / PID 管理）を実装。
  - `run_monitoring.py`：SystemMonitor のポーリングループ起動。`MONITOR_POLL_INTERVAL` 環境変数でポーリング間隔上書き、停止フラグで終了、監視用 DB は常に本番 sqlite_path を使用。

- Paper Trading / ブローカー分離
  - ペーパートレードモード（KABUSYS_ENV=paper_trading）時は専用 SQLite（デフォルト `data/paper_trading.db`）を使用する方針と、それに対応する設定（`paper_sqlite_path`, `paper_fill_mode`）を実装。

- 監視・レポートツール
  - `kabusys.tools.paper_verification_report`：Paper Trading データベースから稼働率、注文成功率、送信率、レイテンシ等を集計して検証レポートを出力する CLI。日時フィルタ（--from/--to）と DB 指定（--db）に対応。P95 計算、閾値（稼働率99%、成立率90% 等）に基づく PASS/FAIL 判定を行う。

- ポートフォリオ構築モジュール（純粋関数群）
  - `kabusys.portfolio.portfolio_builder`
    - select_candidates: シグナルのスコア降順ソートと上位 N 選出
    - calc_equal_weights / calc_score_weights: 等配分・スコア加重配分（スコア全0 のフォールバック警告）
  - `kabusys.portfolio.position_sizing`
    - calc_position_sizes: risk_based / equal / score に対応した株数算出。単元（lot_size）丸め、per-stock 上限、aggregate cap（available_cash によるスケーリング）、cost_buffer を用いた保守的見積り、端数の再配分ロジックを実装。
  - `kabusys.portfolio.risk_adjustment`
    - apply_sector_cap: セクター集中を検出し、既存エクスポージャーが閾値を超えたセクターの新規候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: market レジーム（bull/neutral/bear）に基づく投下資金乗数を返す（未知レジームはフォールバックと警告）。

- 共通ユーティリティ
  - `kabusys.utils.logging_setup.setup_logging`：標準出力（stdout）と日次ローテートファイルハンドラをルートロガーに設定し、ログディレクトリ作成や既存ハンドラのクリーンアップ処理を行う。ログレベル/出力先の解決順を定義。
  - `kabusys.utils.process_priority`：Windows / POSIX の差分を吸収してプロセス優先度（high/normal/low）を設定、CPU affinity 固定処理も提供。psutil の権限不足や未対応プラットフォームでは安全にスキップし警告を出す。

- research モジュール（ファクター計算）
  - `kabusys.research.factor_research`：DuckDB を用いたファクター計算の骨組み（モメンタム・MA200乖離・ATR 等）を追加。設計上、DuckDB の prices_daily / raw_financials テーブルのみ参照する純粋関数群を目指す（コードは一部実装途中）。

- パッケージ情報
  - `kabusys.__init__` にバージョン情報 `__version__ = "0.1.0"` を追加。

### Changed
- （初版リリースのため該当なし）

### Fixed
- （初版リリースのため該当なし）

### Security
- 環境変数の取り扱いにおいて、`.env` の自動ロードを無効化するフラグ（KABUSYS_DISABLE_AUTO_ENV_LOAD）を追加。`.env` は Git にコミットしない旨を config_setup のヘッダに明記。

### Notes / Implementation details（主な設計・安全機構）
- DB 分離
  - 監視（monitoring）は環境にかかわらず本番の `sqlite_path` を使用する設計（監視データは本番 DB を想定）。
  - 実行エンジン（execution）は `paper_trading` 環境であれば専用の paper トレード DB を使用し本番 DB と完全に分離する。
- Stop / Kill Switch
  - run_* スクリプトはプロジェクト配下 `data/stop_requested.flag` や `data/kill.flag` 等のファイルを監視して安全に停止する仕組みを持つ（起動時にフラグが立っていると起動を行わない等）。
- ログ
  - stdout に出力する StreamHandler は stdout を利用（stderr と分離）するため、cron や Task Scheduler で stdout まとめ取りしやすい設計。
  - 日次ローテーション（30日保持）をサポート。ログディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソールのみで継続。
- ポートフォリオ・ポジションサイジング
  - 複数の安全弁（per-stock 上限、aggregate cap、lot_size 丸め、cost_buffer で保守見積り）を実装し、利用可能現金を超えないようスケーリングするアルゴリズムを採用。
- プラットフォーム互換性
  - process_priority 周りは Windows / Linux / macOS を考慮し、未対応プラットフォームや権限不足の場合は警告を出して処理をスキップする実装。

---

今後の改善点（想定）
- research.factor_research の完全実装（全ファクターと正規化ユーティリティ連携）
- 銘柄ごとの lot_size 管理や銘柄マスタとの連携（position_sizing の拡張）
- monitoring / execution のさらに詳細なエラーハンドリングとメトリクス充実
- テストカバレッジ向上と CI ワークフローの整備

------------------------------------------------------------
参考:
- 主なエントリポイント
  - python -m kabusys.config_setup
  - python -m kabusys.validate_config
  - python -m kabusys.tools.paper_verification_report
  - run_execution.py / run_monitoring.py（スクリプトとして直接実行可能）