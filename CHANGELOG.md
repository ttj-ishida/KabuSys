# CHANGELOG

すべての重要な変更を Keep a Changelog（https://keepachangelog.com/ja/1.0.0/）に準拠して記載します。

## [Unreleased]

- 特になし（現状のスナップショットは 0.1.0 リリース相当の機能群を含みます）。

## [0.1.0] - 2026-04-20

初期リリース相当。日本株自動売買システム KabuSys の基本機能をまとめて導入しました。主な追加点は以下のとおりです。

### 追加（Added）
- 全体
  - パッケージ初期版を追加。バージョンは `__version__ = "0.1.0"`。
  - モジュール構成を整備（execution / monitoring / portfolio / research / utils / tools など）。

- 実行系（Execution）
  - run_execution 起動スクリプトを追加。
    - プロセス優先度を起動時に設定（`set_process_priority("high")`）。
    - 環境に応じて本番用またはペーパートレード用（`paper_trading`）の SQLite を選択して接続。
    - Broker クライアントのファクトリ（`BrokerClientFactory`）を利用してブローカー接続を抽象化。
    - ExecutionEngine を別スレッドで起動し、ファイルベースの停止フラグで安全に停止可能。
    - ペーパートレード時は本番 DB と分離して `data/paper_trading.db` を利用する挙動をサポート（環境変数で上書き可）。

- 監視（Monitoring）
  - run_monitoring 起動スクリプトを追加。
    - `SystemMonitor` を使ったポーリングループを実装。
    - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL` で上書き可能（デフォルト 60 秒）。
    - 監視は環境に関わらず本番の sqlite_path を使用して監視テーブルを管理。
    - 停止フラグファイルによりループを終了する仕組みを実装。

- 設定管理（Config）
  - `kabusys.config.Settings` による環境変数ラッパーを追加。
    - `.env` / `.env.local` の自動読み込み（プロジェクトルート検出）を実装。
    - 自動ロードを無効化する `KABUSYS_DISABLE_AUTO_ENV_LOAD` をサポート。
    - `.env` パースロジックを強化（export プレフィックス、クォート、エスケープ、インラインコメントの取り扱い等に対応）。
    - 各種設定プロパティ（DB パス、PID ファイルパス、閾値設定、paper_trading 用設定など）を提供。
    - `PAPER_FILL_MODE` のバリデーション、有効値チェックを実装。
    - 環境種類（development / paper_trading / live）とログレベルバリデーションを実装。

- 設定ユーティリティ / CLI
  - 対話式ウィザード `config_setup.py` を追加。
    - `.env` の初期作成・更新を対話的に支援（シークレット入力・選択肢・デフォルト提示）。
    - 保存前に入力内容の確認を行う。
  - 設定検証 CLI `validate_config.py` を追加。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の検証、DB パスの親ディレクトリチェック、config/*.yaml の存在とパース検証（PyYAML が存在する場合）などを実施。
    - `--strict` オプションで警告を失敗扱いにできる。

- ポートフォリオ構築（Portfolio）
  - 銘柄選定・重み計算（`portfolio_builder.py`）
    - 信号のソート / 上位 N 抽出（`select_candidates`）。
    - 等金額配分（`calc_equal_weights`）。
    - スコア加重配分（`calc_score_weights`） — 全スコアが 0 の場合は等配分へフォールバック。
  - リスク調整（`risk_adjustment.py`）
    - セクター集中制限を適用して候補を除外する `apply_sector_cap` を実装（`unknown` セクターは除外対象外）。
    - 市場レジームに応じた投下資金乗数を返す `calc_regime_multiplier`（`bull`/`neutral`/`bear` をサポート、未知レジームはフォールバック）。
  - 銘柄ごとの株数決定（`position_sizing.py`）
    - `risk_based` / `equal` / `score` の配分方式を実装。
    - 単元（lot_size）丸め、1銘柄上限（max_position_pct）、総投下上限（max_utilization）、コストバッファ（cost_buffer）を考慮したスケーリングロジックを導入。
    - 利用可能現金を超える場合のスケールダウンと残差処理（lot 単位での再配分）を実装。

- 研究（Research）
  - ファクター計算モジュール `research/factor_research.py` を追加（モメンタム・MA200・ATR・流動性等の計算を想定）。
    - DuckDB 接続を受け取り prices_daily / raw_financials を参照して計算する設計。
    - （注）ファイル末尾で実装途中の箇所が存在する（スナップショットのため後続実装を予定）。

- ツール（Tools）
  - ペーパートレード検証レポート生成ツール `tools/paper_verification_report.py` を追加。
    - SQLite（ペーパー用）を読み取り、稼働率、注文成功率、送信率、レイテンシ（平均・最大・P95）などを算出。
    - 閾値をもとに PASS/FAIL を判定するレポートを標準出力に出力。
    - コマンドライン引数で集計期間と DB パスを指定可能。

- ユーティリティ（Utils）
  - ロギングセットアップ `utils/logging_setup.py`
    - すべての起動スクリプトで共通のログ設定を提供。
    - stdout (StreamHandler) へ出力し、日次ローテートするファイルハンドラ（TimedRotatingFileHandler）を組み合わせて利用。
    - ログディレクトリ自動作成、ハンドラの二重登録防止、環境変数によるログレベル・ログディレクトリの指定に対応。
  - プロセス優先度・CPU affinity ユーティリティ `utils/process_priority.py`
    - Windows / POSIX（Linux/Mac/FreeBSD）差分を吸収して優先度（high/normal/low）を設定。
    - CPU affinity を設定する API を提供。
    - psutil によるアクセス権限失敗時は警告を出してスキップする堅牢性を実装。

### 変更（Changed）
- .env の自動ロード挙動
  - OS 環境変数を優先し、`.env` を上書きしないデフォルト（`.env.local` は上書き可）となる設定ロジックを導入。

### 修正（Fixed）
- 環境変数パースの堅牢化
  - `_parse_env_line` でクォート内のバックスラッシュエスケープと対応する閉じクォート探索、コメント処理を改善。
- 監視ポーリング間隔のバリデーション
  - `MONITOR_POLL_INTERVAL` に 0 以下や不正値が指定された場合、デフォルト値（60 秒）にフォールバックしてエラーを回避。

### 注意点 / 既知の制限（Known issues）
- `research/factor_research.py` の一部で実装途上の箇所が見られます（スナップショットによる未完了）。
- `apply_sector_cap` は sector_map に存在しない銘柄を "unknown" 扱いとして保護し、セクター上限の適用対象外としています。価格データが欠損（0.0）だと既存エクスポージャーが過少評価される可能性があるため、将来的にフォールバック価格の導入を検討する旨の TODO を残しています。
- .env ファイルはセキュリティ上コミットしないでください（config_setup のヘッダにも注意喚起あり）。

### セキュリティ（Security）
- .env ファイルに API トークンやパスワードを保存する設計のため、リポジトリに `.env` をコミットしない旨を明記しています。

---

今後の予定（例）
- factor_research の完了（DuckDB クエリ最適化、テスト追加）
- ExecutionEngine / Broker クライアント周りの堅牢化（再接続戦略、詳細な監視イベントの拡充）
- 単体テスト・CI の導入と自動静的解析の追加

（参考: この CHANGELOG は現行ソースコードの内容から機能・変更点を推測して作成しています。）