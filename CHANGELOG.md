Keep a Changelog
=================

すべての注目に値する変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。  
リリース日はコードから推測して付与しています。

Unreleased
---------

(現時点で未リリースの変更はありません)

[0.1.0] - 2026-04-21
-------------------

Added
- プロジェクト初期リリースを追加（__version__ = 0.1.0）。
- 起動スクリプトを追加:
  - run_execution.py
    - ExecutionEngine を起動するエントリポイント。
    - KABUSYS_ENV=paper_trading 時は paper_trading 用の SQLite (data/paper_trading.db) を使用し、本番 DB と分離して動作。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler を組み立て、スレッドでエンジンを実行。停止フラグ (data/stop_requested.flag) を監視して安全停止。
    - 起動時にプロセス優先度を設定し、PID ファイルを書き出す仕組みを想定。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視用 DB は環境に関わらず本番 sqlite_path を使用（監視は本番 DB を参照する設計）。
    - 停止フラグによるループ終了、例外発生時のログ出力処理を実装。
- 設定・環境周り:
  - config.py
    - .env 自動ロード機能（プロジェクトルートの検出: .git または pyproject.toml を基準）。
    - .env および .env.local の読み込み順序（OS 環境変数を保護）。
    - 詳細な .env パース（export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメント対応）。
    - Settings クラスで各種環境設定をプロパティで提供（DB パス、KABUSYS_ENV 検証、PAPER_FILL_MODE 検証など）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能（テスト向け）。
  - config_setup.py
    - 対話式ウィザードで .env を初期作成・更新する CLI を追加。シークレット入力のマスク、選択肢、デフォルト値、保存前の確認を提供。
  - validate_config.py
    - 起動前に .env と config/*.yaml を検証する CLI を追加。必須環境変数のチェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスの親ディレクトリチェック、YAML パース（PyYAML がない場合はスキップして警告）などを実装。--strict モードで警告を FAIL 扱いに可能。
- ユーティリティ:
  - utils/logging_setup.py
    - 全起動スクリプトで共通利用できるログ設定ユーティリティを追加。
    - stdout への StreamHandler（stdout を使用）と日次ローテーションの TimedRotatingFileHandler（logs/<app_name>.log）を設定。ログディレクトリの自動作成、作成失敗時のフォールバック処理を実装。
    - ログレベル解決の優先度（関数引数 > 環境変数 > デフォルト）を採用。
  - utils/process_priority.py
    - クロスプラットフォームでプロセス優先度・CPU affinity を設定するユーティリティを追加。
    - Windows / POSIX（Linux, macOS, FreeBSD）に対応し、psutil による設定を試みる。権限不足や未サポート環境では警告ログを出してスキップ。
- ポートフォリオ構築モジュール（純粋関数群、DB 非依存）:
  - portfolio/portfolio_builder.py
    - BUY シグナルから候補選定（スコア降順・タイブレーク）select_candidates。
    - 等金額配分 calc_equal_weights、スコア加重配分 calc_score_weights（全スコア 0 の場合に等配分へフォールバック）。
  - portfolio/risk_adjustment.py
    - セクター集中制限 apply_sector_cap（既存ポジションのセクター比率が閾値を超える場合の除外）。
    - 市場レジームに応じた投下資金乗数 calc_regime_multiplier（bull/neutral/bear のマッピング、未知値は警告とフォールバック）。
  - portfolio/position_sizing.py
    - 株数決定ロジック calc_position_sizes。
    - risk_based / equal / score の配分方式をサポート。
    - lot_size（単元）丸め、1銘柄上限・総合上限（aggregate cap）のスケールダウン、cost_buffer による保守的見積り、残差を使った追加配分アルゴリズムを実装。
- ツール:
  - tools/paper_verification_report.py
    - ペーパートレーディング用の検証レポート生成スクリプトを追加。
    - system_status / trade_logs / risk_logs テーブルを参照して稼働率、注文成功率、送信率、リスク却下数、レイテンシ (avg/max/P95) を計算し、閾値判定(稼働率等)で PASS/FAIL を出力。
    - DB パスはコマンド引数 --db, 環境変数 PAPER_TRADING_SQLITE_PATH, デフォルトを順に参照。
- research/factor_research.py
  - ファクター計算モジュールの骨子を追加（モメンタム、MA200、ATR、出来高系などの計算方針と定数を定義）。DuckDB を用いた計算を想定（prices_daily / raw_financials を参照）。

Changed
- なし（初回リリースのため、既存コードの「変更」はなし）。

Fixed
- なし（初回リリースとして既知の不具合修正は該当なし。ただし各モジュールで例外安全な処理やフォールバックを多用し堅牢化を図っている）。

Security
- なし（機密情報は .env で管理する方針。config_setup には .env を Git にコミットしない旨の注意書きを含む）。

Notes / 実装上の注記（推測含む）
- .env パーサはシングル/ダブルクォート内のバックスラッシュエスケープや export プレフィックス、インラインコメント処理に対応しており、より堅牢な .env 処理を目指している。
- 設定の自動ロードはプロジェクトルートが検出できないとスキップされるため、パッケージ配布後も動作することを想定。
- 実行時のプロセス優先度設定は管理者権限が必要になる場合があるため、権限不足時は警告のみで続行する安全設計。
- run_monitoring は MONITOR_POLL_INTERVAL の不正な値を検出してデフォルトへフォールバックするなど、運用時の堅牢性に配慮している。
- portfolio モジュールは純粋関数設計でユニットテストが容易な構成を意図しており、将来的な拡張（銘柄別 lot_size など）に配慮した TODO コメントを含む。
- research モジュールはファクター計算の方針・定数を定義しているが、完全実装は一部残っている（momentum 計算の実装開始を示唆する箇所あり）。

今後の予定（例）
- factor_research の完全実装（DuckDB クエリ実装の続き）。
- ExecutionEngine / SystemMonitor のさらなる統合テスト、paper_trading のモックブローカーの充実。
- config/*.yaml のテンプレート生成スクリプトおよびデフォルト値の配布。

--- 

※ この CHANGELOG は、提示されたソースコードから機能・意図を推測して作成しています。実際のコミット履歴が存在する場合は、コミットログに基づく正確な CHANGELOG 生成を推奨します。