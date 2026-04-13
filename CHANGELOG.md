# CHANGELOG

すべての変更は Keep a Changelog 準拠で記載しています。  
バージョン付けはパッケージ内の __version__ に準拠しています。

## [Unreleased]

## [0.1.0] - 2026-04-13

### Added
- 基本リリース: KabuSys の初期実装を追加。
  - パッケージバージョンを 0.1.0 に設定（src/kabusys/__init__.py）。
- 実行/監視用エントリスクリプトを追加。
  - run_execution.py: ExecutionEngine を起動する CLI エントリポイント。Broker クライアントのファクトリ経由で本番/ペーパー（KABUSYS_ENV=paper_trading）を切替え、DuckDB/SQLite 接続を行い Engine を実行する。
    - Paper Trading 実行時は専用 SQLite（data/paper_trading.db がデフォルト）を使用して本番 DB と分離する設計。
    - 実行前にプロセス優先度を "high" に設定する呼び出しを追加（utils/process_priority.set_process_priority）。
  - run_monitoring.py: SystemMonitor のポーリングループを起動するスクリプト。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視処理は環境にかかわらず本番 sqlite_path を使用する仕様。
- 環境設定管理モジュールを実装（src/kabusys/config.py）。
  - .env/.env.local の自動読み込み（プロジェクトルート検出: .git または pyproject.toml）。
  - 自動ロード無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - .env パーサで export KEY=val、クォート、インラインコメント等に対応。
  - Settings クラスに各種プロパティを実装（DB パス、PID/KILL ファイルパス、閾値、env/log_level 判定、paper_trading 用設定等）。
  - PAPER_FILL_MODE のバリデーションを導入（instant/partial/never/reject）。
- Paper Trading 検証レポート生成ツールを追加（src/kabusys/tools/paper_verification_report.py）。
  - SQLite の paper_trading DB を解析して稼働率・注文成功率・送信率・レイテンシ（P95）等を計算し、PASS/FAIL 判定を出力する CLI ツールを提供。
  - --from / --to / --db オプションで期間および DB を指定可能。DB 欠損やテーブル未存在時に安全にフォールバック。
- ポートフォリオ構築関連の純粋関数群を追加（src/kabusys/portfolio）。
  - portfolio_builder: select_candidates、calc_equal_weights、calc_score_weights（スコアが全て 0 の場合は等配分にフォールバック）。
  - risk_adjustment: apply_sector_cap（セクター集中制限の適用）、calc_regime_multiplier（市場レジームに応じた乗数。未知レジームは警告のうえ 1.0 でフォールバック）。
  - position_sizing: calc_position_sizes（allocation_method に応じた発注株数算出。risk_based / equal / score 対応、単元丸め、aggregate cap によるスケールダウン、cost_buffer を考慮した保守的見積りなど）。
  - これらはすべて DB 参照を行わない純粋関数として設計（メモリ内計算）。
- Research 機能（src/kabusys/research）を追加。
  - factor_research: calc_momentum、calc_volatility、calc_value（DuckDB の prices_daily / raw_financials を用いたファクター計算）。
  - feature_exploration: calc_forward_returns、calc_ic（Spearman ランク相関）、factor_summary、rank（同順位は平均ランク）等の統計/解析ユーティリティ。外部ライブラリに依存せず実装。
- AI ニュース NLP スコアリングモジュールを追加（src/kabusys/ai/news_nlp.py）。
  - raw_news / news_symbols を集約し OpenAI（gpt-4o-mini）へバッチ送信してセンチメントスコアを ai_scores テーブルへ書き込む処理を実装。
  - API キー解決ロジック、バッチサイズ、トークン過多対策（記事数／文字数トリム）、リトライ（指数バックオフ）、レスポンス検証、スコアクリッピング（±1.0）等の堅牢化を実装。
  - タイムウィンドウ計算 util（calc_news_window）を提供し、ルックアヘッドバイアスを排除する設計。
- プロセス優先度・CPU affinity ユーティリティを追加（src/kabusys/utils/process_priority.py）。
  - set_process_priority(level) と set_cpu_affinity(cpu_count) を提供。Windows / POSIX(Linux/macOS/FreeBSD) を吸収し、権限不足や未対応環境では警告でスキップするフェイルセーフ。

### Changed
- DB 周りの設計方針を明確化。
  - 監視系は環境にかかわらず production 用 sqlite_path を参照する挙動を明記（run_monitoring）。
  - 実行系は paper_trading 時に専用 DB を使用して本番と論理的に分離（run_execution）。
- ロギングと初期化の順序を明確化。
  - run_* スクリプトで実行開始時に logging.basicConfig を設定し、最初にプロセス優先度を設定するように統一。
- .env 読み込みの挙動調整。
  - OS 環境変数は保護される（.env.local の override でも OS 環境変数を上書きしない）。
  - export 構文、クォート付き値のエスケープ、インラインコメントの扱いを強化。
- 各種入力値の検証を強化・明示化。
  - MONITOR_POLL_INTERVAL は正の整数でない場合に警告してデフォルトへフォールバック。
  - PAPER_FILL_MODE / KABUSYS_ENV / LOG_LEVEL の許容値チェックとエラーメッセージを追加。
  - calc_forward_returns の horizons 引数のバリデーション（正の整数かつ <= 252）を追加。
- リサーチ・ファクター/解析 SQL を DuckDB 上で完結するよう整理（スキャン長のバッファや NULL 伝播制御などによる安定化）。

### Fixed
- .env パーサの動作改善: 空行・コメント行の無視、export プレフィックス対応、引用符内のエスケープ処理、インラインコメント判定の改善により .env の互換性と安全性を向上。
- calc_score_weights: 全スコアが 0.0 の場合に等金額配分へフォールバックして警告を出すようにしてゼロ除算を回避。
- position_sizing のスケールダウンロジックにて残余キャッシュ配分の再現性を確保（ソートの安定化・lot_size 単位での補正）。
- process_priority: 未対応 OS や権限不足時に例外を吹き飛ばしてログ警告でスキップするように改善（起動時の堅牢性向上）。
- paper_verification_report: DB/テーブル未存在時に例外で落ちないように sqlite3.OperationalError を捕捉してフォールバックする処理を追加。

### Security
- OpenAI API キーは引数または環境変数（OPENAI_API_KEY）で解決され、未設定時は明示的にエラーを出すようにして秘密情報の未指定を検出可能に。

---

注記:
- 多くのモジュールは純粋関数（DB 非依存）で設計されておりユニットテストやリサーチ用途での再利用を想定しています。
- 各所で「将来の拡張」や TODO（銘柄別 lot_size、価格フォールバック等）がコメントで示されており、将来的な機能追加・改善の余地を残しています。