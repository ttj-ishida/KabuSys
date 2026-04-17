# Changelog

すべての重要な変更を記録します。  
このファイルは Keep a Changelog のフォーマットに準拠しています。  

フォーマット: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]


## [0.1.0] - 2026-04-17

初回リリース。主要な機能群と CLI、ユーティリティ、ポートフォリオ構築 / ポジションサイズ算出、リサーチ用ファクター計算、モニタリング / 実行ランナー等を含みます。

### Added
- 基本パッケージメタ情報
  - __version__ を "0.1.0" として公開（kabusys パッケージ）。
  - __all__ に主要サブパッケージを登録。

- 環境設定 / 管理
  - Settings クラスを実装し、環境変数から設定を取得する仕組みを提供（J-Quants、kabuステーション、LINE、DB パス、監視閾値など）。
  - .env 自動ロード機構（プロジェクトルート検出、.env / .env.local の優先度制御、OS 環境変数保護）。
  - 強力な環境変数パーサ（クォート、エスケープ、インラインコメント対応）。

- CLI ツール
  - config_setup: 対話式ウィザードで .env を初期作成 / 更新する CLI を追加。
    - 項目定義（KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DB パス, LOG_LEVEL, Kill Switch など）。
    - 既存 .env の読み込み・マスク表示・確認保存機能。
  - validate_config: 起動前チェック用 CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV 値チェック、ログレベルチェック、DB パス親ディレクトリチェック、config/*.yaml の存在チェック（PyYAML があればパース検証）など。
    - --strict モード：警告も失敗扱いにできる。

- 実行ランナー / モニタリング
  - run_execution: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading 時は paper 用 DB（data/paper_trading.db）を使用し MockBrokerClient を利用する設計に対応。
    - stop flag（data/stop_requested.flag）検知による安全停止、実行 PID 管理（data/execution.pid）。
    - 各種コンポーネント（BrokerFactory、OrderRepository、OrderManager、RiskManager、Reconciler、ExecutionEngine）を組み立ててスレッドで実行。
  - run_monitoring: SystemMonitor 用ポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバック。
    - 監視 DB は環境に依らず本番 sqlite_path を使用。
    - stop flag による終了検知、例外時のログ再試行、プロセス優先度設定などを実装。

- モニタリング DB 初期化
  - init_monitoring_db（monitoring.monitoring_db）を利用して必要な監視テーブルの冪等初期化を行う呼び出しを run スクリプトに導入。

- ツール
  - tools/paper_verification_report.py を追加。
    - Paper Trading 用 SQLite DB から稼働率、注文成功率、送信率、リスク却下数、平均/最大/P95 レイテンシ等を集計・レポート出力。
    - デフォルト閾値（稼働率 99%、注文成功率 90%、送信率 95%、P95 レイテンシ 200 ms）を定義。
    - --from / --to / --db オプション対応。

- ポートフォリオ構築（純関数群）
  - portfolio.portfolio_builder: 候補選定（スコア順, tie-breaker）、等金額配分、スコア加重配分（スコア全0 の場合は等分にフォールバック）。
  - portfolio.risk_adjustment: セクター集中制限の適用（apply_sector_cap）、市場レジームに基づく投下資金乗数（calc_regime_multiplier）。
  - portfolio.position_sizing: ポジションサイズ算出（risk_based / equal / score 方式）、単元（lot）丸め、aggregate cap によるスケールダウン処理、コストバッファ対応。

- リサーチ / ファクター計算
  - research.factor_research: DuckDB からのデータ参照に基づくモメンタム、ボラティリティ / 流動性等のファクター計算関数を実装。
    - mom_1m / mom_3m / mom_6m / ma200_dev、atr_20、atr_pct、avg_turnover、volume_ratio 等を出力。
    - ウィンドウ不足時の None 処理、P95 計算ユーティリティ等。

- プロセス制御ユーティリティ
  - utils.process_priority:
    - set_process_priority(level): Windows / POSIX に跨るプロセス優先度設定（"high" / "normal" / "low"）。
    - set_cpu_affinity(cpu_count): プロセスを最初の N コアにピン留めする機能。
    - PSUtil の権限不足や非対応 OS を考慮した安全なフォールバックとログ出力。

### Changed
- 設定自動読み込みの優先度と保護
  - OS 環境変数を保護した上で .env（上書き不可）→ .env.local（上書き可）の順で読み込む実装を採用。

- DB パスの扱い
  - run_execution は paper_trading 環境時に専用の paper_sqlite_path を使用するように分離（本番 DB とのデータ分離を確保）。

### Fixed
- 環境変数パースの堅牢化
  - .env 内のクォート / エスケープ / コメント処理を改善し、より正確にキー/値を抽出するように修正（export KEY=val 形式にも対応）。

- ポーリング間隔の検証
  - MONITOR_POLL_INTERVAL の不正値（非整数・0 以下）を検出して警告を出し、デフォルト 60 秒へフォールバックする処理を追加。これにより time.sleep による ValueError を回避。

### Known issues / TODO
- portfolio.risk_adjustment.apply_sector_cap 内の price フォールバック:
  - price_map に価格が欠損（0.0）ある場合、エクスポージャーが過小見積りされてしまう可能性があり、将来的に前日終値や取得原価などのフォールバックを導入予定。
- position_sizing の lot_size は現状グローバル固定（将来的に銘柄別 lot_map を受け取る設計に拡張予定）。
- calc_regime_multiplier は未知のレジームで警告して 1.0 にフォールバック（意図的）。実運用時はレジーム検出側の品質向上を推奨。

### Security
- 本リリースではセキュリティに関する既知の問題はありません。ただし .env ファイルは絶対に Git にコミットしない旨をドキュメントおよび config_setup のヘッダに明記しています。

---

今後のリリースでは、実運用での監視アラート（LINE 通知）の整備、Strategy / Execution のテストカバレッジ強化、ファクター計算の最適化や DuckDB スキーマ変更対応などを予定しています。