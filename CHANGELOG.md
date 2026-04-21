# Changelog

すべての重要な変更をここに記載します。本ファイルは Keep a Changelog の様式に準拠します。  

現在のリリース履歴:

- [0.1.0] - 2026-04-21

---

[0.1.0] - 2026-04-21
--------------------

Added
- 初回公開リリース: KabuSys v0.1.0 を追加。
- 実行エントリポイント
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。  
    - KABUSYS_ENV に応じた DB 切り分け (paper_trading 時は PAPER_TRADING_SQLITE_PATH / data/paper_trading.db を使用) と BrokerClientFactory によるブローカクライアント生成を実装。  
    - プロセス優先度を高 priority に設定する仕組みを起動時に実行。  
    - 停止フラグ (data/stop_requested.flag) を監視して安全に終了するループを実装。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。  
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。  
    - 監視は環境にかかわらず本番 sqlite_path を使用する挙動を明示。  
    - stop フラグの検知、例外時のログ出力、終了時の DB クローズ等を実装。
- 設定管理・CLI
  - config.py: 環境変数ロードと Settings クラスを実装。  
    - .env / .env.local 自動読み込み（プロジェクトルート自動検出、KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能）。  
    - 複数の設定プロパティを提供 (J-Quants / kabuAPI / LINE / DB パス / 監視閾値 / 環境チェック等)。  
    - PAPER_FILL_MODE のバリデーション、paper_sqlite_path 等の便利なプロパティを追加。  
  - config_setup.py: 対話式 .env 作成ウィザードを追加。  
    - 秘匿項目のマスク表示、既存 .env の読み込み・編集、保存処理を提供。  
  - validate_config.py: 起動前設定検証 CLI を追加。  
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在・パース検証（PyYAML が無い場合はスキップして警告）等を実施。  
    - --strict モードで警告を FAIL 扱いにできる。
- ポートフォリオ構築ライブラリ
  - portfolio/portfolio_builder.py: 候補選定・重み計算（select_candidates, calc_equal_weights, calc_score_weights）を実装。  
    - スコア降順の選定、スコア合計が 0 の場合のフォールバック等をハンドリング。
  - portfolio/risk_adjustment.py: セクター集中制限 apply_sector_cap とレジーム乗数 calc_regime_multiplier を実装。  
    - セクター別エクスポージャ計算、売却予定銘柄の除外、unknown セクターの扱い、レジーム毎のデフォルト乗数（bull/neutral/bear）を提供。  
  - portfolio/position_sizing.py: 発注株数決定ロジックを実装（calc_position_sizes）。  
    - allocation_method として "risk_based" / "equal" / "score" をサポート。  
    - lot_size（単元株）丸め、1銘柄上限、aggregate cap（available_cash 超過時のスケーリング）や cost_buffer を用いた保守的見積り、残差処理による割り当てロジックを実装。
  - portfolio/__init__.py で上記関数群を公開。
- モニタリング / DB 初期化
  - monitoring.monitoring_db の init_monitoring_db を起動時に呼び出し、監視テーブルの存在を保証（冪等）。
- 実行補助ツール
  - tools/paper_verification_report.py: Paper Trading 用検証レポート生成スクリプトを追加。  
    - 稼働率・注文成功率・送信率・リスク却下数・API レイテンシ（平均/最大/P95）を集計して判定（PASS/FAIL）を出力。  
    - 日付フィルタ、P95 計算、DB 存在チェック、閾値（稼働率 99%、成立率 90% 等）を実装。
- ロギング & プロセス制御ユーティリティ
  - utils/logging_setup.py: 共通ロギング初期化関数 setup_logging を追加。  
    - stdout ストリームハンドラと日次ローテーションのファイルハンドラ（TimedRotatingFileHandler）をルートロガーに設定。ログディレクトリ作成失敗時はコンソール出力にフォールバック。  
    - LOG_LEVEL / LOG_DIR の解決順を実装。
  - utils/process_priority.py: psutil を利用したプロセス優先度設定と CPU affinity 設定を追加。  
    - Windows と POSIX(Linux/macOS/FreeBSD) を吸収する実装。権限不足などの失敗時は警告出力してスキップ。
- リサーチ基盤（着手）
  - research/factor_research.py: DuckDB を用いたファクター計算モジュールの骨組みを追加（モメンタム等の定義と calc_momentum の署名と説明）。実装途中での追加。
- パッケージ情報
  - src/kabusys/__init__.py に __version__ = "0.1.0" を設定。

Changed
- 初回公開につき変更履歴はなし（新規実装の集合）。

Fixed
- 該当なし（初回リリース）。

Security
- 該当なし。

Notes / Implementation details / 既知の制約
- .env 自動ロードはプロジェクトルートが検出できない場合はスキップされる。自動ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD を設定する。  
- run_monitoring は監視 DB（sqlite_path）を環境に関わらず本番用パスで接続する仕様。paper_trading の完全分離は run_execution 側で paper_sqlite_path を用いる。  
- position_sizing の lot_size は現状全銘柄共通（将来的に銘柄別拡張を予定）。  
- apply_sector_cap の価格欠損時の挙動に関する TODO コメントあり（フォールバック価格の利用検討）。  
- research/factor_research.py は一部未完（calc_momentum の実装が途中で切れている）。今後のリリースでファクター計算を完成予定。

---

今後の予定（例）
- factor_research の実装完了（モメンタム / ボラティリティ / バリュー / 流動性ファクター）とテスト追加。  
- ExecutionEngine / RiskManager / OrderManager 周りのユニットテストとエンドツーエンドの紙トレード検証。  
- ドキュメント（PortfolioConstruction.md 等）のコード参照整合性チェックとサンプル設定ファイルの充実。

--- 

（注）本 CHANGELOG は与えられたコードベースの内容から推測して作成しています。実際の変更履歴やリリース日付はリポジトリのコミット履歴等に基づいて調整してください。