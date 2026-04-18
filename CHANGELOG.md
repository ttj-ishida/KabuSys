# Changelog

すべての注目すべき変更はここに記録します。  
このファイルは「Keep a Changelog」の形式に準拠しています。  

フォーマット:
- Unreleased: 今後の変更（開発中）
- 0.1.0: 初回リリース（推定: 2026-04-18）

---

## [Unreleased]
### 追加予定
- research/factor_research のファクター群（Momentum 等）の実装完了・追加テスト
- モニタリング・実行の統合テスト、及びより詳細なエラーメトリクス収集
- 銘柄別 lot_size を stocks マスタから読み込む拡張（position_sizing の TODO を反映）

### 修正予定
- position_sizing の price 欠損時のフォールバック実装（risk_adjustment の TODO に対応）
- DuckDB/SQLite 周りの接続リトライや障害耐性の強化

---

## [0.1.0] - 2026-04-18
初回リリース。KabuSys 自動売買システムの基礎機能群を実装。

### 追加
- コア設定と環境管理
  - Settings クラスを導入し、環境変数（.env / .env.local の自動読み込みを含む）からアプリ設定を取得する仕組みを実装。
  - .env パーサ実装: export プレフィックス、シングル/ダブルクォート内のエスケープ、行内コメント処理などを考慮した堅牢なパーサを提供。
  - Settings 経由で各種設定（DUCKDB/SQLite パス、PID / kill フラグパス、Paper Trading 設定、しきい値等）を取得可能。

- 起動スクリプト / ランタイム
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading 時は paper_trading 用 SQLite（data/paper_trading.db）を使用して本番 DB と分離する動作をサポート。
    - BrokerClientFactory により本番 / モックブローカー切替を行う設計。
    - ExecutionEngine の起動、スレッドでの run_session 実行、停止フラグ（data/stop_requested.flag）と PID ファイル（data/execution.pid）の取り扱いを実装。
    - RiskManager のデフォルト設定（max_position_pct 等）を組み立てて渡す実装を提供。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番 sqlite_path を使用する旨を明示。
    - 停止フラグファイル検出でループを終了する安全なシャットダウン処理を実装。

- モニタリング関連
  - monitoring_db の初期化コール（init_monitoring_db）を実装点検して起動時に監視テーブルの存在を保証（冪等）。

- ロギング・運用ユーティリティ
  - utils/logging_setup.py を追加。
    - root ロガーに StreamHandler (stdout) と TimedRotatingFileHandler（デイリーローテート、30 日保持）を設定。
    - 既存ハンドラをクリーンに削除して二重登録を防止。
    - LOG_DIR 作成失敗時はファイル出力をスキップしてコンソール出力のみで継続。
  - utils/process_priority.py を追加。
    - Windows / POSIX(Linux, macOS 等) の差分を吸収してプロセス優先度を設定（high/normal/low）。
    - CPU affinity を最初の N コアに固定するユーティリティを提供。
    - 権限不足や未対応 OS の際は警告ログでスキップする安全設計。

- 設定支援ツール・検証ツール
  - config_setup.py: 対話式 .env ウィザードを追加。
    - J-Quants / kabu API / DB パス / ログレベル 等の設定を対話形式で作成・更新できる。
    - 秘匿項目は表示マスク、保存前の確認を実装。
  - validate_config.py: 設定検証 CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV 値チェック、LOG_LEVEL チェック、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在・パース（PyYAML があれば内容検証）を実施。
    - KABUSYS_ENV=live の場合の追加ガード（LINE トークン未設定、KILL_FLAG_CLEAR_ON_START の警告）を追加。
    - --strict による警告を FAIL 扱いにするモードをサポート。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - select_candidates: スコア降順と tie-break による選出。
    - calc_equal_weights / calc_score_weights: 等重・スコア加重配分（スコア全ゼロ時は等重にフォールバック）。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: 既存保有を考慮したセクター集中制限。sell予定銘柄を除外して計算する機能。
    - calc_regime_multiplier: market レジーム（bull/neutral/bear）に応じた投下資金乗数を返す実装（未知レジームはフォールバック）。
  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method（risk_based/equal/score）に基づく株数決定ロジック。
    - 単元株丸め、1銘柄上限、aggregate cap（利用可能現金を超える場合のスケールダウン）、cost_buffer（手数料・スリッページ見積り）考慮、lot 単位での残差処理まで実装。

- リサーチ（部分実装）
  - research/factor_research.py を追加（モメンタム等の計算ロジックを設計）。
    - モメンタム用の定数・スキャン幅・P95 等ユーティリティを実装開始。（ファイル末尾で実装が続く設計）

- ツール
  - tools/paper_verification_report.py
    - ペーパートレード DB（PAPER_TRADING_SQLITE_PATH）から稼働率、注文成功率、送信率、P95 レイテンシ等を集計してレポートを標準出力に出力する CLI を実装。
    - 閾値（稼働率 99%、成立率 90% 等）に基づく PASS/FAIL 判定を行う。

- パッケージメタ
  - src/kabusys/__init__.py にバージョン __version__ = "0.1.0" を設定。

### 変更
- 自動環境変数ロードの挙動を定義
  - プロジェクトルート検出: .git または pyproject.toml を基準とするため CWD に依存しないように実装。
  - 読み込み優先度: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロードを無効化可能。
  - .env の上書き時に OS 環境変数を保護する protected 機構を導入。

- ロギングの既存ハンドラ処理を明示的に flush/close してから削除するように変更（多重ログ出力回避）。

### 修正（バグ修正 / 安全設計）
- 環境変数パーサの堅牢化
  - export 句対応、クォート内部のバックスラッシュエスケープ処理、インラインコメントの扱いを改善。
- プロセス優先度設定の例外ハンドリング強化
  - 権限不足や未対応 OS での安全スキップと警告ログ出力を実装。
- DB 初期化の冪等性を担保
  - run_execution/run_monitoring 起動時に init_monitoring_db を呼ぶことで監視テーブルの存在を保証（既存でも安全）。

### 既知の制約 / TODO
- research/factor_research の一部実装が継続中（ファクター計算の完全実装・テストが必要）。
- position_sizing の price 欠損時のフォールバック（前日終値等）は未実装（TODO コメントあり）。
- 銘柄別単元（lot_size）の汎用化は将来的な拡張予定（現在は全銘柄共通 lot_size を想定）。

---

## 書式とポリシー
- 重要な変更は全てここに記載します。マイナーな変更や内部的なリファクタは適宜まとめて記載する場合があります。
- バージョン運用ルールは SemVer を推奨します（本リリースは初期バージョン 0.1.0）。

---

（以上）