# Changelog

すべての変更は「Keep a Changelog」準拠で記載しています。  
日付はリリース日を示します。

## [Unreleased]

(現在なし)

## [0.1.0] - 2026-04-17

### Added
- 全体
  - 初回公開リリース (パッケージバージョン: 0.1.0)。
  - パッケージ概要 (kabusys) とエクスポート定義を追加。

- 実行 / 監視
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - 起動時にプロセス優先度を "high" に設定。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite を使用して本番 DB と分離。
    - BrokerClientFactory を経由してブローカークライアントを生成。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み立て、ExecutionEngine を別スレッドで実行。停止フラグ (data/stop_requested.flag) による安全停止に対応。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番 sqlite_path を使用する挙動を明示。

- 設定とユーティリティ
  - config.py: Settings クラスを追加。環境変数／.env の読み込み・アクセスを管理。
    - プロジェクトルート自動検出（.git または pyproject.toml を基準）。
    - 自動 .env 読み込みの仕組み（OS 環境変数の保護機能あり）。
    - 各種設定プロパティを提供 (DB パス、KABUSYS_ENV、ログレベル、閾値など)。
    - PAPER_FILL_MODE 等の入力バリデーションを実装。
  - config_setup.py: 対話式 .env 作成/更新ウィザードを追加。
    - シークレット項目のマスク表示、デフォルト値提示、最終確認とファイル書き込み。
    - 生成される .env にコミットしない旨の注意を含めるテンプレート出力。
  - validate_config.py: 設定検証 CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL 値チェック、DB パスの親ディレクトリ検査、config/*.yaml の存在・パース検証（PyYAML 未インストール時は警告）。
    - --strict オプションで警告を FAIL 扱いにできる。

- ポートフォリオ構築関連（純粋関数群）
  - portfolio.portfolio_builder:
    - select_candidates: スコア降順・タイブレークに signal_rank を用いる候補選定。
    - calc_equal_weights: 等金額配分。
    - calc_score_weights: スコア加重配分（全銘柄スコアが 0 の場合は等金額へフォールバック、警告ログ）。
  - portfolio.risk_adjustment:
    - apply_sector_cap: セクター集中制限ロジック（既存保有のセクター比率に応じて候補を除外。"unknown" セクターは除外しない）。
    - calc_regime_multiplier: market regime に応じた投下資金乗数（bull/neutral/bear とフォールバック）。
  - portfolio.position_sizing:
    - calc_position_sizes: 各種配分方式 ("risk_based", "equal", "score") に対応した株数決定ロジック。
      - 単元株丸め (lot_size)、単銘柄上限 (max_position_pct)、aggregate cap とスケーリング、cost_buffer を考慮した保守的見積り。
      - スケールダウン時の残差 (fractional remainder) に基づく追加配分アルゴリズムを実装。

- 研究・ファクター計算
  - research.factor_research:
    - calc_momentum、calc_volatility 等のファクター計算関数を追加。
    - DuckDB 接続を受け取り SQL + Python で prices_daily / raw_financials を参照して計算する設計。
    - Momentum（1M/3M/6M、MA200 乖離）、ATR・流動性指標などを計算。

- ツール
  - tools.paper_verification_report:
    - Paper Trading 検証レポート生成スクリプトを追加。
    - 稼働率、注文成功率、送信率、P95 レイテンシ等を集計し PASS/FAIL を判定する閾値を定義。
    - 日付フィルタ、P95 計算、DB 存在チェックとフェールバック処理を実装。

- OS / プロセス関連ユーティリティ
  - utils.process_priority:
    - set_process_priority(level) を追加（Windows / POSIX を吸収して優先度設定）。
    - set_cpu_affinity(cpu_count) を追加（指定コア数へ固定、権限や未実装 API はログ警告でスキップ）。
    - psutil を利用し、権限不足や未対応 OS でのフォールバックを考慮。

### Changed
- .env 自動読み込みの戦略を明確化：
  - 読み込み順: OS 環境変数 > .env.local > .env
  - OS 環境変数を protected として .env の上書きを防止。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート。

- 監視 / 実行の DB 接続仕様を明示：
  - 監視 (run_monitoring) は環境にかかわらず sqlite_path（本番監視 DB）を使用。
  - 実行 (run_execution) は paper_trading 環境時に paper_sqlite_path（data/paper_trading.db）を使用して DB を完全分離。

- 起動時のプロセス優先度設定を各起動スクリプトで最初に行うよう統一。

### Fixed
- MONITOR_POLL_INTERVAL の取り扱いを堅牢化（run_monitoring.py）。
  - 非整数値や 0 以下の値を受けた場合は警告を出してデフォルト（60 秒）にフォールバック。
- .env パーサ (_parse_env_line) の改善（config.py）：
  - export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ処理、コメント判定の改善などにより .env の記述をより正確にパース。
- validate_config の挙動改善：
  - PyYAML 未インストール時に YAML 検証をスキップして警告を出す安全なフォールバック。
  - KABUSYS_ENV=live 時の追加ガード（LINE トークンや KILL_FLAG_CLEAR_ON_START の危険な設定に関する警告）。
- position sizing / risk adjustment の細かな耐障害性改善：
  - 価格欠損時は適切にスキップして過少評価による期待外れ動作を低減。
  - スケーリングロジックで整数単元（lot_size）に丸め、端数分配を安定化。

### Documentation / UX
- config_setup ウィザードでシークレットはマスク表示、最終確認プロンプトを追加し誤操作を防止。
- paper_verification_report の出力を読みやすいレポート形式に整形し、データ不足時の説明を追加。
- ログメッセージは日本語で統一し、運用者にわかりやすい情報を出力するよう改善。

### Security
- .env の取扱いに関する注意 (config_setup の生成ヘッダー) を明示：.env を絶対に Git にコミットしないよう文書化。
- 環境変数の必須チェックでプレースホルダ値（例: _here / your_value）を警告対象にして、誤ったまま本番に投入するリスクを低減。

### Known limitations / Notes
- research.factor_research モジュールは DuckDB の prices_daily / raw_financials テーブル前提で実行される（DB スキーマ準備が必要）。
- 一部の機能（例: ExecutionEngine, SystemMonitor 等）はこのリリースでは参照のみ（内部実装の詳細は別モジュールに依存）。本番運用前に validate_config やウィザードで設定検証を推奨。
- process_priority / set_cpu_affinity は権限やプラットフォーム依存のため、権限不足時は警告を出して処理をスキップする。

---

以上。今後のリリースではテストカバレッジの拡充、ドキュメント (API/運用手順) の追加、各アルゴリズムのパラメータ調整用設定の外出し等を計画しています。