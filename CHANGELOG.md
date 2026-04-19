# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠して記載しています。  
バージョンタグはパッケージ内の `__version__`（現在: 0.1.0）に合わせています。

注: 日付はこのリリースを推定した日付です（リポジトリの実際のリリース日がある場合は置き換えてください）。

## [Unreleased]

## [0.1.0] - 2026-04-19

### Added
- プロジェクト初期実装（KabuSys 自動売買システムの基本コンポーネントを追加）
  - パッケージメタ情報
    - src/kabusys/__init__.py にバージョン `0.1.0` を追加。

  - 環境設定 & 管理
    - .env 自動読み込み機能を実装（プロジェクトルート検出: .git または pyproject.toml を基準）。
    - .env パーサを実装（クォート、エスケープ、コメント処理をサポート）。
    - Settings クラスを追加（環境変数経由で設定取得、必須チェック、各種デフォルト、環境判定ユーティリティを提供）。
    - 自動読み込みを無効化するための環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD` サポート。

  - 設定関連 CLI
    - 環境設定ウィザード: `kabusys.config_setup`（対話的に `.env` を作成・更新する機能を提供）。
    - 設定検証ツール: `kabusys.validate_config`（.env と config/*.yaml の存在・簡易整合性チェック、`--strict` オプションで警告を失敗扱いに可能）。

  - 起動スクリプト
    - 監視ループ起動: `run_monitoring.py`
      - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
      - 監視は常に本番用 sqlite のパスを使用（環境に依存せず）。
      - stop flag ファイル検知でループ終了。
      - DuckDB 接続サポート。
      - SystemMonitor 初期化・1回実行チェック (`check_once`) の呼び出しとエラーハンドリング。
      - プロセス優先度を起動時に "high" に設定。

    - 実行エンジン起動: `run_execution.py`
      - KABUSYS_ENV が `paper_trading` の場合は Paper Trading 用 DB（`data/paper_trading.db`）を使用して本番 DB と分離。
      - BrokerClientFactory を利用してブローカークライアント生成（環境に応じて Mock を使い分ける設計）。
      - OrderRepository / OrderManager / RiskManager / Reconciler / ExecutionEngine の組み立てと起動制御。
      - stop flag と PID ファイル管理、スレッドでのエンジン実行と安全シャットダウン処理。
      - プロセス優先度を起動時に "high" に設定。

  - ポートフォリオ構築（純粋関数群）
    - portfolio_builder:
      - 候補選定（スコア降順、タイブレークロジック）`select_candidates`
      - 等金額配分 `calc_equal_weights`
      - スコア加重配分 `calc_score_weights`（スコア全て 0 の場合は等分にフォールバック）
    - risk_adjustment:
      - セクター集中制限適用 `apply_sector_cap`（既存ポジションのセクター比率に基づいて候補を除外）
      - レジームに応じた乗数 `calc_regime_multiplier`（"bull"/"neutral"/"bear" をサポート、未知レジームは警告と共にフォールバック）
    - position_sizing:
      - 発注株数計算 `calc_position_sizes`
        - allocation_method: "risk_based" / "equal" / "score" をサポート
        - lot_size 単位の丸め、per-stock / aggregate cap、cost_buffer（手数料・スリッページ考慮）に基づくリスケーリングロジックを実装
        - 空価格や欠損データに対するログ出力でスキップ処理

  - レポート・解析ツール
    - Paper Trading 検証レポート生成スクリプト `tools/paper_verification_report.py`
      - システム安定性（稼働率）、注文成功率、送信率、リスク却下数、API レイテンシ（平均 / 最大 / P95）を集計・判定。
      - パス/フェイル基準（稼働率、成功率、送信率、P95 レイテンシ）を定義。
      - コマンドライン引数 `--from` / `--to` / `--db` をサポート。

  - 研究用ファクター計算（骨組み）
    - research/factor_research.py を追加（Momentum, Value, Volatility, Liquidity ファクター計算を意図）。
    - DuckDB 接続を受け SQL + Python で計算する方針と定数群を実装開始（calc_momentum 等の実装の着手あり、続きを要実装）。

  - ユーティリティ
    - ロギング設定ユーティリティ `utils/logging_setup.py`
      - StreamHandler（stdout）と TimedRotatingFileHandler（日次、30 日保持）をルートロガーに設定。
      - LOG_LEVEL / LOG_DIR の解決順、ハンドラの重複防止を考慮。
      - ファイル出力失敗時にコンソール出力へフォールバック。
    - プロセス優先度・CPU affinity ユーティリティ `utils/process_priority.py`
      - Windows / POSIX の差分を吸収してプロセス優先度を設定（psutil を利用）。
      - CPU affinity を最初の N コアへ設定する関数を提供。
      - 権限不足や未対応 OS の場合は警告を出してスキップ。

  - DB 初期化フック
    - 監視用 DB テーブルが存在しない場合に備え、起動時に `init_monitoring_db` を呼び出して冪等に初期化を保証（monitoring 側の DB 初期化ユーティリティを利用）。

### Changed
- （初期リリースのため該当なし）

### Fixed
- （初期リリースのため該当なし）

### Removed
- （初期リリースのため該当なし）

### Notes / Known issues / TODO
- research/factor_research.py は実装途中（ファイル末尾が切れている/未完成の箇所があるため、calc_momentum 等の完全実装を要する）。
- apply_sector_cap 内で price が 0.0 の場合に exposure を過少見積もる旨の TODO コメントあり — 前日終値等のフォールバックを将来的に検討予定。
- position_sizing の lot_size は現状グローバル固定（将来的に銘柄別 lot_map への拡張を検討）。
- Settings のプロパティで不正な環境変数があると ValueError を送出するため、起動時に例外を投げる設計になっている点に注意（運用上は validate_config を事前実行することを推奨）。
- run_monitoring は監視用 DB を「環境にかかわらず本番 sqlite_path を使用する」設計（意図的な設計だが、誤設定に注意）。
- run_execution は paper_trading モードで DB を分離するが、DuckDB は共有パスを使用する設計になっている（必要に応じて分離を検討）。
- ログディレクトリ作成や優先度設定には OS 権限依存の処理が含まれるため、権限不足時はフォールバック動作（警告）となる。

### Dependencies（主な外部依存）
- psutil（プロセス優先度 / CPU affinity）
- duckdb（分析用 DB 接続）
- sqlite3（標準ライブラリ）
- （オプション）PyYAML（config/*.yaml の検証で利用可能）

---

参照:
- 起動スクリプト: python -m kabusys.run_monitoring, python -m kabusys.run_execution
- 設定関連: python -m kabusys.config_setup, python -m kabusys.validate_config
- レポート: python -m kabusys.tools.paper_verification_report

（必要であれば、各ファイルの変更差分・コミットメッセージ風の詳細なリストも生成できます。どの粒度で記載するかご指示ください。）