# CHANGELOG

すべての注目すべき変更を記録します。  
フォーマットは Keep a Changelog に準拠しています。  

## [Unreleased]

（現在のスナップショットに対する未リリースの変更はありません）

---

## [0.1.0] - 2026-04-18

初回公開リリース。以下の主要コンポーネント・機能を含みます。

### Added
- 基本アプリケーション情報
  - パッケージバージョン: `kabusys.__version__ = "0.1.0"`。

- 設定管理
  - `kabusys.config.Settings`：環境変数からの設定取得を一元化。
  - 自動 `.env` ロード機能を実装（プロジェクトルートを `.git` または `pyproject.toml` で検出）。
  - `.env` ファイルのパースを厳密化：`export KEY=val`、シングル/ダブルクォート内のエスケープ、インラインコメントの扱いに対応。
  - OS 環境変数を保護する「protected」機能（上書き禁止）を導入。

- 環境設定ウィザード（CLI）
  - `kabusys.config_setup`：対話式ウィザードで `.env` の初期作成・更新を支援。
  - 秘匿項目は表示時にマスク。生成される `.env` ファイルは Git にコミットしないよう注意書きを出力。

- 設定検証（CLI）
  - `kabusys.validate_config`：起動前に環境変数と `config/*.yaml` の存在・基本整合性を検証。  
  - `--strict` オプションで警告も失敗扱いにできる。
  - PyYAML 未インストール時は YAML 検証をスキップして警告出力。

- 実行系エントリ
  - `run_execution.py`：ExecutionEngine 起動スクリプト。
    - 起動時にプロセス優先度を "high" に設定。
    - `KABUSYS_ENV=paper_trading` の場合は専用の Paper Trading SQLite（デフォルト `data/paper_trading.db`／環境変数で上書き）を使用して本番 DB と分離。
    - ブローカークライアント生成（`BrokerClientFactory`）と OrderRepository / OrderManager / RiskManager / Reconciler の組み立て。
    - エンジンは別スレッドで実行し、停止フラグファイル検知で安全に停止させる仕組みを実装。
    - PID ファイル管理。

  - `run_monitoring.py`：SystemMonitor ポーリングループ起動スクリプト。
    - デフォルトポーリング間隔 60 秒、環境変数 `MONITOR_POLL_INTERVAL` で上書き可能。無効値はデフォルトにフォールバックして警告。
    - 監視は環境にかかわらず本番用の sqlite_path を使用（監視用 DB は本番 DB を参照する設計）。
    - 停止フラグファイル存在チェックでループ停止。KeyboardInterrupt による終了もハンドリング。
    - SQLite / DuckDB の初期化（`init_monitoring_db` 呼び出し）を行う。

- ロギングユーティリティ
  - `kabusys.utils.logging_setup.setup_logging`：
    - stdout 出力の StreamHandler と日次ローテーション（TimedRotatingFileHandler）でのファイル出力をルートロガーに設定。
    - ログディレクトリ自動作成（失敗時はファイル出力をスキップしてコンソールのみ継続）。
    - 既存ハンドラをクリアして二重出力を防止。

- プロセス優先度ユーティリティ
  - `kabusys.utils.process_priority.set_process_priority`：Windows / POSIX（Linux, macOS, FreeBSD）を吸収し、"high" / "normal" / "low" の抽象レベルで優先度を設定。失敗時は警告を出してスキップ。
  - `set_cpu_affinity`：任意のコア数に対する CPU affinity 設定（アクセス権限等で失敗した場合は警告）。

- ポートフォリオ構築モジュール
  - `kabusys.portfolio.portfolio_builder`：
    - 候補選定（`select_candidates`：スコア降順、同点は signal_rank でタイブレーク）。
    - 等金額配分（`calc_equal_weights`）。
    - スコア重み配分（`calc_score_weights`）：全スコアが 0 の場合は等金額にフォールバックして警告。
  - `kabusys.portfolio.position_sizing.calc_position_sizes`：
    - 複数の配分方式（`risk_based`, `equal`, `score`）に対応。
    - 単元株（lot_size）丸め、個別ポジション上限、aggregate キャップ（利用可能現金）に基づくスケールダウン、残余の分配ロジックを実装。
    - コストバッファ（スリッページ・手数料見積り）考慮。
  - `kabusys.portfolio.risk_adjustment`：
    - セクター集中制限（`apply_sector_cap`）：既存保有を元にセクター別エクスポージャーを計算し上限超過セクターの候補を除外（"unknown" セクターは除外対象外）。
    - レジーム乗数（`calc_regime_multiplier`）："bull"/"neutral"/"bear" に応じた投下資金 multiplier を返す。未知レジームはフォールバックして警告。

