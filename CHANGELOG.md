CHANGELOG
=========

すべての変更は Keep a Changelog（https://keepachangelog.com/ja/1.0.0/）の形式に準拠して記載しています。

Unreleased
----------

なし

[0.1.0] - 2026-04-21
--------------------

Added
- 初回リリース: KabuSys 日本株自動売買フレームワークの基本コンポーネントを追加。
- 設定管理:
  - Settings クラスを実装し、環境変数経由で各種設定を取得可能に。
  - 自動 .env ロード機能を実装（プロジェクトルート検出: .git または pyproject.toml に基づく）。環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能。
  - .env パース機能を強化（export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントルール対応）。
  - PAPER_FILL_MODE、PAPER_TRADING_SQLITE_PATH 等の paper_trading 用設定を追加。PAPER_FILL_MODE の入力検証を実装。
  - 各種監視閾値（CPU/MEM/DISK）や PID / kill flag 等のパス設定を提供。

- CLI ユーティリティ:
  - 対話式設定ウィザード (kabusys.config_setup) を追加し、.env の初期作成・更新を支援。
  - 設定検証ツール (kabusys.validate_config) を追加。必須環境変数、KABUSYS_ENV 値、ログレベル、DB パス、config/*.yaml の存在とパース（PyYAML があれば）を検証。--strict オプションで警告をエラー扱いに可能。

- 起動スクリプト:
  - run_execution: ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV=paper_trading の場合は paper_trading 用 DB を使用し、本番 DB と完全分離。BrokerClientFactory を用いてブローカークライアントを選択。エンジンは別スレッドで実行され、 data/stop_requested.flag による停止制御を実装。プロセス優先度を起動直後に high に設定。
  - run_monitoring: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境にかかわらず本番 sqlite_path を使用する仕様。

- 監視・DB 初期化:
  - init_monitoring_db を呼んで監視テーブルの存在を保証（冪等性あり）。

- ロギング:
  - setup_logging ユーティリティを追加。stdout への StreamHandler と日次ローテーション（TimedRotatingFileHandler）でログを出力。ログディレクトリ自動作成、失敗時はファイル出力をスキップしてコンソールのみで継続。LOG_LEVEL / LOG_DIR による設定を考慮。

- プロセス管理:
  - set_process_priority, set_cpu_affinity を実装（Windows と POSIX 系の差分吸収、psutil 利用、権限不足等の失敗は警告でスキップ）。

- ポートフォリオ構築（純粋関数群）:
  - portfolio_builder: 候補選定 select_candidates、等金額 calc_equal_weights、スコア加重 calc_score_weights を実装。スコアが全て 0 の場合は等金額にフォールバックして警告を出力。
  - risk_adjustment: セクター集中制限 apply_sector_cap（sell_list を除外扱い、unknown セクターは制限除外）、市場レジームに応じた資金乗数 calc_regime_multiplier（bull/neutral/bear マッピング、未知レジームは警告とフォールバック）。
  - position_sizing: calc_position_sizes を実装。allocation_method は "risk_based"（ポジションあたりリスクベース）および "equal"/"score" をサポート。単元株（lot_size）丸め、1 銘柄上限、全体 aggregate cap 調整（スケーリング）と端数の lot 単位での追加配分ロジックを搭載。cost_buffer により保守的なコスト見積りを適用。

- Paper Trading 検証ツール:
  - tools/paper_verification_report を追加。PAPER_TRADING_SQLITE_PATH（または --db）からデータを読み取り、稼働率、注文成功率、送信率、P95 レイテンシ等を集計して PASS/FAIL 判定を出力。P95 計算ユーティリティ、各種閾値（稼働率 99%、fill 90%、send 95%、P95 latency 200 ms）を定義。DB が無い場合のエラーメッセージを実装。

- research:
  - research/factor_research モジュールを追加（ファクター計算の基本設計、定数、calc_momentum の実装開始）。DuckDB を用いて prices_daily / raw_financials を参照する設計。

Changed
- ログ出力方針: stdout を標準出力先とすることでタスクスケジューラや cron でのリダイレクトを容易に。

Fixed
- .env 読み込み時に OS から読み込まれた環境変数を保護するロジックを追加（.env の上書き制御）。.env.local を上書き読み込みする順序を明確化。

Security
- .env ウィザードで秘密情報（J-Quants トークン、kabu API パスワード、LINE トークン）をマスクして表示するようにし、.env ファイルを Git にコミットしない旨の注意を明記。

Deprecated
- なし

Removed
- なし

Notes / Known issues
- research/factor_research.calc_momentum の実装が途中（ファイル末尾が切れている／未完）。完成が必要。
- position_sizing の価格欠損処理（price が 0/未取得の場合のフォールバック）は TODO として注釈あり。将来的に前日終値等のフォールバックロジックを追加することを推奨。
- ログディレクトリ作成やプロセス優先度 / CPU affinity の設定は権限やプラットフォーム依存で失敗する可能性があり、その場合は警告でスキップされる。
- config/*.yaml の存在チェックは PyYAML 非インストール時はパース検証をスキップする仕様。

ライセンス・バージョン
- パッケージバージョンは src/kabusys/__init__.py にて __version__ = "0.1.0" を設定。