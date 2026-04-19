# Changelog

すべての変更は Keep a Changelog の形式に従って記載しています。  
（コードベースから推測して作成した初期リリース相当の一覧です）

全般的な注記
- 本ドキュメントは提供されたソースコードから機能・挙動を推測して作成した CHANGELOG です。
- 実際のコミット履歴やリリースノートが存在する場合はそちらを優先してください。

## [Unreleased]

## [0.1.0] - 2026-04-19
初回リリース（推測）。主要機能の実装と CLI / ユーティリティ群を追加。

### 追加 (Added)
- アプリケーション基盤
  - パッケージのバージョンを `__version__ = "0.1.0"` として設定。
  - パッケージ公開用の top-level モジュールエクスポートを追加（data, strategy, execution, monitoring）。

- 環境設定 / 設定管理
  - Settings クラス（kabusys.config）を実装：
    - 環境変数から各種設定を取得（J-Quants / kabu API / LINE / DB パス / 監視閾値 等）。
    - KABUSYS_ENV, LOG_LEVEL 等のバリデーションを実装。
    - paper_trading 用専用 DB パス、paper_fill_mode の検証ロジック等を実装。
  - .env 自動読み込み機構を実装：
    - プロジェクトルートを .git または pyproject.toml を基準に自動検出。
    - `.env` → `.env.local` の順でロード。OS 環境変数は保護（上書き禁止）。
    - `KABUSYS_DISABLE_AUTO_ENV_LOAD` で自動ロードを無効化可能。
  - .env パースの堅牢化（引用符・エスケープ・コメント処理に対応）。

- 設定関連 CLI
  - 環境設定ウィザード（kabusys.config_setup）を追加：
    - 対話式で .env を生成・更新するウィザード。
    - 必須項目のマスク表示、選択肢・デフォルト・説明付き入力。
    - .env ファイル書き出しロジックを実装（テンプレート付き）。
  - 設定検証ツール（kabusys.validate_config）を追加：
    - 必須環境変数・KABUSYS_ENV・LOG_LEVEL・DB パス・config/*.yaml の存在とパース（PyYAML があればパース検証）を行う。
    - `--strict` モード: 警告も失敗（exit 1）として扱う。

- 実行 / 監視用スクリプト
  - ExecutionEngine 起動スクリプト（kabusys.run_execution）を追加：
    - 起動時にプロセス優先度を "high" に設定。
    - `KABUSYS_ENV=paper_trading` の場合は paper_trading 用 SQLite を使用して本番 DB と分離。
    - BrokerClientFactory を利用してブローカークライアントを生成。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み立て、ExecutionEngine をスレッドで起動。
    - 停止フラグ（data/stop_requested.flag）監視と安全停止ハンドリング。
  - Monitoring 起動スクリプト（kabusys.run_monitoring）を追加：
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番 sqlite_path を使用する設計。
    - 停止フラグ検知でループを終了。check_once() の例外はログに残して次サイクルへ継続。

- ログ・プロセスユーティリティ
  - ロギング設定ユーティリティ（kabusys.utils.logging_setup）を追加：
    - stdout への StreamHandler（標準出力）と日次ローテートファイルハンドラ（TimedRotatingFileHandler）をルートロガーに設定。
    - ログディレクトリ作成に失敗した場合はファイルハンドラをスキップしてコンソールのみで継続。
    - ログレベル解決順（引数 → 環境変数 → デフォルト）。
  - プロセス優先度 / CPU affinity ユーティリティ（kabusys.utils.process_priority）を追加：
    - Windows / POSIX（Linux, Darwin, FreeBSD）に対応した優先度設定を実装（psutil 利用）。
    - set_process_priority(level) と set_cpu_affinity(cpu_count) を提供。
    - 権限不足や未対応 OS の場合は警告ログを出してスキップ。

- ポートフォリオ構築（純粋関数群）
  - 銘柄選定・重み計算（kabusys.portfolio.portfolio_builder）を追加：
    - select_candidates（スコア順で上位 N 選出）
    - calc_equal_weights（等金額配分）
    - calc_score_weights（スコア加重配分、全スコアが 0 の場合は等配分にフォールバックして警告）
  - セクター制限・レジーム乗数（kabusys.portfolio.risk_adjustment）を追加：
    - apply_sector_cap：既存保有のセクター比率が閾値を超える場合、同セクターの新規候補を除外（"unknown" セクターは制限を適用しない）。
    - calc_regime_multiplier：regime ("bull"/"neutral"/"bear") に応じた投下資金乗数（フォールバックと警告あり）。
  - 株数決定・リスク制限・単元丸め（kabusys.portfolio.position_sizing）を追加：
    - calc_position_sizes：allocation_method ("risk_based","equal","score") に対応。
    - risk_based：リスク許容率・ストップロスを基に算出。
    - 等配分/スコア配分：重みを基に各銘柄のターゲット株数を算出。
    - lot_size（単元）での丸め、ポートフォリオ総投下額が利用可能現金を超える場合のスケーリング（余剰分の按分ロジック）を実装。
    - cost_buffer により手数料・スリッページ見積りを考慮。

- リサーチ / ファクター計算
  - ファクター計算モジュール（kabusys.research.factor_research）を追加（モメンタム / MA / ATR / ボラティリティ / 流動性 等の計算方針とヘルパーを実装）。
  - DuckDB 接続を受け取り prices_daily / raw_financials テーブルから計算する設計。
  - P95 計算ユーティリティ / 各種窓長定義を実装。

- ツール
  - Paper Trading 検証レポート生成スクリプト（kabusys.tools.paper_verification_report）を追加：
    - paper_trading 用 SQLite（環境変数または --db）から指標（稼働率・注文成功率・送信率・P95 レイテンシ等）を集計してレポートを出力。
    - 合格基準（稼働率 >=99%、成立率 >=90%、送信率 >=95%、P95 レイテンシ <=200ms）を設定して PASS/FAIL を判定。
    - 日付フィルタ（--from / --to）対応。

### 変更 (Changed)
- （初回リリースのため該当なし）

### 修正 (Fixed)
- （初回リリースのため該当なし）

### 注意・既知の問題 (Known issues)
- factor_research.py の実装が途中で切れている箇所が確認される（ソースの末尾が途中で終端）。このため一部ファクター計算ロジックは未完の可能性がある。
- run_monitoring/run_execution はそれぞれ monitoring_db / SystemMonitor / ExecutionEngine 等の別モジュールに依存しており、これらの実装（ソース未提示）により挙動が変わる可能性がある。
- process_priority や CPU affinity の設定は権限不足やプラットフォーム差分によりスキップされることがある（警告ログで通知）。
- .env パース・ロードは多くのエッジケースを考慮しているが、特殊なエスケープや極端な入力に対しての追加テストが必要。

### 将来的な改善案（コード内 TODO より抜粋）
- price が欠損（0.0）の場合のフォールバック価格処理（apply_sector_cap の TODO）。
- 銘柄ごとの lot_size（単元）の導入。将来的には銘柄マスタを参照する設計に拡張予定（position_sizing のコメント）。
- factor_research の未完了部分の実装完了。

---

以上が、提供されたコードベースから推測して作成した CHANGELOG.md です。必要であれば、実際のコミット単位や日付を反映したバージョン別の詳細な変更履歴を作成しますので、追加の情報（例えばコミットログやリリース日）を提供してください。