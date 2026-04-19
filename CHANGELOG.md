# Changelog

すべての変更は「Keep a Changelog」形式に従っています。  
慣例: 変更は重要度ごとにカテゴリ分け（Added, Changed, Fixed, Deprecated, Removed, Security）しています。

## [Unreleased]

- （現時点で未リリースの変更はありません）

## [0.1.0] - 2026-04-19

### Added
- 初期リリースとして KabuSys のコアユーティリティとランタイムコンポーネントを追加。
  - パッケージ情報
    - src/kabusys/__init__.py にバージョン定義 __version__ = "0.1.0" を追加。
  - 環境設定 / 設定管理
    - src/kabusys/config.py
      - .env 自動読み込み機能（.env, .env.local、OS環境変数優先）を実装。プロジェクトルートの検出は .git または pyproject.toml を探索。
      - 環境変数のパースロジックを独自に実装（export形式、クォートやコメントの扱い、エスケープ対応）。
      - Settings クラスを提供し、J-Quants / kabu API / DB パス /監視閾値 / 実行環境等の設定アクセスを統一。
      - 環境値のバリデーション（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE など）を実装。
  - 起動用スクリプト
    - src/kabusys/run_monitoring.py
      - SystemMonitor のポーリングループを起動するスクリプト。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト60秒）。
      - 監視用 DB は KABUSYS_ENV に依らず設定された本番 sqlite_path を使用する設計。
      - 停止フラグ（data/stop_requested.flag）検出、例外ハンドリング、DB接続のクリーンアップを実装。
    - src/kabusys/run_execution.py
      - ExecutionEngine 起動スクリプト。KABUSYS_ENV=paper_trading の場合は paper_trading 用の SQLite（data/paper_trading.db）を使用し、本番 DB と分離。
      - BrokerClientFactory を用いたブローカークライアント生成、OrderRepository/OrderManager/RiskManager/Reconciler/ExecutionEngine の組み立て。
      - 停止フラグ・PID ファイルの扱い、スレッドでのエンジン実行と優雅な停止処理を実装。
  - 設定支援ツール / 検証ツール
    - src/kabusys/config_setup.py
      - .env 初期作成・更新の対話ウィザード。主要な設定項目（KABUSYS_ENV、JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DBパス、LOG_LEVEL 等）を対話的に入力して .env を生成。
    - src/kabusys/validate_config.py
      - .env と config/*.yaml の事前検証用 CLI。必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL 値チェック、DBパスの親ディレクトリ確認、YAML の簡易パース検証を実装。
      - --strict オプションで警告を失敗扱いにできる。
  - ロギング／プロセス制御ユーティリティ
    - src/kabusys/utils/logging_setup.py
      - 共通のログ設定ユーティリティを実装。コンソール（stdout）と日次ローテーションファイル（TimedRotatingFileHandler）をルートロガーに設定。ログディレクトリ作成失敗時のフォールバックも考慮。
    - src/kabusys/utils/process_priority.py
      - Windows/Linux/macOS を吸収してプロセス優先度（high/normal/low）を設定するユーティリティ。CPU affinity を設定する関数も提供。権限不足や未対応 OS の扱いを考慮して安全にフォールバック。
  - ポートフォリオ構築関連（純関数群）
    - src/kabusys/portfolio/portfolio_builder.py
      - 候補選定（score 降順、signal_rank によるタイブレーク）、等金額配分、スコア加重配分を実装。スコアが全て 0 の場合は警告と等金額フォールバックを実装。
    - src/kabusys/portfolio/risk_adjustment.py
      - セクター集中制限（apply_sector_cap）と市場レジームに基づく乗数（calc_regime_multiplier）を実装。unknown セクターの扱い、ログ出力を含む。
    - src/kabusys/portfolio/position_sizing.py
      - リスクベース、等分配、スコア配分に基づく発注株数算定ロジックを実装。単元株（lot_size）丸め、ポジション上限、aggregate cap によるスケーリング、cost_buffer を考慮した保守的推定などを実装。
    - src/kabusys/portfolio/__init__.py で上記関数を公開。
  - リサーチ（ファクター計算）基盤（途中実装）
    - src/kabusys/research/factor_research.py
      - DuckDB を用いたファクター計算基盤を追加。Momentum / Value / Volatility / Liquidity の設計方針、定数、calc_momentum 等のインターフェースを実装（ファイル末尾は途中）。
  - ツール
    - src/kabusys/tools/paper_verification_report.py
      - Paper Trading 用の検証レポート生成ツールを追加。指定期間の system_status / trade_logs / risk_logs から稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）を集計して PASS/FAIL 判定（閾値はソースに定義）を行う。CLI 引数で期間・DB指定が可能。
  - その他
    - SQLite / DuckDB 接続の初期化フック（init_monitoring_db を各起動スクリプトで呼び出すことで監視テーブル作成を保証）。
    - 停止フラグ（data/stop_requested.flag）およびPIDファイルの扱いを統一的に管理。

### Changed
- （初期リリースのため該当なし）

### Fixed
- （初期リリースのため該当なし）

### Deprecated
- （初期リリースのため該当なし）

### Removed
- （初期リリースのため該当なし）

### Security
- （初期リリースのため該当なし）

---

注意:
- 設定値や動作はソース内の docstring / コメントに基づき推測して作成しています。実際の運用前に .env 設定、PID/stop フラグや DB のパス、paper_trading モード等を必ず確認してください。
- 今後のリリースでは research/factor_research の未完部分の実装、テスト追加、エラーハンドリングやリソース管理の強化が想定されます。