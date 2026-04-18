# CHANGELOG

すべての重要な変更は Keep a Changelog の慣習に従って記録します。  
このファイルはコードベースの内容から推測して作成した初期リリース向けの変更履歴です。

フォーマット:
- Unreleased: 将来の変更用
- 各リリースにはリリース日を記載

---

## [Unreleased]

- 将来の変更・改善事項をここに記載します。

---

## [0.1.0] - 2026-04-18

初回公開リリース。主要な機能群とユーティリティ、CLI、ポートフォリオ構築・サイズ決定ロジック、監視・実行用ランナーを実装しています。

### 追加 (Added)

- コア設定・環境ロード
  - Settings クラスを実装（kabusys.config）。
    - .env 自動ロード機能（プロジェクトルートを探索して .env / .env.local を読み込む）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化。
    - 必須環境変数チェック用の _require ユーティリティ。
    - 各種設定プロパティ（DB パス、paper_trading 用パス、閾値、ログレベル判定等）。
    - PAPER_FILL_MODE の検証（instant/partial/never/reject）。

- 設定ウィザード CLI（kabusys.config_setup）
  - 対話式ウィザードで .env の初期作成 / 更新を支援。
  - J-Quants / kabu API / DB パス / LINE 通知など主要項目を扱う。
  - 既存 .env 読み込み、シークレットマスク表示、保存確認機能を提供。

- 設定検証 CLI（kabusys.validate_config）
  - .env と config/*.yaml の存在・基本整合性チェックを実装。
  - 必須環境変数チェック、KABUSYS_ENV 検証、LOG_LEVEL 検証、DB パス親ディレクトリ確認、YAML パース検査（PyYAML 必要）。
  - KABUSYS_ENV=live 用の追加ガード（LINE 通知設定や Kill Flag 動作に関する警告）。
  - --strict オプションで警告も失敗として扱う。

- 実行 / 監視用ランナー
  - run_execution.py
    - ExecutionEngine 起動ラッパー。
    - KABUSYS_ENV=paper_trading の場合は paper 用の専用 SQLite(DB) を使用（data/paper_trading.db をデフォルト）。
    - BrokerClientFactory を介して本番/モックのブローカークライアントを選択。
    - ExecutionEngine を別スレッドで起動し、data/stop_requested.flag による外部停止をサポート。
    - PID ファイル（data/execution.pid）管理。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔上書き可能（デフォルト 60 秒、無効値は警告のうえデフォルトにフォールバック）。
    - 監視は環境にかかわらず本番 sqlite_path を使用して監視テーブルを初期化。

- 監視 DB 初期化ヘルパー
  - init_monitoring_db の呼び出しにより監視テーブルの存在を保証（冪等）。

- ロギングユーティリティ（kabusys.utils.logging_setup）
  - 共通ログ設定関数 setup_logging を実装。
  - stdout への StreamHandler と日次ローテーション（TimedRotatingFileHandler）を用いたファイル出力（デフォルト logs/<app_name>.log、30 日保持）を追加。
  - LOG_DIR / LOG_LEVEL 環境変数に対応。ログディレクトリ作成失敗時はファイル出力をスキップして stdout のみで継続。

- プロセス優先度・CPU affinity ユーティリティ（kabusys.utils.process_priority）
  - set_process_priority(level) を実装（"high"/"normal"/"low"）。
  - Windows と POSIX 系（Linux/Mac/FreeBSD）を抽象化して nice 値・priority クラスを設定。
  - set_cpu_affinity(cpu_count) によりプロセスの CPU Affinity 固定をサポート（未指定時は全コア）。
  - 権限エラー等は警告を出して静かにスキップ。

- ポートフォリオ構築関連（kabusys.portfolio）
  - portfolio_builder:
    - select_candidates: スコア降順 + タイブレークにより候補選定。
    - calc_equal_weights, calc_score_weights: 等金額配分、スコア加重配分（スコア合計 0 の場合は等配分にフォールバック）。
  - risk_adjustment:
    - apply_sector_cap: セクター毎の既存エクスポージャーを計算し、上限超過セクターの新規候補を除外（unknown セクターは除外対象外）。
    - calc_regime_multiplier: レジームラベルに応じた資金乗数（bull/neutral/bear をサポート、未知のレジームはフォールバック）。
  - position_sizing:
    - calc_position_sizes: allocation_method ("risk_based", "equal", "score") に応じた発注株数を算出。
    - 単元株（lot_size）丸め、1 銘柄上限・aggregate cap（利用可能現金超過時のスケーリング）、cost_buffer による保守的見積りを実装。
    - risk_based では stop_loss_pct に基づくリスク制限計算を実装。

- Paper Trading 検証レポート（kabusys.tools.paper_verification_report）
  - paper_trading DB（デフォルト data/paper_trading.db）を解析し、稼働率、注文成功率、送信率、P95 レイテンシ等を算出し標準出力へレポート出力。
  - PASS/FAIL 判定基準を定義（稼働率 >=99%、成立率 >=90%、送信率 >=95%、P95 <=200ms）。
  - 日付フィルタ (--from/--to) と --db オプションをサポート。
  - P95 計算、各種 SQL クエリを実装。

- 研究用ファクタ計算（kabusys.research.factor_research）
  - モメンタム / ボラティリティ / リキディティ / バリュー等の計算ロジックの骨組みを実装（DuckDB を使った prices_daily / raw_financials の参照を想定）。
  - 各種定数・窓長を定義（1M/3M/6M、MA200、ATR20 等）。

- パッケージメタ情報
  - __version__ = "0.1.0"
  - パッケージエクスポート __all__ を定義（"data","strategy","execution","monitoring" 等を想定）。

### 変更 (Changed)

- N/A（初回リリースのため履歴上の変更はありません）

### 修正 (Fixed)

- MONITOR_POLL_INTERVAL に不正値（0 以下や非整数）が指定された場合に time.sleep が ValueError を起こす問題に対処。無効値は警告を出してデフォルト（60 秒）にフォールバックするように実装。

### 既知の問題 (Known issues)

- kabusys.research.factor_research.calc_momentum の実装が途中で切れている（ファイル末尾が不完全）。factor 計算モジュールの一部関数は未完了のため、実装完了が必要。
- 一部 TODO コメントあり（例: apply_sector_cap の価格欠損時のフォールバックや position_sizing の銘柄別 lot_size 対応）。将来的な改善候補。
- ローカルファイル/ディレクトリ作成権限がない環境ではログのファイル出力や DB ファイル生成が失敗する場合があり、これらは警告を出してフォールバック（stdout のみ等）する設計になっているが、運用時には適切なディレクトリ権限を推奨。

### セキュリティ (Security)

- 現在既知のセキュリティ脆弱性は特になし（ただしシークレット値は .env に平文保存されるため .env を絶対に Git 等へコミットしないことを README やウィザードにて注意喚起）。

---

配布/運用上の注意:
- .env.example を基に .env を作成し、validate_config で設定検証を行ってから実行してください。
- 本番（KABUSYS_ENV=live）での運用時は LINE 通知等のアラート設定を必ず確認してください（validate_config の live guard を参照）。
- paper_trading 実行時は本番 DB と完全分離するよう paper_sqlite_path を使用します（デフォルト: data/paper_trading.db）。

（この CHANGELOG はコード内容から推測して作成したものであり、実際のコミット履歴に基づくものではありません。）