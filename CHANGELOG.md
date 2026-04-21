# Changelog

すべての重要な変更をこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠します。  
現在のパッケージバージョン: 0.1.0

注: 以下の変更点は今回提供されたコードベースの内容から推測してまとめたものです。

## [Unreleased]
(未リリースの変更はここに記載します)

## [0.1.0] - 2026-04-21
最初の公開リリース候補。システム全体のコア機能、CLI ユーティリティ、ポートフォリオ構築・サイズ計算ロジック、モニタリング・実行エンジンの起動スクリプトなどを実装しました。

### 追加 (Added)
- 全体
  - パッケージ初期版を追加。モジュール群を整理して公開。
  - バージョン定義: `kabusys.__version__ = "0.1.0"`。

- 実行 / ワーカー
  - run_execution: ExecutionEngine 起動スクリプトを追加。プロセス優先度設定、DB 接続、Broker クライアント生成、エンジンのスレッド起動・停止監視（stop flag）を実装。
    - Paper trading モード（KABUSYS_ENV=paper_trading）では専用の SQLite（`data/paper_trading.db` をデフォルト）を使用し、本番 DB と分離。
    - プロセス PID 管理用ファイルサポート（`data/execution.pid`）。
  - run_monitoring: SystemMonitor ポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は常に本番用の sqlite_path を使用する設計。

- 設定 / 構成
  - config: 環境変数/設定管理モジュールを追加。
    - プロジェクトルート自動検出（.git または pyproject.toml を基準）。
    - .env/.env.local 自動読み込み（OS 環境変数を保護、KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
    - 複数の設定プロパティを提供（J-Quants / kabu API / DB パス / Paper Trading 設定 / 監視閾値 / 環境判定 等）。
    - PAPER_FILL_MODE のバリデーション実装（"instant"|"partial"|"never"|"reject"）。
    - KABUSYS_ENV / LOG_LEVEL のバリデーション。
  - config_setup: 対話式 .env ウィザードを追加（.env の初期作成・更新を支援）。
    - 入力のマスク・デフォルト・選択肢表示など UX を提供。
    - .env の書き込みテンプレートを実装（機密値はマスクして表示）。

- 検証ツール
  - validate_config: 起動前に .env と config/*.yaml を検証する CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV の妥当性確認、DB パス親ディレクトリ存在チェック、YAML パース検証（PyYAML が存在する場合）。
    - 本番環境 (live) に関する追加ガード（LINE 通知設定、KILL_FLAG_CLEAR_ON_START 設定の警告等）。
    - --strict オプションで警告も失敗扱いにする機能。

- ロギング / プロセス制御
  - logging_setup: 統一的なログ設定ユーティリティを追加。
    - StreamHandler を stdout に、TimedRotatingFileHandler を日次で追加（デフォルト logs/、30 日保持）。
    - 既存ハンドラの二重登録防止（既存ハンドラを flush/close 後に削除して再設定）。
    - LOG_DIR / LOG_LEVEL の解決順とフォールバックを実装。
  - process_priority: プロセス優先度と CPU affinity 設定ユーティリティを追加。
    - Windows / POSIX を吸収した抽象化。set_process_priority("high"|"normal"|"low")、set_cpu_affinity(N) を提供。
    - 権限や未対応 OS に対する安全なフォールバック（警告ログ）を実装。

- ポートフォリオ構築（純粋関数群）
  - portfolio.portfolio_builder
    - select_candidates: BUY シグナルのスコア降順選定（同点は signal_rank でブレーク）を実装。
    - calc_equal_weights: 等金額配分。
    - calc_score_weights: スコア加重配分（全スコアが 0 の場合は等金額にフォールバック）。
  - portfolio.risk_adjustment
    - apply_sector_cap: セクター集中上限チェック（既存ポジションの時価比率により新規候補を除外）を実装。
      - "unknown" セクターは上限チェック対象外にする挙動。
    - calc_regime_multiplier: 市場レジームに応じた資金乗数（bull/neutral/bear）を実装。未知レジームは警告を出して 1.0 にフォールバック。
  - portfolio.position_sizing
    - calc_position_sizes: 発注株数計算を実装。
      - allocation_method: "risk_based" / "equal" / "score" をサポート。
      - lot_size（単元株）を考慮した丸め処理、max_position_pct / max_utilization / cost_buffer を考慮した aggregate cap スケーリング、スケーリング後の端数配分アルゴリズムを実装。
      - 価格未取得銘柄のスキップ、ログによるデバッグ情報出力。

- リサーチ
  - research.factor_research: ファクター計算モジュールを追加（設計方針・定数・関数概要を実装）。
    - Momentum、Value、Volatility、Liquidity 等の計算を想定。DuckDB を用いた prices_daily/raw_financials 参照を前提。
    - （ファイル途中までの実装が含まれており、モメンタム計算関数 calc_momentum の実装開始が見られる）

- ツール
  - tools.paper_verification_report: Paper Trading 検証レポート生成スクリプトを追加。
    - system_status / trade_logs / risk_logs を参照して稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）を集計・出力。
    - 合格判定基準（閾値）を定義（稼働率 >= 99%、注文成功率 >= 90%、送信率 >= 95%、P95 レイテンシ <= 200ms）。
    - 日付フィルタ（--from / --to）および DB パス上書き (--db) をサポート。

- DB 初期化サポート
  - monitoring.monitoring_db.init_monitoring_db を各種起動処理で呼び出し、監視テーブルが存在することを保証（冪等）する処理を導入。

### 変更 (Changed)
- なし（初回リリースのため既存変更はなし）

### 修正 (Fixed)
- なし（初回リリースのためバグ修正履歴はなし）

### 既知の制限 / 注意点 (Known issues / Notes)
- research.factor_research の実装が途中で終わっているファイルが含まれており、完全実装は今後の作業が必要です。
- position_sizing や risk_adjustment の一部ロジック（価格欠損時のフォールバックなど）については TODO コメントが残っており、将来的な拡張が想定されています。
- .env の自動ロードはプロジェクトルートを検出できない場合はスキップされます（テスト環境などで挙動を変えたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を使用してください）。
- process_priority / set_cpu_affinity は環境や権限に依存して失敗する可能性があり、その場合は警告を出して処理をスキップします。
- ログディレクトリ作成やファイルハンドラ生成に失敗した場合はコンソール出力（stdout）のみで継続します。

### セキュリティ (Security)
- 機密値（API トークン・パスワード等）は .env に保存する設計を前提とするため、.env を Git にコミットしないよう README / コメントで注意喚起を行っています（config_setup にも注意コメントあり）。

---

今後の予定（例）
- research.factor_research の完実装とテスト追加
- ExecutionEngine / Broker まわりのユニットテスト強化（MockBroker の挙動確認）
- モニタリングのアラート送信（LINE 等）実装
- パフォーマンス改善とドキュメント拡充

もし特定の変更点について詳細な説明や、CHANGELOG に記載する文言の修正希望があればお知らせください。