以下は提示されたコードベースの内容から推測して作成した CHANGELOG.md です。コードの実装内容に基づく推定のリリースノートであり、実際のコミット履歴とは完全に一致しない可能性があります。

Keep a Changelog 準拠フォーマット（日本語）

## [Unreleased]

（現時点では特に未リリースの変更は記載していません。次回リリース時にここへ記載してください。）

## [0.1.0] - 2026-04-25

初回リリース（コードベースから推定）。日本株自動売買システム KabuSys の基本機能と運用用ユーティリティ群を実装。

### 追加（Added）
- アプリケーション設定管理（kabusys.config）
  - プロジェクトルート検出による .env 自動読み込み（.env / .env.local、OS 環境変数優先）。
  - .env ファイルのパース機能を独自実装（export プレフィックス・シングル／ダブルクォート、バックスラッシュエスケープ、インラインコメント処理に対応）。
  - Settings クラスを提供し、各種環境変数の取得とバリデーションを行う（J-Quants / kabu API / DB パス / Paper Trading 設定 / 監視閾値 等）。
  - PAPER_FILL_MODE の検証（有効値: instant/partial/never/reject）。
  - KABUSYS_ENV / LOG_LEVEL の検証とユーティリティプロパティ（is_live / is_paper / is_dev）。

- 設定ウィザード CLI（kabusys.config_setup）
  - 対話式に .env を初期作成・更新するウィザードを提供。
  - 秘匿項目はマスク表示、デフォルト値・選択肢に対応。
  - .env の書き込みテンプレートを生成（Git にコミットしないよう注意書き付き）。

- 設定検証 CLI（kabusys.validate_config）
  - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在チェック。
  - config/*.yaml の存在確認と（PyYAML があれば）パース検証。
  - KABUSYS_ENV=live のための追加ガード（LINE 通知設定や KILL_FLAG_CLEAR_ON_START の警告）。
  - --strict を指定すると警告も失敗扱いで終了コード 1 を返す。

- 運用スクリプト
  - 実行エンジン起動スクリプト（kabusys.run_execution）
    - KABUSYS_ENV=paper_trading 時は paper_trading 用 SQLite（デフォルト: data/paper_trading.db）を使用して本番 DB と完全分離。
    - BrokerClientFactory を通じて Mock / 実ブローカーを切り替え。
    - ExecutionEngine の起動、スレッド管理、停止フラグ（data/stop_requested.flag）検知、PID ファイル管理（data/execution.pid）。
    - RiskManager の初期設定（max_position_pct 等のデフォルト値を設定）。
  - 監視（モニタ）起動スクリプト（kabusys.run_monitoring）
    - SystemMonitor をポーリングループで実行。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバック。
    - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path（data/monitoring.db）を使用する設計（運用上の意図に基づく）。

- ロギングユーティリティ（kabusys.utils.logging_setup）
  - ルートロガーに対して StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション、30 日分保持）を設定。
  - LOG_DIR / LOG_LEVEL の環境変数や引数による解決。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソール出力のみ継続。
  - ハンドラ二重設定防止（既存ハンドラをクリアしてから再設定）。

- プロセス優先度ユーティリティ（kabusys.utils.process_priority）
  - Windows と POSIX（Linux/Mac/FreeBSD）を吸収する set_process_priority(level) を提供（high/normal/low）。
  - set_cpu_affinity を提供（最初の N コアに固定）。
  - 権限不足や未対応 OS の場合は警告を出してスキップ。

- ポートフォリオ構築ライブラリ（kabusys.portfolio）
  - 銘柄候補選定（select_candidates）: スコア降順、タイブレークは signal_rank。
  - 重み計算: 等金額（calc_equal_weights）、スコア加重（calc_score_weights、全スコアが 0 の場合は等金額にフォールバック）。
  - セクター集中制限（apply_sector_cap）: 既存保有のセクター比率が閾値を超える場合の候補除外（unknown セクターは無視）。
  - レジーム乗数（calc_regime_multiplier）: bull/neutral/bear に対してそれぞれ 1.0/0.7/0.3。未知レジームは警告し 1.0 にフォールバック。
  - 目標株数計算（calc_position_sizes）:
    - allocation_method により risk_based / equal / score をサポート。
    - 単元株（lot_size）丸め、1 銘柄上限、aggregate cap（available_cash）を考慮したスケーリング処理を実装。
    - cost_buffer を用いた手数料・スリッページの保守的見積り。
    - スケールダウン後の残余キャッシュを用いて残差順に単位配分する処理を実装。

- Paper Trading 検証レポートツール（kabusys.tools.paper_verification_report）
  - Paper Trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）から集計してレポート出力。
  - 指標: 稼働率（uptime）、注文成功率（fill rate）、送信率（send rate）、P95 レイテンシ、リスク却下数、総ポーリング数など。
  - デフォルトの合格基準を設定（例: 稼働率 >= 99%、P95 <= 200 ms、など）および PASS/FAIL 判定。

- 研究用ファクター計算モジュール（kabusys.research.factor_research）
  - Momentum / Value / Volatility / Liquidity 等のファクターを計算する設計と初期実装（DuckDB を使用、prices_daily / raw_financials を参照）。
  - （ファイル末尾で関数実装が途中で切れているため、一部未完の実装を含む可能性あり）

### 変更（Changed）
- なし（初回リリースのため該当なし）

### 修正（Fixed）
- なし（初回リリースのため該当なし）

### 既知の注意点 / TODO（Notes）
- apply_sector_cap 内の価格欠損時（price が 0.0）の扱いについて TODO コメントあり。将来的に前日終値や取得原価でフォールバックすることが想定されている。
- factor_research モジュールはファイル末尾で実装が途切れている（コードスニペットが途中）ため、完全実装が必要。
- process_priority / set_cpu_affinity は権限に依存する操作のため、実行環境によっては AccessDenied で警告を出してスキップする挙動。
- ログディレクトリの作成に失敗した場合はファイル出力が無効化される（警告を標準エラーに出す）。
- monitoring は KABUSYS_ENV に依存せず本番 sqlite_path を使う設計になっているため、環境によっては意図した DB を参照していないと感じられる可能性あり（コード上明示的にそのように実装されている）。

### セキュリティ（Security）
- セキュリティ修正は今回の初回リリースには含まれていません。環境変数（API トークン・パスワード等）は .env に保存されることを想定しており、.env を絶対にリポジトリにコミットしないよう注意が明記されています。

## 未分類 / 補足
- 本 CHANGELOG は提示コードから推測して作成したもので、実際のコミットメッセージや変更履歴に基づくものではありません。必要であれば、実際の git 履歴（コミット）を参照して正確な CHANGELOG を生成してください。