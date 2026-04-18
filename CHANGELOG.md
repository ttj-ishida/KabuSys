# Changelog

すべての注目すべき変更点を記録します。本ファイルは Keep a Changelog の体裁に従います。

現行バージョン: 0.1.0

## [0.1.0] - 初回リリース
最初の公開リリース。システム全体の基盤機能（設定、実行/監視ランナー、ポートフォリオ構築、ユーティリティ、検証ツール、レポート生成など）を実装しました。

### 追加
- 基本パッケージ情報
  - `kabusys.__version__` を 0.1.0 として公開。

- 設定管理
  - .env 自動読み込み機能を実装（プロジェクトルート検出: `.git` または `pyproject.toml` を起点に探索）。
  - `.env` / `.env.local` の読み込み順序をサポート（OS 環境変数を保護する仕組みあり）。
  - 高度な .env パーサーを実装:
    - `export KEY=val` 形式対応
    - シングル/ダブルクォート内でのエスケープ処理対応
    - インラインコメントの取り扱い（クォート有無に応じたルール）
  - `Settings` クラスを実装し、環境変数アクセスをプロパティ化:
    - DB パス（DuckDB/SQLite）、PID/Kill フラグ、しきい値、Paper Trading の設定（PAPER_FILL_MODE、PAPER_TRADING_SQLITE_PATH など）
    - 環境（KABUSYS_ENV）とログレベルのバリデーション
    - `settings` 便宜オブジェクトを提供

- 起動ランナー
  - 実行エンジン起動スクリプト: `src/kabusys/run_execution.py`
    - `KABUSYS_ENV=paper_trading` 時に専用の Paper Trading DB を使用して本番 DB と分離
    - ブローカークライアントのファクトリ使用（BrokerClientFactory）
    - ExecutionEngine の組み立てとスレッド起動、停止フラグ（data/stop_requested.flag）による安全停止
    - PID ファイル管理用パス (data/execution.pid) の使用
  - 監視ループ起動スクリプト: `src/kabusys/run_monitoring.py`
    - SystemMonitor の初期化とポーリングループ
    - 環境変数 `MONITOR_POLL_INTERVAL` によるポーリング間隔の上書き（デフォルト 60 秒）
    - 監視は KABUSYS_ENV にかかわらず本番の sqlite_path を使用する点を明示
    - 停止フラグ検出でループ終了

- モジュール: ポートフォリオ構築
  - 候補選定・重み付け: `kabusys.portfolio.portfolio_builder`
    - select_candidates（スコア降順・タイブレークロジック）
    - calc_equal_weights（等金額配分）
    - calc_score_weights（スコア正規化、全スコア 0 の場合は等配分にフォールバック）
  - セクター集中制限・レジーム乗数: `kabusys.portfolio.risk_adjustment`
    - apply_sector_cap（既存保有を考慮したセクター上限フィルタ）
    - calc_regime_multiplier（"bull"/"neutral"/"bear" に対応、未知レジームは警告して 1.0 にフォールバック）
    - 実装上の注意点（unknown セクターは上限適用除外等）をドキュメント化
  - 発注株数決定・リスク制限: `kabusys.portfolio.position_sizing`
    - calc_position_sizes（allocation_method に応じた株数計算: "risk_based", "equal", "score"）
    - lot_size（現状グローバル固定）、cost_buffer（手数料・スリッページの保守的見積り）、aggregate cap のスケーリングロジック
    - 利用可能現金を超える場合のスケールダウンと残差への追加配分（lot 単位での処理）

- ユーティリティ
  - ログ設定ユーティリティ: `kabusys.utils.logging_setup`
    - stdout への StreamHandler（stdout を使用）と日次ローテートする TimedRotatingFileHandler をルートロガーへ設定
    - ログレベル・ログディレクトリの解決順序（引数 > 環境変数 > デフォルト）
    - ログディレクトリ作成失敗時のフォールバック（ファイルハンドラをスキップしてコンソール出力のみ）
    - 日次ローテーション・30 日分保持
  - プロセス優先度 / CPU affinity ユーティリティ: `kabusys.utils.process_priority`
    - Windows / POSIX(Linux, macOS 等) を吸収した優先度設定（"high"/"normal"/"low"）
    - CPU affinity の設定（利用可能コア数に基づき最初の N コアに固定）
    - 失敗時は警告を出して安全にスキップ

