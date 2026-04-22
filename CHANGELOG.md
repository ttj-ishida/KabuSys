# CHANGELOG

すべての変更は Keep a Changelog の形式に従います。  
このファイルは、リポジトリ内のソースコードの内容から推測して作成した変更履歴です。

## [0.1.0] - 2026-04-22

### 追加 (Added)
- 全体
  - 初回公開相当の機能群を追加。自動売買システム「KabuSys」のコアユーティリティ、起動スクリプト、ポートフォリオ構築ロジック、検証ツール等を含む。
  - パッケージメタ情報にバージョン `0.1.0` を設定。

- 起動/サービス
  - run_monitoring スクリプトを追加。SystemMonitor のポーリングループ起動、停止フラグ検出、MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
  - run_execution スクリプトを追加。ExecutionEngine を起動・監視し、Paper Trading モード時は専用の SQLite（data/paper_trading.db）を使用して本番 DB と完全分離。
  - PID / stop フラグ管理に対応（data/*.pid / stop_requested.flag ファイルを使用）。

- 設定管理
  - Settings クラスを追加し、環境変数からアプリ設定を一元取得。
  - 自動 .env ロード機能を追加（プロジェクトルート探索により .env / .env.local を読み込み、OS 環境変数は保護する）。
  - 新しい設定プロパティを追加: PAPER_FILL_MODE（Paper Trading の成行/部分約定挙動）、PAPER_TRADING_SQLITE_PATH、PID/KILL フラグ関連設定、CPU/MEM/DISK 閾値、環境種別判定（is_live/is_paper/is_dev）など。

- 設定補助ツール
  - config_setup CLI を追加。対話式ウィザードで .env を作成・更新する機能を提供（入力補助、シークレットマスキング、保存時確認）。
  - validate_config CLI を追加。環境変数・config/*.yaml の存在・簡易検証を実行。--strict オプションで警告を失敗扱いにできる。PyYAML の有無を考慮したパース検出。

- ロギング / プロセス管理
  - 統一ロギングセットアップ関数 setup_logging を追加。stdout 出力（StreamHandler）と日次ローテーションによるファイル出力（TimedRotatingFileHandler）をルートロガーに構成。ログディレクトリは環境変数で上書き可能。
  - set_process_priority / set_cpu_affinity を提供する process_priority ユーティリティを追加。Windows/Linux/macOS の差分を吸収してプロセス優先度や CPU affinity を設定可能（権限不足時は警告でスキップ）。

- ポートフォリオ構築
  - portfolio モジュールを追加:
    - portfolio_builder: 候補選定（select_candidates）、等配分/スコア加重（calc_equal_weights / calc_score_weights）。
    - risk_adjustment: セクター集中排除（apply_sector_cap）、市場レジームに応じた投下資金乗数（calc_regime_multiplier）。
    - position_sizing: 各銘柄の発注株数算出（calc_position_sizes）。risk_based / equal / score の配分方式をサポートし、単元株丸め、個別上限、aggregate スケーリング（available_cash に合わせたスケールダウン）を実装。

- 検証レポート
  - tools/paper_verification_report を追加。Paper Trading の SQLite ログから稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）等を集計して人間向けレポートを出力。閾値判定で PASS/FAIL を示す。

- リサーチ
  - research/factor_research のファイルを追加（ファクター計算の設計と一部定数を実装）。DuckDB 経由で価格・財務テーブルを参照してファクターを計算する方針。

### 変更 (Changed)
- DB 接続方針
  - 監視（monitoring）は KABUSYS_ENV にかかわらず production 用 sqlite_path を使用する旨を明示。paper_trading モードでは execution が別 DB を選択する設計に分離。

- .env 読み込みロジック
  - .env のパース機能を強化（export キーワード対応、シングル/ダブルクォート内のバックスラッシュエスケープ処理、インラインコメントのハンドリング等）。プロジェクトルート判定は .git / pyproject.toml の存在で行うためパッケージ配布後も安定動作。

- ログ出力
  - stdout を標準のログストリームに使用（stderr ではなく stdout）し、ジョブスケジューラからのリダイレクトを考慮。

### 修正 (Fixed)
- 設定検証の堅牢性
  - validate_config で PyYAML 未導入時は YAML 検証をスキップして警告するようにし、パース失敗時はエラーとして報告する挙動を実装。
  - .env 読み込み時にファイル読み込み失敗が発生した場合に警告を出して処理継続するよう保護。

- 実行時安定化
  - run_monitoring のポーリング間隔を環境変数（MONITOR_POLL_INTERVAL）で上書き可能にし、不正な値（0 以下や非数）の場合にデフォルトへフォールバックして例外発生を防止。
  - run_execution の起動ループで stop フラグ検出時にエンジンを安全に停止する処理を追加。

### 注意点 (Notes)
- Paper Trading（KABUSYS_ENV=paper_trading）は production DB と完全に分離されるように設計されています。Paper 用 DB のパスは PAPER_TRADING_SQLITE_PATH（または Settings.paper_sqlite_path）で設定できます。
- process_priority や CPU affinity の設定は OS/権限に依存します。設定に失敗した場合は警告ロギングが出力され、処理は継続されます。
- portfolio / position_sizing のアルゴリズムは現時点で単元（lot_size）を全銘柄共通で扱う仕様です。将来的に銘柄別単元対応の拡張を想定しています（TODO コメントあり）。

### セキュリティ (Security)
- .env ファイルは機密情報を含むため、生成した .env を Git にコミットしない旨の注記を config_setup に明示。

---

If you expect additional historical releases, or want Unreleased / future notes added,教えてください。