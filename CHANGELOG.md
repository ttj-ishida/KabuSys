Keep a Changelog
================

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。

＜注＞以下は提供されたソースコードから推測して作成した変更履歴です。実際のコミット履歴ではありません。

Unreleased
---------

- なし

[0.1.0] - 2026-04-17
--------------------

Added
- 初期リリース: KabuSys 基本機能群を追加。
  - 実行コンポーネント
    - run_execution.py: ExecutionEngine 起動スクリプト、スレッド実行・停止フラグ対応、紙 (paper_trading) 環境では専用 DB を使用する仕組みを実装。
    - BrokerClientFactory を通じたブローカークライアントの生成、OrderManager / OrderRepository / RiskManager / Reconciler の組み立てと ExecutionEngine の起動ロジックを実装。
  - 監視コンポーネント
    - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL 環境変数によるポーリング間隔上書き、停止フラグ検出、実行時にプロセス優先度設定を行う。
    - 監視 DB 初期化 (init_monitoring_db) を呼び出す処理を追加。
  - 設定管理
    - config.py: 環境変数/.env ローダー、.env パース（export プレフィックス・クォート・エスケープ・インラインコメント対応）、環境値の検証を備えた Settings クラスを実装。自動ロードの無効化フラグ (KABUSYS_DISABLE_AUTO_ENV_LOAD) をサポート。
  - ポートフォリオ構築
    - portfolio.portfolio_builder: 候補選定 (select_candidates)、等金額/スコア加重重み計算 (calc_equal_weights / calc_score_weights) を実装。
    - portfolio.position_sizing: 発注株数算出ロジック（risk_based / equal / score）、単元丸め、aggregate cap によるスケールダウン、cost_buffer を考慮した残差処理を実装。
    - portfolio.risk_adjustment: セクター上限適用 (apply_sector_cap)、マーケットレジーム乗数 (calc_regime_multiplier) を実装。
  - リサーチ / ファクター
    - research.factor_research: DuckDB を用いたモメンタム / ボラティリティ / バリュー系ファクター計算（SQL ウィンドウ関数利用）を実装。
    - research.feature_exploration: 将来リターン計算 (calc_forward_returns)、IC（Spearman）計算 (calc_ic)、ファクター統計サマリ (factor_summary)、ランク付けユーティリティ (rank) を実装。外部依存を使わない実装。
  - AI / ニュース NLP（下記参照）
    - ai.news_nlp: raw_news を集約して OpenAI API (gpt-4o-mini) に問い合わせ、銘柄ごとのセンチメントを ai_scores に格納する処理を実装（バッチ送信、リトライ、レスポンス検証、スコアクリッピング等の設計を含む）。
  - ツール
    - tools.paper_verification_report: Paper Trading 用検証レポート生成スクリプトを追加。稼働率・注文成功率・送信率・レイテンシ（P95）等を集計し PASS/FAIL 判定を行う CLI を提供。
  - ユーティリティ
    - utils.process_priority: プラットフォーム差（Windows / POSIX）を吸収したプロセス優先度設定および CPU affinity 設定ユーティリティを実装。アクセス権限不足などの失敗は警告でスキップする安全設計。

Changed
- デフォルト動作 / 分離ポリシー
  - run_monitoring: 監視は KABUSYS_ENV に関係なく本番用 sqlite_path を使用する設計に明示（監視データは本番 DB を参照）。
  - run_execution: paper_trading 環境向けに paper_sqlite_path を切り分け、Paper Trading と本番 DB を完全に分離。
- 設定ロード順序: OS 環境 > .env.local > .env の優先順位と、OS 環境を保護する protected オプションを導入。

Fixed
- .env パーサーの堅牢化（config._parse_env_line）
  - export キーワード対応、シングル／ダブルクォート内のバックスラッシュエスケープ対応、インラインコメントの取り扱いの改善。
  - 無効行や不正フォーマット行を無視する安全な実装。
- プロセス優先度設定の堅牢化（utils.process_priority）
  - 未対応 OS ではスキップして警告、アクセス拒否や未実装の属性に対して例外を捕捉して警告を出力することでクラッシュしないように。
- ExecutionEngine 起動前の停止フラグチェックを追加（既に停止フラグが立っている場合は起動せず終了）。
- init_monitoring_db 呼び出しを冪等に行い、監視テーブルが確実に存在するように。

Security
- Settings._require による必須環境変数チェックを導入。未設定時は早期に ValueError を送出して起動時エラーで露呈させる方針。

Notes / Known issues
- ai/news_nlp.py: OpenAI 連携の設計（バッチ処理、リトライ、レスポンス検証、部分成功時の部分更新戦略など）は実装思想が明確に記載されていますが、提供されたソースは途中で切れている箇所があり（ファイル末尾の一部が欠落）、完全実装状態かどうかは要確認です。
- position_sizing.calc_position_sizes の TODO: 将来的に銘柄別 lot_size のサポートが予定されている旨の注記あり。
- apply_sector_cap の価格欠損時の挙動に関する TODO コメント: price が 0.0 の場合にエクスポージャーが過少見積りされ得るため、将来的なフォールバック価格実装が検討中。
- DuckDB を用いるリサーチ系処理は prices_daily / raw_financials 等のテーブル定義・投入が前提。データ不足時に None を返す設計になっているため、運用時はデータ前処理と入力整備が必要。

未分類 / 開発メモ
- パフォーマンス設計（DuckDB でのウィンドウ関数利用、スキャン範囲のカレンダーバッファ等）が随所に見られ、実運用スケールを考慮した実装になっています。
- CLI ツールや起動スクリプトはログ出力（logging）を標準で行い、運用性を高める設計。

版权・ライセンス
- 本 CHANGELOG はソースコードからの推測に基づいて作成されています。実際の変更履歴はコミットログ（git）を参照してください。