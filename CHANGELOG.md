CHANGELOG
=========

この CHANGELOG は Keep a Changelog の形式に準拠しています。  
コードベースから推測できる機能追加・改善・バグ修正等を日本語でまとめています。

フォーマット:
- Unreleased: 今後の変更（現時点では空または短期予定）
- 各リリースは日付付きで記載（リリース日はコード確認日を使用）

Unreleased
----------
- 今後の改善候補・既知の作業:
  - research/factor_research.py の未完了箇所の実装（ファイルが途中で終端しているため、ファクター計算ロジックの完成）
  - ExecutionEngine / 各実行コンポーネント周りの補完ドキュメントと追加テスト
  - 単元株（lot_size）を銘柄毎に扱う拡張（コメントに将来の TODO が存在）
  - 追加のエラーロギング・監視指標の強化

[0.1.0] - 2026-04-25
--------------------
初回公開（推定）。以下の主要機能・改修点が導入されています。

Added
- 基本 CLI / 実行エントリ
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。停止フラグ（data/stop_requested.flag）検知で優雅に終了。
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV=paper_trading 時は paper_trading 専用の SQLite を使用（本番 DB と分離）。実行はデーモンスレッドで行い停止フラグで制御。
  - validate_config.py: .env と config/*.yaml の事前検証用 CLI を追加。必須環境変数チェック、パスの存在確認、YAML の簡易パース検証、live 環境向けガード等を実装。--strict オプションあり。
  - config_setup.py: 対話式ウィザードで .env を初期作成/更新する CLI を追加。秘密情報はマスク表示。生成ファイルに注意喚起コメントを付与。

- 設定管理
  - config.py: 自動 .env ロード（.env, .env.local、OS 環境変数優先）、堅牢な .env パーサ（引用符・エスケープ・コメントの扱いを考慮）。Settings クラスによるアクセスラッパーを提供（各種環境変数の検証・デフォルト解決含む）。

- ロギング・プロセス管理ユーティリティ
  - utils/logging_setup.py: 統一的なログ設定ユーティリティを追加。コンソール（stdout）出力と日次ローテーションするファイルハンドラをルートロガーに設定。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
  - utils/process_priority.py: クロスプラットフォームのプロセス優先度設定（Windows / POSIX）と CPU affinity 設定ユーティリティを追加。権限不足や未対応 OS で安全にフォールバック。

- Portfolio 構築機能（純粋関数）
  - portfolio/portfolio_builder.py: シグナル選定（スコア降順、タイブレーク）、等金額配分、スコア加重配分（全スコア 0 の場合は等分にフォールバック）を実装。
  - portfolio/risk_adjustment.py: セクター集中制限（apply_sector_cap）と市場レジームに基づく投下資金乗数（calc_regime_multiplier）を実装。未知レジーム時はフォールバック動作とログ警告。
  - portfolio/position_sizing.py: 株数計算ロジックを実装。risk_based / equal / score 配分方式に対応。単元株（lot_size）丸め、1 銘柄上限、aggregate cap によるスケーリング（余剰配分ロジック含む）、cost_buffer を用いた保守的見積りを含む。

- 分析・検証ツール
  - tools/paper_verification_report.py: Paper Trading の検証レポート生成ツールを追加。稼働率、注文成功率（Fill Rate）、送信率、P95 レイテンシ等を SQLite のトレードログ/監視テーブルから集計して PASS/FAIL 判定を行う。日付範囲指定 (--from/--to) と DB パス指定オプションあり。

- データベース連携
  - DuckDB と SQLite の両方を使用する設計。monitoring 用 DB 初期化の idempotent な init_monitoring_db 呼び出し位置を確保。
  - Monitoring は KABUSYS_ENV に関わらず本番 sqlite_path を使用する旨の設計上の注意。

Changed / Behavior
- 起動時のプロセス優先度を "high" に設定する処理を標準化（run_monitoring.py / run_execution.py）。最初に呼び出すことでリソース割当の安定化を図る。
- run_execution.py:
  - KABUSYS_ENV=paper_trading の場合に MockBroker を使用して paper_trading 用 DB（data/paper_trading.db）へ完全分離する設計。
  - エンジンの開始前に停止フラグを確認し、既に停止フラグがあれば起動しない安全措置を導入。
- 設定自動読み込み:
  - .env 自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD を使って無効化可能。
  - .env.local は .env の設定を上書き可能（ただし OS 環境変数は保護）。

Fixed / Robustness
- .env パーサの堅牢化: export プレフィックス対応、シングル/ダブルクォート内でのバックスラッシュエスケープ処理、コメントの認識ルール強化。
- ロギング設定: 既存ハンドラを安全に flush/close してから再設定することで二重ハンドラ設定を防止。ログディレクトリ作成失敗時のフォールバックロジックを追加。
- process_priority の例外処理: 権限不足や未実装メソッドに対する警告ログで処理を継続（クラッシュ防止）。
- run_monitoring のポーリングループ: monitor.check_once() 実行中に例外が発生してもループは継続し、例外をログに記録して次回へ移行するように堅牢化。
- validate_config: PyYAML が未インストールの場合は YAML チェックをスキップし、警告を出して継続する。

Security
- .env の自動生成時に「.env は絶対に Git にコミットしないこと」という注記を出力（config_setup.py）。
- 機密環境変数はウィザードでマスク表示（config_setup.py）して露出を抑止。

Documentation / Developer Experience
- config_setup.py により新規ユーザーが対話的に .env を作成可能。保存前に設定確認・キャンセル可。
- validate_config.py による起動前の設定検証で運用ミスを未然に検出。
- ロギングの統一により各スクリプトで同様のログ出力構成を利用可能。

Known issues / Notes
- research/factor_research.py が途中で終端（未完）。Momentum 等のファクター計算実装の続きが必要。
- position_sizing.py の TODO: 将来的に銘柄別 lot_size の対応を検討中。
- 一部コンポーネント（ExecutionEngine、BrokerClient 等）は本変更履歴で参照されるが実装詳細はこの差分に含まれない（別モジュールに依存）。

ライセンス・バージョン
- パッケージバージョン: __version__ = "0.1.0"

貢献
- この CHANGELOG はコードから推測して作成しています。実際のリリースノートと差異がある場合は修正してください。