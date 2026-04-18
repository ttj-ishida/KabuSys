# Changelog

すべての変更は "Keep a Changelog" の形式に従い、セマンティックバージョニングを採用します。

## [0.1.0] - 2026-04-18

### 追加 (Added)
- 全体
  - 初回公開リリース。パッケージバージョンを `__version__ = "0.1.0"` として設定。

- 実行 / 監視スクリプト
  - src/kabusys/run_execution.py
    - ExecutionEngine を起動するエントリポイントを追加。
    - 起動時にプロセス優先度を "high" に設定。
    - KABUSYS_ENV が `paper_trading` の場合は paper_trading 用の専用 SQLite DB（デフォルト: `data/paper_trading.db`）を使用して本番 DB と完全分離する仕様を導入。
    - ブローカークライアントは BrokerClientFactory を経由して生成（環境に応じて Mock/実ブローカーを切替）。
    - RiskManager の初期設定（デフォルト設定を含む）を組み立てて ExecutionEngine に注入。初期ポートフォリオ値には broker.get_available_cash() を利用。
    - エンジンはデーモンスレッドで実行、`data/stop_requested.flag` の検知で安全に停止する仕組みを備える。
    - 実行時 pid ファイル出力 (`data/execution.pid`) をサポート。

  - src/kabusys/run_monitoring.py
    - SystemMonitor のポーリングループを起動するスクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値（0 以下・非数）の場合はデフォルトにフォールバックして警告を出す。
    - 監視は環境にかかわらず本番 `sqlite_path`（デフォルト: `data/monitoring.db`）を使用する（監視 DB は共通）。
    - 停止フラグファイル `data/stop_requested.flag` を検知してループを終了。
    - 例外発生時は例外をキャッチしてログ出力し、次のポーリングまで待機する堅牢化を実装。

- 設定管理
  - src/kabusys/config.py
    - .env 自動読み込み機能を導入（プロジェクトルートが特定できる場合、`.env` を読み込む。`.env.local` は OS 環境変数を保護しつつ上書き読み込み）。
    - .env パースを強化:
      - `export KEY=val` 形式に対応
      - シングル/ダブルクォート内のバックスラッシュエスケープを処理
      - クォートなし行でのインラインコメント処理を改善
    - Settings クラスを提供し、環境変数をプロパティとしてアクセス可能に:
      - J-Quants / kabu API トークン類、DuckDB/SQLite パス、paper_trading 用 DB パス、PID/Kill flag パス、監視閾値 (CPU/MEM/DISK) などをサポート。
      - PAPER_FILL_MODE のバリデーション（"instant" | "partial" | "never" | "reject"、デフォルト "instant"）を追加。
      - KABUSYS_ENV の有効値検査（`development`/`paper_trading`/`live`）とログレベルのバリデーションを追加。

  - src/kabusys/config_setup.py
    - 対話式の .env 作成ウィザードを追加。
    - J-Quants / kabu API 等の必須項目、DUCKDB/SQLITE パス、ログレベル、Kill Switch 関連などを対話的に設定して .env を書き出す。
    - 既存 .env の読み込み、シークレット値のマスク表示、保存前の確認プロンプトを実装。

  - src/kabusys/validate_config.py
    - 起動前に設定不備を検出する CLI を追加。
    - 必須環境変数の存在チェック、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ確認、`config/*.yaml` の存在確認（PyYAML があればパース検証）を実施。
    - `--strict` オプションで警告も失敗扱いにできる。
    - Live 環境向けの注意喚起（LINE 通知未設定や Kill Flag 自動クリア設定の警告）を追加。

- ツール
  - src/kabusys/tools/paper_verification_report.py
    - ペーパートレーディング用検証レポート生成スクリプトを追加。
    - system_status / trade_logs / risk_logs テーブルから稼働率、注文成功率、送信率、リスク却下数、API レイテンシ（平均・最大・P95）などを集計・判定。
    - 基準値（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200ms）を定義し PASS/FAIL 判定を行う。
    - コマンドライン引数で期間指定（--from/--to）と DB パス指定（--db）をサポート。環境変数 `PAPER_TRADING_SQLITE_PATH` にも対応。

