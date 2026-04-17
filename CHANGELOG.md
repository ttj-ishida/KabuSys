CHANGELOG
=========

すべての重要な変更履歴を記録します。フォーマットは「Keep a Changelog」に準拠しています。

Unreleased
----------
- ai/news_nlp モジュールが途中で切れている（ファイル末尾が不完全）。OpenAI API 呼び出し後のレスポンス処理／DB 書き込みの続き実装が必要。
- 一部の TODO・拡張メモが残っている箇所あり（position_sizing の価格フォールバック、将来的な lot_size マスタ等）。運用前に確認を推奨。

0.1.0 - 2026-04-17
------------------

Added
- 基本機能の初回実装（ライブラリ全体の初期リリース相当）。
- 実行/監視起動スクリプト
  - run_execution.py: ExecutionEngine を起動する CLI スクリプトを追加。KABUSYS_ENV=paper_trading 時は専用の paper_trading DB を使用し、本番 DB と分離。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。停止はプロジェクトの data/stop_requested.flag ファイルで制御。
- 設定管理
  - config.py: 環境変数 / .env / .env.local 自動ロード機能を追加（プロジェクトルート検出: .git / pyproject.toml）。KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化対応。
  - Settings クラスを追加し、各種設定（DB パス、Paper Trading 設定、監視閾値、PID/フラグパスなど）をプロパティ経由で取得可能に。
  - PAPER_FILL_MODE、KABUSYS_ENV、LOG_LEVEL 等の入力検証を実装。
- DB / 分析基盤
  - DuckDB のパイプラインを前提とした research 用関数群を追加（factor_research.py, feature_exploration.py）。
    - モメンタム / ボラティリティ / バリュー等のファクター計算（calc_momentum, calc_volatility, calc_value）。
    - 前方リターン計算（calc_forward_returns）、IC（calc_ic）、ファクター統計サマリ（factor_summary）、rank ユーティリティ。
  - monitoring 用テーブル初期化ユーティリティを呼び出す仕組みを実装（init_monitoring_db の呼び出し場所を run_* に追加）。
- ポートフォリオ構築
  - portfolio パッケージを追加（pure functions）
    - portfolio_builder: シグナル選別と重み計算（select_candidates, calc_equal_weights, calc_score_weights）。
    - risk_adjustment: セクター上限適用（apply_sector_cap）、レジーム乗数（calc_regime_multiplier）。
    - position_sizing: 発注株数計算ロジック（calc_position_sizes）。risk_based / equal / score の配分方式をサポートし、単元（lot_size）丸め、aggregate cap によるスケールダウン、残差に基づく追加配分ロジックを実装。
- 実行時ユーティリティ
  - utils/process_priority.py: クロスプラットフォームのプロセス優先度設定と CPU affinity 設定を実装。Windows / POSIX に対応し、権限不足時は警告でスキップ。
- ツール
  - tools/paper_verification_report.py: Paper Trading 用検証レポート生成スクリプトを追加。稼働率、注文成功率/送信率、P95 レイテンシ等を計算して CLI 出力（PASS/FAIL 判定）。
- AI ニュース NLP（初期実装）
  - ai/news_nlp.py: raw_news を OpenAI にバッチ送信して銘柄ごとにセンチメントスコアを算出する設計を追加。バッチサイズ、トリム上限、ウィンドウ計算、リトライ戦略、結果バリデーション、スコアクリップ等の方針を実装。ただしファイル末尾が不完全のため一部処理が未実装。

Fixed / Improved
- .env パーサの堅牢化（config._parse_env_line）
  - export プレフィックス対応
  - シングル/ダブルクォート内のバックスラッシュエスケープ処理を考慮してクォート閉鎖を正しく検出
  - クォートなしの場合の inline コメント判定（直前が空白/タブのときのみコメント扱い）
  - ファイル読み込み失敗時に警告を出す（例外抑制で安全に動作）
- 環境変数パース時の上書きポリシーを明示（.env と .env.local の読込優先度、OS 環境変数保護）。
- MONITOR_POLL_INTERVAL の検証強化
  - 0 以下の値や数値でない値はデフォルト（60 秒）にフォールバックし、warning ログを出力。time.sleep に渡す不正値による例外発生を未然に防止。
- DB/監視周りの堅牢化
  - run_execution/run_monitoring で監視テーブルの存在を保証するため init_monitoring_db を起動時に呼び出す（冪等）。
  - run_execution は停止フラグを検出した場合に起動をキャンセル / 実行中に停止させるロジックを実装。
- position_sizing のスケールダウンアルゴリズム改良
  - 合計コスト超過時にスケールを適用し、lot_size 単位で端数を再配分するアルゴリズムを追加（再現性のため二次キーに code を使用して安定化）。
- research モジュールの欠損データ扱い
  - 過去データ不足時に None を返すことで downstream の誤動作を防止（ma200, atr 等のカウント条件をチェック）。

Security
- ai/news_nlp.score_news: OpenAI API キーが未設定の場合に ValueError を送出して明示的に失敗させる（無条件に空のキーで API 呼び出ししない）。
- Settings._require による必須環境変数の明示的エラー報告を実装（運用開始時の設定ミスを早期発見）。

Breaking Changes
- 本リリースは初期公開のため、既存の互換性破壊は想定していません。ただし下記点に注意してください:
  - run_monitoring は環境にかかわらず settings.sqlite_path（本番監視 DB）を使用する設計になっています。テスト目的で監視を分離したい場合は設定を確認してください。
  - position_sizing は現状で単元（lot_size）を全銘柄共通値として扱います。将来的な銘柄別 lot_size を導入する際は呼び出しシグネチャが変更される可能性があります（TODO コメントあり）。

Notes / Migration
- Paper Trading を行う場合は KABUSYS_ENV=paper_trading を設定してください。この場合、paper_sqlite_path（デフォルト data/paper_trading.db）に注文履歴等を記録します。本番 DB と明確に分離されます。
- .env の自動ロードはプロジェクトルートが検出できない環境ではスキップされます（パッケージ配布後の CWD に依存しない挙動）。
- ai/news_nlp は現状で未完の箇所があるため、本番運用前に完全実装と十分なエラーハンドリングの確認が必要です。

Acknowledgements
- 初期実装では DuckDB を分析基盤として強く想定しています。prices_daily / raw_financials / raw_news 等のテーブルスキーマを準備してから各分析関数を運用してください。