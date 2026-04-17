# CHANGELOG

すべての変更は Keep a Changelog の形式に従って記載しています。  
バージョン番号は src/kabusys/__init__.py の __version__ に基づきます。

## [Unreleased]

（なし）

## [0.1.0] - 2026-04-17

### Added
- 基本アプリケーション構成を追加。
  - パッケージ情報: src/kabusys/__init__.py に __version__ = "0.1.0" を追加。
- 環境設定管理（.env 自動読み込み・パース機能）。
  - src/kabusys/config.py
    - プロジェクトルート検出ロジックを実装（.git または pyproject.toml を基準）。
    - .env および .env.local の自動読み込み（OS 環境変数優先、上書き制御あり）。
    - export KEY=val、クォート内のエスケープ、インラインコメントなどを考慮した詳細な .env パーサを実装。
    - 必須環境変数取得ヘルパー _require と Settings クラスを実装。多数の設定プロパティを提供（DB パス、API トークン、Paper Trading 用設定、監視閾値など）。
    - 環境種別バリデーション（development / paper_trading / live）とログレベル検証を実装。
- 環境設定ウィザード CLI を追加。
  - src/kabusys/config_setup.py
    - 対話式で .env を作成・更新するウィザードを実装。シークレット項目はマスク表示。
    - .env の読み書きロジック、既存値の再利用、保存確認プロンプトを提供。
- 設定検証 CLI を追加。
  - src/kabusys/validate_config.py
    - 必須環境変数やパス、config/*.yaml の存在・パースチェック、KABUSYS_ENV による本番用ガードなどを実装。
    - --strict オプションで警告を FAIL 扱いにできる。
    - PyYAML 未インストール時は YAML 検証をスキップして警告を出す。
- 実行エントリスクリプトを追加。
  - src/kabusys/run_execution.py
    - ExecutionEngine 起動スクリプト（プロセス優先度設定、DB 接続、ブローカーファクトリ利用、各コンポーネント組み立て、別スレッドで実行）。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 専用 SQLite（PAPER_TRADING_SQLITE_PATH）を使用して本番 DB と分離。
    - 停止フラグ（data/stop_requested.flag）検知で安全に停止。
    - PID ファイル管理（data/execution.pid）連携。
    - RiskManager のデフォルト設定（max_position_pct など）を設定して起動時に利用可能現金を初期化。
- 監視（Monitoring）起動スクリプトを追加。
  - src/kabusys/run_monitoring.py
    - SystemMonitor ポーリングループを実装。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番 sqlite_path を使用する仕様。
    - 停止フラグ検知でループ終了、例外はロギングして次ポーリングへ継続。
- Paper Trading 検証レポートツールを追加。
  - src/kabusys/tools/paper_verification_report.py
    - ペーパートレード用 SQLite を集計してシステム稼働率・注文成功率・送信率・レイテンシ（P95）などを算出、PASS/FAIL 判定を出力する CLI。
    - P95 計算、閾値（稼働率 99% 等）定義、日付フィルタ機能を実装。
- ポートフォリオ構築・資金配分モジュールを追加。
  - src/kabusys/portfolio/portfolio_builder.py
    - シグナルの候補選定（スコア順、タイブレークに signal_rank 使用）、等金額配分、スコア加重配分を実装。
  - src/kabusys/portfolio/risk_adjustment.py
    - セクター集中上限チェック（apply_sector_cap）、市場レジームに応じた乗数（calc_regime_multiplier）を実装。
  - src/kabusys/portfolio/position_sizing.py
    - リスクベース／等金額／スコア加重の発注株数算出、単元株（lot_size）丸め、aggregate cap によるスケーリング、cost_buffer による保守的見積りを実装。
  - src/kabusys/portfolio/__init__.py で各関数をエクスポート。
- 研究用ファクター計算モジュールを追加（DuckDB ベース）。
  - src/kabusys/research/factor_research.py
    - Momentum（1M/3M/6M、MA200乖離）および Volatility（ATR、出来高関連）ファクター計算関数を実装。DuckDB 接続を受け取り SQL + Python で計算する設計。
- プロセス優先度・CPU affinity ユーティリティを追加。
  - src/kabusys/utils/process_priority.py
    - Windows/Linux/その他を吸収してプロセス優先度（high/normal/low）を設定する set_process_priority を実装。
    - CPU affinity を設定する set_cpu_affinity を実装（コア数指定で最初のNコアに固定）。
    - 権限不足や未対応 OS の場合は警告を出して安全にスキップ。
- その他ユーティリティ・パッケージ構成ファイルを追加。
  - src/kabusys/tools/__init__.py などのパッケージ初期化。

### Changed
- なし（初回リリース）

### Fixed
- なし（初回リリース）

### Security
- 環境ファイルの取り扱いに関する注意書き（config_setup.py の .env ファイルに関する警告）を追加。シークレットは表示時にマスク。

### Notes / Migration
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD が必要。未設定時は起動前に validate を実行して検出可能。
- .env 自動読み込み:
  - OS 環境変数が優先されます。プロジェクトルートが検出できない場合は自動読み込みをスキップします。
  - テストなどで自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- Paper Trading:
  - paper_trading 環境では PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）を使用し、本番監視 DB（SQLITE_PATH）とは分離されます。
- 実行前チェック:
  - python -m kabusys.validate_config で設定検証を推奨します。
  - .env 作成には python -m kabusys.config_setup を利用できます。
- データディレクトリ:
  - デフォルトの DB/flag/PID パス（data/*.db, data/*.flag, data/*.pid）が期待されます。親ディレクトリが存在しない場合は起動時に警告が出ます。

---

今後の予定（例）
- 更なるテスト追加・CI 統合
- strategy / execution 内部コンポーネントの実装詳細（現状は起動フローとインターフェースを整備）
- ファクター・ポートフォリオロジックの最適化およびバックテストツールの追加

問い合わせや補足説明が必要であればお知らせください。