CHANGELOG
=========

全ての重要な変更はここに記録します。
フォーマットは Keep a Changelog に準拠します。
リリース日はリポジトリの現行状態に基づき推定しています。

Unreleased
----------

- なし

0.1.0 - 2026-04-13
------------------

Added
- 全体
  - 初回公開相当の機能群を追加。モジュールは自動売買エンジン（execution）、ポートフォリオ構築（portfolio）、リサーチ（research）、AIニューススコアリング（ai）、監視（monitoring）、設定管理（config）、ユーティリティ（utils）、ツール（tools）を含む。
  - パッケージバージョンを設定: kabusys.__version__ = "0.1.0"（src/kabusys/__init__.py）。

- 設定管理 (.env の自動読み込み / Settings)
  - プロジェクトルート検出機能を導入し、.git または pyproject.toml を基準に .env/.env.local を自動ロード（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。(src/kabusys/config.py)
  - .env パーサは export 形式やシングル/ダブルクォート、エスケープ、インラインコメントの取り扱いに対応。無効行は無視する実装。 (src/kabusys/config.py)
  - Settings クラスを提供し、環境変数の取得・バリデーションを統一（KABUSYS_ENV, PAPER_FILL_MODE, LOG_LEVEL 等）。データベースパスや PID ファイルパスなどの既定値を定義。 (src/kabusys/config.py)

- 実行エントリポイント
  - ExecutionEngine 起動スクリプトを追加。paper_trading 環境では paper_trading 専用 SQLite DB を使用して本番 DB と完全分離する挙動を実装（src/kabusys/run_execution.py）。
  - SystemMonitor ポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能。監視は環境に依らず本番 sqlite_path を使用する旨を明記。 (src/kabusys/run_monitoring.py)

- 監視関連
  - 監視 DB 初期化ユーティリティ（init_monitoring_db）を呼び出し冪等にテーブルを準備（run スクリプト内呼び出し）。 (src/kabusys/run_monitoring.py, run_execution.py)

- Utilities
  - プロセス優先度・CPU affinity 設定ユーティリティを追加。Windows と POSIX を抽象化して set_process_priority, set_cpu_affinity を提供。権限不足や未対応 OS の場合は警告を出して安全にスキップする実装。 (src/kabusys/utils/process_priority.py)

- Portfolio（ポートフォリオ構築）
  - 候補選定・重み計算関数を追加: select_candidates（スコア降順・タイブレーク処理）、calc_equal_weights、calc_score_weights（スコアが全て 0 の場合は等金額配分へフォールバック）。 (src/kabusys/portfolio/portfolio_builder.py)
  - セクター集中制限の適用関数を追加: apply_sector_cap（当日売却予定をエクスポージャーから除外、"unknown" セクターは制限適用を行わない）。(src/kabusys/portfolio/risk_adjustment.py)
  - 市場レジーム乗数 calc_regime_multiplier を追加（bull/neutral/bear をサポート。未知レジームは警告して 1.0 にフォールバック）。(src/kabusys/portfolio/risk_adjustment.py)
  - ポジションサイズ計算ロジック calc_position_sizes を追加。allocation_method に応じて risk_based / equal / score を実装。単元株（lot_size）丸め、1銘柄上限、aggregate cap（available_cash 超過時のスケーリング）、cost_buffer（手数料/スリッページ見積り）対応。残差の配分ロジックも実装。 (src/kabusys/portfolio/position_sizing.py)
  - portfolio パッケージの __all__ を整備して主要関数をエクスポート。 (src/kabusys/portfolio/__init__.py)

- Research（ファクター計算・特徴量探索）
  - モメンタム/ボラティリティ/バリューのファクター計算関数を追加（calc_momentum, calc_volatility, calc_value）。DuckDB の prices_daily / raw_financials を参照する SQL ベースの実装。各指標はデータ不足時に None を返す設計。 (src/kabusys/research/factor_research.py)
  - 将来リターン計算 calc_forward_returns を追加。可変ホライズンに対応し SQL でまとめて取得。 (src/kabusys/research/feature_exploration.py)
  - IC（Information Coefficient）計算（スピアマンのランク相関）calc_ic、ランク変換ユーティリティ rank、ファクター統計サマリ factor_summary を追加。標準ライブラリのみで実装。 (src/kabusys/research/feature_exploration.py)
  - research パッケージのエクスポートを追加。 (src/kabusys/research/__init__.py)

- AI: ニュースNLP（ニュースセンチメント）
  - raw_news を元に OpenAI API（gpt-4o-mini）で銘柄別センチメントスコアを生成し ai_scores テーブルへ書き込む処理を追加。チャンク（最大 20 銘柄）でのバッチ送信、トークン肥大化対策（記事数・文字数制限）、レスポンスバリデーション、スコアクリップ（±1.0）、リトライ（429・ネットワーク・5xx）を実装。部分成功時に既存スコアの保護を行う（対象コードのみ削除→挿入）。(src/kabusys/ai/news_nlp.py)
  - OpenAI API キー未指定時は ValueError を送出する挙動。タイムウィンドウ計算 calc_news_window を提供（JST ベースで前日15:00〜当日08:30 相当を UTC で扱う）。(src/kabusys/ai/news_nlp.py)

- Tools
  - Paper Trading 検証レポート生成ツールを追加。コマンドライン引数 (--from, --to, --db) に対応し、稼働率・注文成功率・送信率・レイテンシ等の集計と PASS/FAIL 判定を出力。閾値と判定基準を定義。DB が存在しない場合は分かりやすくエラー表示。 (src/kabusys/tools/paper_verification_report.py)

Changed
- 実行時のプロセス優先度設定を各起動スクリプトの最初に適用することで、実行中のプロセスが優先度設定の影響を受けるようにした（run_monitoring, run_execution で set_process_priority("high") を呼び出し）。 (src/kabusys/run_monitoring.py, src/kabusys/run_execution.py)

Fixed
- なし（初期リリース）

Deprecated
- なし

Removed
- なし

Security
- なし

Notes / Important behavioral details
- 監視プロセス（run_monitoring.py）は KABUSYS_ENV にかかわらず常に Settings.sqlite_path（本番監視 DB）を使用します。監視データは環境別に分離されませんので運用時は注意してください。
- ExecutionEngine の実行時に paper_trading 環境を使用する場合は PAPER_TRADING_SQLITE_PATH（または Settings.paper_sqlite_path のデフォルト data/paper_trading.db）が使用され、本番 DB と分離されます（run_execution.py）。
- MONITOR_POLL_INTERVAL 環境変数は整数秒でポーリング間隔を指定できます。1 未満や不正な値は警告してデフォルト 60 秒にフォールバックします（run_monitoring.py）。
- OpenAI を使ったニューススコアリングは API キー必須。キー未指定時は ValueError を返します（src/kabusys/ai/news_nlp.py）。
- process_priority や CPU affinity の設定は権限がない環境や未対応 OS では安全にスキップし、警告ログを出力します。

今後の予定（例）
- ポートフォリオ構築における銘柄別 lot_size サポート（stocks マスタ参照）や価格フォールバックロジックの強化。
- ニュース NLP の部分失敗時の再試行/ロールフォワード戦略の改善。
- 更なるユニットテストとドキュメントの拡充。

---

上記はコードベース内の実装とコメントに基づき推測してまとめた CHANGELOG です。詳細な変更履歴やリリース番号・日付の正確な決定はリポジトリのタグ付けやリリースポリシーに従って更新してください。