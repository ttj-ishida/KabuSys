CHANGELOG
=========

すべての重要な変更は Keep a Changelog の形式に従って記載しています。
日付はこのコードスナップショットの反映日として 2026-04-17 を使用しています。

Unreleased
----------
（なし）

[0.1.0] - 2026-04-17
--------------------

Added
- 初期リリース: KabuSys 自動売買システムのコアユーティリティと CLI を追加しました。
  - 実行・監視ランチャー
    - run_execution.py: ExecutionEngine の起動スクリプトを実装。
      - KABUSYS_ENV が paper_trading の場合は paper_trading 用 SQLite（デフォルト data/paper_trading.db）を使用して本番 DB と分離。
      - BrokerClientFactory を用いたブローカークライアント作成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、およびデーモンスレッドでの実行管理を提供。
      - 起動前に data/stop_requested.flag を確認し、フラグが立っていれば起動をスキップ。
      - 停止フラグを検知すると安全に engine.stop() を呼び出して終了。
    - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを実装。
      - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値は警告してデフォルトにフォールバック。
      - 監視は常に本番用 sqlite_path を使用して監視データを記録（環境に依存せず）。
      - data/stop_requested.flag による外部停止制御をサポート。
  - 設定管理
    - config.py: .env 自動読み込み機能（.env, .env.local）を追加。プロジェクトルートは .git または pyproject.toml を基準に探索。
      - export KEY=val 形式やクォート／エスケープ、行内コメントを扱うパーサ実装。
      - Settings クラスを提供し、J-Quants / kabu API / DB パス / 監視閾値等のプロパティを安全に取得可能。
      - KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロードを無効化可能。
  - 設定ユーティリティ
    - config_setup.py: 対話式ウィザードで .env の初期作成・更新を支援。
      - 入力プロンプト、既存値の再利用、シークレットのマスク表示、保存確認を実装。
    - validate_config.py: 起動前の設定検証 CLI を実装。
      - 必須環境変数の存在確認、プレースホルダ値チェック、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在／パースチェック（PyYAML があれば内容確認）を行う。
      - --strict モードで警告を FAIL 扱いにできる。
  - ポートフォリオ構築関連（純粋関数）
    - portfolio/portfolio_builder.py
      - select_candidates: BUY シグナルのスコアでソートして上位 N を選択。
      - calc_equal_weights / calc_score_weights: 等金額配分・スコア加重配分の計算（スコア全零時は等分にフォールバック）。
    - portfolio/position_sizing.py
      - calc_position_sizes: risk_based／equal／score の各配分方式を実装。単元株（lot_size）丸め、1 銘柄上限、aggregate cap（available_cash）超過時のスケーリングと残差処理を実装。
      - cost_buffer（手数料・スリッページ見積り）を考慮した保守的見積り。
    - portfolio/risk_adjustment.py
      - apply_sector_cap: セクター集中上限の判定と候補除外（"unknown" セクターは上限適用外）。
      - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear）を提供。未知レジームは警告を出して 1.0 にフォールバック。
  - ユーティリティ
    - utils/process_priority.py
      - set_process_priority: Windows / POSIX を吸収してプロセス優先度を設定。未対応 OS や権限不足時は警告してスキップ。
      - set_cpu_affinity: 指定コア数で CPU affinity を設定（利用不可時は警告）。
  - 解析 / 研究
    - research/factor_research.py
      - DuckDB 経由で Momentum / Volatility / Liquidity 等のファクターを計算する関数群を実装。ウィンドウ関数を活用し、データ不足時は None を返す設計。
  - ツール
    - tools/paper_verification_report.py
      - Paper Trading 用 SQLite を集計し、稼働率・注文成功率・送信率・レイテンシ（avg / max / P95）などの検証レポートを生成。
      - 基準（稼働率 99%、成功率 90%、送信率 95%、P95 ≤ 200ms）に基づく PASS/FAIL 判定を提供。
  - パッケージ情報
    - __init__.py にてバージョンを "0.1.0" として定義。

Changed
- ログ・起動挙動
  - run_execution/run_monitoring の起動時にプロセス優先度を "high" に設定する処理を追加（utils.process_priority.set_process_priority を使用）。
- DB 初期化
  - init_monitoring_db(sqlite_conn) を起動パスで呼ぶことで、監視テーブルの存在を冪等的に保証。

Fixed
- 環境変数パーサの堅牢化（config._parse_env_line）
  - export プレフィックス、クォート内のバックスラッシュエスケープ、行内コメントの取り扱いを正しく処理するよう修正。
- MONITOR_POLL_INTERVAL の安全な扱い（run_monitoring._get_poll_interval）
  - 0 以下や整数以外の値に対して警告を出してデフォルトにフォールバック。time.sleep に渡せない値による例外発生を回避。
- ExecutionEngine 起動の安全措置（run_execution）
  - 起動直前に停止フラグをチェックしているため、手動で停止状態のまま誤起動するのを防止。
- position_sizing のスケーリングと端数処理
  - aggregate cap 超過時のスケールダウン処理で再現性を保つためのソートキー安定化（code を二次キー）と残余キャッシュによる lot_size 単位の追加配分ロジックを実装。
- process_priority の例外ハンドリングを強化
  - AccessDenied / NotImplementedError 等を捕捉して警告ログを出力し、起動失敗にならないようにした。

Security
- 機密情報の扱い
  - config_setup のプロンプトでシークレットはマスクして表示。README 等で .env を Git にコミットしない旨を明記。

Deprecated
- なし

Breaking Changes
- なし（現時点で互換性を壊す変更は意図していません）

Notes / Known issues
- portfolio/risk_adjustment.apply_sector_cap: price_map に欠損（0.0）がある場合、エクスポージャーが過小評価される可能性があり TODO コメントでフォールバック価格の検討を記載しています。
- research/factor_research は DuckDB のテーブル構成（prices_daily / raw_financials）に依存します。テーブルスキーマが異なる場合は呼び出し側で整合させてください。
- validate_config は PyYAML が未インストールだと YAML 内容チェックをスキップし、警告を出します。CI 等で厳密に検証する場合は PyYAML の導入を推奨します。

Authors
-------
KabuSys 開発チーム

-----