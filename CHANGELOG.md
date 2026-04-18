CHANGELOG
=========

すべての注目に値する変更はこのファイルに記載します。
フォーマットは "Keep a Changelog" に準拠します。

Unreleased
----------
- （なし）

[0.1.0] - 2026-04-18
--------------------
初回リリース。以下の主要機能・実装を含みます。

Added
-----
- 実行用スクリプト
  - run_execution.py
    - ExecutionEngine を起動するエントリポイントを実装。
    - KABUSYS_ENV が paper_trading の場合は paper_sqlite_path（data/paper_trading.db がデフォルト）を用いて本番 DB と分離。
    - BrokerClientFactory によりブローカークライアントを動的生成（MockBrokerClient を含む想定）。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine を起動。スレッドでエンジンを実行し、 data/stop_requested.flag の検出で安全に停止。
    - engine の PID を data/execution.pid に記録する想定（pid_file を利用）。
    - RiskManager に対するデフォルト構成を定義（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）。initial_portfolio_value は broker.get_available_cash() から初期化。

  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを実装。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。不正な値は警告を出してデフォルトにフォールバック。
    - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する（監視用 DB を統一）。
    - 起動時にプロセス優先度を "high" に設定（set_process_priority）。
    - data/stop_requested.flag の存在でループを終了。KeyboardInterrupt もハンドリング。

- 設定管理
  - config.py
    - .env 自動ロード機能を実装（プロジェクトルートを .git または pyproject.toml で探索）。
    - .env の読み込み順序: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
    - .env の行パーサは export プレフィックス、クォート、バックスラッシュエスケープ、インラインコメントを考慮した堅牢な実装。
    - Settings クラスで各種設定値をプロパティ経由で取得。値のバリデーション（PAPER_FILL_MODE、KABUSYS_ENV、LOG_LEVEL 等）を実装。
    - paper_trading 用の PAPER_TRADING_SQLITE_PATH / PAPER_FILL_MODE サポート、pid/kill flag パス、閾値設定（CPU/MEM/DISK）等を提供。

  - config_setup.py
    - 対話式ウィザードで .env を初期作成・更新する CLI を実装。
    - 入力の既存値表示（シークレットはマスク）、選択肢サポート、保存確認、.env のテンプレート書き出しを実装。

  - validate_config.py
    - 起動前に環境変数や config/*.yaml の設定不備を検出する CLI を実装。
    - 必須/任意の環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在チェック、YAML ファイルの存在確認および PyYAML が利用できる場合はパース検査を実施。
    - KABUSYS_ENV=live 時の追加ガード（LINE 通知未設定や KILL_FLAG_CLEAR_ON_START の警告）を実装。
    - --strict オプションで警告を FAIL 扱いにできる。

- ポートフォリオ構築関連（純粋関数群、DB 参照なし）
  - portfolio/portfolio_builder.py
    - BUY シグナルの候補選定 select_candidates（スコア降順、同点は signal_rank のタイブレーク）。
    - 等重配分 calc_equal_weights、スコア加重配分 calc_score_weights（スコア合計が 0 の場合は等重にフォールバック）。

  - portfolio/risk_adjustment.py
    - セクター集中制限 apply_sector_cap（既存保有のセクター比率が閾値を超える場合は新規候補から除外。unknown セクターは除外対象外）。
    - 市場レジームに応じた資金乗数 calc_regime_multiplier（bull/neutral/bear のマップと未定義時のフォールバック）。

  - portfolio/position_sizing.py
    - ポジションサイズ計算 calc_position_sizes
      - allocation_method: "risk_based" / "equal" / "score" をサポート。
      - risk_based: portfolio_value・risk_pct・stop_loss_pct に基づく株数算出。
      - equal/score: 重みと max_utilization に基づく配分。
      - 単元株（lot_size）丸め、per-position 上限、aggregate cap（利用可能現金 available_cash を超えた場合のスケーリング）を実装。
      - cost_buffer を利用した保守的コスト見積り、スケーリング後の残差を用いた優先的な追加配分ロジック（lot 単位）を実装。

- 監視・検証ツール
  - tools/paper_verification_report.py
    - Paper Trading 用検証レポート生成スクリプトを実装。
    - system_status, trade_logs, risk_logs テーブルから稼働率、注文成功率、送信率、リスク却下数、レイテンシ（平均/最大/P95）を集計。
    - 閾値（稼働率 99%、成功率 90%、送信率 95%、P95 レイテンシ 200ms）に基づく PASS/FAIL 判定を実装。
    - コマンドライン引数 --from / --to / --db をサポート。

- ユーティリティ
  - utils/logging_setup.py
    - 統一的なログ初期化関数 setup_logging を実装。
    - stdout への StreamHandler と日次ローテーション（TimedRotatingFileHandler、30 日保持）をルートロガーに設定。既存ハンドラは一旦クリア。
    - LOG_DIR 作成失敗時はファイル出力をスキップしてコンソール出力のみ継続。
    - LOG_LEVEL の解決順（引数 > 環境変数 > デフォルト）を実装。

  - utils/process_priority.py
    - Windows / POSIX（Linux, macOS, FreeBSD）の差分を吸収してプロセス優先度を設定する set_process_priority を実装（"high" / "normal" / "low"）。
    - CPU affinity を最初の N コアに固定する set_cpu_affinity を実装。
    - 権限不足や未対応プラットフォーム時は警告を出して処理をスキップ。

- パッケージ情報
  - __init__.py にて __version__ = "0.1.0" を定義。

Changed
-------
- （初回リリースのため該当なし）

Fixed
-----
- （初回リリースのため該当なし）

Security
--------
- （該当なし）

Notes / Known issues
--------------------
- config._find_project_root() は .git または pyproject.toml に依存しているため、配布後や特殊なレイアウトでは自動 .env ロードがスキップされる可能性がある。
- portfolio/risk_adjustment.apply_sector_cap 内の価格欠損時の挙動について TODO コメントあり（価格が 0 の場合にエクスポージャーが過少見積りされる可能性）。将来的にフォールバック価格の導入を検討予定。
- research/factor_research.py はファイル末尾で未完（途中で切れている）ため、ファクター計算の一部実装が未完了。今後実装を継続する必要あり。
- process_priority の優先度設定はプラットフォーム依存かつ権限要件があるため、失敗した場合は警告に留め処理を継続する設計。

Acknowledgements
----------------
- 本リリースでは、ロギング・設定管理・実行/監視ランナー・ポートフォリオ構築・リスク制御・検証レポート等、運用に必要な基盤機能を中心に実装しました。今後は戦略本体（シグナル生成・ファクター計算等）の完成、テストカバレッジの拡充、エラーハンドリング強化を進めます。