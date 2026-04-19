CHANGELOG
=========

All notable changes to this project will be documented in this file.
This project adheres to "Keep a Changelog" とセマンティックバージョニングに従います。
（https://keepachangelog.com/ja/1.0.0/）

Unreleased
----------

- なし

0.1.0 - 2026-04-19
------------------

Added
- プロジェクト初回リリースを公開。
  - パッケージバージョン: `kabusys.__version__ = "0.1.0"`。

- 起動スクリプト
  - run_monitoring.py
    - SystemMonitor をポーリングする監視ループ起動スクリプト。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止はプロジェクト内の `data/stop_requested.flag` ファイル検知または KeyboardInterrupt により行う。
    - 監視用 DB は環境に関係なく本番の sqlite_path を使用する（監視テーブルの初期化を実施）。
    - DuckDB 接続を使用。

  - run_execution.py
    - ExecutionEngine を起動するスクリプト。
    - `KABUSYS_ENV=paper_trading` のときは MockBrokerClient を使用し、paper_trading 用 SQLite（`data/paper_trading.db`）に記録して本番 DB と分離。
    - 起動前に `data/stop_requested.flag` をチェックし、存在すれば起動を中止。
    - 実行中はスレッド監視により停止フラグ検知で Engine を安全に停止。PID ファイル (`data/execution.pid` など) をサポート。

- 設定管理
  - config.py
    - 環境変数 / .env 自動読み込み機能（プロジェクトルートを .git / pyproject.toml から探索）。
    - 自動読み込みは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
    - `.env` と `.env.local` の読み込み優先順位を実装（OS 環境変数を保護）。
    - Settings クラスを導入し、各種設定プロパティを提供（J-Quants / kabu API / DB パス / PID パス / 監視閾値 / 環境判定等）。
    - `PAPER_FILL_MODE`（"instant"|"partial"|"never"|"reject"）や `PAPER_TRADING_SQLITE_PATH` をサポート。
    - 環境値の妥当性検証（KABUSYS_ENV, LOG_LEVEL 等）を実装。

- 設定ユーティリティ / CLI
  - config_setup.py
    - 対話式ウィザードで `.env` を作成・更新する CLI を追加。
    - デフォルト値、選択肢、機密入力（マスク表示）などをサポート。
    - 生成される .env のテンプレート形式と注意書きを自動生成。

  - validate_config.py
    - 起動前に `.env` と config/*.yaml の妥当性を検証する CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV の検証、DB パスの親ディレクトリ存在チェック、YAML パース（PyYAML があれば）などを行う。
    - `--strict` オプションで警告もエラー扱いにできる。

- ポートフォリオ構築ライブラリ（純粋関数群）
  - portfolio.portfolio_builder
    - select_candidates: BUY シグナルをスコア降順でソートして上位 N を選択。
    - calc_equal_weights / calc_score_weights: 等金額配分およびスコア加重配分（スコア合計 0 の場合は等配分にフォールバック）。
  - portfolio.risk_adjustment
    - apply_sector_cap: セクター集中制限ロジック（既存保有に基づくセクターエクスポージャー計算と候補除外）。
    - calc_regime_multiplier: market レジームに応じた投下資金乗数（bull/neutral/bear のマッピング、未知値はフォールバックとワーニング）。
  - portfolio.position_sizing
    - calc_position_sizes: allocation_method（"risk_based" / "equal" / "score"）に応じた株数決定ロジックを実装。
    - lot_size（単元株）丸め、1銘柄上限・集計キャップ（aggregate cap）スケーリング、cost_buffer を用いた保守的評価、残差に対する追加配分アルゴリズムを実装。
    - 価格データ欠損時のスキップやログ出力の扱いを明示。

- 監視・検証ツール
  - tools.paper_verification_report.py
    - Paper Trading 用の検証レポート生成スクリプトを追加。
    - 指標: 稼働率 (uptime)、注文成功率（Filled/Created）、送信率（Sent/Created）、P95 レイテンシ等を算出。
    - デフォルトの閾値: 稼働率 >= 99%、成功率 >= 90%、送信率 >= 95%、P95 レイテンシ <= 200 ms。
    - 日付範囲フィルタ (--from / --to)、DB パス指定 (--db) 対応。
    - DB 存在チェックやテーブル欠如時に耐性を持つ実装。

- 研究用ファクターモジュール（下地）
  - research.factor_research
    - Momentum / MA / ATR / Volume 系の計算方針と定数を定義。DuckDB 接続を受け取り prices_daily / raw_financials テーブルから計算する設計。
    - 将来的なファクター計算関数の実装方針をドキュメント化。

- ユーティリティ
  - utils.logging_setup
    - 一貫したログ設定ユーティリティを提供。
    - StreamHandler を stdout に出力、TimedRotatingFileHandler による日次ローテーション（30 日保管）をサポート。
    - LOG_DIR の作成に失敗した場合にファイルハンドラをスキップするフォールバックを実装。
    - 既存ハンドラのクリーンアップ（重複防止）を実装。
  - utils.process_priority
    - Windows / POSIX の差分を吸収してプロセス優先度（high/normal/low）を設定するユーティリティを実装。
    - CPU affinity を最初の N コアに固定する set_cpu_affinity を提供（失敗時はワーニングでスキップ）。
    - アクセス権限や未対応 OS でのフォールバック処理を実装。

Changed
- ドキュメント化（コード内 docstring / コメント）を充実：
  - PortfolioConstruction / StrategyModel 等の設計参照セクションを明記し、各純粋関数の前提・制約をコメントで明示。
  - CLI の使い方と注意点をモジュール先頭 docstring に記載。

Fixed
- 環境変数パースの堅牢化
  - .env パーサでシングル／ダブルクォート、バックスラッシュエスケープ、インラインコメント扱いなどに対応。無効行や export プレフィックスを正しく無視するよう修正。
- run_monitoring の MONITOR_POLL_INTERVAL の不正値（0 や負、非整数）に対するフォールバック処理を追加。無効値検出時は警告を出してデフォルト (60 秒) を使用。

Notes / Implementation details
- DB 周り
  - DuckDB と SQLite を併用する設計。分析向けの DuckDB、トランザクション・監視向けに SQLite を利用。
  - 監視テーブルの初期化関数 init_monitoring_db が起動時に呼ばれる（冪等）。

- Paper Trading 分離
  - paper_trading モードでは paper 用 SQLite を使用し、本番データと完全に分離されることを想定。

- ログ
  - ログは stdout に出力されるため、タスクスケジューラや cron からの起動時にも扱いやすい設計。
  - ファイル出力は logs/<app_name>.log に日次ローテーションで保存。

- 安全ガード
  - 実行/監視プロセスはプロジェクト内の stop flag ファイルで外部から停止指示を受けられるように設計。
  - validate_config による事前チェックや config_setup による対話式設定で運用ミスを削減。

Security
- 本リリースでの既知のセキュリティ関連変更はなし。
- .env は絶対に Git にコミットしない注意喚起がウィザードに含まれます。

今後の予定（短期）
- research.factor_research の完全実装（ファクター計算ロジックの追加）。
- ExecutionEngine / SystemMonitor 周りの単体テスト強化。
- 銘柄別 lot_size 対応（stocks マスタ参照による拡張）。

-- end --