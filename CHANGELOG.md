CHANGELOG
=========

このファイルは「Keep a Changelog」形式に準拠しており、重要な変更点を分かりやすく記録します。

フォーマットの解説: https://keepachangelog.com/ja/1.0.0/

Unreleased
----------

### Added
- run_monitoring 起動スクリプトを追加（src/kabusys/run_monitoring.py）
  - SystemMonitor のポーリングループを起動する CLI スクリプト。
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
  - 停止はプロジェクト直下の data/stop_requested.flag によるフラグ検出で安全に行う。
  - 監視は常に本番用 sqlite_path を使用して起動する仕様。

- run_execution 起動スクリプトを追加（src/kabusys/run_execution.py）
  - ExecutionEngine を起動する CLI スクリプト。
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、paper_trading 用の専用 SQLite DB（data/paper_trading.db をデフォルト）へ記録して本番 DB と完全分離。
  - 停止フラグ（data/stop_requested.flag）と PID ファイルによる制御を実装。
  - スレッドで engine.run_session をデーモン実行し、安全な停止手順を備える。

- 設定管理モジュールを導入（src/kabusys/config.py）
  - .env/.env.local の自動読み込み機能（プロジェクトルート自動検出）。
  - 読み込みの保護（OS 環境変数の上書きを防ぐ protected 設定）。
  - .env パーサーは export 構文、クォート内バックスラッシュエスケープ、インラインコメントの取り扱い等に対応。
  - Settings クラスでアプリ設定をプロパティとして提供（DB パス、Paper Trading 設定、閾値、環境判定等）。
  - 不正な値（例: KABUSYS_ENV / LOG_LEVEL / PAPER_FILL_MODE）に対して明示的に ValueError を送出し、設定ミスを早期検出。

- ポートフォリオ構築関連の純粋関数群を追加（src/kabusys/portfolio/*）
  - 候補選定・重み計算（portfolio_builder.py）
    - select_candidates, calc_equal_weights, calc_score_weights を実装。
    - スコアが全て 0 の場合は等配分へフォールバックし warning をログ出力。
  - セクター集中制限・レジーム乗数（risk_adjustment.py）
    - apply_sector_cap により既存保有比率が閾値を超えるセクターの新規候補除外。
    - calc_regime_multiplier によるレジームごとの投下資金乗数（bull/neutral/bear）。
  - 株数決定・投下資金スケール（position_sizing.py）
    - allocation_method（risk_based / equal / score）に基づく発注株数計算。
    - 単元（lot_size）丸め、per-position 上限、aggregate cap（利用可能現金）によるスケールダウン、端数配分ロジックを実装。

- リサーチ（研究）モジュールを追加（src/kabusys/research/*）
  - ファクター計算（factor_research.py）
    - momentum（1m/3m/6m リターン、MA200 乖離）、volatility（ATR20、出来高等）、value（PER/ROE）を DuckDB を用いて計算。
  - 特徴量探索ユーティリティ（feature_exploration.py）
    - 将来リターン calc_forward_returns、IC 計算 calc_ic、ファクター統計 summary 等を実装。
    - pandas 等に依存せず標準ライブラリのみで実装。
  - research パッケージのエクスポートを整備（src/kabusys/research/__init__.py）。

- AI ニュース NLP スコアリング機能（初期実装）（src/kabusys/ai/news_nlp.py）
  - raw_news から期間ウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）を集計し、OpenAI（gpt-4o-mini）へバッチ送信して銘柄ごとのセンチメント（-1.0〜1.0）を生成して ai_scores テーブルへ登録するフローを実装。
  - バッチサイズ、文字数上限、記事数上限、JSON Mode 出力を前提とした堅牢な設計。
  - 429/ネットワーク断/5xx に対する指数バックオフの再試行ロジックを備える。
  - OpenAI API キー未設定時に ValueError を送出して明示する。
  - （注）ファイル末尾で記事フェッチ処理が途切れているため、完全な実行パスは現状未完（下記 Known issues を参照）。

- ユーティリティを拡充（src/kabusys/utils/process_priority.py）
  - set_process_priority(level) により Windows/Linux/Mac の差分を吸収してプロセス優先度を設定。
  - set_cpu_affinity(cpu_count) による CPU アフィニティ固定機能を追加。
  - アクセス権限不足や未対応環境に対するワーニング処理を実装。

- 検証ツールを追加（src/kabusys/tools/paper_verification_report.py）
  - Paper Trading の検証レポート生成スクリプト（CLI）。
  - 稼働率・注文成功率・送信率・レイテンシ（P95）などを計算し、PASS/FAIL 判定を表示。
  - 日付フィルタ（--from / --to）と DB パス指定（--db / 環境変数）に対応。

### Fixed
- 環境変数読み込みの堅牢化（src/kabusys/config.py）
  - クォート内のバックスラッシュエスケープや export 形式を正しく処理することで .env パースの誤動作を低減。
  - 自動ロード時にプロジェクトルートが見つからない場合はスキップする安全策を追加。

- モニタリング・実行スクリプトの安全な停止/初期化処理を改善
  - init_monitoring_db を起動時に呼び出して監視テーブルを冪等に初期化（存在確認を保証）。
  - stop flag・pid file を使ったプロセス制御を安定化。

### Changed
- なし（初期リリース相当の追加が中心のため、破壊的変更は含まれない想定）。

### Known issues / Notes
- apply_sector_cap の価格欠損時の挙動（price が 0.0 の場合のエクスポージャー過少見積り）について TODO コメントあり。
- position_sizing では現状 lot_size を全銘柄共通で扱う。将来的には銘柄別 lot_size を渡す設計に拡張する予定（TODO コメント）。
- news_nlp.py はファイル末尾で article 集約関数呼び出しが途中で途切れており、記事取得部分（_fetch_articles 等）が未定義／未完の可能性がある。現状は設計と多くの処理（ウィンドウ算出・API 呼び出し・検証）を記述済みだが、完全実装の確認が必要。
- DuckDB の executemany に関する留意点（実装コメントあり）：空パラメータでの executemany を渡さない等の運用上の注意がある。
- set_process_priority / set_cpu_affinity は権限やプラットフォーム依存で失敗する可能性があり、失敗時はワーニングでスキップする実装。

0.1.0 - 2026-04-16
------------------
初回公開リリース（コードベースの初期機能群をリリース相当にまとめた想定）

### Added
- 上記 Unreleased に列挙した主要機能群を初期実装として追加:
  - 起動スクリプト: run_monitoring, run_execution
  - 設定管理: Settings、.env 自動読み込み・保護
  - ポートフォリオ構築: portfolio_builder, position_sizing, risk_adjustment
  - リサーチ: factor_research, feature_exploration、research パッケージ統合
  - AI ニュース NLP: 初期設計と API 呼び出し部分
  - ユーティリティ: process_priority（優先度・affinity 設定）
  - 検証ツール: paper_verification_report
  - パッケージメタ情報: __version__ = "0.1.0" を設定

### Fixed
- .env パースの堅牢化（コメント扱い・クォート内エスケープ等）を実装。
- モニタリング初期化と安全な停止処理を改善。

Deprecated
----------
- なし

Removed
-------
- なし

Security
--------
- OpenAI API キーは必須パラメータまたは環境変数（OPENAI_API_KEY）で明示的に指定する仕様とし、未設定時は ValueError を発生させることで意図しない外部アクセスを防止。

補足
----
- 各モジュール内に TODO / コメントで今後の改善点が明記されています（価格フォールバック、銘柄別 lot_size、news_nlp の最終実装等）。次回リリースではこれらの改善・完成を反映することを推奨します。