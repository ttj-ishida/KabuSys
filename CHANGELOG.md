# CHANGELOG

すべての重要な変更点を記録します。フォーマットは "Keep a Changelog" に準拠しています。

なお本ファイルはコード内容から推測して作成しています（リポジトリの履歴そのものではありません）。実際のコミット履歴がある場合は適宜差し替えてください。

すべてのバージョンはセマンティックバージョニングを想定しています。

## [Unreleased]

- なし

## [0.1.0] - 2026-04-24

初回公開リリース。以下の主要機能・ユーティリティを実装しました。

### 追加 (Added)

- 基本パッケージとバージョン情報
  - パッケージ初期化: `kabusys.__version__ = "0.1.0"` を追加。

- 設定管理
  - Settings クラス（`kabusys.config`）を実装。
    - 環境変数から各種設定を取得するプロパティを提供（J-Quants / kabuステーション / LINE / DB / 監視閾値 / システムフラグ等）。
    - 環境（KABUSYS_ENV）として `development`, `paper_trading`, `live` をサポート。
    - Paper Trading 用の別 SQLite パス（`PAPER_TRADING_SQLITE_PATH`）や `PAPER_FILL_MODE` をサポート。
  - 自動 .env ロード機能を実装（プロジェクトルートを .git または pyproject.toml で探索）。
    - OS 環境変数優先、`.env.local` が `.env` を上書きする挙動を採用。
    - 自動ロードを無効化するための `KABUSYS_DISABLE_AUTO_ENV_LOAD` を追加。

- .env パース & ウィザード
  - `.env` の堅牢なパーサを実装（コメント、export プレフィックス、クォート中のエスケープの扱い等に対応）。
  - 対話形式で .env を作成/更新する CLI ウィザード（`kabusys.config_setup`）を実装。
    - 多数のキー定義（KABUSYS_ENV、JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DUCKDB_PATH、SQLITE_PATH、LOG_LEVEL、KILL_FLAG_CLEAR_ON_START 等）。
    - シークレット項目はマスク表示、デフォルト値の取り扱い、保存前の確認を行う。
    - .env を生成する際に「絶対に Git にコミットしないでください」という注意書きを出力。

- 設定検証ツール
  - `kabusys.validate_config` を実装。
    - 必須環境変数の存在確認、KABUSYS_ENV/LOG_LEVEL 値チェック、DB パスの親ディレクトリチェック、config/*.yaml の存在および（PyYAML があれば）パース検証、live 環境向けの追加ガード等を実施。
    - `--strict` オプションで警告を失敗扱いにできる。

- 実行・監視の起動スクリプト
  - ExecutionEngine 起動スクリプト（`kabusys.run_execution`）を追加。
    - 起動時にプロセス優先度を "high" に設定。
    - `KABUSYS_ENV=paper_trading` 時は paper_trading 用 SQLite（本番 DB と分離）を使用。
    - BrokerClientFactory によるブローカークライアント作成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、Engine のデーモンスレッド起動・停止処理を実装。
    - 停止フラグ（data/stop_requested.flag）および PID ファイルの利用。
  - Monitoring 起動スクリプト（`kabusys.run_monitoring`）を追加。
    - `MONITOR_POLL_INTERVAL` 環境変数でポーリング間隔をオーバーライド可能（デフォルト 60 秒）。不正値はフォールバックして警告。
    - 監視は環境に関わらず本番用 sqlite_path を使用する設計（監視データの一元管理）。
    - SystemMonitor の単発チェックループ（check_once）を呼び出し、例外時はログを残して次回ポーリングへ継続。
    - 停止フラグ検知と KeyboardInterrupt のハンドリング。

- ロギングユーティリティ
  - `kabusys.utils.logging_setup.setup_logging` を実装。
    - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション、30日保持）を設定。
    - ログレベル・ログディレクトリの解決順を定義（引数 > 環境変数 > デフォルト）。
    - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。

- プロセス優先度 / CPU affinity ユーティリティ
  - `kabusys.utils.process_priority` を実装。
    - Windows / POSIX（Linux/Mac/FreeBSD）差分を吸収してプロセス優先度を設定（`set_process_priority("high"|"normal"|"low")`）。
    - CPU コア固定（`set_cpu_affinity`）をサポート。権限不足や未サポート環境では警告を出して安全にスキップ。

- ポートフォリオ構築モジュール
  - `kabusys.portfolio.portfolio_builder`
    - シグナル選定（スコア降順、タイブレークに signal_rank）select_candidates。
    - 等重み・スコア正規化重み計算（calc_equal_weights / calc_score_weights）。全スコアが 0 の場合は等重みへフォールバックし警告。
  - `kabusys.portfolio.risk_adjustment`
    - セクター集中制限の適用（apply_sector_cap）。既存保有のセクターエクスポージャーを評価して候補を除外。unknown セクターは制限対象外。
    - レジーム乗数（calc_regime_multiplier）：bull/neutral/bear に対する乗数を返す。未知レジームは 1.0 でフォールバックし警告。
  - `kabusys.portfolio.position_sizing`
    - allocation_method（"risk_based"/"equal"/"score"）に基づく株数算出を実装。
    - 単元株（lot_size）丸め、1銘柄上限・aggregate cap（available_cash）によるスケーリング、cost_buffer を考慮した保守的見積り、残余の再配分ロジックを実装。

- リサーチ / ファクター計算（設計開始）
  - `kabusys.research.factor_research` にモメンタム等ファクター計算の骨組みを追加（DuckDB 接続を受けて prices_daily / raw_financials を参照する設計）。
    - モメンタム・MA200・ATR・流動性等の計算を行う想定の定数と関数を下準備。

- Paper Trading 向けレポートツール
  - `kabusys.tools.paper_verification_report` を実装。
    - Paper Trading の SQLite（デフォルト: data/paper_trading.db）を解析してレポートを生成。
    - 検証指標: 稼働率(uptime)、注文成功率(fill_rate)、送信率(send_rate)、P95 レイテンシ、リスク却下件数など。
    - 判定基準（デフォルト閾値）を定義し、PASS/FAIL を出力。
    - CLI オプションで期間指定（--from/--to）および DB パス指定（--db）。

### 変更 (Changed)

- なし（初回リリースに伴う実装）

### 修正 (Fixed)

- なし（初回リリースに伴う実装）

### セキュリティ (Security)

- .env を生成するテンプレートとウィザードで「.env を絶対に Git にコミットしないこと」を明示。
- シークレット値はウィザード表示でマスク表示。

### 既知の制限 / 注意点 (Notes)

- process_priority/set_cpu_affinity は実行環境の権限によっては動作せず警告が出ます（想定どおりスキップされます）。
- run_monitoring は監視 DB に対して常に本番 sqlite_path を使用します。開発環境での切り替えが不要な設計となっています（必要なら設定の追加を検討してください）。
- 一部の機能は外部依存（例: PyYAML による config YAML 検証）が任意です。PyYAML 未インストール時は該当チェックがスキップされ、警告のみ出力します。
- position_sizing の lot_size は現状すべての銘柄に共通の前提（例: 100 株）です。将来的に銘柄別 lot_size をサポートする設計拡張を予定。

---

この CHANGELOG はコードの内容から推測して作成した要約です。実際の開発履歴（コミット単位の差分）やリリースノートと合わせて必要な部分を追記・修正してください。