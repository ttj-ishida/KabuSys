CHANGELOG
=========

All notable changes to this project will be documented in this file.
This project adheres to "Keep a Changelog" (https://keepachangelog.com/ja/1.0.0/).
※ コードベースから推測して記載しています。実際のコミット履歴ではありません。

Unreleased
----------
- 研究用モジュールに未完の実装あり
  - research/factor_research.py の実装が途中（関数内で途中切れの箇所あり）。今後の実装・テストを予定。
- 小さな改善・追加予定
  - 追加のユニットテスト・ドキュメント整備
  - エラーハンドリング・ログの微調整

[0.1.0] - 2026-04-19
--------------------
Added
- 基本パッケージ初期実装
  - kabusys パッケージの初期リリース。
  - バージョンは __version__ = "0.1.0"。
- 実行/監視用エントリポイント
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading 時は paper_trading 用の SQLite（data/paper_trading.db を想定）を使用し、本番 DB と分離。
    - BrokerClientFactory を用いてブローカークライアントを切替可能（実ブローカー / モック）。
    - Engine の PID ファイル管理、停止フラグ (data/stop_requested.flag) による安全停止ロジックを実装。
    - スレッドで ExecutionEngine.run_session を起動し、停止フラグ検出で安全に停止する仕組みを提供。
  - run_monitoring.py: SystemMonitor 用のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番 sqlite_path を使用する設計（注意点として明示）。
    - 停止フラグ検出でループを終了、KeyboardInterrupt にも対応。
- 設定管理・ウィザード・検証
  - config.py: 環境変数読み込み・設定クラス (Settings) を実装。
    - .env 自動読み込み（プロジェクトルートを .git または pyproject.toml で検出）。
    - .env/.env.local の読み込み順と上書きルールを実装（OS 環境変数は保護）。
    - 多数の設定プロパティを提供（DB パス、API トークン、環境判定、paper_trading 用パス、各種閾値等）。
    - PAPER_FILL_MODE 等の値検証を実装。
  - config_setup.py: 対話式 .env 作成/更新ウィザードを追加。
    - J-Quants / kabu API トークンなどの入力支援、既存値の再利用、秘密値のマスク表示。
  - validate_config.py: 起動前設定検証ツールを追加。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL 検証、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在と（PyYAML があれば）パース検証。
    - --strict オプションで警告を失敗扱いにできる。
- ポートフォリオ構築ライブラリ
  - portfolio/portfolio_builder.py
    - 選定ロジック select_candidates（スコア降順、タイブレークルール）。
    - 重み計算: calc_equal_weights, calc_score_weights（スコア総和が 0 の場合は等配分にフォールバック）。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中上限チェックおよび候補除外ロジック。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear）。
  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method に応じた発注株数算出（risk_based / equal / score）。
    - 単元株（lot_size）丸め、per-position・aggregate の上限処理、cost_buffer を使った保守的見積り、スケーリングと端数配分ロジックを実装。
- ユーティリティ
  - utils/logging_setup.py
    - ルートロガーの統一設定関数 setup_logging を実装。
    - stdout に StreamHandler を出力（cron 等で stdout/stderr をまとめてリダイレクトしやすくするため）。
    - TimedRotatingFileHandler を用いた日次ローテーション（デフォルト 30 日保持）。ログディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソールのみで継続。
    - 既存ハンドラをクリアして二重登録を防止。
  - utils/process_priority.py
    - set_process_priority(level) でクロスプラットフォームに優先度設定（Windows: HIGH_PRIORITY_CLASS 等、POSIX: nice 値）。
    - set_cpu_affinity(cpu_count) で最初 N コアに固定する機能を用意（アクセス権限や未サポート環境は警告でスキップ）。
    - psutil 例外（AccessDenied 等）をハンドルして安全にフォールバック。
- モニタリング DB 初期化
  - monitoring/monitoring_db.py（呼び出し箇所あり）で監視用テーブルの初期化ロジックを想定（init_monitoring_db を各起動スクリプトで呼ぶことで冪等にテーブル保証）。
- Paper Trading 検証ツール
  - tools/paper_verification_report.py
    - paper_trading DB を読み取り、稼働率・注文成功率・送信率・API レイテンシ（平均・最大・P95）等を算出してレポート出力。
    - 基準値（稼働率 >= 99%、fill_rate >= 90%、send_rate >= 95%、P95 <= 200ms）に基づく PASS/FAIL 判定。
    - 日付フィルタ（--from / --to）と DB パスの引数/環境変数での指定をサポート。
- research/factor_research.py
  - ファクター計算モジュールを追加（Momentum / Value / Volatility / Liquidity を想定）。DuckDB を用いた prices_daily/raw_financials ベースの計算設計。現状モジュールはスキャン窓や定数等の設計が追加済みで実装途中。

Changed
- ログ出力の挙動
  - StreamHandler を stdout に固定（stderr ではない）。ファイルハンドラ作成に失敗してもコンソールには出力されるようにフォールバック。
- .env 読み込みの堅牢化
  - export KEY=val 形式、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメントの扱いなどに対応したパーサを実装。
  - .env.local を .env の上書きとして扱い、OS 環境変数を保護する仕組みを導入。
- Monitor の挙動（設計上の注意）
  - run_monitoring は KABUSYS_ENV にかかわらず監視用に Settings.sqlite_path（本番想定）を使用する仕様にしています。環境ごとの DB 分離が必要な場合は設定変更が必要。

Fixed
- 起動時のハンドラの二重登録を防止
  - setup_logging が既存ハンドラを適切に flush/close/削除してから再設定するように修正。

Security
- 機密情報の扱い
  - config_setup のウィザードで秘密情報（トークン・パスワード）をマスク表示。
  - .env ファイルは Git にコミットしない旨をテンプレートに明記。

Notes / Breaking changes
- run_monitoring が常に production の sqlite_path を使用する点は運用上の注意点です。テスト環境で監視を分離したい場合は設定（SQLITE_PATH）やコードの変更を検討してください。
- process_priority / cpu_affinity の利用は権限依存であり、アクセス拒否時は警告を出してスキップします。実行環境での権限設定を確認してください。

Acknowledgments
- 本 CHANGELOG は提供されたソースコードを解析して機能・設計を推測して作成したものです。実際のリリースノートや変更履歴と差異がある可能性があります。必要であれば、実際のコミットログを元に詳細化・修正します。