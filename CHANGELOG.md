CHANGELOG
=========

すべての重要な変更はこのファイルに記録します。本プロジェクトでは Keep a Changelog のフォーマットに従い、セマンティックバージョニングを採用します。

[Unreleased]
------------

- ドキュメントや細かな改善は今後のリリースで追加予定です。

[0.1.0] - 2026-04-18
-------------------

初回公開リリース。自動売買システム KabuSys の基本機能群を実装しました。

Added
- 実行エントリ
  - run_execution.py: ExecutionEngine を起動する CLI スクリプトを追加。
    - KABUSYS_ENV=paper_trading 時は MockBrokerClient を利用し、paper_trading 専用 SQLite（デフォルト data/paper_trading.db）に記録して本番 DB と分離。
    - 起動時にプロセス優先度を "high" に設定するフックを追加。
    - 停止制御: data/stop_requested.flag の存在を監視して安全に停止。起動時の PID ファイル data/execution.pid を扱う。
    - ExecutionEngine の依存コンポーネント（BrokerClient、OrderRepository、OrderManager、RiskManager、Reconciler）を組み立ててスレッドで実行する。
    - RiskManager の既定設定（max_position_pct=0.20, max_utilization=0.80 等）を導入。

  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバックして警告表示。
    - Monitoring は環境に関係なく本番 sqlite_path を使用して監視データを記録。
    - 停止フラグファイル（data/stop_requested.flag）でループ終了。

- 設定管理 / CLI
  - config.py: 設定読み込み・管理機能を実装。
    - .env/.env.local の自動ロード（OS 環境変数優先）。KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応。
    - .env 行パーサの実装（export 形式、クォート/エスケープ、インラインコメントの取り扱いを考慮）。
    - Settings クラスで環境変数をラップ（データベースパス、PID/kill flag パス、閾値、PAPER_FILL_MODE の検証など）。
  - config_setup.py: .env 初期作成・更新ウィザードを対話式で実装（保存時に .env へ書き出し）。シークレット入力のマスク、既存値の再利用をサポート。
  - validate_config.py: 起動前設定検証 CLI を実装。
    - 必須環境変数チェック、KABUSYS_ENV の妥当性チェック、DB パスの親ディレクトリ確認、config/*.yaml の存在および YAML パースチェック（PyYAML 有無で挙動分岐）。
    - --strict オプションで警告も失敗扱いにできる。

- データ分析 / レポート
  - tools/paper_verification_report.py: Paper Trading 向けの検証レポート生成ツールを追加。
    - 稼働率、注文成功率（Filled/Created）、送信率（Sent/Created）、P95 レイテンシなどを算出し PASS/FAIL 判定。
    - デフォルト閾値を定義（稼働率 99%、注文成功率 90%、送信率 95%、P95 レイテンシ 200ms）。
    - 日付フィルタ（--from / --to）と DB パス指定（--db / 環境変数）に対応。テーブル欠損時は安全にデフォルト値で扱う。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - select_candidates: BUY シグナルをスコア降順で選定（タイブレークに signal_rank を使用）。
    - calc_equal_weights / calc_score_weights: 等金額配分とスコア加重配分を実装（全銘柄スコアが 0 の場合は等配分にフォールバックし警告）。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中上限をチェックして候補をフィルタ（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: 市場レジームに応じた投入資金乗数（bull/neutral/bear）を実装。未知レジームは 1.0 にフォールバックして警告表示。
  - portfolio/position_sizing.py
    - calc_position_sizes: 発注株数決定ロジックを実装（risk_based / equal / score に対応）。
    - 単元株（lot_size）で丸め、aggregate cap（available_cash）超過時のスケーリング、残余の端数配分ロジックを実装。
    - cost_buffer による保守的コスト見積りを考慮。

- リサーチ（DuckDB 統合）
  - research/factor_research.py（モジュール化：モメンタム / ボラティリティ等のファクター計算）
    - DuckDB 接続を受け取り SQL と Python で高速にファクターを算出（prices_daily / raw_financials テーブル参照）。
    - calc_momentum、calc_volatility 等の実装（移動平均・リターン・ATR・出来高指標など。データ不足時は None を返す設計）。

- ユーティリティ
  - utils/process_priority.py
    - set_process_priority: Windows / POSIX の差を吸収してプロセス優先度を設定（psutil 利用、未対応 OS はスキップして警告）。
    - set_cpu_affinity: 指定コア数にプロセスをピン留めする補助関数（アクセス権限や未実装 API を考慮して安全にスキップ）。
    - 例外と権限不足は警告ログに落とす実装。

Changed
- 初回リリースにつき「変更」はなし（新規実装）。

Fixed
- 初期実装での耐障害性を考慮
  - DB テーブルが存在しない場合のレポート生成や監視ループの例外処理を追加（OperationalError 等の扱いで安全に挙動）。
  - 環境変数パースの堅牢化（quoted value のエスケープ処理・コメント判定）。

Security
- .env ファイルの注意書きを config_setup.py のヘッダに明示（絶対に Git にコミットしないこと）。
- シークレット項目はウィザード表示時にマスク表示。

Notes / Known issues / TODO
- portfolio/risk_adjustment.apply_sector_cap:
  - price が欠損（0.0）の場合、セクターエクスポージャーが過少評価されうる。将来的に前日終値や取得原価でのフォールバックを検討する旨を TODO として記載。
- position_sizing:
  - 現状 lot_size は全銘柄共通（デフォルト 100）。将来的に銘柄別 lot_map を受け取る拡張を想定している。
- research/factor_research:
  - calc_volatility 等の実装は複雑なウィンドウ集計を行うため、DuckDB の存在（および prices_daily/raw_financials テーブルの整備）が前提。
- process_priority / set_cpu_affinity:
  - 権限不足や未対応 OS では設定がスキップされる。診断のためログ出力は残るが、期待通りに動作しない場合は環境依存の問題を確認すること。
- Monitoring:
  - run_monitoring は monitoring 用 DB を環境にかかわらず本番 sqlite_path に接続する設計になっているため、テスト目的で分離したい場合は手動でパスを調整する必要がある。

Authors
- KabuSys 開発チーム（コード内 docstring を基に自動生成）

ライセンスや貢献方法についてはリポジトリの README を参照してください。