Keep a Changelog
=================

すべての重要な変更点をこのファイルで管理します。
フォーマットは「Keep a Changelog」に準拠します。  
http://keepachangelog.com/ja/1.0.0/

Unreleased
----------

（現在なし）

[0.1.0] - 2026-04-21
-------------------

Added
- 初期リリース: KabuSys の基本的な自動売買・検証ユーティリティ群を追加。
  - 実行エントリスクリプト
    - run_execution.py: ExecutionEngine 起動スクリプトを追加。スレッドでエンジンを起動・監視し、data/execution.pid に PID を書き出す。data/stop_requested.flag により停止可能。
    - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。停止フラグ検出、例外ハンドリング、MONITOR_POLL_INTERVAL 環境変数によるポーリング間隔上書きをサポート。
  - 設定・環境管理
    - config.py: .env 自動ロード機能（.env / .env.local、OS 環境変数保護、KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能）、堅牢な .env パーサ（export プレフィックス、クォート・エスケープ、インラインコメント対応）、Settings クラスを追加。
    - config_setup.py: 対話式ウィザードにより .env の初期作成・更新を支援する CLI を追加。
    - validate_config.py: .env や config/*.yaml の起動前検証 CLI を追加。--strict モードをサポート。
  - ポートフォリオ構築関連（純粋関数群）
    - portfolio.portfolio_builder: 候補選定（select_candidates）、等金額/スコア加重の重み計算（calc_equal_weights / calc_score_weights）。
    - portfolio.risk_adjustment: セクター集中制限の適用（apply_sector_cap）、市場レジームに応じた投下資金乗数（calc_regime_multiplier）。
    - portfolio.position_sizing: 各銘柄の株数算出ロジック（risk_based / equal/score、単元丸め、aggregate cap スケーリング、cost_buffer 対応）。
  - ユーティリティ
    - utils.logging_setup: 統一ログ設定ユーティリティを追加。StreamHandler（stdout）と TimedRotatingFileHandler（日次・30日保持）を設定。ログディレクトリ作成失敗時はコンソールのみで動作継続。
    - utils.process_priority: プロセス優先度と CPU affinity を OS 間差分を吸収して設定するユーティリティを追加（Windows/Linux/macOS 対応、権限不足時は警告でスキップ）。
  - 実行・監視のための DB 接続
    - DuckDB/SQLite を使用する設計を導入（Settings でパス指定）。monitoring は環境にかかわらず本番 sqlite_path を使用する挙動を採用。paper_trading 環境時は paper 用 SQLite を分離して使用（PAPER_TRADING_SQLITE_PATH）。
  - ブローカー抽象化
    - execution パッケージに BrokerClientFactory（設定に応じて MockBrokerClient を選択）を導入し、paper_trading と本番を分離。
  - ツール
    - tools.paper_verification_report: Paper Trading の検証レポート生成スクリプトを追加。稼働率、注文成功率、送信率、レイテンシ（平均・最大・P95）などを集計して PASS/FAIL 判定を出力。
  - 研究用モジュール（骨格）
    - research.factor_research: ファクター計算モジュールの骨格（モメンタム・ボラティリティ等を想定）。calc_momentum 等の実装開始（DuckDB を用いた prices_daily 参照設計）。

Changed
- ログ出力
  - すべての起動スクリプトから utils.logging_setup.setup_logging を使うことでログ動作を統一。ログレベルの決定順（引数 > 環境変数 LOG_LEVEL > デフォルト）とログディレクトリ解決順（引数 > LOG_DIR env > デフォルト）を規定。
- .env 読み込み順序
  - OS 環境変数 > .env.local > .env の優先順で自動ロード（プロジェクトルートが特定できない場合は自動ロードをスキップ）。
- 実行時優先度
  - 起動時に set_process_priority("high") を呼び出して、監視・実行プロセスの優先度を上げるようにした（プラットフォーム差分を吸収しつつ、権限問題は警告でスキップ）。
- ExecutionEngine 起動
  - ペーパートレード時は MockBrokerClient を使用し、paper_trading 用 DB（data/paper_trading.db）へ記録することで本番 DB と完全分離する挙動を明確化。

Fixed
- レジリエンス向上
  - run_monitoring のポーリングループで check_once() が例外を投げてもループを継続するように例外捕捉を追加（ログに exception を出力）。
  - run_execution/run_monitoring ともに finally ブロックで DB 接続を確実に close するように実装。
- .env パースに関する細かい誤動作対策
  - シングル/ダブルクォート内のバックスラッシュエスケープ処理、export プレフィックスのサポート、インラインコメント処理の改善。
- 設定検証の安全性
  - validate_config は PyYAML 未導入時に YAML 検証をスキップして警告を出す挙動を導入（サブコマンドからの環境チェックでハードクラッシュしないように）。

Notes / Known limitations
- research.factor_research モジュールは（ソース切り出しの都合上）calc_momentum の実装が途中で切れているように見えるため、完全実装は今後のタスクです。
- position_sizing の単元株（lot_size）は現在グローバル共通設定。将来的に銘柄別単元対応（stocks マスタの導入）が想定されている旨の TODO コメントあり。
- 一部の高度な機能（CPU affinity、プロセス優先度変更）は権限やプラットフォームに依存し、失敗時はログ警告でフォールバックします。

Authors
- KabuSys 開発チーム（コードベースから推測して記載）

License
- 各ファイルに明示的なライセンス表記はありません。配布前にライセンス追加を検討してください。