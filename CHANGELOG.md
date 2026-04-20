CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠しています。

Unreleased
----------

（なし）

0.1.0 - 2026-04-20
-----------------

Added
- 初期リリース。KabuSys の基本機能群を実装。
  - エントリポイント / 実行スクリプト
    - run_execution.py: ExecutionEngine 起動スクリプトを追加。  
      - KABUSYS_ENV=paper_trading 時は paper_trading 専用 SQLite（デフォルト data/paper_trading.db）を使用し、本番 DB と完全に分離。
      - 起動時にプロセス優先度を "high" に設定し、停止フラグ（data/stop_requested.flag）および PID ファイル（data/execution.pid）を扱う。
      - Engine を別スレッドで実行し、停止フラグ検知で安全に停止する仕組みを搭載。
    - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。  
      - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。無効値はデフォルトにフォールバックして警告を出力。
      - 監視は環境にかかわらず本番 sqlite_path を使用する（監視 DB を本番 DB として扱う想定）。
  - 設定管理
    - config.py: Settings クラス実装。環境変数・.env の自動読み込み機構を提供（プロジェクトルートを .git / pyproject.toml で探索）。  
      - .env のパースはシングル/ダブルクォート、エスケープ、インラインコメント等に対応。
      - 各種プロパティ（J-Quants、kabu API、DB パス、PID/kill フラグ、監視閾値、環境切替判定など）を提供し、値検証（例: PAPER_FILL_MODE、KABUSYS_ENV、LOG_LEVEL）を実行。
    - config_setup.py: 対話式ウィザードで .env を作成・更新する CLI を追加。既存 .env の読み込み、シークレットのマスク表示、保存確認を実装。
    - validate_config.py: 起動前の設定検証 CLI を追加。必須環境変数、KABUSYS_ENV、ログレベル、DB パス、config/*.yaml の存在・パースをチェック。--strict モードあり。
  - ポートフォリオ構築（メモリ内純粋関数群）
    - portfolio/portfolio_builder.py: 候補選定（スコア降順・タイブレークルール）、等金額配分、スコア加重配分を実装（スコア全0 の場合は等配分にフォールバック）。
    - portfolio/risk_adjustment.py: セクター集中制限（apply_sector_cap）と市場レジームに応じた乗数（calc_regime_multiplier）を実装。unknown セクターは上限適用除外。
    - portfolio/position_sizing.py: 発注株数決定ロジックを実装。
      - risk_based / equal / score の allocation_method をサポート。
      - 単元株（lot_size）丸め、1銘柄上限、aggregate cap（利用可能現金）に基づくスケーリングと残差配分ロジックを実装。
      - cost_buffer（手数料・スリッページ見積り）を加味した保守的見積り対応。
  - ユーティリティ
    - utils/logging_setup.py: 統一ログ設定ユーティリティ。  
      - stdout への StreamHandler と日次ローテーション（TimedRotatingFileHandler）を組み合わせて root ロガーを構成。既存ハンドラをクリアして二重設定を防止。ログディレクトリ作成失敗時はファイル出力をスキップして警告を出力。
    - utils/process_priority.py: プラットフォーム非依存のプロセス優先度設定および CPU affinity 設定関数を提供（Windows / POSIX 対応、失敗時は警告スキップ）。
  - 監視・検証ツール
    - monitoring.monitoring_db（初期化呼び出し箇所あり）との連携を実装（起動スクリプトから init を呼ぶ）。
    - tools/paper_verification_report.py: Paper Trading 用の検証レポート生成スクリプトを追加。  
      - 稼働率、注文成功率、送信率、リスク却下数、API レイテンシ（平均/最大/P95）を算出し、閾値（稼働率 99%、成立率 90% 等）に基づく PASS/FAIL 判定を行う。  
      - 日付範囲フィルタ、DB パスの CLI 指定 / 環境変数指定対応。
  - research/factor_research.py: ファクター計算モジュールの骨組み（モメンタム / MA200 / ATR / 流動性等）を追加（DuckDB 接続を受け SQL/Python で計算する設計）。
  - パッケージ情報
    - __init__.py にてバージョン __version__ = "0.1.0" を設定。

Changed
- ログ出力
  - logging_setup: 表準出力に stdout を使用するよう明示（cron 等のリダイレクト運用を想定）。ログディレクトリ作成に失敗しても起動継続。
- .env 自動読み込みのポリシー
  - config.py: 自動ロード順を OS 環境 > .env.local > .env（既存 OS 環境は保護）とし、プロジェクトルートが不明な場合は自動ロードをスキップする挙動に変更。
- run_monitoring.py
  - 監視プロセスは KABUSYS_ENV にかかわらず本番 sqlite_path を使用するよう明文化（監視 DB を本番 DB として扱う運用）。
- run_execution.py
  - paper_trading モードでは paper_sqlite_path を使用して本番 DB と完全分離する動作を実装。

Fixed
- 環境変数パーサ（config._parse_env_line）
  - クォート内のバックスラッシュエスケープやインラインコメントの扱いを改善し、より多くの .env 記述に対応。
- MONITOR_POLL_INTERVAL 処理
  - 整数パースおよび 0/負値の扱いを堅牢化し、無効な値はデフォルトにフォールバックして警告を出すようにした（time.sleep に渡す前の防御）。
- process_priority
  - OS 非対応時やアクセス権限不足での例外を捕捉して警告ログに落とすようにし、起動失敗にしないよう改良。
- position_sizing
  - 価格欠損時のスキップ、単元丸め、aggregate cap スケーリングと残差配分の安定化を実装。スケールダウン後の追加配分は残差が大きい順で再現性を保って割当てる。

Notes / Known limitations
- research/factor_research.py は計算ロジックの実装途中（ファイル末尾が途中で切れている箇所あり）。今後、DuckDB を用いたファクター計算ロジックの完成が必要。
- apply_sector_cap 内の注記: price が欠損（0.0）の場合にエクスポージャーが過少見積りされる可能性があり、将来的にフォールバック価格（前日終値等）を導入することを検討する旨の TODO が残っている。
- 単元株（lot_size）は現状ハードコード的に共通値（デフォルト 100）を想定している。将来的には銘柄別 lot_map へ拡張する計画。

Security
- （今回のリリースで特に扱うセキュリティ関連の変更はありません。環境変数にシークレットを保存する点については .env を絶対にコミットしない旨をドキュメントに明記しています。）

以上。README や Release ノートへの反映、ユニットテスト追加、未実装部分（factor_research の完成など）を次のタスクとして推奨します。