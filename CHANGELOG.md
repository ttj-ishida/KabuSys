# Changelog

すべての重要な変更を記録します。  
このファイルは "Keep a Changelog" の形式に従っています。  
発行日: 2026-03-29

## Unreleased
- （現在のコードベースは初期リリース v0.1.0 を想定しています。今後の変更はここに記載されます。）

## [0.1.0] - 2026-03-29
初期リリース。日本株自動売買プラットフォームのコアライブラリ群を実装・公開。

### Added
- パッケージ基盤
  - kabusys パッケージの公開（__version__ = "0.1.0"）。
  - パッケージ公開 API（__all__）に "data", "strategy", "execution", "monitoring" を準備。

- 設定・環境変数管理（kabusys.config）
  - .env/.env.local をプロジェクトルート（.git または pyproject.toml）から自動読み込みする仕組みを実装。
  - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env のパースは export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント（スペース直前の # をコメントと扱う）に対応。
  - OS の既存環境変数を保護するための protected オプションを実装（.env.local は既存値を上書き可能だが OS 環境変数は保護）。
  - Settings クラスを提供し、必須キー取得（_require）・既定値・入力検証（KABUSYS_ENV, LOG_LEVEL 等）・便利プロパティ（is_live / is_paper / is_dev）を実装。
  - データベースパス設定（DUCKDB_PATH, SQLITE_PATH）を Path 型で返す。

- AI（自然言語処理）機能（kabusys.ai）
  - ニュースセンチメントスコアリング（kabusys.ai.news_nlp）
    - raw_news / news_symbols テーブルから銘柄毎に記事を集約し、OpenAI（gpt-4o-mini, JSON Mode）へバッチ送信して銘柄ごとのスコアを算出。
    - タイムウィンドウは前日 15:00 JST 〜 当日 08:30 JST（UTC に変換して DB 検索）。
    - 1 銘柄あたりの記事数・文字数上限（_MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK）でトークン肥大化を回避。
    - バッチ処理（最大 20 銘柄/回）・リトライ（429・ネットワーク断・タイムアウト・5xx に対する指数バックオフ）・レスポンス検証・スコアの ±1 クリップを実装。
    - レスポンスの JSON 抽出・堅牢なバリデーション（results リスト、code/score 型確認、未知コードの無視）を実装。
    - テスト容易性のため OpenAI 呼び出しを差し替え可能（内部 _call_openai_api の patch を想定）。
    - 成功した銘柄のみ ai_scores テーブルに DELETE → INSERT で冪等書き込み（部分失敗時に既存スコアを保護）。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定。
    - prices_daily / raw_news / market_regime を参照して計算・結果を market_regime テーブルへ冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）。
    - マクロニュース抽出（キーワードリスト）→ OpenAI による JSON 出力パース → 合成スコア。記事がない場合や API 失敗時は macro_sentiment を 0.0 にフォールバックするフェイルセーフ。
    - OpenAI 呼び出しは独立実装でモジュール結合を避け、テスト差し替えに対応。
    - ルックアヘッドバイアス防止のため、日時比較は target_date 未満／半開区間を使用、datetime.today()/date.today() を直接参照しない設計。

- Data（kabusys.data）
  - マーケットカレンダー管理（kabusys.data.calendar_management）
    - market_calendar テーブルを用いた営業日判定 API を提供：is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day。
    - DB にデータがある場合は DB 値優先、未登録日は曜日ベース（週末除外）でフォールバックする一貫したロジック。
    - next/prev_trading_day は最大探索日数制限（_MAX_SEARCH_DAYS）を設け、無限ループを回避。
    - calendar_update_job を通じて J-Quants API から差分取得 → 市場カレンダー更新（J-Quants クライアント呼出しと保存処理を想定）。バックフィルや健全性チェックを実装。
  - ETL パイプライン基盤（kabusys.data.pipeline / kabusys.data.etl）
    - ETLResult データクラスを実装（取得数・保存数・品質チェック結果・エラー一覧等を格納・シリアライズ可能）。
    - 差分更新、バックフィル、品質チェックの設計方針に基づくユーティリティ関数を提供（内部的に jquants_client と quality モジュールを使用）。
    - kabusys.data.etl で ETLResult を再エクスポート。

- Research（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）
    - モメンタム（1M/3M/6M リターン、200 日 MA 乖離）、ボラティリティ（20 日 ATR）、流動性（20 日平均売買代金、出来高比率）、バリュー（PER, ROE）を DuckDB 上の SQL + Python で実装。
    - データ不足時は None を返す、結果は (date, code) をキーにした dict のリストで返却。
    - prices_daily / raw_financials のみを参照し本番注文APIにはアクセスしない設計。
  - 特徴量探索・統計（kabusys.research.feature_exploration）
    - 将来リターン計算（calc_forward_returns）：複数ホライズンのリードを使って一度に計算、horizons のバリデーション。
    - IC（calc_ic）：スピアマンランク相関を実装（同順位は平均ランク、有效レコード 3 件未満で None）。
    - rank、factor_summary（count/mean/std/min/max/median）などのユーティリティを実装。
    - pandas 等の外部依存を避け、標準ライブラリのみで完結。

### Changed
- 設計方針・実装注記（ドキュメント的追加）
  - 各モジュールにおいて「ルックアヘッドバイアス防止」「フェイルセーフ」「テスト差し替え可能」等の設計方針を明記。
  - DuckDB のバージョン互換性（executemany の空リスト制約等）を考慮した実装（ai_scores 書込み時の個別 DELETE 等）。

### Fixed
- N/A（初期リリースのためバグ修正履歴はなし。実装内にログ出力や例外ハンドリングの強化を含む。）

### Security
- 機密情報取り扱い
  - OpenAI API キーは関数引数で注入可能（api_key）、または環境変数 OPENAI_API_KEY を参照。未設定時は ValueError を送出して明示。
  - .env 読み込み時に OS 環境変数を上書きしない保護ロジックを実装。

### Known limitations / Notes
- OpenAI 呼び出しは外部ネットワークを伴うため実行環境で API キー・ネットワーク設定が必要。
- news_nlp/regime_detector は JSON Mode を期待したレスポンスを前提とするため、モデル出力の変化によりパースが必要となる場合がある（復元ロジックは実装済み）。
- 一部モジュール（strategy, execution, monitoring）はパッケージ API に含まれるが、本リリースでの実装は主に data / research / ai に集中している。今後の拡張予定。

---

（今後の変更は Unreleased セクションに追加し、リリース時に日付付きのセクションとして移動してください。）