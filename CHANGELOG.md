CHANGELOG
=========

すべての注目すべき変更を記録します。本プロジェクトは Keep a Changelog の形式に準拠しています。

フォーマット:
  - Added: 新規機能
  - Changed: 既存挙動の変更
  - Fixed: バグ修正 / 堅牢化
  - Deprecated / Removed / Security: 該当する場合に記載

[0.1.0] - 2026-04-20
-------------------

Added
- 基本機能の初期実装を追加しました。日本株自動売買システム「KabuSys」のコアモジュール群を含みます。
  - 環境設定:
    - .env ファイルの自動読み込み機能（.env / .env.local、OS 環境変数優先）の実装（kabusys.config）。
    - 対話式環境設定ウィザード（python -m kabusys.config_setup）を追加。.env の生成／更新を支援します。
    - 設定検証 CLI（python -m kabusys.validate_config）を追加。必須環境変数や config/*.yaml の存在・パース検査、--strict モードをサポートします。
  - 実行スクリプト:
    - Execution エンジン起動スクリプト（src/kabusys/run_execution.py）を追加。paper_trading モードでは MockBrokerClient を使い専用 SQLite（data/paper_trading.db）に記録する分離設計を導入。
    - SystemMonitor ポーリングループ起動スクリプト（src/kabusys/run_monitoring.py）を追加。ポーリング間隔は環境変数で上書き可能（MONITOR_POLL_INTERVAL）。
  - ポートフォリオ構築:
    - 銘柄選定と重み計算（select_candidates, calc_equal_weights, calc_score_weights）を実装（kabusys.portfolio.portfolio_builder）。
    - セクター集中制限、レジーム乗数（apply_sector_cap, calc_regime_multiplier）を実装（kabusys.portfolio.risk_adjustment）。
    - 株数算出ロジック（calc_position_sizes）を実装。risk_based / equal / score の割当方式、単元株丸め、aggregate cap（利用可能現金に合わせたスケーリング）、cost_buffer を考慮。
  - 監視・検証ツール:
    - Paper Trading 検証レポート生成スクリプト（python -m kabusys.tools.paper_verification_report）を追加。稼働率・注文成功率・送信率・P95 レイテンシ等を算出し PASS/FAIL 判定を出力。
  - ロギング／プロセス制御ユーティリティ:
    - 統一ログ設定ユーティリティ（kabusys.utils.logging_setup）。コンソール（stdout）出力 + 日次ローテーションファイル出力（TimedRotatingFileHandler）をサポート。LOG_DIR / LOG_LEVEL に対応。
    - プロセス優先度／CPU affinity 設定ユーティリティ（kabusys.utils.process_priority）。Windows / POSIX を抽象化して優先度設定を試行。失敗時は警告を出して安全にスキップ。

Changed
- 実行時の初期化ポリシー:
  - すべての起動スクリプトで起動直後にプロセス優先度を "high" に設定する処理を追加（set_process_priority を呼び出し）。重要処理（監視・発注）の安定化を狙いとしています。
- データベース接続の取り扱い:
  - Monitoring は KABUSYS_ENV に依らず本番用 sqlite_path を使用する（監視データは一貫した場所に保管する設計）。
  - Execution は paper_trading 環境時に専用 SQLite（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）を使用して本番 DB と完全分離。
- ログ出力:
  - StreamHandler は stdout を用いる（stderr ではなく）。cron 等からのリダイレクト運用を考慮。
  - ログディレクトリが作成できない場合はファイル出力をスキップしてコンソール出力のみで安全に継続する実装に変更。
- .env 読み込みの振る舞い:
  - .env のパースを強化（export プレフィックス対応、クォート内のバックスラッシュエスケープ、インラインコメント扱いの改良）。.env.local は .env の上書きとして扱う。

Fixed / Hardened
- 環境変数パーサーの堅牢化（kabusys.config._parse_env_line）:
  - シングル／ダブルクォート内のエスケープ処理、export プレフィックス、インラインコメントの扱いを実装し不正な .env 行をスキップするようにしました。
- ロギング設定の堅牢化:
  - 既存ハンドラを安全に flush/close してから置き換えるようにして、二重ハンドラ登録やリソースリークを防止。
  - ファイルハンドラ作成で例外が発生しても、コンソール出力は維持されるようにハンドリング。
- Process priority / CPU affinity:
  - 権限不足や未サポートプラットフォームでの例外をキャッチして警告ログを出すようにし、起動失敗を回避。
- Execution / Monitoring の停止制御:
  - data/stop_requested.flag（プロジェクトルートの stop flag）を検知して安全にループを終了する仕組みを導入。Execution はエンジンスレッドに対して engine.stop() を呼び出すことで停止を要求。

Notes / Known limitations
- position_sizing.calc_position_sizes:
  - 銘柄ごとの単元数（lot_size）は現状グローバル固定（デフォルト 100）。将来的に銘柄マスタから個別 lot_size を取得する拡張を予定（TODO コメントあり）。
  - open_prices に価格が欠損（0.0）ある場合、エクスポージャーや算出結果が過小評価される可能性がある旨の注記。将来的に前日終値等のフォールバックを検討。
- validate_config:
  - config/*.yaml の内容検証は PyYAML がインストールされている場合のみ実行。未インストール時は警告を出してスキップする挙動。
- research.factor_research:
  - ファクター計算モジュールが含まれているが、実装ファイルは一部が継続途中（切り出しの途中で終端）であり、追加実装が必要。

Developer notes
- 起動スクリプトのログ名はアプリ名（"execution" / "monitoring"）をファイル名に使用します（logs/<app_name>.log）。
- 環境自動ロードを無効化したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト等で利用）。
- validate_config の --strict を使うと警告も失敗扱い（exit 1）になります。

今後の予定
- factor_research の完全実装（ファクター計算ロジックの完成・テスト）
- 銘柄マスタ拡張（個別 lot_size、セクター情報のマスタ化）
- 監視・アラート（LINE）連携の強化（本番環境ガードの追加）
- 単体テスト・統合テストの追加と CI パイプライン整備

---
このリリースは初期の機能セットをまとめたものです。バグや改善提案があれば issue を送ってください。