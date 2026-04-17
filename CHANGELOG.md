# Changelog

すべての重要な変更をこのファイルで記録します。フォーマットは「Keep a Changelog」に準拠します。  

※このファイルはリポジトリ内のコードから推測して作成した初期リリース向けの要約です。

## [0.1.0] - 初回リリース
リリース日: 2026-04-17

### 追加 (Added)
- 基本パッケージ情報
  - パッケージバージョンを `__version__ = "0.1.0"` として設定。

- 設定・環境変数管理
  - Settings クラス（kabusys.config）を実装し、環境変数を高レベルに提供。
  - .env 自動ロード機能を実装（プロジェクトルート検出: .git または pyproject.toml を基準）。
  - .env 読み込みのパーサを堅牢化（コメント、クォート、export 形式対応）。
  - 必須環境変数取得ヘルパー `_require()`。
  - 各種設定プロパティを提供（J-Quants、kabuステーション、LINE、DBパス、監視しきい値、実行環境等）。
  - PAPER_FILL_MODE の値検証（"instant" | "partial" | "never" | "reject"）。

- 設定用 CLI ウィザード
  - `kabusys.config_setup`：対話式ウィザードで .env を生成・更新するツールを追加。
  - デフォルト値・選択肢・シークレット入力のサポートおよび安全に .env を書き出す実装。

- 設定検証 CLI
  - `kabusys.validate_config`：.env と config/*.yaml の存在・基本整合性チェックを行う CLI を追加。
  - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性確認、DBパス・コンフィグ YAML の検証、ライブ環境向け追加警告を実装。
  - `--strict` オプションで警告を失敗扱いにできる。

- 実行エンジン起動スクリプト
  - `kabusys.run_execution`: ExecutionEngine の起動スクリプトを追加。
    - KABUSYS_ENV が `paper_trading` の場合は paper 用 SQLite（デフォルト: data/paper_trading.db）を使用して本番 DB と分離。
    - BrokerClientFactory を利用したブローカークライアント生成。
    - OrderRepository / OrderManager / RiskManager / Reconciler 等の組み立て。
    - エンジンは別スレッドで起動。stop flag（data/stop_requested.flag）を検出して安全停止。
    - 起動時にプロセス優先度を "high" に設定（utils/process_priority を使用）。
    - 実行中に PID ファイル（data/execution.pid）を利用。

- 監視ループ起動スクリプト
  - `kabusys.run_monitoring`: SystemMonitor を定期実行するスクリプトを追加。
    - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL` で上書き可能（デフォルト 60 秒）。
    - 監視は常に本番用 sqlite_path を参照（環境に依存せず本番監視 DB を使用）。
    - stop flag（data/stop_requested.flag）でループを終了。KeyboardInterrupt による終了もハンドリング。
    - プロセス優先度を "high" に設定。

- 監視 DB 初期化フック
  - monitoring_db 初期化ユーティリティ（init_monitoring_db）を参照して起動時に監視テーブルの存在を保証（冪等）。

- プロフィール／ポートフォリオ構築モジュール
  - `kabusys.portfolio` パッケージを追加。
    - portfolio_builder:
      - select_candidates: スコア順による候補選出（タイブレークは signal_rank）。
      - calc_equal_weights / calc_score_weights: 等配分・スコア加重の重み計算（スコア全0は等配分にフォールバック）。
    - risk_adjustment:
      - apply_sector_cap: セクター集中制限（既存保有を考慮して候補を除外、"unknown" セクターは無視）。
      - calc_regime_multiplier: レジームに応じた投下資金乗数（bull/neutral/bear マッピング、未知はフォールバック）。
    - position_sizing:
      - calc_position_sizes: 重み・方式（risk_based / equal / score）に基づく発注株数計算。
      - 単元株（lot_size）、max_position_pct、max_utilization、cost_buffer 等を考慮した集約キャップとスケーリングロジックを実装。
      - risk_based 方式でのリスク・ストップロスに基づく株数算出も実装。

- リサーチ / ファクター計算
  - `kabusys.research.factor_research` を追加。
    - DuckDB（prices_daily / raw_financials テーブル）を用いてファクター計算を行う純粋関数群。
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離の計算（データ不足時は None）。
    - calc_volatility: ATR20、相対ATR、20日平均売買代金、出来高比率の計算（不完全データ処理を考慮）。
    - 計算窓やスキャン日数の定数を定義。

- ツール
  - `kabusys.tools.paper_verification_report`:
    - Paper Trading 用検証レポート生成スクリプトを追加。
    - system_status / trade_logs / risk_logs テーブルから稼働率、注文成功率、送信率、レイテンシ（平均・最大・P95）を集計し PASS/FAIL 判定を出力。
    - デフォルト DB は環境変数 `PAPER_TRADING_SQLITE_PATH`（デフォルト: data/paper_trading.db）。
    - CLI オプションで期間（--from, --to）や DB パス（--db）を指定可能。

- プロセス優先度 / CPU affinity ユーティリティ
  - `kabusys.utils.process_priority` を実装。
    - Windows / POSIX を吸収してプロセス優先度（high/normal/low）を設定（psutil を使用）。
    - set_cpu_affinity: 最初の N コアにプロセスをピン留めする機能を追加。
    - 権限不足や未サポート環境でのフォールバック / ログ出力あり。

- 外部依存と DB
  - DuckDB と SQLite を併用する設計を採用（DuckDB は分析、SQLite は監視・発注履歴）。
  - psutil を利用したプロセス制御。

### 変更 (Changed)
- 該当なし（初回リリース）。

### 修正 (Fixed)
- 該当なし（初回リリース）。

### 削除 (Removed)
- 該当なし（初回リリース）。

### セキュリティ (Security)
- 該当なし。

### 注意事項 / 運用メモ
- run_monitoring は MONITOR_POLL_INTERVAL を環境変数で指定可能。0 以下や不正値はデフォルト（60 秒）にフォールバックして警告を出力。
- run_execution は paper_trading モードで本番 DB と完全に分離して動作（PAPER_TRADING_SQLITE_PATH を使用）。
- config の自動ロードはプロジェクトルートが検出できない場合はスキップされ、環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で明示的に無効化可能。
- Live 環境（KABUSYS_ENV=live）では validate_config がいくつかの注意喚起（LINE 通知設定未設定や KILL_FLAG_CLEAR_ON_START の危険性）を出力する。
- position_sizing 等の計算関数は純粋関数（副作用なし、DBアクセスなし）として設計されており、ユニットテストや再利用に適している。

---

今後のバージョンでは、既知の改善点（例: price フォールバック戦略、銘柄ごとの lot_size マッピング、より詳細なエラーハンドリングやロギングの拡充など）を反映していく予定です。