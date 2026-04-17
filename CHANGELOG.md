CHANGELOG
=========

すべての注目すべき変更を記録します。これは Keep a Changelog の形式に準拠しています。

フォーマット:
- 変更はセマンティックバージョニングに従って記載しています。
- 日付はリリース日を示します。

v0.1.0 - 2026-04-17
-------------------

Added
- 初回公開（ベース実装）として以下を追加しました。
  - 実行用スクリプト
    - run_execution.py
      - ExecutionEngine を起動するエントリポイント。
      - KABUSYS_ENV=paper_trading の場合に paper_trading 専用 SQLite（data/paper_trading.db）を使用し、MockBrokerClient を利用して本番 DB と分離。
      - エンジンの PID 管理、停止フラグ（data/stop_requested.flag）監視、デーモンスレッドでの実行制御を含む。
      - 起動直後にプロセス優先度を "high" に設定（utils.process_priority を利用）。
    - run_monitoring.py
      - SystemMonitor のポーリングループ起動スクリプト。
      - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き（デフォルト 60 秒）。不正値はデフォルトにフォールバック。
      - 監視用 DB は環境に依らず本番 sqlite_path を使用する設計（monitoring テーブル初期化含む）。
      - 停止フラグ検知時に安全にループを終了し、DB 接続をクローズする。

  - 設定関連
    - config.py
      - .env 自動ロード機能（プロジェクトルートを探して .env および .env.local を読み込み）。
      - _find_project_root により __file__ からプロジェクトルートを特定（.git / pyproject.toml を基準）。
      - .env パースの堅牢化:
        - export KEY=val 形式対応、シングル／ダブルクォート内のバックスラッシュエスケープ処理、インラインコメントの取り扱い改善。
      - Settings クラスにより環境変数をプロパティとして提供（パスや閾値・フラグのデフォルト・バリデーション含む）。
      - PAPER_FILL_MODE の妥当性チェック、paper_trading 用 sqlite パス、各種閾値 (CPU/MEM/DISK) 等を定義。

    - config_setup.py
      - 対話式ウィザードで .env の初期作成／更新を支援。
      - 入力補助（選択肢、デフォルト値、シークレットマスク表示）、既存 .env の読み込み、最終確認後書き込みを実装。
      - .env 出力テンプレートを用意（Git にコミットしない旨のヘッダを含む）。

    - validate_config.py
      - 起動前検証 CLI を提供。
      - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性検証、DB パスの親ディレクトリ存在チェック、config/*.yaml の有無・パース検証（PyYAML がある場合）。
      - --strict モードで警告も失敗扱いにできる。
      - 本番環境 (KABUSYS_ENV=live) 向けの追加ガード（LINE 通知設定未設定や KILL_FLAG_CLEAR_ON_START の危険値検出）。

  - ポートフォリオ構築ライブラリ（純粋関数群）
    - portfolio/portfolio_builder.py
      - select_candidates: スコア降順＋タイブレークで候補選定。
      - calc_equal_weights / calc_score_weights: 等配分・スコア加重配分（全スコア 0 の場合はフォールバック）。
    - portfolio/risk_adjustment.py
      - apply_sector_cap: セクター集中上限に基づく候補除外ロジック（sell_codes を除外に含める等）。
      - calc_regime_multiplier: 市場レジームに応じた資金乗数（bull/neutral/bear のマップ、未知レジームはフォールバックで警告）。
    - portfolio/position_sizing.py
      - calc_position_sizes: risk_based / equal / score の割当方式を実装。単元株（lot_size）丸め、per-stock 上限、aggregate cap（available_cash）を考慮したスケールダウンと端数処理ロジックを実装。
      - cost_buffer により手数料・スリッページを保守的に見積もる。

  - 実行時ユーティリティ
    - utils/process_priority.py
      - プラットフォームを吸収してプロセス優先度（Windows: priority class、POSIX: nice 値）を設定するヘルパー。
      - set_cpu_affinity を追加し、プロセスを最初の N コアに固定可能（存在しない環境では安全にスキップ）。
      - 権限不足や未サポート環境に対するフォールバック／警告処理。

  - 研究用 / 分析用
    - research/factor_research.py
      - DuckDB 接続を用いたファクター計算モジュール（Momentum / Volatility / Liquidity 等）。
      - mom_1m/3m/6m、MA200 乖離、ATR、20日平均出来高などを SQL + Python で計算。
      - データ不足時の None 処理やウィンドウ行数チェックを含む。
    - DuckDB を主要な分析 DB として想定（config の duckdb_path を参照）。

  - ツール
    - tools/paper_verification_report.py
      - Paper Trading の検証レポート生成スクリプトを追加。
      - system_status / trade_logs / risk_logs から稼働率、注文成功率、送信率、レイテンシ（平均・最大・P95）などの指標を集計し、閾値（稼働率 99%、注文成功率 90%、送信率 95%、P95 200ms）で PASS/FAIL 判定を行う。
      - --from/--to/--db オプションで期間や DB を指定可能。
      - DB が存在しない・テーブル欠如時の堅牢なフォールバックを実装。

  - パッケージメタ
    - __init__.py にてパッケージ名と初版バージョン __version__ = "0.1.0" を設定。
    - package のエクスポート（portfolio モジュール等）を __all__ で整理。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Deprecated
- （初回リリースのため該当なし）

Removed
- （初回リリースのため該当なし）

Security
- （初回リリースのため該当なし）

Notes / 実装上の注意
- .env の自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。プロジェクトルートが検出できない場合は自動ロードをスキップします。
- run_execution / run_monitoring は起動時にプロセス優先度を上げようとしますが、権限不足の場合は警告を出して処理を継続します。
- position_sizing や risk_adjustment のロジックは PortfolioConstruction.md / StrategyModel.md に基づく設計注記を含み、将来的な拡張（銘柄別 lot_size 等）を想定しています。
- Paper Trading と本番 DB は意図的に分離されており、paper_trading 環境での誤操作リスクを低減しています。

今後の予定（抜粋）
- YAML ベースの config ファイル群のより詳細なバリデーションとサンプル生成スクリプトの充実化。
- 銘柄別 lot_size サポート、価格フォールバックロジック（price 欠損時の扱い改善）。
- ExecutionEngine / SystemMonitor の追加メトリクスや監視アラートの実装強化。

--- 

（以上）