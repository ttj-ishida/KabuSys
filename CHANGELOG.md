CHANGELOG
=========

すべての公開変更は Keep a Changelog の形式に準拠して記載しています。
このファイルはコード内容から推測して生成した初期リリースの変更履歴です。

[Unreleased]
------------

- （なし）

[0.1.0] - 2026-04-16
--------------------

Added
- プロジェクト初期リリース。
- 実行エントリ / ユーティリティ
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。BrokerClientFactory によるブローカークライアント生成、OrderRepository/OrderManager/RiskManager/Reconciler の組み立て、ExecutionEngine のスレッド起動・停止処理、paper_trading 環境では専用 SQLite（data/paper_trading.db）を使用する分離を実装。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を指定可能（デフォルト 60 秒）。停止フラグファイル（data/stop_requested.flag）検出で安全に終了。
  - tools/paper_verification_report.py: Paper Trading の検証レポート生成ツールを追加。稼働率、注文成功率、送信率、レイテンシ（P95 等）などを集計し PASS/FAIL 判定を出力。--from/--to/--db オプションをサポート。
- 設定・環境変数管理
  - config.py: .env 自動読み込み（プロジェクトルート検出 .git / pyproject.toml 基準）、.env/.env.local の読み込み順、KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化、export 形式やクォート・インラインコメント対応のパーサを実装。
  - Settings クラスを導入し、各種設定（DB パス、PID ファイル、閾値、環境種類 KABUSYS_ENV、paper_trading モード、PAPER_FILL_MODE など）をプロパティとして提供。環境値検証（有効値チェック）を実施。
- データベース・分析基盤
  - DuckDB を集計用に採用（duckdb_path 設定）。monitoring 用 SQLite と DuckDB の併用を前提とした設計。
- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py: シグナルの候補選定 select_candidates、等金額・スコア加重の重み計算 calc_equal_weights / calc_score_weights（全スコアが 0 の場合は等配分へフォールバック）を実装。
  - portfolio/risk_adjustment.py: セクター集中制限 apply_sector_cap（既存保有のセクター暴露を計算し上限超過セクターの新規候補を除外）、市場レジームに基づく投下資金乗数 calc_regime_multiplier を実装（bull/neutral/bear にマップ、未知レジームはログ警告して 1.0 フォールバック）。
  - portfolio/position_sizing.py: position_sizing を実装。allocation_method に "risk_based" / "equal" / "score" をサポート。単元株（lot_size）丸め、銘柄別上限・aggregate cap（利用可能現金に合わせたスケーリング）、cost_buffer による保守的見積り、価格欠損時のスキップなどを実装。
- リサーチ / ファクター計算
  - research/factor_research.py: momentum（1M/3M/6M、MA200乖離）、volatility（ATR20、相対ATR、平均売買代金、出来高比率）、value（PER/ROE）などを DuckDB を用いた SQL クエリで計算する関数を実装。欠損データやウィンドウ不足時の None ハンドリングを行う。
  - research/feature_exploration.py: 将来リターン calc_forward_returns（任意ホライズン）、IC（Spearman ランク相関）calc_ic、ファクターの統計サマリー factor_summary、ランク関数 rank を実装。外部ライブラリに依存せず標準ライブラリのみで実装。
  - research/__init__.py: 主要関数のエクスポートを提供。
- AI / ニュース NLP（インテグレーション）
  - ai/news_nlp.py: raw_news / news_symbols からニュースを銘柄毎に集約し OpenAI API（gpt-4o-mini）でセンチメントをスコア化して ai_scores テーブルへ書き込む設計を追加。設計上の特徴:
    - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）を UTC で計算。
    - 1 銘柄あたりの記事数・文字数制限（_MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK）。
    - 最大バッチサイズ、リトライ（429/ネットワーク/5xx に対して指数バックオフ）、レスポンスバリデーション、スコアの ±1.0 クリッピング、部分失敗時の既存スコア保護（対象コードのみ DELETE→INSERT）などを想定。
    - API キー解決とエラーハンドリングを実装（未完の箇所あり）。
- 監視（Monitoring）
  - monitoring モジュール関連（init_monitoring_db / SystemMonitor を参照する起動フローを run_monitoring/run_execution で整備）。監視データベース初期化の冪等処理を実装。
- プロセス制御ユーティリティ
  - utils/process_priority.py: set_process_priority（Windows / POSIX を吸収）、set_cpu_affinity（最初の N コアに固定）を実装。psutil による実装で権限不足や未対応 API を安全に扱いログ警告でフォールバック。
- パッケージメタデータ
  - __init__.py に __version__="0.1.0" を設定。

Changed
- N/A（初期リリースのため既存の変更履歴はなし）。

Fixed
- N/A（初期リリースのため既存のバグ修正履歴はなし）。

Security
- 環境変数の自動ロード時に OS 環境変数を保護するため protected セットを使用（.env.local の override でも OS 環境変数を上書きしない挙動）。

Notes / 実装上の留意点（ドキュメント兼用）
- .env パーサは export プレフィックス、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメントの扱いなどをサポート。プロジェクト配布後も動作するよう __file__ からプロジェクトルートを探索する実装。
- paper_trading モードでは本番 DB と分離して PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）を使用するため、実運用と検証が混ざらないよう配慮。
- ポジションサイズ等の計算は現状全銘柄で共通の lot_size（デフォルト 100）を想定している。将来的に銘柄別 lot_size の拡張を想定する注記あり。
- ai/news_nlp.py は設計と多くの実装を含むが、ファイル末尾が切れている箇所があり（_fetch_articles 呼び出しの途中で終了）、実行前に残りの実装（記事取得・API 呼び出しループ・DB 書込処理等）の完成が必要。
- DuckDB での executemany に関する注意（空パラメータを渡さない等）がコードコメントで明示されている。

今後の予定（推測）
- ai/news_nlp の未完実装の完成（記事のフェッチ・バッチ送信・DB 書込ロジック）。
- 実運用での監視・ExecutionEngine の統合テスト、paper_trading 検証ツールの追加の自動化。
- 銘柄別 lot_size / 手数料・スリッページモデルの精緻化、価格欠損時のフォールバック価格導入。

----------------------------------------
本 CHANGELOG はコードベースから推測して作成したため、実際のコミット履歴や変更単位とは異なる場合があります。必要であれば、実際の git コミット履歴やリリースノートに合わせて修正してください。