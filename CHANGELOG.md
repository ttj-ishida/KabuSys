CHANGELOG
=========

すべての注目すべき変更点をこのファイルに記録します。フォーマットは "Keep a Changelog" に準拠します。
日付はコードベースのコンテキストに合わせて設定しています。

Unreleased
----------

（なし）

[0.1.0] - 2026-04-18
-------------------

Added
- 基本リリース: 初版公開。
- 実行用スクリプトを追加
  - run_execution.py: ExecutionEngine を起動するエントリポイントを追加。KABUSYS_ENV により paper_trading モード時は専用の MockBrokerClient と paper_trading 用 SQLite(DB) を使用する（本番 DB と分離）。実行中は PID ファイルを書き、外部の停止フラグファイル（data/stop_requested.flag）で安全に停止できる。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能。停止フラグ検出や例外保護、DB 接続の確実なクローズ処理を実装。
- 環境設定・検証ツールを追加
  - config_setup.py: 対話式 .env 作成/更新ウィザード。機密項目のマスク表示、デフォルト値・選択肢の提示、保存確認を実装。
  - validate_config.py: 起動前の設定検証 CLI を追加。必須環境変数の存在チェック、KABUSYS_ENV や LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在と YAML パース（PyYAML があれば内容検証）を行う。--strict モードで警告を失敗扱いにできる。
- 設定管理
  - config.py: .env 自動読み込み機能を実装（プロジェクトルート検出による .env / .env.local の読み込み、OS 環境変数を保護する仕組み、KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化）。.env のパースはクォート/エスケープ/コメント/`export `プレフィックスに対応。Settings クラスで各種設定プロパティを提供（デフォルト値、型変換、妥当性チェックを含む）。
  - Settings に paper_trading 用設定（paper_sqlite_path, paper_fill_mode など）を追加。paper_fill_mode は有効値チェックを行う。
- ロギング・プロセス制御ユーティリティ
  - utils/logging_setup.py: 統一ロギングセットアップ関数 setup_logging を追加。コンソール(stdout) と日次ローテーションファイル（TimedRotatingFileHandler）をルートロガーに設定。既存ハンドラをクリアして重複出力を防止。ログディレクトリ作成に失敗した場合はファイル出力をスキップして継続。
  - utils/process_priority.py: プロセス優先度（high/normal/low）設定と CPU affinity 固定関数を追加。Windows と POSIX 系の違いを吸収し、権限不足や未対応 OS 時は警告を出してフェイルセーフでスキップ。
- ポートフォリオ構築ライブラリ
  - portfolio/portfolio_builder.py: 候補選定（select_candidates）、等配分（calc_equal_weights）、スコア加重（calc_score_weights）を追加。スコアが全て 0 の場合は等配分へフォールバックして警告。
  - portfolio/risk_adjustment.py: セクター集中制限 apply_sector_cap と 市場レジームに応じた乗数 calc_regime_multiplier を追加。未知レジームや unknown セクター時のフォールバック挙動を定義。
  - portfolio/position_sizing.py: position sizing（calc_position_sizes）を実装。allocation_method（"risk_based" / "equal" / "score"）をサポートし、単元株（lot_size）丸め、1銘柄上限・集約キャップ・コストバッファ考慮、スケールダウン後の残差処理まで実装。
- 分析・検証ツール
  - tools/paper_verification_report.py: Paper Trading の検証レポートを生成するスクリプトを追加。稼働率、注文成功率、送信率、P95 レイテンシなどを算出し、閾値に基づく PASS/FAIL 判定を出力。CLI 引数で期間・DB パスを指定可能。
- 研究用モジュール開始
  - research/factor_research.py: ファクター計算モジュールの骨格を追加（momentum / volatility / value / liquidity 計算方針、DuckDB 接続を受け取る設計）。

Changed
- ログ出力先の統一: 各起動スクリプトは共通の setup_logging を利用するようになり、ログ管理が統一化された。
- 実行・監視プロセスの優先度を起動直後に "high" に設定するように変更（set_process_priority の呼び出しを追加）。

Fixed
- .env パーサの堅牢化: クォート・エスケープ・インラインコメント・`export `プレフィックスを正しく扱うように改善。既存 OS 環境変数を保護するため、.env の上書き振る舞いを制御できるようにした。
- validate_config: PyYAML 未インストール時には YAML 検証をスキップして警告を出すようにして、ツール自体が壊れないようにした。
- run_monitoring: MONITOR_POLL_INTERVAL の不正値に対するフォールバック処理を実装（0 以下や非整数はデフォルトに戻す）。monitor.check_once() 内での例外を捕捉してポーリングループ全体の継続を保証。
- logging_setup: 既存ハンドラの flush/close と削除を行い、二重ハンドラ登録による重複ログ出力を防止。
- process_priority / set_cpu_affinity: 権限不足や未サポート環境での失敗時に例外をバブリングさせず警告ログでスキップするようにし、起動の堅牢性を向上。

Removed
- （なし）

Deprecated
- （なし）

Security
- 機密情報（J-Quants トークン、kabu API パスワード等）は config_setup の表示でマスクされ、.env ファイルは Git に絶対にコミットしないよう注意書きを明記。

Notes / Breaking changes
- Settings の妥当性チェック強化により、KABUSYS_ENV や PAPER_FILL_MODE、LOG_LEVEL に不正な値が設定されていると ValueError が発生して起動が失敗します。環境変数の設定は validate_config で事前検証することを推奨します。
- run_monitoring は「監視用 DB として settings.sqlite_path（production 想定）」を常に使用します。paper_trading 用 DB と完全分離したい場合は設定を見直してください。
- process_priority.set_cpu_affinity は cpu_count < 1 の入力を ValueError で弾きます。

作者・参考
- 本リリースはローカル自動売買システム（KabuSys）の初期公開版です。詳細はソース内の docstring / コメントを参照してください。