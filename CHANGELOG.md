# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠して記載しています。  
本ファイルはコードベースから推測して生成したリリースノートです。実装のコメントや挙動に基づく要約であり、実際のコミット履歴とは異なる場合があります。

## [Unreleased]

### 追加
- なし

### 変更
- なし

### 修正
- なし

---

## [0.1.0] - 初回リリース (推定)
リリース日: 未指定

### Added
- パッケージ基盤
  - kabusys パッケージ初期構成を追加。__version__ = "0.1.0" を設定。
  - パッケージ公開時の public API を __all__ に定義（data, strategy, execution, monitoring）。

- 設定管理
  - 環境変数読み込み・管理モジュール (src/kabusys/config.py)
    - プロジェクトルート自動探索（.git または pyproject.toml）により .env/.env.local を自動読み込み。
    - .env のパースはクォート・エスケープ・コメントを考慮した堅牢な実装。
    - 必須環境変数チェック用の _require ユーティリティを提供。
    - 各種設定プロパティを提供（J-Quants トークン、kabu API、DB パス、PID ファイルパス、監視閾値、環境種別など）。
    - PAPER_FILL_MODE の妥当性チェック（instant/partial/never/reject）を導入。
    - paper_trading 用の別 SQLite パス (PAPER_TRADING_SQLITE_PATH) をサポート。

  - 環境設定ウィザード CLI (src/kabusys/config_setup.py)
    - 対話式で .env を初期作成・更新するウィザードを追加。
    - デフォルト値、選択肢、シークレット入力の扱い、既存 .env 読み込み、保存確認を実装。
    - .env を書き出す際に注意書きを付与（.env をコミットしない旨の警告）。

  - 設定検証 CLI (src/kabusys/validate_config.py)
    - .env と config/*.yaml の基本整合性チェックを行う CLI を追加。
    - 必須環境変数の未設定、プレースホルダ値、KABUSYS_ENV/LOG_LEVEL の整合性、DB パスの親ディレクトリ存在確認を実施。
    - PyYAML が未インストールの場合に YAML 検証をスキップするフォールバックを用意。
    - KABUSYS_ENV=live 時の本番ガード（LINE 設定未設定や KILL_FLAG_CLEAR_ON_START の危険設定検出）を追加。
    - --strict オプションで警告を FAIL 扱いにできる。

- 実行ユーティリティ / デーモン起動スクリプト
  - 実行エンジン起動スクリプト (src/kabusys/run_execution.py)
    - ExecutionEngine の起動処理を提供。
    - KABUSYS_ENV=paper_trading の場合は paper 用専用 SQLite DB に切替え（本番 DB と分離）。
    - BrokerClientFactory を介して実際のブローカまたはモックを生成。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine を起動。
    - stop フラグ（data/stop_requested.flag）と pid ファイル管理、スレッド実行・停止監視を実装。

  - 監視プロセス起動スクリプト (src/kabusys/run_monitoring.py)
    - SystemMonitor のポーリングループを起動するスクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトへフォールバック。
    - 監視は KABUSYS_ENV に関わらず本番 sqlite_path を使用して監視データを記録。
    - stop フラグ検知でループ終了、KeyboardInterrupt のハンドリング、DB 接続のクリーンアップを実装。

- ロギング・プロセス管理ユーティリティ
  - ログ設定ユーティリティ (src/kabusys/utils/logging_setup.py)
    - StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション、30日保持）を root ロガーに設定する共通関数を追加。
    - 既存ハンドラのクリア、ログレベル・ログディレクトリの解決順を定義。
    - ログディレクトリ作成失敗時はファイルハンドラをスキップして stdout のみで継続。
    - stdout を利用することで cron 等でのリダイレクト運用に配慮。

  - プロセス優先度 / CPU アフィニティユーティリティ (src/kabusys/utils/process_priority.py)
    - Windows/Linux/macOS を抽象化してプロセス優先度（high/normal/low）を設定する関数を追加。
    - CPU affinity を最初の N コアに固定する set_cpu_affinity を提供。
    - 権限不足や未対応 OS に対するフォールバック・警告を実装。

- ポートフォリオ構築関連ライブラリ（純粋関数群）
  - portfolio_builder (src/kabusys/portfolio/portfolio_builder.py)
    - シグナル選定(select_candidates)、等金額配分(calc_equal_weights)、スコア加重(calc_score_weights) を追加。スコア合計が 0 の際は等分にフォールバック。

  - risk_adjustment (src/kabusys/portfolio/risk_adjustment.py)
    - セクター集中制限 apply_sector_cap（当日売却銘柄を除外可能、"unknown" セクターは無視）を実装。
    - 市場レジームに応じた投下資金乗数 calc_regime_multiplier（bull/neutral/bear をマッピング）を実装。

  - position_sizing (src/kabusys/portfolio/position_sizing.py)
    - position sizing ロジックを実装（allocation_method: "risk_based"/"equal"/"score"）。
    - lot_size（単元）考慮、max_position_pct、max_utilization、cost_buffer を加味した aggregate cap のスケールダウンアルゴリズムを実装。
    - 小数端数を lot 単位で調整するアルゴリズムを実装（fractional remainder に基づく追加配分）。

  - portfolio パッケージの __init__ を整備して上記関数群をエクスポート。

- リサーチ / ファクター計算（基盤）
  - factor_research (src/kabusys/research/factor_research.py)
    - Momentum / Value / Volatility / Liquidity の設計に基づくモジュール骨格を追加。
    - DuckDB 接続を受け取り、prices_daily / raw_financials を参照して計算する設計注記を含む。
    - P95 等の統計ユーティリティや計算定数を定義。
    - （注）関数実装は継続中のため一部未完。

- Paper Trading 検証ツール
  - paper_verification_report (src/kabusys/tools/paper_verification_report.py)
    - ペーパートレード用 SQLite（デフォルト data/paper_trading.db）を読み取り、期間指定可能な検証レポートを標準出力に生成。
    - システム稼働率、注文成功率（fill_rate）、送信率（send_rate）、P95 レイテンシ等を算出し PASS/FAIL 判定を行う。
    - P95 の計算、日付フィルタの組み立て、欠損テーブルに対するフォールバックを実装。
    - CLI オプション --from/--to/--db をサポート。

- 監視 DB 初期化
  - monitoring_db.init_monitoring_db を実行して監視用テーブルの存在を保証する呼び出しを run_monitoring/run_execution に追加（冪等に実行）。

### Changed
- 起動処理におけるプロセス優先度設定を最初に行うように変更（set_process_priority("high") を起動直後に呼び出す）して、重要プロセスの実行安定性を向上。
- ログ出力を stdout に統一（StreamHandler を stdout に設定）。cron/Task Scheduler などの運用を想定。
- run_execution は paper_trading モード時に専用 SQLite を使用することで本番 DB とデータ分離を担保。

### Fixed
- MONITOR_POLL_INTERVAL のパースで 0 以下や不正な文字列が指定された場合にデフォルト値へフォールバックするように安全化（run_monitoring）。
- logging_setup: ログディレクトリ作成に失敗した際にファイル出力をスキップしてもアプリが継続できるようにエラーハンドリングを追加。
- process_priority: サポート外 OS や権限不足時に警告を出して処理をスキップすることで例外による起動失敗を回避。

### Deprecated
- なし

### Removed
- なし

### Security
- .env を生成する際の注意書きを出力し、.env を絶対に Git にコミットしないよう強調（config_setup）。
- 必須の機密項目（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）は _require() を通じて未設定時に明示的なエラーを発生させる。

### Known issues / TODO
- portfolio/risk_adjustment.apply_sector_cap:
  - price が欠損（0.0）の場合にエクスポージャーが過少見積もられる可能性があり、将来的に前日終値や取得原価などのフォールバック価格を検討する旨の TODO コメントあり。
- research/factor_research.py:
  - ファイル末尾付近で関数実装が未完（行が途切れている）。ファクター計算ロジックの完成が必要。
- position_sizing:
  - lot_size は現状全銘柄共通の仮定。将来的に銘柄ごとの lot_map を受け取る拡張が想定されている。
- run_monitoring/run_execution:
  - stop フラグや kill フラグの扱いはファイルベース（data/stop_requested.flag, data/kill.flag）。複数プロセス運用時の排他や分散環境での運用については追加設計が必要。

---

脚注:
- 本 CHANGELOG はリポジトリ内のソースコード（関数名・コメント・docstring・処理の分岐など）から推測して作成したものであり、実際のリリースノートやコミットメッセージとは異なる可能性があります。変更内容の最終確認はソース管理履歴（git log）を参照してください。