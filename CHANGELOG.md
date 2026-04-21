CHANGELOG
=========

All notable changes to this project will be documented in this file.
This project adheres to "Keep a Changelog" and is released under Semantic Versioning.

フォーマット: 日本語（Keep a Changelog 準拠）

Unreleased
----------
（現在の変更はありません。次回リリースに含める変更をここに記載してください。）

[0.1.0] - 2026-04-21
-------------------
初回リリース。以下の機能を実装しました。

Added
- 基本情報
  - パッケージバージョンを `__version__ = "0.1.0"` としてリリース。

- 設定関連
  - Settings クラスを実装し、環境変数および .env/.env.local からの自動読み込みをサポート。
    - 自動読み込みはプロジェクトルート（.git または pyproject.toml を探索）を基準に行う。
    - 自動ロードを無効化するための環境変数: `KABUSYS_DISABLE_AUTO_ENV_LOAD`
    - 多数の設定プロパティを提供（J-Quants、kabu API、LINE トークン、DB パス、監視閾値、実行環境フラグ等）。
    - `PAPER_FILL_MODE` の有効値チェック（"instant" | "partial" | "never" | "reject"）。
    - `KABUSYS_ENV` の有効値チェック（"development" | "paper_trading" | "live"）およびログレベル検証。

  - .env 参照パーサ実装
    - export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ対応、行末コメント処理など冗長な .env 書式に対応。

- 環境設定ツール
  - 対話式ウィザード `kabusys.config_setup` を実装（python -m kabusys.config_setup）。
    - .env の初期作成・更新を支援。
    - シークレット項目はマスク表示、選択肢・デフォルト提示を実装。
    - 最終確認後に .env を書き出す機能を提供。

