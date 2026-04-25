# Changelog

すべての重要な変更点を Keep a Changelog の形式で記載します。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

## [0.1.0] - 2026-04-25

### Added
- 基本リリースを追加。KabuSys 日本株自動売買システムのコア・ユーティリティ・CLI を含む。
- 環境設定・ローディング
  - Settings クラスを追加し、環境変数を経由して各種設定値（J-Quants / kabuAPI / DB パス /ログレベル /環境種別 など）を取得可能に。
  - 自動 .env ロード機能を実装（プロジェクトルートの .env, .env.local を順に読み込み。OS 環境変数は保護）。自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD` により無効化可能。
  - .env パーサを強化:
    - `export KEY=val` 形式をサポート
    - シングル/ダブルクォート内のバックスラッシュエスケープを正しく処理
    - クォートなしの値におけるインラインコメント処理を改善
- CLI / ユーティリティ
  - config_setup: 対話式ウィザードで .env を初期作成 / 更新する CLI を追加（シークレット項目は表示をマスク）。
  - validate_config: 起動前に .env と config/*.yaml の基本検証を行う CLI を追加。`--strict` オプションで警告をFAIL扱いにできる。
  - tools/paper_verification_report: ペーパートレード DB を集計して検証レポートを生成するスクリプトを追加。期間指定や DB パス上書きに対応。
- 起動スクリプト
  - run_execution: ExecutionEngine 起動スクリプトを追加。`KABUSYS_ENV=paper_trading` の場合は MockBrokerClient を使用し、ペーパートレード用 DB に完全分離して記録する。
  - run_monitoring: SystemMonitor のポーリングループ起動スクリプトを追加。環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。
- DB / I/O 周り
  - DuckDB および SQLite の接続を受ける処理を各スクリプトに導入（duckdb は分析用、sqlite は監視/履歴用）。
  - 監視用テーブルの初期化関数 init_monitoring_db を起動時に呼び出してテーブル存在を保証（冪等）。
- ロギング / プロセス管理
  - utils/logging_setup: ルートロガーに StreamHandler (stdout) と TimedRotatingFileHandler（ログ日次ローテーション、30日保持）を設定するユーティリティを追加。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソール出力のみで継続。
  - utils/process_priority: psutil を使ったプロセス優先度設定ユーティリティを追加。Windows / POSIX(Linux/macOS/FreeBSD) に対応。CPU affinity 設定補助関数も実装。
- ポートフォリオ構築ライブラリ
  - portfolio モジュールを追加:
    - portfolio_builder: 候補選定 (select_candidates)、等重配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights)。スコア合計が 0 の場合は等重にフォールバックする警告ロギングを実装。
    - risk_adjustment: セクター集中上限の適用 (apply_sector_cap)、市場レジームに応じた投下資金乗数 (calc_regime_multiplier) を実装。未知レジームはフォールバックして警告ログを出す。
    - position_sizing: 各銘柄の発注株数算出 (calc_position_sizes)。risk_based / equal / score の配分方式、単元株（lot_size）丸め、aggregate cap によるスケーリング、コストバッファを考慮したスケールダウンアルゴリズムを実装。
- 研究用
  - research/factor_research: DuckDB を用いたファクター算出モジュール（モメンタム / MA200 / ATR / 出来高など）を追加（関数群の設計と実装を含む。ファイルは途中まで実装）。

### Changed
- ロギングの出力先を stdout に明示（StreamHandler）し、cron 等からのリダイレクト運用を考慮。
- run_monitoring と run_execution の起動時にプロセス優先度を最初に "high" に設定するよう統一。
- run_monitoring は KABUSYS_ENV に関係なく監視用の sqlite_path（本番パス）を使用する仕様とした（監視は常に本番 DB を参照する想定）。
- run_execution は paper_trading 環境時に専用の paper_sqlite_path を使用して本番 DB と完全に分離する動作。
- .env の読み込み順序と上書きルールを明確化:
  - OS 環境変数 > .env.local > .env（.env.local は override=True だが OS 環境変数は保護）
- config_setup の .env 書き出しフォーマットを定義（コメント付きテンプレートで生成）。

### Fixed
- run_monitoring のポーリング間隔取得で不正な環境変数値が指定された場合にデフォルトにフォールバックして警告を出す処理を追加。0 以下や非数値を安全に扱う。
- DB/ファイルリソースは finally ブロックで確実にクローズするように修正（run_execution / run_monitoring）。
- run_execution のエンジン起動前に停止フラグが既に立っている場合は起動をスキップする安全措置を追加。
- logging_setup: ログディレクトリ作成失敗時に致命的ではなく警告を出してコンソール出力のみで継続するように修正。

### Security
- .env を生成する際に、出力ファイルは絶対に Git にコミットしない旨をコメントで明記（config_setup にて注意喚起）。

### Notes / Implementation details / Limitations
- process_priority は権限不足や未対応 OS の場合に例外を吐かず警告でスキップする設計。管理者権限が必要な場面がある点に注意。
- portfolio.position_sizing の price フォールバック（価格未取得時）は一部 TODO を残しており、将来的に前日終値などのフォールバックを追加する予定。
- factor_research は DuckDB 経由でのテーブル参照を前提としており、prices_daily / raw_financials の存在が必要。
- validate_config は PyYAML 未インストール時に YAML 検証をスキップして警告を出す（PyYAML の optional 依存）。
- paper_verification_report の基準値（稼働率・成功率・送信率・P95 等）はコード内定数で管理されており、将来的に構成ファイル化が可能。

---

今後の予定（例）
- factor_research の完全実装とテスト追加
- 単体テスト・CI の整備
- 実行エンジン / ブローカー周りの堅牢性向上（再試行・レートリミット制御の強化）
- ログ/メトリクスの中央集約（Prometheus / Loki 等）対応

（以上）