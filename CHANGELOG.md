# Changelog

すべての注目すべき変更点を記録します。フォーマットは「Keep a Changelog」に準拠しています。  

※このファイルはコードベースからの推測に基づいて作成しています（自動生成ではありません）。

---

## [Unreleased]

- なし

---

## [0.1.0] - 2026-04-18

初回リリース。以下の機能群・CLI・ユーティリティを実装しています。

### Added

- 全体
  - パッケージ初期化とバージョン定義を追加（src/kabusys/__init__.py: __version__ = "0.1.0"）。
- 設定・環境管理
  - Settings クラスを実装し、環境変数から各種設定を取得可能にしました（src/kabusys/config.py）。
    - DB パス、KABUSYS_ENV（development / paper_trading / live）、ログレベル、
      各種しきい値、PID/kill ファイルパス等をプロパティ経由で取得。
    - PAPER_FILL_MODE の検証（instant/partial/never/reject）や env 値の妥当性チェックを実装。
  - .env 自動ロード機構を追加（プロジェクトルートの .env /.env.local を読み込み）。
    - 読み込み順: OS 環境 > .env.local > .env
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応。
  - .env ファイルのパースを強化:
    - export KEY=val 形式対応、シングル/ダブルクォート対応、エスケープ処理、行内コメント処理など（src/kabusys/config.py）。
- 設定支援 CLI
  - 環境設定ウィザードを追加（python -m kabusys.config_setup）。
    - .env の対話的作成・更新をサポート（項目定義・既存値の読み込み・シークレットマスク表示・保存）。
    - デフォルト値と項目説明を含むテンプレート生成ロジックを搭載（src/kabusys/config_setup.py）。
  - 設定検証 CLI を追加（python -m kabusys.validate_config）。
    - 必須環境変数のチェック、KABUSYS_ENV/LOG_LEVEL の妥当性検証、DB パス存在チェック、
      config/*.yaml の存在・パース検証（PyYAML が存在する場合）、
      本番向けガード（LINE 設定不足や KILL_FLAG_CLEAR_ON_START の警告）を実施。
    - --strict オプションで警告を FAIL 扱いにできる（exit code 管理）。
- 実行エントリポイント
  - ExecutionEngine 起動スクリプトを追加（src/kabusys/run_execution.py）。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 専用 SQLite を使用し、本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository/OrderManager/RiskManager/Reconciler/ExecutionEngine の組み立てとライフサイクル管理。
    - 実行中の停止フラグ（data/stop_requested.flag）検知と安全停止処理、PID ファイル処理（data/execution.pid）に対応。
  - SystemMonitor ポーリングループ起動スクリプトを追加（src/kabusys/run_monitoring.py）。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバック。
    - 監視は設定にかかわらず本番 sqlite_path を参照して監視テーブルを初期化。
    - 停止フラグ検知で安全にループを終了。
- モニタリング / DB 初期化
  - 監視用 DB テーブル初期化ユーティリティ（init_monitoring_db を各起動処理で呼び出す）を利用。
- ポートフォリオ構築ライブラリ
  - 銘柄選定・重み計算（select_candidates / calc_equal_weights / calc_score_weights）を実装（src/kabusys/portfolio/portfolio_builder.py）。
    - スコア降順および signal_rank によるタイブレークを実装。
    - スコアが全て 0 の場合のフォールバックロジックを実装。
  - セクター集中制限とレジーム乗数（apply_sector_cap / calc_regime_multiplier）を実装（src/kabusys/portfolio/risk_adjustment.py）。
    - 既存保有を考慮したセクター別エクスポージャー計算と候補除外ロジック。
    - market regime に応じた投下資金乗数（bull/neutral/bear）と未知レジームのフォールバック。
  - ポジションサイズ計算（calc_position_sizes）を実装（src/kabusys/portfolio/position_sizing.py）。
    - risk_based / equal / score の配分方式をサポート。
    - lot_size（単元）丸め、per-position 上限・aggregate cap（利用可能現金に対する縮小）、
      cost_buffer（手数料/スリッページ見積）を考慮したスケーリングロジックを実装。
- ユーティリティ
  - ログ設定ユーティリティを追加（src/kabusys/utils/logging_setup.py）。
    - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次・30日保持）を設定。
    - LOG_LEVEL / LOG_DIR /引数レベルの解決順をサポート。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
  - プロセス優先度・CPU affinity 設定ユーティリティを追加（src/kabusys/utils/process_priority.py）。
    - Windows / POSIX の違いを吸収して set_process_priority("high"|"normal"|"low") を提供。
    - set_cpu_affinity(n) によりプロセスを最初の N コアに固定可能（権限や未対応プラットフォームでは警告を出してスキップ）。
- ツール
  - Paper Trading 用検証レポート生成スクリプトを追加（src/kabusys/tools/paper_verification_report.py）。
    - データベース（PAPER_TRADING_SQLITE_PATH, --db）からシステム稼働率、注文成功率、送信率、リスク却下数、レイテンシ（平均/最大/P95）を集計してレポート出力。
    - PASS/FAIL 基準（稼働率・成功率・送信率・P95 レイテンシなど）を実装。
- 研究用モジュール（骨子）
  - ファクター計算モジュールの下地を追加（src/kabusys/research/factor_research.py）。
    - モメンタム／ボラティリティ等の計算方針と定数の定義を含む（prices_daily / raw_financials を想定）。
    - （注）ファイル途中まで実装。詳細関数は継続実装が必要。

### Changed

- なし（初回リリースのため変更履歴はありません）。

### Fixed

- なし（初回リリース）。

### Notes / Implementation details

- 起動スクリプト（execution / monitoring）は start-up 時にプロセス優先度を "high" に設定しようと試みます。権限がない環境では警告が出てスキップされます。
- run_execution は paper_trading 環境では本番 DB とは完全に分離された paper_trading 用 SQLite（デフォルト data/paper_trading.db）を使用します。
- ロギングは標準出力（stdout）へ出すように設計されているため、cron や外部スーパーバイザでの出力リダイレクト運用に適しています。
- .env のパースは現状かなり堅牢に設計されていますが、特殊ケース（複雑な入れ子クォート等）では手動調整が必要になる可能性があります。
- research/factor_research.py はファイル末尾が途中で切れているため、完全なファクター計算ロジックは未実装の箇所が残っています。

---

今後の予定（想定）
- factor_research の fully implemented functions（ファクター計算ロジックの完成）。
- ExecutionEngine / Monitoring のユニットテストとエンドツーエンドテスト追加。
- strategy / data モジュールとの統合テスト（一貫した DB スキーマの検証）。
- 監視・アラート（LINE 通知）連携の実装とドキュメント強化。