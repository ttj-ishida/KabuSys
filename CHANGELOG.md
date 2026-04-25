Changelog
=========

すべての変更は Keep a Changelog の慣習に従って記載しています。
通常、セマンティックバージョニングを使用します。

フォーマット:
- Added: 新機能
- Changed: 変更点（後方互換性あり）
- Fixed: バグ修正（後方互換性あり）
- Security: セキュリティ関連修正

[Unreleased]
-------------

- （今後の変更予定）

[0.1.0] - 2026-04-25
--------------------

Added
- 全体
  - 初回リリース。KabuSys 自動売買フレームワークの基本コンポーネントを実装。
  - パッケージバージョンを __version__ = "0.1.0" として定義。

- 実行用スクリプト
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV が paper_trading の場合は専用の paper_trading SQLite DB を使用して本番 DB と分離（PAPER_TRADING_SQLITE_PATH で上書き可）。
    - ブローカークライアント生成を BrokerClientFactory に委譲。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine を起動。
    - 停止フラグ（data/stop_requested.flag）検出で安全に停止する仕組みを追加。
    - 実行中の PID を data/execution.pid に保存する仕組み（pid_file）を参照。

  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能（デフォルト 60 秒、無効値は警告してデフォルトを使用）。
    - 監視は環境にかかわらず本番用 sqlite_path を使用する設計。
    - 停止フラグ検出でループを抜けてリソースをクローズする安全な終了処理を実装。

- 設定・環境
  - config.py
    - .env / .env.local を自動でロードする機能を実装（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
    - .env のパース機能を実装（export KEY=val、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント処理に対応）。
    - Settings クラスを実装し、主要な環境変数をプロパティ経由で安全に取得（必須チェック・値検証含む）。
    - PAPER_FILL_MODE, KABUSYS_ENV, LOG_LEVEL 等の値検証を提供。
    - 本番/ペーパー/開発環境判定プロパティ（is_live, is_paper, is_dev）を追加。

  - config_setup.py
    - 対話式ウィザードにより .env を初期作成・更新する CLI を追加。
    - 秘匿項目はマスク表示、デフォルト値・選択肢の提示、既存 .env の読み込みと再利用に対応。
    - .env 書き込みテンプレートを定義（.env を絶対にコミットしない旨のヘッダ含む）。

  - validate_config.py
    - 起動前の設定検証 CLI を追加（必須環境変数、パスの存在チェック、config/*.yaml の存在・パース検証、KABUSYS_ENV=live 用の追加ガード等）。
    - --strict オプションで警告を失敗扱いにできる。

- ロギング・プロセス制御ユーティリティ
  - utils/logging_setup.py
    - 全アプリケーションで使える共通のログ設定ユーティリティを追加。
    - stdout へ StreamHandler、日次ローテートの TimedRotatingFileHandler（デフォルト logs/<app>.log）をルートロガーに設定。
    - ログディレクトリ作成失敗時はファイル出力をスキップしコンソール出力のみで継続する堅牢性を実装。
    - 既存ハンドラの二重設定回避（再設定時に既存ハンドラを flush/close して削除）。

  - utils/process_priority.py
    - クロスプラットフォーム（Windows / POSIX）でプロセス優先度（nice / Windows priority class）を設定するユーティリティを追加。
    - set_cpu_affinity による CPU ピニング機能を提供（アクセス権限や未対応 OS の場合は警告を出してスキップ）。
    - 無効なレベル値に対する ValueError、権限不足や未実装 API の場合は Warning を出す安全設計。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - select_candidates: BUY シグナルのスコア降順ソート、上位 N を選定。
    - calc_equal_weights, calc_score_weights: 等金額配分、およびスコア加重配分（スコア合計が 0 の場合は等配分へフォールバック）を実装。

  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中上限を満たすよう候補銘柄を除外する機能を実装（sell_codes を除外して計算、"unknown" セクターは制限対象外）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に基づく投下資金乗数を実装（未知レジームは警告の上で 1.0 にフォールバック）。

  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method("risk_based","equal","score") に応じて発注株数を計算するロジックを実装。
    - 単元（lot_size）丸め、1 銘柄上限（max_position_pct）、aggregate cap（available_cash）によるスケーリング、cost_buffer による保守的見積りを実装。
    - 現在保有との差分のみ発注する設計。価格欠損時のスキップやログ出力を実装。
    - aggregate スケーリング時に残余キャッシュを用いた lot 単位の再配分アルゴリズムを実装（端数の補完を再現性ある順序で割当）。

- リサーチ / ファクター計算
  - research/factor_research.py
    - モメンタム・ボラティリティ・流動性などのファクター計算のための基盤実装を追加。DuckDB 接続を受け prices_daily / raw_financials を参照して計算する設計。
    - 1M/3M/6M リターン、MA200 乖離、ATR 等の計算方針と定数を定義。
    - （注）ファイルは途中で切れているため一部実装が未完（今後のコミットで継続予定）。

- ツール
  - tools/paper_verification_report.py
    - ペーパートレーディング用の検証レポート生成ツールを追加。
    - system_status / trade_logs / risk_logs を参照して稼働率、注文成功率（fill rate）、送信率、P95 レイテンシ等を集計して PASS/FAIL 判定を行う。
    - コマンドライン引数 --from/--to/--db をサポート。PAPER_TRADING_SQLITE_PATH 環境変数も利用可。
    - デフォルト閾値（稼働率 99%、fill 90%、send 95%、P95 200ms）を定義し、基準未達の指摘を出力。

Changed
- なし（初回リリース）。

Fixed
- なし（初回リリース）。ただしロバスト化・入力検証（環境変数、.env のパース、ファイル/ディレクトリ作成失敗時のフォールバック等）を多く盛り込むことで運用時のエラー耐性を強化。

Security
- なし（初回リリース）。ただし secret（トークン・パスワード）入力はウィザードでマスク表示する配慮を実装。

Notes / 運用上の注意
- run_monitoring は「監視 DB」に対して常に sqlite_path（本番用）を使用します。paper_trading 環境で監視だけ別 DB にしたい場合は設定を見直してください。
- run_execution は KABUSYS_ENV=paper_trading の場合に paper_trading 用 DB を使用して本番 DB と明確に分離します。
- process priority / cpu affinity の設定は権限や OS に依存します。権限不足や未対応 OS では警告が出て処理をスキップします。
- factor_research.py は実装継続中の箇所があるため、該当機能を使用する際は補完実装を行ってください。

今後の予定（例）
- factor_research の完全実装（DuckDB SQL を用いた高速集計とテスト追加）
- ExecutionEngine / SystemMonitor 周りのエラーシナリオに対する E2E テスト追加
- 銘柄別 lot_size マスタ対応（position_sizing の拡張）
- ロギングの構成管理（ログレベルやログディレクトリの設定をより細かく扱う CLI/設定ファイルの追加）

--- 

（この CHANGELOG はソースコードの内容から推測して作成しています。実際のコミット履歴や設計ドキュメントに合わせて適宜修正してください。）