- 検証・設定ウィザード
  - 設定検証 CLI: `kabusys.validate_config`
    - 必須環境変数の有無チェック、KABUSYS_ENV/LOG_LEVEL/DB パスの検証
    - config/*.yaml の存在確認と（PyYAML があれば）パース検証
    - KABUSYS_ENV=live 用の追加安全チェック（LINE 設定の存在確認、KILL_FLAG_CLEAR_ON_START の警告等）
    - `--strict` オプション（警告を FAIL 扱いにする）
  - 環境設定ウィザード CLI: `kabusys.config_setup`
    - 対話形式で .env を作成・更新するウィザード
    - 入力補助（デフォルト・選択肢・シークレットマスク）
    - `.env` 出力テンプレート（Git コミット禁止の注意書き等）

- ツール
  - Paper Trading 検証レポート: `kabusys.tools.paper_verification_report`
    - Paper Trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）から稼働率、注文成功率、送信率、レイテンシ（avg/max/P95）、リスク却下数を算出してテキストレポートを出力
    - 基準値（稼働率99%、成立率90%、送信率95%、P95レイテンシ200ms）に基づく PASS/FAIL 判定
    - コマンドラインで期間指定（--from/--to）および DB パス指定（--db）に対応

- リサーチ
  - ファクター計算基盤（momentum 等）を開始実装: `kabusys.research.factor_research`
    - Momentum 指標（1M/3M/6M、MA200 乖離）等の計算方針と定数を定義
    - DuckDB 接続を受ける設計（prices_daily / raw_financials テーブル参照）
    - （注）一部実装はベースのみで継続実装が必要（ソース内に未完了箇所あり）

### 変更
- ログ出力の標準出力先を stderr ではなく stdout に統一（cron 等の外部リダイレクト互換性向上）。
- .env 読み込みの上書きポリシー:
  - `.env` は OS 環境変数を上書きしない（デフォルト）
  - `.env.local` は既存 OS 環境変数を保護しつつ上書き可能（開発向け）

### 修正 / 安全対策
- 起動時にプロセス優先度を先に設定することで、実行/監視の安定性を向上。
- Execution/Monitoring の DB 初期化で監視テーブルが存在することを保証（冪等的な init_monitoring_db 呼び出し）。
- run_execution/run_monitoring は停止フラグ（data/stop_requested.flag）検出で安全終了する実装。
- validate_config による起動前の設定検証機能を追加し、誤設定による事故リスクを低減。

### 既知の制限 / 注意事項
- `apply_sector_cap`: price_map に価格が欠損（0.0）がある場合、エクスポージャーが過小見積もられる可能性があり、将来的に前日終値や取得原価でのフォールバックを検討する旨を TODO として記載。
- `position_sizing`:
  - 単元株数（lot_size）は現状全銘柄共通の固定値（デフォルト 100）。将来的に銘柄別 lot_map に拡張する予定。
  - price が欠損の場合は当該銘柄をスキップする動作。
- factor_research モジュールは一部実装未完（ソース末尾で未完の行あり）。リサーチ機能は今後継続実装予定。
- PyYAML 未インストール環境では config/*.yaml の内容検証をスキップする（警告表示）。

### セキュリティ
- 機密情報（トークン・パスワード等）は .env に記載する前提。`.env` の Git 管理に注意（config_setup にも注意文を挿入）。
- 起動前に validate_config を実行して、本番（live）環境での未設定な通知設定等を検出することを推奨。

---

今後の予定（例）
- factor_research の完全実装（全ファクター計算、Z スコア正規化の統合）
- ExecutionEngine / Broker クライアント周りの詳細実装とテストカバレッジ強化
- 銘柄別 lot_size サポート、価格フォールバックロジックの導入
- モニタリング・アラート（LINE 通知等）の追加強化

（補足）本 CHANGELOG はソースコードの現状から推測して作成しています。今後のコミットで機能追加や修正が行われた場合、適宜更新してください。