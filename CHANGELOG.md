# CHANGELOG

すべての注目すべき変更点を記録します。フォーマットは「Keep a Changelog」に準拠しています。

## [0.1.0] - 2026-04-24

### 追加
- プロジェクトの初期リリースを追加。
- 基本的なランタイムスクリプト・CLI
  - run_monitoring.py
    - SystemMonitor ポーリングループ起動スクリプトを追加。
    - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能（デフォルト 60 秒）。不正な値はデフォルトにフォールバックし警告を出力。
    - 停止制御: リポジトリルート/data/stop_requested.flag の存在検知でループを終了。
    - Monitoring は環境（KABUSYS_ENV）にかかわらず production 用 sqlite_path を使用。
    - 起動時にプロセス優先度を "high" に設定（utils.process_priority を使用）。
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient（Factory 経由）を使用し data/paper_trading.db を利用して本番 DB から分離して動作。
    - 停止フラグ、PID ファイル管理、デーモンスレッドでのエンジン実行と安全な停止処理を実装。
    - 起動時にプロセス優先度を "high" に設定。
- 設定管理
  - config.py
    - .env 自動ロード機能を実装（プロジェクトルートは .git または pyproject.toml を基準に検索）。
    - .env / .env.local の読み込み順序: OS 環境 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - .env パーサは export KEY=val、クォート値（エスケープ対応）、コメント処理に対応。
    - Settings クラスを提供。主要なプロパティ（J-Quants, kabuAPI, DB パス, PAPER_FILL_MODE バリデーション, 各種しきい値、env/log level 判定など）を用意。
    - settings インスタンスをモジュールグローバルで提供。
  - config_setup.py
    - 対話式ウィザードで .env の初期作成・更新を支援。デフォルト値、選択肢、シークレット入力対応、保存確認を実装。
  - validate_config.py
    - 起動前に .env および config/*.yaml の妥当性をチェックする CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL 判定、DB パスの親ディレクトリ存在チェック、YAML パース（PyYAML が無い場合はスキップ）などを実装。
    - --strict モードで警告を失敗扱いにできる。
- ロギング・プロセス制御ユーティリティ
  - utils/logging_setup.py
    - 共通のログ設定関数 setup_logging を追加。stdout への StreamHandler と日次ローテーション（TimedRotatingFileHandler）を組み合わせて設定。ログディレクトリは引数・環境変数・デフォルトの順で解決。既存ハンドラの二重設定を防止。
    - コンソールは stdout に出力（stderr ではない）。
  - utils/process_priority.py
    - クロスプラットフォームでのプロセス優先度設定 (set_process_priority) および CPU affinity 設定 (set_cpu_affinity) を追加。Windows / POSIX(nice) を吸収し、失敗時は警告でスキップ。
- ポートフォリオ構築ライブラリ（純粋関数群、DB非依存）
  - portfolio/portfolio_builder.py
    - シグナルの候補選定 select_candidates（スコア降順、タイブレークに signal_rank）。
    - 重み計算 calc_equal_weights、calc_score_weights（全スコア 0 の場合は等配分にフォールバックして警告）。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中上限チェックに基づき候補を除外するロジックを提供。sell_codes を考慮して当日売却予定銘柄をエクスポージャー計算から除外可能。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を返す。未知レジームは 1.0 にフォールバック（警告）。
  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method ("risk_based","equal","score") に基づく発注株数計算を実装。ロット丸め、per-position 上限、aggregate cap（利用可能現金を超える場合のスケールダウン）、cost_buffer による保守的見積り、残差処理による lot 単位の追加配分を実装。
    - TODO: 将来的に銘柄別 lot_size のサポート、価格フォールバック（price が欠損時）の改善予定（コード内に注釈あり）。
- 分析・検証ツール
  - tools/paper_verification_report.py
    - Paper Trading 向け検証レポート生成スクリプトを追加。
    - デフォルト DB パス: 環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db。
    - システム安定性（稼働率）、注文成功率・送信率、リスク却下数、API レイテンシ（avg/max/P95）を集計し、閾値（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200ms）に基づいて PASS/FAIL 判定を行う。
- 研究用モジュール（部分実装）
  - research/factor_research.py
    - DuckDB を使ったファクター計算（モメンタム、MA200乖離、ATR、ボラティリティ、流動性等）の設計と初期実装を追加（関数インターフェースと定数を整備）。（ファイル末尾で未完の箇所あり）
- パッケージ情報
  - __init__.py にてバージョンを "0.1.0" として設定。

### 変更
- （初回リリースのため該当なし）

### 修正
- （初回リリースのため該当なし）

### 既知の問題・制限事項
- research/factor_research.py の実装は途中で切れている箇所があり、いくつかの関数は未完または未使用の可能性あり。
- calc_position_sizes の価格欠損時のフォールバック（前日終値や取得原価など）はまだ実装されておらず、price が 0.0 の場合にエクスポージャーが過少見積もられるリスクがある（コード内に TODO 注釈あり）。
- config の自動 .env ロードはプロジェクトルート検出（.git / pyproject.toml）に依存するため、配布後の環境で期待どおり動作しない場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を有効化して手動で環境を設定する必要がある。
- YAML の検証は PyYAML のインストールが前提。未インストール時はスキップされ警告が出る。
- utils/process_priority の一部機能は権限不足やプラットフォーム非対応で動作しない場合がある（その場合は警告を出してスキップ）。

### セキュリティ・運用に関する注記
- .env ファイルは絶対に Git 等にコミットしないことを README/生成ヘッダで強く推奨。
- validate_config の警告は本番環境（KABUSYS_ENV=live）で特に重要。--strict オプションで運用前チェックを厳格化することを推奨。
- KILL_FLAG_CLEAR_ON_START は本番では "0" を推奨（設定ミスで自動クリアされると危険）。

---

今後の予定（例）
- research モジュールの完成（ファクター計算の SQL 実装完了、正規化ユーティリティとの連携）。
- position_sizing の銘柄別 lot_size 対応・価格フォールバックの実装。
- 監視・実行コンポーネントの単体テスト追加と E2E テスト整備。