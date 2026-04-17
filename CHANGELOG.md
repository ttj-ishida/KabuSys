CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠しています。  
重要な変更点はカテゴリ別に記載しています（Added / Changed / Fixed / Deprecated / Removed / Security）。

Unreleased
----------

Added
- run_monitoring スクリプトを追加（src/kabusys/run_monitoring.py）。
  - SystemMonitor のポーリングループを起動するエントリポイント。
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト: 60秒）。不正値はデフォルトにフォールバックして警告を出力。
  - 停止制御用の stop_requested.flag を監視し、検知でループを終了。
  - プロセス優先度を起動時に "high" に設定。

Changed
- run_monitoring: Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用するよう明示。
- 設定読み込みロジックの説明・挙動を明確化（src/kabusys/config.py）。
  - .env / .env.local の自動読み込み順序（OS 環境変数 > .env.local > .env）と無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD を説明。
  - .env パーサを強化：export KEY= 形式のサポート、クォート文字とバックスラッシュエスケープの正しい扱い、インラインコメントの扱い改善。
  - protected パラメータにより既存 OS 環境変数の上書きを防止する仕組みを導入。
- Settings に多数のプロパティを整理・追加（データベース・監視・システム設定関連）。
  - PAPER_FILL_MODE のバリデーション（有効値: "instant" | "partial" | "never" | "reject"）。
  - paper_trading 用 SQLite パス（PAPER_TRADING_SQLITE_PATH）を明示的に分離。
  - 監視用の PID / kill flag /閾値（CPU/MEM/DISK）等を Settings 経由で取得可能に。
- run_execution スクリプトを追加／改善（src/kabusys/run_execution.py）。
  - ExecutionEngine 起動スクリプト。KABUSYS_ENV=paper_trading の場合は paper_trading 用の専用 SQLite DB を使用して本番 DB と完全分離。
  - BrokerClientFactory を利用してブローカークライアントを選択。
  - OrderRepository / OrderManager / RiskManager / Reconciler を組み立て、ExecutionEngine をスレッドで実行。stop flag を検知すると安全に停止。
  - RiskManager のデフォルト設定（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）を設定。
- utils/process_priority.py を追加（src/kabusys/utils/process_priority.py）。
  - Windows と POSIX を吸収したプロセス優先度設定（set_process_priority）。
  - CPU affinity を設定する set_cpu_affinity を追加（psutil ベース）。権限不足や未対応環境では警告を出してスキップ。
- portfolio 関連モジュールを追加（src/kabusys/portfolio/*）。
  - 銘柄選定: select_candidates, calc_equal_weights, calc_score_weights。
  - セクター露出制御: apply_sector_cap（unknown セクターは上限適用対象外）。
  - レジーム乗数: calc_regime_multiplier（未知レジーム時は警告を出して 1.0 でフォールバック）。
  - ポジションサイズ算出: calc_position_sizes（risk_based / equal / score の各配分方式、lot_size 単位丸め、aggregate cap と cost_buffer を考慮したスケーリング）。
- research モジュールを追加（src/kabusys/research/*）。
  - factor_research: calc_momentum, calc_volatility, calc_value — DuckDB の prices_daily / raw_financials を参照してファクターを計算。
  - feature_exploration: calc_forward_returns, calc_ic (Spearman rank)、factor_summary, rank — 外部ライブラリに依存しない実装。
  - DuckDB を前提とした設計（SQL + Python での実装）。
- AI ニュース NLP スコアリング基盤を追加（src/kabusys/ai/news_nlp.py）。
  - raw_news / news_symbols を集約して OpenAI (gpt-4o-mini) でセンチメント（-1.0〜1.0）を生成して ai_scores に格納する設計。
  - バッチ処理、トークン肥大化対策（1 銘柄あたりの最大記事数／文字数）、リトライ（指数バックオフ）、レスポンス検証、スコアクリップ等を想定した堅牢設計。
  - API キー未設定時は明示的にエラーを返す。
  - （注）score_news の実装は途中で切れているため、未完成箇所あり。部分実装はフェイルセーフ設計を意識。
- tools/paper_verification_report を追加（src/kabusys/tools/paper_verification_report.py）。
  - Paper Trading の検証レポートを生成する CLI スクリプト（--from / --to / --db オプション）。
  - システム稼働率、注文成功率、送信率、P95 レイテンシ等を算出し PASS/FAIL 判定を行う。DB が存在しない場合やテーブルがない場合は N/A または 0 として扱い安全に終了。
  - レポート基準値（稼働率 99%, 成功率 90%, 送信率 95%, P95 <= 200 ms）を定義。

Fixed
- .env パーサ周りのロバストネス向上（コメント処理、クォート内のエスケープ処理、export 形式のサポート）。これにより .env の誤解析による設定不整合を低減。
- position_sizing のスケーリングロジックで lot_size 単位の丸め・残余配分を追加し、available_cash 超過時の再配分をより安定化。
- calc_score_weights: 全スコアが 0.0 の場合は等金額配分にフォールバックし警告を出力。

Security
- OpenAI API キーは引数または環境変数 (OPENAI_API_KEY) を必須扱いにして、未設定時は ValueError を送出。キーの自動漏洩を防ぐためログには出力しない設計。

Known issues / TODO
- src/kabusys/ai/news_nlp.py の score_news 実装が途中で切れている（fetch と送信処理の残りが未記載）。本番運用前に完了および E2E テストが必要。
- apply_sector_cap の価格欠損（price == 0.0）の扱いに注釈あり（現在は露出を過少見積もる可能性があるため将来的にフォールバック価格を検討）。
- CPU affinity / プロセス優先度設定は権限に依存するため、権限不足時はスキップされログに警告が出る設計。運用時は権限確認が必要。

[0.1.0] - 2026-04-17
--------------------
Initial release

Added
- プロジェクト初期リリースとして以下の主要機能を提供:
  - 自動売買システムのコア構成要素（ExecutionEngine 含む）と起動スクリプト（run_execution）。
  - システム監視用スクリプト（run_monitoring）と監視データベース初期化ユーティリティ。
  - Portfolio construction ライブラリ（選定・重み付け・ポジションサイズ・リスク調整）。
  - Research ライブラリ（ファクター計算: Momentum/Volatility/Value、将来リターン、IC、統計サマリー）。
  - AI ニュース NLP スコアリングの基盤（OpenAI API 利用設計）。
  - Paper Trading 検証レポート生成ツール（CLI）。
  - 設定管理モジュール（.env 自動ロード、各種 Settings プロパティ）。
  - process_priority / CPU affinity ユーティリティ（psutil ベース）。
  - DuckDB を用いた分析ワークフローを前提とした SQL + Python 実装。

Changed
- パッケージ初期構成、モジュールエクスポートの定義（kabusys.__init__.py に __version__ と __all__）。

Fixed
- 初期実装段階での既知バグ修正（.env パース、スコア重み計算のフォールバックなど）。

Notes
- 本バージョンは「基盤実装・アルゴリズム部の純粋関数群と起動スクリプト」を中心とした初期リリースです。AI の外部 API 呼び出し部分や ExecutionEngine の詳細な動作は運用前に環境依存設定・テストが必要です。