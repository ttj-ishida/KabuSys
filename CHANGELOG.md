CHANGELOG
=========

すべての重要な変更は、このファイルに記録します。フォーマットは "Keep a Changelog" に準拠します。
慣例:
- バージョン見出しは [X.Y.Z] — YYYY-MM-DD
- セクション: Added, Changed, Fixed, Removed, Security（該当があれば）

[Unreleased]
-----------

- 今後の変更を記載するセクション（未リリースの変更点）。

[0.1.0] — 2026-04-17
-------------------

Added
- 初回リリース。以下の主要機能とユーティリティを追加。
  - 実行 / 監視関連
    - run_execution: ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV=paper_trading 時は paper_trading 用の SQLite DB を使用する仕組みを実装（本番 DB と分離）。停止フラグ / PID 管理に対応。
    - run_monitoring: SystemMonitor ポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能。停止フラグ検出で安全に終了。
  - 設定管理
    - config.Settings: 環境変数を集約する Settings クラスを実装。DB パス、Paper Trading 設定、監視閾値、ログレベル、実行環境判定（development/paper_trading/live）など多数のプロパティを提供。
    - 自動 .env ロード機能を実装（プロジェクトルートを .git/pyproject.toml から探索）。.env と .env.local の読み込み順序と OS 環境変数保護をサポート。
    - .env パーサを強化: export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの取り扱いに対応。
  - 実行ユーティリティ
    - utils.process_priority: Windows / POSIX を吸収するプロセス優先度設定と CPU affinity 設定を提供。権限不足や未対応プラットフォーム時には安全にスキップして警告を出力。
  - ポートフォリオ構築
    - portfolio.portfolio_builder: シグナル選定 (select_candidates)、等金額配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights) を実装。
    - portfolio.risk_adjustment: セクター集中制限適用 (apply_sector_cap)、市場レジームに応じた乗数計算 (calc_regime_multiplier) を実装。未知レジームのフォールバック挙動を明記。
    - portfolio.position_sizing: 銘柄ごとの発注株数算出ロジックを実装（risk_based / equal / score）。単元株丸め、1銘柄上限、aggregate cap によるスケーリング、手数料・スリッページ用の cost_buffer をサポート。
  - リサーチ / ファクター
    - research.factor_research: Momentum / Volatility / Value ファクター計算を DuckDB SQL ベースで実装。MA200乖離、ATR20、20日平均売買代金、PER/ROE などを算出。
    - research.feature_exploration: 将来リターン計算 (calc_forward_returns)、IC（スピアマンランク相関）計算 (calc_ic)、ファクター統計サマリー (factor_summary)、ランク関数 (rank) を実装。外部ライブラリに依存しない純 Python 実装。
  - ニュース NLP（AI）
    - ai.news_nlp: raw_news を OpenAI API（gpt-4o-mini を想定）で銘柄別にスコア化するスクリプトを追加。バッチ処理、最大記事/文字数トリム、リトライ（429/5xx/タイムアウト）、レスポンス検証、スコアクリッピング（±1.0）、部分成功時のテーブル更新戦略等を実装。ニュース収集ウィンドウ計算ユーティリティ（JST → UTC 変換）を提供。
  - ツール
    - tools.paper_verification_report: Paper Trading 用の検証レポート生成 CLI を追加。期間指定（--from/--to）と DB パス指定（--db）をサポート。稼働率・注文成功率・送信率・P95 レイテンシ等を算出し、PASS/FAIL を判定する基準値を提供。P95 計算やデータ欠損時の挙動を明確化。
  - データアクセス
    - monitoring.monitoring_db: 監視用テーブル初期化ユーティリティを追加（init_monitoring_db を使用して冪等に初期化）。
  - パッケージ化
    - kabusys.__init__ に __version__="0.1.0" を追加し、主要サブパッケージのエクスポートを定義。

Changed
- 設計方針の明示化:
  - Research / AI / Portfolio モジュールは本番 API や発注系へアクセスしない（DuckDB / メモリ内計算のみ）という設計を強調。ルックアヘッドバイアスを避けるため、date/datetime の直接参照を避ける実装方針を採用。

Fixed
- 各種エッジケースの安全化:
  - .env ローダー: ファイル読み込み失敗時に警告を出して継続するように修正。
  - calc_score_weights: 全銘柄のスコア合計が 0.0 の場合は等金額配分にフォールバックして警告を出すように修正。
  - research.feature_exploration.calc_ic / rank: ties の処理（平均ランク）を明確化し、浮動小数丸め誤差対策を追加。
  - position_sizing: 価格欠損（None/0）や単元未満の処理を安全にスキップするロジックを追加。aggregate cap スケーリング後の再配分で再現性を確保するため残差のソート基準を安定化。
  - tools.paper_verification_report: DB のテーブル欠損（OperationalError）をハンドリングし、レポート生成を中断せず可能な指標のみ出力するように改善。P95 計算で空リストを扱う処理を追加。
  - utils.process_priority: 非サポート OS や権限不足時に警告を出して安全にスキップするように修正。

Security
- OpenAI API キーの取り扱い:
  - ai.news_nlp.score_news は api_key 引数または環境変数 OPENAI_API_KEY を必須にし、未設定時は明示的にエラーを返す（誤設定による意図しない外部呼び出しを防止）。

Notes / Implementation details
- Paper Trading 分離:
  - 実行スクリプトは paper_trading 環境では専用 SQLite（デフォルト data/paper_trading.db）を使用し、本番データベースと完全に分離することでテスト/検証を容易にしています。
- 監視データベース:
  - run_monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を参照して監視データを記録します（監視データは運用環境の状態把握用）。
- ローカル .env の自動読み込み:
  - デフォルトでプロジェクトルートを探して .env/.env.local を自動ロードします。テスト等で無効化するため KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を利用可能。
- DuckDB を利用:
  - リサーチ・AI モジュールは DuckDB 接続を受け取り SQL を主体に計算する設計（高速な分析処理と一貫性のため）。

Acknowledgements
- 初回リリースに関わる多数のユーティリティ・アルゴリズムを含むため、追加のテスト（特に edge-case と API エラー処理）を推奨します。

--- 
（以降のバージョンでは、API モックの詳細、実行エンジンのフェイルオーバー、単体テスト追加、ドキュメント整備等の変更を記載してください。）