CHANGELOG
=========

すべての変更は Keep a Changelog の慣習に従って分類しています。
重大度の高い変更や破壊的変更がある場合は明記しています。

フォーマット:
- Unreleased: 将来リリース予定の変更（現時点では未使用）
- 各リリースは日付付きで記載

Unreleased
----------
（現時点で未リリースの変更はありません）

[0.1.0] - 2026-04-18
-------------------

初回リリース — 基本的な自動売買基盤と運用ユーティリティを実装。

Added
-----
- 全体
  - パッケージ初期バージョンを導入（__version__ = "0.1.0"）。
  - プロジェクト構成・実行スクリプト、各種ユーティリティ、ポートフォリオ構築・リスク調整・ポジション決定ロジック、検証ツール等を追加。

- 設定・起動関連
  - 環境変数/ .env 管理モジュール (kabusys.config)
    - プロジェクトルート自動検出（.git または pyproject.toml を基準）による .env 自動ロードを実装。
    - .env の行解析器を実装（コメント、export プレフィックス、シングル/ダブルクォート、エスケープ処理に対応）。
    - Settings クラスを追加し、各種設定値（J-Quants、kabuAPI、DB パス、Paper Trading 設定、監視しきい値等）をプロパティとして取得・検証。
    - PAPER_FILL_MODE 等の列挙的設定に対する検証を実装。

  - 環境設定ウィザード CLI (kabusys.config_setup)
    - 対話式で .env の生成/更新を行うウィザードを追加。
    - 入力補助（デフォルト表示、シークレットマスク、選択肢チェック）付き。
    - .env の読み込み/書き込みロジックを提供。

  - 設定検証 CLI (kabusys.validate_config)
    - 起動前に必須環境変数やファイルパス、config/*.yaml の存在と YAML パースを検証するツールを追加。
    - --strict オプションで警告をエラー扱いにできる。
    - 本番環境用の追加ガード（LINE 通知設定や KILL_FLAG_CLEAR_ON_START の警告）を実装。

- 実行/監視ランナー
  - 実行エンジン起動スクリプト (kabusys.run_execution)
    - ExecutionEngine を起動するエントリポイントを追加。
    - KABUSYS_ENV=paper_trading の場合、paper_trading 専用 SQLite (data/paper_trading.db) を使用し、本番 DB と分離。
    - ブローカークライアントのファクトリ経由生成、OrderRepository / OrderManager / RiskManager / Reconciler を組み立て、デーモンスレッドでセッション起動。
    - 停止フラグ（data/stop_requested.flag）検知による安全停止と PID ファイル管理処理を追加。

  - 監視ランナー (kabusys.run_monitoring)
    - SystemMonitor のポーリングループを起動するエントリポイントを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値は警告とデフォルトフォールバック。
    - 監視は環境にかかわらず本番 sqlite_path を用いて監視データを記録する（設計上の意図）。
    - 停止フラグ検知、例外時のログ出力、防御的な DB クローズを実装。

- ロギング・プロセス管理ユーティリティ
  - ログ設定ユーティリティ (kabusys.utils.logging_setup)
    - stdout 出力用 StreamHandler と日次ローテーションの TimedRotatingFileHandler（logs/<app>.log、30日保持）をルートロガーに設定。
    - LOG_LEVEL / LOG_DIR / 引数に基づく設定解決、既存ハンドラクリアの実装。
    - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみ継続。

  - プロセス優先度・CPU affinity ユーティリティ (kabusys.utils.process_priority)
    - Windows / POSIX（Linux/Mac/FreeBSD）差分を吸収した set_process_priority を実装（high/normal/low）。
    - set_cpu_affinity によるプロセスのコア固定機能を追加（権限不足時は警告でスキップ）。
    - 権限不足や未対応 OS に対するフォールバックとログ出力を実装。

- ポートフォリオ構築（純粋関数群）
  - portfolio.portfolio_builder
    - select_candidates: BUY シグナルをスコア降順かつ signal_rank でタイブレークして上位 N を選択。
    - calc_equal_weights: 等金額配分。
    - calc_score_weights: スコア正規化配分。全スコアが 0 の場合は等金額配分にフォールバックし警告を出す。

  - portfolio.risk_adjustment
    - apply_sector_cap: 同一セクターの既存エクスポージャが閾値を超える場合に新規候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数の提供。未知レジームはフォールバック（1.0）し警告を出す。

  - portfolio.position_sizing
    - calc_position_sizes: allocation_method ("risk_based", "equal", "score") に応じた株数算出を実装。
      - リスクベース計算（risk_pct, stop_loss_pct）と単元丸め（lot_size）、1銘柄上限・利用率上限、コストバッファを考慮。
      - aggregate cap (available_cash) を超える場合はスケーリングして lot_size 単位で残差を補正するアルゴリズムを実装。
      - 価格欠損時のスキップ、ゼロ除算回避、ログ出力を実装。

  - portfolio パッケージエクスポートを整備。

- 解析 / 検証ツール
  - tools.paper_verification_report
    - Paper Trading 用 SQLite の履歴から稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）、リスク却下数を集計して人間向けレポートを出力する CLI を追加。
    - 閾値（稼働率 99.0%、成立率 90%、送信率 95%、P95 レイテンシ 200 ms）に基づく PASS/FAIL 判定を実装。
    - 日付フィルタ（--from / --to）、DB パス指定（--db / 環境変数）をサポート。
    - P95 計算や欠損テーブルに対する防御的フォールバックを実装。

- 研究用モジュール（部分実装）
  - research.factor_research
    - モメンタム / ボラティリティ / バリュー等のファクター計算を想定した枠組みを追加（DuckDB 接続を受け取り prices_daily/raw_financials を参照する設計）。
    - モメンタム計算の定数とドキュメントを含む（コードの一部は継続実装の途中）。

Changed
-------
- （初回リリースのため該当なし）

Fixed
-----
- 環境変数パーサ:
  - クォート内のバックスラッシュエスケープやコメント判定の扱いを改善し、より堅牢な .env 読み込みを提供。
- MONITOR_POLL_INTERVAL のパース:
  - 不正（0 以下や非整数）な値を入力された場合に警告してデフォルト（60 秒）へフォールバック。

Security
--------
- .env 出力ウィザードでシークレット項目はマスク表示し、.env を Git にコミットしない旨を明示（README 的注意書きとして .env ファイル生成ヘッダに記録）。

Notes / Breaking changes
------------------------
- 本リリースでは監視用 DB（monitoring）と paper_trading 用 DB を明確に分離している。paper_trading 環境で実行する際は paper_trading 用 SQLite（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）を使用するため、本番の monitoring DB とは完全に独立して動作します。
- run_monitoring は「環境にかかわらず本番 sqlite_path を使う」仕様になっています。運用時に意図しない DB に記録されないよう設定を確認してください。
- process priority, cpu affinity の設定は権限依存のため、実行環境によっては設定に失敗して警告が出力されます（動作はスキップされます）。

Acknowledgements / Future work
------------------------------
- research.factor_research の完全実装（SQL 実装・Zスコア正規化ユーティリティ連携）や、ExecutionEngine 周りの詳細ロジック、テストケース整備、各コンポーネントのインターフェイス安定化を今後行う予定です。