# Changelog

すべての変更は Keep a Changelog の形式に準拠します。  
安定版リリースと主要な追加・変更点を日本語で記載しています。コードベースから推測した内容に基づいて作成しています。

## Unreleased
- 予定/改善（コード内の TODO や未実装部分に基づく）
  - research/factor_research.calc_momentum の実装完了および他ファクター計算の単体テスト追加。
  - apply_sector_cap の price 欠損時のフォールバック（前日終値や取得原価など）対応を追加。
  - position_sizing の lot_size を銘柄ごとに指定できるように拡張（stocks マスタの導入）。
  - DuckDB/SQLite の接続例外や I/O エラーに対する耐性強化（リトライ・フェイルオーバー戦略）。
  - モニタリングのポーリング間隔・停止制御の運用性向上（動的再読込、外部管理 API など）。
  - 追加のユニット・統合テスト、CI ワークフロー整備。

---

## [0.1.0] - 2026-04-18

### Added
- 基本アプリケーション構成
  - パッケージメタ情報 (src/kabusys/__init__.py, __version__ = "0.1.0") を追加。

- 環境設定・読み込み
  - 柔軟で堅牢な .env 読み込みロジックを実装（src/kabusys/config.py）。
    - プロジェクトルート自動検出 (.git / pyproject.toml)。
    - export プレフィックス、クォート付き値、エスケープ、インラインコメント処理に対応した行パーサ。
    - .env と .env.local の自動読み込み（OS環境変数優先）。KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化オプション。
  - Settings クラスによる環境変数アクセスラッパーを実装。多くのプロパティを提供:
    - J-Quants / kabuステーション / LINE API 設定
    - DuckDB/SQLite パス、Paper Trading 用 DB 切替、PAPER_FILL_MODE 検証
    - 監視関連閾値 (CPU/Memory/Disk)、PID / kill flag パス、ログレベル、実行環境判定 (development/paper_trading/live)
    - バリデーション（無効値検出時は例外）

- 設定支援 CLI
  - 対話式 .env 作成ウィザード（src/kabusys/config_setup.py）。
    - シークレット入力のマスク、選択肢、既存値の再利用。
    - .env テンプレート書き出し機能。
  - 起動前設定検証ツール（src/kabusys/validate_config.py）。
    - 必須環境変数チェック、KABUSYS_ENV 検証、LOG_LEVEL 検証、DB パス確認、config/*.yaml の存在と YAML パース検査（PyYAML がある場合）。
    - 本番環境向けの安全ガード（LINE 未設定や KILL_FLAG_CLEAR_ON_START の注意喚起）。
    - --strict モード（警告を FAIL 扱い）をサポート。

- 実行・監視スクリプト
  - 実行エンジン起動スクリプト（src/kabusys/run_execution.py）
    - プロセス優先度を High に設定して起動。
    - KABUSYS_ENV=paper_trading の場合、paper_trading 用専用 SQLite DB を使用し本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler を組み合わせ ExecutionEngine を起動。
    - 停止フラグ (data/stop_requested.flag) による安全停止、実行 PID ファイル管理。
    - RiskManager のデフォルト設定（例: max_position_pct=20%、max_utilization=80%、rate_limit_per_sec 等）と初期ポートフォリオ値をブローカーから取得して設定。
  - 監視ポーリング起動スクリプト（src/kabusys/run_monitoring.py）
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトへフォールバック。
    - 監視は環境に関わらず本番 sqlite_path を参照して監視テーブルを初期化。
    - SystemMonitor.check_once() を定期実行、例外はロギングして次ポーリングへ継続。停止フラグで終了。

- ポートフォリオ構築ロジック（純粋関数群、DB 非依存）
  - 候補選定および重み計算（src/kabusys/portfolio/portfolio_builder.py）
    - select_candidates: スコア降順・signal_rank によるタイブレークで上位 N を選定。
    - calc_equal_weights / calc_score_weights: 等金額配分・スコア加重配分（スコア合計 0 の場合は等配分にフォールバック）。
  - セクター集中制限・レジーム乗数（src/kabusys/portfolio/risk_adjustment.py）
    - apply_sector_cap: 既存保有を考慮して特定セクターの新規エントリをブロック（unknown セクターは無視）。
    - calc_regime_multiplier: market レジームに応じた投下資金乗数（bull=1.0、neutral=0.7、bear=0.3、未知は警告して 1.0 フォールバック）。
  - 口数計算・リスク制限・単元丸め（src/kabusys/portfolio/position_sizing.py）
    - allocation_method に応じた株数計算 ("risk_based" / "equal" / "score")。
    - 損切り率・許容リスク率・単元株丸め・max_position_pct / max_utilization・aggregate cap（available_cash でスケール）に対応。
    - cost_buffer を考慮した保守的見積りと残差処理（lot_size 単位で端数配分）。

- 解析・研究モジュール
  - research/factor_research.py（ファクター計算の枠組みを実装）
    - Momentum / Value / Volatility / Liquidity 等の計算方針を定義。
    - DuckDB 接続を受け prices_daily / raw_financials テーブルを参照する設計（ただし一部関数は未完/継続実装の痕跡あり）。

- ユーティリティ
  - ロギング設定ユーティリティ（src/kabusys/utils/logging_setup.py）
    - ルートロガーに StreamHandler (stdout) と TimedRotatingFileHandler（日次・30日保持）を設定。
    - ログディレクトリ作成に失敗した場合はコンソールのみにフォールバック。
    - LOG_LEVEL / LOG_DIR の優先解決ロジック。
  - プロセス優先度・CPU affinity ユーティリティ（src/kabusys/utils/process_priority.py）
    - Windows / POSIX の差分吸収（psutil 利用）。
    - set_process_priority(level) により current process の nice / priority を設定。失敗時は警告でスキップ。
    - set_cpu_affinity(cpu_count) により最初の N コアに固定（AccessDenied 等は警告でスキップ）。

- ツール
  - Paper Trading 検証レポート生成スクリプト（src/kabusys/tools/paper_verification_report.py）
    - SQLite (PAPER_TRADING_SQLITE_PATH) から様々な指標を集計して CLI レポートを生成。
    - 稼働率、注文成功率、送信率、リスク却下数、レイテンシ（平均/最大/P95）を算出。
    - PASS/FAIL の閾値を定義（稼働率 >= 99%、fill_rate >= 90%、send_rate >=95%、P95 <= 200ms）。
    - --from/--to/--db オプションをサポート。

### Changed
- なし（初回リリースとして新規実装中心）

### Fixed
- なし（初回リリース）

### Security
- なし（初回リリース）

---

注意:
- 設計・実装の多くは外部リソース（ブローカー、DuckDB/SQLite テーブル、config/*.yaml 等）に依存します。実運用ではそれらのセットアップや秘匿情報管理 (.env の扱い、J-Quants / kabu API のトークン等) に注意してください。
- 一部の実装上の注記（TODO コメント）や未完の関数が見受けられます。上記「Unreleased」に今後の改善候補を挙げています。