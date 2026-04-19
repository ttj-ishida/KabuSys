# CHANGELOG

すべての重要な変更をここに記録します。  
フォーマットは「Keep a Changelog」に準拠しています。  
（以下の記載は提示されたソースコードの内容から推測して作成しています。）

## Unreleased
- Added
  - research/factor_research.py の実装が進行中（モメンタム・ボラティリティ等のファクター計算ロジックを実装中）。一部実装が未完/切り出し途中のため、今後追加のユニットや出力整形が入る見込み。
- Changed
  - 内部設計の調整予定: portfolio/position_sizing のスケーリング・端数処理ロジックや risk_adjustment のセクター除外ルールに関する微調整。
- Fixed
  - なし（現時点での未リリース修正は明記なし）。
- Notes
  - 本セクションは今後の開発計画や未完成箇所の短期的な追記に使用します。

---

## 0.1.0 - 2026-04-19
初回公開（推定） — 基本的な自動売買フレームワークのコア機能を実装。

### Added
- 全体
  - パッケージ初期バージョンを定義（kabusys.__version__ = "0.1.0"）。
- 設定関連
  - 環境変数／.env 管理モジュール（kabusys.config）
    - プロジェクトルート自動検出（.git または pyproject.toml を基準）。
    - 独自の .env パーサを実装（コメント、クォート、export 構文に対応）。
    - .env/.env.local の自動ロード（OS 環境変数を保護）。
    - Settings クラスを提供し、各種設定値（DB パス、API トークン、監視閾値、環境種別など）を型付きプロパティで取得可能。
    - PAPER_FILL_MODE のバリデーション（instant/partial/never/reject を許容）。
  - 対話式設定ウィザード（kabusys.config_setup）
    - .env を対話的に生成／更新する CLI を提供。シークレットはマスク表示、保存確認あり。
- 検証ツール
  - 設定検証 CLI（kabusys.validate_config）
    - 必須環境変数や KABUSYS_ENV、LOG_LEVEL、DB パス、config/*.yaml の存在・パースチェック。
    - --strict オプションで警告も失敗扱いにできる。
    - PyYAML 未インストール時は YAML 検証をスキップして警告出力。
- 起動スクリプト
  - 監視プロセス起動スクリプト（kabusys.run_monitoring）
    - SystemMonitor のポーリングループを起動。MONITOR_POLL_INTERVAL 環境変数による間隔上書き（デフォルト 60 秒）。
    - 停止フラグ（data/stop_requested.flag）検知による安全終了処理。
    - 監視は環境に依らず本番用 sqlite_path を使用する設計。
  - 実行エンジン起動スクリプト（kabusys.run_execution）
    - ExecutionEngine を組み立ててセッションをデーモンスレッドで起動。
    - KABUSYS_ENV=paper_trading 時は paper_trading 用 SQLite（data/paper_trading.db など）を使用し、本番 DB と分離。
    - 停止フラグ検知で engine.stop() を呼び安全に停止。
    - PID ファイル管理、優先度設定（High）を実施。
- 実行関連コンポーネント（名前空間でのエクスポートあり）
  - Broker クライアント生成ファクトリ（BrokerClientFactory: 実行時に本番/モックを切り替え想定）。
  - ExecutionEngine、OrderManager、OrderRepository、Reconciler、RiskManager 等の組み立て（run_execution で起動）。
- モニタリング DB
  - 監視テーブル初期化ヘルパ（init_monitoring_db）があり、sqlite 接続時に呼び出して冪等にテーブルを保証。
- ロギング・プロセス制御ユーティリティ
  - ロギングセットアップ（kabusys.utils.logging_setup）
    - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次・30世代）を設定。
    - LOG_DIR 作成失敗時はファイル出力をスキップしてコンソールのみで継続。
    - 既存ハンドラの二重登録を防止して再設定する。
  - プロセス優先度 / CPU affinity ユーティリティ（kabusys.utils.process_priority）
    - Windows / POSIX を吸収して簡易に優先度変更（high/normal/low）や CPU affinity 固定をサポート。
    - 権限不足や未対応環境では警告を出して安全にフォールバック。
- ポートフォリオ構築ライブラリ（kabusys.portfolio）
  - portfolio_builder
    - 候補選定（select_candidates）、等分配（calc_equal_weights）、スコア加重配分（calc_score_weights）。スコア合計が 0 の場合は等分配へフォールバックし警告出力。
  - risk_adjustment
    - セクター集中を抑制する apply_sector_cap（当日売却予定の銘柄はエクスポージャー計算から除外）。
    - 市場レジームに応じた投下資金乗数 calc_regime_multiplier（bull/neutral/bear、未知値は警告の上 1.0 フォールバック）。
  - position_sizing
    - allocation_method（risk_based / equal / score）に基づく発注株数計算。
    - 単元株（lot_size）で丸め、per-stock 上限・aggregate 上限のチェック、コストバッファ（手数料・スリッページ想定）対応。
    - 利用可能現金を超える場合はスケールダウンして端数（lot 単位）を残差順に再配分するアルゴリズムを実装。
- Paper Trading 検証ツール
  - tools/paper_verification_report.py
    - Paper Trading 用 SQLite から稼働率、注文成功率、送信率、P95 レイテンシ等を集計しレポートを出力。
    - デフォルト閾値（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200ms）に基づく PASS/FAIL 判定。
    - --from/--to/--db オプションで期間・DB を指定可能。
    - P95 算出、日付フィルタの ISO8601 変換に対応。
- research
  - research/factor_research.py（ファクター計算の骨組みを実装）
    - DuckDB 接続を受けて prices_daily / raw_financials を参照する設計。モメンタム等の計算用定数を定義。
    - 実装途中の関数あり（ファイル末尾で途中切れが見られる）。

### Changed
- ロギング
  - StreamHandler を stdout に固定（stderr ではなく stdout を使うことで cron 等のリダイレクトが容易に）。
- DB の取り扱い
  - 監視（monitoring）は KABUSYS_ENV にかかわらず「本番用 sqlite_path」を使用するポリシーを明示（run_monitoring）。
  - 実行（execution）は paper_trading 時に専用 SQLite を使用し本番 DB と分離（run_execution）。
- .env 読み込み優先度
  - OS 環境変数 > .env.local > .env の優先順で読み込む仕様とし、既存 OS 環境は保護（protected パラメータ）する実装に。

### Fixed
- 設定バリデーション
  - validate_config によりプレースホルダ値（"_here" 等）検出時に警告を出すようにした。
- 起動スクリプトの停止処理
  - stop フラグファイルを監視して安全に終了する処理を標準化（run_monitoring / run_execution）。

### Security
- 機密情報の扱い
  - config_setup の出力で .env ファイルに機密情報を保存する旨の注意書き（.env を Git にコミットしないよう明示）。
  - Settings の必須トークン取得時に未設定で ValueError を送出して安全性を担保。

---

もし特定ファイルや機能ごとの詳細な変更履歴（コミット単位や差分に基づく正確なログ）が必要であれば、Git の履歴（git log / git diff）を提供していただければ、それに基づく正確な CHANGELOG を作成できます。