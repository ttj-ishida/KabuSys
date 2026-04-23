CHANGELOG
=========

この変更履歴は "Keep a Changelog" の形式に準拠しています。  
主にソースコードから推測できる追加点・改良点・修正点を日本語で記載しています。

Unreleased
----------

Added
- run_monitoring 起動スクリプトを追加 / 改良
  - 環境変数 MONITOR_POLL_INTERVAL によりポーリング間隔を上書き可能（デフォルト 60 秒）。
  - 停止フラグファイル data/stop_requested.flag を検知して安全に監視ループを終了。
  - Monitoring は実行環境にかかわらず本番用 sqlite_path を使用して DB 初期化を行う。
  - duckdb も併用して接続を確立、終了時にコネクションを確実にクローズ。

- run_execution 起動スクリプトを追加 / 改良
  - KABUSYS_ENV=paper_trading の場合は paper_trading 専用の SQLite（デフォルト data/paper_trading.db）を使用し本番 DB と分離。
  - 起動時に process priority を "high" に設定。
  - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine を起動。
  - 停止フラグ（data/stop_requested.flag）検知でセッションを安全に停止。PID ファイル管理に対応。

- 設定管理（kabusys.config）
  - .env の自動読み込みを追加（プロジェクトルートを .git または pyproject.toml から探索）。
  - .env/.env.local の読み込み順序と既存 OS 環境変数保護を実装。
  - 複雑な .env 行のパースを実装（export プレフィックス対応、クォートおよびエスケープ、インラインコメントルール）。
  - Settings クラスを通じて各種設定値を遅延評価で取得（DB パス、paper_trading 切替、しきい値など）。
  - PAPER_FILL_MODE の検証や KABUSYS_ENV/LOG_LEVEL のバリデーションを実装。

- 設定ウィザード（kabusys.config_setup）
  - 対話式で .env の初期作成・更新を行うウィザードを実装。
  - よく使うキーの説明表示、シークレット入力のマスク、既存値の再利用をサポート。
  - .env のテンプレート書き出し機能を提供。

- 設定検証 CLI（kabusys.validate_config）
  - 必須環境変数や KABUSYS_ENV、LOG_LEVEL、DB パス、config/*.yaml の存在と YAML パースをチェックする検証ツールを実装。
  - --strict オプションで警告も失敗扱いにできる。
  - 本番環境（live）向けの追加ガード（LINE 通知設定の有無、KILL_FLAG_CLEAR_ON_START の危険性）を検出。

- ロギングユーティリティ（kabusys.utils.logging_setup）
  - ルートロガーに StreamHandler（標準出力）と TimedRotatingFileHandler（日次ローテーション）を統一的に設定するユーティリティを実装。
  - ログディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソール出力のみで継続。
  - 標準エラーではなく標準出力へログを出力する設計。

- プロセス優先度ユーティリティ（kabusys.utils.process_priority）
  - Windows/Linux/Mac の差分を吸収してプロセス優先度（nice / Windows priority class）を設定するヘルパーを実装。
  - CPU affinity を最初の N コアへ固定する機能を実装。
  - 権限不足や未対応プラットフォーム時に警告を出して安全にスキップ。

- ポートフォリオ構築モジュール（kabusys.portfolio）
  - 銘柄選定（select_candidates）、等金額配分 / スコア加重（calc_equal_weights / calc_score_weights）を実装。
  - セクター集中制限（apply_sector_cap）、レジームに応じた投下資金乗数（calc_regime_multiplier）を実装。
  - ポジションサイズ算出（calc_position_sizes）を実装。リスクベース／equal／score の割当方式をサポートし、単元株（lot_size）で丸め、アグリゲートキャップ超過時のスケーリング/端数配分ロジックを実装。

- Paper Trading 検証レポート（kabusys.tools.paper_verification_report）
  - ペーパートレード用 SQLite からシステム稼働率、注文成功率、送信率、レイテンシ（P95 など）、リスク却下数を集計して人間可読なレポートを出力する CLI を実装。
  - 既定の閾値（稼働率 99%、成立率 90% など）による PASS/FAIL 判定を実装。
  - --from / --to / --db オプションで期間・DB を指定可能。

Changed
- logging_setup: ログレベル決定順やログディレクトリ解決の挙動を明確化。既存ハンドラを安全に flush/close してから再設定するように変更。
- .env 自動読み込みの振る舞いを明確化（KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化）。
- run_monitoring/run_execution: 起動シーケンスで最初にプロセス優先度を設定するように統一。
- process_priority: 未対応 OS の取り扱いと例外時の警告を強化。

Fixed
- .env パーサー: export プレフィックス、クォート内のバックスラッシュエスケープ、インラインコメントの扱いなどの細かいケースを正しく処理するよう改善（以前は誤認・トリムされるケースがあったと推測）。
- logging_setup: ログディレクトリ作成失敗時にファイルハンドラ生成で例外が発生しアプリが落ちる問題を回避（フォールバック実装）。
- process_priority: 権限不足や未サポート機能呼び出し時に例外で死なないよう try/except により安全にスキップするよう改善。

Deprecated
- なし（現時点のコードからは非推奨 API の宣言は確認できません）。

Removed
- なし（現時点のコードからは削除された機能は確認できません）。

Security
- 環境変数の取り扱いでシークレットは対話ウィザード上で表示をマスクするなどの配慮を追加。外部への送信等はコードからは見受けられません。

Notes / Known issues / TODO
- factor_research モジュールの実装が途中（ファイル末尾が途切れている/続きあり）と思われるため、モメンタム等の計算ロジックは今後の追加実装・テストが必要。
- position_sizing の max_per_stock 計算で価格が 0 の場合に 0 を返す仕様があるため、価格欠損時のエクスポージャー過少評価に関する TODO コメントあり（前日終値や取得原価でのフォールバック検討）。
- apply_sector_cap は "unknown" セクターを上限検査から除外する仕様。データ品質次第で意図しない集中が発生する可能性があるため、監査ログ／警告を検討中。
- run_monitoring/run_execution は stop/kill フラグファイルを使った外部制御を行う設計だが、クラスタやコンテナ環境での運用時は別途プロセス管理（systemd / k8s 等）との整合性を確認すること。

[0.1.0] - 2026-04-23
--------------------
Added
- 初期リリース。上記の各 CLI（run_execution, run_monitoring, config_setup, validate_config, tools.paper_verification_report）およびユーティリティ（logging_setup, process_priority）とポートフォリオ・計算モジュール（portfolio/*）を含む基本機能を実装。
- Settings クラスによる環境変数ラッパ、.env 自動読み込みと安全な保護機構を実装。
- Paper trading と本番 DB の分離、監視用 DB 初期化ロジックを実装。

Fixed
- 初期リリースにて既知の例外・フォールトシナリオに対する堅牢性（ファイルハンドラ作成失敗、psutil の例外、DB 接続の安全なクローズ等）を強化。

---

注: 上記 CHANGELOG はリポジトリ内のソースコードから挙動・目的を推測して作成しています。実際のコミット履歴やリリース計画に応じて日付・バージョン・分類を調整してください。