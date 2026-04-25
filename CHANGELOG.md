# Changelog

すべての notable な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠しています。  
翻訳・記述はコードベースの内容から推測して作成しています。

- リリースノートは新しい順に記載しています。
- 各エントリは Added / Changed / Fixed / Security などのカテゴリで整理しています。

## [0.1.0] - 2026-04-25

Added
- 基本アプリケーションパッケージを追加
  - パッケージ名: kabusys、バージョン: 0.1.0
- 起動スクリプト
  - run_execution.py: ExecutionEngine を起動するエントリポイントを追加。  
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite（デフォルト: data/paper_trading.db）と MockBrokerClient を使用し、本番 DB と分離。
    - 起動時にプロセス優先度を "high" に設定し、停止フラグ (data/stop_requested.flag) と PID ファイル管理を行う。
    - スレッドでエンジンを実行し、停止フラグ検知時に安全に停止する処理を実装。
  - run_monitoring.py: SystemMonitor のポーリングループを起動するエントリポイントを追加。  
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒、無効値は警告してデフォルトにフォールバック）。
    - 監視 DB は環境にかかわらず本番 sqlite_path を使用する（意図的な動作）。
    - 停止フラグ検知でループを抜け、DB 接続を確実にクローズする安全設計。
- 設定管理
  - config.py: 環境変数/.env 読み込みと Settings クラスを実装。
    - プロジェクトルート自動検出（.git または pyproject.toml を基準）により .env / .env.local の自動ロードを行う（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
    - .env の読み込みは OS 環境変数を保護（上書き防止）する仕組みを実装。
    - 多くの設定プロパティを提供（J-Quants、kabu API、LINE、DB パス、監視閾値、環境種別検証など）。
    - PAPER_FILL_MODE の値検証（instant/partial/never/reject）を実装。
- 設定ユーティリティ / CLI
  - config_setup.py: 対話式ウィザードで .env を初期作成・更新するツールを追加。  
    - シークレット値のマスク表示、選択肢サポート、既存値の再利用、最終確認後に .env を書き込む機能を提供。
  - validate_config.py: 起動前の設定検証ツールを追加。  
    - 必須環境変数チェック、KABUSYS_ENV や LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリチェック、config/*.yaml の存在・パース検証（PyYAML があれば内容検証）を実施。  
    - --strict オプションで警告を FAIL 扱いにする。
- ロギング＆プロセス制御ユーティリティ
  - utils/logging_setup.py: 統一的なロギング設定ユーティリティを追加。  
    - コンソール出力（stdout）と日次ローテーションファイル（logs/<app>.log、30 日分保持）をルートロガーに設定。  
    - ログディレクトリ作成失敗時はファイルハンドラをスキップしてコンソールのみで継続。
  - utils/process_priority.py: クロスプラットフォームなプロセス優先度設定と CPU affinity 設定を追加。  
    - Windows / POSIX の差異を吸収、psutil を用いた実装。権限不足等は警告してスキップ。
- ポートフォリオ構築関連（純粋関数群）
  - portfolio/portfolio_builder.py: 候補選定と重み計算（等金額・スコア加重）を実装。  
    - 同点タイブレークやスコアが全て 0 の場合のフォールバックを考慮。
  - portfolio/risk_adjustment.py: セクター集中制限（apply_sector_cap）と市場レジーム乗数（calc_regime_multiplier）を実装。  
    - セクターが "unknown" の取り扱いや、レジームマップ（bull/neutral/bear）を実装。
  - portfolio/position_sizing.py: 株数決定ロジックを実装（risk_based / equal / score）。  
    - 単元株丸め（lot_size）、1 銘柄上限、aggregate cap（available_cash に対するスケーリング）、cost_buffer を考慮した投資額調整／残差分配アルゴリズムを実装。
- 研究／ファクター計算
  - research/factor_research.py: ファクター計算基盤（Momentum, Value, Volatility, Liquidity）に関するモジュールを追加。  
    - Momentum 計算（mom_1m / mom_3m / mom_6m / ma200_dev）などの実装方針と定数を定義（DuckDB 接続で prices_daily を参照する設計）。
- ツール
  - tools/paper_verification_report.py: Paper Trading 用検証レポート生成ツールを追加。  
    - 稼働率、注文成功率（fill rate）、送信率、レイテンシ（平均 / 最大 / P95）を算出・判定し、PASS/FAIL 判定基準を実装。  
    - --from / --to / --db オプションで期間・DB を指定可能。デフォルト DB は PAPER_TRADING_SQLITE_PATH または data/paper_trading.db。
- 汎用パッケージ初期化
  - __init__.py にてバージョン (0.1.0) とエクスポート設定を追加。

Changed
- （初回リリース）設計上の注意点や安全策を複数箇所で導入：  
  - DB 接続の確実なクローズ、停止フラグの使用、PID ファイル管理、ログ設定の失敗時フォールバックなど。

Fixed
- （実装時点での堅牢性向上）
  - .env パーサ: シングル/ダブルクォート処理、バックスラッシュによるエスケープ、コメント扱いの改善を実装。  
  - logging_setup: 既存ハンドラを flush/close してから削除することで二重設定を防止。

Security
- シークレット値の取り扱い: config_setup の対話表示でシークレットをマスク表示し、.env を生成する際に注意喚起を追記。

Notes / Known limitations
- research/factor_research.py は DuckDB を前提に設計されており、実行には prices_daily / raw_financials テーブル等のデータ準備が必要です。
- 一部の細かなフォールバック（例: position_sizing の price 欠損時の価格フォールバック）は TODO コメントとして残されています。
- run_monitoring/run_execution はファイルベースの停止フラグ・PID 管理を前提とするため、コンテナ運用等で別の運用慣習がある場合はラッパーや調整が必要です。

今後の予定（提案）
- ファクター計算・シグナル生成の統合テスト、DuckDB テーブルのスキーマ検証ツール追加。
- stocks マスタで単元株情報 (lot_size) を保持し、position_sizing を銘柄別単元対応に拡張。
- モニタリング・実行のユニット/統合テスト強化、CI での自動検証導入。

--- 

（この CHANGELOG は現在のコードベースの構造・コメント・ docstring から推測して作成しています。実際の変更履歴やリリース日付はプロジェクトの運用に合わせて適宜調整してください。）