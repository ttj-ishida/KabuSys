Keep a Changelog に準拠した形式で、コードベースの内容から推測した変更履歴を日本語で作成しました。
バージョン情報はパッケージ定義の __version__（0.1.0）と現在日付（2026-04-19）を用いています。必要に応じて日付やバージョンは調整してください。

CHANGELOG.md
=============
All notable changes to this project will be documented in this file.

フォーマット: https://keepachangelog.com/ja/1.0.0/

[Unreleased]
------------

[0.1.0] - 2026-04-19
--------------------
Added
- 基本機能（初期リリース）
  - 株自動売買システム KabuSys の初期モジュール群を追加。
  - パッケージバージョンを 0.1.0 に設定。

- 起動スクリプト / 実行フロー
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading 時は paper_trading 用 DB を使用（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）。
    - BrokerClientFactory を用いたブローカー抽象化を導入。
    - ExecutionEngine をスレッドで実行し、data/stop_requested.flag による安全停止をサポート。
    - 起動時にプロセス優先度を "high" に設定する仕組みを実装。
  - run_monitoring.py: SystemMonitor 用のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境に依らず本番用 sqlite_path を使用する設計。
    - 停止フラグ file（data/stop_requested.flag）を検知してループを終了。

- 環境・設定管理
  - config.py: 環境変数と設定読み込みクラス Settings を追加。
    - .env 自動ロード（プロジェクトルート判定: .git / pyproject.toml）。
    - .env/.env.local の読み込み順と OS 環境変数保護（protected keys）。
    - 複数の設定プロパティ（DBパス、API トークン、KABUSYS_ENV, LOG_LEVEL, 各しきい値等）。
    - PAPER_FILL_MODE の検証、paper_sqlite_path など paper_trading 特有項目のサポート。
  - config_setup.py: 対話式 .env ウィザードを追加（.env の初期作成/更新を支援）。
    - 秘匿入力、選択肢サポート、.env 書き出しテンプレートを搭載。
  - validate_config.py: 設定検証 CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パス存在確認（親ディレクトリ）、config/*.yaml の存在・パースチェック（PyYAML がある場合）。
    - --strict モードで警告を FAIL 扱いにできる。

- ポートフォリオ構築（純粋関数群）
  - portfolio.portfolio_builder
    - select_candidates: BUY シグナルをスコア降順で選定（タイブレークに signal_rank）。
    - calc_equal_weights / calc_score_weights: 等金額配分・スコア加重配分を提供。スコア合計が 0 の場合は等配分にフォールバックして警告を出力。
  - portfolio.risk_adjustment
    - apply_sector_cap: セクター集中上限ロジック（既存ポジションのセクター比率を計算し、上限超過セクターの候補を除外）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数（未定義レジームは警告して 1.0 フォールバック）。
  - portfolio.position_sizing
    - calc_position_sizes: allocation_method（risk_based / equal / score）に基づく発注株数計算。
      - lot_size（単元）丸め、max_position_pct、max_utilization、cost_buffer を考慮した aggregate cap のスケーリング。
      - 価格欠損時のスキップ、スケーリング時の残差処理（小数端数を考慮して lot 単位で追加配分）を実装。

- 監視・ログ周りユーティリティ
  - utils.logging_setup: 統一されたログ設定ユーティリティを追加。
    - stdout への StreamHandler、日次ローテーション（TimedRotatingFileHandler）でログファイルを logs/<app>.log に保存（保管 30 日）。
    - ログレベル・ログディレクトリの解決ロジック（引数 > 環境変数 > デフォルト）。
    - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソール出力のみ継続。
  - utils.process_priority: プロセス優先度 / CPU affinity 設定ユーティリティを追加。
    - Windows / POSIX の差分吸収（psutil ベース）。優先度レベル: high / normal / low。
    - set_cpu_affinity により最初の N コアにプロセスをピン留め可能。
    - 権限不足や未サポート環境では警告ログを出してスキップ。

- 分析・検証ツール
  - tools.paper_verification_report: Paper Trading 用検証レポート生成スクリプトを追加。
    - DB（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）から統計を集計し、稼働率・注文成功率・送信率・レイテンシ（平均/最大/P95）等を出力。
    - デフォルト閾値を定義（稼働率 99% など）し、PASS/FAIL を判定。
    - DB テーブル欠如時に安全に N/A を返すフォールトトレランスあり。

- 研究用モジュール（部分実装）
  - research.factor_research: ファクター計算基盤を追加（Momentum, Value, Volatility, Liquidity を想定）。
    - calc_momentum の実装スケルトン（DuckDB 接続を受け prices_daily を参照し、mom_1m/3m/6m, MA200 乖離を計算する設計）を含む（実装途中）。

Changed
- N/A（初期リリース） — 将来のリリースで変更点を記述予定。

Fixed
- .env パーサーの堅牢化
  - config._parse_env_line: export プレフィックス対応、クォート内のバックスラッシュエスケープ処理、インラインコメントの扱い、クォートなしのコメント処理の改良を実装。
  - _load_env_file: ファイル読み込み失敗時に警告を出して処理を継続（テスト耐性向上）。
  - 自動ロードにおける OS 環境変数保護（protected keys）を実装し、既存 OS 環境を上書きしないようにした。

- 複数箇所での安全停止 / リソース解放
  - run_execution/run_monitoring: 停止フラグ検知時の安全な終了処理と DB 接続のクローズを確実化。
  - run_execution: スレッド終了待ちのタイムアウト処理（join timeout）を追加。

Security
- 秘匿値の取り扱いに注意（config_setup で .env にトークン等を平文で保存するため、.env を絶対に Git にコミットしない旨の注意書きを追加）。

Deprecated
- なし

Removed
- なし

Notes / Implementation details
- 監視 DB（monitoring.db）と Paper Trading DB（paper_trading.db）は設計上分離されている。run_monitoring は常に settings.sqlite_path（本番監視 DB）を使用し、run_execution は KABUSYS_ENV により paper_trading 用 DB を選択する。
- ロギングは stdout を StreamHandler に使用（cron やスケジューラでのログ集約を想定）。
- position_sizing や risk_adjustment は純粋関数（副作用なし）として設計され、テスト容易性を重視。
- DuckDB を分析用に使用し、research モジュールは DuckDB 接続を受けて SQL/Python 混在でファクターを計算する設計。

今後の予定（例）
- research.factor_research の完全実装（全ファクター計算・正規化）。
- strategy / execution の統合テスト、シミュレーションバッチの自動化。
- 銘柄マスタに lot_size 等を含めた拡張（position_sizing の銘柄別単元サポート）。
- 監視・アラートの LINE 通知統合強化（本番向けの通知テスト）。

--- 
（注）本 CHANGELOG はご提供のコード内容から推測した初期リリースの要点をまとめたもので、実際の変更履歴やリリースノートと差異がある場合があります。必要であれば日付・バージョンや文言の調整、より詳細なコミット単位の履歴化（git log ベースの生成）を行えます。