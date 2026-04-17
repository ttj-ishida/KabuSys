# Changelog

すべての注目すべき変更履歴を記録します。本ファイルは Keep a Changelog の形式に準拠します。

※このリリースはコードベースから推測して作成した初回リリースノートです（実装ファイル群を要約）。

## [0.1.0] - 2026-04-17

### 追加 (Added)
- 実行エントリ・運用スクリプト
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` によりポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は KABUSYS_ENV にかかわらず本番用の SQLite パスを使用して DB に接続。
    - 停止フラグファイル（data/stop_requested.flag）を検知して安全にループを終了。
    - プロセス優先度を起動時に "high" に設定。
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - `KABUSYS_ENV=paper_trading` の場合はペーパートレード用の MockBrokerClient を使用し、専用 SQLite（デフォルト: data/paper_trading.db）に記録して本番 DB と分離。
    - 停止フラグと実行 PID 管理（data/execution.pid）に対応。バックグラウンドスレッドで engine を実行し、停止フラグ検知で安全停止。
    - プロセス優先度を起動時に "high" に設定。

- 設定・環境管理
  - config.py: Settings クラスを提供。環境変数から各種設定を取得するプロパティを実装。
    - DUCKDB/SQLite パス、PID/kill フラグのパス、監視閾値（CPU/MEM/DISK）などを取得可能。
    - `PAPER_FILL_MODE` の検証（有効値: instant/partial/never/reject）。
    - `KABUSYS_ENV` の値検証（development / paper_trading / live）。
    - 自動 .env 読み込み機構（プロジェクトルートを検出して .env / .env.local をロード。OS 環境変数は保護）。`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
  - config_setup.py: 対話式 .env 作成/更新ウィザードを追加。
    - デフォルト値・選択肢・シークレット入力等に対応し、結果を .env に保存。
  - validate_config.py: 設定検証 CLI を追加。
    - 必須環境変数の存在、KABUSYS_ENV の整合性、LOG_LEVEL、DB パス親ディレクトリ存在チェック、config/*.yaml の存在と（PyYAML があれば）パース検証、本番環境向けのガードチェックを実行。
    - `--strict` オプションで警告も失敗扱いにできる。

- ポートフォリオ構築関連（純粋関数群）
  - portfolio/portfolio_builder.py:
    - select_candidates: BUY シグナルをスコア降順（タイブレーク: signal_rank）で上位 N を選定。
    - calc_equal_weights: 等金額配分（1/N）。
    - calc_score_weights: スコア正規化配分。全銘柄スコアが 0 の場合は等配分へフォールバック（警告を出力）。
  - portfolio/risk_adjustment.py:
    - apply_sector_cap: セクター集中上限チェック。既存保有のセクター比率が閾値を超える場合、そのセクターの新規候補を除外（"unknown" セクターは無視）。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull:1.0, neutral:0.7, bear:0.3）。未知レジームは 1.0 にフォールバック（警告）。
  - portfolio/position_sizing.py:
    - calc_position_sizes: 複数配分方式をサポート（risk_based, equal, score）。ロット丸め（lot_size）や per-position 上限、aggregate cap（available_cash に基づくスケーリング）、cost_buffer（スリッページ・手数料見積）を実装。価格欠損時のスキップや安全弁（_max_per_stock）を考慮。

- ユーティリティ
  - utils/process_priority.py:
    - set_process_priority(level): Windows / POSIX の差分を吸収してプロセス優先度を設定。未対応 OS やアクセス拒否時は警告ログを出してスキップ。
    - set_cpu_affinity(cpu_count): 指定コア数に CPU affinity を設定（エラー時は警告してスキップ）。
  - utils パッケージ初期化。

- リサーチ・ファクター計算
  - research/factor_research.py:
    - momentum, volatility 等の定量ファクター計算を実装（DuckDB 接続を受け取り SQL で計算）。
    - モメンタム（1M/3M/6M、MA200 乖離）、ATR（20日）、出来高・売買代金系指標などを算出。データ不足時は None を返す設計。

- ペーパートレード検証ツール
  - tools/paper_verification_report.py:
    - ペーパートレード SQLite を読み取り検証レポートを生成する CLI を追加。
    - レポート指標: 稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、P95 レイテンシ、リスク却下数等。
    - デフォルト合格閾値を定義（例: 稼働率 >= 99.0%、P95 <= 200 ms 等）。日付フィルタ（--from / --to）と DB パスオーバーライド（--db）に対応。
    - P95 計算ユーティリティ実装。

- パッケージ情報
  - src/kabusys/__init__.py にバージョン __version__ = "0.1.0" を設定。

### 変更 (Changed)
- 設定読み込みの優先順位を明確化: OS 環境変数 > .env.local > .env（.env.local は .env を上書き）。
- .env パーサが export 形式、クォート、バックスラッシュエスケープ、インラインコメントを解釈するよう拡張。
- Monitoring と Execution の DB 接続振る舞いを明確化:
  - 監視は常に本番 sqlite_path を参照。
  - 実行（Execution）は paper_trading 環境では paper_sqlite_path を使用（本番と完全分離）。

### 修正 (Fixed)
- 各モジュールで DB 接続を finally で確実にクローズするよう実装（run_monitoring/run_execution 等）。
- process_priority: 未対応 OS やアクセス拒否時の例外をキャッチして安全にフォールバックするよう改善。

### 注意事項 (Notes)
- 本コードは複数の外部ライブラリ（psutil, duckdb, sqlite3, PyYAML（任意））に依存します。validate_config は PyYAML がない場合は YAML の検証をスキップして警告します。
- .env は機密情報を含むため絶対にリポジトリにコミットしないでください（config_setup にも注意喚起文を記載）。
- run_monitoring/run_execution はプロダクション環境で使用する際、KABUSYS_ENV や kill/stop フラグ、PID 管理の運用ルールを遵守してください（validate_config の本番ガード警告を参照）。

### 既知の制約 / TODO（コード中注記より）
- position_sizing: lot_size を将来的に銘柄別に拡張することが想定されている。
- risk_adjustment.apply_sector_cap: price が欠損時にエクスポージャーが過小見積もりされる可能性があり、将来的に代替価格フォールバックを検討する旨がコメントで残されている。
- research/factor_research の一部は大規模テーブルを想定しており、DuckDB の最適化やメモリ要件に注意が必要。

---

今後のリリースでは、実際の動作確認・統合テスト結果に基づくバグ修正、詳細なログ改善、設定の柔軟化、さらに戦略・実行ロジックの洗練化などを反映していく予定です。