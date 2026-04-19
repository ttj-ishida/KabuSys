CHANGELOG
=========

すべての注目すべき変更を時系列で記録します。  
このファイルは "Keep a Changelog" のフォーマットに準拠しています。

フォーマット:
- Added: 新機能
- Changed: 既存機能の変更
- Fixed: バグ修正
- Removed: 削除

[Unreleased]
------------

- （現在未リリースの変更はありません）

[0.1.0] - 2026-04-19
-------------------

Added
- 初回リリース。KabuSys のコアユーティリティ、実行・監視エントリポイント、設定管理、ポートフォリオ構築、検証ツール等を追加。
  - 起動スクリプト
    - src/kabusys/run_monitoring.py
      - SystemMonitor のポーリングループ起動スクリプトを追加。
      - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
      - 停止フラグ file: data/stop_requested.flag を検出してループを終了。
      - 監視は設定にかかわらず本番用 sqlite_path を使用し、duckdb も接続する。
    - src/kabusys/run_execution.py
      - ExecutionEngine 起動スクリプトを追加。
      - KABUSYS_ENV=paper_trading の場合は paper_trading 用の専用 SQLite（data/paper_trading.db 等）を使用し、本番 DB と分離。
      - BrokerClientFactory を用いたブローカークライアント生成、ExecutionEngine のバックグラウンド起動、停止フラグによる停止制御（data/execution.pid / stop flag）を実装。
  - 設定管理
    - src/kabusys/config.py
      - .env 自動読み込み機構を実装（プロジェクトルート検出: .git / pyproject.toml 基準）。
      - .env のパースはクォート・エスケープ・インラインコメントに対応。
      - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
      - Settings クラスで各種環境変数をプロパティとして提供（DB パス、PID ファイル、閾値、環境種別判定等）。
      - PAPER_FILL_MODE のバリデーションや paper_trading 用 sqlite パス、各種閾値のプロパティを実装。
  - 設定ユーティリティ / CLI
    - src/kabusys/config_setup.py
      - 対話式ウィザードで .env を作成 / 更新する機能を追加。
      - デフォルト値・選択肢・シークレット入力・保存確認を提供。
    - src/kabusys/validate_config.py
      - .env や config/*.yaml の設定検証 CLI を追加。必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の検証、DB パスの親ディレクトリ存在確認、YAML パース（PyYAML が利用可能な場合）などを行う。
      - --strict オプションで警告を FAIL 扱いにできる。
  - ロギング / プロセス制御ユーティリティ
    - src/kabusys/utils/logging_setup.py
      - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次、30日保持）を設定する共通セットアップを実装。
      - 既存ハンドラの重複を避けるためクリア後に設定。LOG_DIR / LOG_LEVEL の優先解決を実装。
      - ログディレクトリ作成失敗時もフォールバックしてコンソール出力を継続。
    - src/kabusys/utils/process_priority.py
      - プラットフォーム差分を吸収したプロセス優先度設定（Windows の priority class / POSIX の nice 値）を実装。
      - CPU affinity 設定ヘルパー（最初の N コアに固定）を追加。権限不足や未対応 OS では警告でスキップ。
  - ポートフォリオ構築関連（純粋関数群）
    - src/kabusys/portfolio/portfolio_builder.py
      - 候補選定 (select_candidates)、等配分 (calc_equal_weights)、スコア加重 (calc_score_weights) を追加。
    - src/kabusys/portfolio/risk_adjustment.py
      - セクター集中制限の適用 (apply_sector_cap)、市場レジームに応じた乗数計算 (calc_regime_multiplier) を実装。
      - 未知レジームは警告を出してフォールバック（1.0）。
    - src/kabusys/portfolio/position_sizing.py
      - 発注株数計算 (calc_position_sizes) を実装。allocation_method に応じて "risk_based" / "equal" / "score" をサポート。
      - lot_size（単元）による丸め、max_position_pct / max_utilization / cost_buffer による上限・スケーリング処理を実装。
  - 解析 / 検証ツール
    - src/kabusys/tools/paper_verification_report.py
      - Paper Trading 用の検証レポート生成ツールを追加。
      - 稼働率、注文成功率、送信率、レイテンシ（平均・最大・P95）などを算出し PASS/FAIL 判定（閾値はソース内定義）。
      - 日付範囲フィルタや DB パス指定（--db / 環境変数）をサポート。
  - 研究用ファクター計算（初期実装）
    - src/kabusys/research/factor_research.py
      - Momentum / Value / Volatility / Liquidity 等のファクター計算を行う設計で骨組みを追加（DuckDB を利用して prices_daily / raw_financials 参照を想定）。ファイルは一部実装段階。

  - パッケージメタ
    - src/kabusys/__init__.py
      - パッケージ初期化と __version__ = "0.1.0" を追加。

Changed
- n/a（初回リリースのため過去変更なし）

Fixed
- n/a

Removed
- n/a

Notes / Behavioural details
- 実行・監視プロセスは起動直後にプロセス優先度を "high" に設定しようとしますが、権限不足や未対応プラットフォームでは警告を出してスキップされます。
- .env の自動読み込みはプロジェクトルートが検出できない場合や KABUSYS_DISABLE_AUTO_ENV_LOAD を設定した場合はスキップされます。
- run_monitoring は MONITOR_POLL_INTERVAL の不正な値（0 以下や整数でない文字列）をログ警告して既定の 60 秒にフォールバックします。
- run_execution は paper_trading 環境時に本番 DB と分離して paper_trading 用 DB を利用します。MockBroker の利用等は BrokerClientFactory の実装に依存します。
- logging_setup はログディレクトリ作成失敗時にファイル出力を無効化し、標準出力のみでログ出力を継続します。
- Portfolio / Position sizing では lot_size（単元）単位で丸められ、available_cash を超えた場合はスケールダウンと端数調整を行います。

開発者向け補足
- config._find_project_root() は __file__ の親ディレクトリを探索してプロジェクトルートを特定するため、パッケージ配布後もカレントワーキングディレクトリに依存せず動作することを意図しています。
- .env のパースはシェル風のクォートとエスケープ、インラインコメント（空白直前の # をコメントとして扱う）に対応しています。詳細は src/kabusys/config.py のロジック参照。

今後の予定（未実装 / 検討事項）
- position_sizing の価格フォールバック戦略（価格欠損時の前日終値や取得原価の利用）。
- strategy/research 部分のファクター群実装の完成と単体テスト整備。
- BrokerClient のモック/実装分離の明確化とテスト用フックの追加。
- ドキュメント整備（API リファレンス・運用手順書等）。

--- 

注: 本 CHANGELOG は提供されたコードベースから推測して作成しています。実際のリリースノートはプロジェクトのリリースポリシーや変更履歴管理に基づいて調整してください。