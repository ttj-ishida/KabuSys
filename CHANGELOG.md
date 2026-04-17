# CHANGELOG

すべての変更は Keep a Changelog のフォーマットに準拠して記載しています。

## [0.1.0] - 2026-04-17

### 追加 (Added)
- 初期リリース。KabuSys の基本機能群を実装・追加。
- コア設定・環境変数管理
  - `kabusys.config.Settings` を導入。環境変数から設定を取得するためのプロパティを提供。
  - 自動 .env 読み込み機能を実装（プロジェクトルートの検出: .git または pyproject.toml を使用）。`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
  - .env のパース機能を強化（`export KEY=...` 形式サポート、シングル/ダブルクォート内のバックスラッシュエスケープ処理、インラインコメントの取り扱い）。
  - 主要な環境変数一覧（例: `JQUANTS_REFRESH_TOKEN`, `KABU_API_PASSWORD`, `DUCKDB_PATH`, `SQLITE_PATH`, `KABUSYS_ENV`, `LOG_LEVEL` など）を定義し、`Settings` 経由で参照可能に。

- 設定関連 CLI
  - `kabusys.config_setup`：対話式ウィザードで `.env` を初期作成/更新する CLI を追加。
    - デフォルトや既存値の再利用、シークレット入力のマスク表示、保存確認などの対話ワークフローをサポート。
  - `kabusys.validate_config`：起動前の設定検証 CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV 値検査、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在と（PyYAML インストール時の）パース検証、本番時のガードチェックを実施。
    - `--strict` オプションで警告も失敗扱いにできる。

- 実行・監視エントリポイント
  - `kabusys.run_execution`：ExecutionEngine を起動するスクリプトを追加。
    - 起動時にプロセス優先度を "high" に設定するユーティリティ呼び出しを行う。
    - `KABUSYS_ENV=paper_trading` の場合は paper 用 SQLite (`PAPER_TRADING_SQLITE_PATH` / デフォルト `data/paper_trading.db`) を使用し、本番 DB と分離（MockBrokerClient の利用は BrokerClientFactory 側で切替）。
    - エンジンはデーモンスレッドで実行され、`data/stop_requested.flag`（停止フラグ）を監視して安全に停止可能。PID ファイル指定 (`data/execution.pid` デフォルト)。
    - RiskManager/RiskConfig の初期パラメータを設定して起動。
  - `kabusys.run_monitoring`：SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL`（秒）でポーリング間隔を上書き可能（デフォルト 60 秒）。無効値は自動的にデフォルトへフォールバックしログ警告を出力。
    - Monitoring は KABUSYS_ENV に関係なく本番の `sqlite_path` を利用する設計（監視データは一元管理）。
    - 停止フラグ `data/stop_requested.flag` の検知でループ終了。
    - DB 初期化処理（`init_monitoring_db`）と DuckDB 接続を確立。

- ポートフォリオ構築・リスク関連
  - `kabusys.portfolio.portfolio_builder`
    - シグナル選別（スコア降順、タイブレーク: signal_rank）、等重量配分 (`calc_equal_weights`)、スコア加重配分 (`calc_score_weights`、全銘柄のスコアが 0 の場合は等配分へフォールバック）を追加。
  - `kabusys.portfolio.risk_adjustment`
    - セクター集中制限を適用する `apply_sector_cap` を追加（当日売却銘柄を除外、"unknown" セクターは制限対象外）。
    - 市場レジームに応じた投下資金乗数を返す `calc_regime_multiplier`（"bull"=1.0, "neutral"=0.7, "bear"=0.3、未知のレジームは警告して 1.0 にフォールバック）。
  - `kabusys.portfolio.position_sizing`
    - 複数の配分方式（`risk_based`, `equal`, `score`）に対応した株数計算 `calc_position_sizes` を実装。
    - 単元株（lot_size）丸め、per-position 上限（max_position_pct）、aggregate cap によるスケールダウン、cost_buffer を考慮した保守的見積り、余剰配分の再配分アルゴリズムを実装。

- 研究用ファクター計算
  - `kabusys.research.factor_research`
    - DuckDB の prices_daily/raw_financials テーブルを用いるモメンタム・ボラティリティ等のファクター計算関数を追加（例: mom_1m/mom_3m/mom_6m, ma200_dev, atr_20 等）。
    - データ不足時の None 扱い、P95 等の計算ロジックを備える設計。

- ユーティリティ
  - `kabusys.utils.process_priority`
    - Windows / POSIX（Linux/macOS/FreeBSD）差分を吸収してプロセス優先度を切替える `set_process_priority(level)` を追加。psutil の権限や未サポート環境では警告を出してスキップ。
    - CPU affinity 固定用 `set_cpu_affinity(cpu_count)` を追加（psutil が提供する機能を使用、エラー時は警告スキップ）。

- ツール
  - `kabusys.tools.paper_verification_report`
    - Paper Trading 用 SQLite DB（`PAPER_TRADING_SQLITE_PATH` / デフォルト `data/paper_trading.db`）から複数指標（稼働率、注文成功率、送信率、リスク却下数、平均/最大/P95 レイテンシ）を集計し検証レポートを生成する CLI を追加。
    - デフォルト基準値（稼働率 >= 99%、注文成功率 >= 90%、送信率 >= 95%、P95 レイテンシ <= 200ms）に基づく PASS/FAIL 判定を出力。

### 変更 (Changed)
- なし（初回リリースのため、主に新規追加）。

### 修正 (Fixed)
- なし（初回リリース。ただし各モジュールでエラー時の耐性（例: DB テーブル未存在時のハンドリング、psutil の例外処理、.env 読み込み失敗時の警告）を設けて堅牢化）。

### 注意点 / 破壊的変更 (Notes / Breaking Changes)
- 監視プロセス（run_monitoring）は KABUSYS_ENV にかかわらず settings.sqlite_path（デフォルト: data/monitoring.db）を使用します。監視データを分離したい場合は sqlite_path を明示的に変更してください。
- Paper Trading 実行は paper 用 SQLite（`PAPER_TRADING_SQLITE_PATH`）に記録され、本番 DB とは完全分離されます。paper 設定での DB 指定を誤ると意図せず本番 DB に書き込む可能性があるため注意してください。
- .env 自動読み込みはプロジェクトルート検出に依存します（.git または pyproject.toml）。プロジェクト配布後や特殊な配置では自動読み込みがスキップされる場合があります。必要に応じて `KABUSYS_DISABLE_AUTO_ENV_LOAD` を設定してください。
- `MONITOR_POLL_INTERVAL` は正の整数（秒）を期待します。不正値がセットされていると警告してデフォルト（60秒）にフォールバックします。

### セキュリティ (Security)
- シークレット値（トークン・パスワード等）は .env に平文で保存される設計です。.env は絶対にリポジトリにコミットしないでください（config_setup でも同様の注意を表示）。

---

開発チームへの補足:
- 各モジュールに詳細な単体テスト（特に position sizing のスケーリング・端数処理、.env のパース・マージ挙動、monitoring の停止フラグ処理）を追加することを推奨します。
- 将来的な拡張点として、銘柄ごとの lot_size を持つマスタ導入や、price のフォールバックロジック（risk_adjustment 内の TODO）を検討してください。