# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠します。

## [Unreleased]
（なし）

## [0.1.0] - 2026-04-21

### Added
- 実行・監視用の起動スクリプトを追加
  - run_execution.py: ExecutionEngine を起動するエントリポイント。KABUSYS_ENV=paper_trading 時はモックブローカを使用し、paper_trading 用の SQLite DB を分離して利用する。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能。
- 環境設定関連の CLI を追加
  - config_setup.py: 対話式ウィザードで .env を作成・更新するツールを提供。
  - validate_config.py: .env と config/*.yaml の設定を起動前に検証する CLI（--strict オプションで警告を FAIL 扱いにできる）。
- Paper Trading 検証用ツールを追加
  - tools/paper_verification_report.py: ペーパートレード履歴（SQLite）から稼働率、注文成功率、レイテンシ等を集計して検証レポートを出力するツールを追加。P95 計算や期間フィルタをサポート。
- 設定管理モジュールを追加/実装
  - config.py: .env 自動読み込み（.env, .env.local）、.env パース（クォート・エスケープ・export プレフィックス対応）、必須値チェック、各種設定プロパティ（DB パス、KABUSYS_ENV、PAPER_FILL_MODE 等）を実装。
- ポートフォリオ構築・リスク調整・ポジションサイズ計算モジュールを追加
  - portfolio.portfolio_builder: シグナル選定（スコア順ソート等）、等金額/スコア加重の重み計算。
  - portfolio.risk_adjustment: セクター集中制限の適用（apply_sector_cap）、市場レジームに応じた乗数（calc_regime_multiplier）。
  - portfolio.position_sizing: 投下株数の計算（risk_based / equal / score）、単元株丸め、aggregate cap によるスケールダウン処理。
- 研究用ファクター計算基盤の開始実装
  - research/factor_research.py: DuckDB を使ったモメンタム等のファクター計算を設計。モジュール構成と定数を定義（calc_momentum 等の実装を含む）。
- 汎用ユーティリティを追加
  - utils/logging_setup.py: ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション）を設定するユーティリティを実装。ログディレクトリ自動生成やログレベル解決をサポート。
  - utils/process_priority.py: Windows/Linux（および一部 POSIX）向けにプロセス優先度と CPU affinity を設定するユーティリティを実装（psutil 利用、失敗時は警告でスキップ）。

### Changed
- ログ出力の標準化
  - StreamHandler は stderr ではなく stdout を使用（Task Scheduler / cron などでのリダイレクトを想定）。
  - ログは日次ローテーションで最大 30 日分保持されるように設定。
- DB 周りの挙動
  - run_monitoring は監視用 DB へ接続する際、KABUSYS_ENV に関係なく本番用 sqlite_path を使用する旨を明確化（監視データは本番 DB を参照する設計）。
  - run_execution は paper_trading 環境では paper_sqlite_path を使用して本番 DB と完全分離する。
- 起動時のプロセス優先度設定
  - run_execution/run_monitoring 起動時に最初に set_process_priority("high") を呼びプロセス優先度を上げるようにした（プラットフォームを吸収するラッパを利用）。
- 環境変数の読み込み順序と保護
  - .env と .env.local の自動読み込みを実装（OS 環境変数が優先、.env.local は .env を上書き可能）。既存 OS 環境変数は保護される。
- 設定検証の強化
  - validate_config で必須環境変数や config/*.yaml の存在・パースチェック、本番ガード（KABUSYS_ENV=live 時の注意喚起）を行うようにした。
- ExecutionEngine の既定リスク設定
  - RiskConfig に複数のデフォルトパラメータを設定（max_position_pct, max_utilization, rate_limit_per_sec 等）。初期ポートフォリオ値を broker.get_available_cash() から取得して設定。

### Fixed / Improved
- .env パーシングの堅牢化
  - export プレフィックス、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメント処理（クォート外で # がコメントとなる条件）に対応。
  - 読み込み失敗時は警告で継続するようにした。
- run_monitoring のポーリング間隔の堅牢化
  - MONITOR_POLL_INTERVAL 環境変数を整数として解釈。不正値や 0/負数が指定された場合はデフォルト（60 秒）にフォールバックして警告を出す。
- プロセス優先度 / CPU affinity 設定のフォールトトレランス
  - psutil の AccessDenied 等のエラー発生時は警告を出して処理を継続するように変更。
- position_sizing の投資合計超過時スケーリング
  - aggregate cap 適用時に残余キャッシュを用いてロット単位で再配分するアルゴリズムを実装し、再現性を確保するためのソート順（残差→コード）を導入。

### Notes / Known issues
- position_sizing と apply_sector_cap にて価格欠損時のフォールバック（前日終値等）は未実装で TODO コメントあり。価格が 0 または欠損だと見積りが過少になり得る点に注意。
- calc_regime_multiplier は未知のレジームで 1.0 にフォールバックして警告を出す設計。
- research/factor_research.py の一部関数（calc_momentum 等）の実装が続く箇所で未完となっている可能性あり（本リリースでは基盤設計と定数を含む）。
- paper_verification_report の閾値は現時点ではハードコーディング（稼働率 99% 等）。運用に合わせて調整推奨。

### Metadata
- パッケージバージョン: __version__ = "0.1.0" を設定（src/kabusys/__init__.py）。
- リリース日: 2026-04-21

---

（将来のリリースでは Unreleased セクションに変更を記録し、リリースごとにセクションを追加してください。）