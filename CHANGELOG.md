CHANGELOG
=========

すべての重要な変更点をこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠します。

注: この CHANGELOG はソースコードの内容から推測して作成しています。実際のコミット履歴とは差異がある可能性があります。

[0.1.0] - 2026-04-17
-------------------

Added
- 基本パッケージ初期リリース。
- 実行用エントリポイント:
  - run_execution.py: ExecutionEngine を起動するスクリプトを追加。KABUSYS_ENV が paper_trading の場合は MockBrokerClient を使用し、paper_trading 用に分離された SQLite（data/paper_trading.db をデフォルト）を使用する。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。停止はプロジェクトの data/stop_requested.flag によって制御。
- 設定管理:
  - config.Settings クラスを追加。環境変数（および .env / .env.local の自動ロード）から各種設定を提供（DB パス、API トークン、監視閾値、環境種別など）。
  - .env ファイル読み込みロジックはプロジェクトルート（.git または pyproject.toml）を基準に探索。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - 環境変数パース機能の強化（export プレフィックス、クォート、エスケープ、インラインコメント処理等）。
  - 設定バリデーション（KABUSYS_ENV、LOG_LEVEL、PAPER_FILL_MODE など）の追加。
- ポートフォリオ構築関連（純粋関数群）:
  - portfolio.portfolio_builder: 候補選定(select_candidates)、等金額配分(calc_equal_weights)、スコア加重配分(calc_score_weights) を追加。
  - portfolio.risk_adjustment: セクター集中制限(apply_sector_cap)、市場レジームに応じた投下資金乗数(calc_regime_multiplier) を追加。
  - portfolio.position_sizing: position sizing ロジック(calc_position_sizes) を追加。単元株（lot_size）丸め、リスクベース配分、等金額/スコアベース配分、aggregate cap によるスケールダウンをサポート。
- リサーチ / ファクター計算:
  - research.factor_research: Momentum / Volatility / Value ファクター計算（DuckDB 参照、prices_daily / raw_financials テーブル使用）を実装。
  - research.feature_exploration: 将来リターン計算(calc_forward_returns)、IC（calc_ic）、ファクター統計サマリ(factor_summary)、ランク変換(rank) を実装。外部ライブラリに依存しない純粋 Python 実装。
  - research パッケージは zscore_normalize（kabusys.data.stats から）もエクスポート。
- AI ニュース NLP:
  - ai.news_nlp モジュールを追加（ニュース記事を OpenAI API で評価して ai_scores に保存するワークフローを実装）。
  - バッチ処理（最大 20 銘柄/API コール）、トークン肥大対策（記事数・文字数制限）、429/5xx/ネットワークエラーに対する指数バックオフ再試行、結果バリデーション、スコアクリップ（±1.0）などを組み込み。
  - ニュース収集ウィンドウ計算(calc_news_window) を提供（JST ベースの前日15:00〜当日08:30 を UTC に変換して使用）。
- ツール:
  - tools.paper_verification_report: Paper Trading の検証レポート生成スクリプトを追加。稼働率、注文成功率、送信率、レイテンシ（P95）などを算出し PASS/FAIL を判定する簡易レポートを標準出力に出力。閾値はソース内定義（稼働率 99%, 成功率 90% 等）。
- ユーティリティ:
  - utils.process_priority: Windows / POSIX の差分を吸収してプロセス優先度を設定するユーティリティを追加。CPU affinity を最初の N コアに固定する機能も提供。アクセス拒否等は警告でスキップ。

Changed
- DB 周りの扱いを明確化:
  - 監視（monitoring）は KABUSYS_ENV にかかわらず本番用 sqlite_path を使用する設計（run_monitoring）。
  - run_execution は paper_trading モード時に paper_sqlite_path を使用し本番 DB と分離する。
- ログ出力とエラーハンドリングの強化:
  - run_monitoring のポーリングループで check_once() の例外を捕捉してログ出力して継続するように変更（堅牢性向上）。
  - 各種モジュールでデバッグ/警告ログを追加（ファイル名・関数単位で詳細ログあり）。
- DuckDB / SQLite の利用:
  - 多くのリサーチ/AI モジュールが DuckDB 接続を受け取る設計に統一。SQL はキャッシュ可能で、テーブル（prices_daily, raw_financials, raw_news, news_symbols, ai_scores 等）を前提。
  - executemany の事前パラメータ空検査や OperationalError 取り扱い（レポート生成ツール）など、実行時エラーに対するフォールトトレランスを追加。

Fixed
- .env 読み込みの堅牢性向上:
  - ファイルオープン失敗時に warnings.warn で通知して処理を継続。
  - クォート内のバックスラッシュエスケープを正しく処理するよう修正。
- ポジションサイズ計算の丸め処理やスケールダウンロジックにおける端数配分の安定化（残余配分は再現性を保つためソート基準に code を利用）。
- calc_value: target_date 以前の最新財務データを銘柄ごとに正しく選択するクエリ実装（ROW_NUMBER によるフィルタ）。
- レイテンシ指標（P95）計算: trade_logs から全値を取得して P95 を計算するロジックを実装。空データ時は N/A を返すように安定化。
- process_priority: 未対応 OS では警告を出してスキップ、アクセス権限不足等の例外を捕捉して警告にとどめるように変更。

Security
- API キー取り扱い:
  - ai.news_nlp.score_news は引数または環境変数 OPENAI_API_KEY による明示的な API キー解決を要求。未設定時は ValueError を送出して明示的に失敗させる（誤った匿名呼び出し防止）。

Known issues / Notes
- ai.news_nlp モジュールは大規模な API 使用を想定しており、実行時に OpenAI の利用制限やコストに注意が必要。
- calc_value では PBR・配当利回りは未実装（ソース内注記あり）。
- apply_sector_cap のエクスポージャー計算で価格が欠損（0.0）だと過少見積りとなる可能性があり、前日終値や取得原価を用いたフォールバックを将来検討する TODO が残る。
- position_sizing は現状全銘柄共通の lot_size（デフォルト 100）を仮定。将来的に銘柄別 lot_map を受け取る拡張を想定している。
- news_nlp のソースは一部（_fetch_articles 等）が未表示/途中で切れているため、完全動作には追加実装が必要な箇所がある可能性がある（本 CHANGELOG は現状コードからの推測に基づく）。

Notes for operators / developers
- 自動 .env ロードはプロジェクトルート検出に依存するため、パッケージ配布後に環境変数の自動読み込みを望まない場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- run_monitoring/run_execution は停止フラグ（data/stop_requested.flag）により安全に停止できます。Execution は起動時に既にフラグがある場合は起動を行いません。
- MONITOR_POLL_INTERVAL は環境変数で秒数を指定可能。無効値や 0/負の値はデフォルト（60 秒）にフォールバックします。
- Paper Trading の動作や検証は tools.paper_verification_report を活用してください（PAPER_TRADING_SQLITE_PATH を指定可能）。

-----------------------------------------------------------------------
このリリースは初期的な機能群の実装と、運用に耐えるための堅牢化を中心としています。今後のリリースでは AI スコアリングの完全実装、銘柄別 lot サポート、追加ファクター・シグナル、さらに監視・アラート機能の充実を予定しています。