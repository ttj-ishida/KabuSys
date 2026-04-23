CHANGELOG
=========

すべての変更は Keep a Changelog の形式に従っています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

Unreleased
----------

- 現在のワーキングツリーに対する未リリースの変更はありません。

0.1.0 - 2026-04-23
-----------------

Added
- 初回リリース: KabuSys 基本機能群を追加。
  - 起動スクリプト／サービス
    - run_execution.py: ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV=paper_trading 時は MockBrokerClient を用い、paper_trading 用の SQLite（デフォルト: data/paper_trading.db）に記録する。停止フラグ（data/stop_requested.flag）検知・PID 管理・デーモンスレッドでの実行をサポート。
    - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視テーブルは常に本番 sqlite_path を使用して初期化する。
  - 設定・検証
    - config.py: .env 自動読み込み（.env → .env.local、OS 環境変数優先）、.env パース（export プレフィックス、クォート、インラインコメント対応）、Settings クラスによる typed プロパティを提供（DB パス、paper_trading 用パス、KABUSYS_ENV、しきい値等）。
    - config_setup.py: 対話式の .env 作成/更新ウィザードを追加。代表的な環境変数項目を用意し、既存の .env からの再利用・確認・保存をサポート。
    - validate_config.py: 起動前チェック CLI を追加。必須環境変数、KABUSYS_ENV 値、ログレベル、DB パス、config/*.yaml の存在と YAML パース（PyYAML が無い場合はスキップ）などを検証。--strict オプションで警告をエラー扱いにできる。
  - ポートフォリオ構築（純粋関数群）
    - portfolio.portfolio_builder: シグナル選定（select_candidates）、等配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を提供。スコアが全て 0 の場合は等分配へフォールバック（警告ログ）。
    - portfolio.risk_adjustment: セクター集中制限（apply_sector_cap）とレジーム乗数（calc_regime_multiplier）を提供。既存保有のセクターエクスポージャーを基に新規候補をフィルタリングし、"unknown" セクターは上限チェックの対象外とする。レジームに未知値が来た場合はログを出力して 1.0 にフォールバック。
    - portfolio.position_sizing: 株数計算ロジックを追加。allocation_method に "risk_based", "equal", "score" をサポート。単元株（lot_size）丸め、1銘柄上限、aggregate cap（available_cash）によるスケールダウン、cost_buffer（手数料/スリッページ見積り）考慮、残差の再配分ロジックを実装。
  - ユーティリティ
    - utils.logging_setup: 統一ログ設定ユーティリティを追加。stdout への StreamHandler と日次ローテーション（TimedRotatingFileHandler）を持つファイル出力を設定。ログディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソールのみで継続。ログレベル・ログディレクトリの解決ルールを実装。
    - utils.process_priority: Windows / POSIX の差分を吸収してプロセス優先度（high/normal/low）および CPU affinity を設定するユーティリティを追加。権限不足や未対応 OS の場合は警告を出して安全にスキップする実装。
  - 監視・検証ツール
    - monitoring.monitoring_db, monitoring.system_monitor など（起動スクリプトから使用）により監視テーブル初期化と単回チェックをサポート（run_monitoring から利用）。
    - tools.paper_verification_report.py: Paper Trading 用の検証レポート生成ツールを追加。system_status / trade_logs / risk_logs からシステム稼働率、注文成功率、送信率、リスク却下数、レイテンシ（平均・最大・P95）を算出し、基準値（稼働率 >= 99%、注文成功率 >= 90%、送信率 >= 95%、P95 <= 200ms）に基づいて PASS/FAIL を判定する。日付フィルタ（--from/--to）と DB パス指定（--db / 環境変数）をサポート。
  - データアクセス
    - DuckDB を分析用 DB として統合（duckdb パスを Settings で管理）。factor_research モジュール等で DuckDB 接続を受け取ってファクター計算を行う設計。

Changed
- 初版のため過去からの変更は無し。

Fixed
- 初版のため過去からの修正履歴は無し。ただし次のランタイム上の安全対策が含まれる:
  - MONITOR_POLL_INTERVAL の不正値（0以下や非数）を検出してデフォルトにフォールバックし、警告ログを出力。
  - .env 読み込みでファイル読み込み失敗時に警告（warnings.warn）を出す実装。
  - ログディレクトリ作成失敗時はファイルハンドラ作成をスキップし、標準出力のみでログ出力するフェイルセーフ。

Security
- 環境変数の取り扱いにおいて .env の自動読み込みを行うが、.env は絶対に Git にコミットしない旨を README/ウィザード内のコメントで明記（config_setup に記述）。

Notes / Implementation details
- run_monitoring は「監視は本番 sqlite_path を使用する」と明示しており、環境に依らず監視データを本番の監視 DB に貯める設計になっている点に注意。
- run_execution は Paper Trading と Live を明確に分離し、paper_trading 時は専用の SQLite にデータを残すことで本番 DB と分離している。
- .env パーサは export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメント処理を扱い、既存の OS 環境変数を保護するための protected オプションを備えている。

今後の予定（例）
- factor_research の完全実装（ファクター計算ロジックの続き）。
- テストカバレッジの追加（ユニットテスト・統合テスト）。
- エラーメトリクス収集・外部モニタリング連携の強化。
- 単元（lot）情報を銘柄マスタに保持して銘柄毎に対応する拡張。

--- 
（この CHANGELOG は与えられたコードベースの内容から推測して作成しています。実際のリリースノートは開発者の意図に合わせて調整してください。）