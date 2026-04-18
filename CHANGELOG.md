# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠し、Semantic Versioning を想定しています。

- リリース履歴はコードベースから推測して作成しています。実際のコミット履歴と差異がある可能性があります。
- 日付はこのドキュメント作成日 (2026-04-18) を使用しています。

## [Unreleased]

### Added
- なし（次回リリースへ）

### Known issues / Notes
- research/factor_research モジュール中の関数定義が途中で終わっている箇所があり（calc_momentum の途中）、未実装または部分実装の可能性があります。リリース前に完成させることを推奨します。

---

## [0.1.0] - 2026-04-18

### Added
- 基本アーキテクチャと主要 CLI / ランタイムスクリプトを追加
  - run_execution.py
    - ExecutionEngine を起動するエントリーポイント。
    - KABUSYS_ENV に応じて paper_trading 向けに専用 SQLite（デフォルト: data/paper_trading.db）を使用する分離設計。
    - BrokerClientFactory 経由でブローカークライアントを取得し、OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて実行スレッドで engine.run_session を開始。
    - 停止フラグ (data/stop_requested.flag) により安全に停止可能。実行 PID を data/execution.pid に記録する想定（pid_file を受け取る設計）。
    - RiskConfig のデフォルト値を設定（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker_errors, circuit_breaker_window_sec, max_drawdown, initial_portfolio_value を指定）。

  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正な値はデフォルトにフォールバックして警告を出力。
    - 監視処理は監視用 DB（settings.sqlite_path）および DuckDB を使用。停止フラグ検知でループを終了し、KeyboardInterrupt をハンドリングして終了処理を行う。

  - config.py
    - 環境変数管理クラス Settings を実装（プロパティ経由で型変換・バリデーションを実施）。
    - .env 自動読み込み機能を提供（プロジェクトルートを .git / pyproject.toml から探索）。.env と .env.local のローディング順を実装し、OS 環境変数の保護（protected）を実装。
    - 各種設定項目をプロパティ提供（J-Quants / kabu API / LINE / DuckDB / SQLite / Paper Trading / 監視閾値 / システム環境など）。
    - KABUSYS_ENV / LOG_LEVEL / PAPER_FILL_MODE 等のバリデーションを実装。

  - config_setup.py
    - 対話式 .env 作成ウィザードを実装。既存 .env 読み込み、対話プロンプト、秘密項目のマスク表示、ファイル書き出しをサポート。
    - 書き出しテンプレートはコメント付きで、.env を誤ってコミットしない旨を明記。

  - validate_config.py
    - 起動前設定検証 CLI を追加。必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パス（親ディレクトリ存在確認）、config/*.yaml の存在と（PyYAML があれば）パース検証を行う。
    - --strict オプションで警告を FAIL 扱いにできる。

  - utils/logging_setup.py
    - 一貫したログ設定ユーティリティを追加。
    - コンソール出力は stdout 利用（cron 等のリダイレクトに配慮）。
    - 日次ローテーションする TimedRotatingFileHandler を設定（デフォルト logs/<app_name>.log、30 日分保持）。
    - LOG_DIR / LOG_LEVEL の解決ルールを実装し、ディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。

  - utils/process_priority.py
    - プロセス優先度・CPU affinity 設定ユーティリティを追加。
    - Windows（psutil の PriorityClass を使用）および POSIX（nice 値）に対応。例外・アクセス拒否時は警告を出して処理をスキップする安全設計。
    - set_cpu_affinity によるコア固定機能も提供。

  - portfolio パッケージ（純粋関数群）を追加
    - portfolio_builder.py
      - select_candidates: シグナルをスコア降順、タイブレークは signal_rank で整列。
      - calc_equal_weights / calc_score_weights: 等金額配分とスコア正規化配分（スコア合計が 0 の場合は等配分にフォールバック）。
    - risk_adjustment.py
      - apply_sector_cap: 既存保有のセクター別エクスポージャーに基づく新規候補フィルタリング。unknown セクターは除外しない（制限適用外）。
      - calc_regime_multiplier: market レジームに応じた投下資金乗数（bull=1.0, neutral=0.7, bear=0.3）。未知レジームは警告を出して 1.0 にフォールバック。
    - position_sizing.py
      - calc_position_sizes: allocation_method に応じて発注株数を計算（risk_based / equal / score をサポート）。
      - 単元株（lot_size）丸め、1 銘柄上限、aggregate cap（available_cash）によるスケーリング、cost_buffer による保守的見積り、端数配分ロジックを実装。

  - research/factor_research.py
    - ファクター計算モジュールを追加（Momentum / Value / Volatility / Liquidity を想定）。DuckDB の prices_daily/raw_financials を参照する設計で、結果を (date, code) キーの dict リストで返す方針を明記。
    - （注）モジュール内に未完の箇所あり（calc_momentum の途中で終端）。

  - tools/paper_verification_report.py
    - ペーパートレード検証レポート生成スクリプトを追加。
    - 指標: 稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、レイテンシ（avg/max/P95）、リスク却下数などを算出して判定（PASS/FAIL）を出力。
    - デフォルト閾値を設定（稼働率 >=99%、成立率 >=90%、送信率 >=95%、P95 <=200ms）。
    - --from/--to/--db オプションで期間・DB を指定可能。PAPER_TRADING_SQLITE_PATH 環境変数も考慮。

### Changed
- ロギング・プロセス管理周りの設計方針を統一
  - 起動スクリプトから setup_logging() と set_process_priority("high") を常に実行するように統一しているため、運用時のログ／優先度が一貫化。

- .env の読み込み挙動
  - OS 環境変数を保護する protected ロジックを導入。.env.local は .env の上書きとして読み込まれる。

### Fixed
- 環境変数パースの改善
  - config._parse_env_line でクォート内のバックスラッシュエスケープやインラインコメント処理、export KEY=val 形式への対応などを実装し、より堅牢に .env をパースするようにした。
- ログディレクトリ作成失敗時のフォールバック
  - FileHandler の作成に失敗した場合でもコンソール出力は継続するように例外処理を強化。

### Security
- シークレット値を対話式ウィザードでマスク表示（config_setup）し、.env にシークレットを平文で保存する旨の注意文を追加（.env の誤コミット防止を強調）。

### Removed
- なし

---

## Notes / 今後の改善候補
- research/factor_research の未完部分（calc_momentum の実装完了）を優先対応すること。
- position_sizing の価格欠損（price == 0.0）の扱いに関する TODO があるため、前日終値や取得原価でのフォールバック実装を検討。
- apply_sector_cap は "unknown" セクターを制限しない設計だが、運用要件に応じて unknown の扱い（保守的に制限する等）を見直すべき。
- tests が含まれていないため、ユニットテスト/統合テストの整備を推奨。
- ドキュメント（README、運用手順、デプロイ手順）およびコンフィグ生成スクリプト（scripts/generate_config.py の存在示唆あり）を明確化すること。

---

（この CHANGELOG はコード内容から推測して作成しています。実際の変更履歴やバージョン管理の履歴と差がある可能性があります。）