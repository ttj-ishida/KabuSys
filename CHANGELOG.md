CHANGELOG
=========

すべての変更は Keep a Changelog の慣例に従って記載しています。主なカテゴリ: Added / Changed / Fixed / Security / Deprecated / Removed。

※日付はリポジトリ内のコードやコメントから推測して付与しています。

Unreleased
----------

- 特になし

[0.1.0] - 2026-04-25
-------------------

Added
- 初回リリース: KabuSys 日本株自動売買システムの基本コンポーネントを実装
  - 実行用スクリプト
    - run_execution.py: ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV による paper_trading モード対応（MockBrokerClient 使用、paper_trading 用 DB に記録）。
    - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能。停止フラグ (data/stop_requested.flag) により安全に終了。
  - 設定管理
    - config.py: 環境変数/​.env の自動読み込み、.env/.env.local の優先度、.env の柔軟なパース（export 句・クォート・インラインコメント対応）を実装。Settings クラスにプロパティ形式で各種設定を提供（DB パス、PID ファイル、監視閾値、PAPER_FILL_MODE 検証など）。
    - config_setup.py: .env 初期作成・更新の対話式ウィザードを提供（項目定義、既存 .env 読み込み、保存）。
    - validate_config.py: 起動前の設定検証 CLI を追加。必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性、DB パスの親ディレクトリチェック、config/*.yaml の存在と YAML パース（PyYAML があれば検証）。--strict オプションで警告を FAIL 扱いにできる。
  - ロギング・ユーティリティ
    - utils/logging_setup.py: ルートロガー設定ユーティリティを提供。stdout への StreamHandler と日次ローテーションの TimedRotatingFileHandler（logs/<app>.log）を設定。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソール出力のみ継続。
  - プロセス優先度ユーティリティ
    - utils/process_priority.py: Windows / POSIX を吸収したプロセス優先度設定と CPU affinity 設定関数を実装。psutil の利用で安全にフォールバック（権限不足などで警告に留める）。
  - ポートフォリオ構築ライブラリ
    - portfolio/portfolio_builder.py: 候補選定(select_candidates)、等金額配分(calc_equal_weights)、スコア加重(calc_score_weights)を実装。スコアゼロ時のフォールバック警告あり。
    - portfolio/position_sizing.py: 発注株数決定ロジック（risk_based / equal / score 対応）、単元株丸め（lot_size）、aggregate cap によるスケールダウン、cost_buffer を考慮した保守的なコスト推定と残余配分ロジックを実装。
    - portfolio/risk_adjustment.py: セクター集中上限の適用ロジック(apply_sector_cap)と市場レジームに応じた資金乗数(calc_regime_multiplier) を実装（未知レジームはフォールバック）。
    - portfolio/__init__.py: 主要関数の公開 API を定義。
  - 監視/検証ツール
    - tools/paper_verification_report.py: ペーパートレード用の検証レポート生成ツールを追加。system_status / trade_logs / risk_logs などから稼働率、注文成功率、送信率、レイテンシ（平均・最大・P95）を算出し PASS/FAIL 判定を出力。閾値はファイル内定義で調整可能。
  - 研究用モジュール（骨格）
    - research/factor_research.py（部分実装）: モメンタム等のファクター計算方針と定数を実装。DuckDB 接続を受け prices_daily / raw_financials を参照して計算する設計。

Changed
- N/A（初版）

Fixed
- スクリプトの堅牢性向上
  - run_monitoring.py: monitor.check_once() 内での例外をループ内で捕捉してログ出力し、次回ポーリングまで待機するようにして監視ループがクラッシュしないようにした。KeyboardInterrupt のハンドリングと finally による DB 接続クローズを保証。
  - run_execution.py: エンジンのデーモンスレッド監視と停止フラグ検知ロジックを追加。停止フラグ検知時に engine.stop() を呼び安全にシャットダウンする。
  - config._load_env_file: .env 読み込み失敗時に警告を出力し続行するようにしてテスト環境などでの耐性を向上。
  - utils/logging_setup.py: ログディレクトリ作成に失敗した場合でもコンソールログは必ず残るようフォールバック処理を明確化。

Security
- 機密値の扱い
  - config_setup.py: ウィザードで secret 項目（トークン・パスワード）を取り扱う際、表示時はマスク（****）で出力。README 等に .env を絶対に Git にコミットしない旨を記載。

Deprecated
- N/A

Removed
- N/A

Notes / Implementation details（補足）
- DB 分離
  - paper_trading モードでは paper_trading 用の SQLite（デフォルト data/paper_trading.db）を使用して本番 DB と完全分離する設計になっている。
  - 監視機能は KABUSYS_ENV にかかわらず本番用 sqlite_path を参照する実装箇所があるため（run_monitoring.py）、運用時は配置と設定に注意が必要。
- .env の自動ロード
  - デフォルトでプロジェクトルート（.git または pyproject.toml を基準）を探索して .env/.env.local を自動読み込みする。自動ロードを無効化する環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD=1。
- クロスプラットフォーム対応
  - process_priority は Windows と POSIX の差分を吸収する実装。権限不足や未サポート OS では警告ログでスキップする。
- ロギング
  - stdout へ出力する StreamHandler を採用（cron 等で stdout/stderr を一本化して扱いやすくするため）。ファイル出力は logs ディレクトリへ日次ローテーションで保存（30日保持）。

著作・バージョン
- パッケージバージョン: __version__ = "0.1.0"

今後の予定（参考）
- research/factor_research.py の完全実装（ファクター計算 SQL の追加）
- 単体テストの追加と CI 設定
- strategy 実装・シグナル生成パイプラインの統合
- 個別銘柄ごとの lot_size 対応（stocks マスタによる拡張）
- 監視テーブルスキーマや監視 UI の整備

---END---