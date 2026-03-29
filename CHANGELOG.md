# Changelog

すべての注目すべき変更を記載します。これは Keep a Changelog のフォーマットに準拠しています。

## [Unreleased]
（現在のスナップショットに基づく未リリースの変更はありません）

## [0.1.0] - 2026-03-29
初回公開リリース。以下の主要機能とモジュールを実装しました。

### 追加
- パッケージ基盤
  - パッケージメタ情報: kabusys.__version__ = "0.1.0" を追加。
  - モジュールのエクスポート: data, strategy, execution, monitoring を公開。

- 環境設定 / ロード
  - 環境変数管理モジュールを追加（kabusys.config）。
    - プロジェクトルート（.git または pyproject.toml）を起点に .env/.env.local を自動ロード（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
    - .env 行パーサを実装（コメント、export プレフィックス、シングル/ダブルクォート、エスケープ対応）。
    - .env/.env.local 読み込み時の上書きルール（OS 環境変数保護）を導入。
    - 必須環境変数取得ヘルパー (_require) と Settings クラスを実装。
      - J-Quants / kabu API / Slack / データベースパス（DuckDB/SQLite）/環境モード/ログレベル等を取得・検証。
      - 有効値チェック（KABUSYS_ENV や LOG_LEVEL）と is_live/is_paper/is_dev プロパティを提供。

- AI ニュース NLP
  - ニュースセンチメント分析モジュールを追加（kabusys.ai.news_nlp）。
    - タイムウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST）を実装（calc_news_window）。
    - raw_news と news_symbols を基に銘柄ごとに記事を集約し、最大記事数・最大文字数でトリム。
    - OpenAI（gpt-4o-mini）の JSON Mode を使ったバッチスコアリング（最大 20 銘柄/チャンク）。
    - 再試行（429, ネットワーク断, タイムアウト, 5xx）を指数バックオフで実装。
    - レスポンスのバリデーションとスコアの ±1.0 クリップ（_validate_and_extract）。
    - DuckDB への冪等書き込みロジック（DELETE → INSERT、executemany の空リスト回避を考慮）。
    - API キー注入可能（api_key 引数または環境変数 OPENAI_API_KEY）。

- 市場レジーム判定
  - レジーム判定モジュールを追加（kabusys.ai.regime_detector）。
    - ETF 1321（日経225 連動型）の 200 日移動平均乖離（重み 70%）と、マクロニュースの LLM センチメント（重み 30%）を合成して日次で regime_label (bull/neutral/bear) を算出。
    - MA200 計算でルックアヘッドバイアスを防止（target_date 未満のみ使用）。
    - マクロ記事抽出用キーワード一覧と記事フェッチロジック。
    - OpenAI 呼び出しの再試行戦略、API 失敗時のフェイルセーフ（macro_sentiment=0.0）。
    - 結果を market_regime テーブルへ冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）。
    - OpenAI クライアント注入（api_key 引数または環境変数）。

- データ基盤（Data）
  - カレンダー管理（kabusys.data.calendar_management）
    - market_calendar を使った営業日判定・前後営業日検索・期間内営業日取得（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）。
    - DB 不在時は曜日ベースでフォールバック（土日を休日扱い）。
    - 夜間バッチ更新ジョブ calendar_update_job を実装（J-Quants からの差分取得・バックフィル・健全性チェック）。
    - 最大探索日数やバックフィル、サニティチェックなど安全策を導入。

  - ETL パイプライン用ユーティリティ（kabusys.data.pipeline）
    - ETLResult データクラスを追加（ETL 実行結果の構造化、品質問題の表現、辞書化ユーティリティ）。
    - テーブル存在チェック、最大日付取得などの内部ユーティリティを実装。
    - デフォルト挙動：差分更新、backfill、品質チェック収集、id_token 注入可能性（テスト容易性）。

  - パイプライン API エクスポート（kabusys.data.etl）
    - ETLResult を再エクスポート。

  - jquants_client との連携を想定した設計（コメントと呼び出し点）。

- リサーチ（Research）
  - factor_research モジュール（kabusys.research.factor_research）
    - Momentum（1M/3M/6M リターン、200 日 MA 乖離）、Volatility（20 日 ATR）、Value（PER/ROE）などのファクター計算関数を実装（calc_momentum / calc_volatility / calc_value）。
    - DuckDB を利用した SQL ベースの計算（prices_daily / raw_financials 参照）。
    - データ不足時には None を返す等の堅牢な挙動。
  - feature_exploration モジュール（kabusys.research.feature_exploration）
    - 将来リターン計算（calc_forward_returns）、IC（スピアマン ρ）計算（calc_ic）、ランク付けユーティリティ（rank）、ファクター統計サマリ（factor_summary）を実装。
    - pandas 等に依存せず標準ライブラリ + DuckDB で実装。
  - research パッケージ __all__ でユーティリティを公開。

### 変更（設計上の決定）
- ルックアヘッドバイアス防止を全 AI / リサーチ関数で徹底（datetime.today()/date.today() を内部で参照しない設計）。
- OpenAI 呼び出しはモジュールごとに独立した private 関数で実装し、テスト時に patch しやすく設計。
- DuckDB の互換性考慮（executemany に空リストを渡さない等の実装上の注意）。
- DB 書き込みは可能な限り冪等になるよう DELETE→INSERT、トランザクション（BEGIN/COMMIT/ROLLBACK）で保護。
- API や I/O エラー時は全体を停止させず、ロギングしてフェイルセーフ動作（スコア 0.0 やスキップ）する方針。

### 修正（バグフィックス等）
- 初回リリースのため既知のバグ修正は該当なし（実装段階での堅牢化・ログ出力・例外処理を強化）。

### セキュリティ
- 環境変数や API キーは明示的に環境から取得する設計で、.env 自動ロード時も OS 側の環境変数を保護する仕組みを導入。

---

注記:
- 本 CHANGELOG は提供されたコードベースの内容から推測して作成しています。リリース日やドキュメントにない変更は推測に基づく記述を含みます。実際のコミット履歴やリリースノートがある場合はそちらを優先してください。