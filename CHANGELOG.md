CHANGELOG
=========

すべての変更は Keep a Changelog のフォーマットに準拠しています。
※この履歴は、提示されたソースコードから推測して作成したものであり、
実際のコミット履歴とは異なる場合があります。

Unreleased
----------

Added
- 実行用スクリプトを追加
  - run_execution.py: ExecutionEngine を起動するエントリポイントを実装。KABUSYS_ENV=paper_trading の場合は paper_trading 用の専用 SQLite DB を使用する（data/paper_trading.db をデフォルト）。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを実装。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。停止はプロジェクト内 data/stop_requested.flag によるファイルフラグで制御。

- 設定管理
  - config.py: .env/.env.local の自動読み込み機能を追加（OS 環境変数を上書きしない保護機能付き）。.git または pyproject.toml を辿ってプロジェクトルートを検出する実装。環境変数のパースはシングル／ダブルクォートや export プレフィックス、インラインコメントに対応。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py: シグナル候補選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を実装。スコア合計が 0 の場合は等金額配分へフォールバックして警告を出す。
  - portfolio/risk_adjustment.py: セクター集中上限チェック（apply_sector_cap）と市場レジームに応じた乗数（calc_regime_multiplier）を実装。unknown セクターは上限適用外。
  - portfolio/position_sizing.py: allocation_method（risk_based / equal / score）に基づく株数決定ロジックを実装。単元株（lot_size）丸め、aggregate cap によるスケーリング、cost_buffer を使った保守的コスト見積りと残余配分ロジックを含む。

- リサーチ（DuckDB ベース）
  - research/factor_research.py: Momentum / Volatility / Value ファクター計算を実装（prices_daily, raw_financials を参照）。ウィンドウバッファを取ることで週末や祝日を吸収する設計。
  - research/feature_exploration.py: 将来リターン計算（calc_forward_returns）、IC（calc_ic）、ファクターサマリー（factor_summary）および rank 関数を実装。外部ライブラリに依存せず純粋に標準ライブラリと DuckDB を使用する方針。
  - research/__init__.py: 主要関数と zscore_normalize（data.stats 由来）を公開。

- AI ニュース NLP（設計と一部実装）
  - ai/news_nlp.py: raw_news から銘柄別にニュースを集約して OpenAI（gpt-4o-mini, JSON Mode）へバッチ送信し、ai_scores テーブルへ書き込む処理を設計・部分実装。APIキー解決、ウィンドウ計算（JST → UTC 変換）、記事トリミング（最大記事数・文字数）やリトライ方針（429/ネットワーク/5xx の指数バックオフ）などが含まれる。

- ツール
  - tools/paper_verification_report.py: Paper Trading 用の検証レポート生成スクリプトを追加。稼働率・注文成功率・送信率・レイテンシ（P95）などの指標を計算し PASS/FAIL を判定するしきい値を定義。コマンドラインから期間指定や DB パス指定が可能。

- ユーティリティ
  - utils/process_priority.py: プロセス優先度の設定（Windows と POSIX を抽象化）と CPU affinity 設定機能を追加。権限がない場合は警告を出して安全にフォールバック。

Changed
- パッケージメタ
  - __init__.py にバージョン __version__ = "0.1.0" を定義。パッケージ公開に必要な最低情報を追加。

Fixed / Improved
- DB 初期化と接続
  - run_* スクリプトは monitoring 用テーブルの存在を保証するため init_monitoring_db を呼び出す（冪等処理）。
  - duckdb と sqlite を併用するアーキテクチャを採用し、分析系（DuckDB）と運用系（SQLite）を役割分離。

- 設定バリデーション
  - Settings クラスで環境変数の検証（PAPER_FILL_MODE, KABUSYS_ENV, LOG_LEVEL 等）を実装し、不正値は ValueError で早期検出。

- 安全性・耐障害性
  - run_monitoring のポーリングループ内で check_once() が例外を出してもログに残して次ループへ継続するようにして、監視プロセスが停止しないように設計。
  - ai/news_nlp の設計では API 失敗時に部分失敗で他データを保護するため、書き込み時に対象コードを限定して置換する戦略を採用（DELETE→INSERT の範囲を限定）。

Removed
- なし（このリリースでは削除は確認できない）

Security
- OpenAI API キーは明示的に引数または環境変数 OPENAI_API_KEY から解決し、未設定時は ValueError を投げる方針になっている（誤って空のキーを渡して処理を続けることを防止）。

Known issues / TODO / Work in progress
- ai/news_nlp.py は提示されたコードが途中で切れており、記事取得・バッチ送信・レスポンス処理・DB 書き込みの完全実装が未完の可能性あり。
- position_sizing.calc_position_sizes:
  - price が欠損（0.0）の場合にエクスポージャーが過小評価される旨の TODO コメントあり。前日終値や取得原価でのフォールバックなど拡張の余地あり。
  - 将来的には銘柄ごとの lot_size をサポートする拡張が予定されている（現状はグローバルな lot_size）。
- risk_adjustment.calc_regime_multiplier:
  - 未知のレジームに対するフォールバックは 1.0（Bull 相当）としているが、運用ルールに応じた調整が必要な場合がある。
- process_priority.set_cpu_affinity:
  - 一部環境（権限・OS）で失敗する可能性があり、失敗時はログ警告でスキップされる設計。

[0.1.0] - 2026-04-17
--------------------
Added
- 初期リリース相当として上記機能群を収録：
  - 実行 / 監視スクリプト（run_execution, run_monitoring）
  - 環境設定ローダ（.env サポート、保護された上書き処理）
  - ポートフォリオ構築・リスク調整・ポジションサイジングの純粋関数群
  - リサーチ用ファクター計算・特徴量探索モジュール（DuckDB 使用）
  - AI ニュース NLP の基本設計と一部処理
  - Paper Trading 検証レポート生成ツール
  - プロセス優先度 / CPU affinity ユーティリティ

Changed
- ドキュメンテーション（モジュール内ドクストリング）を充実化し、各関数の入力/出力仕様や設計方針を明確化。

Notes
- 本 CHANGELOG はソースコードからの推測に基づくため、実際のコミット単位の変更履歴（責務分離や細かな修正履歴）は含まれていません。実際のリリースノート作成時は Git のコミットログや PR 説明を参照してください。