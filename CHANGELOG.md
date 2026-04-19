CHANGELOG
=========

この CHANGELOG は "Keep a Changelog" の形式に準拠しています。  
リリース日はコードベースから推測して記載しています。バージョンは src/kabusys/__init__.py の __version__ を参照しています。

Unreleased
----------
- なし（現時点で未リリースの変更はありません）

[0.1.0] - 2026-04-19
-------------------

Added
- 基本アプリケーションパッケージを追加（バージョン: 0.1.0）。
  - src/kabusys/__init__.py にて __version__ = "0.1.0" を設定。
- 実行系エントリポイント
  - run_execution.py: ExecutionEngine を起動する CLI スクリプトを追加。
    - KABUSYS_ENV により paper_trading 用の MockBroker と専用 SQLite（data/paper_trading.db）を使用する分離をサポート。
    - 停止フラグ (data/stop_requested.flag) と PID ファイル (data/execution.pid) を扱う仕組みを実装。
    - プロセス優先度を high に設定するユーティリティ呼び出しを実行開始時に行う。
    - ExecutionEngine を別スレッドで実行し、フラグ検知で安全に停止するループ実装。
- 監視系エントリポイント
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番 sqlite_path を使用（監視 DB は共通運用を想定）。
    - 停止フラグ検知、例外捕捉、最後のコネクションクローズを実装。
- 設定管理
  - config.py: 環境変数と .env の自動読み込み・検証機能を追加。
    - プロジェクトルート (.git または pyproject.toml) を探索して .env/.env.local を自動ロード（テスト時に無効化可能）。
    - 複数の設定プロパティ（DBパス、API トークン、環境判定、しきい値など）を getter として提供。
    - PAPER_FILL_MODE 等の妥当性チェックとエラーメッセージを提供。
- 設定ウィザード／検証ツール
  - config_setup.py: 対話式 .env 作成・更新ウィザードを追加。
    - キー一覧、デフォルト、選択肢、シークレット扱いなどを定義し .env を生成。
  - validate_config.py: 起動前チェック CLI を追加。
    - 必須環境変数の存在チェック、KABUSYS_ENV の妥当性、ログレベル、DB パス、config/*.yaml の存在とパース（PyYAML が無い場合はスキップ）を検証。
    - --strict オプションで警告を FAIL 扱いにできる。
- ツール
  - tools/paper_verification_report.py: Paper Trading 検証レポート生成スクリプトを追加。
    - 稼働率、注文成功率、送信率、P95 レイテンシなどを算出し PASS/FAIL 判定を出力。
    - コマンドラインで期間指定 (--from/--to) および DB ファイル指定 (--db) が可能。
    - デフォルト DB パスは data/paper_trading.db、閾値はソース内定数で定義（稼働率 99% 等）。
- ポートフォリオ構築ライブラリ
  - portfolio/portfolio_builder.py: シグナル選別と等重・スコア加重の重み計算を追加。
  - portfolio/risk_adjustment.py: セクター集中制限（apply_sector_cap）とレジーム乗数（calc_regime_multiplier）を追加。
  - portfolio/position_sizing.py: 株数計算（risk_based / equal / score）、単元丸め、aggregate cap スケーリング、コストバッファ対応を追加。
  - portfolio パッケージ __init__ で主要関数をエクスポート。
- ユーティリティ
  - utils/logging_setup.py: 統一ログ設定ユーティリティを追加。
    - StreamHandler（stdout）と TimedRotatingFileHandler（デイリー、30日保持）をルートロガーに設定。
    - 出力ディレクトリ作成失敗時はファイル出力を安全にスキップするフォールバック実装。
    - LOG_LEVEL / LOG_DIR の解決ルールを実装。
  - utils/process_priority.py: クロスプラットフォームなプロセス優先度と CPU affinity 設定を追加。
    - Windows / POSIX (Linux/ Darwin / FreeBSD) に対応し、失敗時は警告を出してスキップ。
    - set_process_priority(level), set_cpu_affinity(cpu_count) を提供。
- research/factor_research.py
  - ファクター計算モジュールを追加（モメンタム、MA200、ATR、流動性などの定義と設計方針）。
  - DuckDB 接続を受け prices_daily / raw_financials を使って計算する設計（未完の関数あり）。

Changed
- なし（初回リリースのため変更履歴は主に追加のみ）

Fixed
- なし（初回リリースにおける既知の修正はなし。ただし各モジュールは堅牢なフォールバック・例外処理を盛り込んでいる）
  - 例: .env 読み込み失敗時の警告、ログディレクトリ作成失敗時のフォールバック、psutil アクセス拒否時の優先度設定スキップ等。

Deprecated
- なし

Removed
- なし

Security
- なし（機密値は .env として取り扱い、config_setup でシークレットはマスク表示を行う設計）

Notes / 実装上の注意
- 監視（run_monitoring）は MONITOR_POLL_INTERVAL を整数で受け取り、1 未満や不正値はデフォルト 60 秒にフォールバックする実装です。
- run_execution は停止フラグファイルの存在を検知して起動を回避・停止するため、運用時は data/stop_requested.flag の管理に注意してください。
- .env の自動ロードはプロジェクトルートを検出できない場合はスキップされます。環境変数を明示的に利用する CI / 配布後の環境では KABUSYS_DISABLE_AUTO_ENV_LOAD を設定できます。
- portfolio/position_sizing の計算では price の欠損（0.0）に対する TODO コメントがあり、将来的に価格フォールバックの追加が想定されています。
- research パッケージ（factor_research）は設計に基づく実装が進行中で、一部関数が未完（ソース末尾で切れている箇所あり）。用途に応じて追加実装が必要です。

今後の予定（提案）
- research/factor_research の完全実装（モメンタム等の集計ロジック完結）。
- テストスイートの追加（CI 用ユニット / 統合テスト）。
- ドキュメントの強化（API リファレンス、運用手順、データスキーマ）。
- 発注・ブローカー抽象化の更なる堅牢化（滑りや手数料のモデル化、lot_size 銘柄別対応）。

以上