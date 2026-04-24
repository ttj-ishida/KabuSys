# Changelog

すべての変更は Keep a Changelog のガイドラインに従って記載しています。  
フォーマット: https://keepachangelog.com/ja/

※ リリース日には本リポジトリ内のコードコメントや日付例を参照して 2026-04-24 を使用しています（初回公開相当のまとめです）。

## [Unreleased]

## [0.1.0] - 2026-04-24

### Added
- 全体
  - 初期機能群を追加。日本株自動売買システム「KabuSys」のコアモジュールを実装・公開。
  - パッケージバージョンは `src/kabusys/__init__.py` にて `0.1.0` を設定。

- 実行・監視スクリプト
  - run_execution.py: ExecutionEngine を起動する CLI スクリプトを追加。
    - KABUSYS_ENV に応じた DB 分離: paper_trading 環境では `PAPER_TRADING_SQLITE_PATH`（デフォルト `data/paper_trading.db`）を使用し、本番 DB と記録を完全に分離。
    - BrokerClientFactory を用いたブローカークライアント生成。
    - OrderRepository / OrderManager / Reconciler / RiskManager を組み合わせて ExecutionEngine を構築し、別スレッドで engine.run_session() を実行。stop フラグ（data/stop_requested.flag）検出で安全停止。
    - PID ファイルの管理（`data/execution.pid` を想定）。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` によるポーリング間隔上書き（デフォルト 60 秒）。不正値は警告を出してデフォルトにフォールバック。
    - 停止フラグ（data/stop_requested.flag）検出でループを終了。
    - 監視は環境にかかわらず（KABUSYS_ENV とは独立して）本番向け sqlite_path を使用するよう設計。

- 設定管理・CLI
  - config.py: 環境変数・設定読み込みモジュールを追加。
    - プロジェクトルートの自動検出（.git または pyproject.toml を基準）。
    - .env ファイルの自動読み込み（優先順: OS 環境 > .env.local > .env）。自動ロードは `KABUSYS_DISABLE_AUTO_ENV_LOAD` で無効化可能。
    - 高度な .env パーサ実装（クォート、エスケープ、インラインコメント処理をサポート）。
    - Settings クラスにより、各種設定プロパティを提供（J-Quants, kabuAPI, DB パス, Paper Trading の動作モード, 監視閾値, ログ設定など）。
    - 各プロパティで必要なバリデーション（例: KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE の有効値チェック）。
  - config_setup.py: .env を対話式に作成・更新するウィザードを追加。
    - 既存 .env の読み込み・再利用、シークレットマスキング、保存時の確認、.env ファイル書式の生成。
    - .env を生成する際に「絶対に Git にコミットしない」旨の注意を出力。
  - validate_config.py: 起動前の設定検証ツールを追加。
    - 必須環境変数の存在確認、KABUSYS_ENV や LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ確認、config/*.yaml の存在と（PyYAML があれば）パース検証、KABUSYS_ENV=live の追加ガードなど。
    - --strict オプションで警告を FAIL 扱いにできる。

- ロギング・プロセス管理ユーティリティ
  - utils/logging_setup.py: 統一的なログ設定ユーティリティを追加。
    - stdout への StreamHandler（標準出力）と日次ローテーションの TimedRotatingFileHandler（デフォルト logs/<app_name>.log）をルートロガーに設定。
    - ログレベルとログディレクトリの解決順を定義（引数 > 環境変数 > デフォルト）。
    - ディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
  - utils/process_priority.py: プロセス優先度／CPU affinity 設定ユーティリティを追加。
    - Windows と POSIX（Linux/macOS/FreeBSD）の差分を吸収。`set_process_priority("high"/"normal"/"low")` と `set_cpu_affinity(n)` を提供。
    - 権限不足や未対応 OS の場合は警告を出してスキップ。

- 取引・リスク関連コンポーネント（Execution 系の内部）
  - execution パッケージ（ファイル本体は実装済みの想定）とリスク管理、オーダー管理周りを統合して動作する構成を提供。RiskManager の既定設定や initial_portfolio_value の初期化に broker.get_available_cash() を使用する設計を採用。

- ポートフォリオ構築ライブラリ
  - portfolio/portfolio_builder.py:
    - select_candidates: スコア降順で候補選定（同点は signal_rank でブレーク）。
    - calc_equal_weights / calc_score_weights: 等金額配分・スコア加重配分を提供。スコア総和が 0 の場合は等配分へフォールバック（警告ログ）。
  - portfolio/risk_adjustment.py:
    - apply_sector_cap: セクター集中上限チェック。既存保有のセクター別時価を計算して上限超過セクターの新規候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数を提供（bull/neutral/bear => 1.0/0.7/0.3）。未知の値は警告を出して 1.0 を返す。
  - portfolio/position_sizing.py:
    - calc_position_sizes: allocation_method（"risk_based" / "equal" / "score"）に応じた発注株数計算。単元株（lot_size）丸め、1 銘柄上限、aggregate cap（available_cash）に基づくスケーリングと端数処理を実装。
    - cost_buffer により手数料・スリッページを保守的に見積り。
    - スケーリング時の残差の大きい順に lot 単位で配分するロジックを実装し、再現性のため二次キーにコードを使用。

- ツール
  - tools/paper_verification_report.py: Paper Trading 用の検証レポート生成スクリプトを追加。
    - 指定期間の system_status / trade_logs / risk_logs から稼働率、注文成功率（Filled/Created）、送信率（Sent/Created）、リスク却下数、レイテンシ（avg/max/P95）を算出。
    - P95 の計算、閾値に基づく PASS/FAIL 判定（デフォルト閾値は稼働率 99%、成立率 90%、送信率 95%、P95 latency 200ms）。
    - DB パスは CLI オプション (--db) / 環境変数 / デフォルトの順で解決。

- リサーチ（ファクター計算）基盤
  - research/factor_research.py（実装着手）
    - DuckDB 接続を受け取り、prices_daily / raw_financials を参照するファクター計算モジュール（Momentum, Value, Volatility, Liquidity）を設計。モメンタム計算の定数・骨格を実装（詳細な実装は継続中）。

### Changed
- N/A（初回リリース）

### Fixed
- N/A（初回リリース）

### Deprecated
- N/A

### Removed
- N/A

### Security
- N/A

### Notes / Known issues / TODO
- .env パーサは多くのケースを扱うが、全ての edge case を網羅しているわけではありません。必要に応じて追加のエスケープルールや形式を導入してください。
- position_sizing.calc_position_sizes:
  - price が欠損（0.0）だとエクスポージャーが過小推定され、ブロックが外れる可能性があります。将来的に前日終値や取得原価などのフォールバック価格を導入する予定（コード中に TODO）。
  - 将来的には銘柄別の lot_size を導入する設計拡張を想定（TODO）。
- process_priority / set_cpu_affinity:
  - 権限不足や対応していない OS の場合は警告を出して処理をスキップします。運用環境では権限の確認を推奨。
- logging_setup:
  - ログディレクトリの作成やファイルハンドラの生成に失敗した場合はコンソール出力のみで継続します（警告ログを出力）。
- Paper Trading と本番の DB は明確に分離される設計ですが、運用時に環境変数の設定ミスがないか validate_config で事前チェックすることを推奨します。

---

今後のリリースでは以下を想定しています:
- research/factor_research の完全実装（Momentum / Value / Volatility / Liquidity の出力）
- ExecutionEngine / monitoring の統合テストと追加のエラーハンドリング改善
- さらなる CLI ドキュメントと運用向けの運用手順（デプロイ、監視、ローテーション設定）の追加

（以上）