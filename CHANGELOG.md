CHANGELOG
=========

この CHANGELOG は Keep a Changelog の形式に準拠しています。
リリースノートはコードベース（src/ 以下）の実装内容から推測して作成しています。

Unreleased
----------

（現在未リリースの変更はありません）

[0.1.0] - 2026-04-13
-------------------

初回公開リリース — 基本機能実装とユーティリティ群を追加。

Added
- 全体
  - パッケージの初期バージョンを設定（__version__ = "0.1.0"）。
  - logging を利用した基本的な情報出力を導入。
- 起動スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60秒）。
    - 監視用 DB は環境にかかわらず本番 sqlite_path を使用する仕様。
    - プロセス優先度を起動時に "high" に設定する処理を組み込み。
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用の SQLite（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）を使用し、本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成と、Engine/OrderManager/Reconciler/RiskManager の組み立てを行いセッションを実行。
    - 起動時にプロセス優先度を "high" に設定。
- 設定管理
  - config.py
    - .env / .env.local の自動読み込み機構を導入（プロジェクトルートを .git または pyproject.toml から検出）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
    - export KEY=val 形式やクォートされた値、インラインコメントの扱いなどを考慮した .env パーサー実装。
    - Settings クラスで多数の環境設定プロパティを提供（DB パス、API トークン、PID ファイル、しきい値、環境種別判定等）。
    - KABUSYS_ENV / LOG_LEVEL / PAPER_FILL_MODE の値検証を実装（不正値時は例外を投げる）。
- ポートフォリオ構築
  - portfolio/portfolio_builder.py
    - 候補選別（select_candidates）、等割合配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を実装。
    - スコアが全て 0 の場合は等割合にフォールバックし警告を出力。
  - portfolio/risk_adjustment.py
    - セクター集中制限（apply_sector_cap）と市場レジーム乗数（calc_regime_multiplier）を実装。
    - "unknown" セクターはセクター上限のチェック対象外にする挙動を採用。
    - 未知レジームの扱いは警告して 1.0 でフォールバック。
  - portfolio/position_sizing.py
    - allocation_method（"risk_based" / "equal" / "score"）に基づく株数決定ロジックを追加。
    - 単元（lot_size）丸め、per-position 上限、aggregate cap によるスケーリング、残差分の分配アルゴリズムを実装。
    - price 欠損時にスキップする安全策やコストバッファ考慮を実装。
- 研究・リサーチ
  - research/factor_research.py
    - Momentum / Volatility / Value ファクター計算を DuckDB を使った SQL ベースで実装（prices_daily / raw_financials を参照）。
    - MA200、ATR20、各種リターン（1M/3M/6M）などを取り扱う。
  - research/feature_exploration.py
    - 将来リターン calc_forward_returns、IC（calc_ic）、rank、factor_summary を実装（外部依存無し、標準ライブラリのみ）。
    - rank は同順位を平均ランク扱いにし丸めで ties の検出漏れを防ぐ実装。
  - research パッケージの __init__.py で主要関数をエクスポート。
- AI / ニュース
  - ai/news_nlp.py
    - raw_news を OpenAI（gpt-4o-mini）でバッチスコアリングし ai_scores テーブルへ書き込む機能を実装。
    - タイムウィンドウ計算（JST 基準で前日 15:00 ～ 当日 08:30）と記事集約ロジックを実装。
    - バッチサイズ（20件）での送信、トークン肥大化対策（記事数・文字数上限）、429/5xx/ネットワーク系のリトライ（指数バックオフ）を実装。
    - レスポンスの厳格な JSON バリデーション、スコアの ±1.0 クリップ、部分失敗時に既存スコアを保護して更新する実装方針。
- ツール
  - tools/paper_verification_report.py
    - Paper Trading 用検証レポート生成スクリプトを追加（CLI: --from/--to/--db）。
    - 稼働率、注文成功率、送信率、P95 レイテンシなどを集計して判定（PASS/FAIL）を出力。
    - P95 計算、日時フィルタ作成、DB が存在しない/テーブルが無い場合のフォールバックを実装。
- ユーティリティ
  - utils/process_priority.py
    - Windows / POSIX（Linux, Darwin, FreeBSD）を吸収するプロセス優先度設定関数 set_process_priority を実装。
    - CPU affinity を設定する set_cpu_affinity を実装（引数検証・例外時は警告でスキップ）。
    - 権限不足等の例外は警告出力して処理を継続する堅牢化。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Deprecated
- （初回リリースのため該当なし）

Removed
- （初回リリースのため該当なし）

Security
- OpenAI API キーは引数または環境変数 OPENAI_API_KEY で明示的に渡す必要がある旨を明記。
- 設定値の自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能（テスト用途の配慮）。

Notes / Known behaviors / Breaking changes
- 監視処理（run_monitoring）は「環境にかかわらず」Settings.sqlite_path（本番監視 DB）を使用する仕様になっているため、paper_trading 環境でも監視データが本番 DB に記録される点に注意が必要（意図的な設計）。
- 実行エンジン（run_execution）は paper_trading 環境時に paper_trading 用の SQLite を使用して本番 DB と完全分離する設計。
- .env パーサーは export 付き・クォート付き・インラインコメント等に対応するが、非常に特殊な .env の書式は想定外の挙動をする可能性がある。
- process_priority の設定は権限やプラットフォーム依存のため、失敗時はログに警告を残してスキップする。CPU affinity の設定も同様。
- ai/news_nlp の OpenAI 呼び出しでネットワーク障害やレート制限が生じた場合は再試行を行うが、最終的にスコアが取れなかった銘柄は更新されない（他銘柄は影響を受けないよう部分更新戦略を採用）。

以上。必要であれば各項目をさらにモジュール別に展開して詳細（関数シグネチャ、環境変数一覧、既知の TODO/改善点等）を追記します。