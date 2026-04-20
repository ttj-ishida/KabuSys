# Changelog

すべての変更は Keep a Changelog の形式に従います。  
このリリースはパッケージバージョン __0.1.0__ に対応します。

## [0.1.0] - 2026-04-20

### Added
- 初期公開: KabuSys のコアユーティリティ・実行スクリプト・ポートフォリオ構築ロジックを追加。
- CLI / スクリプト
  - `python -m kabusys.config_setup` — 対話式の .env 作成/更新ウィザードを追加。シークレットマスク、選択肢、デフォルト値、保存確認付き。
  - `python -m kabusys.validate_config` — 起動前の設定検証ツールを追加。必須環境変数、KABUSYS_ENV、LOG_LEVEL、DBパス、config/*.yaml の存在と簡易パース検証（PyYAML がある場合）をチェック。`--strict` オプションで警告を失敗扱いにできる。
  - `src/kabusys/run_execution.py` — ExecutionEngine 起動スクリプトを追加。`KABUSYS_ENV=paper_trading` 時は paper_trading 用の SQLite を使用して本番 DB と分離（`PAPER_TRADING_SQLITE_PATH` で上書き可能）。起動時にプロセス優先度を `high` に上げ、停止フラグの監視・安全停止に対応。
  - `src/kabusys/run_monitoring.py` — SystemMonitor ポーリングループ起動スクリプトを追加。`MONITOR_POLL_INTERVAL` 環境変数でポーリング間隔上書き可能（デフォルト 60 秒）。監視は環境に関わらず設定の本番 sqlite_path を使用する（監視 DB は一意に扱う）。
- 設定・環境管理
  - `src/kabusys/config.py` — .env 自動読み込み機能を実装（プロジェクトルートの検出、`.env`, `.env.local` の読み込み順、OS 環境変数保護）。`.env` のパースは `export` プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、行内コメントに対応。`Settings` クラスで主要な環境変数をプロパティ化し、バリデーションとデフォルト解決を提供（`PAPER_FILL_MODE` の有効値チェック等）。
- ロギング & プロセス管理ユーティリティ
  - `src/kabusys/utils/logging_setup.py` — 統一ロギング設定ユーティリティ。 stdout への StreamHandler と日次ローテートするファイルハンドラ（TimedRotatingFileHandler）をルートロガーにセット。ログディレクトリ作成失敗時はファイル出力をスキップし、コンソールのみで継続。
  - `src/kabusys/utils/process_priority.py` — クロスプラットフォームでプロセス優先度・CPU affinity を設定するユーティリティを追加。Windows / POSIX(nice) を吸収しアクセス権限不足等を安全にハンドリング。
- ポートフォリオ構築ライブラリ（純粋関数）
  - `kabusys.portfolio.portfolio_builder` — 候補選定(select_candidates)、等配分(calc_equal_weights)、スコア加重(calc_score_weights)。
  - `kabusys.portfolio.risk_adjustment` — セクター集中制限適用(apply_sector_cap)、市場レジームによる乗数(calc_regime_multiplier)。
  - `kabusys.portfolio.position_sizing` — 発注株数決定ロジック(calc_position_sizes)。等配分/スコア/リスクベースの方式をサポート。単元株（lot_size）丸め、銘柄上限・アグリゲートキャップ、コストバッファを考慮したスケーリングを実装。
- モニタリング / Execution 連携
  - 監視テーブル初期化用ユーティリティ `init_monitoring_db` を呼び出す実装が run scripts に組み込まれ、監視テーブルの冪等な初期化を保証。
- Paper Trading 検証ツール
  - `src/kabusys/tools/paper_verification_report.py` — Paper Trading 用 SQLite のログを解析して検証レポートを生成する CLI を追加。期間指定オプション `--from` / `--to`、DB 指定 `--db` をサポート。稼働率、注文成功率、送信率、P95 レイテンシ等を集計し、閾値（稼働率 99%、成功率 90%、送信率 95%、P95 200ms）に基づく PASS/FAIL 判定を出力。
- 研究用モジュール始動
  - `src/kabusys/research/factor_research.py` を追加。Momentum / Value / Volatility / Liquidity 等のファクターを DuckDB の prices_daily / raw_financials テーブルから計算する方針を実装（モジュール骨子・定数・calc_momentum の実装開始を含む）。

### Changed
- （初回リリースのため該当なし）既存の振る舞いを明示する注記やデフォルト値を整備（例: logging の出力先解決順、.env の自動ロード挙動など）。

### Fixed
- （初回リリースのため該当なし）運用で想定される例外・失敗ケースに対する防御的ハンドリングを追加：
  - .env ファイル読み込み失敗時は警告発行して継続。
  - ログディレクトリ作成/ファイルハンドラ作成失敗時はコンソールログのみで継続。
  - process priority / cpu affinity の設定で権限不足や未実装例外が発生した場合は警告を出してスキップ。
  - run_monitoring の check_once() 内例外は catch して次ポーリングまで継続。

### Deprecated
- なし

### Removed
- なし

### Security
- なし

---

注記・既知の制限:
- run_monitoring は意図的に「監視用 DB は環境に関わらず本番 sqlite_path を使用」する設計。運用上の分離が必要な場合は環境変数でパスを調整してください。
- `research/factor_research.py` はファクター計算の骨子と一部実装を含みますが、完全実装・テストは引き続き進行中です。
- Execution 起動時の RiskManager 初期値（初期ポートフォリオ値）に broker.get_available_cash() を使用。Broker 実装が返す値に依存します。
- .env 自動ロードはプロジェクトルートが検出できない場合はスキップされます（テスト等では `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能）。

この CHANGELOG はコードベースからの推定に基づいて作成しています。詳細な変更履歴（個別コミット・差分）はバージョン管理履歴を参照してください。