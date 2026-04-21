# CHANGELOG

すべての変更は Keep a Changelog のフォーマットに従います。  
このファイルは主にコードベースから推測して作成した初期リリースの変更履歴です。

## [0.1.0] - 2026-04-21

初回リリース。KabuSys の基本的な構成管理、起動スクリプト、ポートフォリオ構築、実行/監視ランナー、ユーティリティ、検証ツール、およびペーパートレード検証レポート生成機能を導入しました。

### 追加
- コアパッケージ
  - パッケージ初期化とバージョン定義 (src/kabusys/__init__.py)。
- 設定管理
  - Settings クラスによる環境変数ベースの設定取得（J-Quants / kabuステーション / DB パス /監視閾値等）(src/kabusys/config.py)。
  - .env 自動ロード機能（プロジェクトルート自動検出、優先順位: OS 環境変数 > .env.local > .env、KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化）を追加。プロジェクトルートは .git または pyproject.toml を探索して特定。
  - .env パーサーが export KEY=val 形式、クォートされた値、インラインコメントなどに対応。
  - PAPER_FILL_MODE（"instant" | "partial" | "never" | "reject"）等の検証を組み込み。
- 起動スクリプト / ランナー
  - 実行エンジン起動スクリプト: run_execution（src/kabusys/run_execution.py）
    - KABUSYS_ENV=paper_trading 時に MockBrokerClient を使用し、paper_trading 用専用 SQLite DB を使用して本番 DB と分離。
    - プロセス優先度を起動時に "high" に設定（platform 横断実装を利用）。
    - エンジンはデーモンスレッドで実行され、data/stop_requested.flag により安全に停止可能。
    - デフォルトの PID ファイルパス管理。
  - 監視ループ起動スクリプト: run_monitoring（src/kabusys/run_monitoring.py）
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバック。
    - 監視は環境にかかわらず本番 sqlite_path を参照して監視テーブルを初期化。
    - 停止フラグ検知と例外隔離（check_once() 内の例外はログ出力して次サイクルへ）。
- 検証・セットアップツール
  - 設定検証 CLI: validate_config（src/kabusys/validate_config.py）
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の検証、DB パス/親ディレクトリチェック、config/*.yaml の存在とパース検証（PyYAML が利用可能な場合）。
    - --strict オプションで警告を FAIL 扱いにできる。
  - 環境設定ウィザード CLI: config_setup（src/kabusys/config_setup.py）
    - 対話式ウィザードで .env の初期作成・更新を支援。シークレット入力のマスク、選択肢、デフォルト値表示、保存確認など。
- ポートフォリオ構築（純粋関数群、DB 非依存）
  - portfolio_builder: select_candidates（スコア降順選定）、calc_equal_weights、calc_score_weights（スコアが全て 0 の場合に等分配へフォールバック） (src/kabusys/portfolio/portfolio_builder.py)。
  - risk_adjustment: apply_sector_cap（セクター集中制限適用。unknown セクターは除外しない）、calc_regime_multiplier（レジームに基づく投下資金乗数） (src/kabusys/portfolio/risk_adjustment.py)。
  - position_sizing: calc_position_sizes（等分/スコア/リスクベースの発注株数決定、単元株丸め、aggregate cap スケーリング、cost_buffer を考慮） (src/kabusys/portfolio/position_sizing.py)。
- ユーティリティ
  - ログ設定ユーティリティ: setup_logging（コンソール stdout と TimedRotatingFileHandler による日次ローテーション、既存ハンドラのクリアなど） (src/kabusys/utils/logging_setup.py)。
  - プロセス優先度/CPU affinity ユーティリティ: set_process_priority / set_cpu_affinity（psutil を使用、Windows / POSIX を吸収） (src/kabusys/utils/process_priority.py)。
- ツール
  - Paper Trading 検証レポート生成スクリプト: tools/paper_verification_report（期間指定可、PAPER_TRADING_SQLITE_PATH で DB 指定、稼働率・注文成功率・送信率・レイテンシ等を集計して PASS/FAIL 判定） (src/kabusys/tools/paper_verification_report.py)。
- 研究用途（計算モジュールの骨組み）
  - factor_research モジュールの導入（DuckDB 接続を受け取りモメンタム / Value / Volatility / Liquidity 等を計算する設計。注: ファイル末尾で未完の関数あり） (src/kabusys/research/factor_research.py)。

### 変更
- ログ挙動
  - デフォルトで logs/ ディレクトリを作成してアプリごとのログファイル（<app_name>.log）を日次ローテーションで管理。作成失敗時はファイル出力をスキップしてコンソールのみで継続。
  - コンソール出力は stderr ではなく stdout を使用（cron 等で stdout/stderr をリダイレクトしやすくするため）。
- .env 読み込みの安全策
  - 自動ロード時に既存 OS 環境変数は保護（protected）され、.env.local は .env を上書きするが OS 変数は上書きしない。
- 起動時のプロセス優先度を先頭で設定することで監視/実行プロセスの優先度を保証。
- run_execution は paper_trading 環境で専用 DB を使用するよう明確化（本番 DB からの完全分離）。

### 修正（堅牢性向上）
- .env ファイル読み込みでファイルオープン失敗時に例外を投げず warnings.warn で通知して継続するよう対応（読み込み失敗時の耐障害性向上）。
- _parse_env_line の実装を改善し、クォート中のバックスラッシュエスケープやインラインコメント処理に対応。
- MONITOR_POLL_INTERVAL の取得関数で 0 以下や非整数の値を検出した際にデフォルトへフォールバックして time.sleep の ValueError を防止。
- calc_score_weights: 全銘柄のスコア合計が 0 の場合は等金額配分へフォールバックしてゼロ除算を回避。
- position_sizing の aggregate スケーリングロジックは単元株（lot_size）単位での丸めと残余配分を行い、手数料/スリッページ見積り（cost_buffer）を考慮して投資上限を超えないように調整。
- process_priority / set_cpu_affinity は権限不足や未サポート環境で失敗しても警告ログでスキップするよう安全化。

### 注意点 / 既知の制限
- factor_research の一部関数が未完（ファイル末尾で途中）であり、完全実装は今後のリリースで対応予定。
- apply_sector_cap: price_map に価格が欠損（0.0）の場合にエクスポージャーが過少見積もられる可能性があり、将来的に価格フォールバック（前日終値等）の対応を検討中。
- .env は機密情報を含むため絶対にリポジトリにコミットしないでください（config_setup のヘッダに注意喚起あり）。
- run_monitoring は監視用 DB に常に "本番" sqlite_path を使用する設計（監視履歴を環境に依存せず一元管理する意図）。

---

今後の予定（想定）
- factor_research の完全実装（ファクター計算の SQL / 正規化ユーティリティ連携）。
- テストカバレッジの拡充と CI による自動検証。
- 単体/統合テスト用に KABUSYS_DISABLE_AUTO_ENV_LOAD を利用したテスト用設定の整備。
- position_sizing の銘柄別 lot_size 対応（stocks マスタの導入）。

（この CHANGELOG はコード内容からの推測に基づいて作成しています。実際の開発履歴やリリース注記はリポジトリの正式な履歴を参照してください。）