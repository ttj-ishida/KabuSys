CHANGELOG
=========

すべての重要な変更点を記録します。本ファイルは "Keep a Changelog" の形式に準拠しています。

フォーマット:
- 既知のリリースのみを記載（初回リリース: 0.1.0）
- 日付はリリース日です

[0.1.0] - 2026-04-18
-------------------

Added
- 全体
  - 初回リリースを公開（__version__ = "0.1.0"）。
  - DuckDB / SQLite を用いたデータ処理基盤の土台を追加。

- 実行・監視スクリプト
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合に MockBrokerClient を使用し、paper_trading 用の専用 SQLite（デフォルト: data/paper_trading.db）にデータを記録する仕組みを実装。
    - BrokerClientFactory, OrderRepository, OrderManager, RiskManager, Reconciler 等の組み立てと、スレッドでの ExecutionEngine 実行、stop フラグ（data/execution.pid / data/stop_requested.flag）による安全停止処理を実装。
    - 起動時にプロセス優先度を "high" に設定。

  - run_monitoring.py
    - SystemMonitor ポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値は警告を出しデフォルトにフォールバック。
    - 監視は環境（KABUSYS_ENV）にかかわらず本番の sqlite_path を使用する設計。
    - 停止フラグ（data/stop_requested.flag）検知でループを終了。

- 設定関連
  - config.py
    - Settings クラスを追加し、環境変数からアプリ設定を抽象化（J-Quants / kabu API / DB パス /監視閾値など）。
    - 自動 .env ロード機構を追加（プロジェクトルート検出: .git または pyproject.toml を起点）。OS 環境変数を保護する仕組みあり。
    - .env パースはクォートやエスケープ、コメントの扱いに対応。
    - PAPER_FILL_MODE のバリデーション（instant/partial/never/reject）や PAPER_TRADING_SQLITE_PATH 等、ペーパートレード向け設定を追加。

  - config_setup.py
    - 対話式ウィザードで .env の初期作成・更新を行う CLI を追加。
    - 各設定項目のラベル・説明・既定値・選択肢を提示し保存処理（.env 生成）を行う。
    - シークレット入力はマスク表示。既存 .env の読み込み・再利用に対応。

  - validate_config.py
    - 起動前の設定検証 CLI を追加（必須環境変数の存在、KABUSYS_ENV や LOG_LEVEL の妥当性、DB パスや config/*.yaml の存在等をチェック）。
    - --strict モードで警告も失敗扱いにできる。
    - PyYAML 未インストール時は YAML 検証をスキップし警告を出す。

- ユーティリティ
  - utils/logging_setup.py
    - 統一的なログ設定ユーティリティを追加。
    - ルートロガーに StreamHandler (stdout) と TimedRotatingFileHandler（日次、30日保持）を設定。
    - ログディレクトリ作成失敗時はファイル出力を無効化してコンソール出力のみで継続。
    - ログレベル/ログディレクトリ解決ロジックを実装（引数 > 環境変数 > デフォルト）。

  - utils/process_priority.py
    - プロセス優先度（high/normal/low）と CPU affinity 設定機能を追加。
    - Windows/Linux/macOS 系に対応し、アクセス権限エラー時は警告を出しスキップ。
    - set_cpu_affinity によりプロセスを先頭 N コアにピン留め可能。

- ポートフォリオ構成（純関数群）
  - portfolio/portfolio_builder.py
    - シグナル候補の選定（スコア降順、signal_rank でタイブレーク）。
    - 等金額配分 calc_equal_weights、スコア加重配分 calc_score_weights（全スコアが 0 の場合は等分配へフォールバック）。

  - portfolio/risk_adjustment.py
    - セクター集中制限 apply_sector_cap を実装（既存保有のセクター比率が閾値超過のセクターから新規候補を除外）。
    - 市場レジームに応じた投下資金乗数 calc_regime_multiplier（bull/neutral/bear 向けマップ）を提供。
    - 不明セクターは "unknown" 扱いで上限適用除外とする設計上の判断を明記。

  - portfolio/position_sizing.py
    - position サイズ計算を実装（allocation_method: risk_based / equal / score）。
    - risk_based: 許容リスク率・stop_loss を用いた株数算出。
    - equal/score: 重みと max_utilization を用いた配分。
    - 単元株（lot_size）丸め、aggregate cap によるスケールダウンと端数配分ロジック（残余キャッシュで lot 単位の追加配分）を実装。
    - cost_buffer を考慮して保守的なコスト見積りを行う。

- リサーチ / ファクター計算
  - research/factor_research.py
    - モメンタム等のファクター計算モジュールを追加（設計・定数・calc_momentum の骨格を実装）。
    - DuckDB 接続を受け取り prices_daily / raw_financials テーブルを参照して各種ファクター（mom_1m/3m/6m、MA200 乖離など）を計算する方針。
    - （注）ファイル末尾で実装が途中で切れている個所があり、calc_momentum の SQL 呼び出し等の詳細は継続実装が必要。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading 用検証レポート生成スクリプトを追加。
    - システム稼働率、注文成功率、送信率、リスク却下数、API レイテンシ（平均・最大・P95）を算出して PASS/FAIL 判定を行う。
    - デフォルト DB は data/paper_trading.db。--db / 環境変数で上書き可能。
    - P95 計算ユーティリティと各種閾値（稼働率 99%、成功率 90% 等）を定義。

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。

Deprecated
- 初回リリースのため該当なし。

Removed
- 初回リリースのため該当なし。

Security
- 初回リリースのため該当なし。

Notes / Known issues / TODO
- research/factor_research.py は実装途中（ファイル末尾が切れている）。ファクター計算ロジックの完成が必要。
- portfolio/risk_adjustment.apply_sector_cap:
  - price_map に price が欠損（0.0）だとエクスポージャが過少見積りされ、想定外の振る舞いとなる旨の TODO コメントあり。前日終値等のフォールバックを将来検討する予定。
- position_sizing:
  - 将来的に銘柄別の lot_size を持たせる設計への TODO コメント（現状は全銘柄共通単元 100 を想定）。
- run_monitoring は監視 DB に本番 sqlite_path を常に使用するため、監視とペーパートレード DB の混同に注意。
- 自動 .env ロードはプロジェクトルートが検出できない場合はスキップされる（パッケージ配布時の安全措置）。
- テスト、ドキュメント（Usage / API リファレンス）、および一部のエラーハンドリング/境界条件については追加整備が必要。

開発上の補足
- ログはデフォルトで stdout と logs/<app_name>.log（ローテーション）に出力。ログディレクトリ作成に失敗した場合はファイル出力を行わないが処理は継続する。
- プロセス優先度や CPU affinity の設定は権限や OS に依存するため、失敗時は警告を出してスキップする設計。

今後の予定（短期）
- factor_research の完成（ファクター群の SQL 実装・正規化ユーティリティ統合）
- テストの整備（ユニット/統合）
- 設定・起動に関するドキュメント追記
- 監視・実行コンポーネントの追加的な堅牢性強化（リトライ戦略、より詳細なメトリクス）

----- 

注: 本 CHANGELOG はコードベースの内容から推測して作成しています。実際の設計意図や未公開の変更点がある場合は、適宜更新してください。