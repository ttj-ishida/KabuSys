# Changelog

すべての注目すべき変更点を記録します。  
このファイルは「Keep a Changelog」規約に準拠しています。  

なお、本 CHANGELOG は与えられたコードベースから実装内容を推測して作成しています。

## [0.1.0] - 2026-04-17
初回公開リリース。

### 追加 (Added)
- パッケージ基盤
  - kabusys パッケージの基本を実装。バージョンは `__version__ = "0.1.0"` に設定。
  - パッケージ公開用の __all__ を設定（"data", "strategy", "execution", "monitoring"）。

- 環境設定 / ローダー
  - `kabusys.config.Settings` による環境変数ベースの設定管理を実装。
  - 自動 `.env` 読み込み機能を実装（プロジェクトルート検出: .git または pyproject.toml を基準）。
  - 読み込み順序: OS 環境 > .env.local > .env。`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` による無効化に対応。
  - `.env` パーサを厳密に実装（コメント・export、クォート、エスケープ対応）。
  - 各種設定プロパティを実装（DB パス、PID/kill フラグパス、閾値、ログレベル、環境種別等）。
  - 設定値のバリデーションを追加（`KABUSYS_ENV`, `PAPER_FILL_MODE`, `LOG_LEVEL` 等）。

- 実行 / 監視ランナー
  - `run_execution.py`：ExecutionEngine 起動スクリプトを実装。
    - KABUSYS_ENV が `paper_trading` の場合は paper_trading 専用 SQLite(DB: `PAPER_TRADING_SQLITE_PATH` または `data/paper_trading.db`) を使用し、本番 DB と分離。
    - Broker クライアントのファクトリ呼び出し、OrderRepository/OrderManager/RiskManager/Reconciler の組み立て、ExecutionEngine の起動（スレッド実行）を実装。
    - 停止フラグ（data/stop_requested.flag）による安全停止処理、PID ファイル経由の管理、タイムアウト付き join を実装。
    - RiskManager のデフォルト設定値（max_position_pct 等）を提供し、初期ポートフォリオ値に broker.get_available_cash() を使用。

  - `run_monitoring.py`：SystemMonitor ポーリングループ起動スクリプトを実装。
    - 環境変数 `MONITOR_POLL_INTERVAL` によるポーリング間隔上書き対応（デフォルト 60 秒。0 以下/不正値はデフォルトにフォールバックして警告ログ）。
    - 監視は KABUSYS_ENV にかかわらず本番の `sqlite_path` を使用する仕様に明記。
    - 停止フラグ（data/stop_requested.flag）検知でループを終了。
    - check_once() の例外はログ出力して次ポーリングへ継続。

- ユーティリティ
  - `kabusys.utils.process_priority`：プロセス優先度/CPU affinity 設定ユーティリティを実装。
    - Windows と POSIX（Linux, Darwin, FreeBSD）で適切に優先度を設定（psutil 使用）。
    - `set_process_priority(level)` による "high" / "normal" / "low" のサポートと入力検証。
    - `set_cpu_affinity(cpu_count)` による最初の N コアへピン留め機能。
    - 許可不足や未対応 OS の場合は警告ログを出してフォールバック。

- ポートフォリオ構築（純粋関数群）
  - `kabusys.portfolio.portfolio_builder`：
    - 候補選定 (select_candidates)、等重み（calc_equal_weights）、スコア加重（calc_score_weights）を実装。
    - calc_score_weights は全スコアが 0 の場合に等金額配分へフォールバックして警告を出力。
  - `kabusys.portfolio.risk_adjustment`：
    - セクター集中制限適用 (apply_sector_cap)。既存ポジションのセクターエクスポージャーを考慮して候補を除外。
    - 市場レジームに基づく乗数 (calc_regime_multiplier) を実装（bull/neutral/bear をサポート、未知レジームは 1.0 にフォールバックして警告）。
  - `kabusys.portfolio.position_sizing`：
    - 各銘柄の発注株数計算（allocation_method: "risk_based" / "equal" / "score"）。
    - 単元株（lot_size）丸め、1銘柄上限、aggregate cap（利用可能現金に対するスケーリング）、cost_buffer を考慮した保守的見積り。
    - aggregate cap 適用時の再配分ロジック（端数の分配を残差順で行う）を実装。
    - 価格欠損時のスキップ／ログ出力。

