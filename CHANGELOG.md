# Changelog

すべての重要な変更点を記録します。フォーマットは「Keep a Changelog」に準拠しています。

現在のバージョン: 0.1.0

## [0.1.0] - 2026-04-18

初回リリース。本リリースではシステム稼働用の起動スクリプト、設定管理ツール、ポートフォリオ構築ロジック、実行/監視ユーティリティ、ペーパートレード検証ツールなど、基本的なコンポーネントを実装しています。

### Added
- 基本パッケージ構成
  - パッケージメタ情報を追加（src/kabusys/__init__.py、バージョン 0.1.0）。
- 起動スクリプト
  - 実行エンジン起動スクリプト（src/kabusys/run_execution.py）を追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用 DB を使用し、MockBrokerClient を利用する想定。
    - 停止フラグ（data/stop_requested.flag）と PID 管理（data/execution.pid）に対応。
    - 起動時にプロセス優先度を "high" に設定。
  - 監視ポーリングループ起動スクリプト（src/kabusys/run_monitoring.py）を追加。
    - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番 sqlite_path を使用する設計（監視用 DB 初期化処理を実行）。
    - 停止フラグ検知でループ終了、KeyboardInterrupt 対応。
- 設定管理
  - Settings クラス（src/kabusys/config.py）を追加。
    - .env 自動読み込み（プロジェクトルート検出: .git または pyproject.toml）。
    - .env と .env.local の読み込み順序、OS 環境変数の保護対応。
    - 各種設定プロパティ（DB パス、API トークン、環境判定、閾値など）とバリデーションを実装。
    - PAPER_FILL_MODE に対する妥当性チェックや KABUSYS_ENV / LOG_LEVEL の検証。
- 設定ユーティリティ / CLI
  - 設定検証ツール（src/kabusys/validate_config.py）を追加。
    - 必須環境変数チェック、KABUSYS_ENV／LOG_LEVEL 検証、DB パスディレクトリ存在チェック、config/*.yaml の存在確認（PyYAML が無ければ警告）。
    - KABUSYS_ENV=live 時の追加ガード（LINE 通知設定や Kill Switch 設定の警告）。
    - --strict フラグで警告を FAIL 扱いにできる。
  - 対話式 .env 作成ウィザード（src/kabusys/config_setup.py）を追加。
    - 各種設定項目（J-Quants トークン、kabu API パスワード、DB パス、LOG_LEVEL、KILL_FLAG_CLEAR_ON_START など）を対話的に作成・更新可能。
    - 既存 .env 読み込み・マスク表示・確認プロンプト・保存機能を備える。
- ロギング・プロセス設定ユーティリティ
  - 統一ログ設定ユーティリティ（src/kabusys/utils/logging_setup.py）を追加。
    - ルートロガーに StreamHandler (stdout) と TimedRotatingFileHandler（日次、30日保持）を設定。
    - ログディレクトリ自動作成（失敗時はファイル出力をスキップしてコンソールのみ）。
    - ログレベル解決順を実装（引数 > 環境変数 > デフォルト）。
  - プロセス優先度・CPU affinity ユーティリティ（src/kabusys/utils/process_priority.py）を追加。
    - Windows / POSIX の差分吸収（nice / HIGH_PRIORITY_CLASS 等）に対応。
    - set_process_priority(level) と set_cpu_affinity(cpu_count) を提供。権限不足や未対応 OS の場合は警告を出してスキップ。
- ポートフォリオ構築ライブラリ
  - candidate 選定・重み計算（src/kabusys/portfolio/portfolio_builder.py）。
    - select_candidates: スコア降順 + タイブレークで候補選定。
    - calc_equal_weights / calc_score_weights: 等金額・スコア加重配分（全スコア 0 の場合は等分にフォールバック）。
  - セクター集中制限・レジーム乗数（src/kabusys/portfolio/risk_adjustment.py）。
    - apply_sector_cap: 既存保有を考慮してセクター上限を超える新規候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: レジーム（bull/neutral/bear）に応じた乗数を返す（未知レジームは警告のうえ 1.0 をフォールバック）。
  - 株数決定・リスク制限・単元丸め（src/kabusys/portfolio/position_sizing.py）。
    - allocation_method: "risk_based" / "equal" / "score" をサポート。
    - lot_size（単元）丸め、max_position_pct（1銘柄上限）、max_utilization（総投下上限）、cost_buffer（手数料/スリッページ見積り）を考慮したスケーリングロジックを実装。
    - aggregate cap 超過時のスケールダウンと端数処理（lot 単位で残余キャッシュを再配分）。
- 研究／ファクター計算
  - ファクター計算モジュール（src/kabusys/research/factor_research.py）を追加（モメンタム等の計算機能を実装予定）。
    - Momentum（1M/3M/6M、MA200乖離）、ATR、流動性指標などの計算設計を盛り込む（DuckDB を用いた prices_daily / raw_financials 参照を想定）。
- ペーパートレード検証ツール
  - Paper Trading 検証レポート生成スクリプト（src/kabusys/tools/paper_verification_report.py）を追加。
    - 稼働率・注文成功率・送信率・レイテンシ（P95 を含む）を集計して PASS/FAIL 判定（閾値: 稼働率 >=99%、成立率 >=90%、送信率 >=95%、P95 <=200ms）。
    - コマンドライン引数で期間指定（--from / --to）と DB パス指定（--db）をサポート。デフォルト DB は data/paper_trading.db。
- DB 初期化ユーティリティ呼び出し
  - 起動スクリプトで監視用テーブルの存在確認／作成を行うために init_monitoring_db を呼び出す（冪等）。
- tools パッケージ
  - src/kabusys/tools/__init__.py を追加（ツール群の名前空間）。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Notes / Usage highlights
- 環境変数管理
  - 自動 .env ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能（テスト用途）。
  - .env パーサは quoted 値・export 形式・インラインコメントに対応する慎重な実装。
- 監視ループ
  - MONITOR_POLL_INTERVAL が不正（整数変換失敗や <=0）な場合はデフォルト 60 秒にフォールバックして警告を出す。
  - 監視は停止フラグファイルの存在検出で優雅に終了する。
- 実行エンジン
  - paper_trading 環境では本番 DB と分離された paper_trading 用 SQLite を使用する（PAPER_TRADING_SQLITE_PATH で上書き可能）。
  - RiskManager の初期設定には broker.get_available_cash() を用いた初期ポートフォリオ値の取得を行う（ブローカ実装に依存）。
- ロギング
  - コンソール出力は stdout を使用（cron 等で stdout/stderr を一本化する運用を想定）。
  - ログファイル書き込みができない環境ではコンソール出力のみで耐障害性を確保。

### Known limitations / TODO
- research/factor_research.py の一部（calc_momentum の実装）が最後まで含まれておらず、細部実装が未完の可能性あり（今後の実装／整備が必要）。
- position_sizing の price フォールバック（価格欠損時の取り扱い）に関する TODO が残っている（前日終値等のフォールバック実装を検討）。
- 将来的に銘柄別の lot_size を持たせる拡張（stocks マスタの導入）を想定している。
- YAML 検証は PyYAML がインストールされているときのみ実行される（未インストール時は警告）。

---

以上が現時点でコードベースから推測できる変更点・実装内容のまとめです。必要であれば、各ファイルごとのより詳細な変更点や今後のタスク一覧を追加で生成します。