CHANGELOG
=========

すべての変更は Keep a Changelog の書式に従います。  
各リリースには主な追加機能・変更点を日本語で記載しています。

Unreleased
----------

- ドキュメント化・補足情報の追加（内部向け）。

[0.1.0] - 2026-04-17
--------------------

Added
- 基本パッケージ初期リリース (version 0.1.0)
  - 環境設定・読み込み
    - .env 自動読み込み機能を実装（プロジェクトルートの .env / .env.local を読み込む）。
    - 自動読み込みを無効化する環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD。
    - .env パースは export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメント等に対応。
    - Settings クラスを導入し、J-Quants / kabuステーション / DB /監視閾値 等の設定をプロパティで提供。
    - PAPER_FILL_MODE のバリデーション（instant/partial/never/reject）。
    - Paper Trading 用のデフォルト SQLite パス (data/paper_trading.db) をサポート。
    - KABUSYS_ENV (development / paper_trading / live) と LOG_LEVEL の検証を実装。

  - 設定管理 CLI
    - config_setup: 対話式ウィザードで .env を作成・更新する CLI を追加。
      - 各種設定項目（J-Quants トークン、kabu API パスワード、DB パス、LOG_LEVEL 等）を対話入力。
      - シークレット項目はマスク表示。生成される .env には Git にコミットしない注意書きを追加。
    - validate_config: 起動前検証 CLI を追加。
      - 必須環境変数の存在確認、KABUSYS_ENV の妥当性、DB パス親ディレクトリの存在、config/*.yaml の存在・YAML パースチェック（PyYAML がない場合は警告）を実行。
      - --strict オプションで警告を FAIL 扱いにできる。

  - 実行・監視エントリポイント
    - run_execution:
      - ExecutionEngine 起動用スクリプト。
      - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、paper_trading 用 DB（data/paper_trading.db など）に記録して本番 DB と分離。
      - ブローカークライアント生成、OrderRepository/OrderManager/RiskManager/Reconciler の組み立て、ExecutionEngine のスレッド起動・停止処理、停止フラグ（data/stop_requested.flag）検出を実装。
      - 起動時にプロセス優先度を "high" に設定。
    - run_monitoring:
      - SystemMonitor のポーリングループ起動スクリプト。
      - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正な値・0 以下はデフォルトにフォールバックして警告を出す。
      - Monitoring は環境に関わらず本番 sqlite_path を使用する（監視用 DB の初期化を実施）。
      - 停止フラグ検知でループ終了、KeyboardInterrupt による安全終了処理を実装。
      - 起動時にプロセス優先度を "high" に設定。

  - データベース / 分析
    - DuckDB および SQLite 接続の利用を明示（duckdb_path, sqlite_path）。
    - 監視テーブルの初期化（init_monitoring_db）を起動時に行う（冪等性確保）。

  - ツール
    - tools/paper_verification_report:
      - ペーパートレード DB を集計して検証レポートを生成するスクリプトを追加。
      - オプション: --from, --to（期間指定）、--db（DB ファイル指定）。
      - 指標: 稼働率（uptime）、注文成功率（fill rate）、送信率（send rate）、レイテンシ（avg / max / P95）など。
      - パス/閾値: 稼働率 99.0%、注文成功率 90.0%、送信率 95.0%、P95 レイテンシ 200ms を基準とした PASS/FAIL 判定を実装。

  - ポートフォリオ構築（純粋関数群）
    - portfolio.portfolio_builder:
      - select_candidates: スコア降順＋タイブレークで候補選定。
      - calc_equal_weights / calc_score_weights: 等配分・スコア加重配分（スコアが全て 0 の場合は等配分にフォールバック）。
    - portfolio.risk_adjustment:
      - apply_sector_cap: セクター集中上限チェック（max_sector_pct）と候補フィルタリング。unknown セクターは適用除外。
      - calc_regime_multiplier: market レジームに応じた投下資金乗数（bull/neutral/bear）と未知レジームのフォールバック。
    - portfolio.position_sizing:
      - calc_position_sizes: allocation_method（risk_based / equal / score）に応じた株数算出、単元株（lot_size）丸め、1 銘柄上限・aggregate cap（available_cash によるスケーリング）、cost_buffer（手数料・スリッページ考慮）を実装。
      - risk_based: 損切り率 stop_loss_pct と risk_pct ベースで株数算出。
      - スケールダウン時は端数/残差を用いた安定的な分配ロジックを採用。

  - 研究用モジュール
    - research.factor_research:
      - calc_momentum: 1M/3M/6M リターン、MA200 乖離率を DuckDB 上の prices_daily テーブルから計算（データ不足時は None）。
      - calc_volatility: ATR（20 日）や 20 日平均売買代金、出来高比率などを計算する機能を実装（長期スキャン範囲や NULL の扱いに注意）。
      - DuckDB を利用し SQL + Python で効率的に計算する設計。

  - ユーティリティ
    - utils.process_priority:
      - クロスプラットフォームでのプロセス優先度設定機能を追加（Windows 用 priority class、POSIX 用 nice を抽象化）。
      - set_cpu_affinity でプロセスの CPU affinity を設定可能（未対応 OS や権限不足時は警告を出してスキップ）。
      - 許容値チェック・例外処理を含む。

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。

Deprecated
- 初回リリースのため該当なし。

Removed
- 初回リリースのため該当なし。

Security
- 初回リリースのため特記事項なし。

Notes / 注意事項
- .env に秘密情報（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等）を保存する設計のため、.env を誤ってリポジトリにコミットしないでください（config_setup の出力にも注意喚起あり）。
- run_monitoring は監視用 DB に本番 sqlite_path を使用します。テスト・ペーパートレード時の監視分離が必要な場合は運用上の対応が必要です。
- process priority / CPU affinity の設定は OS・権限に依存します。失敗した場合は警告ログが出力され設定はスキップされます。
- Paper Trading を利用する際は PAPER_FILL_MODE, PAPER_TRADING_SQLITE_PATH の設定を確認してください。

以上。