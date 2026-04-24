# CHANGELOG

すべての注目すべき変更を記録します。  
フォーマットは "Keep a Changelog" に準拠し、セマンティックバージョニングを想定しています。

※ 以下は提供されたコードベースの内容から推測して作成した変更履歴です。

## [0.1.0] - 2026-04-24
初回リリース（推定）

### Added
- 基本アプリケーション設定
  - Settings クラスを追加し、環境変数および .env/.env.local からの設定読み込みを提供。
  - .env 自動ロード機構を実装（プロジェクトルート検出、OS 環境変数保護、`.env.local` による上書き）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロードを無効化可能。
  - 設定検証のための validate_config CLI を追加（必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL 検証、DB パス確認、config/*.yaml の存在・パースチェック、--strict オプション）。

- 環境設定ウィザード
  - config_setup に対話式ウィザードを実装。.env の初期作成・更新を支援する（シークレットマスク表示、選択肢サポート、保存確認）。

- 実行系スクリプト
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite を使用し MockBrokerClient を利用することで本番 DB と分離する設計。
    - プロセス優先度設定（high）および PID ファイル管理、停止フラグ（data/stop_requested.flag）による安全停止。
    - 依存コンポーネント（BrokerClientFactory, OrderRepository, OrderManager, RiskManager, Reconciler, ExecutionEngine）を組み立ててスレッド実行。
    - RiskManager のデフォルト構成（max_position_pct, max_utilization, rate_limit_per_sec 等）を定義。

- 監視系スクリプト
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値時はデフォルトにフォールバックし警告を出す。
    - 監視は環境に依らず本番 sqlite_path を使用する設計（監視データの一元化）。
    - stop フラグ検知、例外ハンドリング、DB / duckdb 接続の確立とクリーンアップ。

- ユーティリティ
  - logging_setup: 統一ログ設定ユーティリティを追加
    - stdout への StreamHandler と日次ローテートの TimedRotatingFileHandler（デフォルト logs/、30日保持）をルートロガーに設定。
    - ログディレクトリ作成失敗時はファイル出力をスキップしコンソールに警告を出力。
    - ログレベル解決（引数→環境変数→デフォルト）。
  - process_priority: Windows / POSIX の差分を吸収するプロセス優先度設定ユーティリティを追加
    - nice / Windows 優先度クラスを使用して "high"/"normal"/"low" を設定。失敗時は警告を出してスキップ。
    - set_cpu_affinity によりプロセスの CPU affinity を設定する補助関数を提供。

- ポートフォリオ構築モジュール
  - portfolio_builder: シグナル選定（select_candidates）と重み計算（等分配 calc_equal_weights、スコア加重 calc_score_weights）を実装。
  - risk_adjustment: セクター集中制限 apply_sector_cap、レジーム乗数 calc_regime_multiplier を実装（未知レジームはフォールバック、Bear/Neutral/Bull の乗数定義）。
  - position_sizing: position size 計算（risk_based / equal / score）、単元株（lot_size）丸め、max position / aggregate cap (available_cash) のスケーリング、cost_buffer を考慮した保守的見積りを実装。

- 研究・分析補助
  - research.factor_research モジュール（ファクター計算基盤）を追加（Momentum 等の指標算出を目的に DuckDB 接続を受け取る設計）。※ ファイル末尾で未完の関数定義あり（calculate momentum の途中で切れている）。

- ツール
  - tools.paper_verification_report: Paper Trading の検証レポート生成ツールを追加
    - 指標: 稼働率 (uptime_pct)、注文成功率 (fill_rate)、送信率 (send_rate)、レイテンシ（avg/max/P95）、リスク却下数。
    - デフォルト閾値を定義して PASS/FAIL 判定を行う（稼働率 99.0%、fill_rate 90%、send_rate 95%、P95 latency 200 ms）。
    - --from/--to/--db オプションをサポート。DB が存在しない場合はエラーメッセージを表示。

### Changed
- ログとプロセスの初期化順序を統一
  - 起動スクリプト（monitoring / execution）で最初にログ設定・プロセス優先度設定を行い、以降の処理で統一された環境を確保。

- DB 接続ポリシー
  - 監視系は環境に関係なく本番 sqlite_path を参照する（監視データを本番 DB に集約）。
  - 実行系は paper_trading 環境時に専用の paper_sqlite_path を使用して本番 DB と分離。

### Fixed
- .env パーサーの堅牢化
  - クォート付き値のバックスラッシュエスケープ処理、コメントの扱い、export プレフィックス対応などを実装し、より実用的な .env パースを実現。
- ログハンドラ重複防止
  - setup_logging は既存ハンドラを flush/close してから削除・再設定するようにして二重登録を防止。

### Notes / Implementation details
- Settings クラスで環境値検証を行う（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE の入力検証）。
- run_execution.py は Engine をバックグラウンドスレッドで実行し、停止フラグ検知で安全に停止させる設計。
- position_sizing の aggregate スケールダウンは小数残差を考慮し、lot_size 単位で再配分するロジックを実装。
- process_priority / set_cpu_affinity は権限不足などの例外をキャッチして警告を出力し、実行継続できるようにしている。
- research.factor_research は DuckDB 経由で prices_daily / raw_financials を参照する前提で実装されている（外部 API に依存しない）。

### Known issues / TODO（コードから推測）
- research.factor_research の calc_momentum 関数が途中で切れており未完（実装継続が必要）。
- apply_sector_cap 内で price_map の欠損（0.0）を考慮したフォールバックが未実装（TODO コメントあり）。
- 将来的に銘柄単位で lot_size を持たせる設計への拡張がコメントとして残っている。
- config/*.yaml の構造バリデーションは PyYAML がインストールされている場合にのみ行われる（スキップ可能）。

---

今後のリリースでは、未完のファクター計算の完了、より詳細な単体テスト、運用時の監視・アラート連携（LINE通知など）の拡張、本番向けの安全ガード強化を検討してください。