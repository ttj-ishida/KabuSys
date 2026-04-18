# Changelog

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) の慣習に従って記載しています。  
バージョンはパッケージの __version__ に基づきます。

## [0.1.0] - 初回リリース（推定）
リリース日: 未設定

### 追加 (Added)
- 基本アプリケーション構成と起動スクリプトを追加
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV に応じて paper_trading 用の Mock ブローカまたは本番ブローカを選択し、専用 SQLite（paper_trading.db）または本番 SQLite（monitoring.db）を使用する。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能。
- 設定・環境変数管理
  - config.py: Settings クラスを実装。.env 自動ロード（.env < .env.local、OS 環境変数優先）や必須環境変数チェック用の _require()、各種設定プロパティを追加（DB パス、ログレベル、KABUSYS_ENV、paper_trading 関連等）。
  - config_setup.py: 対話式の .env 作成・更新ウィザードを追加。ユーザーに分かりやすいプロンプトとデフォルト値、シークレットマスク表示、保存確認を提供。
  - validate_config.py: 起動前に .env および config/*.yaml の簡易検証を行う CLI を追加。--strict オプションで警告を失敗扱いにできる。
- ポートフォリオ構築関連モジュール（純粋関数群）
  - portfolio.portfolio_builder: 候補選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を追加。
  - portfolio.position_sizing: 発注株数計算ロジック（calc_position_sizes）を追加。allocation_method による分配、単元株丸め、aggregate cap によるスケーリング、cost_buffer を用いた保守的見積りを実装。
  - portfolio.risk_adjustment: セクター上限適用（apply_sector_cap）とレジーム乗数（calc_regime_multiplier）を追加。
  - portfolio パッケージの __all__ を整備。
- 研究・ファクター計算（骨格）
  - research.factor_research: モメンタムや移動平均系の計算を行うための関数（calc_momentum 等）の骨格を追加（DuckDB を利用）。
- ツール
  - tools.paper_verification_report: Paper Trading 用の検証レポート生成スクリプトを追加。稼働率・注文成功率・送信率・レイテンシ（P95）などを算出して PASS/FAIL 判定を出力する。閾値はソース内で定義（例: 稼働率 99% 等）。
- 汎用ユーティリティ
  - utils.logging_setup: 統一的なログ設定ユーティリティを追加。コンソール（stdout）と日次ローテーションファイルハンドラ（TimedRotatingFileHandler）を設定。ログディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソールのみで継続する。
  - utils.process_priority: クロスプラットフォームでのプロセス優先度設定（Windows / POSIX）と CPU affinity を設定する関数（set_process_priority, set_cpu_affinity）を追加。呼び出し側は OS に依存しないインターフェースを利用可能。

### 変更 (Changed)
- DB 周りの運用ポリシー
  - 監視コンポーネント（run_monitoring）は KABUSYS_ENV にかかわらず本番用 sqlite_path を使用するように仕様を明確化（監視用 DB の一貫性確保）。
  - ExecutionEngine は KABUSYS_ENV=paper_trading のとき専用の paper_sqlite_path を使用して、本番 DB と完全に分離する。
- ロギングの改善
  - ログハンドラ設定時に既存ハンドラを flush/close のうえ削除して二重設定を防止。
  - stdout を StreamHandler に使用（stderr ではなく stdout）して、外部システムからのリダイレクト扱いを簡素化。
  - ファイルハンドラ作成失敗時は警告出力してコンソール出力のみで継続するよう堅牢化。
- .env 読み込みルールの明確化
  - 自動ロードの優先順位を明確化（OS 環境変数 > .env.local > .env）。
  - .env パーサーで export プレフィックス、クォート、バックスラッシュエスケープ、インラインコメントなどをより正確に処理するよう改良。
- Execution/Monitoring 起動フロー
  - 起動時にプロセス優先度を最初に High に設定する処理を追加（set_process_priority("high")）。
  - 停止フラグ（data/stop_requested.flag）や kill flag の存在をチェックし、該当する場合は安全に停止または起動を中止する挙動を追加。
  - run_execution は ExecutionEngine を別スレッドで走らせ、停止フラグ検知で engine.stop() を呼んで正常終了を試みる。
- 設定検証の強化
  - validate_config で必須環境変数チェック、KABUSYS_ENV 値チェック、LOG_LEVEL の妥当性確認、DB パス親ディレクトリ存在チェック、config/*.yaml の存在・パース（PyYAML があれば）チェック、本番時のガード条件（LINE 設定、KILL_FLAG_CLEAR_ON_START の警告）を行う。

### 修正 (Fixed)
- 不正な MONITOR_POLL_INTERVAL の扱いを安全化
  - run_monitoring の _get_poll_interval() が環境変数の不正な値（整数化失敗や 0 以下）を検出した場合に警告を出しデフォルト（60 秒）にフォールバックするようにした。
- スコア重み付けのフォールバック
  - calc_score_weights() で全スコアが 0 の場合、等金額配分にフォールバックして警告ログを出すようにして、ゼロ除算や不正な分配を回避。
- レジーム乗数の既定値フォールバック
  - calc_regime_multiplier() で未知のレジームラベルが与えられた場合に警告を出し 1.0 を返すようにして、致命的エラーを防止。
- process_priority / CPU affinity の失敗耐性
  - psutil のアクセス権限不足や未対応プラットフォームで例外が発生した場合に警告を出して処理をスキップするようにした。
- Paper verification レポートの堅牢化
  - DB のテーブルが存在しない（OperationalError）場合に個別にデフォルト値を用いる安全策を追加（テーブル欠如による未処理例外防止）。
- .env 書き込みテンプレートでの注意喚起を追加
  - config_setup で生成される .env 頭部に「.env を絶対に Git にコミットしないこと」を明記。

### ドキュメント (Documentation)
- docstrings とモジュールレベルコメントを充実化
  - 各モジュール（起動スクリプト、ユーティリティ、ポートフォリオ各モジュール、ツール）に用途や使用方法、設計上の意図・注意点を記載。
  - config_setup や validate_config の CLI 使用方法を README 的に追記（モジュール内のトップコメントとして）。

### 削除 (Removed)
- なし（このリリースでは重大な削除は行われていないと推測）。

### セキュリティ (Security)
- .env 取り扱いに関する注意を明示（config_setup の生成ファイルヘッダーに「.env を絶対に Git にコミットしないこと」等を記載）。  
- その他セキュリティ修正は明示されていない。

---

注記:
- 上記は提供されたコードベース（現状のソース）から推測して作成した CHANGELOG です。実際のコミット履歴やリリースノートがある場合は、それに合わせて調整してください。