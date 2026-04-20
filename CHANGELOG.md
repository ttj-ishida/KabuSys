# CHANGELOG

すべての変更は Keep a Changelog の形式に従います。  
このファイルはリポジトリのコード内容から推測して作成したリリースノートです（自動生成・推定に基づきます）。誤りや補足があれば修正してください。

## [Unreleased]

- ドキュメント化・テストケースの追加など未リリースの作業が想定されます（コード内に TODO/拡張案が多数存在します）。

## [0.1.0] - 2026-04-20

初回リリース — KabuSys 基本モジュール群を実装しました。以下の主要機能と CLI / ユーティリティを提供します。

### 追加 (Added)
- コア機能
  - portfolio: 銘柄選定・配分・株数算出・リスク調整の純粋関数群を実装。
    - select_candidates: BUY シグナルから候補選定（スコア降順、同点は signal_rank でタイブレーク）。
    - calc_equal_weights / calc_score_weights: 等金額配分・スコア重み付け（スコア全0時に等金額へフォールバック）。
    - calc_position_sizes: allocation_method（risk_based / equal / score）に基づく株数決定、単元株丸め、aggregate cap によるスケーリング。
    - apply_sector_cap: セクター集中上限チェック。既存ポジションと当日売却予定を考慮して候補を除外。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金係数を提供。
  - research: factor_research モジュールを追加（モメンタム・ボラティリティ等のファクター計算の基盤を実装）。（関数の一部は継続実装予定）
- 起動スクリプト / 実行系
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV に応じて Paper Trading 用の専用 SQLite を使用（settings.is_paper による切替）。
    - BrokerClientFactory 経由で本番/モックブローカーを生成、OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine を起動。
    - stop flag（data/stop_requested.flag）と実行 PID ファイル（data/execution.pid）をサポートし、外部からの停止指示を受け付ける。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL によるポーリング間隔変更（デフォルト 60 秒）。
    - 監視は常に本番の sqlite_path を参照（環境に依存せず監視 DB を使用）。
    - stop フラグでループ終了、例外発生時はログに記録して次ループに回復。
- 設定管理 / ユーティリティ
  - config.py:
    - .env 自動読み込み機能を実装（プロジェクトルートを .git / pyproject.toml で探索）。
    - .env / .env.local のロード順や上書きルール（OS 環境変数を保護）を実装。
    - Settings クラスで各種環境変数の取得とバリデーションを提供（DB パス、KABUSYS_ENV、PAPER_FILL_MODE 等）。
    - 必須環境変数が未設定の場合に ValueError を投げる _require() を提供。
  - config_setup.py:
    - .env の対話式ウィザード（初期作成 / 更新）を実装。シークレット値のマスク表示、選択肢・デフォルト値をサポート。
    - 書き込みテンプレートを用意（.env を Git にコミットしない旨を明記）。
  - validate_config.py:
    - 起動前検証 CLI を追加。.env と config/*.yaml の存在・基本整合性検証を実施。
    - --strict モードで警告を失敗扱いにできる。
- ロギング / プロセス調整
  - utils/logging_setup.py:
    - StreamHandler（stdout）と TimedRotatingFileHandler（日次・30世代保持）をルートロガーに設定する共通セットアップを提供。
    - LOG_DIR / LOG_LEVEL の解決順を実装。ログディレクトリ作成失敗時はファイル出力を無効化しコンソール出力のみで継続。
  - utils/process_priority.py:
    - プラットフォームを吸収するプロセス優先度設定（Windows / POSIX）と CPU affinity 設定ユーティリティを実装。
    - 権限不足や未対応 OS は警告ログ化してスキップする安全設計。
- ツール
  - tools/paper_verification_report.py:
    - ペーパートレードの検証レポート生成スクリプトを実装。
    - system_status / trade_logs / risk_logs から稼働率・注文成功率・送信率・レイテンシ等を集計し、閾値（稼働率 99%、成立率 90% 等）との比較で PASS/FAIL を判定。
    - --from / --to / --db オプションをサポート。PAPER_TRADING_SQLITE_PATH 環境変数にも対応。
- パッケージ情報
  - src/kabusys/__init__.py に __version__ = "0.1.0" を設定。

### 変更 (Changed)
- なし（初回リリースのため既存からの変更はありません）。ただし設計上の既定値やフォールバック動作を多く定義しています（例: PAPER_FILL_MODE のバリデーションとデフォルト、ログ設定のフォールバック等）。

### 修正 (Fixed)
- なし（新規実装）。

### 既知の制約 / 注意事項
- factor_research.calc_momentum の実装はファイル末尾で途中（start_da... で途切れ）になっている箇所があり、完全実装が必要です（DuckDB クエリ等の最終調整を要する）。
- calc_position_sizes 内のコメントにあるように将来的に銘柄別 lot_size 対応や価格フォールバックを検討する必要あり（現在は単一 lot_size を前提）。
- apply_sector_cap は sector_map に存在しないコードを "unknown" 扱いとしてセクター制限を適用しない設計。意図的だが運用上の注意が必要。
- run_monitoring / run_execution は stop フラグと PID ファイルを利用するが、複数インスタンス同時稼働に関するガードは限定的です。
- process_priority と CPU affinity は OS と権限に依存しており、設定に失敗した場合は警告に留まります。
- .env 自動読み込みはプロジェクトルートを検出できない場合はスキップされるため、パッケージ配布後の挙動に注意してください。

### 開発上の TODO / 改善案（コード内コメントより）
- portfolio.position_sizing: 銘柄別 lot_size を持つ設計への拡張（stocks マスタ導入）。
- portfolio.position_sizing: 価格が欠損した際のフォールバック（前日終値や取得原価の使用）を実装。
- research/factor_research: ファクター群の完全実装とテストデータ増強。
- モジュール単体テスト（特に position sizing / risk manager / reconciler 等の端数・スケールロジック）を充実させる。
- config の .env パーサーは多くのケースを扱えるよう実装済みだが、特殊ケースの追加カバレッジを検討。

---

以上が初回リリース (0.1.0) の想定変更履歴です。必要に応じて日付・項目を編集して正確な公開履歴に合わせてください。