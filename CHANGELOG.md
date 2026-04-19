CHANGELOG
=========

このプロジェクトは Keep a Changelog の形式に従って変更履歴を管理しています。  
セマンティックバージョニング (SemVer) を採用しています。

Unreleased
----------

（未リリースの変更はここに記載してください）

0.1.0 — 2026-04-19
------------------

初回リリース。本リリースは自動売買システム「KabuSys」のコア機能群のベース実装を含みます。主な追加点は以下の通りです。

Added
- 実行 / 監視ランナー
  - src/kabusys/run_execution.py
    - ExecutionEngine 起動用のエントリポイントを追加。スレッドでエンジンを実行し、data/execution.pid に PID を書き出す。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用の専用 SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB と分離して動作可能（BrokerClientFactory により MockBrokerClient を選択）。
    - 停止フラグ（data/stop_requested.flag）を監視し、検出時に安全にエンジン停止を行う制御を実装。
  - src/kabusys/run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は監視用 sqlite（settings.sqlite_path）に接続し duckdb も併用。停止フラグファイルの存在でループを終了。

- 設定管理・検証・ウィザード
  - src/kabusys/config.py
    - .env ファイル自動読み込み機構を実装（プロジェクトルートを .git または pyproject.toml で探索）。
    - 細かな .env パーサーを実装（export プレフィックス、クォート対応、インラインコメントの扱い等）。
    - Settings クラスを追加し、環境変数経由で設定値を安全に取得する API を提供（DB パス、PID/kill フラグ、paper_trading 用設定、リソース閾値など）。
  - src/kabusys/config_setup.py
    - 対話式 .env 作成/更新ウィザードを追加。主要な環境変数を対話的に設定して .env ファイルを生成。
  - src/kabusys/validate_config.py
    - 起動前に .env や config/*.yaml の不備を検出する CLI を追加。必須環境変数チェック、KABUSYS_ENV の妥当性、ログレベル、DB パスや YAML の存在・パース確認、KABUSYS_ENV=live 時の追加ガードなどを実装。--strict オプションで警告も失敗扱いにできる。

- ポートフォリオ構築ライブラリ（純粋関数群）
  - src/kabusys/portfolio/portfolio_builder.py
    - シグナル選定（select_candidates）、等分配・スコア加重（calc_equal_weights / calc_score_weights）を実装。スコア全てが 0 の場合は等分配にフォールバック。
  - src/kabusys/portfolio/risk_adjustment.py
    - セクター集中上限の適用（apply_sector_cap）と市場レジームに応じた投下資金乗数（calc_regime_multiplier）を実装。unknown セクターの扱い、レジームフォールバック動作を定義。
  - src/kabusys/portfolio/position_sizing.py
    - 株数決定ロジックを実装（allocation_method: "risk_based" / "equal" / "score" をサポート）。
    - 単元（lot_size）考慮、1銘柄上限、ポートフォリオ総合上限（available_cash）に基づくスケーリング、コストバッファ（cost_buffer）を考慮した保守的な計算を実装。
    - 投下量を lot_size 単位に丸め、残余キャッシュに応じた端数再配分ロジックを実装。

- ユーティリティ
  - src/kabusys/utils/logging_setup.py
    - 統一ログ設定ユーティリティを追加。StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション、30日保持）をルートロガーに設定。ログディレクトリ自動作成と失敗時のフォールバックに対応。
  - src/kabusys/utils/process_priority.py
    - クロスプラットフォームなプロセス優先度設定ユーティリティを追加（set_process_priority）。Windows / POSIX に対するフォールバックを実装。CPU アフィニティ設定（set_cpu_affinity）も提供。

- 監視 DB 初期化
  - src/kabusys/monitoring/monitoring_db.py（参照、init_monitoring_db 呼び出し）
    - 監視テーブルが存在することを保証する初期化処理を run スクリプトで呼び出す（冪等）。

- 分析・検証ツール
  - src/kabusys/tools/paper_verification_report.py
    - Paper Trading の検証レポート生成スクリプトを追加。指定期間の稼働率、注文成功率、送信率、P95 レイテンシ等を集計し PASS/FAIL 判定を出力。PAPER_TRADING_SQLITE_PATH 環境変数または --db オプションで DB 指定可能。
  - src/kabusys/research/factor_research.py
    - DuckDB 経由でのファクター（Momentum, Value, Volatility, Liquidity）計算モジュールのスケルトンを追加（モメンタム計算などの実装方針と定数を定義）。DuckDB の prices_daily / raw_financials を参照する設計。

- パッケージ情報
  - src/kabusys/__init__.py にバージョン情報 __version__ = "0.1.0" を追加。

Changed
- （このリリースでの既存機能の変更はありません）

Fixed
- 環境変数パーサーの堅牢化（_parse_env_line）
  - export プレフィックス、シングル/ダブルクォート内のエスケープ処理、インラインコメントの扱い、不正な行のスキップなどに対応。
- MONITOR_POLL_INTERVAL の不正値処理
  - 0 以下や非整数値が指定された場合は警告を出してデフォルト（60 秒）にフォールバックするようにした（run_monitoring）。
- ログディレクトリ作成失敗時のフォールバック処理
  - ディレクトリ作成に失敗してもコンソール出力のみで継続するようにハンドリングを追加（logging_setup）。
- プロセス優先度/アフィニティ設定の例外ハンドリング
  - 権限不足やプラットフォーム差異で発生する例外をキャッチして警告ログを出すようにした（process_priority）。

Security
- シークレット系（J-Quants トークン、kabu API パスワード、LINE トークン）は .env に保存する前提。config_setup の出力ヘッダで .env を Git にコミットしないよう明示。

Notes / Implementation details of interest
- Paper Trading と Live の DB 分離: run_execution は settings.is_paper を用いて paper_trading 用 SQLite を選択。これにより検証用データと本番データを分離。
- stop/kill フラグの存在をファイルで管理（data/stop_requested.flag, data/kill.flag）。起動時・実行中にこれらのフラグを検査して安全停止や起動抑止を行う設計。
- RiskManager / ExecutionEngine の既定値:
  - RiskConfig は max_position_pct や max_utilization、rate_limit_per_sec、circuit_breaker 閾値、initial_portfolio_value などをデフォルトで設定（初期化時に broker.get_available_cash() を利用）。
- ロギングは stdout を主に使用（cron 等との相性を考慮）。ファイル出力は logs/<app_name>.log に日次ローテーションで蓄積。

既知の改善点（将来対応想定）
- portfolio.position_sizing: 銘柄毎の lot_size をサポートすることで丸め処理の柔軟性を向上予定（TODO コメントあり）。
- risk_adjustment.apply_sector_cap: 価格欠損（price が 0.0）の場合にエクスポージャーが過少見積もられる可能性があり、前日終値等へのフォールバックを検討中。
- research.factor_research: モジュールは設計と一部定数を含むが実装が未完了の関数が存在（今後の実装でファクター計算ロジックを完成予定）。

以上。変更点の詳細や将来の変更についてはソース内のドキュメント／コメントを参照してください。