CHANGELOG
=========

この CHANGELOG は Keep a Changelog の形式に準拠しています。コードベースの内容から推測して作成しています。

Unreleased
----------

- なし（特に未リリースの破壊的変更や新機能は検出されていません）。
  - TODO コメントや将来的な拡張 (例: price フォールバック、lot_size の銘柄別対応) がソース内に存在します。

0.1.0 - 初期リリース
-------------------

リリース日: (未指定)

Added
- 実行用スクリプト
  - run_execution.py
    - ExecutionEngine を起動するエントリポイントを追加。起動時にプロセス優先度を「high」に設定し SQLite / DuckDB に接続してセッションを実行する。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite DB を使用して本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler を組み合わせて実行エンジンを構築。
    - RiskManager のデフォルトパラメータ（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker など）を設定し、初期ポートフォリオ値は broker.get_available_cash() から取得。

  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - Monitoring は実行環境にかかわらず本番 sqlite_path を使用して監視データを記録。
    - 起動時にプロセス優先度を「high」に設定、例外時にもループを継続するフェイルセーフ動作を採用。

- 設定・環境変数管理
  - config.py
    - .env ファイルの自動読み込み機能を実装（プロジェクトルートを .git / pyproject.toml で探索）。
    - 読み込み順序: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
    - .env パーサで export 形式、クォート文字列やインラインコメントの扱いをサポート。
    - Settings クラスを提供し、各種環境設定（DB パス、PID ファイル、閾値、PAPER_FILL_MODE 等）をプロパティで提供。値検証（env / log_level / PAPER_FILL_MODE）を実装。

- ポートフォリオ構築ライブラリ
  - portfolio/portfolio_builder.py
    - シグナル選別（select_candidates）、等分配 (calc_equal_weights)、スコア加重配分 (calc_score_weights) を追加。スコア全ゼロ時は等分配にフォールバックして警告を出力。

  - portfolio/risk_adjustment.py
    - セクター集中制限を適用する apply_sector_cap を実装。既存保有のセクター別エクスポージャを計算し、上限超過セクターの候補を除外（"unknown" セクターは適用除外）。
    - 市場レジームに応じた資金乗数 calc_regime_multiplier を実装（bull/neutral/bear のマッピング、未知レジーム時に 1.0 でフォールバック）。

  - portfolio/position_sizing.py
    - 株数決定ロジック calc_position_sizes を実装。allocation_method に応じて risk_based / equal / score の各方式をサポート。
    - lot_size による丸め、per-position 上限、aggregate cap のスケーリング、cost_buffer による保守的見積り、残差の再配分ロジックを実装。
    - 価格欠損時のスキップとログ出力、ドキュメント中に将来拡張（銘柄別 lot_size）の TODO を明記。

- リサーチ・ファクター計算
  - research/factor_research.py
    - DuckDB を使ったファクター計算関数を追加: calc_momentum, calc_volatility, calc_value。prices_daily / raw_financials を参照して多数の指標（1/3/6 ヶ月リターン、MA200乖離、ATR20、avg_turnover、PER、ROE 等）を計算。

  - research/feature_exploration.py
    - 将来リターン計算 calc_forward_returns（任意ホライズン）、IC 計算 calc_ic（Spearman ランク相関）、rank（同順位は平均ランク）、統計サマリ factor_summary を追加。外部依存を避け、標準ライブラリと DuckDB で実装。

  - research/__init__.py
    - 主要関数をパッケージ API としてエクスポート。

- AI ニュース NLP
  - ai/news_nlp.py
    - raw_news / news_symbols を集約し OpenAI API (gpt-4o-mini) を用いて銘柄ごとのセンチメントスコアを生成して ai_scores テーブルへ書き込む機能を実装。
    - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）を計算して対象記事を抽出。
    - バッチ処理（_BATCH_SIZE=20）、1 銘柄あたりの文字数/記事数制限、スコアの ±1.0 クリップ、429/ネットワーク/5xx に対する指数バックオフリトライを実装。
    - API 失敗時はフェイルセーフでスキップし、部分失敗時に既存スコアを保護するために対象コードのみを置換する方針（DELETE → INSERT）。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading の検証レポート出力ツールを追加。PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）を参照し、稼働率／注文成功率／送信率／レイテンシ（P95 含む）などを集計して PASS/FAIL 判定を出力。
    - P95 計算、日付フィルタ、欠損テーブルに対する安全なフォールバックを実装。

- ユーティリティ
  - utils/process_priority.py
    - プロセス優先度設定と CPU affinity 設定を実装。Windows と POSIX (Linux/Mac/FreeBSD) を吸収する実装で、権限不足や未対応 OS の場合は警告を出してスキップするフェイルセーフ。
    - set_process_priority("high"|"normal"|"low")、set_cpu_affinity(cpu_count) を提供。

Changed
- パッケージ基盤
  - kabusys/__init__.py に __version__ = "0.1.0" を追加し、主要サブパッケージを __all__ に列挙。

Fixed
- 安全性・堅牢性の向上
  - 環境変数読み込み・パースの堅牢化（クォート内のバックスラッシュ処理、インラインコメント扱いなど）。
  - ポーリング間隔の環境変数 MONITOR_POLL_INTERVAL に対し不正値（0 以下、非整数）を検出してデフォルトにフォールバックし、警告を出力。
  - duckdb / sqlite3 の接続開放（finally で close）を各スクリプトで保証。
  - 複数箇所での例外処理により単一エラーでプロセス全体が停止しないように保護（例: monitoring の check_once() 呼び出しの例外キャッチ、AI スコア取得時の一部失敗スキップなど）。

Documentation / Notes
- ソース内ドキュメントに設計指針や注意点を明記
  - research, portfolio, ai モジュールには外部 API へのアクセスを避ける設計やルックアヘッドバイアス防止の方針が明記されている。
  - position_sizing や risk_adjustment に将来対応すべき点（例: price フォールバック、銘柄別 lot_size）を TODO コメントで残している。

Security
- OpenAI API キーは引数または環境変数 OPENAI_API_KEY で注入する設計。未設定時は明示的なエラーを出す（安全性の観点でキーが漏洩しないようコード化していない）。

Breaking Changes
- なし（今回の 0.1.0 は初期リリースとしての機能追加が中心）。

既知の制限・今後の課題
- price が欠損（0.0）の場合の補完（前日終値、取得原価のフォールバック）は未実装。現状だと過少評価されてブロックが外れる可能性あり（position_sizing / apply_sector_cap に注記あり）。
- lot_size は全銘柄共通の単純設計。将来的に銘柄別 lot_size マッピングへの拡張を想定。
- DuckDB の executemany に関する挙動（空 params の扱い）に注意。ai/news_nlp 等で防御コードあり。
- OpenAI API 呼び出しの詳細バリデーションと JSON Mode を用いたレスポンス検証は実装されているが、運用上のロギングや監査・再実行フローの整備が今後の改善点。

---

変更点はコードベースから推測して作成しています。必要であれば、個々のファイル別にさらに詳細な変更ログ（関数レベルの説明や注意事項）を追加します。どの程度の粒度で記載するか指示をください。