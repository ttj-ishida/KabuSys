# CHANGELOG

すべての注目すべき変更を記載します。本ファイルは Keep a Changelog の形式に準拠しています。  

履歴はソースコードの実装内容から推測して作成しています。

## [Unreleased]

（なし）

## [0.1.0] - 2026-04-17

初期リリース。以下の機能群とユーティリティを実装／追加しました。

### Added
- コアパッケージ基盤
  - パッケージ情報（kabusys.__version__ = 0.1.0）。
  - プロジェクトルート検出機能（.git または pyproject.toml を基準）を備えた自動 .env ロード機構を実装。
  - .env ファイル読み書きおよびパースの堅牢化（export プレフィックス対応、クォート・エスケープ、行内コメント処理）。
  - Settings クラスによる環境変数ラッパー（各種パス、API トークン、監視閾値、ペーパートレード設定等のプロパティ化とバリデーション）。

- CLI / 運用ツール
  - 環境設定ウィザード（kabusys.config_setup）:
    - インタラクティブに .env を作成・更新するウィザードを提供。
    - シークレット項目のマスク表示、選択肢・デフォルト対応、保存確認等を実装。
  - 設定検証ツール（kabusys.validate_config）:
    - 必須環境変数や KABUSYS_ENV、ログレベル、DB パス、config/*.yaml の存在・パースチェック機能。
    - --strict オプションで警告も失敗扱いにできる。
    - PyYAML 未インストール時は YAML 検証をスキップして警告を出力。
  - Paper Trading 検証レポート生成スクリプト（kabusys.tools.paper_verification_report）:
    - paper_trading 用 SQLite DB から稼働率、注文成功率、送信率、レイテンシ（平均・最大・P95）を集計し PASS/FAIL 判定を出力。
    - 日付フィルタ（--from / --to）と DB パス指定（--db / 環境変数対応）をサポート。
    - 判定閾値（稼働率、成功率、送信率、P95）を定義して報告。

- 監視・実行まわり
  - 監視プロセス起動スクリプト（kabusys.run_monitoring）:
    - SystemMonitor のポーリングループ起動、MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止フラグ（data/stop_requested.flag）検知による安全終了、ログ出力、DB 接続（監視は環境にかかわらず本番 sqlite_path を使用）。
    - duckdb 接続との併用。
  - 実行エンジン起動スクリプト（kabusys.run_execution）:
    - ExecutionEngine の組み立てと起動。スレッドで run_session を実行し停止フラグで安全に停止可能。
    - KABUSYS_ENV=paper_trading 時は paper 専用 SQLite（デフォルト data/paper_trading.db）を使用し、本番 DB と分離。
    - BrokerClientFactory 経由でブローカークライアントを生成（Mock の切替を想定）。
    - ExecutionEngine に渡す RiskManager / OrderManager / Reconciler 等の依存注入。

- ポートフォリオ構築（純粋関数群）
  - kabusys.portfolio モジュール:
    - portfolio_builder: 候補選定（スコア降順タイブレーク）、等金額配分 calc_equal_weights、スコア加重 calc_score_weights（全スコア 0 の場合は等配分へフォールバック）。
    - risk_adjustment: セクター集中制限 apply_sector_cap（既存ポジションのセクター比率計算、sell 処分予定の除外、unknown セクターは制限対象外）、市場レジームに応じた投下資金乗数 calc_regime_multiplier（bull/neutral/bear マップと未知レジームのフォールバック）。
    - position_sizing: 株数計算 calc_position_sizes（risk_based / equal / score 対応、lot 単位丸め、per-position 上限、aggregate cap スケーリング、cost_buffer を考慮した調整、残余配分の再割当ロジック）。

- 研究／ファクター計算
  - kabusys.research.factor_research:
    - DuckDB を使ったファクター計算（momentum、volatility 等）。
    - mom_1m/3m/6m、MA200 乖離、20日 ATR、20日平均売買代金、volume_ratio などを計算する SQL 実装。
    - データ不足時は None を返す設計。

- ユーティリティ
  - プロセス優先度・CPU affinity ユーティリティ（kabusys.utils.process_priority）:
    - Windows / POSIX の差分を吸収して set_process_priority(level) を実装（high/normal/low）。
    - set_cpu_affinity(cpu_count) によるコア固定機能。
    - 権限不足や未対応 OS の場合は警告を出してスキップする安全な実装。

- データベース関連
  - DuckDB と SQLite の併用を前提にした設計（duckdb_path, sqlite_path, paper_sqlite_path のプロパティ）。
  - 監視用 DB 初期化関数 init_monitoring_db を呼び出すことで監視テーブルの存在を保証（冪等）。

### Changed
- （初回リリースのため該当なし）

### Fixed
- .env のパースロジックでの改善（クォート内でのバックスラッシュエスケープ対応、export プレフィックス処理、行内コメント処理）により既知のパース不具合を回避。
- プラットフォーム差分（Windows/Linux/macOS）でのプロセス優先度設定時に発生し得る例外をキャッチして、安全にフォールバックするように修正（権限不足の警告出力）。

### Security
- .env ファイルの生成ウィザードで「.env は絶対に Git にコミットしないこと」という注記を追加（シークレット保護の啓発）。

### Notes / Operational details
- PAPER_FILL_MODE には制約があり、有効値は "instant" / "partial" / "never" / "reject"。無効値は Settings で ValueError を送出するため起動時に検出可能。
- KABUSYS_ENV の有効値は development / paper_trading / live。live 設定時は validate_config が追加の注意（LINE 通知設定、KILL_FLAG_CLEAR_ON_START 設定）を警告する。
- 監視とエンジンは stop_requested.flag / kill.flag / pid ファイル等を用いたシンプルな運用制御を想定。
- Paper Trading 用 DB は本番 DB と完全分離される設計（ペーパートレードの結果が本番に混入しない）。

---

今後の改善候補（コード中に TODO コメント等で示唆されている点）
- position_sizing における銘柄別 lot_size 拡張（現状は一律 100 を想定。将来的にマスタ導入で拡張予定）。
- apply_sector_cap の price 欠損時のフォールバック（前日終値や取得原価の利用検討）。
- factor_research のさらなるファクター拡張・パフォーマンスチューニング。
- YAML 検証のための PyYAML の明示的依存管理（インストール時の optional 要件化やドキュメント化）。