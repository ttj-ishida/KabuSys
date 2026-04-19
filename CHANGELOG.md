# CHANGELOG

すべての重要な変更は Keep a Changelog の形式に従って記載しています。  
日付はコードベースの現状から推測して付与しています。

なお、本ログは提供されたソースコードの内容から推測して作成しています。実際のコミット履歴とは異なる場合があります。

## [Unreleased]
- なし

## [0.1.0] - 2026-04-19
初期リリース。自動売買システム KabuSys の基礎機能を実装しました。

### 追加 (Added)
- 起動スクリプト
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV=paper_trading 時は専用の paper trading SQLite DB を使用し MockBrokerClient を利用して本番 DB と完全分離して動作。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト: 60秒）。停止は data/stop_requested.flag により検出。
- 設定管理
  - config.py: 環境変数/​.env ファイル読み込みロジックと Settings クラスを実装。プロジェクトルート自動検出、.env 読み込みの保護（OS 環境変数を上書きしない挙動）を実装。
  - config_setup.py: 対話式の .env 作成/更新ウィザードを実装。
  - validate_config.py: .env と config/*.yaml の簡易検証 CLI を実装。--strict モードあり。
- ロギング・プロセス管理ユーティリティ
  - utils/logging_setup.py: ルートロガー設定ユーティリティ（コンソール stdout 出力 + 日次ローテーションファイル出力）を実装。ログディレクトリ自動作成、既存ハンドラのクリア。
  - utils/process_priority.py: psutil を用いたプロセス優先度設定・CPU affinity 設定ユーティリティを実装（Windows / POSIX 差分を吸収）。
- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py: 候補選定、等金額・スコア重みの計算を実装（select_candidates, calc_equal_weights, calc_score_weights）。
  - portfolio/risk_adjustment.py: セクター集中上限フィルタ（apply_sector_cap）と市場レジーム乗数（calc_regime_multiplier）を実装。
  - portfolio/position_sizing.py: 単元丸め、risk_based / equal / score の割当方式に対応した株数決定ロジックを実装。aggregate cap（利用可能現金によるスケーリング）や cost_buffer を考慮。
  - portfolio パッケージのエクスポート設定を実装。
- ツール
  - tools/paper_verification_report.py: Paper Trading 用の検証レポート生成スクリプトを追加。稼働率、注文成功率・送信率、レイテンシ（平均／最大／P95）、リスク却下数などを集計して出力。日付範囲フィルタと DB パス指定 (--db / 環境変数) に対応。
- 研究（計算）モジュール（部分実装）
  - research/factor_research.py: DuckDB を使ったファクター計算モジュールの骨格を実装（モメンタム・MA200・ATR 等の定数と関数の雛形）。

### 変更 (Changed)
- run_monitoring/run_execution の起動時にプロセス優先度を "high" に設定してから各種初期化を行うようにし、優先度設定失敗時はログで警告して継続する設計とした。
- utils/logging_setup.py:
  - コンソール出力を stdout に統一（cron などからのリダイレクトを考慮）。
  - ログディレクトリ作成に失敗した場合はファイルハンドラをスキップしてコンソールのみで継続する堅牢化。
- config.py:
  - .env パーサーを強化（export プレフィックス対応、クォート内のエスケープ対応、インラインコメントの判定ルールなど）。
  - 自動 .env ロードを OS 環境変数を保護する仕組み（protected set）で実行する挙動を導入。
  - Settings に PAPER_FILL_MODE（検証付き）、paper_sqlite_path、pid_file_path、kill_flag 関連設定、閾値設定（CPU/MEM/DISK）などを追加。
  - KABUSYS_ENV と LOG_LEVEL の妥当性検証を強化。
- validate_config.py:
  - 起動前チェックで YAML パーサが利用可能かどうかを判定し、PyYAML がない場合は YAML 検証をスキップして警告を出す仕様を追加。
  - config ファイルのテンプレートを参照する警告メッセージを追加（config/*.yaml が存在しない場合の案内）。
- run_execution.py:
  - paper_trading モード時に paper trading 専用 SQLite を使用することで本番データベースと完全に分離する設計を採用。
  - ExecutionEngine を別スレッドで実行し、停止フラグ検知時に安全に停止させる制御を追加。
- position_sizing のスケーリングロジック:
  - aggregate cap 超過時にスケールして lot_size 単位で再配分するアルゴリズムを導入。残余キャッシュで端数分配する際に再現性を保つソート処理を実装。

### 修正 (Fixed)
- .env 読み込みで I/O エラーが発生した場合に警告を出して処理を継続するようにし、起動が一切停止しない堅牢化を実施。
- process_priority / set_cpu_affinity: OS によってサポートされない API の取り扱いで発生しうる例外をキャッチして警告ログに落とすようにし、起動失敗を防止。
- paper_verification_report の P95 計算と SQL 集計ロジックにおいて、テーブルやカラムが存在しない場合でも例外を捕捉して欠損値扱いにすることでスクリプトが途中で終了しないように改善。

### ドキュメント・注意事項 (Notes)
- config_setup.py により生成される .env はセキュリティ上コミットしないことを明示（ヘッダコメント）。  
- run_monitoring は監視用 SQLite を常に本番 sqlite_path で接続する設計になっているため、環境による DB 切り替えを期待する場合は注意が必要。
- factor_research.py はファイル内で処理が途中で切れている（calc_momentum 実装途中）ため、計算ロジックの追加実装が今後の作業になります。

--- 

今後の予定（推測）
- research/factor_research.py の各ファクター計算の完成化。
- ExecutionEngine / BrokerClientFactory 周りのテスト強化、MockBroker の充実。
- 監視・アラート（LINE 通知など）の実装強化（validate_config の警告項目にある設定を活かす）。