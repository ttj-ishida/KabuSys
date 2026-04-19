CHANGELOG
=========

すべての注目すべき変更をこのファイルに記載します。  
（以下は提示されたコードベースの内容から推測して作成した変更履歴です。）

[Unreleased]
------------
- 追加
  - factor_research モジュールの拡張（モメンタム／ボラティリティ等の定数・インターフェースが追加済み、実装継続中）。
  - ポートフォリオ構築・リスク調整関係のユーティリティの拡張（将来的な銘柄ごとの lot_size 対応などの注記を追加）。
- 変更
  - ドキュメント・コメントの補強（PortfolioConstruction.md 等参照の注記追加）。
- 注意事項
  - 一部モジュール（例: factor_research）の実装途中の箇所が存在します。利用時は最新版の実装状況を確認してください。

[0.1.1] - 2026-04-18
-------------------
- 追加
  - MONITOR_POLL_INTERVAL 環境変数による監視ポーリング間隔上書き機能を run_monitoring に追加。無効な値（0以下や整数以外）の場合はデフォルト 60 秒にフォールバックして警告を出力。
  - run_monitoring/run_execution の停止制御にファイルベースの stop_requested.flag（data/stop_requested.flag）を採用し、外部から安全にループを停止できる仕組みを統一。
  - Paper Trading 向け DB 分離: 実行エンジンは KABUSYS_ENV=paper_trading の場合に専用 SQLite（デフォルト data/paper_trading.db）を使用するように明確化。
- 変更
  - run_monitoring: 監視は KABUSYS_ENV に依存せず「本番 sqlite_path」を使用するという仕様を明示（本番監視データは統一 DB で保持）。
  - run_execution: 起動時にプロセス優先度を "high" に設定する処理を先頭で実行するようにした（utils.process_priority）。
  - run_execution: エンジンを別スレッドで実行し、メインスレッドで stop flag を監視して graceful shutdown する挙動を実装。
- 修正
  - DB 初期化: 起動時に monitoring テーブルが存在することを保証するため init_monitoring_db を呼び出す（冪等性を保つ処理）。
  - ロギング設定: setup_logging により stdout ストリームと日次ローテートファイルハンドラを設定。ログディレクトリ作成失敗時はコンソールのみで継続するフォールバックを追加。
  - process_priority: Windows/Linux の差分を吸収する実装に改善。psutil の定数が存在しない環境でも動作するよう getattr フォールバックを導入し、AccessDenied 等の例外をハンドリング。
- ドキュメント
  - Paper Trading 検証レポート（tools/paper_verification_report.py）に閾値、出力フォーマット、コマンドラインオプション（--from/--to/--db）を追加。

[0.1.0] - 2026-04-15
-------------------
- 初回公開（推定）
- 追加（主要機能）
  - 設定管理
    - Settings クラスによる環境変数ラッパーを導入。KABUSYS_ENV, LOG_LEVEL, 各種パス（DUCKDB_PATH/SQLITE_PATH/PAPER_TRADING_SQLITE_PATH）やしきい値（CPU/MEM/DISK）等をプロパティで取得可能。
    - .env 自動ロード機能をプロジェクトルート（.git または pyproject.toml）から実行する実装。.env/.env.local の読み込み順や OS 環境変数保護（protected）をサポート。
    - .env パースの細かい仕様：export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ、コメント処理等を実装。
  - 環境設定・検証 CLI
    - config_setup.py: 対話式ウィザードで .env を生成・更新する機能を追加（シークレット項目のマスク表示、確認プロンプト、ファイル書き込み）。
    - validate_config.py: 起動前に必須環境変数や YAML 設定ファイルの存在・パースをチェックする CLI。--strict オプションで警告も失敗扱いにできる。
  - 実行・監視用エントリスクリプト
    - run_execution.py: ExecutionEngine を起動するエントリ。BrokerClientFactory を利用して本番 / ペーパートレード切替に対応。リスク管理・OrderManager・Reconciler の組立てとスレッド実行、pid ファイル管理、停止フラグ監視を実装。
    - run_monitoring.py: SystemMonitor のポーリングループを実装。MONITOR_POLL_INTERVAL（環境変数で上書き可）、停止フラグ検知、例外ハンドリング、DB 初期化を実装。
  - ポートフォリオ構築ライブラリ（pure functions）
    - portfolio.portfolio_builder: 候補選定（select_candidates）・等分配（calc_equal_weights）・スコア加重（calc_score_weights）。
    - portfolio.position_sizing: allocation_method（risk_based / equal / score）に基づく株数算出、単元株丸め、aggregate cap によるスケールダウン処理、cost_buffer を利用した保守見積り。
    - portfolio.risk_adjustment: セクターキャップ適用（apply_sector_cap）、市場レジームに応じた投下資金 multiplier（calc_regime_multiplier）を実装。
    - これらは DB 参照を伴わない純粋関数として実装され、テスト容易性を考慮。
  - ユーティリティ
    - utils.logging_setup: 一貫したログ設定ユーティリティ（stdout + 日次ローテートファイル）。既存ハンドラをクリアして再設定することで多重出力を回避。
    - utils.process_priority: プロセス優先度と CPU affinity 設定ユーティリティ（Windows / POSIX を吸収）。
  - ツール
    - tools/paper_verification_report.py: Paper Trading 用の検証レポート生成スクリプトを追加。稼働率・注文成功率・送信率・P95 レイテンシ等を集計して PASS/FAIL 判定を出力する。
  - 研究向けモジュール
    - research.factor_research: ファクター計算用の骨格（モメンタム、MA、ATR、出来高等の定数・関数インターフェース）を追加。DuckDB を用いたデータ参照を前提。
- 変更（設計上の注記）
  - Paper Trading と Live を明確に分離する設計（DB、BrokerClient の差分、PAPER_FILL_MODE のバリデーション等）。
  - ロギングは stdout を標準出力に定め、運用時のリダイレクト/ジョブスケジューラ互換性を考慮。
  - .env の自動ロードは必要に応じて KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能（テスト向け）。

既知の制限・今後の予定
--------------------
- factor_research の実装が断片的（ファイル末尾が未完）な箇所があり、実運用には追加実装が必要。
- position_sizing の lot_size は現状グローバル固定（将来的に銘柄別 lot_map への拡張を想定）。
- price 欠損時のフォールバック（前日終値や取得原価など）は TODO コメントが残っており、将来的に改善予定。
- config/.yaml の自動検証は PyYAML の有無に依存する（未インストール時はスキップして警告）。

ライセンス・バージョン
--------------------
- パッケージバージョン (package metadata): 0.1.0（src/kabusys/__init__.py に記載）
- 本 CHANGELOG はコードベースからの推測に基づくため、実際のコミット履歴やリリースノートと差異がある場合があります。必要であれば実際のコミットログ（git）に基づく正確な CHANGELOG の生成をお手伝いします。