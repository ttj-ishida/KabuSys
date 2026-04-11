CHANGELOG
=========

すべての注目すべき変更はここに記録します。フォーマットは "Keep a Changelog" に準拠します。

未リリース
--------

- なし

[0.1.0] - 2026-04-11
--------------------

Added
- 初回リリース。システム全体の主要コンポーネントを追加。
- 実行スクリプト
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する。
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV=paper_trading 時は専用の paper_trading DB を使用し、MockBrokerClient（BrokerClientFactory 経由）でペーパートレードを実行できる。
- 設定管理
  - config.py: .env 自動読み込み（プロジェクトルート検出）を実装。`.env` / `.env.local` の読み込み優先度、export 形式・クォート・コメント処理、環境変数保護（OS 環境変数を上書きしない）をサポート。Settings クラスでアプリ設定をプロパティ化（必須キーチェック、値検証、デフォルト値）。
- プロセス制御ユーティリティ
  - utils/process_priority.py: Windows / POSIX の差分を吸収してプロセス優先度（high/normal/low）と CPU affinity を設定するユーティリティを追加。権限不足や未対応 OS では警告を出して安全にスキップする。
- ポートフォリオ構築（純粋関数）
  - portfolio/portfolio_builder.py: 候補選定（スコア降順、同点タイブレーク）と等金額・スコア加重配分関数を追加。スコアが全て 0 の場合は等金額配分にフォールバックして警告。
  - portfolio/risk_adjustment.py: セクター集中制限（apply_sector_cap）と市場レジームに応じた投下資金乗数（calc_regime_multiplier）を追加。
  - portfolio/position_sizing.py: 単元株丸め、risk_based / equal / score ベースの発注株数計算、個別・集計上限のスケーリングロジック（端数の lot 単位調整を含む）、手数料・スリッページ見積り用 cost_buffer を実装。
- リサーチ（DuckDB ベース）
  - research/factor_research.py: Momentum / Volatility / Value ファクター計算（DuckDB SQL ウィンドウ処理）を追加。十分なデータがない場合は None を返す設計。
  - research/feature_exploration.py: 将来リターン計算、Spearman ランク相関による IC 計算（ties は平均ランク）、ファクター統計サマリーを実装。外部ライブラリに依存しない純粋 Python 実装。
- AI 関連
  - ai/news_nlp.py: raw_news を OpenAI（gpt-4o-mini）でセンチメント評価して ai_scores テーブルへ書き込む処理を追加。バッチ処理、チャンク単位リトライ（429/ネットワーク/タイムアウト/5xx）、JSON バリデーション、スコアの ±1.0 クリップ、DuckDB への冪等書き込み（DELETE → INSERT）を実装。ニュース収集ウィンドウは JST ベースで定義され、ルックアヘッドバイアスを回避する実装にしている。
  - ai/regime_detector.py: ETF 1321 の 200 日 MA 乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次で市場レジーム（'bull'/'neutral'/'bear'）を判定し market_regime テーブルへ冪等書き込みする機能を追加。API 失敗時は macro_sentiment=0.0 のフォールバックを行う。
- パッケージメタ情報
  - __init__.py にて __version__ = "0.1.0" を設定。

Changed
- .env 読み込みロジックを堅牢化（export プレフィックス、クォート/エスケープ、コメントの扱い、.env.local による上書き）。
- Settings の値検証を強化（KABUSYS_ENV / LOG_LEVEL / PAPER_FILL_MODE の許容値チェック、path プロパティで expanduser を適用）。
- DuckDB / SQLite の接続管理を実行スクリプトで統一。監視/実行で init_monitoring_db を呼び出して監視テーブルの存在を保証（冪等）。

Fixed
- MONITOR_POLL_INTERVAL のパースでゼロ以下や不正値が与えられた場合にデフォルトへフォールバックする処理を追加（time.sleep に負の値が渡らないよう安全化）。
- DuckDB に対する executemany の空リスト制約を回避するため、書き込み前に params の空チェックを実装（news_nlp の ai_scores 書き込み）。
- OpenAI API 呼び出しでのエラー取り扱い（429/接続/タイムアウト/5xx）に対して指数バックオフと上限回数のリトライを追加し、その他の例外はスキップすることでサービス継続性を確保。

Security
- OpenAI API キーは明示的に引数で渡すか環境変数 OPENAI_API_KEY を使用する設計。未設定時は例外を投げる（明示的エラー）。

Internal / Notes / Known issues
- portfolio/risk_adjustment.apply_sector_cap:
  - price_map に欠損（0.0）があるとエクスポージャーが過少評価される可能性があり、将来的に前日終値や取得原価へのフォールバックを検討する TODO がある。
- position_sizing:
  - lot_size は現状グローバル固定（デフォルト 100）で、将来的には銘柄別 lot_map への拡張を検討する TODO がある。
- process_priority:
  - 権限不足（psutil.AccessDenied）や未対応プラットフォームでは設定をスキップして警告を出すが、期待どおり設定されない場合がある。
- news_nlp / regime_detector:
  - OpenAI 呼び出しは外部依存であり、部分失敗時は取得済み銘柄のみ上書きする設計にして既存データの保護を行うが、API 利用制限や費用に注意が必要。
- DuckDB SQL クエリは各ファクター関数で大きめのウィンドウをスキャンするため、データ量が多い環境では実行時間に注意。

ライセンスやセキュリティに関する変更
- なし

今後の予定（例）
- 銘柄別 lot_size のサポート（stocks マスタ追加）
- apply_sector_cap の価格フォールバック実装
- ExecutionEngine の詳細ログ・監視メトリクス強化
- OpenAI 呼び出しのコスト制御とローカル代替スコアリングの導入

--- 

注: この CHANGELOG は提供されたコードベースの内容に基づいて作成しています。リポジトリのコミット履歴が別途ある場合は、実際のリリース日やコミット単位の変更内容に合わせて更新してください。