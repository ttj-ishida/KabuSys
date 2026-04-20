# Changelog

すべての変更は Keep a Changelog の慣習に従って記載しています。重要: 日付はコード提出時点の推測日を使用しています。

## [Unreleased]

（なし）

## [0.1.0] - 2026-04-20

初回公開リリース。以下の機能群を実装・公開しました。

### Added
- 実行用スクリプト
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。プロセス優先度を高に設定して起動します。
    - KABUSYS_ENV が `paper_trading` の場合は MockBrokerClient を使用し、paper_trading 用の専用 SQLite DB（デフォルト: `data/paper_trading.db`）に記録して本番 DB と分離します。
    - 実行中の停止制御はプロジェクトルートの `data/stop_requested.flag` を監視し、フラグ検知でエンジンを安全に停止します。
    - 実行 PID を `data/execution.pid` に書き込む仕様をサポート（Engine に渡されます）。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL`（デフォルト 60 秒）で上書き可能。
    - 監視コンポーネントは環境にかかわらず「本番」用の sqlite_path を使用する設計（監視データは一元管理）。
    - 停止フラグ（`data/stop_requested.flag`）検知や KeyboardInterrupt に対応して安全にクローズします。
    - monitor.check_once() 呼び出しで例外が発生してもログ化してループを継続する耐障害性を持たせています。

- 設定管理
  - config.py
    - .env / .env.local の自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml を探索して検出）。OS 環境変数は保護され上書きされません。
    - .env のパースは `export KEY=...`、シングル／ダブルクォート、バックスラッシュエスケープ、インラインコメント等に対応する堅牢な実装。
    - 多数の環境変数プロパティを提供（J-Quants, kabu API, DuckDB/SQLite パス, PAPER_FILL_MODE, PAPER_TRADING_SQLITE_PATH, PID/KILL フラグパス, CPU/MEM/DISK 閾値, KABUSYS_ENV 判定, LOG_LEVEL 等）。
    - `Settings` クラスとデフォルト設定を提供し、`settings = Settings()` により容易に利用可能。
  - config_setup.py
    - 対話式ウィザードで .env を初期作成・更新する CLI を追加。入力のヒントや既存値の再利用、シークレット項目のマスク表示などを実装。
    - 保存前に設定の確認・キャンセルが可能。テンプレート形式で .env を出力します（.env を Git にコミットしない旨の注意を記載）。
  - validate_config.py
    - 起動前検証用 CLI を追加。必須環境変数の有無、KABUSYS_ENV 値、LOG_LEVEL、DB パスの親ディレクトリ存在、config/*.yaml の存在とパース（PyYAML がない場合は検証をスキップして警告）をチェックします。
    - `--strict` オプションを指定すると警告も失敗扱い（exit(1)）になります。

- ロギング / プロセス制御ユーティリティ
  - utils/logging_setup.py
    - ルートロガーに対し StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション、デフォルト 30 日保持）を設定する共通ユーティリティを追加。
    - ログレベルは関数引数、環境変数 `LOG_LEVEL`、デフォルトの順で解決。ログディレクトリは引数 > 環境変数 `LOG_DIR` > `logs/` の順で解決。
    - ログディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソールのみで継続。
  - utils/process_priority.py
    - プラットフォーム差を吸収するプロセス優先度設定ユーティリティを追加。Windows（HIGH_PRIORITY_CLASS 等）と POSIX 系（nice 値）をサポート。
    - CPU affinity を最初の N コアに固定する set_cpu_affinity() を提供。
    - 権限不足などで設定できない場合は警告を出して安全にスキップします。

- ポートフォリオ構築ライブラリ（純関数群）
  - portfolio/portfolio_builder.py
    - シグナルのソート（スコア降順、同点は signal_rank 昇順）、候補選定 select_candidates を実装。
    - 等金額配分 calc_equal_weights、スコア加重 calc_score_weights（全銘柄のスコア合計が 0 の場合は等分配にフォールバック）を実装。
  - portfolio/risk_adjustment.py
    - apply_sector_cap：セクター別上限（max_sector_pct）に基づき新規候補を除外するロジックを実装。既存保有のエクスポージャー計算、"unknown" セクターは上限対象外。
    - calc_regime_multiplier：市場レジーム（bull/neutral/bear）に基づく資金乗数を実装。未知の値は警告を出して 1.0 にフォールバック。
  - portfolio/position_sizing.py
    - calc_position_sizes：allocation_method に応じた株数決定（"risk_based", "equal", "score" をサポート）。
    - 単元（lot_size）で丸め、1 銘柄上限（max_position_pct）、aggregate cap によるスケーリング、コストバッファ(cost_buffer) の考慮、端数分配アルゴリズムを実装。

- ツール
  - tools/paper_verification_report.py
    - ペーパートレーディング用の検証レポート生成ツールを追加。SQLite（デフォルト `data/paper_trading.db`）の trade_logs / system_status / risk_logs などを集計してレポートを出力します。
    - 主要指標: 稼働率（uptime）、注文成功率 (fill rate)、送信率 (send rate)、P95 レイテンシ等。閾値を超えると FAIL 判定になる仕様（デフォルト閾値をソース内定義）。
    - コマンドライン引数 `--from`, `--to`, `--db` をサポート。

- パッケージ情報
  - パッケージバージョンを `__version__ = "0.1.0"` として定義。

### Changed
- コード設計上の注意点（ドキュメント的な変更）
  - logging_setup では StreamHandler を stderr ではなく stdout に出力する仕様になっており、cron 等でのリダイレクト運用に適合させています。
  - .env の自動ロードは OS 環境変数を保護する挙動（.env.local は上書き可能だが OS 環境は優先）を取ります。自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。

### Fixed
- 実行時の頑健性向上
  - run_monitoring のポーリングループ内で monitor.check_once() が例外を投げた場合でも例外をキャッチしてログ出力し、次回ポーリングまで待機して継続するようにしました。
  - run_execution/run_monitoring 共に起動直後にプロセス優先度を変更することで、IO/CPU の競合をある程度緩和するようにしています（ただし権限がない場合はスキップ）。

### Deprecated
- なし

### Removed
- なし

### Security
- なし

---

参照・運用メモ（実装から推測）
- 起動スクリプトはそれぞれ main ガードを持つため `python -m kabusys.run_execution` 等で直接起動可能です。
- .env に機密情報（API トークン等）を保存する設計のため、リポジトリへ .env をコミットしないよう README 等で運用周知する必要があります（config_setup.py も同旨の注釈を出力します）。
- DB 周り（DuckDB / SQLite）は環境変数でパスを切り替え可能です。Paper Trading 用 DB は本番監視 DB と分離されています。

--- 

（注）本 CHANGELOG は提供されたソースコードの内容から推測して作成しています。実際のリリースノート作成時は実開発履歴（コミットログ、タスク管理）を元に適宜修正してください。