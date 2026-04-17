# CHANGELOG

すべての重要な変更は Keep a Changelog の形式に従って記載しています。  
バージョン番号は package の __version__（0.1.0）に合わせています。内容はソースコードから推測してまとめたものです。

なお、日付は本 CHANGELOG 作成日時（自動推定）を使用しています。実際のリリース日が別にある場合は適宜置き換えてください。

## [Unreleased]

- 小さな改善・内部リファクタ（将来のリリース向けのプレースホルダ）

---

## [0.1.0] - 2026-04-17

### Added
- 全体
  - 初期リリース。日本株自動売買システム「KabuSys」の基盤機能を実装。
  - パッケージメタ情報を src/kabusys/__init__.py にて version=0.1.0 として定義。

- 設定・環境管理
  - 環境変数/`.env` ファイル自動読み込み機能を実装（src/kabusys/config.py）。
    - プロジェクトルート検出（.git または pyproject.toml を基準）により cwd に依存しない読み込み。
    - `.env` / `.env.local` の優先順位処理、OS 環境変数の保護機能を実装。
    - クォート文字やエスケープ、インラインコメントの取り扱いなど、堅牢な .env パーサを実装。
    - Settings クラスを公開し、各種設定値（DB パス、API トークン、環境種別など）をプロパティ経由で取得可能に。
    - PAPER_FILL_MODE のバリデーション、有効値の明示化（instant/partial/never/reject）。
  - 設定ウィザード CLI を追加（src/kabusys/config_setup.py）。
    - 対話式で .env を生成・更新するウィザード。デフォルト・既存値の再利用、シークレットマスク表示、確認プロンプト付き。
    - 書き込み時に .env のテンプレートヘッダを出力。

- 構成検証
  - 設定検証 CLI を追加（src/kabusys/validate_config.py）。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性検証、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在・簡易パースチェック（PyYAML があれば内容検証）。
    - KABUSYS_ENV=live 時の追加ガード（LINE 設定や KILL_FLAG_CLEAR_ON_START の危険設定に警告）。

- 実行/監視ランナー
  - 実行エンジン起動スクリプト（src/kabusys/run_execution.py）を追加。
    - KABUSYS_ENV が paper_trading の場合は paper 専用 SQLite（data/paper_trading.db）を使用して本番 DB と完全分離。
    - BrokerClientFactory を利用してブローカークライアントを抽象化（paper/live を切り替え）。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み立て、ExecutionEngine をスレッドで起動。停止フラグ（data/stop_requested.flag）による安全停止処理を実装。
    - プロセス優先度を起動時に high に設定する挙動を導入。
  - 監視ポーリングループ起動スクリプト（src/kabusys/run_monitoring.py）を追加。
    - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用し、monitoring テーブルの初期化を保証。
    - MONITOR_POLL_INTERVAL 環境変数によりポーリング間隔を上書き可能。値の検証と不正値時のデフォルトフォールバック（60秒）を実装。
    - 停止フラグ検知でループを終了、例外発生時はログを出して次ポーリングへ復帰。

- モニタリング DB 初期化
  - init_monitoring_db を呼び出して監視用テーブルが必ず存在するようにする処理を実装（実装ファイルは monitoring パッケージ内に存在すると推定）。

- ユーティリティ
  - プロセス優先度 / CPU affinity 設定ユーティリティを追加（src/kabusys/utils/process_priority.py）。
    - Windows / POSIX（Linux/macOS 等）で差分を吸収。
    - set_process_priority(level) と set_cpu_affinity(cpu_count) を提供。権限・非対応環境では警告を出してスキップする安全設計。

- ポートフォリオ構築（純粋関数群）
  - 候補選定・重み計算（src/kabusys/portfolio/portfolio_builder.py）
    - select_candidates（スコア降順で上位 N を選択）。
    - calc_equal_weights（等金額配分）、calc_score_weights（スコア正規化配分、スコア合計が 0 の場合は等金額にフォールバック）。
  - セクター集中制限・レジーム乗数（src/kabusys/portfolio/risk_adjustment.py）
    - apply_sector_cap（既存保有のセクター比率が閾値を超える場合に当該セクターの新規候補を除外。unknown セクターは適用除外）。
    - calc_regime_multiplier（"bull"/"neutral"/"bear" に応じた資金乗数。未知レジームは 1.0 にフォールバックし警告）。
  - 株数決定・リスク制限・単元丸め（src/kabusys/portfolio/position_sizing.py）
    - calc_position_sizes: risk_based / equal / score の配分アルゴリズムを実装。
    - 単元（lot_size）で丸め、per-stock 上限・aggregate cap（available_cash） によるスケーリング、cost_buffer を考慮した保守的見積り、残余キャッシュを用いた端数調整ロジックを実装。

- 研究用ファクター計算
  - ファクター計算モジュール（src/kabusys/research/factor_research.py）。
    - Momentum（1M/3M/6M リターン、MA200乖離）、Volatility（ATR 等）、Liquidity（20日平均売買代金）などを DuckDB の prices_daily テーブルから計算する関数群を実装。
    - DuckDB 接続を受け取り SQL で計算、結果は (date, code) キーの dict リストを返す設計。

- Paper Trading 検証レポート
  - コマンドラインレポート生成ツール（src/kabusys/tools/paper_verification_report.py）。
    - paper_trading の SQLite（デフォルト: data/paper_trading.db）を読み、システム稼働率、注文成功率（fill/send）、リスク却下数、レイテンシ（平均/最大/P95）などを算出して人間向けレポートを出力。
    - P95 計算関数、しきい値（稼働率・成功率・送信率・P95 レイテンシ）による PASS/FAIL 判定を実装。

### Changed
- 全体設計
  - DB 分離ルールを明確化：paper_trading モードでは paper 専用 SQLite を使用し、本番データと完全に分離する方針を採用。
  - 設定ロード時に OS 環境変数を保護（既存の OS 環境を上書きしないデフォルト動作）。.env.local は override=True で上書き可能だが、OS 環境変数（protected）を上書きしない。

### Fixed / Robustness
- .env パーサの強化
  - 引用符付き値のバックスラッシュエスケープ処理、インラインコメント処理、不正行の無視など多数のケースに対応し、読み込みの堅牢性を高めた。
- process_priority の互換性
  - Windows 固有の優先度定数が存在しない場合に getattr でフォールバックするようにして、モジュールのインポート互換性を確保。
  - 権限不足や未実装 API 呼び出しは警告にとどめ、実行継続するように対応。
- CLI/起動周り
  - run_execution/run_monitoring での DB 接続の確実なクローズ処理（finally ブロック）を実装。
  - 実行開始前に停止フラグをチェックして、誤起動を防止するガードを追加。
  - MONITOR_POLL_INTERVAL の不正値（0 や非数）を検出し、既定値へフォールバックして warning ログを出力。

### Notes / Internal
- docstring にて外部ドキュメント（PortfolioConstruction.md, StrategyModel.md 等）を参照する設計思想が示されているが、これらのドキュメントや一部の実装依存ファイル（monitoring/*.py, execution/*.py の詳細実装や DuckDB のスキーマ）は本リポジトリ内に存在する想定（CHANGELOG はソースから推測して記載）。
- 一部の TODO コメント（例: position_sizing の銘柄別 lot_size 対応、price 欠損時のフォールバック等）が残っており、今後の改良ポイントとして残す。

---

参照:
- Keep a Changelog: https://keepachangelog.com/ja/1.0.0/