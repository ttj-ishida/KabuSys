CHANGELOG
=========

すべての変更は Keep a Changelog の方針に従って記載しています。
新しい機能、変更、修正点などは下記をご参照ください。

フォーマット:
- Added: 新機能
- Changed: 既存機能の変更
- Fixed: バグ修正 / 挙動改善
- Removed / Deprecated / Security 等は該当があれば記載

0.1.0 - 2026-04-25
------------------

Added
- 基本アプリケーション設定管理
  - .env ファイルの自動読み込み機能を実装（プロジェクトルート検出: .git / pyproject.toml を探索）。
  - .env ファイルパーサを実装。以下に対応:
    - export KEY=val 形式
    - シングル/ダブルクォート内のバックスラッシュエスケープ
    - インラインコメントの扱い（クォートあり/なしでの差異を考慮）
  - Settings クラスを導入し、アプリ全体から統一的に環境変数を参照可能に。
    - J-Quants / kabuステーション / LINE / DB パス / 監視・しきい値 / 実行環境（development/paper_trading/live）などのプロパティを提供。
    - KABUSYS_ENV, LOG_LEVEL 等の値検証（不正値は ValueError）。

- 環境設定ウィザード CLI（config_setup）
  - 対話式で .env を新規作成・更新するウィザードを追加。
  - シークレット項目のマスク表示、選択肢/デフォルト表示、確認保存フローを実装。
  - .env テンプレート書き込み機能を提供。

- 設定検証 CLI（validate_config）
  - .env および config/*.yaml の存在と基本的妥当性を検証するコマンドを追加。
  - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ確認、PyYAML があれば YAML のパース検証を実施。
  - --strict オプションで警告を失敗扱いにできる。

- 実行系 / 監視系起動スクリプト
  - run_execution: ExecutionEngine を起動するエントリポイントを追加。
    - KABUSYS_ENV=paper_trading の場合は paper 専用 SQLite を使用（data/paper_trading.db デフォルト）、MockBrokerClient を用いた完全分離を想定。
    - BrokerFactory を通じてブローカークライアントを生成。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine をスレッドで実行。停止フラグ監視により安全停止。
    - リスク管理設定（max_position_pct, max_utilization, rate_limit_per_sec など）を Engine 起動時に注入。initial_portfolio_value は broker.get_available_cash() で取得。
  - run_monitoring: SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトへフォールバックし、ログ出力。
    - 監視用 DB 初期化（monitoring テーブル等の保証）。監視は KABUSYS_ENV にかかわらず「本番」sqlite_path（Settings.sqlite_path）を使用する設計。

- ロギング・プロセス設定ユーティリティ
  - setup_logging: ルートロガーへ StreamHandler (stdout) と TimedRotatingFileHandler（日次、30日保持）を設定するユーティリティを追加。
    - 既存ハンドラをクリアしてから再設定することで二重ログ出力を防止。
    - LOG_DIR / LOG_LEVEL の環境変数や引数で挙動を制御。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
  - process_priority / set_cpu_affinity: クロスプラットフォームでのプロセス優先度・CPU affinity 設定を追加。
    - Windows / POSIX (Linux, Darwin, FreeBSD) を考慮して nice / priority を適用。権限不足や未対応 OS は警告を出してスキップ。

- ポートフォリオ構築ライブラリ（kabusys.portfolio）
  - portfolio_builder:
    - select_candidates: BUY シグナルをスコア降順でソートして候補抽出（同点は signal_rank でタイブレーク）。
    - calc_equal_weights / calc_score_weights: 等金額配分、スコア加重配分を実装。全スコアが 0 の場合は等金額にフォールバック（WARN）。
  - risk_adjustment:
    - apply_sector_cap: セクター集中上限を適用して候補をフィルタリング。売却予定銘柄はエクスポージャー計算から除外。unknown セクターは上限適用除外。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を返す（default: bull=1.0, neutral=0.7, bear=0.3）。未知レジームは警告を出して 1.0 にフォールバック。
  - position_sizing:
    - calc_position_sizes: 複数方式（risk_based, equal, score）で発注株数を計算。lot_size（単元）で丸め、単銘柄上限／aggregate 上限（available_cash）を考慮するスケールダウンロジックを実装。
    - cost_buffer（スリッページ・手数料見積り）を反映した保守的なコスト見積り、残余キャッシュに基づく端数配分のロジックあり。

- Paper Trading 検証ツール（tools.paper_verification_report）
  - Paper Trading 用 SQLite（デフォルト data/paper_trading.db）からデータを集計して検証レポートを生成する CLI を追加。
  - システム稼働率（uptime）、注文成功率（fill rate）、送信率（send rate）、P95 レイテンシ等を計測し PASS/FAIL を判定する閾値を提供（デフォルト閾値をソース内に定義）。
  - 日付フィルタ（--from/--to）、--db オプションによる DB パス指定に対応。
  - P95 計算や latency が NULL の場合の扱い、データが無い場合の適切な N/A 表示を実装。

- パッケージ初期化
  - kabusys パッケージのバージョンを __version__ = "0.1.0" として設定。
  - portfolio / tools / その他モジュールのエクスポートを __all__ 等で整理。

Changed
- ログ出力の標準出力先を stderr ではなく stdout に統一（cron / Task Scheduler でのリダイレクト運用を想定）。
- .env の自動ロード優先順位を OS 環境変数 > .env.local > .env に設定。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動読み込みを抑制可能。
- run_monitoring は環境にかかわらず監視用 DB（Settings.sqlite_path）を使用する挙動を明示化。
- run_execution は paper_trading モード時に専用 SQLite を使用して本番 DB と完全分離する挙動を明示化。

Fixed
- .env パーサの頑健化:
  - クォートありの値でのエスケープ処理、閉じクォート検出を正しく処理。
  - コメントの扱い（クォートあり/なしで挙動を区別）を改善し、誤読を防止。
- ロギング設定時に既存ハンドラを flush/close の上で削除するようにして、多重登録による重複ログを回避。
- process_priority / set_cpu_affinity: 権限不足や未対応 OS での例外をキャッチし、警告でスキップする安全化を追加。
- position_sizing のスケールダウンロジックで、小数端数の再配分を安定・再現性を保つソート順で実施するよう改善。

Security / Notes
- .env は決してリポジトリにコミットしない旨の注記を config_setup に記載。
- Settings._require は必須環境変数未設定時に ValueError を投げることで、起動時に早期検出を促進。
- run_execution / run_monitoring は停止フラグ（data/stop_requested.flag）や PID ファイルを利用して安全に起動・停止する設計。

今後の予定（短期）
- factor_research モジュールの実装完了（calc_momentum など一部が未完のため継続実装予定）。
- 銘柄別 lot_size 対応（stocks マスタに単元情報を持たせる拡張）。
- RiskManager / ExecutionEngine の統合テスト、及び broker のモックを用いた振る舞い検証スイート追加。
- config/*.yaml の内容に基づく動的設定反映（validate_config の拡張）。

補足
- これはコードベースの内容から推測して作成した変更履歴です。実際のコミット履歴やイシューには依存していません。詳細な差分やコミット単位の履歴が必要であれば、git ログやコミットメッセージを基にしたより正確な CHANGELOG を作成できます。