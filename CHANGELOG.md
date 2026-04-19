# Changelog

すべての notable な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。  
このプロジェクトの現在のバージョンは `0.1.0` です（`kabusys.__version__`）。

## [Unreleased]

## [0.1.0] - 2026-04-19
初回リリース。日本株自動売買システムのコアユーティリティ、実行・監視の起動スクリプト、ポートフォリオ構築ロジック、設定関連ツールおよび検証ツールを追加。

### 追加 (Added)
- パッケージ基盤・メタ
  - パッケージ初期化とバージョン定義を追加（`kabusys.__version__ = "0.1.0"`）。

- 設定管理
  - Settings クラスによる環境変数ラップを実装（`kabusys.config.Settings`）。
    - J-Quants / kabuステーション / LINE / DB / 監視閾値など主要設定をプロパティで提供。
    - `KABUSYS_ENV` の検証（`development` / `paper_trading` / `live`）。
    - `PAPER_FILL_MODE` の検証（"instant"|"partial"|"never"|"reject"）。
    - Paper Trading 用 DB パス（`PAPER_TRADING_SQLITE_PATH`）や PID ファイル・kill flag などを管理。
  - .env 自動ロード機能を実装
    - プロジェクトルート（.git または pyproject.toml を探索）発見時に `.env` / `.env.local` を読み込み。
    - OS 環境変数を保護しつつ `.env.local` で上書き可能。
    - `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で自動ロードを無効化可能。
  - .env のパース実装（クォート・エスケープ・コメント処理対応）。

- 設定ウィザード CLI
  - `kabusys.config_setup` に対話式ウィザードを追加。
    - .env の作成・更新を支援。主要項目（KABUSYS_ENV / JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD / DB パス / LOG_LEVEL / KILL_FLAG_CLEAR_ON_START 等）を対話的に入力。
    - 出力はテンプレート化された `.env` ファイル形式で保存。

- 設定検証 CLI
  - `kabusys.validate_config` に設定検証ツールを追加。
    - 必須環境変数チェック、KABUSYS_ENV・LOG_LEVEL の妥当性、DB パスや config/*.yaml の存在・パース（PyYAML が利用可能な場合）、
      本番時の追加ガード（LINE 設定・KILL_FLAG_CLEAR_ON_START）などを検査。
    - `--strict` モードで警告を失敗扱いにできる。

- 実行・監視起動スクリプト
  - ExecutionEngine 起動スクリプト（`kabusys.run_execution`）
    - 起動時にプロセス優先度を "high" に設定。
    - 環境が `paper_trading` の場合は Paper 用の SQLite DB を使用して本番 DB と完全分離。
    - BrokerClientFactory を使用してブローカークライアントを生成し、OrderRepository、OrderManager、RiskManager、Reconciler を組み立て ExecutionEngine を起動。
    - 停止フラグ（data/stop_requested.flag）を監視して安全にシャットダウン。
  - SystemMonitor 起動スクリプト（`kabusys.run_monitoring`）
    - `MONITOR_POLL_INTERVAL` 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は KABUSYS_ENV にかかわらず本番の sqlite_path を使用する設計。
    - 停止フラグの存在でループを終了。check_once() の例外をログに取り次のポーリングを継続。

- 監視 DB 初期化
  - `init_monitoring_db` の呼び出しにより必要な監視テーブルが存在することを保証（冪等）。

- ロギング・プロセス制御ユーティリティ
  - `kabusys.utils.logging_setup.setup_logging`
    - stdout へ StreamHandler、日次ローテートの TimedRotatingFileHandler（デフォルト logs/<app>.log）を設定。
    - ログレベル解決順（引数 > 環境変数 LOG_LEVEL > デフォルト "INFO"）。
    - ログディレクトリ作成失敗時はファイル出力をスキップしコンソール出力のみ継続。
  - `kabusys.utils.process_priority`
    - Windows/Linux/macOS を吸収するプロセス優先度設定（"high"/"normal"/"low"）。
    - CPU アフィニティ設定ユーティリティ `set_cpu_affinity` を追加。
    - 権限不足・未対応環境では警告を出してフォールバック。

- ポートフォリオ構築ライブラリ（純粋関数）
  - `kabusys.portfolio.portfolio_builder`
    - シグナル選定（score 降順、signal_rank でタイブレーク）`select_candidates`
    - 等配分・スコア加重の重み計算 `calc_equal_weights` / `calc_score_weights`（全スコアが 0 の場合に等配分へフォールバック）
  - `kabusys.portfolio.risk_adjustment`
    - セクター集中制限を適用する `apply_sector_cap`（特定セクターが上限を超えている場合に候補を除外）
    - 市場レジームに基づく投下資金乗数 `calc_regime_multiplier`（"bull"/"neutral"/"bear" のマップ、未知のレジームは 1.0 にフォールバック）
  - `kabusys.portfolio.position_sizing`
    - allocation_method に応じた株数決定 `calc_position_sizes`
      - "risk_based" / "equal" / "score" をサポート
      - 単元株（lot_size）丸め、per-position と aggregate の上限適用、cost_buffer を用いた保守的コスト見積り、
        available_cash に対するスケールダウンと端数処理ロジックを実装
    - 将来の拡張（銘柄ごとの lot_size マップなど）を想定した設計（TODO コメントあり）
  - `kabusys.portfolio.__init__` で主要関数をエクスポート

- リサーチ・ファクター計算（骨子）
  - `kabusys.research.factor_research` にモメンタム / MA200 / ATR / 流動性などのファクター計算モジュールを追加（DuckDB 接続を利用する設計。関数群は prices_daily / raw_financials のみ参照する方針）。
  - 設計に関する定数や API を定義（ただしソースは途中まで実装されている箇所あり）。

- ツール
  - Paper Trading 検証レポート生成スクリプト `kabusys.tools.paper_verification_report`
    - Paper Trading 用 SQLite（デフォルト data/paper_trading.db）から稼働率・注文成功率・送信率・レイテンシ等を集計してレポート出力。
    - P95 レイテンシ計算、閾値（稼働率 99%、成立率 90%、送信率 95%、P95 200ms）による PASS/FAIL 判定。
    - コマンドラインオプション `--from` / `--to` / `--db` をサポート。

### 変更 (Changed)
- 起動時共通の挙動
  - 起動スクリプトは最初にプロセス優先度を "high" に設定するよう統一。
  - 監視周りは本番監視 DB を必ず使用する設計（環境に依存しない監視データ採取）。

### 修正 (Fixed)
- データベース初期化が冪等に呼び出されるように `init_monitoring_db` を Execution/Monitoring の両方で呼び出し、監視テーブルの存在を保証。

### ドキュメント / 注意 (Notes)
- .env パーサーはシングル/ダブルクォートとバックスラッシュエスケープ、行内コメント（特定条件下）に対応する実装になっていますが、極端に複雑な .env のケースは未検証の可能性があります。
- `kabusys.research.factor_research` の実装はファイル末尾で途中（コメント／コードが未完）になっている箇所があるため、完全なファクター計算は今後の実装が必要です。
- `position_sizing` の価格欠損時のフォールバック処理や lot_size の銘柄別対応は TODO コメントとして残っています。
- 起動スクリプトは停止フラグ（data/stop_requested.flag）や PID ファイル、kill flag 周りの運用を前提としているため、デプロイ手順にそれらを含める必要があります。
- ログディレクトリ作成やプロセス優先度設定は実行権限に依存するため、権限不足時にフォールバック動作（警告出力）となります。

---

この CHANGELOG はソースコードの内容から推測して作成しています。実際のリリースノートとして公開する際は、実装者による確認・追記を推奨します。