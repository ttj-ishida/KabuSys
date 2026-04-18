# Changelog

すべての重要な変更履歴をここに記録します。本ファイルは「Keep a Changelog」形式に準拠します。

現在のバージョン: 0.1.0

## [0.1.0] - 2026-04-18

### 追加
- 基本パッケージの初期実装を追加。
  - パッケージ情報:
    - src/kabusys/__init__.py にバージョン情報 __version__ = "0.1.0" を設定。

- 環境設定・読み込み機能を追加（src/kabusys/config.py）。
  - プロジェクトルートを .git / pyproject.toml を基準に自動検出し、.env / .env.local を読み込む自動ローダーを実装。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
  - .env の1行パースでクォート付き値、エスケープ、コメント、export 形式に対応。
  - Settings クラスを提供し、環境変数をラップ（J-Quants、kabu API、LINE、DBパス、監視・閾値、運用環境フラグ等をプロパティで取得）。
  - 各プロパティで妥当性チェックを行う（例: KABUSYS_ENV / LOG_LEVEL の有効値チェック、PAPER_FILL_MODE の許容値検証など）。
  - デフォルトパス:
    - DUCKDB_PATH: data/kabusys.duckdb
    - SQLITE_PATH: data/monitoring.db
    - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
    - PID_FILE_PATH: data/execution.pid

- 設定ウィザード CLI を追加（src/kabusys/config_setup.py）。
  - 対話式で .env の初期作成・更新が可能。
  - 入力ガイド、既存 .env の読み込み、シークレットマスク表示、保存キャンセル確認、.env 書き出しをサポート。
  - .env のテンプレートに注意書き（Git にコミットしないこと）を含めて出力。

- 設定検証 CLI を追加（src/kabusys/validate_config.py）。
  - 必須環境変数の存在チェック、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ確認、config/*.yaml の存在・パース検証（PyYAML があれば内容検証、未インストール時は警告）などを実施。
  - --strict オプションで警告も失敗扱い（exit(1)）にできる。

- 実行 / 監視用エントリポイントを追加。
  - 実行エンジン起動スクリプト（src/kabusys/run_execution.py）
    - プロセス優先度を High に設定して起動（utils.process_priority の呼び出し）。
    - KABUSYS_ENV=paper_trading の場合、専用の paper_trading 用 SQLite DB（settings.paper_sqlite_path）と MockBrokerClient を使い本番 DB と完全分離。
    - DuckDB と SQLite の接続を確立し、監視テーブルの初期化を行う。
    - Broker クライアント作成、OrderRepository / OrderManager / RiskManager / Reconciler / ExecutionEngine の組み立てを行い、スレッドで engine.run_session を実行。停止フラグ (data/stop_requested.flag) を監視して安全停止。
    - エンジン用の PID ファイル管理（data/execution.pid）を想定。
  - 監視ループ起動スクリプト（src/kabusys/run_monitoring.py）
    - プロセス優先度を High に設定。
    - Monitoring は環境にかかわらず本番 sqlite_path を使用して監視 DB を初期化。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値・0 以下はデフォルトにフォールバックし警告を出力。
    - 停止フラグによりループを終了。例外はログ出力して次のポーリングまで待機。

- モニタリング DB の初期化呼び出しポイントを追加（init_monitoring_db を run_* スクリプトで使用）。
  - monitoring 用のテーブル存在保証（冪等）を実装。

- Paper Trading 検証レポート生成ツールを追加（src/kabusys/tools/paper_verification_report.py）。
  - ペーパートレード用 SQLite（PAPER_TRADING_SQLITE_PATH）からデータを集計してレポート出力。
  - 指標:
    - 稼働率 (uptime)
    - 注文成功率 (fill rate)、送信率 (send rate)
    - リスク却下数
    - レイテンシ（avg / max / P95）
  - P95 計算、期間フィルタ (--from / --to)、--db オプションによる DB パス指定に対応。
  - 合格/不合格判定のしきい値を定義（例: uptime >= 99.0%、fill_rate >= 90%、P95 <= 200 ms など）。

- ポートフォリオ構築関連の純関数群を追加（src/kabusys/portfolio/*）。
  - portfolio_builder.py:
    - select_candidates: スコア降順・同点時 signal_rank による上位選抜。
    - calc_equal_weights: 等金額配分。
    - calc_score_weights: スコア正規化配分（全スコアが 0 の場合は等配分にフォールバック）。
  - risk_adjustment.py:
    - apply_sector_cap: 同一セクターの既存エクスポージャが上限を超える場合、新規候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: 市場レジーム (bull/neutral/bear) に応じた投下資金乗数の計算（未知のレジームは警告の上 1.0 でフォールバック）。
  - position_sizing.py:
    - calc_position_sizes: allocation_method ("risk_based", "equal", "score") に応じた発注株数計算。単元株丸め、1銘柄上限、aggregate cap によるスケーリング、cost_buffer を用いた保守的見積り、lot_size 単位での残差配分ロジックなどを実装。

- 研究用ファクター計算モジュールを追加（src/kabusys/research/factor_research.py）。
  - calc_momentum: mom_1m/mom_3m/mom_6m、MA200乖離（ma200_dev）を DuckDB の prices_daily テーブルから計算。
  - calc_volatility: ATR、相対ATR、20日平均売買代金、出来高比率等の算出（関数とSQLを組み合わせて実装）。
  - 計算ウィンドウやスキャンバッファ（例: 200日移動平均、ATR 20 日、スキャン範囲）は定数化。

- プロセス優先度 / CPU アフィニティユーティリティを追加（src/kabusys/utils/process_priority.py）。
  - set_process_priority(level): クロスプラットフォーム（Windows / POSIX）での優先度設定を試行。権限不足や非対応 OS の場合は警告を出力してスキップ。
  - set_cpu_affinity(cpu_count): プロセスを最初の N コアに固定する機能（未指定は全コア使用）。不正値検出と例外処理を実装。

### 変更（設計）
- 初期設計方針として、以下を採用:
  - DuckDB を分析用途、SQLite を監視／取引ログ用途に使い分け。
  - Paper Trading は本番 DB と分離（専用 SQLite）して安全に検証可能にする。
  - 設定は .env と環境変数で管理し、安全のため .env を Git 管理外にするドキュメントを明示。
  - 監視・実行プロセスは外部ファイル（stop_requested.flag, execution.pid）で簡単に制御できる仕組み。

### 既知の制限 / 注意点
- 一部の機能は外部ライブラリに依存（例: PyYAML がない場合は config/*.yaml の内容検証をスキップして警告）。
- process_priority の優先度設定や CPU affinity は OS と権限に依存し、失敗時は警告を出して続行する設計。
- portfolio/risk_adjustment.apply_sector_cap は price が欠損 (0.0) の場合にエクスポージャが過少見積もられる可能性がある旨を TODO コメントで示している（将来的なフォールバック価格の導入を検討）。
- calc_score_weights は全スコア 0 の場合に等金額配分へフォールバックし警告ログを出力する。

---

今後の見込み:
- 監視・実行の統合テスト、外部 API クライアントの実装（kabuステーション / J-Quants 連携）の追加、より詳細なエラーハンドリングと運用ドキュメントの整備を予定しています。