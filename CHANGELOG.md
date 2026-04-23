# CHANGELOG

すべての変更は「Keep a Changelog」形式に従って記載しています。  
このファイルは、提供されたコードベースから推測できる主要な追加・変更点をまとめたものです。

注意: 日付や「追加」「修正」の分類はコード内容に基づく推測です。実際のコミット履歴と異なる場合があります。

## [Unreleased]

- なし

## [0.1.0] - 2026-04-23

### Added
- プロジェクト初期リリース。
- 全体
  - パッケージメタ情報を追加（kabusys.__version__ = "0.1.0"）。
- 設定・環境
  - 環境変数・設定管理モジュールを追加（kabusys.config）。
    - プロジェクトルート検出（.git または pyproject.toml を基準）。
    - .env 自動読み込み（.env, .env.local）、OS 環境変数の保護機能。
    - .env の行パーサーは export 形式・クォート・インラインコメントに対応。
    - 各種設定プロパティ（J-Quants / kabu API / DB パス / PID / kill flag / thresholds / 環境判定等）を提供。
    - 環境変数自動ロードを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - 対話式設定ウィザードを追加（kabusys.config_setup）。
    - .env の作成・更新を支援する対話式 CLI。
    - シークレット項目のマスク表示、既存値の再利用、.env 書き込み機能。
  - 設定検証 CLI を追加（kabusys.validate_config）。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスの親ディレクトリチェック、config/*.yaml の存在・パースチェック（PyYAML が無ければ警告）。
    - 本番環境向けの追加警告（LINE 通知、KILL_FLAG_CLEAR_ON_START）。
    - --strict オプションで警告を失敗扱いにできる。
- 実行系・監視
  - ExecutionEngine 起動スクリプトを追加（kabusys.run_execution）。
    - プロセス優先度を高に設定する処理を行う（utils.process_priority を利用）。
    - KABUSYS_ENV=paper_trading の場合は専用 SQLite（PAPER_TRADING_SQLITE_PATH）を使用して本番 DB と分離。
    - BrokerClientFactory を介したブローカークライアント作成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、ExecutionEngine の起動・停止ロジックを実装。
    - 停止フラグ（data/stop_requested.flag）検知による安全停止、pid ファイルの取り扱い。
  - SystemMonitor 起動スクリプトを追加（kabusys.run_monitoring）。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は実行環境にかかわらず本番 sqlite_path を利用する設計（監視 DB の一貫性確保）。
    - 停止フラグ検知で監視ループを終了、例外発生時はログ出力して次ポーリングへ継続。
- ロギング・ユーティリティ
  - 統一ログ設定ユーティリティを追加（kabusys.utils.logging_setup）。
    - stdout 出力用 StreamHandler と日次ローテートの TimedRotatingFileHandler（ログディレクトリ作成・30 日保持）をルートロガーに設定。
    - 既存ハンドラのクリア、ログレベル/ログディレクトリ優先解決（引数 > 環境変数 > デフォルト）。
    - ログディレクトリ作成失敗時はファイル出力を無効化し、コンソールのみで稼働するフェールセーフを実装。
- プロセス管理ユーティリティ
  - クロスプラットフォームプロセス優先度・CPU affinity 設定ユーティリティを追加（kabusys.utils.process_priority）。
    - Windows / POSIX (Linux, Darwin, FreeBSD) に対応した nice / priority 設定。
    - psutil の欠如や権限不足に対する警告・フォールバック処理。
    - CPU affinity を最初の N コアに固定する関数を提供。
- ポートフォリオ構築
  - ポートフォリオ構築系の純粋関数群を追加（kabusys.portfolio）。
    - portfolio_builder:
      - select_candidates: BUY シグナルのソート/上位抽出。
      - calc_equal_weights / calc_score_weights: 等配分・スコア加重配分（スコア全0 の場合は等分にフォールバック）。
    - risk_adjustment:
      - apply_sector_cap: セクター集中制限を適用し、上限超過セクターの新規候補を除外（"unknown" セクターは除外対象外）。
      - calc_regime_multiplier: market レジーム ("bull"/"neutral"/"bear") に基づく投資乗数を返す（未知のレジームは 1.0 にフォールバック）。
    - position_sizing:
      - calc_position_sizes: allocation_method (risk_based / equal / score) に基づく発注株数計算。単元株丸め、1 銘柄上限、aggregate cap によるスケールダウン、cost_buffer（手数料・スリッページ見積り）を考慮した配分アルゴリズムを実装。
- Paper Trading / レポート
  - Paper Trading 検証レポート生成スクリプトを追加（kabusys.tools.paper_verification_report）。
    - 稼働率、注文成功率（Fill）、送信率（Sent）、リスク却下数、API レイテンシ（平均/最大/P95）などを算出してレポート出力。
    - P95 計算、期間フィルタ、しきい値判定（稼働率 99%、Fill 90%、Send 95%、P95 レイテンシ 200 ms）を実装。
    - PAPER_TRADING_SQLITE_PATH 環境変数 / --db オプションで DB 指定可能。
- リサーチ
  - ファクター計算モジュール（kabusys.research.factor_research）を追加（実装途中）。
    - モメンタム (1M/3M/6M)、MA200 乖離、ATR・出来高系の計算設計と定数を定義。DuckDB 経由で prices_daily / raw_financials を参照する方針。

### Changed
- なし（初回リリース）

### Fixed
- なし（初回リリース）

### Notes / Implementation details
- 多くのユーティリティは「失敗時は警告を出して処理を続行する」設計を採用しており、運用環境での冗長性を重視している（例: ログディレクトリ作成失敗、psutil の機能不足、DB ファイル未存在時のレポート処理等）。
- .env パースはシェル風のクォート・エスケープを考慮。ただし完全なシェル解釈を模倣するものではない点に注意。
- Paper Trading と本番 DB を明確に分離する設計が取り入れられている（PAPER_TRADING_SQLITE_PATH の導入）。

---

将来的な変更やバグ修正は本 CHANGELOG に追記してください。必要であれば、各モジュールの機能追加・修正をより詳細に分割してバージョン履歴を細かく作成できます。どの粒度で残したいか指示ください。