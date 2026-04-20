Keep a Changelog に準拠した CHANGELOG.md（日本語）を作成しました。コードベースの内容から推測して記載しています。必要があれば調整します。

----------------------------------------
# CHANGELOG

すべての注目すべき変更はこのファイルに記載します。  
フォーマットは "Keep a Changelog"（https://keepachangelog.com/ja/1.0.0/）に従います。

## [Unreleased]

## [0.1.0] - 2026-04-20
初回リリース — KabuSys の骨格となる自動売買・監視・設定ツール群を追加。

### 追加 (Added)
- 基本パッケージ情報
  - パッケージバージョンを `src/kabusys/__init__.py` にて `0.1.0` として定義。

- 起動スクリプト / デーモン
  - `run_execution.py`
    - ExecutionEngine を起動するメインスクリプトを追加。
    - 環境変数 `KABUSYS_ENV=paper_trading` の場合はペーパートレード用の分離された SQLite（デフォルト: data/paper_trading.db）を使用する挙動を導入（MockBrokerClient 経由の処理想定）。
    - プロセス優先度を高く設定したのちに各コンポーネントを初期化し、スレッドでエンジンを実行。停止フラグ（data/stop_requested.flag）検知で安全に停止する仕組みを実装。
    - PID ファイル管理（data/execution.pid）をサポート。
  - `run_monitoring.py`
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL` で上書き可能（デフォルト 60 秒）。不正値は警告のうえデフォルトにフォールバック。
    - 監視用 DB は環境にかかわらず本番の sqlite_path を使用する（監視は常に監視対象 DB を見る想定）。
    - 停止フラグ（data/stop_requested.flag）検知でループを終了。

- 環境設定・設定管理
  - `config.py`
    - .env 自動読み込み機能を実装（プロジェクトルートの .env / .env.local を読み込む。読み込み順: OS 環境 > .env.local > .env）。
    - 自動ロードを無効化するための環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD` を追加。
    - .env の読み込みで既存 OS 環境変数を保護する仕組み（protected keys）を導入。
    - .env の行パーサを強化（export 形式対応、クォート内のエスケープ対応、インラインコメント処理など）。
    - 設定アクセス用の Settings クラスを追加（J-Quants, kabu API, LINE, DB パス, 監視閾値, 環境判定プロパティ等を提供）。
    - Paper Trading 固有設定（PAPER_FILL_MODE, PAPER_TRADING_SQLITE_PATH）をサポート。PAPER_FILL_MODE の妥当性チェック実装。

  - `config_setup.py`
    - 対話式ウィザードによる .env 初期作成 / 更新ツールを追加。
    - 必須・任意項目やシークレットのマスク表示、確認プロンプト、ファイル書き出しをサポート。

  - `validate_config.py`
    - 起動前チェック CLI を追加。必須環境変数、KABUSYS_ENV の妥当性、ログレベル、DB パス、config/*.yaml の存在／パースチェックを実装。
    - PyYAML が未インストールの場合は YAML 検証をスキップして警告を出す。
    - `--strict` オプションで警告を FAIL として扱うモードを追加。
    - 本番環境用の追加ガード（LINE トークン未設定や Kill Flag 自動クリアの設定への注意喚起）を実装。

- ロギング / プロセス制御ユーティリティ
  - `utils/logging_setup.py`
    - 共通ロギング設定ユーティリティを追加。
    - stdout への StreamHandler と日次ローテーション (TimedRotatingFileHandler、30日分保持) のファイルハンドラをルートロガーに設定。
    - ログディレクトリ作成に失敗した場合はファイル出力をスキップして stdout のみで継続するフォールバックを実装。
    - ログレベル・ログディレクトリの解決順（引数 > 環境変数 > デフォルト）を実装。
  - `utils/process_priority.py`
    - Windows / POSIX（Linux/macOS 等）を吸収するプロセス優先度設定ユーティリティを追加。
    - CPU affinity 設定（最初の N コアに固定）をサポート。権限不足や未対応 OS の場合は警告を出してスキップ。

- Execution 周りのコンポーネント（スケルトン）
  - 実行系（ExecutionEngine、OrderManager、OrderRepository、RiskManager、Reconciler、BrokerClientFactory）を組み立てるための参照/呼び出しを run_execution に実装（各モジュール自体は別ファイルに存在する想定）。

- Paper Trading 検証ツール
  - `tools/paper_verification_report.py`
    - ペーパートレード記録（SQLite）から各種指標（稼働率、注文成功率、送信率、リスク却下数、レイテンシ統計）を集計してレポートを出力するツールを追加。
    - コマンドライン引数で期間指定（--from, --to）および DB パス指定（--db）をサポート。
    - P95 計算、閾値比較（稼働率 99%、注文成功率 90%、送信率 95%、P95 レイテンシ 200 ms）を行い PASS/FAIL 判定を出力。

- ポートフォリオ構築 / 資金配分ユーティリティ
  - `portfolio/portfolio_builder.py`
    - 候補銘柄選定（スコア降順・タイブレーク）、等金額配分、スコア加重配分の純粋関数を追加。
  - `portfolio/risk_adjustment.py`
    - セクター集中上限の適用（既存ポジションのセクター比率を計算して新規候補を除外）および市場レジームに応じた投下資金乗数（bull/neutral/bear）を計算する関数を追加。
  - `portfolio/position_sizing.py`
    - 各銘柄の発注株数算出ロジックを追加（allocation_method: risk_based / equal / score をサポート）。
    - 単元株（lot_size）丸め、1銘柄上限・aggregate cap（利用可能現金に応じたスケーリング）、cost_buffer（手数料・スリッページ見積）を考慮。
    - リスクベース算出、スケーリングに伴う端数処理（fractional remainder に基づく追加配分）などのロジックを実装。

- リサーチ / ファクター計算（骨格）
  - `research/factor_research.py`
    - Momentum / Value / Volatility / Liquidity 等のファクター計算を行うためのモジュール骨格を追加（DuckDB 接続を受け取る設計、定数・計算方針の注記あり）。一部関数は未完（ファイル末尾で途中）。

### 変更 (Changed)
- 監視（monitoring）DBの扱い
  - 監視は環境にかかわらずデフォルトの本番 sqlite_path を参照するように明示（run_monitoring）。
- .env の読み込み方をより安全に
  - OS 環境変数を上書きしない既定動作、.env.local の優先適用、protected keys の概念を導入（config.py）。

### 修正 (Fixed)
- 環境パーサの堅牢化
  - export 形式やクォート内のエスケープ処理、インラインコメント取り扱いなどをサポートし、不正な .env 行を安全に無視するように改善（config._parse_env_line）。

### セキュリティ (Security)
- シークレット値の取り扱い
  - config_setup ウィザードでシークレット表示をマスク（****）してプロンプト表示。
  - .env をコミットしないことを README/ファイルヘッダで明記（config_setup による .env テンプレート）。

### 既知の制約・注意点 (Known issues / Notes)
- research/factor_research.py は一部実装が途中で終わっています（ファクター計算の一部関数が未完）。今後の実装が必要です。
- run_execution は BrokerClientFactory など外部コンポーネントに依存しており、環境に応じた Broker の実装（Mock / 実取引）が必要です。
- process_priority / cpu_affinity の設定は権限や OS に依存し、失敗時は警告を出してスキップします。
- logging_setup はログディレクトリの作成に失敗するとファイル出力を停止します（代わりに stdout にログを出す）。これはフォールバック動作です。

----------------------------------------

必要であれば以下を追加できます:
- それぞれのモジュールごとの詳細な変更差分（関数一覧やインターフェイスの説明）
- リリース日をソース管理のコミット日やリリースタグに合わせて調整
- Unreleased セクションに開発中の変更を追加

どの程度の粒度で記載を続けるか指示をください。