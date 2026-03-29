# Changelog

すべての変更は Keep a Changelog の仕様に従って記載しています。  
慣例に従い、バージョンは semver を想定しています。

## [Unreleased]

## [0.1.0] - 2026-03-29
初回リリース。日本株自動売買プラットフォームのコアユーティリティ群を実装しました。
主にデータ取得/ETL、マーケットカレンダー管理、ファクター計算、ニュース NLP、そして市場レジーム判定に関する機能を提供します。

### Added
- パッケージ初期化
  - kabusys パッケージのバージョンを 0.1.0 として追加。
  - __all__ で主要サブパッケージ（data, strategy, execution, monitoring）を公開。

- 設定管理（kabusys.config）
  - .env／.env.local ファイルおよび環境変数から設定を読み込む自動ロード機能を実装（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
  - .env パーサ実装（export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの扱いに対応）。
  - OS 環境変数を保護する protected オプション（.env.local による上書き制御含む）。
  - Settings クラスを提供し、以下の設定プロパティを公開：
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH, SQLITE_PATH
    - KABUSYS_ENV（development / paper_trading / live 検証）、LOG_LEVEL（検証）
    - is_live / is_paper / is_dev の簡易判定ヘルパー
  - 必須環境変数未設定時は明示的な例外（ValueError）で通知。

- Data（kabusys.data）
  - カレンダー管理（calendar_management）
    - JPX カレンダーの夜間バッチ更新ジョブ（calendar_update_job）を実装。
    - market_calendar テーブルを利用した営業日判定 API を提供：
      - is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days
    - DB にデータがない／未登録日のフォールバック（曜日ベース）や最大探索日数制限（_MAX_SEARCH_DAYS）など堅牢な設計。
    - バックフィル／健全性チェック（_BACKFILL_DAYS、_SANITY_MAX_FUTURE_DAYS）。
  - ETL パイプライン（pipeline）
    - ETLResult データクラスを公開（kabusys.data.etl で再エクスポート）。
    - 差分取得、保存（idempotent 保存を想定）、品質チェックのための構成と結果収集の仕組みを実装。
    - DuckDB の存在チェックや最大日付取得ユーティリティを実装。

- AI（kabusys.ai）
  - ニュース NLP（news_nlp）
    - raw_news / news_symbols を集約して銘柄ごとのニューステキストを作成。
    - gpt-4o-mini（OpenAI）を用いたバッチセンチメント評価を実装。
    - チャンク処理（デフォルト最大 20 銘柄 / チャンク）、1銘柄あたりの最大記事数・文字数制限（トークン肥大対策）。
    - JSON モードを用いた出力を想定し、レスポンスのバリデーション／パース（余分な前後テキストが混入する場合の {} 抽出復元処理含む）。
    - 429・ネットワーク断・タイムアウト・5xx に対する指数バックオフリトライ、その他エラーはフェイルセーフによりスキップして継続。
    - スコアは ±1.0 にクリップ、成功した銘柄のみ ai_scores テーブルへ安全に置換（DELETE → INSERT、部分失敗時の保護）。
    - calc_news_window ヘルパー（JST 窓の UTC 変換）を実装（前日 15:00 JST 〜 当日 08:30 JST に対応）。
  - 市場レジーム判定（regime_detector）
    - ETF 1321（日経225 連動型）の 200 日移動平均乖離（重み 70%）と、マクロニュースの LLM センチメント（重み 30%）を合成して市場レジーム（bull / neutral / bear）を算出。
    - マクロニュース抽出（キーワードベース、最大 20 件）と OpenAI 呼び出し（gpt-4o-mini, JSON mode）による macro_sentiment 評価を実装。
    - API 呼び出しのリトライ戦略、API 失敗時のフェイルセーフ（macro_sentiment = 0.0）を備える。
    - DuckDB を用いた冪等な DB 書き込み（BEGIN / DELETE / INSERT / COMMIT）とロールバック処理。

- Research（kabusys.research）
  - ファクター計算（factor_research）
    - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev（200日 MA 乖離）を計算。
    - calc_volatility: atr_20, atr_pct, avg_turnover, volume_ratio を計算（ATR の NULL 伝播制御や窓サイズの扱いを含む）。
    - calc_value: raw_financials からの最新財務データを用いて PER / ROE を算出（EPS が 0/欠損の扱いに対応）。
    - DuckDB 上で SQL を活用した効率的実装。結果は (date, code) を含む dict リストで返す。
  - 特徴量探索（feature_exploration）
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一度のクエリで取得可能に実装。ホライズンは 1..252 の検証あり。
    - calc_ic: factor と forward returns の間の Spearman ランク相関（IC）を計算。データ不足時（有効レコード < 3）は None を返す。
    - rank: 同順位は平均ランクを返す安定化実装（丸め誤差対策）。
    - factor_summary: count/mean/std/min/max/median を計算する統計サマリー機能。
  - kabusys.data.stats の zscore_normalize を再エクスポート。

- 公開インターフェース整理
  - 各サブパッケージ（ai, research, data）の __init__.py で主要関数を明示的にエクスポート。

### Changed / Design decisions
- ルックアヘッドバイアス対策
  - 各 AI / リサーチ関数は datetime.today() / date.today() に依存しない設計（すべて target_date 引数ベース）。
  - DB クエリは target_date 未満／以下など排他的条件で未来データ参照を防止。
- OpenAI 統合
  - JSON Mode（response_format={"type":"json_object"}）を利用する想定で厳格な JSON の取り扱いを行うが、稀な前後テキスト混入に対する復元ロジックを追加。
  - API 呼び出しはモデル名（gpt-4o-mini）を固定で利用。テストのため _call_openai_api をモック可能に設計。
- フェイルセーフと堅牢性
  - AI API の失敗時は例外を全て伝播させず、可能な範囲で処理を続行（0.0 の中立スコア、もしくは該当銘柄のスキップ）。
  - DB 書き込みはトランザクション制御（BEGIN / COMMIT / ROLLBACK）を行い、ROLLBACK 失敗時は logger で警告。
  - DuckDB の executemany に対する互換性配慮（空リストを渡さないチェック）。
- ロギング
  - 各処理において詳細な logger.debug/info/warning/exception を配置し、運用時の調査を容易にする設計。

### Notes / Requirements
- 必須環境変数:
  - OpenAI API: OPENAI_API_KEY（news_nlp / regime_detector の呼び出し時、api_key 引数で上書き可能）
  - J-Quants: JQUANTS_REFRESH_TOKEN
  - kabuステーション: KABU_API_PASSWORD（KABU_API_BASE_URL はデフォルトあり）
  - Slack 通知: SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
- データ永続化:
  - デフォルトの DuckDB ファイルパスは data/kabusys.duckdb、SQLite は data/monitoring.db（設定で上書き可）。
- モデル／パラメータの固定値（将来変更の余地あり）:
  - ニュース・レジーム判定: gpt-4o-mini、ニュースチャンクサイズ 20、スコアクリップ ±1.0、MA 重み 0.7 / マクロ重み 0.3、200 日移動平均等。

(備考) 本 CHANGELOG は現行コードベースから機能と設計判断を推測して作成しています。実際の変更履歴やリリースノートのポリシーに合わせて追記・修正してください。