# CHANGELOG

すべての変更は Keep a Changelog の形式に従います。  
セマンティックバージョニングを採用しています。

## [Unreleased]

## [0.1.0] - 2026-04-17
初回リリース

### Added
- パッケージ基盤
  - kabusys パッケージ初期実装。__version__ = 0.1.0 を設定。
  - パッケージ公開用の __all__ エクスポートを整理（data/strategy/execution/monitoring を想定）。

- 設定関連
  - Settings クラスを実装（kabusys.config）。環境変数ベースで設定を取得する統一 API を提供。
  - 自動 .env ロード機能を実装（プロジェクトルート検出: .git または pyproject.toml を基準）。.env と .env.local の読み込み順を定義。テスト等で自動ロードを抑止する KABUSYS_DISABLE_AUTO_ENV_LOAD に対応。
  - .env パースロジックを拡充（kabusys.config._parse_env_line）。export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの扱いに対応。
  - 種別チェック・検証付きプロパティを多数実装（J-Quants / kabu API / DB パス / Paper Trading 用設定 / 監視閾値 / 環境種別・ログレベル判定等）。

- 設定操作 CLI
  - 対話式環境設定ウィザードを追加（kabusys.config_setup）。
    - .env の初期作成・既存 .env 読み込み・項目毎の入力補助・シークレットマスク表示・保存機能を提供。
  - 設定検証 CLI を追加（kabusys.validate_config）。
    - 必須環境変数や KABUSYS_ENV の整合性、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在と（PyYAML がインストールされていれば）パース検証を行う。
    - --strict オプションで警告を FAIL 扱いにできる。

- 実行・監視エントリポイント
  - ExecutionEngine 起動スクリプトを追加（kabusys.run_execution）。
    - KABUSYS_ENV=paper_trading の場合は paper 用専用 SQLite（デフォルト data/paper_trading.db）を使用し、本番 DB と分離。
    - BrokerClientFactory によりブローカークライアントを生成（本番/モックの切り替え想定）。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine を起動。別スレッドで run_session を実行し、stop フラグ（data/stop_requested.flag）を監視して安全に停止。
    - PID ファイル（data/execution.pid）を利用。
  - SystemMonitor ポーリングループ起動スクリプトを追加（kabusys.run_monitoring）。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバックして警告出力。
    - 監視は KABUSYS_ENV に関係なく本番 sqlite_path を使用する（監視データの一元管理）。
    - ループ内で例外を捕捉してログ出力し、次回ポーリングへ継続する堅牢化。
    - 停止フラグファイルでの終了と KeyboardInterrupt のハンドリングを実装。

- 監視・DB 初期化
  - init_monitoring_db 関数を利用して監視用テーブルの存在を保証（冪等な初期化）。

- ユーティリティ
  - process_priority ユーティリティ（kabusys.utils.process_priority）を追加。
    - Windows / POSIX（Linux, macOS 等）差分を吸収してプロセス優先度（high/normal/low）を設定。
    - CPU affinity を最初の N コアに固定する set_cpu_affinity を提供。
    - アクセス権限や未対応 OS の場合は警告を出して安全にスキップ。

- ポートフォリオ構築関連（純関数群）
  - portfolio_builder:
    - select_candidates: BUY シグナルをスコア降順 + signal_rank で整列して候補を選択。
    - calc_equal_weights / calc_score_weights: 等配分・スコア加重配分を実装。全スコアが 0 の場合は等配分にフォールバックして警告。
  - risk_adjustment:
    - apply_sector_cap: セクター別既存エクスポージャーを算出し、max_sector_pct を超えるセクターの新規候補を除外（"unknown" セクターは除外対象としない）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に対する投下資金乗数を返す（未知レジームは 1.0 でフォールバックして警告）。
  - position_sizing:
    - calc_position_sizes: allocation_method（risk_based / equal / score）に基づき発注株数を算出。損切り幅・許容リスク・単元株（lot_size）丸め、per-stock 上限・aggregate cap によるスケールダウン、cost_buffer を用いた保守的見積り、残余の端数処理（lot 単位での追加配分）を実装。

- リサーチ（DuckDB ベース）
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離率を DuckDB 上で計算。
    - calc_volatility: ATR, 相対 ATR、20日平均売買代金、出来高比率などを計算する SQL を実装。
    - 設計方針は DuckDB の prices_daily / raw_financials テーブルのみ参照し、外部 API を呼ばない純粋な計算関数として設計。

- ツール
  - Paper Trading 検証レポート生成スクリプトを追加（kabusys.tools.paper_verification_report）。
    - system_status / trade_logs / risk_logs から稼働率、注文成功率（fill rate）、送信率、P95 レイテンシ等を集計。
    - P95 計算、閾値判定（稼働率 >= 99%、fill >= 90%、send >= 95%、P95 <= 200ms）を実装し、PASS/FAIL レポートを標準出力に出力。
    - --from / --to / --db オプションに対応。PAPER_TRADING_SQLITE_PATH 環境変数を尊重。

### Changed
- 設定の取り扱いを明確化
  - .env 読み込みの優先順位を OS 環境変数 > .env.local > .env として実装（既存 OS 環境変数は保護）。
  - Settings プロパティで不正値検出時に明確な例外メッセージを返すように整備（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE 等）。

- DB 周りの扱い
  - 監視コンポーネントは環境に関わらず監視用 sqlite_path（本番設定）を使用する設計に変更し、監視データの一貫性を確保。
  - run_execution は paper_trading モード時に paper_sqlite_path を使用して本番 DB と明確に分離。

### Fixed
- .env パースに関する細かい不具合対応
  - 引用符内のバックスラッシュエスケープやインラインコメントの扱いを改善し、より実用的な .env パースを実現。
- ポーリングループの堅牢化
  - run_monitoring のチェックループで monitor.check_once() が例外を投げてもループを継続するようにし、予期しないエラーによる監視停止を防止。
- CPU / プロセス優先度設定での失敗ハンドリングを強化
  - アクセス権限不足や未実装機能に対して警告を出し、安全に続行するよう修正。

### Security
- .env ファイルは絶対に Git にコミットしない旨を config_setup のヘッダに明記（注意喚起）。

### Known issues / Limitations
- position_sizing や apply_sector_cap では価格の欠損（0.0）の場合にエクスポージャーや target_shares が過少に見積もられる可能性がある旨の TODO コメントを残しています。将来的に前日終値や取得原価でのフォールバックを検討。
- 一部の機能（config/*.yaml の詳細なスキーマ検証など）は PyYAML がインストールされていない環境ではスキップされます（validate_config 参照）。

---

今後のリリースでは以下の改善を予定しています（例）:
- stocks マスタによる銘柄別 lot_size 対応
- position_sizing の手数料・スリッページのより精密なモデル化
- monitoring / execution の統合的なメトリクス出力（Prometheus など）
- config.yml のスキーマバリデーション強化

（以上）