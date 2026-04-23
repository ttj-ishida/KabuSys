# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」規約に準拠します。

現在のリリース方針：
- セマンティックバージョニング（MAJOR.MINOR.PATCH）を想定。
- 主要な機能追加・設計は Added、後方互換性のある改善は Changed、バグ修正は Fixed に記載します。

なお、この CHANGELOG はリポジトリ内のコードを解析して推測した変更点を基に作成しています。

## [Unreleased]
- （今後の変更をここに記載）

## [0.1.0] - 2026-04-23
初回リリース。システム全体の起動スクリプト、設定管理、検証ツール、ポートフォリオ構成ロジック、ユーティリティ等を実装。

### Added
- 起動スクリプト
  - run_execution.py
    - ExecutionEngine を起動するエントリポイントを追加。プロセス優先度を設定し、スレッドでエンジンを実行。
    - KABUSYS_ENV が `paper_trading` の場合は専用の paper_trading DB を使用し、本番 DB と分離（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）。
    - BrokerClientFactory によりブローカークライアントを生成し、OrderRepository / OrderManager / RiskManager / Reconciler を組み立ててエンジンを起動。
    - 停止フラグ（data/execution.pid / data/stop_requested.flag）を監視し安全に停止可能。
  - run_monitoring.py
    - SystemMonitor のポーリングループを起動するスクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は KABUSYS_ENV にかかわらず本番用の sqlite_path を使用（監視データは共通の監視 DB に保存）。
    - stop フラグファイルでループ終了を制御。

- 設定管理
  - config.py
    - Settings クラスでアプリケーション設定をプロパティとして提供（J-Quants、kabu API、LINE、DB パス、監視閾値、環境判定など）。
    - プロジェクトルート検出（.git または pyproject.toml）に基づき .env 自動読み込みを実装（.env と .env.local、OS 環境変数優先）。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - .env のパースは引用符やエスケープ、コメントの扱いに対応。
    - PAPER_FILL_MODE の妥当性チェックや KABUSYS_ENV / LOG_LEVEL の検証を実装。
    - settings インスタンスをモジュールレベルで提供。

  - config_setup.py
    - 対話式ウィザードで .env を生成/更新する CLI を追加（項目の説明、シークレットマスク、デフォルト提供、保存の確認など）。
    - 書き込みフォーマットは .env に適したテンプレートで出力。

  - validate_config.py
    - 起動前チェック用 CLI を追加。必須環境変数の未設定、KABUSYS_ENV の不正値、ログレベル、DB パスの親ディレクトリ、config/*.yaml の存在・パース（PyYAML 利用時）等を検証。
    - --strict モードで警告も失敗（exit(1)）として扱う機能を追加。
    - 本番環境（KABUSYS_ENV=live）向けの追加ガード（LINE 通知設定、KILL_FLAG_CLEAR_ON_START の注意喚起）を実装。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading 用 SQLite DB（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）から検証レポートを生成するスクリプトを追加。
    - 稼働率・注文成功率・送信率・リスク却下数・API レイテンシ（平均・最大・P95）を集計し PASS/FAIL 判定を行う。
    - デフォルトの閾値を定義（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200ms）。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - シグナル候補の選定 select_candidates、等金額重み calc_equal_weights、スコア加重 calc_score_weights を実装。
    - スコア合計が 0 の場合に等金額配分へフォールバック（警告ログ）。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中制限により候補を除外するロジックを実装（売却予定銘柄の除外、"unknown" セクターの扱いなど）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた資金乗数を提供（未知のレジームは 1.0 へフォールバック）。
  - portfolio/position_sizing.py
    - calc_position_sizes: 等配分 / スコア配分 / リスクベース配分に応じた発注株数決定ロジックを実装。
    - 単元株（lot_size）で丸め、1銘柄上限、aggregate 上限（available_cash）でスケールダウンするアルゴリズムを実装。
    - cost_buffer により手数料・スリッページを保守的に見積もる処理を導入。
    - リスクベース配分では stop_loss_pct と risk_pct を用いた計算を採用。

- ユーティリティ
  - utils/logging_setup.py
    - 全起動スクリプトから共通で利用できるログ設定ユーティリティを追加。
    - stdout への StreamHandler（標準出力）、日次ローテーションされる TimedRotatingFileHandler（logs/<app_name>.log）を設定。
    - 既存ハンドラのクリーンアップやログディレクトリ作成失敗時のフォールバックを実装。
    - LOG_DIR / LOG_LEVEL 環境変数や関数引数で挙動を調整可能。
  - utils/process_priority.py
    - psutil を用いたプロセス優先度設定（set_process_priority）と CPU affinity 設定（set_cpu_affinity）を追加。
    - Windows / POSIX（Linux, Darwin, FreeBSD）を吸収する実装で、権限不足等のケースは警告ログを出して安全にスキップ。

- パッケージ情報
  - __init__.py にてパッケージバージョン __version__ = "0.1.0" を設定。

- 研究モジュール（部分実装）
  - research/factor_research.py
    - ファクター計算（モメンタム等）を実装するための骨格を追加。DuckDB を使い prices_daily / raw_financials から因子を計算する設計。
    - 参照する日数や移動平均・ATR 等の定数を定義（関数 calc_momentum は実装途中の様子）。

### Changed
- （初回リリースのため過去の変更なし）

### Fixed
- （初回リリースのため過去の修正なし）

### Security
- 環境ファイル管理に関する注意を README / .env コメント内に記載（.env を Git にコミットしない旨）。

---

補足:
- 停止・キル制御は file-based flag（data/stop_requested.flag、data/kill.flag）および pid ファイルを用いているため、運用時には data ディレクトリの位置と権限管理に注意してください。
- .env の自動読み込みはプロジェクトルート検出に依存するため、パッケージ配布後も正しく動作するように __file__ を基準に探索しています。
- paper_trading モードでは実世界の発注とは完全に分離される設計になっており、専用の SQLite を利用します。

（この CHANGELOG はコードの内容から推測して作成しました。実際のリリースノートとして使用する場合は、変更差分やコミットメッセージを基に適宜調整してください。）