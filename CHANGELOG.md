CHANGELOG
=========
すべての変更は「Keep a Changelog」準拠で記載しています（セマンティックバージョニングを想定）。

[Unreleased]
-------------

0.1.0 - 2026-04-18
------------------
Added
- 初回公開: KabuSys v0.1.0 を追加。
- 実行エントリスクリプト
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止はプロジェクト内 data/stop_requested.flag による検知で行う。
    - 監視用 DB は環境（KABUSYS_ENV）に関わらず本番 sqlite_path を使用する仕様。
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用 DB を使用し MockBrokerClient に切り替え（本番 DB と完全分離）。
    - 実行中の停止は data/stop_requested.flag を監視、PID 管理用ファイルへの書き込みに対応。
- 設定管理
  - config.py: .env の自動ロード機能を実装（プロジェクトルート検出: .git 或いは pyproject.toml を基準）。
    - .env/.env.local の読み込み規則（OS 環境変数を保護する protected ロジック）。
    - export プレフィックス、クォート／エスケープ、インラインコメントの取り扱いをサポートするパーサ実装。
    - 必須環境変数取得用 _require() 実装（未設定時は ValueError を送出）。
    - 各種設定プロパティを提供（DB パス、Paper trading のパラメータ、監視閾値、環境種別など）。
    - PAPER_FILL_MODE の検証（"instant"|"partial"|"never"|"reject" のみ許容）。
    - 自動ロードを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD サポート。
- 設定関連 CLI
  - config_setup.py: 対話式 .env ウィザードを追加。
    - シークレット項目はマスク表示、既存 .env の読み込みと Enter での再利用対応。
    - 出力時に .env を上書き／作成し、.env を Git にコミットしないよう注意喚起。
  - validate_config.py: 設定検証 CLI を追加。
    - 必須環境変数・KABUSYS_ENV・LOG_LEVEL・DB パス・config/*.yaml の存在／YAML パース（PyYAML が存在する場合）などのチェックを実装。
    - KABUSYS_ENV=live 時の追加ガード（LINE トークン未設定や KILL_FLAG_CLEAR_ON_START 設定時の警告）。
    - --strict オプションで警告を失敗扱いにできる。
- ポートフォリオ・ポジション決定モジュール
  - portfolio/portfolio_builder.py: 候補選定と重み算出（等分配・スコア加重）を追加。スコアがすべて 0 の場合は等分配にフォールバックして警告。
  - portfolio/risk_adjustment.py: セクター集中制限（apply_sector_cap）とレジーム乗数（calc_regime_multiplier）を追加。未知レジームは警告して 1.0 をフォールバック。
  - portfolio/position_sizing.py: 株数算出ロジックを実装（risk_based / equal / score）。
    - lot_size（単元）対応、max_position_pct / max_utilization / cost_buffer を考慮。
    - aggregate cap 超過時のスケールダウンと端数処理（残余キャッシュを fractional 残差順に配分）を実装。
- リサーチ
  - research/factor_research.py: DuckDB を用いたファクター計算モジュール（Momentum / Volatility / Liquidity 等）。
    - prices_daily テーブルを前提に、移動平均やATR、各種ホライズンのリターンを計算。
    - データ不足時は None で扱う設計。
- ツール
  - tools/paper_verification_report.py: Paper Trading 検証レポート生成スクリプトを追加。
    - 稼働率、注文成功率（fill）、送信率（send）、リスク却下数、レイテンシ（avg/max/P95）を集計。
    - P95 計算、日付フィルタ、しきい値による PASS/FAIL 判定を実装。
    - PAPER_TRADING_SQLITE_PATH や --db オプションで DB パスを指定可能。
- ユーティリティ
  - utils/process_priority.py: プロセス優先度と CPU affinity 設定ユーティリティを追加。
    - Windows / POSIX（Linux/Mac/FreeBSD）で差分を吸収。
    - set_process_priority("high" | "normal" | "low") と set_cpu_affinity(n) を提供。
    - psutil のアクセス制限や未実装 API を安全にハンドリングして警告を出す。

Changed
- なし（初回リリース）。

Fixed
- 環境変数パーサの堅牢化: export プレフィックス、クォート内エスケープ、インラインコメントの扱いを明確化。
- MONITOR_POLL_INTERVAL の不正値対応: 0 以下や数値以外が指定された場合にデフォルト値へフォールバックし、警告ログを出力するように修正。
- DuckDB / SQLite 接続の明示化: 監視・実行それぞれで適切な DB パスを使うように整備（paper_trading は専用 DB）。

Security
- config_setup.py で生成される .env に関して「絶対に Git にコミットしないこと」を明記（ファイルヘッダに注意書き追加）。
- 必須環境変数未設定時は起動前に検出して明確に失敗させる検証ロジックを提供。

Notes
- 実行例
  - 監視: python -m kabusys.run_monitoring
  - 実行エンジン: python -m kabusys.run_execution
  - 設定ウィザード: python -m kabusys.config_setup
  - 設定検証: python -m kabusys.validate_config
  - Paper レポート: python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- デフォルトパス
  - DuckDB: data/kabusys.duckdb
  - SQLite (monitoring): data/monitoring.db
  - Paper trading SQLite: data/paper_trading.db
  - PID / フラグファイル: data/execution.pid / data/stop_requested.flag / data/kill.flag（パスは Settings で上書き可能）
- 注意事項
  - run_monitoring は監視データを本番用 SQLite に書き込む設計（環境にかかわらず sqlite_path を使用）。ペーパートレードと完全に分離したい場合は run_execution が paper_trading 用 DB を使う点に注意。
  - process_priority や cpu_affinity は OS 権限や psutil の実装状況に依存するため、失敗時はログ警告でスキップされる。
  - config/*.yaml の検証は PyYAML がインストールされている場合のみ内容まで検査する（存在確認は常時行う）。

Unreleased
- 将来的な改善案（TODO）
  - position_sizing の lot_size を銘柄別に持たせる（stocks マスタに lot_size を追加）。
  - price 欠損時のフォールバック（前日終値や取得原価）を導入してエクスポージャー計算の過少見積り問題を解消。
  - monitoring と execution のさらに細かな権限分離・テスト用フラグの追加。
  - factor_research の計算を最適化し、並列処理オプションを追加。

(以上)