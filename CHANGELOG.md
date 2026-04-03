Changelog
=========

すべての注目すべき変更点をここに記録します。フォーマットは「Keep a Changelog」に準拠しています。
リリースはセマンティックバージョニングに従います。

Unreleased
----------

（なし）

0.1.0 - 2026-04-03
------------------

初回リリース — 日本株自動売買システムのコアモジュール群を実装しました。以下は実装済みの主要機能・API・設計上の重要な挙動の概要です。

Added
- パッケージ初期化
  - kabusys パッケージ（__version__ = "0.1.0"）を追加。サブモジュールを公開: data, research, ai, execution, monitoring, strategy（__all__ に基づく）。

- 設定・環境変数管理 (kabusys.config)
  - .env ファイル自動ロード機能を追加（プロジェクトルートの検出: .git または pyproject.toml を起点に探索）。
  - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - .env 読み取りロジック:
    - export KEY=val 形式対応
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理対応
    - クォートなしの場合のインラインコメント処理（# の前に空白がある場合をコメントと見なす）
    - ファイル読み込み失敗時は警告を出力して継続（テストに優しい）
  - _load_env_file の override/protected オプションにより OS 環境変数を保護しつつ .env.local を上書き可能。
  - Settings クラスを追加し、環境変数をプロパティ経由で取得:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等の必須項目チェック（未設定時は ValueError）
    - KABU_API_BASE_URL, LINE_*、データベースパス（DUCKDB_PATH / SQLITE_PATH）のデフォルト値
    - 監視用ファイルパス（PID/KILL flag）としきい値（CPU/MEMORY/DISK）
    - KABUSYS_ENV の検証（development / paper_trading / live）
    - LOG_LEVEL の検証（DEBUG/INFO/WARNING/ERROR/CRITICAL）
    - is_live / is_paper / is_dev の簡易判定プロパティ

- AI モジュール (kabusys.ai)
  - ニュース NLP（kabusys.ai.news_nlp）
    - raw_news / news_symbols を集約して銘柄別に記事をまとめ、OpenAI（gpt-4o-mini, JSON mode）へ送信して銘柄単位のセンチメントを取得。
    - バッチ処理: 最大 20 銘柄ずつ送信（_BATCH_SIZE）。
    - 1 銘柄あたり最大記事数と文字数で上限（_MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK）を導入しトークン肥大化を抑制。
    - リトライ/バックオフ: 429・ネットワーク断・タイムアウト・5xx を対象に指数バックオフで最大試行回数を設定（_MAX_RETRIES, _RETRY_BASE_SECONDS）。
    - レスポンス検証: JSON 抽出/パース、"results" の存在、code の正規化（数値→文字列対応）、スコア数値変換、未知コードの無視、±1.0 のクリップ。
    - 書き込み: 取得した銘柄コードのみ ai_scores に DELETE → INSERT（部分失敗時に既存スコアを保護）。
    - テスト容易性: _call_openai_api を patch 可能に設計。
    - ニュース集計ウィンドウ計算 util: calc_news_window(target_date)（JST ベースの前日15:00 ～ 当日08:30 を UTC ナイーブ datetime で返す）
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（日経225 連動 ETF）の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して市場レジームを判定（'bull' / 'neutral' / 'bear'）。
    - マクロニュース抽出: raw_news からマクロキーワード（日本・米国・グローバルの経済指標語等）にマッチするタイトルを最大 20 件取得。
    - OpenAI 呼び出しは専用実装で行い、API 失敗時は macro_sentiment=0.0 にフォールバック（耐障害性）。
    - レジームスコア合成は clip して判定閾値により label を決定。
    - 結果は market_regime テーブルへ冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）。DB 書き込み失敗時は ROLLBACK を試みて例外を伝播。

- Data モジュール (kabusys.data)
  - カレンダー管理（kabusys.data.calendar_management）
    - market_calendar テーブルを基に営業日判定を行うユーティリティ群を実装:
      - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day
    - DB にデータがない場合は曜日ベースのフォールバック（平日 = 営業日）。
    - next/prev_trading_day は最大探索日数を設けて無限ループを防止（_MAX_SEARCH_DAYS）。
    - calendar_update_job: J-Quants API から差分取得し market_calendar を冪等更新。バックフィルと健全性チェック（_BACKFILL_DAYS, _SANITY_MAX_FUTURE_DAYS）を実装。
  - ETL パイプライン（kabusys.data.pipeline）
    - ETLResult データクラスを公開（kabusys.data.etl で再エクスポート）。
    - 差分取得、保存、品質チェックを行う設計に基づいたユーティリティを実装するための土台を整備（J-Quants 連携想定）。
    - DuckDB を対象としたテーブル存在チェックや最大日付取得等の補助関数を実装。
    - ETLResult は品質問題をシリアライズ可能な辞書に変換する to_dict を提供。

- Research モジュール (kabusys.research)
  - ファクター計算（kabusys.research.factor_research）
    - モメンタム: mom_1m, mom_3m, mom_6m, ma200_dev（200 日 MA 乖離）を計算する calc_momentum。
    - ボラティリティ/流動性: atr_20, atr_pct, avg_turnover, volume_ratio を計算する calc_volatility。
    - バリュー: per, roe を計算する calc_value（raw_financials と prices_daily を参照）。
    - DuckDB SQL を多用して営業日ベースのラグ・移動平均等を計算。データ不足時は None を返す一貫した挙動。
  - 特徴量探索（kabusys.research.feature_exploration）
    - 将来リターン計算 calc_forward_returns（複数ホライズンを一括取得、horizons のバリデーションあり）。
    - Information Coefficient（Spearman ρ）を計算する calc_ic（重複ランク処理・最小サンプルチェック）。
    - ランク変換ユーティリティ rank（同順位は平均ランクに変換）。
    - ファクター統計サマリー factor_summary（count/mean/std/min/max/median を計算）。
    - pandas など外部依存なしで純 Python 実装。研究用に本番 API へはアクセスしない（安全設計）。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Security
- OpenAI API キーは環境変数 OPENAI_API_KEY または各関数の api_key 引数で指定する必要があります。キー未設定時は ValueError を発生させ安全に中断します。
- .env 自動ロードでは OS 環境変数が保護され、.env.local による上書きは OS 環境変数を上書きしないよう配慮されています。

Notes / Known limitations
- AI 関連処理は OpenAI のレスポンスに依存するため、API の仕様変更やレスポンス変動に備えてレスポンスパース/バリデーションやフォールバック（0.0）を実装しています。完全な堅牢性は保証されません。
- research モジュールおよび data の多くの処理は DuckDB のテーブルスキーマ（prices_daily, raw_news, raw_financials, market_calendar, ai_scores, news_symbols 等）に依存しています。実行前に適切なテーブルを準備してください。
- ETL の実装は基盤とユーティリティを提供する段階であり、実運用のためのスケジューリング/監査ログ連携等は別途必要です。
- calc_news_window / ニュース集約は JST 基準で設計されているため、UTC タイムゾーン扱いに注意してください（内部では UTC naive datetime を使用する設計）。

署名
----
この CHANGELOG はコードベース（src/kabusys 以下）の内容から推測して作成しています。実際のリリースノートや履歴が別に存在する場合はそちらを正としてください。