# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。  

- リリース順: 最新が上
- 日付形式: YYYY-MM-DD

## [Unreleased]

（現在未リリースの変更はここに記載してください）

---

## [0.1.0] - 2026-04-24

初回公開リリース。プロジェクトの主要コンポーネント（実行エンジン、監視、設定管理、ポートフォリオ構築、ユーティリティ、解析ツール等）を含む統合的な日本株自動売買フレームワークを実装しました。

### Added
- 実行・監視のエントリポイントスクリプトを追加
  - run_execution.py: ExecutionEngine を起動するためのスクリプト。KABUSYS_ENV=paper_trading の場合はペーパートレード用 DB を使用し MockBrokerClient と分離して実行可能。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL 環境変数でポーリング周期を上書き可能。
- 設定管理とウィザード / 検証 CLI
  - config.py: 環境変数の読み込み・ラッパー。プロジェクトルート検出による .env/.env.local の自動読み込みを実装（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
  - config_setup.py: .env を対話的に作成・更新するウィザードを追加。
  - validate_config.py: .env や config/*.yaml の起動前チェック用 CLI （--strict オプションで警告を失敗扱いにできる）。
- Paper Trading 用レポートツール
  - tools/paper_verification_report.py: ペーパートレードの検証レポート生成スクリプト（期間フィルタ・P95 レイテンシなどの指標を出力）。
- ポートフォリオ構築関連の純粋関数群（DB 非依存）
  - portfolio/portfolio_builder.py: シグナル選定・重み計算（select_candidates, calc_equal_weights, calc_score_weights）。
  - portfolio/risk_adjustment.py: セクター上限適用とレジーム乗数（apply_sector_cap, calc_regime_multiplier）。
  - portfolio/position_sizing.py: 株数決定・リスクベース配分・単元株丸め（calc_position_sizes）。
- 研究用ファクター計算モジュール（骨組み）
  - research/factor_research.py: DuckDB 接続を受けてファクターを計算するモジュールの雛形（モメンタム等の仕様を含む）。
- ロギング・プロセス管理ユーティリティ
  - utils/logging_setup.py: StreamHandler（stdout）＋ TimedRotatingFileHandler（日次ローテート、30日保持）を用いた統一ログ設定ユーティリティ。
  - utils/process_priority.py: Windows / POSIX の差分を吸収したプロセス優先度設定・CPU affinity 設定ユーティリティ（set_process_priority, set_cpu_affinity）。
- DB 初期化ヘルパー（監視用）
  - monitoring/monitoring_db.py の init_monitoring_db を利用して監視テーブルが存在することを保証（冪等化）。
- パッケージメタ情報
  - __init__.py にバージョン番号 __version__ = "0.1.0" を追加。

### Changed
- 環境変数のロード順と保護機構
  - 自動ロード: OS 環境 > .env.local（上書き）> .env（未設定項目を埋める）。
  - OS 側環境変数は protected として .env による上書きを防止。
- run_monitoring の DB 接続動作
  - 監視（monitoring）は KABUSYS_ENV に関わらず本番用 sqlite_path を使用する設計に明示（監視用データを本番 DB に記録する想定）。
- run_execution の DB 切替
  - KABUSYS_ENV=paper_trading の場合、paper_sqlite_path（デフォルト data/paper_trading.db）を使用して本番 DB と分離。
- ログ出力
  - ログは標準出力（stdout）に出力するように変更（cron/スケジューラでの運用を考慮）。
  - ログディレクトリ作成に失敗した場合はファイルハンドラをスキップし、コンソール出力のみ続行するフェールセーフを追加。
- .env パースの堅牢化
  - config._parse_env_line で export プレフィックス、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメント取り扱いを実装し、より多様な .env 書式をサポート。
- position_sizing の配分ロジック改善
  - aggregate cap 適用時にスケールダウンして lot_size 単位で再配分するアルゴリズムを実装。残余資金を考慮して端数を優先度順に配分する処理を導入。
- risk_adjustment の挙動
  - セクター不明 (unknown) の銘柄はセクター上限チェックの対象外に（除外しない）。
  - 未知のレジームでは警告を出して multiplier=1.0 にフォールバック。

### Fixed
- MONITOR_POLL_INTERVAL の値検証
  - 非整数や 0 以下の値が設定された場合に警告を出しデフォルト（60 秒）へフォールバックするように修正（time.sleep に渡す際の ValueError 回避）。
- プロセス優先度設定の安全化
  - set_process_priority/set_cpu_affinity で権限不足や未サポート API 発生時に警告を出してスキップするようにした（AccessDenied 等の例外をハンドル）。
- validate_config の診断強化
  - 必須環境変数の存在チェック、プレースホルダ値検出、ファイルパスの親ディレクトリ存在チェック、YAML の有無に応じた検証パス（PyYAML 未インストール時はスキップ）等を実装。
- 多言語/出力の安定化
  - 各種 CLI の出力整形やエラーハンドリング（KeyboardInterrupt/EOFError）の処理を整理し、中断時に適切にメッセージを出すように改良。

### Documentation
- 各モジュールに詳細な docstring と使用例を追加（設定ファイル生成手順、CLI の使い方、主要関数の引数説明など）。
- config_setup ウィザードのヘルプメッセージと .env テンプレート出力を追加。

### Internal / Non-user visible
- DuckDB 連携ポイントを複数モジュールへ導入（execution, monitoring, research 等）。
- 各モジュールで例外発生時にロギングを行って処理継続する堅牢性を強化（監視ループの例外ハンドル等）。

---

今後の予定（例）
- research/factor_research の完全実装（残りの計算ロジック、テストの追加）
- ExecutionEngine / Broker クライアントの拡張（実ブローカー・ペーパーブローカーの差分テスト）
- CI 用の自動構成検証・テストスイート整備

--- 

この CHANGELOG はコードベースから推測して作成したものであり、実際のコミット履歴や意図とは差異がある可能性があります。実際の変更履歴として利用する場合はコミットログや PR の説明と突合してください。