CHANGELOG
=========

この CHANGELOG は Keep a Changelog の形式に概ね準拠します。  
（コードベースから推測して作成しています。実際の変更履歴や日付は適宜調整してください。）

フォーマット:
- Added: 新規追加機能
- Changed: 仕様変更・改善
- Fixed: バグ修正・堅牢化
- Security: セキュリティ関連の注意
- Notes: 実装上の既知の制約や TODO

-----------------------------------------------------------------------

Unreleased
----------

- なし（現時点ではリリース v0.1.0 相当の機能群がメイン）

-----------------------------------------------------------------------

[0.1.0] - 2026-04-22
--------------------

Added
- 起動スクリプト
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止フラグファイル data/stop_requested.flag を検知してクリーンシャットダウン。
    - 監視は環境にかかわらず本番 sqlite_path を使用（監視データは本番 DB に記録）。
  - run_execution.py: ExecutionEngine の起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用の専用 SQLite（data/paper_trading.db）を使用し、本番 DB と分離。
    - 停止フラグと PID ファイルによるプロセス管理に対応。スレッドでエンジンをデーモン実行し、停止フラグで停止。
- 設定管理とウィザード・検証
  - config.py: 環境変数と設定値取得用 Settings クラスを追加。
    - .env 自動読み込み（.env, .env.local）をプロジェクトルートから行う（自動ロード無効化フラグあり）。
    - 各種設定（DB パス、PID パス、閾値、PAPER_FILL_MODE 等）の取得と簡易バリデーションを提供。
  - config_setup.py: 対話式 .env 作成/更新ウィザードを追加（CLI）。
    - 秘匿入力のマスク、選択肢/デフォルト対応、.env に保存するテンプレート生成を提供。
    - .env を絶対にコミットしない旨のヘッダを自動で書き出す。
  - validate_config.py: 起動前設定検証 CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の検証、DB パスや config/*.yaml の存在チェック、live 環境向けガードなどを実行。
    - --strict を指定すると警告も失敗扱いにできる。
- ポートフォリオ構築関連（純粋関数群）
  - portfolio.portfolio_builder:
    - select_candidates: BUY シグナルのスコア順選定（タイブレーク処理あり）。
    - calc_equal_weights, calc_score_weights: 等配分・スコア加重配分を提供（スコア全ゼロ時に等配分へフォールバック）。
  - portfolio.risk_adjustment:
    - apply_sector_cap: セクター集中制限を適用し、超過セクターの候補銘柄を除外。
    - calc_regime_multiplier: 市場レジームに基づく投下資金乗数を返す（bull/neutral/bear のマッピング、未知レジームはフォールバック）。
  - portfolio.position_sizing:
    - calc_position_sizes: 複数の配分方式（risk_based / equal / score）に基づいて発注株数を計算。
    - lot_size 単位で丸め、per-stock 上限や aggregate cap（available_cash）を考慮したスケーリング・残差処理を実装。
    - cost_buffer（手数料・スリッページ想定）を反映して保守的なコスト見積りを行う。
- ユーティリティ
  - utils.logging_setup: StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション）で一元的にロギングを設定するユーティリティを追加。
    - ログディレクトリ作成に失敗した場合はファイル出力を無効化して stdout のみで継続するフォールバック実装あり。
  - utils.process_priority: プラットフォーム（Windows / POSIX）に依存しないプロセス優先度設定と CPU affinity 設定を提供。
    - 権限不足や未対応 OS の場合は警告を出してスキップ。
- ツール
  - tools.paper_verification_report: Paper Trading 用検証レポート生成スクリプトを追加。
    - system_status / trade_logs / risk_logs から稼働率・注文成功率・送信率・レイテンシなどを集計し、PASS/FAIL 判定を行う。
    - P95 計算、期間フィルタ（--from/--to）や DB パスの引数/環境変数対応あり。
- リサーチ（部分実装）
  - research.factor_research: DuckDB を用いた定量ファクター計算モジュールの骨格（モメンタム・MA200・ATR 等の定義、関数スケルトン）を追加（実装途中の箇所あり）。

Changed
- なし（初期リリース相当の追加が主体）

Fixed / Robustness improvements
- .env パーサの強化
  - config._parse_env_line がシングル/ダブルクォート内のバックスラッシュエスケープやインラインコメントの扱いに対応。export KEY=val 形式にも対応。
  - .env の自動読み込みはプロジェクトルート (.git または pyproject.toml を探索) から行うため CWD に依存しない。
- ロギング設定の堅牢化
  - ログディレクトリの作成失敗時にファイルハンドラ作成を省略し、コンソール出力のみで継続するようにして起動失敗を回避。
- process_priority, set_cpu_affinity は権限/未対応プラットフォーム時に安全にスキップし、警告を出す実装に。
- run_monitoring._get_poll_interval: MONITOR_POLL_INTERVAL の不正入力に対して警告を出しデフォルトへフォールバックするバリデーションを追加。
- init_monitoring_db は冪等に監視テーブルの存在を保証する呼び出しとして統合（複数箇所から安全に呼べるように利用）。

Security
- config_setup にて生成される .env ファイルへ「絶対に Git にコミットしないこと」の注意を含めて出力。
- Settings._require は必須環境変数未設定時に明示的な ValueError を発生させ、起動前に問題に気付けるように。

Notes / Known limitations / TODO
- research.factor_research は一部実装が未完（ファイル末尾で切れている／スケルトンのみ）。フル実装が必要。
- position_sizing.calc_position_sizes:
  - price が欠損（0.0）の場合、エクスポージャーの過少見積りに繋がる可能性があり、将来的に前日終値や取得原価へのフォールバックを検討する旨の TODO がある。
  - lot_size は現在全銘柄共通。将来的に銘柄別 lot_map を受け取る拡張が想定されている。
- apply_sector_cap:
  - sector_map に存在しないコードは "unknown" 扱いでセクター上限制約を適用しない。必要に応じて扱いを変更する検討が必要。
- process_priority / set_cpu_affinity は OS 権限や psutil の機能制限により効果が出ない場合がある（警告を出してスキップ）。
- ロギングのファイルハンドラ作成・ディレクトリ作成に失敗した際はコンソール出力のみとなるため、運用時にログディレクトリの権限設定を確認すること。
- run_monitoring は監視データを本番 sqlite_path に記録する設計のため、監視用途と発注系の DB 分離については運用ポリシーに注意が必要（paper_trading は run_execution 側で専用 DB を使用）。

-----------------------------------------------------------------------

参考
- パッケージバージョン: __version__ = "0.1.0"
- 日付はソース解析時点（2026-04-22）を使用しました。適宜調整してください。