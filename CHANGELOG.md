# CHANGELOG

すべての重要な変更点を記録します。フォーマットは "Keep a Changelog" に準拠します。

全般方針:
- 可能な限りコードベースから推測して記載しています（実装コメント、CLI ヘルプ、デフォルト値、TODO コメント等に基づく）。
- 実運用時は実際のリリース日・バージョン運用ルールに合わせて更新してください。

## [Unreleased]

（なし）

## [0.1.0] - 2026-04-21

初回リリース — 基本機能の実装と CLI / ユーティリティ群の追加。

### 追加 (Added)
- 全体
  - パッケージ初期リリース。バージョンは `kabusys.__version__ = "0.1.0"`。
  - DuckDB / SQLite を用いたデータ基盤を使用する構成を導入（設定でパス指定可能）。
- 実行系 / 監視
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite（デフォルト: data/paper_trading.db）と MockBroker を利用して本番 DB と分離。
    - エンジンはバックグラウンドスレッドで動作し、 data/stop_requested.flag を監視して安全に停止可能。
    - 実行 PID ファイル管理（data/execution.pid）に対応。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。
    - POLL 間隔は環境変数 `MONITOR_POLL_INTERVAL` で上書き可（デフォルト 60 秒）。
    - 停止フラグ（data/stop_requested.flag）に対応。
    - 監視は常に本番用 sqlite_path を使用（環境に依存しない設計）。
- 設定管理
  - config.py: 環境変数・設定管理クラス `Settings` を追加。
    - 自動 .env ロード機能: プロジェクトルート（.git または pyproject.toml）を探索して `.env` / `.env.local` をロード（OS 環境変数は保護）。
    - `.env` ロードは `KABUSYS_DISABLE_AUTO_ENV_LOAD` で無効化可能（テスト用途）。
    - 各種設定プロパティを提供（J-Quants / kabu API / LINE / DB パス / 監視閾値 / 実行環境等）。
    - `paper_fill_mode` のバリデーション（instant/partial/never/reject）や `KABUSYS_ENV` の検証。
  - config_setup.py: 対話式 .env 作成ウィザードを追加。
    - .env の読み書き、既存値の再利用、機密値のマスク表示、保存確認を実装。
    - .env 生成テンプレートに注意書き（Git にコミットしないよう警告）を含む。
  - validate_config.py: 起動前設定検証 CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DUCKDB/SQLITE パス親ディレクトリチェック、config/*.yaml の存在とパース（PyYAML がインストールされている場合）を実施。
    - `--strict` オプションで警告も失敗扱いにできる。
    - 本番環境（KABUSYS_ENV=live）向けの追加ガード（LINE 設定や Kill Switch の注意喚起）。
- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - シグナルをスコア降順にソートして上位 N 件を選択する `select_candidates`。
    - 等金額配分（`calc_equal_weights`）とスコア加重配分（`calc_score_weights`）を実装。全スコアが 0 の場合は等配分にフォールバック。
  - portfolio/risk_adjustment.py
    - セクター集中上限を適用して候補を除外する `apply_sector_cap`。
    - 市場レジームに応じた投下資金乗数を返す `calc_regime_multiplier`（bull/neutral/bear のマッピング、未知レジームは警告して 1.0 でフォールバック）。
  - portfolio/position_sizing.py
    - 各銘柄の発注株数を計算する `calc_position_sizes` を実装。
    - risk_based / equal / score の割当方法に対応、単元株（lot_size）での丸め、per-position 上限や aggregate cap によるスケーリング、cost_buffer を考慮した保守的見積りを実装。
    - スケールダウン時に余剰キャッシュを考慮して残差ベースで追加配分するアルゴリズムを実装（再現性を保つため安定ソート）。
  - これらのポートフォリオ関数は「DB参照なし・純粋関数」として設計されている（メモリ内計算のみ）。
- ツール
  - tools/paper_verification_report.py: Paper Trading 検証レポート生成ツールを追加。
    - 稼働率、注文成功率（Filled/Created）、送信率（Sent/Created）、リスク却下数、API レイテンシ（avg/max/P95）等を集計し PASS/FAIL 判定を行う。
    - デフォルト閾値を定義（稼働率 99%、成立率 90%、送信率 95%、P95 ≤ 200 ms）。
    - --from/--to/--db の CLI オプション対応、DB 存在チェックとエラーメッセージ。
- ロギング / プロセス管理ユーティリティ
  - utils/logging_setup.py
    - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション、30日保持）を設定する `setup_logging` を実装。
    - 既存ハンドラのクリア処理、ログディレクトリ作成失敗時のフォールバック（コンソールのみ）に対応。
    - stdout を使うことで cron 等でのリダイレクト運用に配慮。
  - utils/process_priority.py
    - プラットフォーム差分を吸収してプロセス優先度を設定する `set_process_priority` と CPU affinity を設定する `set_cpu_affinity` を実装（psutil を利用）。
    - Windows / POSIX（Linux/Mac/FreeBSD）をサポートし、権限不足等で失敗した場合は警告して継続。

- モニタリング DB 初期化
  - monitoring.monitoring_db.init_monitoring_db を起動時に呼び、監視テーブルが存在することを冪等的に保証（monitoring と execution 両方で呼び出し）。

- リサーチ
  - research/factor_research.py: ファクター計算モジュールを追加（Momentum / Value / Volatility / Liquidity を想定）。
    - DuckDB 接続を受け取り prices_daily / raw_financials を参照してファクターを計算する設計。
    - 定数（窓長等）とモメンタム計算インターフェースを定義。

### 変更 (Changed)
- なし（初回リリースのため既存コードからの差分は無し）

### 修正 (Fixed)
- なし（初回リリース）

### 既知の問題 / 注意事項 (Known issues / Notes)
- portfolio/risk_adjustment.apply_sector_cap:
  - price が欠損（0.0）の場合、エクスポージャーが過少見積りされる可能性がある旨の TODO コメントあり。将来的に価格フォールバック追加を検討。
- portfolio/position_sizing:
  - 将来的に銘柄ごとの lot_size をサポートするための拡張（TODO コメント）。
- utils/logging_setup:
  - ログディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソール出力へフォールバックする。設定環境に応じて権限やパスを確認すること。
- utils/process_priority:
  - 優先度設定は OS および権限に依存するため、権限不足（psutil.AccessDenied 等）で失敗するケースがある。失敗時は警告ログでスキップする設計。
- research/factor_research.py:
  - ファイル末尾が未完（実装途中の痕跡あり）。モメンタム計算の実装が含まれるが途中で切れている可能性があるため、利用前に実装完了の確認が必要。

### セキュリティ (Security)
- 環境変数には機密情報（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等）を想定。`.env` は Git にコミットしないよう注意喚起を実装。
- config_setup にて機密値はマスク表示されるが、端末履歴等の取り扱いには注意。

### 破壊的変更 (Breaking Changes)
- なし（初回リリース）

---

履歴は実装のコメント・デフォルト値・CLI ヘルプ等から推測して作成しています。実際のリリースノートとして用いる際は、テスト結果・デプロイ手順・マイグレーション等の情報を追記してください。