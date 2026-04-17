# CHANGELOG

すべての重要な変更をここに記録します。フォーマットは "Keep a Changelog" に準拠しています。

全般:
- 初期リリース。CLI / ライブラリ / ユーティリティ群を含む基本的な自動売買フレームワークを追加。

## [0.1.0] - 2026-04-17

### Added
- 基本パッケージ情報
  - パッケージバージョンを追加 (kabusys.__version__ = "0.1.0")。

- 設定管理
  - 環境変数 / .env 自動読み込み機能を実装（kabusys.config）。
    - プロジェクトルート（.git または pyproject.toml）を基準に .env / .env.local を自動ロード。
    - OS 環境変数を保護する protected オプションを実装。
    - .env パースはクォート、エスケープ、コメントを考慮して処理。
    - Settings クラスで主要設定値をプロパティとして公開（J-Quants / kabu API / DB パス / 監視閾値 / 実行環境など）。
    - 環境値のバリデーション（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE 等）。

- 設定ウィザード CLI
  - 対話式 .env 生成/更新ツールを追加（kabusys.config_setup）。
    - 多数の設定項目（KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DB パス, LINE トークン等）を対話的に作成可能。
    - 秘匿項目のマスク表示、既存 .env の読み込み、最終確認・保存機能を備える。

- 設定検証ツール
  - 起動前検証用 CLI を追加（kabusys.validate_config）。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL 検証、DB パス存在有無ヒント、config/*.yaml の存在と YAML パース検証（PyYAML が存在する場合）。
    - 本番（live）向けの追加ガード（LINE 通知設定、KILL_FLAG_CLEAR_ON_START の注意喚起）。
    - --strict オプションで警告を FAIL 扱いにする機能。

- 実行エントリ / 監視エントリ
  - ExecutionEngine 起動スクリプト（kabusys.run_execution）。
    - 実行前にプロセス優先度を high に設定。
    - KABUSYS_ENV=paper_trading の場合、paper_trading 用の専用 SQLite を使用して本番 DB と完全分離。
    - BrokerClientFactory を利用したブローカークライアント抽象化、OrderRepository / OrderManager / RiskManager / Reconciler / ExecutionEngine を組み立てて実行。
    - 停止フラグ（data/stop_requested.flag）および PID ファイル（data/execution.pid）に対応。
  - SystemMonitor ポーリングループ起動スクリプト（kabusys.run_monitoring）。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 起動時にプロセス優先度を high に設定。
    - 監視用 DB 初期化（init_monitoring_db）と DuckDB 接続を確立して SystemMonitor を定期実行。
    - 停止フラグ検知・KeyboardInterrupt 対応・例外保護を実装。

- 監視 / 実行補助
  - 監視 DB 初期化フック呼び出しを各起動スクリプトに追加（init_monitoring_db を起動時に呼び出し、冪等に監視テーブルを保証）。

- Paper Trading 検証ツール
  - paper_trading 用検証レポート生成スクリプトを追加（kabusys.tools.paper_verification_report）。
    - system_status, trade_logs, risk_logs から統計を集計し、稼働率 / 注文成功率 / 送信率 / レイテンシ（平均・最大・P95）を算出。
    - 判定閾値（稼働率 >= 99%、成立率 >= 90%、送信率 >= 95%、P95 <= 200ms）を定義して PASS/FAIL を出力。
    - --from/--to/--db オプションで期間・DB を指定可能。PAPER_TRADING_SQLITE_PATH 環境変数にも対応。

- ポートフォリオ構成・ポジション算出モジュール
  - 銘柄選定・重み算出（kabusys.portfolio.portfolio_builder）
    - select_candidates: スコア降順で候補選定（タイブレークは signal_rank）。
    - calc_equal_weights: 等金額配分。
    - calc_score_weights: スコア比率配分（全スコアが 0 の場合は等配分にフォールバック）。
  - セクター集中制限・レジーム乗数（kabusys.portfolio.risk_adjustment）
    - apply_sector_cap: 既存保有に基づくセクター上限チェック（unknown セクターは制限対象外）。
    - calc_regime_multiplier: market regime に応じた乗数（bull/neutral/bear）。
  - 株数算出・リスク制限・単元丸め（kabusys.portfolio.position_sizing）
    - calc_position_sizes: allocation_method に応じた株数計算（risk_based / equal / score）。
    - 単元株（lot_size）丸め、per-stock 上限・aggregate cap、cost_buffer（コスト見積）を考慮したスケーリングと端数配分ロジックを実装。
    - risk_based では損切り幅等からポジションサイズ算出。
  - 上記をパッケージエクスポート（kabusys.portfolio.__all__）。

- 研究用ファクター計算
  - ファクター計算モジュールを追加（kabusys.research.factor_research）。
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離率を DuckDB の prices_daily から計算。
    - calc_volatility: ATR20, 相対 ATR, 20日平均売買代金, 出来高比率等を計算する設計（長めのスキャン範囲や NULL 伝播に注意した実装）。
    - DuckDB 接続を受け取り SQL + Python で計算する方針。結果は (date, code) ベースの辞書リスト。

- ユーティリティ
  - プロセス優先度・CPU affinity ユーティリティ（kabusys.utils.process_priority）。
    - set_process_priority(level): Windows / POSIX の差を吸収し "high"/"normal"/"low" を設定（psutil 使用、例外時は警告でスキップ）。
    - set_cpu_affinity(cpu_count): 最初の N コアにプロセスを固定する機能（未対応 OS / 権限不足時は警告でスキップ）。

### Changed
- （初期リリースのため特記すべき変更なし）

### Fixed
- 起動・実行の堅牢化
  - run_monitoring のポーリング間隔が不正（0以下や非整数）の場合にデフォルト 60 秒へフォールバックして例外を避ける処理を追加。
  - run_monitoring / run_execution で例外発生時にログを残してループ継続または安全に終了する処理を追加。

### Known issues / Notes
- run_monitoring はコメントに明記の通り「Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用」する挙動になっています（設計上の意図／注意事項）。
- set_process_priority / set_cpu_affinity は権限不足やプラットフォーム差分で失敗する可能性があります。失敗時は警告ログを出して処理をスキップします。
- position_sizing の price 欠損時（price が 0 または None）はログ出力してスキップする実装。欠損価格によるエクスポージャー過小見積り等の注意点はコメントで記載。
- .env 自動読み込みはプロジェクトルートが検出できない場合はスキップされます。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
- config/*.yaml の内容チェックは PyYAML に依存。未インストール時は内容検証をスキップして警告を出します。
- calc_regime_multiplier は未知のレジームに対して 1.0 でフォールバックし警告を出します。

### Security
- 秘匿情報（J-Quants トークン / kabu API パスワード / LINE トークン等）は .env に保存することを想定。README 等で .env をリポジトリに含めない運用を強く推奨。

---

今後の予定（例）
- テストカバレッジの強化（ユニット / 統合）。
- broker 実装の差し替えや MockBroker の挙動拡充。
- ポートフォリオ構成ロジックのチューニングとバックテスト統合。