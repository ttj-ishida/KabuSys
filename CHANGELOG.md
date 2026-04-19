Keep a Changelog
=================

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠しています。

Unreleased
---------

（なし）

0.1.0 - 2026-04-19
-----------------

Added
- コア機能を実装した初期リリース。
  - 環境設定 / 設定読み込み
    - Settings クラス（kabusys.config）を実装。環境変数および .env/.env.local 自動ロードのサポート（優先順位: OS 環境 > .env.local > .env）。
    - .env 読み込みロジックはクォート、エスケープ、コメントなどを考慮したパーサを実装。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロードの無効化が可能。
    - 設定ウィザード CLI（kabusys.config_setup）を追加。対話式で .env を生成・更新可能。
    - 設定検証 CLI（kabusys.validate_config）を追加。必須環境変数、KABUSYS_ENV、ログレベル、DB パス、config/*.yaml の存在／パースチェックを実行。--strict モードで警告を失敗扱いにできる。
  - 起動スクリプト
    - 実行エンジン起動スクリプト（src/kabusys/run_execution.py）を追加。
      - KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite を使用し、MockBrokerClient を使ったペーパートレードと本番 DB の分離をサポート（コメントによる挙動説明）。
      - 停止フラグ（data/stop_requested.flag）を監視して安全に停止する仕組み。
      - execution.pid に PID を保存する仕組み（Engine に渡す）。
    - 監視ループ起動スクリプト（src/kabusys/run_monitoring.py）を追加。
      - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔をオーバーライド可能（デフォルト 60 秒）。
      - 監視は環境に関わらず本番 sqlite_path を使用する（設計上の注意点として明記）。
      - 停止フラグ検知でループ終了、例外発生時はログ出力して次ポーリングへ継続。
  - ログ・プロセス管理ユーティリティ
    - 統一的なログ設定ユーティリティ（kabusys.utils.logging_setup）を実装。stdout への StreamHandler と日次ローテーションの TimedRotatingFileHandler（logs/<app>.log、30日保持）をルートロガーに設定。ログディレクトリ作成失敗時はファイル出力をスキップ。
    - プロセス優先度・CPU affinity 設定ユーティリティ（kabusys.utils.process_priority）を実装。Windows / POSIX の差分を吸収し、AccessDenied 等を安全にハンドリング。
  - DB 統合
    - DuckDB と SQLite を併用する設計をサポート（Settings に DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH を提供）。
    - 監視 DB 初期化ヘルパー（init_monitoring_db）が起動時に呼ばれる（冪等性を確保）。
  - 実行系コンポーネント（骨格）
    - BrokerClientFactory、ExecutionEngine、OrderManager、OrderRepository、Reconciler、RiskManager などの起動/組み立てフローを run_execution で構築するコードを追加（実体は別モジュールに実装想定）。
    - RiskManager に渡すデフォルト設定（max_position_pct 等）を Engine 起動時に組み立て。
  - ポートフォリオ構築（純粋関数群）
    - 銘柄選定: select_candidates（スコア降順・タイブレークルール実装）。
    - 重み計算: calc_equal_weights（等金額）、calc_score_weights（スコア正規化、全スコア 0 の場合はフォールバックして等金額）。
    - セクター上限: apply_sector_cap（既存保有エクスポージャを基にセクター集中を除外、"unknown" セクターは制限適用外）。
    - レジーム乗数: calc_regime_multiplier（"bull"/"neutral"/"bear" に対する乗数とフォールバック挙動）。
    - ポジションサイズ計算: calc_position_sizes（allocation_method: "risk_based" / "equal" / "score" に対応、lot_size 単位で丸め、aggregate cap によりスケールダウンして残余を lot 単位で再配分、cost_buffer を考慮）。
  - 解析・レポートツール
    - Paper Trading 検証レポート生成スクリプト（kabusys.tools.paper_verification_report）を追加。ペーパートレード用 SQLite からシステム稼働率、注文成功率・送信率、リスク却下数、レイテンシ（avg/max/P95）を集計し、PASS/FAIL 判定（しきい値をソース内で定義）を出力。
  - 研究用モジュール（骨格）
    - factor_research モジュールを追加。Momentum 等のファクター計算方針を定義し、DuckDB を用いて prices_daily / raw_financials に依存する計算を行う設計（モジュール末尾でモメンタム計算を開始する実装が含まれているが、ファイルの末尾が切れているため一部未完の状態）。

Changed
- N/A（初期リリースのため過去との比較は無し）。

Fixed
- N/A

Notes / Design decisions
- 監視プロセス（run_monitoring）は意図的に KABUSYS_ENV に関わらず production の sqlite_path を使う旨が明記されているため、監視用 DB とペーパートレード DB は分離して運用される。ただし運用上の混乱を避けるため .env の設定を確認することを推奨。
- .env パーサはクォートやエスケープにかなり対応しているため、複雑な値も安全に扱える。ただし特殊ケースは手動で確認のこと。
- logging_setup はログディレクトリ作成の失敗時にファイルハンドラをスキップするフェールセーフを持つため、コンテナ環境や権限のない環境でも標準出力にはログが出ることを想定している。
- process_priority や cpu_affinity の設定では権限不足や未サポート OS を想定した例外処理があるため、設定が適用されない場合は警告ログにて通知される。

Known issues / TODO
- factor_research.calc_momentum の実装ファイルが途中で切れており（ファイル末尾の途切れ）、完全実装が未完。将来的にファクター群の全実装を追加予定。
- position_sizing の価格欠損（price が 0.0）の扱いに関して TODO コメントあり。前日終値などのフォールバック戦略を検討する必要がある。
- 一部の実行系（BrokerClientFactory や ExecutionEngine の内部実装）は本変更リスト内のスクリプトで参照するのみで、詳細な実装は別ファイルに依存している。実運用前に各依存コンポーネントの実装と統合テストを推奨。

作者
- KabuSys プロジェクトチーム

---