- ポートフォリオ構築ライブラリ
  - src/kabusys/portfolio/portfolio_builder.py
    - 候補選定 (select_candidates)、等配分/スコア加重重み計算 (calc_equal_weights, calc_score_weights) を実装。
    - スコア全てが 0 の場合は警告を出し等配分にフォールバック。

  - src/kabusys/portfolio/risk_adjustment.py
    - セクター集中制限 (apply_sector_cap) を実装。既存保有を考慮して、1 セクター当たり上限比率を超える候補を除外。
    - レジームに応じた投下資金乗数 calc_regime_multiplier を実装（"bull":1.0, "neutral":0.7, "bear":0.3、未知レジームは 1.0 にフォールバックし警告）。

  - src/kabusys/portfolio/position_sizing.py
    - position sizing ロジックを実装。
    - allocation_method に "risk_based"、"equal"、"score" をサポート。
    - 単元株 (lot_size) に基づく丸め、1 銘柄上限・aggregate cap、コストバッファ（手数料/スリッページ見積り）による保守的な見積もり、スケーリングと端数処理（fractional remainder に基づく追加配分）を実装。
    - 価格欠損時のスキップやログ出力を実装。

- ユーティリティ
  - src/kabusys/utils/logging_setup.py
    - 統一的なロギング設定ユーティリティを追加。
    - stdout への StreamHandler と日次ローテーションの TimedRotatingFileHandler（デフォルト logs/<app_name>.log、30 日保持）をルートロガーに設定。
    - 環境変数 `LOG_DIR`、`LOG_LEVEL` に対応。ディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソールのみで継続。

  - src/kabusys/utils/process_priority.py
    - Windows / POSIX（Linux/Mac/FreeBSD）差分を吸収したプロセス優先度設定関数 set_process_priority を追加。
    - CPU affinity を最初の N コアに固定する set_cpu_affinity を追加（例外時は警告を出してスキップ）。
    - アクセス権限不足や未対応プラットフォームに対するフォールバックと警告処理を実装。

- 研究用 / ファクター計算
  - src/kabusys/research/factor_research.py（計算ロジックの骨組み）
    - DuckDB 接続を受けて Momentum / Value / Volatility / Liquidity 等のファクターを計算する設計を追加（calc_momentum を実装中の形跡あり）。
    - 設計方針・定数・スキャン範囲の定義を含む。

### 変更 (Changed)
- なし（初回リリースのため変更履歴は追加のみ）。

### 修正 (Fixed)
- なし（初回リリース）。

### 既知の注意点 / 補足
- .env 自動読み込みはプロジェクトルートの検出に依存する（`.git` または `pyproject.toml` を基準）。プロジェクトルートが特定できない場合は自動ロードをスキップします。自動ロードを無効化したい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- run_monitoring/run_execution は停止フラグファイル（data/stop_requested.flag）を用いて外部から安全に停止できます。Kill Switch 用の `KILL_FLAG_CLEAR_ON_START` なども設定可能です。
- POSITION SIZING 等の金融ロジックはドメインルールに基づく実装（丸め・上限・スケールダウン）を含みます。実運用前にパラメータのチューニングと広範なテストを推奨します。
- YAML 検証は PyYAML がインストールされている場合にのみ行われます。インストールされていない場合、YAML 内容検証はスキップされます。

---

今後の予定（例）
- factor_research の完全実装（ファクターの SQL/計算ロジック完了）
- テストカバレッジ拡充と CI パイプライン整備
- 発注まわりのモック／統合テストの追加

（必要があれば個別ファイルごとの詳細な変更点の追記を行います。）