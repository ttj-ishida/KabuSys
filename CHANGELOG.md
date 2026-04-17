# Changelog

すべての重要な変更履歴はここに記録します。  
このファイルは Keep a Changelog 準拠の形式で記載しています。

リンクやコミット参照は含めていません — 変更はソースコードから推測してまとめています。

## [0.1.0] - 2026-04-17

### 追加
- 基本パッケージの初期リリース
  - パッケージ名: kabusys、バージョン: 0.1.0 (src/kabusys/__init__.py)
- 実行・監視ランナー
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。環境変数に応じて paper_trading 用の SQLite を分離して使用（data/paper_trading.db がデフォルト）。プロセス優先度設定、PID ファイル、停止フラグの監視、バックグラウンドスレッドでのエンジン実行ロジックを提供。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。停止フラグ検知でループ終了。
- 設定管理
  - config.py: .env 自動ロード機能を実装（プロジェクトルートの検出: .git または pyproject.toml）。.env/.env.local の読み込み順序、export 形式・クォート・コメント対応のパーサ実装。KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応。
  - Settings クラスを提供し、環境変数の集中管理（API トークン、DB パス、監視閾値、ログレベル、環境判定など）。各プロパティに入力検証（例: KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE）。
- ツール
  - tools/paper_verification_report.py: Paper Trading 用の検証レポート生成ツールを追加。稼働率、注文成功率、送信率、レイテンシ（平均・最大・P95）などを算出し、閾値に基づく PASS/FAIL 判定を表示。コマンドライン引数で期間指定と DB パス指定が可能。
- ポートフォリオ構築ライブラリ
  - portfolio/portfolio_builder.py: 候補選定（select_candidates）、等配分・スコア加重（calc_equal_weights, calc_score_weights）を追加。スコア合計が 0 の場合は等配分にフォールバック。
  - portfolio/risk_adjustment.py: セクター集中上限の適用（apply_sector_cap）と市場レジームに応じた乗数算出（calc_regime_multiplier）を追加。
  - portfolio/position_sizing.py: 発注株数決定ロジック（risk_based / equal / score）、単元 (lot_size) による丸め、per-position 上限、全体投下額の aggregate cap と縮退時のスケールダウン + 端数再配分アルゴリズムを実装。
  - portfolio/__init__.py: 主要関数をパッケージとしてエクスポート。
- ユーティリティ
  - utils/process_priority.py: プロセス優先度設定ユーティリティを追加（Windows / POSIX 差分吸収）。CPU affinity 設定関数 set_cpu_affinity を追加。
- リサーチ関連
  - research/factor_research.py: Momentum / Volatility / Value のファクター計算関数を実装（DuckDB 接続を受け取り prices_daily / raw_financials を参照）。MA200・ATR20・各種リターン等を算出。
  - research/feature_exploration.py: 将来リターン計算、IC（Spearman ランク相関）計算、ファクター統計サマリ等を実装。外部依存を極力抑え、標準ライブラリのみで実装。
  - research/__init__.py: 上記関数群と zscore_normalize をエクスポート。
- AI / ニュース NLP
  - ai/news_nlp.py: raw_news を OpenAI API（gpt-4o-mini 想定）でセンチメント評価し、銘柄ごとの ai_scores を更新する処理を追加（処理設計・定数・ウィンドウ計算・バッチ送信・リトライ・レスポンス検証・スコアクリッピングなどを設計）。OpenAI API キーの解決およびエラーハンドリング方針を定義。

### 変更（設計上の改善・注釈）
- DB 周り
  - 監視機能 init_monitoring_db を起動フローで必ず呼ぶことで監視テーブルの存在を保証（冪等）。
  - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する設計に明示（run_monitoring.py）。
- 環境変数読み込み
  - .env のパーサはクォート内のバックスラッシュエスケープ、export プレフィックス、インラインコメント取り扱い、.env.local による上書き等をサポートし、OS 環境変数は保護（protected）されるよう実装。
- ロギングとフォールトトレランス
  - run_monitoring のポーリング内で check_once() の例外をキャッチしてログに出力し、次ポーリングに進むフェイルセーフを実装。
  - run_execution は起動時に停止フラグを検査し、既に停止フラグがある場合は起動をスキップする仕様を採用。
- ポートフォリオ／注文ロジックの現実対応
  - position_sizing の aggregate cap は cost_buffer を加味して保守的に見積もるようになっている。端数分配は lot_size 単位で残差が大きい順に追加配分するアルゴリズムを導入。
  - apply_sector_cap は sector_map にないコードを "unknown" 扱いし、unknown セクターは上限適用対象外とする（注: price が 0 の場合の評価不足に関する TODO コメントあり）。
- research モジュールの堅牢化
  - factor_research と feature_exploration の実装はデータ不足時に None を返す等の安全策を講じている。calc_ic は ties（同順位）を平均ランクで扱う実装でスピアマン ρ の算出を安定化。

### 修正（バグ修正相当・バリデーション追加）
- 環境変数の妥当性チェックを強化
  - KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE の値検証を追加し、不正値時に ValueError を送出するようにした。
- MONITOR_POLL_INTERVAL の扱いを改善
  - 環境変数からの文字列→整数変換で不正値（0以下や非数）を検出すると警告を出し、デフォルトにフォールバックする実装を追加。0 や負値が time.sleep に渡って ValueError を起こすのを防止。
- process_priority 周りの例外処理強化
  - psutil の AccessDenied 等で失敗した場合は警告ログを残して処理を継続するようにした（起動失敗の致命化を回避）。

### 既知の注意点 / TODO
- price が欠損（0.0）の場合のエクスポージャーや position sizing の評価が過小見積りになる可能性がある。将来的に前日終値や取得原価などのフォールバック価格を用いる改善案がコメントとして残されている（portfolio/risk_adjustment.py）。
- ai/news_nlp.py は外部 API を利用する重要箇所のため、キー未設定時の明示的エラーやリトライ設計はされているが、実運用でのレート制限・コスト等の監視が必要。
- DuckDB / SQLite のクエリはテーブル存在や構造に依存するため、migration やスキーマ管理が適切に行われていることが前提。

---

以上がこのコードベースから推測できる主な変更点・追加機能です。必要であれば、各ファイルごとの詳細な変更点や設計意図をより細かく分割して追記できます。