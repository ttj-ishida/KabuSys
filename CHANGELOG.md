CHANGELOG
=========

すべての重要な変更点を記録します。本ファイルは "Keep a Changelog" の形式に準拠しています。  
以下の記載はリポジトリ内のコードからの推測に基づいて作成しています。

## [0.1.0] - 2026-04-23
初回リリース（コードベースから推測）

### 追加 (Added)
- 基本パッケージ情報を追加
  - kabusys パッケージ初期バージョンを定義（__version__ = "0.1.0"）。
- 実行スクリプト
  - run_execution.py: ExecutionEngine を起動する CLI スクリプトを追加。
    - KABUSYS_ENV に応じて paper_trading 用の専用 SQLite（data/paper_trading.db）を使用する分離機能を実装。
    - BrokerClientFactory によるブローカークライアント抽象化を導入。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み立て、ExecutionEngine をスレッドで実行する制御ループを実装。
    - 停止フラグ（data/stop_requested.flag）および PID ファイル処理を導入。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番 sqlite_path を利用する旨を明示。
    - 停止フラグ検知での安全停止処理を実装。
- 設定管理
  - config.py: 環境変数 / .env 自動ロード機構を実装。
    - プロジェクトルートを .git または pyproject.toml で検索し、.env/.env.local を自動ロード（KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化あり）。
    - .env パースロジックは export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメント等に対応する堅牢な実装。
    - 各種設定プロパティ（DB パス、API トークン、環境種別、紙トレード挙動等）を型付きプロパティで提供。PAPER_FILL_MODE の検証を実施。
  - config_setup.py: 対話式 .env 作成・更新ウィザードを追加。
    - デフォルト値、選択肢表示、シークレット入力のマスク、保存前確認等をサポート。
- 設定検証ツール
  - validate_config.py: 起動前チェック用 CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ確認、config/*.yaml の存在と（PyYAML がある場合の）パース検証、本番環境向けの注意喚起等を実装。
    - --strict オプションで警告をエラー扱いにできる。
- ロギング・ユーティリティ
  - utils/logging_setup.py: 統一ログ設定ユーティリティを追加。
    - stdout への StreamHandler と日次ローテーションの TimedRotatingFileHandler（30日保持）をルートロガーに設定。
    - LOG_DIR 環境変数や引数でログディレクトリを指定可能。ディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソール出力にフォールバック。
- プロセス制御ユーティリティ
  - utils/process_priority.py: プロセス優先度および CPU affinity 設定ユーティリティを追加。
    - Windows / POSIX の差分を吸収して優先度を設定（"high"/"normal"/"low"）。
    - CPU affinity を先頭 N コアに固定する set_cpu_affinity を提供。
    - 権限不足や未対応 OS の場合は警告を出して安全にスキップ。
- ポートフォリオ構築ライブラリ（ポートフォリオロジック）
  - portfolio/portfolio_builder.py: 候補選定と重み計算（等金額・スコア重み）を追加。
    - スコアがすべて 0 の場合は等金額にフォールバック。
  - portfolio/risk_adjustment.py: セクター集中制限（apply_sector_cap）とレジーム乗数（calc_regime_multiplier）を追加。
    - セクター上限を超える場合の候補除外ロジック、レジームに基づく投下資金乗数を実装（bull/neutral/bear を想定）。
  - portfolio/position_sizing.py: 株数決定ロジックを追加。
    - risk_based / equal / score の割当方式をサポート。
    - 単元株（lot_size）丸め、1銘柄上限・aggregate cap（available_cash）でのスケーリング、手数料・スリッページ用 cost_buffer を考慮。
    - 不足データ（価格未取得等）は安全にスキップ。
- Paper Trading 検証ツール
  - tools/paper_verification_report.py: Paper Trading 用の検証レポート生成スクリプトを追加。
    - 稼働率、注文成功率、送信率、レイテンシ（平均・最大・P95）等を計算し、PASS/FAIL 判定を出力。
    - デフォルト DB パスは data/paper_trading.db。コマンドラインで期間・DB を指定可能。
    - 閾値（稼働率 99% 等）を定義。
- 研究用ファクターモジュール（未完を含む）
  - research/factor_research.py: モメンタム等ファクター計算モジュールを追加（DuckDB 接続で prices_daily / raw_financials を参照する設計）。（ファイル末尾で実装途中の箇所あり）

### 変更 (Changed)
- なし（初回リリース）

### 修正 (Fixed)
- 環境変数の無効値に対する安全処理を導入
  - MONITOR_POLL_INTERVAL の不正値は警告してデフォルトにフォールバック（run_monitoring.py）。
  - PAPER_FILL_MODE の不正値は ValueError を送出して早期検出（config.py）。
  - ログディレクトリ作成失敗時にファイルハンドラ生成をスキップするフォールバックを実装（logging_setup.py）。
  - process_priority や cpu_affinity 実行時の権限不足を例外で落とさず警告ログにとどめる（process_priority.py）。

### セキュリティ (Security)
- 機密情報の取扱いに関する注意
  - config_setup の .env ヘッダに「.env は絶対に Git にコミットしないこと」を明記。
  - 対話式ウィザードでシークレット項目はマスク表示。

### 既知の制約 / TODO（実装から推測）
- research/factor_research.py はモメンタム計算の実装が途中で終わっており、追加実装が必要。
- position_sizing の lot_size は全銘柄共通。将来的には銘柄別単元情報を導入する予定（TODO コメントあり）。
- apply_sector_cap は price_map が欠損（0.0）だとエクスポージャーが低めに評価される問題がある旨の TODO コメントあり（フォールバック価格の検討を示唆）。
- run_monitoring はMonitoring用 DBを環境にかかわらず本番 sqlite_path としているため、テスト環境での分離を行いたい場合は注意が必要。

---

注: 上記はリポジトリ内のソースコードを読み取り推測した CHANGELOG です。必要に応じて実際のコミット履歴やリリースノートに合わせて調整してください。