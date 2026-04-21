# CHANGELOG

すべての注目すべき変更履歴をこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠します。  

## [Unreleased]

## [0.1.0] - 2026-04-21
初回リリース。日本株自動売買システム (KabuSys) の基本コンポーネントを実装しました。

### 追加 (Added)
- 全体
  - パッケージ初期版を追加。バージョンは `kabusys.__version__ = "0.1.0"`。
  - プロジェクトルート検出ロジックを実装し、.env 自動ロードの基盤を追加（`.env` / `.env.local` を優先順で読み込み、OS 環境変数を保護）。
  - 環境変数ファイルの柔軟なパーサーを実装（`export` プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメント処理に対応）。

- 設定関連
  - Settings クラス (`src/kabusys/config.py`) を実装し、アプリケーション設定（J-Quants トークン、kabu API パスワード、DB パス、PID ファイル、監視閾値、環境判定など）を環境変数から取得可能に。
  - `settings` インスタンスをエクスポート。

- 開発/運用支援 CLI
  - 環境設定ウィザード `config_setup.py` を追加：
    - 対話式で `.env` を作成・更新できるウィザード（シークレット入力マスク、選択肢、デフォルトのサポート）。
    - `.env` 書き込みテンプレートを提供。
  - 設定検証 CLI `validate_config.py` を追加：
    - 必須環境変数のチェック、KABUSYS_ENV/LOG_LEVEL の妥当性検証、DB パスの親ディレクトリ検査、config/*.yaml の存在・パース検証（PyYAML 未導入時は警告）。
    - `--strict` オプションで警告を失敗扱いにできる。

- 実行スクリプト / デーモン
  - 実行エンジン起動スクリプト `run_execution.py` を追加：
    - `KABUSYS_ENV=paper_trading` のときは Paper Trading 用 SQLite（`PAPER_TRADING_SQLITE_PATH` / `data/paper_trading.db`）を使用し、本番 DB から完全に分離。
    - BrokerClient の生成は `BrokerClientFactory.create(settings)` に委譲。
    - OrderRepository、OrderManager、RiskManager（`RiskConfig` デフォルト値を含む）、Reconciler、ExecutionEngine を組み立ててデーモンとして実行。
    - 停止フラグ（data/stop_requested.flag）および実行 PID ファイル（data/execution.pid）による制御をサポート。
  - 監視ループ起動スクリプト `run_monitoring.py` を追加：
    - `SystemMonitor` を初期化しポーリングループを起動。ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL`（デフォルト 60 秒）で上書き可。
    - 監視は KABUSYS_ENV にかかわらず本番用 `sqlite_path` を使用して監視テーブルを管理。
    - 停止フラグの検知でループ終了、KeyboardInterrupt ハンドリングを実装。

- 監視 / DB 初期化
  - 監視用 DB 初期化ユーティリティ `init_monitoring_db` を参照実装（各起動スクリプトで冪等に呼び出して監視テーブルの存在を保証）。

- ロギング / プロセス管理ユーティリティ
  - 統一ログ設定ユーティリティ `utils/logging_setup.py` を追加：
    - ルートロガーに StreamHandler (stdout) と TimedRotatingFileHandler（日次・30世代保持）を設定。
    - ログレベルおよびログディレクトリの解決順を実装。ログディレクトリ作成失敗時はファイル出力をスキップして stdout のみで継続。
  - プロセス優先度/CPU affinity ユーティリティ `utils/process_priority.py` を追加：
    - Windows と POSIX を吸収して `set_process_priority("high"|"normal"|"low")`、`set_cpu_affinity(n)` を提供。
    - 権限不足等で設定できない場合は警告を出し安全にフォールバック。

- ポートフォリオ構築
  - `portfolio` パッケージを追加（純粋関数群、DB 非依存、メモリ内計算）：
    - `portfolio_builder.py`：
      - 候補抽出 select_candidates、等金額 calc_equal_weights、スコア加重 calc_score_weights（スコアが全て 0 の場合等金額にフォールバック）。
    - `risk_adjustment.py`：
      - セクター集中制限 apply_sector_cap（当日売却予定銘柄の除外、"unknown" セクターは適用除外）。
      - レジーム乗数 calc_regime_multiplier（bull/neutral/bear に対する乗数、未知値は警告のうえ 1.0 フォールバック）。
    - `position_sizing.py`：
      - 各配分方式（risk_based / equal / score）に対応した株数計算（単元株丸め、per-stock 上限、aggregate cap スケーリング、cost_buffer による保守的見積り、残差に基づくロット追加配分）。
    - package export を設定 (`portfolio.__init__`)。

- リサーチ / ファクター
  - `research/factor_research.py` を追加（ファクター計算の基礎実装）：
    - モメンタム、移動平均乖離、ATR、流動性等の計算方針と定数を定義（DuckDB への依存を想定）。
    - P95 計算やスキャン窓などのユーティリティを実装（実装はモジュール内で継続的に拡張予定）。

- ツール
  - `tools/paper_verification_report.py` を追加：
    - Paper Trading 用 SQLite（`PAPER_TRADING_SQLITE_PATH`）から各種指標（稼働率、注文成功率、送信率、P95 レイテンシ）を集計してレポート出力。
    - Pass/Fail 基準値を定義（稼働率 >= 99%、注文成功率 >= 90% など）。
    - 日付フィルタ（--from / --to）、--db オプションに対応。

### 変更 (Changed)
- なし（初回リリースのため既存機能の変更履歴はなし）。

### 修正 (Fixed)
- なし（初回リリース）。

### 注意事項 / 運用メモ
- .env 自動読み込みはデフォルトで有効。自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト等で使用）。
- Paper Trading 環境は本番 SQLite と分離されています。運用時に誤って本番 DB を上書きしないよう `KABUSYS_ENV` と `PAPER_TRADING_SQLITE_PATH` の設定を確認してください。
- run_monitoring は監視 DB に本番 `SQLITE_PATH` を使用します（監視情報は本番環境での一元管理を想定）。これは設計上の意図であるため、必要に応じて設定を変更してください。
- プロセス優先度設定や CPU affinity の操作は権限のある環境でのみ成功します。失敗した場合は警告ログが出力され、処理は継続されます。

---

将来のリリースでは、ファクター計算の全面実装、ExecutionEngine / Broker 周りの詳細実装、テストカバレッジと CI ワークフロー、ドキュメントの追加を予定しています。