KEEP A CHANGELOG に準拠した CHANGELOG.md（日本語）

すべての変更はパッケージバージョン __version__ = "0.1.0" に基づき推測して記載しています。
日付は本日（2026-04-25）をリリース日として設定しています。

フォーマット: https://keepachangelog.com/ja/1.0.0/

Unreleased
----------

（なし）

[0.1.0] - 2026-04-25
-------------------

Added
- 基本機能の初期実装を追加。
  - 環境設定/読み込み
    - .env / .env.local 自動読み込み機能を実装（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。（src/kabusys/config.py）
    - .env ファイルの柔軟なパース実装（export プレフィックス、クォート値、インラインコメント等に対応）。（src/kabusys/config.py）
    - Settings クラスを導入し、アプリケーション設定をプロパティ経由で取得可能にした（DBパス、KABUSYS_ENV、PAPER_FILL_MODE 等）。環境値のバリデーションを含む。（src/kabusys/config.py）
  - 設定関連 CLI
    - 対話式 .env 作成/更新ウィザードを追加（python -m kabusys.config_setup）。既存 .env 読み込み・シークレットマスク表示等をサポート。（src/kabusys/config_setup.py）
    - 起動前に環境変数や config/*.yaml の妥当性を検証する CLI を追加（python -m kabusys.validate_config）。--strict オプションで警告を fail 扱いにできる。PyYAML が無い場合は YAML 検証をスキップする旨の警告を出す実装。（src/kabusys/validate_config.py）
  - 起動スクリプト
    - SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境に関わらず本番 sqlite_path を使用する仕様。（src/kabusys/run_monitoring.py）
    - ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV=paper_trading の場合は専用のペーパートレード用 SQLite を使用し MockBrokerClient を利用する（本番 DB と分離）。停止フラグや PID 管理を行う。（src/kabusys/run_execution.py）
  - ロギング / プロセス制御
    - 統一的ログ設定ユーティリティを追加。StreamHandler（stdout）と日次ローテートの TimedRotatingFileHandler をルートロガーに設定する。ログディレクトリ作成失敗時はファイル出力をスキップして標準出力のみで継続する。（src/kabusys/utils/logging_setup.py）
    - プロセス優先度・CPU affinity 設定ユーティリティを追加。Windows / POSIX の差分を吸収し、失敗時は警告を出してスキップする。（src/kabusys/utils/process_priority.py）
  - ポートフォリオ構築（純粋関数群）
    - 候補選定・重み付け: select_candidates, calc_equal_weights, calc_score_weights を実装。スコアが全て 0 のときは等金額配分にフォールバック。（src/kabusys/portfolio/portfolio_builder.py）
    - セクターキャップ・レジーム乗数: apply_sector_cap（既存保有セクターが閾値を超えている場合に候補を除外）、calc_regime_multiplier（レジームに応じた投下資金乗数）を実装。未知のレジーム時はフォールバックと警告。（src/kabusys/portfolio/risk_adjustment.py）
    - ポジションサイズ決定: calc_position_sizes を実装。risk_based / equal / score の配分方式に対応、単元株（lot_size）丸め、aggregate cap によるスケールダウン（端数処理ロジック含む）を提供。（src/kabusys/portfolio/position_sizing.py）
    - ポートフォリオ API をまとめてエクスポート（src/kabusys/portfolio/__init__.py）
  - ツール
    - Paper Trading 検証レポート生成ツールを追加（python -m kabusys.tools.paper_verification_report）。稼働率、注文成功率、送信率、レイテンシ（P95 含む）などを集計し PASS/FAIL 判定を行う。期間指定オプションと DB パス指定オプションを提供。（src/kabusys/tools/paper_verification_report.py）
  - リサーチ
    - ファクター計算モジュール（ファクター設計・計算方針の枠組み）を追加（momentum 等を想定）。（src/kabusys/research/factor_research.py、実装途中）

Changed
- なし（初期実装のため）

Fixed
- なし（初期実装のため）

Removed
- なし

Security
- なし

Notes / 注意事項
- .env 自動読み込みでは OS 環境変数を上書きしないよう保護措置が入っている。代わりに .env.local は上書き（override）される仕様。
- PAPER_FILL_MODE は有効値（"instant" | "partial" | "never" | "reject"）でない場合に ValueError を送出するため、設定ミスにより起動時例外となる可能性がある。（src/kabusys/config.py）
- run_monitoring は監視用 DB に常に settings.sqlite_path（本番想定のパス）を使用する設計。環境に関係なく本番監視 DB を参照する点に注意。
- run_execution は KABUSYS_ENV=paper_trading の場合に paper_sqlite_path を使い分離している。ペーパートレード DB は data/paper_trading.db がデフォルト。
- logging_setup はログディレクトリの作成に失敗した場合、ファイル出力を無効化して標準出力のみで継続するため、ロギングがディスクに残らない状況がある。

Known issues / TODO
- risk_adjustment.apply_sector_cap: price が欠損（0.0）の場合、エクスポージャーが過少見積りされる可能性がある旨の TODO コメントあり。前日終値や取得原価などのフォールバック価格を導入することが検討されている。（src/kabusys/portfolio/risk_adjustment.py）
- position_sizing: 将来的に銘柄毎の lot_size をサポートする設計への拡張予定。現状は全銘柄共通の lot_size を想定している。（src/kabusys/portfolio/position_sizing.py）
- research/factor_research モジュールは実装途中（ファイル末尾が途中で切れている）ため、完全なファクター計算パイプラインの提供は未完。今後の実装が必要。（src/kabusys/research/factor_research.py）

参考: 主要コマンド/使い方
- 設定ウィザード:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config [--strict]
- モニタリング起動:
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で指定可能
- Execution 起動:
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は paper_trading 用 DB を使用
- Paper Trading 検証レポート:
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]

（以上）