- 研究・リサーチ
  - `kabusys.research.factor_research`：
    - DuckDB を用いたファクター計算（モメンタム、ボラティリティ、バリュー）を実装。
    - mom_1m/3m/6m、MA200 乖離、ATR20、相対 ATR、20日平均売買代金、出来高比率、PER/ROE 等を計算。データ不足時は None を返す。
    - SQL ウィンドウ関数を用いた効率的な計算を実装。
  - `kabusys.research.feature_exploration`：
    - 将来リターン計算（calc_forward_returns）、IC（calc_ic）計算、rank ユーティリティ、factor_summary を実装。
    - pandas 等に依存せず純 Python + DuckDB で実装。入力検証を行う（horizon 範囲チェック等）。
  - `kabusys.research.__init__` に主要 API をエクスポート。

- AI / ニュース NLP
  - `kabusys.ai.news_nlp`：
    - raw_news を OpenAI API（gpt-4o-mini）でセンチメント分析し、銘柄ごとのスコアを ai_scores テーブルに書き込む機能を設計・実装（API キー解決・ウィンドウ計算・バッチ送信・リトライ・レスポンス検証・スコアクリップ等）。
    - ニュース収集ウィンドウ計算 (calc_news_window) を実装（JST ベース→UTC 変換）。例: target_date の前日 15:00 JST 〜 当日 08:30 JST。
    - バッチ処理、最大記事数/最大文字数トリム、429/ネットワーク/5xx に対する指数バックオフリトライの方針を実装。
    - 出力フォーマットの厳密な JSON バリデーション（{"results": [...] }）を要求。
    - （注）与えられたコードスナップショットの末尾で score_news の実装が途中で切れているため、完全な書き込み処理はスナップショット外で続く想定。

- ツール
  - `kabusys.tools.paper_verification_report`：
    - Paper Trading 用の検証レポート生成スクリプトを実装。CLI（--from/--to/--db）対応。
    - 稼働率、注文成功率、送信率、リスク却下数、レイテンシ（avg/max/P95）を集計して PASS/FAIL 判定を出力。
    - P95 計算、期間フィルタ、DB 存在チェック、SQLite の OperationalError に対する保険を実装。
  - `kabusys.tools.__init__` を追加（空）。

### 変更 (Changed)
- 実行時のプロセス優先度を起動直後に "high" へ設定するよう各起動スクリプトで統一 (`run_monitoring.py`, `run_execution.py`)。
- 監視ループの標準ポーリング間隔を 60 秒に設定（環境変数で上書き可能）。

### 修正 (Fixed)
- .env 読み込み時のファイル読み取り失敗に対して警告を出すようにし、処理の継続性を確保。
- DuckDB/SQLite 操作は各スクリプトで接続を最後に確実にクローズするようにした（finally ブロック）。

### 注意点 / 既知の制限 (Known issues / Notes)
- news_nlp.score_news のコードスナップショットが途中までの状態のため、実際の ai_scores への最終書き込み処理や一部エラーハンドリングはスナップショット外で続く想定です。
- apply_sector_cap 内で price が欠損（0.0）の場合にエクスポージャーが過少見積りされ、ブロック漏れが生じる可能性がある旨を TODO コメントで指摘。将来的に前日終値や取得原価でのフォールバックを検討する設計。
- position_sizing は現状全銘柄共通の lot_size（デフォルト 100）前提。将来的には銘柄別 lot_map を受け取る拡張が予定されている（TODO）。
- DuckDB で executemany に空パラメータを渡すと失敗する制約あり（news_nlp の設計コメントに注意喚起あり）。
- process_priority の優先度設定は権限不足や未対応プラットフォームでは実行されず、警告ログが出るが処理は継続する。

### セキュリティ (Security)
- OpenAI API キーや各種シークレットは環境変数で扱われ、`.env` 自動読み込みは OS 環境変数を保護する（protected set）実装になっている。ただし `.env` ファイル取り扱いは運用上の注意が必要。

## 既知の将来作業 (Unreleased / TODO)
- news_nlp の完全実装確認と統合テスト（API バッチ処理・部分失敗時の DB 保護挙動）。
- price 欠損時のフォールバック価格ロジック実装（apply_sector_cap の TODO）。
- 銘柄別の lot_size 管理対応（position_sizing の拡張）。
- テスト用の自動化（ユニット／統合）と CI 設定の確認。

---

この CHANGELOG はソースコードのコメントや実装から内容を推測して作成しています。実運用向けには追加のリリースノート整備、テスト結果、マイグレーション手順等の追記を推奨します。