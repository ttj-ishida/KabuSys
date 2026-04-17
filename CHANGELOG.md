# CHANGELOG

すべての変更は Keep a Changelog 準拠で記載しています。セマンティックバージョニングを採用しています。

## [0.1.0] - 2026-04-17

初回リリース。日本株自動売買システム KabuSys の基本機能群を追加しました。以下はコードベースから推測した主要な追加・動作仕様のまとめです。

### 追加（Added）
- 全体
  - パッケージの初期バージョンを追加（__version__ = "0.1.0"）。
  - DuckDB / SQLite を組み合わせたデータ基盤の利用を前提とした設計を追加（Settings に DB パスを定義）。

- 設定関連
  - 環境変数読み込み・管理モジュール（kabusys.config）を追加。
    - プロジェクトルート検出（.git / pyproject.toml）に基づく .env 自動読み込み（.env, .env.local）。
    - .env の行パース機能を実装（コメント、クォート、export 形式、エスケープ対応）。
    - 必須値チェック用の _require() と Settings クラスを提供。J-Quants / kabu API 等の設定プロパティを定義。
    - Paper Trading 用の別 SQLite パス（PAPER_TRADING_SQLITE_PATH）や paper_fill_mode 等の設定をサポート。
    - 監視やしきい値（CPU/MEM/DISK）や PID / kill flag のパスも設定可能。

  - 対話式設定ウィザード CLI（kabusys.config_setup）を追加。
    - .env の作成・更新を対話的に行う。シークレットは表示をマスク。
    - 書き込みテンプレートを提供し、.env を生成。

  - 設定検証 CLI（kabusys.validate_config）を追加。
    - 必須環境変数、KABUSYS_ENV の妥当性、DB パスや config/*.yaml の存在とパース検証（PyYAML 利用時）をチェック。
    - --strict オプションで警告も失敗扱いにできる。
    - 本番環境（KABUSYS_ENV=live）向けの追加ガード（LINE 通知未設定や KILL_FLAG_CLEAR_ON_START 設定の警告）。

- 実行 / 監視ランナー
  - 実行エンジン起動スクリプト（kabusys.run_execution）を追加。
    - プロセス優先度を起動時に設定（utils.process_priority.set_process_priority）。
    - paper_trading 環境では MockBrokerClient（BrokerClientFactory 経由）と専用 SQLite（data/paper_trading.db）を使用して本番 DB と分離。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み立て、ExecutionEngine を起動。
    - 停止フラグ（data/stop_requested.flag）検知による安全停止、PID ファイル出力、スレッドでのセッション実行制御を実装。

  - 監視ループ起動スクリプト（kabusys.run_monitoring）を追加。
    - SystemMonitor を初期化してポーリングループで定期チェックを実行。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値は警告してデフォルトにフォールバック。
    - 監視 DB 初期化（init_monitoring_db）を保証。監視は環境にかかわらず production 用 sqlite_path を使用する仕様。

- ユーティリティ
  - process_priority（kabusys.utils.process_priority）を追加。
    - Windows / POSIX(Linux/macOS/FreeBSD) の差分を吸収してプロセス優先度を設定。
    - CPU affinity 設定関数も提供（set_cpu_affinity）。権限不足や未対応 OS 時は安全に警告してスキップ。

- ポートフォリオ構築（純粋関数群）
  - portfolio_builder:
    - select_candidates（スコア降順で候補選定）
    - calc_equal_weights（等金額配分）
    - calc_score_weights（スコア正規化配分、全スコア 0 の場合は等配分にフォールバック）
  - risk_adjustment:
    - apply_sector_cap（セクター集中上限の適用、売却予定銘柄の除外、"unknown" セクターは除外しない）
    - calc_regime_multiplier（レジームに応じた投下資金乗数: bull/neutral/bear）
  - position_sizing:
    - calc_position_sizes（risk_based / equal / score の割当方式、ロット丸め、per-stock 上限、aggregate cap（利用可能現金でスケールダウン）、cost_buffer を考慮）

- 研究・データ処理
  - research.factor_research を追加（DuckDB 接続を受け、prices_daily / raw_financials を参照）。
    - calc_momentum（1M/3M/6M リターン、MA200 乖離）
    - calc_volatility（ATR20、相対 ATR、20日平均売買代金、出来高比率）
    - 窓幅・スキャン幅を定義して十分な過去データを参照する実装。

- ツール
  - tools.paper_verification_report（Paper Trading 検証レポート生成）を追加。
    - 指定期間のシステム稼働率、注文成功率・送信率、リスク却下数、API レイテンシ（平均・最大・P95）を集計し PASS/FAIL 判定を出力。
    - デフォルト閾値（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200 ms）を定義。
    - DB が存在しない場合やテーブルが存在しない場合のフォールバックを実装。

### 変更（Changed）
- .env 自動ロードの挙動
  - OS 環境変数が優先され、.env.local が .env を上書きする動作を導入。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。

- 実行時優先度設定
  - run_execution/run_monitoring 起動時に最初にプロセス優先度を "high" に設定するようになっている（set_process_priority の使用）。

### 修正（Fixed）
- 環境変数パースの堅牢化
  - export 形式、クォート内のバックスラッシュエスケープ、インラインコメントの扱いなどを考慮するパーサを実装し、.env の多様な書式に対応。

- データ不足・例外時の耐性向上
  - paper_verification_report と research モジュール、各クエリでテーブル不存在やデータ欠損時に安全にフォールバックする処理を追加（OperationalError ハンドリングや None の扱い）。

### 注意事項（Important Notes）
- 本番／ペーパートレード DB 分離
  - Paper Trading 実行時は専用 SQLite（デフォルト: data/paper_trading.db）を使い、本番の監視 DB（data/monitoring.db 等）とデータを分離する設計です。実運用時は環境変数の設定を確認してください。

- .env の取り扱い
  - config_setup により生成される .env は秘密情報を含みます。ファイルを Git 等へコミットしないでください（警告コメントを出力）。

- 権限やプラットフォーム差
  - process_priority や CPU affinity 設定は OS 権限やプラットフォームに依存します。設定に失敗した場合は警告を出して動作を継続する設計です。

### 既知の制約 / TODO（In this release）
- 一部関数で price が欠損（0.0）の場合にエクスポージャーが過少見積もられる可能性あり（risk_adjustment.apply_sector_cap の TODO）。
- 単元株（lot_size）は現状全銘柄共通で固定（将来的に銘柄別 lot_map へ拡張予定）。
- research モジュールは prices_daily / raw_financials のデータ品質に依存するため、データ不足時は None を返すフィールドがある点に留意。

---

今後のリリースでは以下の点が想定されます（例示）:
- ExecutionEngine / Broker クライアントの実装詳細・エラー処理強化
- モニタリング指標の拡充とアラート通知連携（LINE 等）
- 銘柄別ロット対応・手数料モデルの拡張
- テストカバレッジ・CI の整備

（この CHANGELOG.md は提供されたコードからの推測に基づいて作成しています。実際のコミット履歴や意図と差分がある可能性があります。）