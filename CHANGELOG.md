# CHANGELOG

すべての注目すべき変更を記録します。  
このファイルは「Keep a Changelog」形式に準拠しています。セマンティックバージョニングを採用してください。

## [Unreleased]

（現時点では未リリースの変更はありません）

## [0.1.0] - 2026-04-17

初回リリース。システム全体のコア機能・ユーティリティ群を追加しました。

### 追加 (Added)
- アプリケーションのメタ情報
  - kabusys パッケージのバージョン定義を追加（__version__ = "0.1.0"）。

- 環境設定／管理
  - kabusys.config:
    - .env 自動ロード機能を実装（プロジェクトルート検出: .git または pyproject.toml を基準）。
    - .env ファイルのパース実装（コメント、クォート、エスケープ、export 形式に対応）。
    - Settings クラスを導入し、J-Quants / kabuステーション / LINE API / DB パス / 監視設定 /閾値 / 実行環境等をプロパティ経由で取得可能に。
    - 環境変数の保護やデフォルト値、入力検証（例: PAPER_FILL_MODE, KABUSYS_ENV, LOG_LEVEL）を実装。
    - settings = Settings() の単一インスタンスを提供。

  - kabusys.config_setup:
    - 対話式ウィザードで .env を生成・更新する CLI を追加。
    - 質問リスト、シークレット項目のマスク表示、既存 .env の読み込み、確認フロー、.env 書き出し機能を追加。
    - 実行例: `python -m kabusys.config_setup`

  - kabusys.validate_config:
    - .env および config/*.yaml に対する起動前検証 CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV・LOG_LEVEL 検証、DB パスの親ディレクトリ存在チェック、YAML パーサがあれば config/*.yaml の構文検証、live 環境での注意喚起等を実装。
    - --strict オプションで警告を失敗扱いにできる。
    - 実行例: `python -m kabusys.validate_config [--strict]`

- 実行/監視ランナー
  - run_execution:
    - ExecutionEngine 起動スクリプトを追加。
    - プロセス優先度を高く設定するユーティリティ呼び出しを実行開始時に行う。
    - KABUSYS_ENV による paper_trading モード判定を導入。paper_trading 時は paper_trading 用の SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB と分離。
    - BrokerClientFactory を利用してブローカークライアントを生成し、OrderRepository / OrderManager / RiskManager / Reconciler / ExecutionEngine を組み立てて実行。
    - エンジンはスレッドで起動し、data/stop_requested.flag による外部停止をサポート。PID ファイル管理を行う。
    - 実行中は停止フラグ検出で安全に停止する機構を実装。

  - run_monitoring:
    - SystemMonitor ポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。0 以下や不正な値はデフォルトにフォールバックしてログ出力。
    - 監視 DB 初期化（init_monitoring_db）を実行。監視は環境にかかわらず本番 sqlite_path を使用する点を明示。
    - data/stop_requested.flag ファイルでループを終了可能。

- 監視 / モニタリング関連
  - run_* で init_monitoring_db を呼び出し、監視用テーブルの冪等な初期化を保証。

- ポートフォリオ構築（純粋関数群）
  - kabusys.portfolio.portfolio_builder:
    - select_candidates: BUY シグナルをスコア降順で選定（タイブレークに signal_rank を使用）。
    - calc_equal_weights: 等金額配分の重み計算。
    - calc_score_weights: スコア正規化による重み計算（全スコアが 0 の場合は等配分へフォールバック、警告出力）。
  - kabusys.portfolio.risk_adjustment:
    - apply_sector_cap: セクター集中上限に基づく候補除外ロジック（売却予定銘柄の除外、"unknown" セクターは免除）。
    - calc_regime_multiplier: 市場レジームに応じた資金乗数（bull/neutral/bear をサポート、未定義はフォールバック）。
  - kabusys.portfolio.position_sizing:
    - calc_position_sizes: allocation_method（risk_based / equal / score）に応じた発注株数算出。
    - リスクベース、等比率ベース、スケーリング（available_cash に合わせたスケールダウン）、単元株丸め、コストバッファ対応、aggregate cap ロジックを実装。

- 研究 / ファクター計算
  - kabusys.research.factor_research:
    - DuckDB 接続を受け、prices_daily テーブルからモメンタム（1M/3M/6M）、MA200 乖離、ATR、流動性指標などを計算する関数を追加（calc_momentum, calc_volatility など）。
    - 計算は純粋に DB（DuckDB）上のデータに基づき、結果は (date, code) キーの辞書リストで返す設計。

- ツール
  - kabusys.tools.paper_verification_report:
    - ペーパートレード用 SQLite を読み取り、稼働率・注文成功率・送信率・レイテンシ等の検証レポートを生成する CLI を追加。
    - 日付フィルタ（--from / --to）、DB パスオーバーライド（--db）をサポート。P95 計算、閾値ベースの PASS/FAIL 判定を実装。
    - 実行例: `python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11`

- ユーティリティ
  - kabusys.utils.process_priority:
    - クロスプラットフォームでプロセス優先度（high/normal/low）を設定する set_process_priority を実装（Windows と POSIX を吸収）。
    - CPU affinity を設定する set_cpu_affinity を実装（最初の N コアに固定）。
    - 権限不足や未対応 OS の場合は警告を出して安全にスキップする。

### 変更 (Changed)
- .env の読み込み優先順を明確化:
  - OS 環境変数 > .env.local > .env
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能に。

- DB の扱い:
  - run_monitoring は環境に関わらず本番用 sqlite_path を使用する仕様を明示（監視データは本番 DB に記録する想定）。
  - run_execution は paper_trading の場合、専用の paper_sqlite_path を使用して本番 DB と完全に分離。

- エラー / フォールバック挙動:
  - MONITOR_POLL_INTERVAL の不正値や .env の不正行に対し安全にフォールバックし、警告ログを出力するようにした。
  - PAPER_FILL_MODE 等の環境変数値検証を追加し、不正な値は ValueError を発生させるようにした（早期検出）。

### 修正 (Fixed)
- .env パーサの改善:
  - シングル／ダブルクォート内でのバックスラッシュエスケープに対応。
  - export KEY=val 形式、インラインコメントの扱い（クォートあり／なし）を明確化。
  - 空行・コメント行を無視する処理を堅牢化。

- process_priority の例外処理強化:
  - psutil のプラットフォーム特有定数がない場合でもモジュールロードが失敗しないよう getattr フォールバックを導入。
  - 権限不足やプラットフォーム非対応時にログで通知して処理を継続するように修正。

- position_sizing のスケーリングロジック:
  - aggregate cap スケールダウン時の四捨五入／単元株丸め、残余キャッシュからの追加配分（fractional remainder）を実装し、より再現性のある配分を行うようにした。

### ドキュメント (Documentation)
- 各モジュールに docstring / 使用例を追加し、CLI の使い方や設計意図を明記（例: run_monitoring/run_execution/config_setup/paper_verification_report）。

### セキュリティ (Security)
- .env ファイルに関する注意喚起を追加（.env を絶対に Git にコミットしないことを README レベルで明記）。
- 環境変数未設定時に早期失敗する _require() を導入し、秘密情報がないまま稼働するリスクを低減。

---

今後の予定（例）
- execution エンジンや監視コンポーネントの統合テスト、さらに詳細なドキュメント整備。
- 銘柄ごとの lot_size を持つマスタ対応や position_sizing の拡張。
- DuckDB を用いたファクター計算のパフォーマンス最適化と追加ファクターの導入。

（以上）