- 設定検証ツール
  - `kabusys.validate_config` CLI を実装（python -m kabusys.validate_config）。
    - 必須環境変数の未設定検出、プレースホルダ検出、KABUSYS_ENV / LOG_LEVEL の妥当性チェック。
    - DUCKDB/SQLITE パス親ディレクトリ存在確認、config/*.yaml の存在およびパース検証（PyYAML が存在しない場合はスキップ）。
    - `--strict` オプションで警告も失敗扱いにできる。
    - live 環境向けの追加ガード（LINE 通知設定の未設定や Kill Switch 挙動の警告）。

- 実行（Execution）関連
  - 実行エントリ `run_execution.py` を実装。
    - 起動時にプロセス優先度を "high" に設定する呼び出しを組み込み（utils.process_priority）。
    - `KABUSYS_ENV=paper_trading` 時は MockBrokerClient を利用する想定（paper_trading 用 DB を使用して本番 DB と完全分離）。
    - paper_trading 用 SQLite パスを上書き可能（環境変数: `PAPER_TRADING_SQLITE_PATH`。デフォルト `data/paper_trading.db`）。
    - ExecutionEngine、OrderManager、OrderRepository、RiskManager、Reconciler の組み立てと起動制御（スレッドで実行）。
    - 停止フラグファイル（data/stop_requested.flag）の検知による安全停止処理。
    - PID ファイル管理（data/execution.pid）。
    - RiskConfig の既定値（max_position_pct, max_utilization, rate_limit, circuit breaker 等）を指定。

- 監視（Monitoring）関連
  - 実行エントリ `run_monitoring.py` を実装。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正な値はデフォルトにフォールバック。
    - Monitoring は環境にかかわらず本番の sqlite_path を使用する設計（監視データは分離しない方針）。
    - SystemMonitor の一回チェック実行と例外ハンドリング、停止フラグ検知によるループ終了、KeyboardInterrupt ハンドリングを実装。
    - duckdb 接続も利用。

- ロギング・ユーティリティ
  - `kabusys.utils.logging_setup` を実装。
    - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次、30世代保持）を設定。
    - 既存ハンドラのクリーン再設定、ログディレクトリ作成失敗時のフォールバック（ファイル出力無効化）を考慮。
    - ログレベル・ログディレクトリの解決順（引数 > 環境変数 > デフォルト）を実装。

- プロセス優先度 / CPU Affinity
  - `kabusys.utils.process_priority` を実装。
    - Windows / POSIX の差分を吸収して `set_process_priority(level)` を提供（"high","normal","low"）。
    - `set_cpu_affinity(cpu_count)` によるコア固定機能（利用できない環境では警告してスキップ）。
    - 例外（アクセス権限等）に対する安全なロギング。

- ポートフォリオ構築ライブラリ（純粋関数群）
  - portfolio モジュールを実装し、以下を提供:
    - select_candidates: スコア降順で候補を選択（同点は signal_rank でタイブレーク）。
    - calc_equal_weights / calc_score_weights: 等配分・スコア加重（スコア合計が 0 の場合は等配分へフォールバック）。
    - apply_sector_cap: セクター集中上限チェック（既存ポジション時価を参照し上限超過セクターの新規候補を除外）。"unknown" セクターは制限対象外。
    - calc_regime_multiplier: レジームに応じた投下資金乗数（"bull":1.0, "neutral":0.7, "bear":0.3）。未知レジームは 1.0 にフォールバック（警告）。
    - calc_position_sizes: 発注株数決定ロジック（allocation_method: "risk_based" / "equal" / "score" をサポート）。
      - risk_based: 許容リスク率と stop_loss を基に株数算出。
      - equal/score: 重みを用いた配分・単元株（lot_size）丸め、per-position 上限と aggregate cap（available_cash）でスケールダウン。
      - cost_buffer を考慮した保守的なコスト見積り、端数処理のための remainder ベースの再配分ロジックを実装。
      - 価格欠損時のスキップ・ログ出力。

- Paper Trading 検証ツール
  - `kabusys.tools.paper_verification_report` を実装。
    - ペーパートレード SQLite（デフォルト data/paper_trading.db）から各種指標を集計しレポートを生成する CLI。
    - 出力指標:
      - 稼働率（system_status テーブル）
      - 注文成功率 / 送信率（trade_logs）
      - リスク却下数（risk_logs）
      - レイテンシ（avg / max / P95）
    - P95 の独自実装、日付フィルタ（--from / --to）、DB パス上書き（--db / 環境変数）。
    - 合否基準（稼働率 >= 99%、成立率 >= 90%、送信率 >= 95%、P95 <= 200ms）に基づいた PASS/FAIL 判定。

- 研究（Research）モジュール（開始実装）
  - `kabusys.research.factor_research` を追加。
    - モメンタム / MA200 / ATR / 流動性等の計算方針を記載。
    - DuckDB 接続を受け prices_daily / raw_financials を参照して計算する設計。
    - （モジュールは部分実装であり、今後の完成を予定）

Changed
- （該当なし — 初回リリースのため履歴なし）

Fixed
- （該当なし — 初回リリースのため履歴なし）

Deprecated
- （該当なし）

Removed
- （該当なし）

Security
- （該当なし）

注意事項 / マイグレーションノート
- .env ファイルは機密情報を含むため Git にコミットしないでください（config_setup のヘッダにも明記）。
- 自動 .env 読み込みがプロジェクトルートに依存するため、配布後に CWD に依存しない動作を期待できます。自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- Paper Trading と Live は DB を分離する旨に注意:
  - 本番用監視 DB: `SQLITE_PATH`（デフォルト data/monitoring.db） — 監視プロセスは常にこの DB を使用します。
  - Paper Trading 用 DB: `PAPER_TRADING_SQLITE_PATH`（デフォルト data/paper_trading.db） — 実行エンジンは paper 環境時にこちらを使用します。
- `PAPER_FILL_MODE` の値は厳密に検証されます。無効な値を設定すると起動時に例外が発生します。
- `KABUSYS_ENV` と `LOG_LEVEL` は許容値チェックを行うため、設定ミスがあると起動時あるいは validate_config 実行時に検出されます。
- process priority / cpu affinity の設定は環境（OS 権限等）によっては失敗しますが、安全にスキップされます（警告ログのみ）。

今後の予定（例）
- research.factor_research の完全実装（ファクター計算のSQL/Python実装を完了）。
- ExecutionEngine / BrokerClient のテスト用モックの充実と統合テスト。
- 単体テスト・CI の整備、型注釈の強化、ドキュメント追加。

----- 
（必要があれば、特定ファイルの変更点をより細かく記載します。どの程度の粒度で履歴化したいか指示してください。）