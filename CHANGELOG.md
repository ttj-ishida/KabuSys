# Changelog

すべての注目すべき変更をここに記録します。フォーマットは「Keep a Changelog」に準拠しています。  

現在のリリース: 0.1.0

---

## [Unreleased]

- (なし)

---

## [0.1.0] - 2026-04-17

初回リリース。以下の主要機能・ユーティリティ・CLI を追加しました。

### 追加 (Added)
- 全体
  - パッケージ初期バージョンとして基礎的な自動売買／解析／運用支援機能群を追加。
  - パッケージバージョンを `kabusys.__version__ = "0.1.0"` として定義。

- 環境設定 / 設定読み込み
  - `kabusys.config.Settings`:
    - 環境変数経由での設定取得用プロパティ群を実装（J-Quants / kabuAPI / DB / LINE / 監視閾値 等）。
    - `PAPER_FILL_MODE` の値検証（"instant" | "partial" | "never" | "reject"）を追加。
    - `KABUSYS_ENV` / `LOG_LEVEL` 等の妥当性チェックを実装。
    - `paper_sqlite_path` 等、paper_trading 用データベースパスを提供。
  - 自動 .env 読み込み:
    - プロジェクトルート（.git または pyproject.toml）を基準に `.env` / `.env.local` をロード。OS 環境変数を保護する仕組みあり。
    - `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` による自動ロード無効化をサポート。
  - `.env` パースの堅牢性向上:
    - シングル/ダブルクォート内のバックスラッシュエスケープやコメント扱いの挙動に対応。

- 設定関連 CLI
  - `kabusys.config_setup`:
    - 対話式ウィザードで `.env` を初期作成・更新する CLI を追加。
    - デフォルト値、選択肢、シークレット扱い、説明付きプロンプトを提供。
  - `kabusys.validate_config`:
    - .env と config/*.yaml （存在する場合）を事前検証する CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在チェック、PyYAML 有無に応じた YAML 検証、KABUSYS_ENV=live 時の追加警告等を実装。
    - `--strict` オプションで警告を失敗扱いにするモードを提供。

- 実行エントリ / デーモン類
  - `run_execution.py`:
    - ExecutionEngine 起動スクリプトを追加。
    - `KABUSYS_ENV=paper_trading` 時は paper_trading 用 SQLite を使用し、MockBrokerClient を利用する設計（本番 DB と分離）。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、Engine のスレッド実行と停止フラグ連携を実装。
    - デフォルトの RiskManager 設定値（max_position_pct=0.20, max_utilization=0.80, rate_limit_per_sec=5, circuit_breaker 等）を提供。
  - `run_monitoring.py`:
    - SystemMonitor ポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値時はデフォルトにフォールバックして警告。
    - 停止フラグファイル (data/stop_requested.flag) を検出して安全にループを終了。
    - 監視はどの環境でも本番 sqlite_path を参照する動作。

- モニタリング / DB 初期化
  - `monitoring.monitoring_db.init_monitoring_db` を呼び出して監視テーブルの存在を保証（冪等に初期化）。

- ユーティリティ
  - `kabusys.utils.process_priority`:
    - Windows / POSIX の差分を吸収してプロセス優先度（high/normal/low）を設定するユーティリティを追加。
    - CPU アフィニティを先頭 N コアに固定する `set_cpu_affinity` を追加（利用可能コア数を考慮）。
    - 権限不足や未対応プラットフォームでの安全なフォールバック（警告ログ）を実装。

- ポートフォリオ構築（純粋関数群）
  - `kabusys.portfolio.portfolio_builder`:
    - 候補選定 `select_candidates`、等金額 `calc_equal_weights`、スコア加重 `calc_score_weights` を追加。
    - スコア合計が 0 の場合は等金額にフォールバックして WARNING を出力。
  - `kabusys.portfolio.risk_adjustment`:
    - セクター集中制限の `apply_sector_cap` を追加（当日売却予定銘柄を除外、"unknown" セクターは制限対象外）。
    - マーケットレジームに応じた投下資金乗数 `calc_regime_multiplier` を追加（bull/neutral/bear 対応、未知値は警告して 1.0 フォールバック）。
  - `kabusys.portfolio.position_sizing`:
    - 株数決定ロジック `calc_position_sizes` を追加。
    - risk_based / equal / score の allocation_method に対応。
    - 単元株（lot_size）丸め、1 銘柄上限、aggregate 上限（available_cash）によるスケールダウン、cost_buffer による保守的見積り、残余を端数優先度で配分するロジック等を実装。
  - `kabusys.portfolio.__init__` で主要関数を公開。

- リサーチ / ファクター計算
  - `kabusys.research.factor_research`:
    - DuckDB 接続を用いたファクター計算モジュールを追加。
    - モメンタム（1M/3M/6M、MA200乖離）、ボラティリティ（20日 ATR）、流動性（20日平均売買代金、出来高変化率）等の計算を実装。
    - 空データ・不足データの場合に None を返す設計、ターゲット日に対する SQL ウィンドウ関数を用いた実装。

- ツール
  - `kabusys.tools.paper_verification_report`:
    - Paper Trading の検証レポート生成 CLI を追加（期間指定オプションあり）。
    - 稼働率、注文成功率、送信率、リスク却下数、レイテンシ（平均/最大/P95）などを算出し、閾値に基づく PASS/FAIL 判定を出力。
    - デフォルト閾値: 稼働率 99.0%、成立率 90.0%、送信率 95.0%、P95 レイテンシ 200 ms。
    - P95 計算、日付フィルタリング、DB 存在チェックを実装。

### 変更 (Changed)
- (初回リリースのため該当なし)

### 修正 (Fixed)
- (初回リリースのため該当なし)

### 破壊的変更 (Removed / Breaking Changes)
- (初回リリースのため該当なし)

### 注意事項 / 補足
- セキュリティ: `.env` は絶対に Git にコミットしない旨の注意を config_setup のヘッダに明記。
- 動作プラットフォーム: process priority / cpu affinity の一部操作は権限やプラットフォーム依存で失敗する可能性があり、その場合は警告を出してスキップします。
- Paper Trading: 本番データベースと paper_trading 用 DB は分離される設計（PAPER_TRADING_SQLITE_PATH による上書き可能）。
- 自動ロードや設定検証を活用して起動前に環境を確認してください（`python -m kabusys.validate_config`、`python -m kabusys.config_setup`）。

---

今後の予定（例）
- モニタリングテーブル定義の拡張、アラート送信（LINE）実装、ExecutionEngine 内部のログ/トランザクション保持強化など。