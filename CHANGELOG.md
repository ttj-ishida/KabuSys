CHANGELOG
=========

すべての変更は Keep a Changelog の慣習に従って記載しています。  
フォーマット: https://keepachangelog.com/（日本語訳を参照）

Unreleased
----------

- なし

0.1.0 - 2026-04-22
------------------

Added
- パッケージ初期リリース。
- 実行系スクリプト
  - run_execution.py: ExecutionEngine 起動用スクリプトを追加。プロセス優先度を高く設定し、Daemon スレッドでエンジンを実行。停止は data/stop_requested.flag と execution.pid により制御。
  - run_monitoring.py: SystemMonitor 用ポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境にかかわらず本番 sqlite_path を使用する設計。
- 設定管理
  - config.py: .env の自動読み込み（プロジェクトルート検出）と環境変数ラッパーを実装。必須変数チェック用の _require、各種パス・フラグ・閾値・環境判定プロパティを提供。
  - config_setup.py: 対話式環境設定ウィザードを追加し .env の生成・更新をサポート。デフォルト値や秘匿表示、確認プロンプトを持つ。
  - validate_config.py: 起動前の設定検証 CLI を追加（--strict オプションあり）。必須環境変数、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在、config/*.yaml の存在・パース検証（PyYAML がある場合）などをチェック。
- ポートフォリオ構築モジュール（純粋関数群）
  - portfolio/portfolio_builder.py: シグナルのソート、候補選定、等金額・スコア加重配分を実装。
  - portfolio/position_sizing.py: 各銘柄の発注株数算出（risk_based / equal / score）、単元株丸め、集約キャップ（available_cash に基づくスケーリング）、コストバッファ対応を実装。
  - portfolio/risk_adjustment.py: セクター集中制限（apply_sector_cap）と市場レジームに応じた乗数（calc_regime_multiplier）を実装。
  - portfolio/__init__.py で上記関数群をエクスポート。
- 分析・検証ツール
  - tools/paper_verification_report.py: Paper Trading 用検証レポート生成スクリプトを追加。稼働率、注文成功率・送信率、リスク却下数、レイテンシ（平均/最大/P95）を算出して PASS/FAIL 判定を行う。PAPER_TRADING_SQLITE_PATH 環境変数や CLI オプションで DB を指定可能。
- ログ・プロセスユーティリティ
  - utils/logging_setup.py: 統一的なログ設定ユーティリティを追加。stdout ストリーム出力と日次ローテーション（TimedRotatingFileHandler）をルートロガーに設定。ログディレクトリ作成失敗時はファイル出力をスキップして stdout のみで継続。
  - utils/process_priority.py: Windows/Linux/macOS でのプロセス優先度設定（nice / Windows 優先度定数）と CPU affinity 設定ユーティリティを追加。権限不足や未対応 OS を考慮した例外ハンドリングあり。
- その他
  - __init__.py にパッケージバージョン __version__ = "0.1.0" を設定。
  - research/factor_research.py の骨組み（DuckDB 接続を受け取るファクター計算モジュール）を追加（モメンタム計算などの定義あり）。  

Changed
- 初回リリースのための設計決定を明示:
  - Paper Trading（KABUSYS_ENV=paper_trading）は本番 DB と分離して data/paper_trading.db を使用（Execution 起動時に切り替え）。
  - 監視（monitoring）は env に依存せず本番 sqlite_path を利用する仕様（運用上の一貫性確保）。
  - .env 自動ロードの優先順位: OS 環境 > .env.local > .env。テスト向けに自動ロードを無効化するフラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。

Fixed
- 初期版における既知の設計注意点をドキュメントに明示:
  - position_sizing.calc_position_sizes: price が欠損（0.0）の場合に保守的にスキップする挙動を記載。将来的なフォールバック価格の必要性をコメントとして残す。
  - risk_adjustment.apply_sector_cap: "unknown" セクターはセクター上限適用対象外とし挙動を明示。

Notes / 注意事項
- run_monitoring と run_execution は停止制御にプロジェクトルート/data 内の stop_requested.flag を使用する設計。運用時は該当フラグ管理に注意してください。
- ログディレクトリ作成やプロセス優先度設定は実行環境の権限に依存します。権限不足時は警告を出してスキップするため、必ずしも処理が完了するとは限りません。
- config_setup で生成される .env は絶対に Git にコミットしないことを README に追記推奨。
- research/factor_research.py はモジュール設計の骨子を含みますが、完全実装（全ファクター計算）は今後の作業対象です。

今後の予定（TODO / Roadmap）
- research/factor_research の完全実装（Momentum / Value / Volatility / Liquidity の計算ロジック完成）。
- テストカバレッジの充実（特に position_sizing のスケーリング・端数処理、apply_sector_cap の境界ケース）。
- 設定検証の強化（config/*.yaml のスキーマ検証、自動生成スクリプトとの連携）。
- 個別銘柄ごとの lot_size 対応（stocks マスタから取得する設計への拡張）。

お問い合わせ・貢献
- 変更内容やバグ報告・プルリクエストはリポジトリの Issue / PR をご利用ください。