Keep a Changelog
=================

すべての重要な変更はこのファイルに記録されます。  
このプロジェクトは「Keep a Changelog」規約に従っています。  

フォーマット:
- 変更はセクションごとに分類します（Added, Changed, Fixed, Removed, Security 等）。
- バージョンは [x.y.z] で表記し、公開日を併記します。

Unreleased
----------

- なし

[0.1.0] - 2026-03-29
--------------------

Added
- 初回リリース: KabuSys — 日本株自動売買／リサーチ用ライブラリを追加。
  - パッケージエントリポイント: kabusys/__init__.py（バージョン 0.1.0、主要サブパッケージを公開）。
- 環境設定/管理:
  - kabusys.config: 環境変数と .env ファイルの読み込み機能を追加。
    - .env/.env.local の自動読み込み（OS 環境変数優先、.env.local は上書き可能）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化。
    - export KEY=... 形式やシングル/ダブルクォート、エスケープ、コメント処理に対応したパーサを実装。
    - 必須設定取得ヘルパー _require と Settings クラス（J-Quants、kabuステーション、Slack、DB パス、環境判定、ログレベル等）。
    - 環境値の検証（KABUSYS_ENV, LOG_LEVEL の妥当性チェック）。
- AI（自然言語処理）機能:
  - kabusys.ai.news_nlp:
    - raw_news / news_symbols を集約して OpenAI（gpt-4o-mini）により銘柄ごとのセンチメントを算出。
    - タイムウィンドウ計算（前日 15:00 JST 〜 当日 08:30 JST、内部は UTC naive datetime）。
    - バッチ送信（最大 20 銘柄／チャンク）、記事数・文字数（銘柄あたり上限）でトリム。
    - 再試行（429/ネットワーク/タイムアウト/5xx）用の指数バックオフ実装。
    - レスポンス検証（JSON 抽出、results 配列、code/score 検証、スコアクリップ）と DuckDB への冪等書き込み（DELETE→INSERT、トランザクション）。
    - フェイルセーフ設計：API 失敗時は対象銘柄をスキップして処理継続。
  - kabusys.ai.regime_detector:
    - ETF 1321 の 200 日移動平均乖離（重み70%）と、マクロニュースの LLM センチメント（重み30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定。
    - raw_news からマクロキーワードで記事を抽出し、OpenAI を用いて macro_sentiment を算出（記事が無ければ LLM 呼び出しをスキップ）。
    - API 呼び出しのリトライ/バックオフ、5xx とそれ以外の扱いの分離、JSON パース失敗時は macro_sentiment=0.0 で継続。
    - DuckDB への冪等書き込み（BEGIN/DELETE/INSERT/COMMIT + ROLLBACK を適切に処理）。
    - ルックアヘッドバイアス防止の設計（target_date 未満のデータのみ使用、datetime.today()/date.today() を直接参照しない）。
- Research（因子・特徴量探索）:
  - kabusys.research.factor_research:
    - Momentum（1M/3M/6M リターン、200 日 MA 乖離）、Volatility（20 日 ATR）、Value（PER/ROE）等のファクター計算を実装。
    - DuckDB 上の prices_daily / raw_financials のみ参照する安全設計。
    - データ不足時の None ハンドリング、結果は (date, code) をキーとする dict のリストを返却。
  - kabusys.research.feature_exploration:
    - 将来リターン計算（任意ホライズン、デフォルト [1,5,21]）、IC（Spearman rho）計算、ランク付けユーティリティ、ファクター統計サマリーを実装。
    - 外部依存（pandas 等）無しで標準ライブラリと DuckDB を利用。
  - 研究用ユーティリティの公開（zscore_normalize の再エクスポート等）。
- Data（データ基盤）:
  - kabusys.data.calendar_management:
    - JPX カレンダー管理（market_calendar テーブル）と営業日判定ユーティリティを実装。
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を提供。
    - market_calendar 未取得時は曜日ベース（週末除外）でフォールバック。DB 登録値を優先する一貫したロジック。
    - calendar_update_job: J-Quants からの差分取得・バックフィル・健全性チェック・保存処理を実装（jquants_client 経由）。
  - kabusys.data.pipeline / etl:
    - ETLResult データクラスを公開（取得件数・保存件数・品質問題・エラーを集約）。
    - 差分取得、バックフィル、品質チェック（quality モジュール）を想定した ETL パイプラインの基盤を実装。
    - jquants_client を通じた安全な保存（冪等）を想定。
  - 複数の内部ユーティリティ関数と DuckDB テーブル存在チェック等を実装。
- パッケージ API:
  - 各サブパッケージの __init__.py により主要関数を明示的に公開（例: kabusys.ai.score_news、kabusys.research.calc_momentum 等）。

Security
- 環境変数の自動ロードは OS 環境変数を保護する仕組み（protected set）を持ち、.env.local による上書き機能を提供。
- OpenAI API キーは明示的に引数で渡すか OPENAI_API_KEY 環境変数で供給する必要がある。未設定時は ValueError を発生させる箇所があるため注意。

Notes / Limitations
- DuckDB 接続（duckdb.DuckDBPyConnection）を前提とする API が多く含まれるため、実行には DuckDB と適切なテーブルスキーマが必要。
- OpenAI（gpt-4o-mini）呼び出し部分はテストしやすいように内部呼び出し関数を差し替え可能に設計（unittest.mock.patch で置換可能）。
- 外部 API の失敗はフェイルセーフ（スコアを 0 にフォールバック、あるいは該当チャンクをスキップ）する方針を採用しているため、部分的な欠損は許容するが結果の完全性は保証されない。
- 時刻/ウィンドウ設計はルックアヘッドを防ぐために明示的に設計されており、すべて date オブジェクトと UTC naive datetime を用いている点に注意。

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。

Removed
- 初回リリースのため該当なし。

References
- パッケージバージョンは kabusys/__init__.py の __version__ 値 (0.1.0)。