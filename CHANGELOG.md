Keep a Changelog
=================

すべての注目すべき変更はこのファイルに記録します。  
このプロジェクトは "Keep a Changelog" の慣習に従っています。

フォーマット
-----------
- 変更はセマンティックバージョニングに従います。
- 各リリースは日付付きでカテゴリ（Added, Changed, Fixed, Deprecated, Removed, Security）に整理します。

Unreleased
----------
- （未リリースの変更はここに記載）

0.1.0 - 2026-03-31
------------------

Added
- 初回リリース: kabusys パッケージの基本機能を提供。
  - パッケージ構成:
    - kabusys.config: 環境変数／設定読み込みと検証
    - kabusys.data: Data プラットフォーム向け ETL・カレンダー管理・ユーティリティ
    - kabusys.ai: ニュース NLP と市場レジーム判定（OpenAI 統合）
    - kabusys.research: ファクター計算・特徴量探索
    - そのほかモジュール群（execution, strategy, monitoring を公開対象に含む）
- 設定・環境変数管理（kabusys.config.Settings）
  - .env/.env.local の自動ロード機構を実装（プロジェクトルートは .git または pyproject.toml を基準に探索）。
  - export KEY=val 形式、クォートおよびバックスラッシュエスケープ、インラインコメントの扱いを考慮した .env 解析ロジックを実装。
  - 上書き挙動（override）と OS 環境変数保護（protected set）をサポート。
  - 自動ロード無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - 必須環境変数チェック（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等）。
  - デフォルト値の提供（KABU_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH, LOG_LEVEL の検証、KABUSYS_ENV の検証）と便利なプロパティ（is_live / is_paper / is_dev）。
- データプラットフォーム（kabusys.data）
  - ETL の公開インターフェース（ETLResult dataclass を pipeline モジュールから再エクスポート）。
  - pipeline モジュール:
    - 差分更新・バックフィル・品質チェックを想定した ETLResult を含む ETL 基盤。
    - デフォルトの最小データ開始日やカレンダー先読み・バックフィルの日数を定義。
    - DuckDB を用いた最大日付取得やテーブル存在チェックなどのユーティリティ関数。
  - calendar_management:
    - market_calendar を利用した営業日判定ロジック（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - DB 登録値を優先し、未登録日は曜日ベースでフォールバックする一貫した動作。
    - calendar_update_job: J-Quants からの差分取得・バックフィル・健全性チェック（将来日付の異常検知）と冪等保存を実装。
- ニュース NLP（kabusys.ai.news_nlp）
  - raw_news と news_symbols を元に、銘柄ごとのニュースを集約して OpenAI（gpt-4o-mini）にバッチ送信し、センチメント（ai_score）を ai_scores テーブルへ書込む。
  - タイムウィンドウ（JST 基準: 前日 15:00 ～ 当日 08:30）計算ユーティリティ calc_news_window を提供。
  - 1 銘柄あたりの最大記事数・最大文字数でトリムする仕組み（トークン増大対策）。
  - バッチ処理（最大 20 銘柄/回）、JSON Mode（厳密な JSON 出力想定）、レスポンスバリデーション、スコアの ±1.0 クリップ。
  - 429・ネットワーク断・タイムアウト・5xx に対する指数バックオフのリトライ、失敗時は安全にスキップ（例外を投げず処理継続）。
  - DuckDB への書き込みはトランザクションで DELETE → INSERT（部分失敗時に他コードの既存スコアを保護）。
- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF 1321（日経225連動型）の 200 日 MA 乖離（重み 70%）と、マクロ経済ニュースの LLM によるセンチメント（重み 30%）を合成して market_regime を日次判定。
  - マクロキーワードによる記事抽出、OpenAI 呼び出し（gpt-4o-mini）による macro_sentiment 評価、スコア合成、ラベリング（bull/neutral/bear）。
  - API 失敗時は macro_sentiment を 0.0 としてフォールバック（フェイルセーフ）。DB 書き込みは冪等（DELETE → INSERT）で実装。
- ファクター／リサーチ（kabusys.research）
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）。
    - calc_volatility: 20 日 ATR、相対 ATR（atr_pct）、平均売買代金、出来高比率。
    - calc_value: raw_financials から EPS/ROE を取得して PER/ROE を計算（PBR 等は未実装）。
    - SQL ベースの実装で DuckDB を想定。データ不足時は None を返す。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを取得。
    - calc_ic: ファクターと将来リターンの Spearman ランク相関（IC）を計算（有効データが 3 件未満なら None）。
    - rank: 同順位は平均ランクで扱うランク関数。
    - factor_summary: count/mean/std/min/max/median の集計ユーティリティ。
  - 実装方針: pandas 等外部依存を用いず、ルックアヘッドバイアス回避（date.today() を直接参照しない等）。
- その他
  - パッケージ公開インターフェース（__all__）を整備し、主要関数を意図的に外部公開。
  - OpenAI クライアント呼び出し部分はテスト容易性のため差し替え可能（内部 _call_openai_api を patch 可能）。

Changed
- 初期リリースのため該当なし。

Fixed
- 初期リリースのため該当なし。

Deprecated
- 初期リリースのため該当なし。

Removed
- 初期リリースのため該当なし。

Security
- 初期リリースのため該当なし。

Notes / 注意事項
- 環境変数の必須項目が未設定の場合、Settings のプロパティ取得で ValueError が発生します。初回運用前に .env(.local) を用意することを推奨します（.env.example を参照）。
- OpenAI API を利用する機能（news_nlp, regime_detector）は API キー（OPENAI_API_KEY）を必要とします。api_key を呼び出し引数で注入することも可能です。
- DuckDB のスキーマ（prices_daily, raw_news, news_symbols, ai_scores, raw_financials, market_calendar, market_regime 等）が前提です。ETL の初回実行前にスキーマ準備を行ってください。
- 多くの処理で「ルックアヘッドバイアス回避」の方針を採用しています（target_date 未満／以前のデータのみ参照する等）。本番利用時にもこの設計方針を維持してください。

以降のリリース想定
- エラーハンドリングや監視（monitoring）周りの強化、strategy / execution の接続部実装、J-Quants クライアントまわりの具体的な ETL 実行フローの拡充を予定しています。