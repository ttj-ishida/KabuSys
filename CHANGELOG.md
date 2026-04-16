Keep a Changelog に準拠した変更履歴

すべての注目すべき変更をこのファイルに記載します。  
フォーマット: https://keepachangelog.com/ja/

## [Unreleased]

（なし）

## [0.1.0] - 2026-04-16

Added
- 初期公開: KabuSys パッケージの基本機能を実装。
  - パッケージメタ情報: バージョンを 0.1.0 に設定（src/kabusys/__init__.py）。
- 実行・運用スクリプトを追加。
  - 実行エンジン起動スクリプト: run_execution を追加。ExecutionEngine の起動、Paper Trading 用 DB 分離、停止フラグ・PID 管理、スレッド実行の監視を行う（src/kabusys/run_execution.py）。
  - 監視ループ起動スクリプト: run_monitoring を追加。SystemMonitor のポーリングループ、MONITOR_POLL_INTERVAL による間隔制御、停止フラグ検知を実装（src/kabusys/run_monitoring.py）。
- 設定管理モジュールを実装（src/kabusys/config.py）。
  - .env / .env.local の自動ロード（プロジェクトルート検知: .git または pyproject.toml）。
  - 複雑な .env 行のパース（export プレフィックス、クォート内エスケープ、コメント処理など）をサポート。
  - Settings クラスで環境変数をラップ（DB パス、Paper Trading 切替、監視閾値、KABUSYS_ENV 検証など）。
  - 自動ロード無効化用フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
- Portfolio 構築関連の純粋関数群を追加（src/kabusys/portfolio/*）。
  - 候補選定・重み計算: select_candidates, calc_equal_weights, calc_score_weights（等金額・スコア加重、スコア全0時のフォールバックロジック）。
  - リスク調整: apply_sector_cap（セクター上限適用、売却予定銘柄の除外対応）、calc_regime_multiplier（レジームに応じた乗数、未知レジームはログ出力のうえフォールバック）。
  - ポジションサイジング: calc_position_sizes（risk_based / equal / score の各方式、lot_size 単位丸め、aggregate cap のスケールダウンと端数処理を実装）。
- 研究・ファクター計算モジュールを追加（src/kabusys/research/*）。
  - calc_momentum, calc_volatility, calc_value：DuckDB を用いたファクター計算（MA200、ATR20、出来高・売買代金等）。
  - calc_forward_returns, calc_ic, factor_summary, rank：将来リターン・IC（スピアマン）・統計サマリ等のユーティリティ（外部ライブラリに依存せず実装）。
  - DuckDB SQL を駆使した効率的なスキャン範囲の制御と NULL/データ不足時の安全な扱い。
- AI ニュース NLP スコアリングモジュールを追加（src/kabusys/ai/news_nlp.py）。
  - raw_news / news_symbols から銘柄ごとに記事集約し OpenAI（gpt-4o-mini）へバッチ送信してセンチメント（-1.0〜1.0）を ai_scores へ書き込む設計。
  - バッチサイズ、最大再試行、指数バックオフ、レスポンス検証、スコアクリッピングなどのフェイルセーフ実装。
  - ニュース収集ウィンドウ（JST→UTC 変換）ユーティリティを実装。
- ツール: Paper Trading 向け検証レポート生成スクリプトを追加（src/kabusys/tools/paper_verification_report.py）。
  - コマンドラインから期間指定で paper_trading DB を解析し、稼働率 / 注文成功率 / 送信率 / レイテンシ（P95 等）を算出して PASS/FAIL 判定する。
  - デフォルト閾値（稼働率 99%、成立率 90%、送信率 95%、P95 200ms）を定義。
- ユーティリティ: プロセス優先度・CPU affinity 設定を実装（src/kabusys/utils/process_priority.py）。
  - Windows / POSIX（Linux, Darwin, FreeBSD）差分を吸収して nice/priority/affinity を設定。アクセス権限不足時はログでスキップ。
- DB 関連: monitoring 用テーブル初期化ユーティリティ（init_monitoring_db）を実行箇所に組み込み（run系スクリプトが起動時に監視テーブルを冪等に初期化）。

Changed
- なし（初期リリース）

Fixed
- なし（初期リリース）

Security
- OpenAI API キーの取得は明示的な引数または環境変数（OPENAI_API_KEY）を要求し、未設定時は例外を送出して誤動作を防止（src/kabusys/ai/news_nlp.py）。

Notes / Migration
- 環境変数について:
  - KABUSYS_ENV は "development" / "paper_trading" / "live" のいずれかを指定（大文字小文字は問わない）。無効な値は ValueError を送出。
  - PAPER_TRADING_SQLITE_PATH により Paper Trading 用 DB を分離可能。run_execution は paper_trading モード時に専用 DB を使用する。
  - MONITOR_POLL_INTERVAL で監視ポーリング間隔を上書き可能。正の整数でない場合はデフォルト 60 秒にフォールバック。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env 自動ロードを無効化できる。
- run_monitoring / run_execution はプロセス優先度を起動直後に "high" に設定しようと試みます。権限不足や未対応 OS の場合は警告ログが出力され、処理は継続します。
- Paper Trading に関する注意:
  - Paper Trading は本番 DB と物理的に分離する設計（data/paper_trading.db がデフォルト）。
  - paper_fill_mode（instant/partial/never/reject）でモックの約定挙動を制御。無効値は ValueError。

既知の制約
- 一部の DuckDB クエリは required テーブル（prices_daily, raw_financials, raw_news 等）の存在を前提とするため、対象テーブルが存在しない場合は OperationalError を捕捉して安全に N/A を返す設計になっている（tools のレポート等）。
- position_sizing の lot_size は現状グローバル定数扱いで銘柄別単位未対応（将来的に銘柄マスタに lot_size を持たせることを想定）。
- OpenAI 呼び出しは通信エラーやレート制限に対してリトライするが、API 側の停止等が長期化するとスコア付与が行われない可能性がある（フェイルセーフとして他データはそのまま維持）。

署名
- 実装元ファイル群: src/kabusys/*.py およびサブパッケージ内ファイル群

--- 
（本 CHANGELOG はリポジトリ内ファイルの実装内容から推測して作成しました。詳細な変更履歴や日付はコミットログを参照してください。）