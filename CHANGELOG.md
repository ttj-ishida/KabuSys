# CHANGELOG

すべての重要な変更を「Keep a Changelog」形式で記載します。  
このファイルはコードベースから推測して作成した初回リリース相当の要約です。

フォーマット:
- Unreleased: 今後の変更点（現状なし）
- 各リリース: 追加 (Added)、変更 (Changed)、修正 (Fixed)、非推奨 (Deprecated)、削除 (Removed)、セキュリティ (Security)

## [Unreleased]
- 現時点で未リリースの変更はありません。

## [0.1.0] - 2026-04-24
初回リリース。システム全体のコア機能（設定管理、起動スクリプト、監視、実行エンジン周辺、ポートフォリオ構築ユーティリティ、ユーティリティ関数群、ペーパートレード検証ツール）を実装。

### Added
- 基本パッケージ情報
  - kabusys パッケージ初期化（__version__ = "0.1.0"）
- 設定管理
  - Settings クラス（kabusys.config）
    - 環境変数 / .env 自動読み込み機能（.env, .env.local、OS 環境変数保護）
    - 各種設定プロパティ（J-Quants / kabu API / LINE / DB パス / 監視閾値 / 実行環境フラグなど）
    - 必須環境変数の取得時に未設定なら例外を送出する _require()
  - .env パーサーの実装（クォートやエスケープ、インラインコメントの扱いに対応）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化オプション
- 環境設定ウィザード CLI
  - kabusys.config_setup に対話式ウィザードを実装
  - .env の読み書き、既存値の再利用、シークレットのマスク表示、保存確認をサポート
  - 出力される .env に注意書き（Git にコミットしない等）
- 設定検証 CLI
  - kabusys.validate_config に起動前検証機能を追加
  - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL 検証、DB パス親ディレクトリ存在チェック
  - config/*.yaml の存在確認および PyYAML があればパース検証
  - KABUSYS_ENV=live の追加ガード（LINE 設定未設定、KILL_FLAG_CLEAR_ON_START の警告）
  - --strict モード（警告を FAIL 扱い）
- 起動スクリプト
  - run_monitoring.py
    - SystemMonitor ポーリングループ起動スクリプト
    - 環境変数 MONITOR_POLL_INTERVAL によるポーリング間隔上書き（デフォルト 60 秒）
    - 停止フラグファイル (data/stop_requested.flag) の検知で安全停止
    - 監視用 DB は環境にかかわらず本番 sqlite_path を使用（init_monitoring_db 呼出し）
    - duckdb 接続サポート
  - run_execution.py
    - ExecutionEngine 起動スクリプト
    - KABUSYS_ENV=paper_trading 時に paper_sqlite_path（data/paper_trading.db）を使用して本番 DB と分離
    - BrokerClientFactory によるブローカークライアント生成（MockBrokerClient 想定）
    - ExecutionEngine をデーモンスレッドで実行、停止フラグ監視で安全停止
    - PID ファイル出力パスサポート（data/execution.pid）
    - 依存コンポーネント（OrderRepository, OrderManager, RiskManager, Reconciler）の組立て
    - RiskManager に初期デフォルト設定値をセット（max_position_pct 等）
- 監視 DB 初期化ユーティリティ
  - init_monitoring_db 呼び出しを起動時に行い、監視テーブルの存在を保証（冪等）
- ツール
  - kabusys.tools.paper_verification_report
    - ペーパートレード結果の検証レポート生成
    - 日付フィルタ（--from / --to）、DB パス指定オプション（--db）対応
    - 指標: 稼働率（uptime）、注文成功率、送信率、リスク却下数、API レイテンシ（avg/max/P95）
    - デフォルトの合格基準（稼働率 99%、成立率 90%、送信率 95%、P95 <= 200 ms）を定義
- ポートフォリオ構築モジュール（kabusys.portfolio）
  - portfolio_builder
    - select_candidates: スコア降順で候補選定（タイブレーク: signal_rank）
    - calc_equal_weights: 等金額配分
    - calc_score_weights: スコア比率による重み化（全スコア 0 の場合は等分にフォールバック）
  - risk_adjustment
    - apply_sector_cap: セクター集中上限チェック（sell_codes を除外可能、unknown セクターは除外しない）
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数 ("bull"/"neutral"/"bear" 対応、未知はフォールバック)
  - position_sizing
    - calc_position_sizes: allocation_method("risk_based"/"equal"/"score") に基づく発注株数計算
    - lot_size（単元）丸め、max_position_pct、max_utilization、cost_buffer を考慮した aggregate cap のスケーリングロジック
    - fractional remainder を考慮して残余キャッシュで lot 単位の追加配分を行うアルゴリズム
- 研究用ファクターモジュール（kabusys.research.factor_research）
  - モメンタム、MA200、ATR、出来高などを計算する設計（DuckDB 経由で prices_daily / raw_financials を参照する想定）
  - P95 等の統計ユーティリティを含む（実装は継続中）
- ロギングユーティリティ
  - kabusys.utils.logging_setup
    - setup_logging(): stdout StreamHandler と TimedRotatingFileHandler（日次ローテーション、30 日保持）をルートロガーに設定
    - ログレベル解決順（引数 > 環境変数 LOG_LEVEL > デフォルト）
    - ログディレクトリ解決順（引数 > 環境変数 LOG_DIR > デフォルト "logs/"）
    - ログディレクトリ作成失敗時はファイル出力をスキップして警告を標準エラーに出力
    - stdout を使用することで cron/Task Scheduler などのリダイレクトとの互換性を考慮
- プロセス優先度 / CPU affinity ユーティリティ
  - kabusys.utils.process_priority
    - set_process_priority(level): Windows / POSIX(Linux, Darwin, FreeBSD) を吸収して高/通常/低 の優先度設定をサポート（psutil 使用）
    - set_cpu_affinity(cpu_count): 最初の N コアに固定する機能（未指定でスキップ）
    - アクセス権限不足や未対応 OS では安全に警告を出してスキップ

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Deprecated
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Security
- 環境変数やシークレットは .env に保存することを前提とし、config_setup において .env を Git へコミットしないよう明記

---

注記:
- 上記はソースコードから推測してまとめた CHANGELOG です。実際のリリース日やリリースノートの粒度はプロジェクト方針に合わせて調整してください。
- 今後のリリースでは各変更点を "Added/Changed/Fixed" に沿って差分を明確に記載することを推奨します。