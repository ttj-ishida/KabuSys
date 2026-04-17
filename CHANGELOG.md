CHANGELOG
=========

すべての重要な変更はこのファイルに記録します。
書式は "Keep a Changelog" に準拠しています。
（参考: https://keepachangelog.com/ja/）

Unreleased
----------

### Added
- .env パーサーの強化（export 形式のサポート、クォート内のバックスラッシュエスケープ対応、行末コメントの扱い改善）。
  - 該当: src/kabusys/config.py
- プロセス優先度／CPU affinity ユーティリティを追加。Windows / POSIX を吸収し呼び出し元はプラットフォーム非依存で使用可能。
  - 関数: set_process_priority, set_cpu_affinity
  - 該当: src/kabusys/utils/process_priority.py
- 監視用ポーリング起動スクリプトを追加。環境変数 MONITOR_POLL_INTERVAL で間隔を変更可能。監視データベースは環境に依らず本番 sqlite_path を使用。
  - 該当: src/kabusys/run_monitoring.py
- Execution エンジン起動スクリプトを追加。paper_trading 環境では MockBroker を使用して paper_trading 用 DB に完全分離して記録。
  - 該当: src/kabusys/run_execution.py
- Paper Trading 検証レポート出力ツールを追加。稼働率、注文成功率、送信率、レイテンシ（P95）等を算出する CLI スクリプト。
  - 該当: src/kabusys/tools/paper_verification_report.py
- ポートフォリオ構築関連の純粋関数群を追加（候補選定、等配分／スコア配分、単元丸めを含む株数決定、セクター上限、レジーム乗数）。
  - 該当: src/kabusys/portfolio/*.py
- DuckDB を利用したリサーチ機能を追加。モメンタム／ボラティリティ／バリュー等のファクター計算、将来リターン、IC（スピアマン）計算、統計サマリを提供。
  - 該当: src/kabusys/research/*.py
- ニュース NLP モジュール（OpenAI を用いた銘柄別センチメントスコア付与）を追加。
  - 機能: バッチ送信、最大トークン対策、429/ネットワーク/5xx へのエクスポネンシャルバックオフ、レスポンス検証、スコアクリッピング。
  - 該当: src/kabusys/ai/news_nlp.py
  - 注意: ファイル末尾に未完の箇所あり（Partial 実装／続きが必要）。

### Changed
- .env 自動読み込みの挙動明確化。プロジェクトルートを .git または pyproject.toml で検出し、見つからない場合は自動ロードをスキップ。OS 環境変数はプロテクトされ上書きされない（ただし .env.local は上書き可能）。
  - 該当: src/kabusys/config.py
- Settings に多数のプロパティを実装（デフォルトパスや閾値・フラグを環境変数から取得、値検証を追加）。
  - 例: DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH, PAPER_FILL_MODE のバリデーション、KABUSYS_ENV/LOG_LEVEL の検証、監視閾値（CPU/MEM/DISK）など
  - 該当: src/kabusys/config.py
- run_monitoring / run_execution の起動時にプロセス優先度を "high" に設定するように変更（起動直後に設定）。
  - 該当: src/kabusys/run_monitoring.py, src/kabusys/run_execution.py
- ExecutionEngine 起動ロジック: paper_trading 環境時は paper 用 SQLite を使用して本番 DB と完全分離する仕様を採用。
  - 該当: src/kabusys/run_execution.py

### Fixed
- ポーリング間隔取得時の堅牢性向上: MONITOR_POLL_INTERVAL の不正値（0以下・非整数）を検知してデフォルトにフォールバックするように改善。
  - 該当: src/kabusys/run_monitoring.py
- 各種集計・統計ユーティリティで None / データ欠損時の扱いを明示的にしてクラッシュを防止（例: P95 計算、平均/最大/NULL の扱いなど）。
  - 該当: src/kabusys/tools/paper_verification_report.py, src/kabusys/research/*

### Known issues / Notes
- ai/news_nlp.py は概ね実装済みだが、ファイル末尾が途切れているため完全実行可能な状態ではありません。エラー・部分実装時の挙動はフェイルセーフ（スキップ）を意図していますが、デプロイ前に残りの実装と統合テストが必要です。
- position_sizing / risk_adjustment 内に将来改善予定の TODO（価格欠損時のフォールバック、銘柄別 lot_size の導入など）が残っています。
- process_priority の設定は権限不足や未サポート OS の場合に警告を出してスキップする実装になっています（安全策）。

0.1.0 - 2026-04-17
------------------
初回リリース: 基本機能一式を実装。

### Added
- 核となるライブラリ構造とバージョン定義。
  - src/kabusys/__init__.py に __version__ = "0.1.0"
- 環境設定管理（.env 読み込み、自動ロード、環境変数ラッパー）。
  - src/kabusys/config.py
- 実行エンジン起動スクリプト（ExecutionEngine の起動／停止監視、paper_trading 対応）。
  - src/kabusys/run_execution.py
- 監視（SystemMonitor）ポーリング起動スクリプト。
  - src/kabusys/run_monitoring.py
- ポートフォリオ構築関連（候補選定、重み計算、株数決定、セクター制限、レジーム乗数）。
  - src/kabusys/portfolio/*.py
- リサーチ機能（ファクター計算、特徴量探索、IC/統計サマリ）。
  - src/kabusys/research/*.py
- Paper Trading 検証レポート生成ツール（CLI）。
  - src/kabusys/tools/paper_verification_report.py
- ニュース NLP（OpenAI）モジュール（基盤実装）。
  - src/kabusys/ai/news_nlp.py
- プロセス優先度 / CPU affinity ユーティリティ。
  - src/kabusys/utils/process_priority.py
- DuckDB / SQLite を用いたデータアクセスを前提とした実装群。

### Changed
- 内部設計: 多くのコンポーネントは外部接続（DuckDB / SQLite / ブローカー）を抽象化して受け取る設計に統一。

### Fixed
- 各種 NULL / データ欠損ケースの安全な取り扱いを追加（クラッシュ回避）。

Deprecated
----------
- なし

Removed
-------
- なし

Security
--------
- なし

---

注: 上記はソースコードの内容から推測してまとめた変更履歴です。実際のコミット履歴・プロジェクト管理情報と異なる可能性があるため、リリース作業時は git log 等の一次情報を参照してください。