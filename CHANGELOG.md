# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠しています。セマンティックバージョニングを採用しています。

現在のバージョン: 0.1.0 — 2026-04-18

## [0.1.0] - 2026-04-18
### Added
- 基本アプリケーション骨格を実装
  - パッケージメタ情報を src/kabusys/__init__.py にて __version__="0.1.0" として定義。

- 起動スクリプト
  - 実行エンジン起動スクリプト（run_execution.py）を追加。
    - ExecutionEngine の起動、スレッド管理、停止フラグ（data/stop_requested.flag）による安全停止を実装。
    - KABUSYS_ENV が `paper_trading` の場合は paper_trading 用の SQLite（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）を使用し、本番 DB と分離。
    - 起動時にプロセス優先度を "high" に設定。
    - PID 管理（data/execution.pid）をサポート。
  - システム監視ポーリングループ起動スクリプト（run_monitoring.py）を追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は KABUSYS_ENV にかかわらず本番用 sqlite_path を使用する設計になっている（監視データは本番 DB に保存）。
    - stop フラグ（data/stop_requested.flag）検知でループを終了。
    - check_once() 実行中の例外はログに記録して次回ポーリングに継続。

- 設定管理
  - Settings クラス（src/kabusys/config.py）を実装し、環境変数経由の設定アクセスを提供。
    - J-Quants / kabu API / LINE / DB / 監視 / システム設定など主要設定をプロパティで公開。
    - PAPER_FILL_MODE のバリデーション（有効値: instant / partial / never / reject）。
    - KABUSYS_ENV の検証（development / paper_trading / live）と簡易判別プロパティ is_live / is_paper / is_dev。
  - 自動 .env ロード機能を実装（プロジェクトルートの検出: .git もしくは pyproject.toml を基準）。
    - .env と .env.local の読み込み順序を実装。
    - OS 環境変数は保護され上書きされない。
    - 自動ロードを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - .env パーサーの実装（クォート・エスケープ・コメント処理をサポート）。

- 設定支援 CLI
  - 対話式 .env ウィザード（src/kabusys/config_setup.py）を追加。
    - 設定項目一覧（KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, LINE_* 等）を対話的に作成・更新。
    - シークレット項目はマスク表示、保存前の確認、.env ファイル生成ロジックを提供。

