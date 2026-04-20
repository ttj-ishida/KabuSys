# CHANGELOG

すべての注目すべき変更を記録します。  
このプロジェクトは Keep a Changelog の形式に準拠しています。  
詳細なコミット履歴がないため、ソースコードの内容から推測して記載しています。

なお、日付は本リリース作成日時（本CHANGELOG生成日）を使用しています。

## [Unreleased]
- （なし）

## [0.1.0] - 2026-04-20
初回公開リリース。以下の主要機能・ユーティリティを追加しました。

### 追加
- 実行スクリプト
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。プロセス優先度を高に設定して実行する。
    - KABUSYS_ENV が `paper_trading` の場合はペーパートレード専用の SQLite（data/paper_trading.db または環境変数で指定）を使用し、本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、ExecutionEngine のスレッド実行と停止フラグ監視を実装。
    - 起動時に停止フラグ（data/stop_requested.flag）が立っていれば起動を中止する。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - Monitoring は環境にかかわらず本番の sqlite_path を使用して監視データを保存。
    - 停止フラグの検知によりループを終了し、例外発生時はログを残して次ポーリングへ回復する実装。

- 設定管理
  - config.py
    - .env 自動読み込み機能を実装（プロジェクトルートの検出: .git または pyproject.toml）。
    - .env のパースは export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、行内コメントなどに対応。
    - 環境変数の保護（既存 OS 環境変数は上書きしない）を考慮した読み込みロジック。
    - Settings クラスを提供し、J-Quants / kabu API / DB パス /監視・システム設定など各種設定値をプロパティ経由で取得可能。値検証（例: PAPER_FILL_MODE、KABUSYS_ENV、LOG_LEVEL）を実装。
  - config_setup.py
    - .env の対話式ウィザードを追加。既存 .env の読み込み、入力時のシークレットマスク、デフォルト値や選択肢の提示、最終確認のうえファイル出力を行う。
    - 出力される .env に関する注意メッセージ（Git にコミットしない等）を実装。

- 設定検証 CLI
  - validate_config.py
    - .env と config/*.yaml の設定検証ツールを追加。
    - 必須環境変数の存在チェック、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在チェック、YAML ファイルの存在とパース（PyYAML があれば検証）を実装。
    - `--strict` フラグで警告も失敗扱いにできる。

- ロギング・プロセスユーティリティ
  - utils/logging_setup.py
    - 統一ログ設定ユーティリティを追加。コンソール（stdout）用 StreamHandler と日次ローテーション（TimedRotatingFileHandler、30日保持）のファイルハンドラをルートロガーへ設定。
    - LOG_LEVEL / LOG_DIR / app_name での振る舞い制御、ディレクトリ作成失敗時のフォールバック（コンソールのみ）対応。
  - utils/process_priority.py
    - クロスプラットフォームのプロセス優先度設定（Windows: PRIORITY_CLASS、POSIX: nice 値）と CPU affinity 設定ユーティリティを追加。
    - 権限不足や未対応 OS の際は警告を出して安全にスキップ。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - BUY シグナル選定（スコア降順、同点時のタイブレーク）と最大ポジション数制限の関数を追加。
    - 等金額配分（calc_equal_weights）およびスコア正規化配分（calc_score_weights）を実装。全スコアが 0 の場合は等分配へフォールバック。
  - portfolio/risk_adjustment.py
    - セクター集中上限チェック（apply_sector_cap）を実装。既存保有からセクター比率を計算し、上限超過のセクターの新規候補を除外するロジックを提供。`unknown` セクターは除外対象外とする挙動。
    - 市場レジームに応じた投下資金乗数（calc_regime_multiplier）を実装（"bull"=1.0, "neutral"=0.7, "bear"=0.3、未知時は警告を出して 1.0 にフォールバック）。
  - portfolio/position_sizing.py
    - 各銘柄の発注株数計算を実装。allocation_method（"risk_based" / "equal" / "score"）をサポート。
    - 単元株（lot_size）での丸め、1銘柄上限（max_position_pct）、aggregate cap（available_cash）によるスケーリング、cost_buffer を考慮した保守的なコスト見積、残余資金を用いた端数配分アルゴリズム等を実装。
    - 価格欠損時のスキップ、ログ出力による診断情報などを含む。

- リサーチ（未完の箇所あり）
  - research/factor_research.py（モメンタム/ボラティリティ/ファクター計算設計）
    - DuckDB 接続を受けて prices_daily / raw_financials を参照する設計。モメンタム指標（1M/3M/6M、MA200乖離）、ATR、出来高指標等を計算する方針を明記。ファイル中に計算用定数と docstring を追加（一部実装途中）。

- ペーパートレード検証ツール
  - tools/paper_verification_report.py
    - ペーパートレーディング用 SQLite（デフォルト data/paper_trading.db）から指標を集計して検証レポートをコンソール出力するツールを追加。
    - 稼働率（uptime）、注文成功率（fill rate）、送信率、P95 レイテンシなどの指標を算出・フォーマットし、閾値に基づく PASS/FAIL 判定を実装。データ不足やテーブル未存在時は適切に N/A を扱うフォールバック処理を実装。
    - 日付範囲フィルタ（--from / --to）と --db オプションに対応。

- パッケージ情報
  - __init__.py にバージョン情報を追加（__version__ = "0.1.0"）。

### 改善（設計上の注意点・挙動）
- .env 自動読み込みはデフォルトで有効。テスト等で自動読み込みを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD を設定する。
- ログは stdout と日次ローテーションファイルの両方へ出力。ログディレクトリ作成に失敗した場合はファイル出力を無効化してコンソール出力のみで継続する設計。
- run_monitoring は Monitoring 用 DB に本番 sqlite_path を常に使用する（環境に依存しない監視を意図）。
- run_execution は paper_trading モードで DB を完全に分離するため、本番データと混ざらないよう配慮。

### 既知の制限・ TODO（コード内コメントより）
- price が欠損（0.0）の場合にエクスポージャーが過少見積りされる可能性がある点（risk_adjustment.apply_sector_cap）の注記。将来的に前日終値や取得原価でのフォールバックを検討予定。
- position_sizing は現状で単元株数を全銘柄共通の lot_size として扱っている。将来的に銘柄別 lot_size をマスタで管理する拡張を検討。
- research/factor_research.py の実装は途中（ファイル末尾で未完の箇所あり）。DuckDB を使ったファクター計算の具体実装が残存。

---

（今後のリリースでは各機能の追加・バグ修正・API 変更を個別のバージョンエントリとして記載してください。）