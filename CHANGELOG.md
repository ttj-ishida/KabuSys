# Changelog

すべての変更は Keep a Changelog の形式に従い、日本語で記載しています。  
このファイルはプロジェクトの主要な変更・追加・修正点を要約したものです。

全項目は公開バージョン __0.1.0__ を前提にしています（src/kabusys/__init__.py の __version__ を参照）。

## [0.1.0] - 初回リリース
初期リリース。自動売買システム KabuSys のコア機能、運用ユーティリティ、設定ツール群、およびペーパートレード検証用ツールを提供します。

### 追加
- 起動スクリプト
  - run_execution.py
    - ExecutionEngine を起動するエントリポイントを提供。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 専用の SQLite（data/paper_trading.db、環境変数で上書き可）を使用することで本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立てと ExecutionEngine の起動/停止ロジックを実装。
    - 停止制御はプロジェクト直下の data/stop_requested.flag を監視して行う。
    - 実行中の PID を data/execution.pid に保持する仕組みに対応。

  - run_monitoring.py
    - SystemMonitor のポーリングループを実行するエントリポイントを提供。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値は警告を出してデフォルトにフォールバック。
    - 監視用 DB は環境に依らず本番 sqlite_path を使用して接続・初期化する実装になっている旨を明示。

- 設定管理
  - config.py
    - 環境変数 / .env ファイルの読み込みを担う Settings クラスを提供。
    - .env 自動ロード機能（プロジェクトルートの検出: .git または pyproject.toml を基準）を実装。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - .env の読み込みは OS 環境変数を保護（既存キーは上書きしない / .env.local は上書き可）する仕組み。
    - .env のパースは export プレフィクス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント等に対応。
    - アプリケーション設定プロパティを公開（J-Quants / kabu API / DB パス / PID / Kill flag 等）。
    - PAPER_FILL_MODE の検証（instant/partial/never/reject）や KABUSYS_ENV の検証（development/paper_trading/live）など入力チェックを追加。

  - config_setup.py
    - 対話式ウィザードで .env の初期作成・更新を支援する CLI を追加。
    - ウィザードは既存 .env 読み込み、秘密項目のマスク、選択肢提示、保存確認などを実装。
    - 保存時に .env ファイルのテンプレートを整形して出力。

  - validate_config.py
    - 起動前検証用の CLI を追加。必須環境変数の存在確認、KABUSYS_ENV / LOG_LEVEL の妥当性、DB パスの親ディレクトリチェック、config/*.yaml の存在・パース検証（PyYAML が存在する場合）を行う。
    - KABUSYS_ENV=live のときに追加の注意（LINE 設定や Kill Flag 設定）を出力するガードを実装。
    - --strict オプションで警告も失敗扱いにできる。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - シグナル選別（select_candidates: スコア降順、signal_rank によるタイブレーク）を実装。
    - 等金額配分 calc_equal_weights と スコア比率配分 calc_score_weights（全銘柄スコアが 0 の場合は等配分へフォールバック）を実装。

  - portfolio/risk_adjustment.py
    - セクター集中上限チェック apply_sector_cap を実装（当日売却予定銘柄を除外可、"unknown" セクターは除外対象外）。
    - 市場レジームに応じた投下資金乗数 calc_regime_multiplier（bull/neutral/bear のマッピング）を実装。未知のレジームは 1.0 でフォールバック。

  - portfolio/position_sizing.py
    - 株数決定ロジック calc_position_sizes を実装（allocation_method: risk_based / equal / score）。
    - 単元株（lot_size）で丸め、1銘柄上限・aggregate cap のスケーリング、コストバッファを考慮したスケールダウンと残余配分ロジック等を備える。
    - price が欠損する銘柄はスキップする挙動、細かなログ出力あり。

  - portfolio/__init__.py
    - 上記関数群をパッケージ API としてエクスポート。

- ユーティリティ
  - utils/logging_setup.py
    - 統一的なロギング設定ユーティリティを追加。
    - stdout 出力（StreamHandler）と日次ローテートされたファイル出力（TimedRotatingFileHandler、30 日分保持）をルートロガーに設定する。
    - LOG_LEVEL / LOG_DIR の解決順、既存ハンドラのクリーンアップ、ログディレクトリ作成失敗時のフォールバックなどを実装。

  - utils/process_priority.py
    - Windows/Linux/macOS の差分を吸収するプロセス優先度設定ユーティリティを追加（set_process_priority）。
    - CPU affinity を固定する set_cpu_affinity を提供。
    - 権限不足や未サポート環境では警告を出して安全にスキップする設計。

- ツール
  - tools/paper_verification_report.py
    - ペーパートレード用 SQLite DB を解析して検証レポートを生成する CLI を追加。
    - 指標: 稼働率（uptime）、注文成功率（fill rate）、送信率（send rate）、API レイテンシ（平均 / 最大 / P95）など。
    - デフォルト閾値（稼働率 99% etc）に基づく PASS/FAIL 判定を出力。
    - --from / --to / --db オプションに対応。P95 は簡易アルゴリズムで計算。

- リサーチ（部分実装）
  - research/factor_research.py
    - DuckDB を用いたファクター計算モジュールの骨格を追加（モメンタム / MA / ATR / Liquidity 等を計画）。
    - 日数定数や設計方針のドキュメントコメントを含む（実装は一部で未完）。

- パッケージメタ
  - src/kabusys/__init__.py に __version__ = "0.1.0" を設定。

### 変更
- DB 接続の挙動
  - run_monitoring: 監視機能は環境変数 KABUSYS_ENV に関わらず監視用（本番）sqlite_path を使う旨を明示（安全のための設計判断）。
  - run_execution: paper_trading 環境時は paper_sqlite_path を利用することで本番データと分離。

- .env 自動読み込みの挙動
  - プロジェクトルートが検出できない場合は自動ロードをスキップする（配布パッケージでの安全性向上）。
  - .env の読み込み順序は OS 環境変数 > .env.local > .env（.env.local は override）。

- ロギング
  - ログハンドラの二重追加を防ぐため、既存ハンドラを一旦 flush/close のうえ削除してから再設定するように変更。

### 修正
- 環境変数パースの堅牢化
  - export プレフィクス、クォート内のバックスラッシュエスケープ、インラインコメントの扱いなどに対応し、不正な .env 行を無視するように改善。

- 設定検証
  - validate_config において PyYAML 未インストール時は YAML 検証をスキップし警告を出すように修正（import 時の例外処理）。

- 実行制御
  - run_execution と run_monitoring の両方で data/stop_requested.flag を検知して安全に停止する仕組みを統一的に実装。

### 注意点 / 既知の問題
- research/factor_research.py は実装が途中で切れている箇所があり、完全なファクター計算ロジックは未完成です。
- position_sizing や risk_adjustment の一部ロジックは価格データが欠損した場合に挙動が保守的（スキップやフォールバック）になる設計だが、将来的に価格フォールバック（前日終値や取得原価など）を導入する余地がある旨の TODO コメントあり。
- run_monitoring が常に本番 sqlite_path を使用する点は意図的な設計（監視は本番データを参照）だが、運用時には環境設定を再確認してください。

### ドキュメント
- 各モジュールに実行方法や設定項目、設計方針の詳細コメントを追加（README 相当の説明がソース内ドキュメントとして含まれています）。  
  - 例: run_execution/run_monitoring の冒頭 docstring、config_setup のウィザード説明、paper_verification_report の使用方法コメント等。

---

今後のリリースで予定される改善案（例）
- research モジュールの完全実装（ファクター計算の SQL / 結果正規化）
- ブローカークライアントのテスト用モック類とより詳細なペーパートレードシミュレーション
- 単体テスト・統合テストの追加と CI 設定
- ログの構造化（JSON 出力オプション）やメトリクス収集の強化

もし特定ファイルごとの差分（追加行・修正行など）や、CHANGELOG に追記したい細かな文言があれば教えてください。それに合わせて文面を調整します。