- 設定検証 CLI
  - validate_config CLI（src/kabusys/validate_config.py）を追加。
    - 必須環境変数チェック、KABUSYS_ENV の検証、LOG_LEVEL 検証、DB パスの親ディレクトリ存在確認、config/*.yaml の存在確認（PyYAML がある場合はパース検証）、および本番時のガード（LINE 通知や KILL_FLAG_CLEAR_ON_START の確認）を実装。
    - --strict により warning を fail 扱いにできる。

- ロギングユーティリティ
  - 統一ログ設定ユーティリティ（src/kabusys/utils/logging_setup.py）を追加。
    - StreamHandler を stdout に出力（cron 等でのリダイレクトを想定）。
    - 日次ローテーションの TimedRotatingFileHandler（デフォルト logs/<app_name>.log、30日保持）を実装。
    - ログディレクトリ作成に失敗した場合はファイル出力をスキップしコンソール出力のみ継続する耐障害性を実装。
    - ログレベル解決順: 引数 > LOG_LEVEL 環境変数 > デフォルト(INFO)。

- プロセス制御ユーティリティ
  - process_priority（src/kabusys/utils/process_priority.py）を追加。
    - Windows と POSIX(Linux/Mac/FreeBSD) を吸収し、nice / Windows priority を設定。
    - CPU affinity を指定コア数に固定する set_cpu_affinity を実装。
    - 権限不足や未対応 OS の場合は安全にスキップして警告出力。

- ポートフォリオ構築モジュール
  - portfolio_builder（select_candidates / calc_equal_weights / calc_score_weights）を実装。
    - select_candidates はスコア降順、同点時は signal_rank 昇順でタイブレーク。
    - calc_score_weights は全スコアが 0 の場合に等配分にフォールバックし警告ログを出す。
  - risk_adjustment（apply_sector_cap / calc_regime_multiplier）を実装。
    - セクター集中制限: 既存保有セクター比率が閾値を超える場合に同セクターの新規候補を除外。unknown セクターは除外対象外。
    - レジーム乗数: bull/neutral/bear を 1.0/0.7/0.3 にマップし、未知レジームは警告のうえ 1.0 にフォールバック。
  - position_sizing（calc_position_sizes）を実装。
    - allocation_method に応じた株数算出（risk_based / equal / score）。
    - risk_based: risk_pct, stop_loss_pct に基づくベース株数計算。
    - equal/score: weight に基づく alloc、per-position 上限（max_position_pct）、lot_size（単元株）丸め。
    - aggregate cap 処理: 投資合計が available_cash を超える場合にスケールダウンして lot_size 単位で再配分（端数処理の再配分ロジックを含む）。
    - cost_buffer を考慮して保守的なコスト見積りを行う。

- リサーチ / ファクター計算（開始実装）
  - research/factor_research.py を追加（モメンタム / MA200 / ATR / ボラティリティ / 流動性などを計算するための設計方針と定数を含む）。
  - DuckDB を使った prices_daily / raw_financials を参照する設計（関数 calc_momentum の開始実装が含まれる）。

- Paper Trading 検証ツール
  - tools/paper_verification_report.py を追加。
    - Paper Trading の SQLite（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）からシステム稼働率、注文成功率、送信率、リスク却下数、API レイテンシ（平均/最大/P95）を集計してレポート出力。
    - 閾値を定義して PASS/FAIL 判定を行う（稼働率 >=99%、fill_rate >=90%、send_rate >=95%、P95 latency <=200ms）。
    - 日付フィルタ（--from / --to）と DB パス上書き (--db) をサポート。

- その他ユーティリティ / パッケージ構成
  - tools パッケージの追加（空 __init__）。
  - portfolio サブパッケージの __init__ を整備して主要関数を再エクスポート。

### Changed
- 監視データストレージの扱い
  - run_monitoring は KABUSYS_ENV にかかわらず設定の sqlite_path（監視 DB）を使用するよう明示的に実装（監視データは本番監視 DB に保存される想定）。

- .env 読み込みの優先度/保護ポリシー
  - 自動ロード実装で OS 環境変数を保護しつつ .env.local を .env 上書き用に読み込む方式を採用。テスト時や特殊用途向けに自動ロードを無効化できるオプションを追加。

### Fixed / Robustness
- .env パーサーの堅牢化
  - クォート付き値のバックスラッシュエスケープ処理対応、行内コメント処理の改善を実装。
  - export KEY=val 形式への対応。

- ロギング周りのフォールバック
  - ログディレクトリ作成失敗時にファイルハンドラ生成をスキップして標準出力ログのみ継続することで起動失敗を回避。

- プロセス優先度 / CPU affinity の権限・プラットフォーム差異を許容
  - 権限不足や未実装 API 呼び出しに対して安全にスキップし、警告を出す実装。

### Known issues / Notes
- research/factor_research.calc_momentum の実装が途中（ソースファイル末尾が切れている／実装継続が必要）。DuckDB を用いたファクター計算ロジックは設計方針が含まれるが、完全実装は今後の作業。
- run_monitoring は監視データに本番 sqlite_path を使用するため、開発環境で監視データを分離したい場合は別途設定や運用上の注意が必要。
- position_sizing の注記: price の欠損（0.0）の場合にエクスポージャーが過小評価される可能性があり、将来的な価格フォールバック（前日終値等）の採用を検討中。

---

今後のリリース案（例）:
- 0.1.1: factor_research の完全実装、ユニットテスト追加、CI での自動検証。
- 0.2.0: ExecutionEngine / Broker クライアント周りの詳細実装、発注フロー・モックの拡充、Paper Trading の自動検証パイプライン。

--- 

（この CHANGELOG はソースコードの内容から推測して作成しています。実際のコミット履歴や意図と差異がある場合があるため、正式な変更履歴は VCS の履歴を参照してください。）