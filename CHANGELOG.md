CHANGELOG
=========

すべての重要な変更点をこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠しています。  

注: 本リポジトリのバージョンはパッケージヘッダ（kabusys.__version__）に従い v0.1.0 です。

Unreleased
----------

(なし)

0.1.0 - 2026-04-09
------------------

初回リリース。以下の主要機能と実装上の設計方針を含みます。

Added
- パッケージの基本構成
  - パッケージ名: kabusys
  - エクスポート: data, strategy, execution, monitoring（パッケージ公開インターフェース）

- 環境変数・設定管理 (kabusys.config)
  - .env ファイルまたは OS 環境変数から設定を自動読み込み（プロジェクトルートを .git / pyproject.toml から検出）。
  - .env/.env.local の優先順位と上書きルールを実装（OS 環境変数は保護）。
  - 行パーサーは export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、コメントの扱いなどを正しく解析。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化をサポート。
  - Settings クラスでアプリ設定をプロパティとして提供（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, PAPER_FILL_MODE など）。
  - PAPER_FILL_MODE / KABUSYS_ENV / LOG_LEVEL 等の入力検証（許容値チェック）を実装。
  - pid/kill-flag、CPU/memory/disk のしきい値など監視用設定を提供。

- ニュース NLP / 市場レジーム判定 (kabusys.ai)
  - news_nlp.score_news:
    - raw_news と news_symbols を集約して銘柄単位のニューステキストを作成。
    - OpenAI (gpt-4o-mini) の JSON Mode を用いてバッチ（最大 20 銘柄）でセンチメントを取得。
    - トークン肥大化対策: 1 銘柄あたり記事数と文字数の上限を設定。
    - リトライ（429 / ネットワーク断 / タイムアウト / 5xx）を指数バックオフで実装。
    - レスポンスのバリデーションとスコアの ±1.0 クリップ。
    - 書き込みは冪等（DELETE → INSERT のトランザクション）で、部分失敗時に既存スコアを保護。
    - テスト用に _call_openai_api をモック可能に設計。
    - 設計方針として datetime.today()/date.today() を直接参照せず、ルックアヘッドバイアスを防止。

  - regime_detector.score_regime:
    - ETF 1321（日経225 連動）200 日移動平均乖離（重み 70%）とニュースマクロセンチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定。
    - マクロニュースは news_nlp.calc_news_window を用いて取得。
    - OpenAI 呼び出しは JSON Mode と厳格なパース、リトライ・フォールバック（失敗時 macro_sentiment=0.0）を実装。
    - DB 書き込みは冪等かつトランザクショナル（BEGIN/DELETE/INSERT/COMMIT）。
    - テスト用に _call_openai_api をモック可能に設計。
    - ルックアヘッドバイアス回避のため、price クエリは target_date 未満（排他）で取得。

- データ基盤ユーティリティ (kabusys.data)
  - calendar_management:
    - market_calendar テーブルを用いた営業日判定ロジック（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）。
    - DB 登録値を優先し、未登録日は曜日（平日）ベースのフォールバックを行う一貫性のある挙動。
    - next/prev_trading_day は最大探索日数制限（_MAX_SEARCH_DAYS）を設け例外回避。
    - calendar_update_job: J-Quants API からの差分取得と market_calendar への冪等保存、バックフィルと健全性チェックを実装。
  - pipeline / etl:
    - ETLResult データクラスを提供（target_date, fetched/saved counts, quality issues, errors など）。
    - ETL の設計方針（差分更新、バックフィル、品質チェックの集約）を反映。

- Research（kabusys.research）
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離などを prices_daily から計算。
    - calc_volatility: 20 日 ATR、ATR 比率、20 日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials と prices_daily を組み合わせて PER / ROE を算出（EPS 欠損や 0 は None を返す）。
    - 設計方針: DuckDB 接続のみを使用し、本番 API へアクセスしない。
  - feature_exploration:
    - calc_forward_returns: 将来リターン（指定ホライズン）を一度のクエリで取得。
    - calc_ic: スピアマンランク相関（IC）計算。十分なデータがない場合は None を返す。
    - factor_summary: 各ファクターの count/mean/std/min/max/median を計算。
    - rank ユーティリティ（同順位は平均ランク）を実装。
  - research パッケージは data.stats.zscore_normalize を再エクスポート。

- 再エクスポート / API
  - kabusys.data.etl にて ETLResult を公開（pipeline の再エクスポート）。

- 依存・実行環境備考
  - DuckDB を DB エンジンとして使用（SQL クエリと Python 組合せで処理）。
  - OpenAI Python SDK（client.chat.completions.create を使用）を利用。
  - 環境変数: OPENAI_API_KEY, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD などを利用。

Changed
- 初回リリースのため、該当なし。

Fixed
- 初回リリースのため、該当なし。

Deprecated
- 初回リリースのため、該当なし。

Removed
- 初回リリースのため、該当なし。

Security
- 機密情報の取り扱い:
  - .env 読み込み時に OS 環境変数を上書きしないデフォルト挙動および protected set を実装。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD によりテストや CI で自動ロードを避けられる。

Known issues / Limitations
- DuckDB executemany における空リストバインドの互換性を考慮し、空リストを executemany に渡さない保護ロジックを実装（DuckDB 0.10 特性）。
- OpenAI 依存の箇所は外部サービスの可用性に影響されるため、API エラー時はフェイルセーフ（スコア 0.0 / スキップ）で継続する設計。
- 一部モジュール（strategy, execution, monitoring）の公開エントリは __all__ に存在するが、実装が本差分内で限定的である可能性がある（将来拡張予定）。

Migration Notes
- 本バージョンからの移行に際して特別なマイグレーション手順はありません。  
- DuckDB のスキーマ（prices_daily, raw_news, ai_scores, market_regime, market_calendar, raw_financials, news_symbols 等）を事前に用意してください。
- OpenAI を使う機能を利用する場合は OPENAI_API_KEY を設定してください。

Acknowledgements / Design choices
- ルックアヘッドバイアス対策の徹底（date.today() を直接参照しない、クエリで排他条件を使用）。
- 外部 API 呼び出しは堅牢性（リトライ / バックオフ / フォールバック）を重視。
- テスト容易性のため、OpenAI 呼び出し箇所はモック可能に設計。

（以降のリリースでは機能追加・最適化・バグ修正をここに追記します。）