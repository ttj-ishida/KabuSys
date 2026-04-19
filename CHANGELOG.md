Keep a Changelog
=================

すべての重要な変更をこのファイルに記録します。
フォーマットは「Keep a Changelog」に準拠します。
リリース日付はコードベースのスナップショットから推測して付与しています。

フォーマットのルール:
- すべての変更はカテゴリ別に分けて記載します（Added, Changed, Fixed, Removed）。
- 可能な限り実装の意図や挙動の注釈を付けています。

Unreleased
----------

（現在未リリースの変更はありません）

[0.1.0] - 2026-04-19
--------------------

Added
- 基本アプリケーション構成と起動スクリプトを実装
  - run_execution.py：ExecutionEngine 起動用スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 専用 SQLite DB を使用して本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、ExecutionEngine の起動・停止ロジックを実装。
    - 停止フラグ（data/stop_requested.flag）と PID ファイル（data/execution.pid）をサポート。
  - run_monitoring.py：SystemMonitor（監視）ポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境に関係なく本番 sqlite_path を使用して監視テーブルを初期化。
    - 停止フラグの検出、エラーハンドリング、接続クローズ処理を実装。
- 設定・環境管理
  - config.py：環境変数ラッパー Settings を追加。
    - .env 自動ロード機能（.env / .env.local）をプロジェクトルート（.git または pyproject.toml）から行う（OS 環境変数は保護）。
    - 各種設定プロパティ（DB パス、KABUSYS_ENV、LOG_LEVEL、paper_trading 関連、監視しきい値等）を実装。
    - 入力検証（有効な KABUSYS_ENV 値、PAPER_FILL_MODE の検証など）を実装。
- 設定支援ツール
  - config_setup.py：対話式 .env ウィザードを追加（.env の初期作成・更新）。
    - 各種項目定義、既存 .env 読み込み、項目ごとの入力プロンプト、シークレットのマスキング、保存機能を実装。
  - validate_config.py：設定検証 CLI を追加（必須環境変数・パス・config/*.yaml の存在とパース確認、--strict モードをサポート）。
- ロギングとプロセス制御
  - utils/logging_setup.py：統一的なログ初期化ユーティリティを追加。
    - stdout 出力（StreamHandler）と日次ローテーション（TimedRotatingFileHandler）をルートロガーに設定。
    - ログディレクトリ作成失敗時のフォールバックとログレベル解決順序を実装。
  - utils/process_priority.py：プロセス優先度（high/normal/low）と CPU affinity 設定ユーティリティを追加。
    - Windows / POSIX の差異を吸収し、権限不足時は警告を出してスキップする堅牢な実装。
- ポートフォリオ構築・リスク制御ライブラリ
  - portfolio/portfolio_builder.py：候補選定・重み算出（等金額・スコア加重）を実装。
  - portfolio/position_sizing.py：発注株数計算（risk_based / equal / score）、単元丸め、aggregate cap スケーリング、コストバッファ考慮を実装。
  - portfolio/risk_adjustment.py：セクター集中制限（apply_sector_cap）と市場レジームに応じた乗数（calc_regime_multiplier）を実装。
  - portfolio/__init__.py：主要関数をエクスポート。
- リサーチ／ファクター計算（基礎）
  - research/factor_research.py：DuckDB を使ったモメンタム等ファクター計算モジュールの骨格を実装（関数記述、定数、設計方針）。
    - モメンタム、移動平均乖離、ATR、流動性等を計算する仕様を記載（実装はファイル末尾で続く想定）。
- ツール
  - tools/paper_verification_report.py：Paper Trading 用検証レポート生成スクリプトを追加。
    - system_status / trade_logs / risk_logs などから稼働率、注文成功率、送信率、レイテンシ（平均・最大・P95）を集計して PASS/FAIL を判定。
    - 閾値（稼働率 99%、注文成立率 90% 等）と P95 計算ロジックを実装。
- パッケージ情報
  - __init__.py にてバージョンを "0.1.0" に設定。

Changed
- ログ出力ポリシー
  - ログは標準出力（stdout）を基本とし、ログディレクトリが作成可能な場合にファイルローテーションを有効化する挙動に統一。
- .env 読み込みの優先度
  - OS 環境変数 > .env.local > .env の順で読み込む（OS 環境は保護され、.env.local は上書き可能）。

Fixed
- .env パーサの堅牢化
  - クォート内のバックスラッシュエスケープやインラインコメント処理、"export KEY=val" 形式のサポートを追加し、より実用的な .env パースを実現。
- ポーリング間隔の安全化
  - MONITOR_POLL_INTERVAL の不正値（0 以下や非整数）を検出してデフォルト（60 秒）にフォールバックする保護処理を追加。

Security
- .env ファイルについて明示的に「Git にコミットしないこと」をウィザードの出力に含めるなど、認証情報の取り扱いに関する注意喚起を強化。

Notes / Implementation details
- run_monitoring は監視データ用の SQLite（settings.sqlite_path）を環境に関係なく使用する設計。これは監視が常に本番データの状態を参照する想定のため。
- run_execution は paper_trading モード時に完全に分離された paper DB（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）を使用することで本番 DB と衝突しないようにしている。
- process_priority の設定は権限不足やプラットフォーム非対応時に安全にスキップするよう設計。
- position_sizing の aggregate スケーリングは小数切捨て・単元丸めを考慮し、残余キャッシュに基づく再配分ロジックを持つ（再現性のためソートの安定化を考慮）。
- validate_config は PyYAML がない環境でも動くように設計されており、YAML 検証は PyYAML がインストールされている場合のみ実行される。

Acknowledgments
- 初期実装のため多数のユーティリティ関数・CLI が実装されています。今後のリリースでテストカバレッジの追加、ドキュメントの整備、CI 統合などを行う予定です。