KEEP A CHANGELOG 準拠

すべての変更は https://keepachangelog.com/ (日本語訳) の方式に従って記載しています。

Unreleased
- なし

0.1.0 - 2026-04-02
Added
- 初期リリース: パッケージ kabusys を公開。
  - パッケージメタ情報: src/kabusys/__init__.py にて __version__="0.1.0"、主要サブパッケージを __all__ で公開 (data, strategy, execution, monitoring)。
- 設定/環境変数管理 (src/kabusys/config.py)
  - .env / .env.local 自動読み込み機能を実装。プロジェクトルートは .git または pyproject.toml を起点に探索するため CWD に依存しない。
  - 高度な .env パーサ実装（export プレフィックス対応、クォート内のバックスラッシュエスケープ、行コメントの扱い等）。
  - 環境変数の保護機能: OS 環境変数は protected として .env による上書きを抑止。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化。
  - Settings クラスを通してアプリケーション設定を集約（J-Quants / kabu API / Slack / DB パス / 監視閾値 / 環境・ログレベル判定など）。
  - 環境値検証（KABUSYS_ENV、LOG_LEVEL の許容値チェック）。
- AI モジュール (src/kabusys/ai)
  - ニュース NLP スコアリング (src/kabusys/ai/news_nlp.py)
    - raw_news と news_symbols を集約して銘柄ごとにニューステキストを作成し、OpenAI (モデル: gpt-4o-mini) の JSON-mode を使って一括でセンチメントを取得する score_news を実装。
    - 大量銘柄はチャンク処理（デフォルト 20 銘柄/チャンク）、1 銘柄あたりの記事数・文字数上限でトリム(_MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK)。
    - 429/ネットワーク/タイムアウト/5xx に対する指数バックオフのリトライ実装。
    - レスポンスの堅牢なバリデーション（JSON 抽出、results リストの検証、未知コードは無視、スコアを ±1 にクリップ）。
    - DuckDB への書き込みは部分置換方式（DELETE → INSERT）で冪等性と部分失敗耐性を確保。DuckDB executemany の空リスト制約を考慮。
    - datetime.today()/date.today() を利用しない設計でルックアヘッドバイアスを防止。
  - 市場レジーム判定 (src/kabusys/ai/regime_detector.py)
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定する score_regime を実装。
    - マクロニュース抽出用キーワードリストを定義し、raw_news から対象タイトルを取得。
    - OpenAI 呼び出しは専有実装で行い、API エラー時は macro_sentiment=0.0 として継続するフェイルセーフ。
    - DB 書き込みはトランザクション（BEGIN / DELETE / INSERT / COMMIT）で冪等に実行。失敗時は ROLLBACK を試行。
    - レトライ・エラーハンドリング（RateLimitError / APIConnectionError / APITimeoutError / APIError）を考慮。
- Research モジュール (src/kabusys/research)
  - ファクター計算 (src/kabusys/research/factor_research.py)
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離 (ma200_dev) を計算。
    - calc_volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials から最新財務データを取得して PER/ROE を計算（EPS が無効な場合は None）。
    - DuckDB を用いた SQL 中心実装、欠損データ時の None 戻し、ログ出力。
  - 特徴量探索 (src/kabusys/research/feature_exploration.py)
    - calc_forward_returns: 指定ホライズン先の将来リターン（複数ホライズンをサポート、horizons 検証）。
    - calc_ic: ファクター値と将来リターンのスピアマンランク相関 (IC) を計算（必要なレコード数が不足する場合は None）。
    - rank / factor_summary: ランク変換（タイの平均ランク処理）やカラム統計量の計算。
  - research パッケージは主要関数を __all__ で再公開。
- Data モジュール (src/kabusys/data)
  - カレンダー管理 (src/kabusys/data/calendar_management.py)
    - market_calendar を参照して営業日判定ロジック（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）を提供。DB にデータがない場合は曜日ベース（週末除外）でフォールバック。
    - calendar_update_job: J-Quants API から差分取得して market_calendar を冪等に更新。バックフィル・健全性チェックあり。
  - ETL パイプライン (src/kabusys/data/pipeline.py)
    - ETL の結果を表す ETLResult dataclass を実装（取得・保存レコード数、品質問題、エラーリスト等）。
    - 差分取得、保存、品質チェックの方針をコメントで明記（外部 jquants_client / quality モジュールを使用）。
    - internal utilities: テーブル存在チェック、最大日付取得ユーティリティ（実装途中の注意点は下記参照）。
  - data.etl は ETLResult を再エクスポート。
- 互換性および運用上の配慮
  - DuckDB を主要ストレージとして利用。DuckDB の executemany に関する既知の注意点に配慮している箇所あり（空リスト排除等）。
  - OpenAI 呼び出しは JSON-mode (response_format={"type": "json_object"}) を用い、API 変更に対する堅牢化を実施。
  - ルックアヘッドバイアス防止: モジュールは date.today() 等を参照しない設計（全て target_date を引数で受け取る）。

Security
- .env 読み込み時に OS 環境変数を保護する仕組みを導入（.env による上書きを防止）。
- OpenAI API キーが未設定の場合、score_news / score_regime は ValueError を投げて明示的にエラーにする（キー漏洩を防ぐには外部での秘匿管理を推奨）。

Fixed
- なし（初回リリース）

Deprecated
- なし

Removed
- なし

その他 / 既知の問題 (Known issues)
- src/kabusys/data/pipeline.py の末尾が途中で切れているように見える箇所があります（_get_max_date 関数の return 部分が "return date.fro" で終了しており、ファイルが不完全な可能性があります）。このため現状のままではパーサ/インポートエラーや実行時エラーになる可能性があります。リリース前に該当箇所の修正（正しい日付変換処理の完了）を推奨します。
- OpenAI API 利用部分は外部 API 依存のため、キーやネットワークの問題で挙動が変わる可能性があります。フェイルセーフ（macro_sentiment=0.0、スコアチャンクのスキップ等）は組み込まれていますが、運用ではリトライ設定や監視を行ってください。
- 一部機能は jquants_client / quality 等の外部モジュールに依存しており、それらの実装や API 仕様により挙動が変わる可能性があります。

使い始めのヒント
- 必須環境変数: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, OPENAI_API_KEY（score_news / score_regime 実行時）。
- 自動 .env ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。
- DuckDB の DB ファイルパスは DUCKDB_PATH 環境変数で上書き可能（デフォルト data/kabusys.duckdb）。
- 開発・本番切替: KABUSYS_ENV に development / paper_trading / live のいずれかを設定。

もし CHANGELOG に追記したい、あるいは既知の問題の修正コミットメッセージやリリースノートをより細かく分けたい場合は、その修正差分のソースコードやコミットログを提供してください。