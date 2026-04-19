# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠しています。  
現在のバージョンはパッケージメタデータ (src/kabusys/__init__.py) に従い 0.1.0 です。

リンク: https://keepachangelog.com/（英語）

## [Unreleased]

（なし）

## [0.1.0] - 2026-04-19

最初の公開リリース。自動売買システム「KabuSys」の基本コンポーネント群を実装しています。

### 追加 (Added)
- パッケージ基盤
  - パッケージ初期化とバージョン情報を追加（src/kabusys/__init__.py, version 0.1.0）。
  - 公開 API（ポートフォリオモジュールの関数群）をまとめてエクスポート（src/kabusys/portfolio/__init__.py）。

- 設定管理
  - 環境変数および .env 自動ロード機能を実装（src/kabusys/config.py）。
    - プロジェクトルート (.git または pyproject.toml) を基に自動で .env/.env.local を読み込む。
    - クォートやエスケープ、インラインコメントのある行に対応するパーサ実装。
    - 各種設定プロパティ（J-Quants / kabu API / DB パス / Paper Trading 用設定 / 監視閾値 等）を公開。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
  - 設定ウィザード CLI を追加（src/kabusys/config_setup.py）。
    - 対話式で .env を作成・更新するウィザード。シークレット項目はマスク表示。
    - デフォルト値や選択肢、保存確認を実装。

- 設定検証
  - 起動前の設定検証 CLI を追加（src/kabusys/validate_config.py）。
    - 必須環境変数や KABUSYS_ENV の妥当性、YAML 設定ファイルの存在とパース検証（PyYAML が存在する場合）などをチェック。
    - --strict フラグで警告を FAIL 扱いにできる。

- 起動スクリプト
  - 監視ループ起動スクリプトを追加（src/kabusys/run_monitoring.py）。
    - SystemMonitor を用いたポーリングループ、MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止フラグファイルでループを終了。監視 DB は常に本番 sqlite_path を使用。
  - 実行エンジン起動スクリプトを追加（src/kabusys/run_execution.py）。
    - KABUSYS_ENV=paper_trading のときは MockBrokerClient を使用し、本番 DB と分離した data/paper_trading.db を利用。
    - ExecutionEngine を別スレッドで実行し、停止フラグ検知で安全停止。PID ファイル管理。

- 実行・監視基盤
  - ロギング初期化ユーティリティを追加（src/kabusys/utils/logging_setup.py）。
    - コンソール (stdout) と日次ローテートファイルハンドラ (TimedRotatingFileHandler) をルートロガーに設定。
    - LOG_DIR / LOG_LEVEL の解決順を実装。ログディレクトリ作成失敗時はファイル出力をスキップして継続。
  - プロセス優先度と CPU affinity 設定ユーティリティを追加（src/kabusys/utils/process_priority.py）。
    - Windows / POSIX（Linux/macOS/FreeBSD）差分を吸収して優先度設定を行う。
    - set_cpu_affinity により最初の N コアへピンニング可能。権限不足時は警告のみ。

- ポートフォリオ構築（純粋関数群）
  - 銘柄選定・重み計算（src/kabusys/portfolio/portfolio_builder.py）
    - select_candidates: スコア降順で上位 N を選択（同点は signal_rank でタイブレーク）。
    - calc_equal_weights, calc_score_weights: 等金額・スコア重み配分。スコア合計が 0 の場合は等分へフォールバック。
  - セクター集中制限とレジーム乗数（src/kabusys/portfolio/risk_adjustment.py）
    - apply_sector_cap: セクター別エクスポージャーを計算し上限を超えるセクターの新規候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: market regime（bull/neutral/bear）に応じた投下資金乗数を提供。未知のレジームはフォールバックで 1.0。
  - ポジションサイジング（src/kabusys/portfolio/position_sizing.py）
    - calc_position_sizes: risk_based / equal / score の割当方式をサポート。単元（lot_size）丸め、aggregate cap によるスケールダウン、cost_buffer を考慮した保守的見積りを実装。
    - スケールダウン後の端数処理（lot 単位で残差が大きい順に追加配分）を実装。

- 解析・レポート
  - Paper Trading 検証レポート生成スクリプトを追加（src/kabusys/tools/paper_verification_report.py）。
    - システム稼働率、注文成功率、送信率、レイテンシ（avg/max/P95）等を計算して判定（PASS/FAIL）。
    - P95 計算ユーティリティ、期間フィルタ、閾値定義（稼働率 99%、成功率 90% 等）。
    - DB パスは引数 --db / 環境変数 PAPER_TRADING_SQLITE_PATH / デフォルト順で解決。

- リサーチ基盤（基礎実装）
  - ファクター計算モジュールを追加（src/kabusys/research/factor_research.py）。
    - Momentum / Value / Volatility / Liquidity 等のファクターを DuckDB 接続を用いて計算する方針。関数 calc_momentum 等の骨組みを実装（未完の箇所あり）。

### 変更 (Changed)
- 初回リリースのため変更履歴はなし（新規追加のみ）。

### 修正 (Fixed)
- 初回リリースのため修正履歴はなし。

### ドキュメント / コメント
- 各モジュールに詳細な docstring と使用例、設計上の注意点・ TODO を記載。
  - 例: apply_sector_cap 内の price 欠損に伴う将来拡張の注記、position_sizing の lot_size に関する将来的拡張案、logging_setup の stdout 利用理由 等。

### 既知の制約・注意点 (Notes / Known issues)
- Settings により一部環境変数の値は厳密に検証される（例: KABUSYS_ENV の有効値チェック、PAPER_FILL_MODE の候補検証）。設定ミスは起動時に例外となるため .env の正確な準備を推奨。
- apply_sector_cap は price_map に価格がない場合エクスポージャーを過小に見積もる可能性がある旨をコメントで明示（将来的にフォールバック価格を導入予定）。
- position_sizing の lot_size は全銘柄共通扱い。銘柄別単元管理は将来の拡張ポイント。
- research/factor_research.py は一部実装が途中で切れている（calc_momentum の後続など）。リサーチ部分は今後追加実装・テストが必要。
- ログディレクトリ作成やプロセス優先度／CPU affinity の設定は権限不足やプラットフォーム差分で失敗する可能性があり、その場合は警告を出して処理を継続します。

### セキュリティ (Security)
- 機密情報（J-Quants トークン、kabu API パスワード、LINE トークン）は .env に保存する設計のため、.env をリポジトリにコミットしないことを明示（config_setup のヘッダにも記載）。

---

上記は現在のソースコードとコメントから推測して作成した変更履歴です。リリース日付は本ファイル作成時点（2026-04-19）を採用しています。将来の変更や修正はこのファイルの Unreleased 欄に追記してください。