- 研究・ファクター計算（基礎）
  - `kabusys.research.factor_research`：DuckDB の `prices_daily` / `raw_financials` を使う設計のファクター計算モジュール（モメンタム／Value／Volatility／Liquidity を想定）。（実装が途中のため拡張可能）

- ツール
  - `kabusys.tools.paper_verification_report`：Paper Trading の検証レポート生成スクリプト。
    - 稼働率、注文成功率、送信率、P95 レイテンシなどを集計して PASS/FAIL を判定する閾値を持つ（デフォルト閾値をソース内に定義）。
    - SQLite DB（Paper Trading 用）から集計。日付レンジ指定可能（ISO8601 UTC に変換してフィルタ）。
    - P95 計算、欠測データの扱い、エラーハンドリングを実装。

### Changed
- .env 自動読み込みルール
  - 読み込み優先順位: OS環境 > .env.local > .env。
  - 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で自動ロードを無効化可能（テスト用途を想定）。

- ログ出力の既定
  - コンソールは stdout を使用（stderr ではない）。cron 等で stdout/stderr のリダイレクトを一本化する運用に対応。

- DB 初期化の冪等性
  - 起動時に監視用テーブルが存在することを保証するため `init_monitoring_db` を実行（存在確認・作成を行う設計）。

- 実行系の安全停止
  - ストップフラグ（data/stop_requested.flag）を用いた外部停止手段を統一的に導入。`run_execution` はフラグ検知で Engine.stop() を呼び安全に停止する。

### Fixed
- 不正な環境変数値への耐性
  - `MONITOR_POLL_INTERVAL` が不正（整数でない、または 0 以下）の場合に警告を出しデフォルト（60 秒）にフォールバックするように修正。
  - `PAPER_FILL_MODE` の有効値チェックを追加し、不正値時に ValueError を送出。

- .env パーサ
  - クォート付き文字列内のバックスラッシュエスケープ処理を正しく扱うように改善。
  - コメント検出ロジックの改善（クォートなしの値では「直前がスペース/タブ」の場合に '#' をコメント扱いにする等）。

- ロギング設定の堅牢化
  - 既存ハンドラを flush/close してから削除することで、複数回 setup_logging を呼んだ際の二重出力問題に対処。
  - ログディレクトリ作成やファイルハンドラ作成に失敗した場合は警告してコンソール出力のみで継続するよう優雅にフォールバック。

- process_priority の例外ハンドリング
  - 権限不足や未実装のプラットフォームで発生する例外を捕捉してログ警告を出し、起動失敗を防ぐように改善。

- Paper Trading レポートの堅牢化
  - テーブルが存在しない／クエリで OperationalError が発生するケースをキャッチしてデフォルト値で継続するように修正。
  - 空のレイテンシリストに対して P95 を計算しない（Noneを返す）ように修正。

### Security
- `.env` ファイルは絶対にリポジトリにコミットしないことを明記（config_setup の出力ヘッダに注意書き）。

### Documentation / UX
- 各 CLI スクリプトにヘルプ・使用例を追加（モジュール docstring、CLI ヘルプ）。
- config_setup の対話で現在値の再利用やデフォルトを明示、キャンセル時の挙動をわかりやすく表示。

---

今後の予定（非網羅）
- research.factor_research の続き実装（ファクター計算の実働化）。
- strategy / execution のユニットテスト拡充と外部依存のモック整備。
- ログ・メトリクスの更なる可観測性向上（メトリクス出力、Prometheus 等との統合検討）。

---

（注）この CHANGELOG は提供されたソースコードを基に機能・振る舞いを推測して作成しています。実際のリリースノートは開発履歴・コミットログに基づいて調整してください。