# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠しています。主要なリリース履歴と変更点を日本語で記載します。  
（内容はソースコードから推測して記載しています）

## [Unreleased]

- 現時点で未リリースの変更はありません。

## [0.1.0] - 2026-04-19

初回公開リリース。システム全体の基本機能（設定管理、起動スクリプト、監視・実行エンジン周辺、ポートフォリオ構築、ユーティリティ、検証/ウィザードツール、Paper Trading 検証レポート、ファクター計算の骨組み）を実装・統合しました。

### Added
- 基本パッケージ情報
  - パッケージ初期バージョンを設定（kabusys.__version__ = "0.1.0"）。
- 環境・設定管理
  - .env 自動読み込み機能の導入（プロジェクトルートを .git / pyproject.toml から検出）。
  - .env パースの強化:
    - export プレフィックス対応。
    - シングル/ダブルクォート内のエスケープ処理対応。
    - コメント処理（クォート有無に応じた柔軟な処理）。
  - OS 環境変数を保護する protected オプション、KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化を追加。
  - Settings クラスを実装し、各種環境変数（J-Quants／kabu API／DB パス／Paper Trading 設定／監視閾値／実行環境判定 等）をプロパティ経由で検証・提供。
  - PAPER_FILL_MODE の検証（有効値: instant|partial|never|reject）。
  - Paper Trading 用の専用 SQLite パス設定（PAPER_TRADING_SQLITE_PATH）を追加。
- 設定ユーティリティ / CLI
  - 対話式設定ウィザード（kabusys.config_setup）を追加。.env の初期作成・更新を支援。
  - 設定検証 CLI（kabusys.validate_config）を追加。.env および config/*.yaml の存在・整合性チェック。--strict モードで警告を FAIL 扱いに可能。
  - validate_config は PyYAML 未インストール時に YAML 検証をスキップし警告を出力する。
- 起動スクリプト
  - 実行エンジン起動スクリプト（run_execution）を追加。
    - KABUSYS_ENV=paper_trading の場合は Paper Trading 用 DB を使用し、本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler / ExecutionEngine の組み立て。
    - スレッドでエンジンを実行し、外部 stop フラグ（data/stop_requested.flag）で安全停止。
    - PID ファイル制御（data/execution.pid）対応。
  - 監視ループ起動スクリプト（run_monitoring）を追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き（デフォルト 60秒）。不正値は警告のうえデフォルトにフォールバック。
    - 監視は環境設定にかかわらず本番 sqlite_path を使用する挙動を明示。
    - stop フラグ検知でループを終了、例外発生時はログに出して次回迄待機。
- 監視 DB 初期化
  - init_monitoring_db 呼び出しを起動箇所に含め、監視テーブルの存在を保証（冪等）。
- ロギング / プロセス管理ユーティリティ
  - 統一的ロギング設定ユーティリティ（kabusys.utils.logging_setup.setup_logging）を追加。
    - stdout 出力用 StreamHandler と 日次ローテートの TimedRotatingFileHandler（デフォルト logs/、30日保持）を設定。
    - 既存ハンドラをクリアして多重設定を防止。
    - LOG_DIR / LOG_LEVEL の解決順を実装。ログディレクトリ作成失敗時はファイル出力をスキップして stdout へフォールバック。
  - プロセス優先度・CPU affinity 制御ユーティリティ（kabusys.utils.process_priority）を追加。
    - Windows / POSIX（Linux, Darwin, FreeBSD）対応。優先度レベル: high/normal/low。
    - set_cpu_affinity により最初の N コアにプロセスをピン止め可能。設定失敗時は警告を出してスキップ。
- ポートフォリオ構築ライブラリ（kabusys.portfolio）
  - 候補選定: select_candidates（スコア降順、タイブレークに signal_rank を使用）。
  - 重み計算: calc_equal_weights（等金額）、calc_score_weights（スコア正規化。全スコアが 0 の場合は等金額にフォールバックして警告）。
  - リスク調整: apply_sector_cap（セクター集中制限、unknown セクターは制限対象外）、calc_regime_multiplier（市場レジーム別乗数 + 未知レジームのフォールバックで警告）。
  - ポジションサイジング: calc_position_sizes
    - allocation_method: "risk_based", "equal", "score" をサポート。
    - 単元株（lot_size）丸め、max_position_pct、max_utilization、cost_buffer（手数料・スリッページ見積）を考慮した集約キャップ処理。
    - aggregate cap を超える場合はスケールダウンし、余りキャッシュで残差の大きい銘柄順に単元を追加配分するロジックを実装。
- Paper Trading 検証レポート
  - ツール（kabusys.tools.paper_verification_report）を追加。PAPER_TRADING_SQLITE_PATH を参照し、稼働率・注文成功率・送信率・レイテンシ（平均・最大・P95）・リスク却下数を集計して PASS/FAIL を判定する。
  - デフォルト閾値: 稼働率 99% / 注文成立率 90% / 送信率 95% / P95 レイテンシ 200 ms。
  - コマンドラインで日付レンジ（--from, --to）および DB パス（--db）を指定可能。
- 研究モジュール（骨組み）
  - ファクター計算モジュール（kabusys.research.factor_research）を追加。Momentum, Value, Volatility, Liquidity 等を計算する設計。モメンタム計算のための定数・枠組みを実装（prices_daily / raw_financials を想定した DuckDB 統合）。
  - DuckDB 接続を受け取り SQL + Python で計算する設計方針を採用。

### Changed
- 監視と実行の挙動設計
  - run_execution と run_monitoring の起動フローで起動直後にプロセス優先度を "high" に設定するようにして、他プロセスとの競合を緩和。
  - run_execution は Paper Trading 時に本番 SQLite を使用せず paper_sqlite_path を使用することで完全分離を実現。
  - 監視ループでは例外捕捉を追加し、1 回の失敗でプロセスが落ちないように保護。
- ロギング
  - StreamHandler を stdout に設定（stderr ではなく）して Task Scheduler / cron 等でのリダイレクト運用を想定。
  - 既存ハンドラのフラッシュ／クローズ処理を行い確実にハンドラを置き換えるように変更。

### Fixed
- 環境変数読み込みの堅牢化
  - .env パースで引用符・エスケープ・インラインコメント処理に対応し、誤った読み込みや不正なキー取り込みを防止。
  - _load_env_file のファイル読み込み失敗を警告にとどめプロセスを継続するようにして、IO エラーで起動失敗しないよう改善。
- ポジションサイジング
  - aggregate スケールダウン時の丸め処理・残差配分アルゴリズムを実装し、利用可能現金を超過する無効な発注量が生成されないように修正。
- process_priority / CPU affinity
  - 未対応 OS や権限不足時に例外で停止しないように捕捉して警告する実装に改善。

### Known issues / Notes
- research.factor_research モジュールは設計方針とモメンタム計算の骨組みを実装していますが、関数の完全な実装（データ取得と全ファクター計算の最終化）が未完になる可能性があります（ソースの一部が途中までの実装となっていることを確認してください）。
- 一部の TODO コメント（例: price 欠損時のフォールバック価格利用、個別銘柄の lot_size 拡張など）は将来の改善項目です。
- 設定ファイル（config/*.yaml）は存在しない場合に警告を出します。PyYAML 未導入環境では YAML パースをスキップします。

---

上記は現行のコードベースから推測してまとめた CHANGELOG です。必要があれば、実際のコミット履歴・差分に合わせて日付や細かな表現（破壊的変更の明示、マイグレーション手順など）を追記できます。どの程度の粒度で履歴を残したいか指示いただければ、より細かく分割してバージョン毎に整備します。