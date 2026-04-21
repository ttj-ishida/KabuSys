# CHANGELOG

すべての重要な変更はこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠し、セマンティックバージョニングを採用します。

現在のバージョン: 0.1.0

## [Unreleased]
- 開発中の変更はここに記載します。

## [0.1.0] - 2026-04-21
初回リリース。KabuSys 自動売買フレームワークの基礎機能を実装します。

### 追加 (Added)
- 基本パッケージ構成
  - パッケージ名: `kabusys`
  - バージョン: `__version__ = "0.1.0"`

- 設定 / 環境変数管理
  - `kabusys.config.Settings` による環境変数ラッパーを実装。
  - .env 自動読み込み機能を提供（プロジェクトルートを .git または pyproject.toml で検出）。
  - 自動ロードは `KABUSYS_DISABLE_AUTO_ENV_LOAD` 環境変数で無効化可能。
  - 必須設定の取得ヘルパー `_require` 実装。
  - 主要な設定プロパティを提供（例: `JQUANTS_REFRESH_TOKEN`, `KABU_API_PASSWORD`, `DUCKDB_PATH`, `SQLITE_PATH`, `PAPER_FILL_MODE` 等）。
  - `PAPER_FILL_MODE` の有効値チェック（instant/partial/never/reject）。

- 環境設定ウィザード CLI
  - `kabusys.config_setup`:
    - インタラクティブに `.env` を作成・更新するウィザードを実装。
    - シークレットのマスク表示、選択肢サポート、既存 `.env` 読み込み。
    - `.env` 書き出しテンプレートを提供（Git へのコミットを避ける旨のコメント含む）。
    - 実行例: `python -m kabusys.config_setup`

- 設定検証 CLI
  - `kabusys.validate_config`:
    - 必須環境変数・ログレベル・DB パス・config/*.yaml の存在とパース（PyYAML が存在する場合）・本番環境向けの追加ガードを検証。
    - `--strict` オプションで警告をエラー扱い可能。
    - 実行例: `python -m kabusys.validate_config`

- ロギングセットアップユーティリティ
  - `kabusys.utils.logging_setup.setup_logging`:
    - ルートロガーに StreamHandler (stdout) と TimedRotatingFileHandler（日次ローテーション、30 日分保持）を設定。
    - ログレベル／ログディレクトリの解決順（引数 > 環境変数 > デフォルト）。
    - ログディレクトリ作成失敗時はファイル出力をスキップし、標準出力のみで動作。

- プロセス優先度 / CPU affinity ユーティリティ
  - `kabusys.utils.process_priority`:
    - `set_process_priority(level)` で Windows/Linux/Mac に対応した優先度設定を実装（"high"/"normal"/"low"）。
    - `set_cpu_affinity(cpu_count)` で最初の N コアにプロセスをピン固定する機能を提供。
    - 権限不足や未対応 OS での安全なフォールバック（警告）を実装。

- 実行エンジン起動スクリプト
  - `kabusys.run_execution`:
    - `ExecutionEngine` を組み立てて実行する起動スクリプトを実装。
    - 起動時にプロセス優先度を "high" に設定。
    - DB 接続:
      - `KABUSYS_ENV=paper_trading` の場合は Paper Trading 用 SQLite（デフォルト: `data/paper_trading.db`）を使用し、本番 DB と完全分離。
      - 監視テーブル存在保証のため `init_monitoring_db` を呼ぶ。
    - Broker クライアントは `BrokerClientFactory.create(settings)` で環境に応じた実装を選択（paper_trading では Mock を想定）。
    - `ExecutionEngine.run_session()` をデーモンスレッドで起動、停止フラグ（data/stop_requested.flag）検知で安全停止。
    - PID ファイルのサポート（`data/execution.pid` 等）。

- 監視ループ起動スクリプト
  - `kabusys.run_monitoring`:
    - `SystemMonitor` を作成してポーリングループを実行。
    - デフォルトのポーリング間隔は 60 秒。`MONITOR_POLL_INTERVAL` 環境変数で上書き可能（不正値はデフォルトにフォールバックして警告）。
    - 監視用 DB は環境にかかわらず本番の `sqlite_path` を使用（監視は実データ参照想定）。
    - 停止フラグ（data/stop_requested.flag）検知でループを終了。
    - 起動時にプロセス優先度を "high" に設定。

- ポートフォリオ構築ライブラリ
  - `kabusys.portfolio`:
    - `portfolio_builder`:
      - 候補選択 `select_candidates`（スコア降順、同点は signal_rank でタイブレーク）。
      - 等配分 `calc_equal_weights`、スコア加重 `calc_score_weights`（全スコアが 0 の場合は等配分にフォールバック）。
    - `risk_adjustment`:
      - `apply_sector_cap`: セクター集中上限を適用して候補をフィルタ。未知セクターは適用除外。
      - `calc_regime_multiplier`: 市場レジームに応じた投下資金乗数（bull/neutral/bear）を返す（未知レジームは 1.0 にフォールバック）。
    - `position_sizing`:
      - `calc_position_sizes` により、"risk_based"/"equal"/"score" の配分方式に基づき各銘柄発注株数を算出。
      - 単元株丸め（lot_size）、per-stock 上限・aggregate cap（available_cash）によるスケーリング、cost_buffer による保守見積りを実装。
      - lot 単位での端数処理を行い、残余キャッシュを用いて優先度（fractional remainder）に基づく追加配分を実施。

- Paper Trading 検証ツール
  - `kabusys.tools.paper_verification_report`:
    - Paper Trading 用 SQLite（デフォルト: `data/paper_trading.db`）から統計を集計し、検証レポートを生成する CLI ツールを実装。
    - 指標:
      - 稼働率（uptime_pct）、ポーリング数、エラー数
      - 注文成功率（Filled / Created）、送信率（Sent / Created）
      - リスク却下数（risk_logs）
      - API レイテンシ（avg/max/P95）
    - Pass/Fail 基準（デフォルト）:
      - 稼働率 >= 99.0%
      - 注文成功率 >= 90.0%
      - 送信率 >= 95.0%
      - P95 レイテンシ <= 200 ms
    - CLI オプション: --from / --to（YYYY-MM-DD）、--db（DB パスの上書き）
    - P95 計算、欠損データ時の N/A 表示、DB が存在しない場合の明確なエラーメッセージを実装。

- リサーチ / ファクター計算の骨組み
  - `kabusys.research.factor_research`:
    - Momentum / Value / Volatility / Liquidity 系ファクターの設計方針と定数を定義。
    - DuckDB 接続経由で prices_daily / raw_financials を参照して計算する設計。
    - モメンタム計算関数 `calc_momentum` のインターフェースと説明を実装（計算ロジック続行予定）。

### 変更 (Changed)
- N/A（初回リリースのため該当なし）

### 修正 (Fixed)
- N/A（初回リリースのため該当なし）

### 破壊的変更 (Breaking Changes)
- N/A（初回リリースのため該当なし）

### セキュリティ (Security)
- 環境変数やシークレットは `.env` に記載して管理する設計。`.env` の Git へのコミットを明示的に避ける警告をウィザードで出力。

---

補足:
- 多くの機能は外部実装（例: `ExecutionEngine`, `SystemMonitor`, Broker クライアント等）に依存するため、本リリースでは起動スクリプト・ユーティリティ・純関数ライブラリ・CLI ツールといったインフラ周りを中心に実装しています。今後のリリースでは戦略モデル・エンジン内部・DuckDB を用いたファクター計算の具体実装・テストカバレッジの追加を予定しています。