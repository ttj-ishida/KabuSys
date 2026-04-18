# Changelog

すべての変更は Keep a Changelog の形式に従います。  
このプロジェクトの初回公開リリースを記録しています。

## [0.1.0] - 2026-04-18

### 追加
- 基本バージョン情報を追加
  - パッケージバージョンを `__version__ = "0.1.0"` として定義（src/kabusys/__init__.py）。

- 起動スクリプト
  - run_monitoring: SystemMonitor のポーリングループを起動するスクリプトを追加（src/kabusys/run_monitoring.py）。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止はプロジェクト内 data/stop_requested.flag ファイルで制御。
    - 監視用 DB は KABUSYS_ENV にかかわらず本番用 sqlite_path を使用する実装。
  - run_execution: ExecutionEngine を起動するスクリプトを追加（src/kabusys/run_execution.py）。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 専用 SQLite（data/paper_trading.db など）を使用し、本番 DB と完全分離。
    - 起動時に data/execution.pid を使用して PID を管理、停止は data/stop_requested.flag で制御。
    - BrokerClientFactory によるブローカークライアント生成、OrderManager / RiskManager / Reconciler と組み合わせて ExecutionEngine を起動。

- 設定管理
  - Settings クラスを実装（src/kabusys/config.py）
    - .env の自動ロード機構（プロジェクトルート検出: .git / pyproject.toml を基準）。
    - 自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD` により無効化可能。
    - 各種設定プロパティを実装（J-Quants、kabu API、LINE、DuckDB/SQLite パス、Paper Trade の挙動、監視しきい値、env/log_level 判定など）。
    - PAPER_FILL_MODE, PAPER_TRADING_SQLITE_PATH 等の paper_trading 用設定をサポート。
    - PID ファイル・kill flag 周りのパス設定、しきい値（CPU/MEM/DISK）など。

- 設定ユーティリティ / CLI
  - .env 対話ウィザード（src/kabusys/config_setup.py）
    - .env の初期作成・更新を対話式で支援。既存値の再利用、シークレットのマスク表示、保存確認など。
    - デフォルト値・選択肢を持つ項目を定義（KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, LOG_LEVEL, KILL_FLAG_CLEAR_ON_START 等）。
  - 設定検証 CLI（src/kabusys/validate_config.py）
    - 環境変数や config/*.yaml の存在・簡易検証を行う。
    - --strict オプションで警告を失敗扱いにできる。
    - PyYAML が未インストールの場合は YAML の検証をスキップして警告。
    - 本番環境（KABUSYS_ENV=live）向けの追加ガード（LINE 通知設定や KILL_FLAG_CLEAR_ON_START の危険性に対する警告）。

- ロギング / プロセスユーティリティ
  - 統一的なロギング設定ユーティリティを追加（src/kabusys/utils/logging_setup.py）
    - ルートロガーに StreamHandler (stdout) と TimedRotatingFileHandler（日次ローテーション、既定30日保持）を設定。
    - LOG_LEVEL / LOG_DIR / 引数で上書き可能。ハンドラの二重設定を防止。
    - ファイル出力失敗時はコンソール出力のみにフォールバック。
  - プロセス優先度 / CPU affinity ユーティリティを追加（src/kabusys/utils/process_priority.py）
    - set_process_priority(level) で Windows/Linux/macOS を吸収して優先度設定を試行（high/normal/low）。
    - set_cpu_affinity(cpu_count) で最初の N コアに固定する機能を提供。
    - 権限不足や未対応 OS の場合は警告ログを出してスキップ。

- ポートフォリオ構築関連（純関数群、DB 参照なし）
  - Portfolio builder（src/kabusys/portfolio/portfolio_builder.py）
    - select_candidates: BUY シグナルのスコアでソートして上位 N を選択。
    - calc_equal_weights / calc_score_weights: 等配分・スコア加重の重み計算。全スコアが 0 の場合は等配分にフォールバックして警告。
  - セクター制限 / レジーム乗数（src/kabusys/portfolio/risk_adjustment.py）
    - apply_sector_cap: セクター集中上限チェックと候補除外ロジック。unknown セクターは制限適用なし。
    - calc_regime_multiplier: market regime に応じた資金乗数（bull:1.0, neutral:0.7, bear:0.3、未知は 1.0 でフォールバック）。
  - ポジションサイジング（src/kabusys/portfolio/position_sizing.py）
    - calc_position_sizes: allocation_method (risk_based / equal / score) に対応した株数計算。lot_size（単元）丸め、個別上限・集計上限（available_cash）を考慮するスケーリングロジックを実装。
    - cost_buffer（手数料・スリッページ見積）を用いた保守的評価、残余キャッシュを使った端数配分ロジックを実装。

- Paper Trading 検証ツール
  - paper_verification_report（src/kabusys/tools/paper_verification_report.py）
    - Paper Trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）からデータを集計し、稼働率・注文成功率・送信率・レイテンシ（P95）などの指標を出力する CLI。
    - デフォルト閾値（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200ms）を定義して PASS/FAIL 判定を出力。
    - --from / --to / --db オプションで期間や DB を指定可能。

- データ分析（研究）モジュール
  - factor_research（src/kabusys/research/factor_research.py）
    - momentum / volatility / value / liquidity 等のファクター計算方針と定数を導入。DuckDB 接続を受けて prices_daily / raw_financials を参照する設計。
    - モメンタム計算関数（calc_momentum）などの実装が導入されている（実装途中の箇所あり）。

- パッケージエクスポート
  - portfolio モジュールから主要関数を再エクスポートして使いやすくした（src/kabusys/portfolio/__init__.py）。

### 変更
- N/A（初回リリースのため変更履歴はありません）

### 修正
- N/A（初回リリースのため修正履歴はありません）

### 注意事項 / 既知の制約
- run_monitoring は「監視用 DB を環境にかかわらず本番 sqlite_path を使う」実装になっています。開発環境で監視 DB を分離したい場合は設定やコードの修正が必要です。
- .env の自動ロードはプロジェクトルート検出に依存（.git または pyproject.toml）。パッケージ配布後や特殊なディレクトリ構成では自動ロードが働かない可能性があります。自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- process_priority / cpu_affinity は権限やプラットフォームに依存します。設定に失敗した場合は警告ログを出して処理を続行します。
- factor_research の一部（calc_momentum の続きなど）は実装途中の箇所が含まれます。研究用モジュールは今後の反復で完成させる予定です。
- config_setup により生成される .env はセキュリティ上必ず Git 等にコミットしないでください（ファイル先頭に注意喚起コメントを出力）。

---

今後の予定（例）
- factor_research の実装完了・テスト追加
- SystemMonitor / ExecutionEngine 周りの結合テスト・文書化
- 単体テスト・CI の導入とカバレッジ整備

もし CHANGELOG に追記してほしい点（例えば重要な設計判断や想定ワークフローなど）があれば指示ください。