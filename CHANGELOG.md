# Changelog

すべての変更は Keep a Changelog の慣例に従って記載しています。  
このプロジェクトではセマンティックバージョニングを採用しています。

※ 本ファイルはコードベースから機能・挙動を推測して作成しています。

## [Unreleased]
- 今のところ無し。

## [0.1.0] - 2026-04-18
初回リリース。自動売買システムのコアユーティリティ、起動スクリプト、設定管理、ポートフォリオ構築および検証ツールを追加。

### Added
- 全体
  - パッケージ初期化とバージョン設定 (`kabusys.__version__ = "0.1.0"`).
  - DuckDB / SQLite を利用する分析・監視基盤の導入（設定経由でパス指定）。
- 起動スクリプト
  - run_execution: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV が `paper_trading` の場合は専用のペーパートレード用 SQLite（既定: data/paper_trading.db）を使用し、本番 DB と分離。
    - BrokerClientFactory を利用してブローカークライアントを動的に生成。
    - ExecutionEngine は別スレッドで run_session を実行。data/execution.pid の PID ファイル管理、data/stop_requested.flag による停止フラグ監視を実装。
    - リスク管理（RiskManager）用の初期設定が組み込まれており、初期ポートフォリオ値はブローカから取得して設定。
  - run_monitoring: SystemMonitor ポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` によりポーリング間隔の上書きが可能（デフォルト 60 秒）。
    - 監視プロセスは環境にかかわらず本番用の sqlite_path（監視 DB）を使用して初期化する旨の挙動を採用。
    - 停止フラグ (data/stop_requested.flag) の検知、例外発生時のログ出力を実装。
- 設定・検証
  - config.py: 環境変数 / .env 自動読み込み機能を追加。
    - プロジェクトルート検出（.git または pyproject.toml を基準）により .env/.env.local を自動ロード。
    - 自動読み込みを無効化する `KABUSYS_DISABLE_AUTO_ENV_LOAD` をサポート。
    - .env パース実装はクォートや export プレフィックス、行内コメント等に対応。
    - Settings クラスを追加し、各種設定（DB パス・API トークン・監視閾値・環境判定など）をプロパティで提供・検証。
  - config_setup.py: インタラクティブな環境設定ウィザードを追加。
    - .env の初期作成・更新を対話形式で支援。クリアな説明とデフォルト値・選択肢を提供。
    - J-Quants / kabu API の必須項目やログ周りの設定を含む。
  - validate_config.py: 起動前の設定検証 CLI を追加。
    - 必須環境変数の存在、KABUSYS_ENV / LOG_LEVEL の値チェック、DB パス親ディレクトリの存在確認、config/*.yaml の存在および（PyYAML があれば）パース検証等を実行。
    - `--strict` オプションで警告を Fail 扱いにできる。
- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - select_candidates: スコア降順・タイブレーク処理で候補選定。
    - calc_equal_weights / calc_score_weights: 等配分およびスコア加重配分を提供。全銘柄スコアが 0 の場合は等配分にフォールバックして警告ログを出力。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中制限（既存保有を考慮）を適用し、上限超過セクターの新規候補を除外。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を返す。未知レジームは 1.0 でフォールバック（警告ログ）。
  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method（risk_based / equal / score）に基づく発注株数決定ロジックを実装。
    - 単元株（lot_size）丸め、per-position/max_position_pct による上限、available_cash に基づく aggregate cap（スケーリング）、cost_buffer を考慮した保守的見積り、残差に対する再配分ロジックを搭載。
- ツール
  - tools/paper_verification_report.py: ペーパートレード結果の検証レポート生成スクリプトを追加。
    - system_status, trade_logs, risk_logs から稼働率、注文成功率、送信率、P95 レイテンシ等を算出。
    - PASS/FAIL の判定基準と閾値（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200ms）を実装。
    - CLI 引数 `--from`, `--to`, `--db` をサポート。環境変数 `PAPER_TRADING_SQLITE_PATH` も使用可能。
- ユーティリティ
  - utils/logging_setup.py
    - 統一的なロギング設定関数 setup_logging を追加。stdout へ出力する StreamHandler と、日次ローテーション（TimedRotatingFileHandler）でログをファイルに保存（既定: logs/、30日保持）。
    - ログレベル・ログディレクトリの解決順を定義。ログディレクトリ作成失敗時はファイルハンドラをスキップしてコンソールのみで継続。
  - utils/process_priority.py
    - set_process_priority / set_cpu_affinity を追加。Windows と POSIX を吸収してプロセス優先度・CPU affinity を設定（psutil 利用）。
    - 権限不足や未対応 OS 時は警告を出して安全にスキップ。

### Changed
- （初回リリースのため変更履歴は無し）

### Fixed
- （初回リリースのため修正履歴は無し）

### Security
- 環境ファイル (.env) 関連の注意喚起を config_setup に記載（.env を Git にコミットしないことを明示）。

### Notes / Implementation details（重要な挙動）
- 設定自動ロード
  - OS 環境変数 > .env.local > .env の優先順位で読み込まれる。既存の OS 環境変数は保護され、自動上書きされない。
  - 自動読み込みを無効化する環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- Monitoring と Execution の DB 挙動
  - 監視プロセス（run_monitoring）は KABUSYS_ENV に依らず sqlite_path（監視 DB）を使用して初期化する点に注意。
  - Execution は paper_trading 環境時に paper_sqlite_path を使用し、発注系データを本番 DB と分離する。
- 起動・停止制御
  - 両スクリプトはプロジェクト内の data/stop_requested.flag を監視し、フラグ検出でシャットダウンする安全機構を備える。
  - Execution は PID ファイルを管理し、エンジンスレッドの join / stop を適切に行う。
- ログ
  - ログはデフォルトで stdout に出力され、ファイル出力は logs/<app_name>.log に日次ローテーションで保存（失敗時はコンソールのみ）。
- ポートフォリオ関数群は純粋関数設計（副作用なし、DB 参照なし）でテスト容易性を考慮。

---

今後の改善案（未実装・検討項目）
- price の欠損時のフォールバック価格（前日終値や取得原価など）サポート（apply_sector_cap に注釈あり）。
- 銘柄ごとの lot_size を stocks マスタで管理する設計への拡張（position_sizing に TODO）。
- レジーム判定やシグナル生成側との型・契約のさらなる明確化とテストカバレッジ強化。
- tools / レポートの出力先オプション（CSV/JSON）や単体テスト追加。

（以上）