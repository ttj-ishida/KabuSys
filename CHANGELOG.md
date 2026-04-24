CHANGELOG
=========

このファイルは Keep a Changelog の形式に準拠しています。  
日付はリリース日を示します。

[Unreleased]
------------

- なし

[0.1.0] - 2026-04-24
--------------------

Added
- 基本モジュール群を初期実装
  - 環境設定・読み込み:
    - kabusys.config: .env 自動読み込み（.env, .env.local、OS環境変数保護）、高度な .env パース機能（クォート、エスケープ、コメント処理）を実装。
    - Settings クラスでアプリ全体の環境変数取得を統一（J-Quants / kabuAPI / DB パス / PAPER_FILL_MODE 等）。
  - 設定支援 CLI:
    - kabusys.config_setup: 対話式ウィザードで .env を初期作成・更新するツールを提供（シークレットマスク、選択肢、保存確認）。
    - kabusys.validate_config: .env や config/*.yaml の事前検証ツール（--strict オプションで警告もエラー扱い）。
  - 実行・監視ランチャ:
    - run_execution: ExecutionEngine 起動スクリプト。KABUSYS_ENV=paper_trading 時は paper_trading 専用 SQLite を使用して本番 DB と分離。
    - run_monitoring: SystemMonitor 用ポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を指定可能（デフォルト 60 秒）。停止フラグ（data/stop_requested.flag）を検知して安全に終了。
  - Execution コンポーネント骨格:
    - BrokerClientFactory, ExecutionEngine, OrderManager, OrderRepository, Reconciler, RiskManager（設定値を含む）を組み合わせて起動するフローを実装（起動時に pid ファイルを書き込む等）。
    - RiskConfig によるリスク上限やサーキットブレーカー等の初期設定を導入。initial_portfolio_value を broker.get_available_cash() から初期化。
  - ポートフォリオ構築ライブラリ:
    - kabusys.portfolio: 銘柄選定、重み計算、ポジションサイズ計算、セクター上限、レジーム乗数などの純粋関数を実装。
      - select_candidates, calc_equal_weights, calc_score_weights
      - calc_position_sizes: risk_based / equal / score の配分方式、単元株（lot_size）丸め、aggregate キャップのスケールダウンロジックを実装。
      - apply_sector_cap: セクター集中上限の除外ロジック（"unknown" セクターは制限対象外）を実装。
      - calc_regime_multiplier: market レジームに応じた投下資金乗数（bull/neutral/bear）および未知レジームでのフォールバック。
  - ツール:
    - kabusys.tools.paper_verification_report: Paper Trading 用検証レポート生成スクリプトを追加。稼働率、注文成功率、送信率、レイテンシ（P95）などを集計・判定する機能（閾値定義あり）。
  - 研究用モジュール（骨格）:
    - kabusys.research.factor_research: DuckDB を使ったファクター計算の骨組みを実装（モメンタム / MA / ATR 等の設計方針と定数群を定義）。※実装は継続中。

Changed
- ロギングの統一:
  - kabusys.utils.logging_setup: 全起動スクリプトから呼べる共通ロギング設定を実装。標準出力（stdout）への StreamHandler と、日次ローテーションの TimedRotatingFileHandler（logs/<app_name>.log）を追加。ログディレクトリ作成失敗時はファイルハンドラをスキップして stdout のみで継続するようフォールバック。
  - ログレベル・ログディレクトリ解決の優先度をドキュメント化（引数 > 環境変数 > デフォルト）。
- プロセス優先度/CPU 固定ユーティリティ:
  - kabusys.utils.process_priority: Windows/Linux/macOS の差分を吸収してプロセス優先度（high/normal/low）を設定するユーティリティを実装。CPU affinity 設定関数も追加。権限不足や非対応 OS の場合は警告を出してスキップ。
- DB 周りの挙動:
  - run_monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path（settings.sqlite_path）を使用して monitoring テーブルを初期化する仕様を明確化。
  - run_execution は paper_trading 用に settings.paper_sqlite_path を使用（KABUSYS_ENV=paper_trading の場合）してデータを本番 DB と分離。

Fixed
- .env 読み込みの堅牢性向上:
  - kabusys.config の .env パーサで export プレフィックス、クォート内のエスケープ、インラインコメントの扱い等をサポート。ファイル読み込み失敗時は警告を出して継続。
- validate_config:
  - PyYAML 未インストール時は YAML の内容検証をスキップして警告を出すよう調整（強制的にクラッシュしない）。
- position_sizing の端数処理:
  - lot_size（単元）単位での丸め処理と aggregate cap のスケールダウンで、残余キャッシュを用いて端数分の追加配分を試みるロジックを実装。安全弁として元の目標値や per-stock 上限を超えないようにしている。

Security
- なし

Notes / Migration
- .env ファイルは絶対にリポジトリにコミットしないでください（config_setup のヘッダにも注意喚起があります）。
- 新たに必須の環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD は必須です。kabusys.validate_config で起動前に検証してください。
- Paper Trading を使う場合:
  - KABUSYS_ENV=paper_trading に設定すると run_execution は PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）を使用します。本番 DB と完全に分離するため、ペーパートレード用 DB を別途管理してください。
  - PAPER_FILL_MODE（instant|partial|never|reject）で MockBroker の約定動作を制御できます。無効な値は ValueError を投げます。
- 監視ループ:
  - run_monitoring は MONITOR_POLL_INTERVAL（秒）でポーリング間隔を上書き可能。1 未満や不正な値はデフォルト 60 秒にフォールバックします。
  - 停止フラグファイル（data/stop_requested.flag）を置くことで安全にループを終了できます。
- ログ:
  - LOG_DIR 環境変数でログ出力先を指定できます。ディレクトリ作成に失敗した場合はコンソール出力にフォールバックします。
- 注意:
  - process_priority.set_process_priority はプラットフォーム依存の制約・権限のため失敗する場合があります（警告でスキップ）。本番環境で期待どおりに動作するか事前に確認してください。
  - factor_research は設計方針と一部定数を実装済みですが、完全な実装は継続開発中です。

その他
- パッケージバージョンは kabusys.__version__ = "0.1.0" に設定されています。