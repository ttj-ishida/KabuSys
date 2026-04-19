CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠しています。
さらに詳細な履歴が必要な場合はリポジトリのコミットログを参照してください。

Unreleased
----------

- 進行中 / 予定:
  - research.factor_research の実装が途中で終わっている箇所（ソース内にコメント・未完のコードあり）。ファクター計算の残り実装（データ読み込みの範囲調整・集計処理など）を予定。
  - portfolio.position_sizing の将来的拡張: 銘柄別の単元（lot_size）を stocks マスタから取得するなどの設計変更検討中。
  - apply_sector_cap の価格欠損時のフォールバック（前日終値や取得原価を使う）を将来的に追加予定。

0.1.0 - 2026-04-19
------------------

Added
- 初回リリース（パッケージバージョン: 0.1.0）
  - パッケージのメタ情報を追加:
    - src/kabusys/__init__.py に __version__ = "0.1.0"
  - 設定関連:
    - 環境変数読み込み・管理モジュールを追加（src/kabusys/config.py）。
      - .env 自動読み込み機能（プロジェクトルートの検出: .git または pyproject.toml）。
      - export プレフィックス、クォート文字、バックスラッシュエスケープ、インラインコメントなどに対応した堅牢な .env パーサー。
      - Settings クラス（各種環境変数のラッパー、デフォルト値・バリデーション込み）。
    - 対話式の .env 作成・更新ウィザードを追加（src/kabusys/config_setup.py）。
      - 主要設定項目（KABUSYS_ENV、J-Quants トークン、kabu API パスワード、DBパス、LOG_LEVEL 等）を対話的に生成可能。
    - 起動前検証 CLI を追加（src/kabusys/validate_config.py）。
      - 必須環境変数チェック、KABUSYS_ENV の妥当性、ログレベル、DB パス、config/*.yaml の存在・パース（PyYAML があれば内容検証）などを実施。
      - --strict オプションで警告も失敗扱いにできる。
  - 実行・監視ランチャー:
    - ExecutionEngine 起動スクリプトを追加（src/kabusys/run_execution.py）。
      - プロセス優先度設定（High）や PID ファイル管理、停止フラグ（data/stop_requested.flag）対応。
      - KABUSYS_ENV=paper_trading の場合に paper_trading 専用 SQLite（data/paper_trading.db をデフォルト）を使って本番 DB と分離する設計（MockBrokerClient を利用する想定）。
      - ExecutionEngine／OrderManager／RiskManager／Reconciler の組み立て・起動処理（スレッドで実行・停止フラグ監視）。
    - SystemMonitor 起動スクリプトを追加（src/kabusys/run_monitoring.py）。
      - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒、0 以下はデフォルトにフォールバック）。
      - Monitoring は環境にかかわらず本番用 sqlite_path を使用する（運用上の設計）。
      - stop フラグ検知でループ終了、例外時のログ出力と継続処理。
  - 監視・診断関連:
    - 監視 DB 初期化ユーティリティ（init_monitoring_db の利用点が複数）。
    - Paper Trading の検証レポート生成スクリプトを追加（src/kabusys/tools/paper_verification_report.py）。
      - 指標: 稼働率 (uptime)、注文成功率 (fill rate)、送信率 (send rate)、API レイテンシ (P95 など)。
      - データが不足する場合の N/A 処理、閾値による PASS/FAIL 判定を実装。
  - ポートフォリオ構築関連:
    - 銘柄選定・重み付けユーティリティ（src/kabusys/portfolio/portfolio_builder.py）
      - select_candidates: score 降順 + signal_rank タイブレーク
      - calc_equal_weights, calc_score_weights（全スコア 0 の場合は等金額にフォールバック）
    - セクター集中制限・レジーム乗数（src/kabusys/portfolio/risk_adjustment.py）
      - apply_sector_cap: 既存ポジションをベースにセクター上限を超える場合に候補を除外（unknown セクターは無視）
      - calc_regime_multiplier: bull/neutral/bear に応じた資金乗数（未知レジームはフォールバックして 1.0）
    - ポジションサイズ計算（src/kabusys/portfolio/position_sizing.py）
      - allocation_method ("risk_based", "equal", "score") に対応
      - lot_size（単元）丸め、per-position 上限・aggregate cap のスケーリング、cost_buffer による保守的見積り
      - aggregate cap が超過する場合のスケーリングと残余配分ロジック（fractional remainder に基づく再配分）
  - ユーティリティ:
    - ログ設定ユーティリティを追加（src/kabusys/utils/logging_setup.py）
      - StreamHandler (stdout) と TimedRotatingFileHandler（日次・30日保持）をルートロガーに設定
      - LOG_DIR 作成失敗時はファイル出力をスキップしてコンソールのみで継続
      - 引数/環境変数/デフォルトからログレベルおよびディレクトリを決定
    - プロセス優先度 / CPU affinity 設定ユーティリティを追加（src/kabusys/utils/process_priority.py）
      - Windows / POSIX を吸収、psutil を用いて nice 値 / HIGH_PRIORITY_CLASS を設定
      - set_cpu_affinity により最初の N コアに固定可能（サポートされない環境では警告を出してスキップ）
  - リサーチ関連（骨格）:
    - ファクター計算モジュールの骨格を追加（src/kabusys/research/factor_research.py）
      - モメンタム、MA200乖離、ATR、流動性などの設計方針と定数を定義。DuckDB の接続を受けて SQL/Python で計算する想定。実装は一部未完。

Changed
- 設計・実装上の注意点を注記
  - .env 自動ロードの優先順位: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロードを無効化可能。
  - validate_config では PyYAML が未インストールの場合、YAML 検証をスキップして警告を出力するようにして堅牢化。
  - run_monitoring は例外発生時にループを継続し、次ポーリングでリトライするようにログ出力と例外捕捉を追加。
  - run_execution/run_monitoring といった起動スクリプトは起動時にプロセス優先度を高く設定する（set_process_priority("high")）。

Fixed
- .env のパースの堅牢化
  - export プレフィックス、シングル/ダブルクォート内部のバックスラッシュエスケープ、インラインコメントの取り扱い、無効行の無視などを実装して誤読を防止。
- ログディレクトリ作成失敗時のフォールバック処理を追加（アプリ起動に致命的にならないようにする）。

Known issues / Notes
- research.factor_research は未完の箇所があり（ソース末尾に未完の変数名 start_da 等）、そのままでは一部の機能が未実装／テスト未了です。
- apply_sector_cap の価格欠損時（price_map に存在しない場合）は現状 0.0 を使っているため、エクスポージャーが過小評価される可能性があるとの注記（ソース内に TODO）。
- position_sizing の将来的な拡張（銘柄別単元やマスタ取り込み）が未実装。
- Paper Trading 検証ツールは DB のスキーマ依存（trade_logs, system_status, risk_logs 等）。対象 DB が期待スキーマでない場合、OperationalError を捕捉して N/A で出力する設計だが、詳細なエラー解析は別途必要。

Security
- J-Quants リフレッシュトークンや kabuAPI パスワードなどの機密情報は .env に格納する設計。config_setup の注意書き通り .env をリポジトリにコミットしないこと。
- validate_config で必須環境変数未設定時はエラーを報告するため、起動前に確認可能。

Appendix
- 開発・運用向けヒント:
  - 起動スクリプトは stop フラグ（data/stop_requested.flag）や PID ファイル（data/execution.pid）を用いて外部からの停止/状態管理を行えるように設計されています。
  - ログはデフォルトで logs/<app_name>.log に日次ローテーションで保存されます。LOG_DIR 環境変数で変更可能です。
  - MONITOR_POLL_INTERVAL に不正値（0 や負または非数）を与えるとデフォルト（60 秒）にフォールバックします。