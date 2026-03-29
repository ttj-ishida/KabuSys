# Changelog

すべての注目すべき変更はこのファイルに記載します。  
このプロジェクトは SemVer に従います。  

## [Unreleased]

## 0.1.0 - 2026-03-29
初回リリース

### Added
- パッケージ基盤
  - パッケージメタ情報を追加（kabusys.__init__ に __version__ = "0.1.0"、主要サブパッケージを __all__ で公開）。
- 設定 / 環境変数管理（kabusys.config）
  - .env ファイルおよび環境変数から設定を読み込む Settings クラスを実装。
  - プロジェクトルートを .git または pyproject.toml から自動検出するロジックを実装（CWD に依存しない）。
  - .env と .env.local の読み込み順序をサポート（.env.local は上書き、OS 環境変数は保護）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動読み込みを無効化可能。
  - シンプルだが堅牢な .env 行パーサーを実装（export プレフィックス、クォートやエスケープ、インラインコメント対応）。
  - 必須環境変数取得用の _require() と、環境値検証（KABUSYS_ENV, LOG_LEVEL）の実装。
  - Settings が公開する主要設定例:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH, SQLITE_PATH
    - KABUSYS_ENV（development / paper_trading / live）, LOG_LEVEL
- データ処理 / ETL（kabusys.data.pipeline, kabusys.data.etl）
  - ETLResult データクラスを実装し、ETL 実行結果・品質問題・エラーを構造化して返却可能に。
  - DuckDB を前提とした差分取得ロジック、最終取得日取得ユーティリティ、テーブル存在チェック等を実装。
  - ETL の設計に関する方針（バックフィル、品質チェックの扱い、id_token 注入でのテスト容易性）を反映。
  - etl モジュールで ETLResult を再エクスポート。
- カレンダー管理（kabusys.data.calendar_management）
  - JPX マーケットカレンダー取得・保存・夜間更新ジョブ（calendar_update_job）を実装。
  - 営業日判定 API（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）を提供。
  - market_calendar が未取得の場合は曜日ベース（土日除外）でフォールバックする設計。
  - DB 優先・未登録日は曜日フォールバックの一貫性、探索上限による無限ループ防止、バックフィル期間設定等を実装。
  - J-Quants クライアント呼び出しのエラーハンドリングとログ出力。
- 研究・ファクター（kabusys.research）
  - factor_research: モメンタム / ボラティリティ / バリュー系ファクター計算を実装。
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）。
    - calc_volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率等。
    - calc_value: PER / ROE（raw_financials の最新データを target_date 以前から取得）。
  - feature_exploration: 将来リターン計算・IC（Information Coefficient）計算・統計サマリー・ランク変換を実装。
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一括取得。
    - calc_ic: Spearman（ランク）相関で IC を計算（有効レコードが 3 未満なら None を返す）。
    - rank: 同順位を平均ランクで扱うランク化ユーティリティ（丸めで ties の検出漏れを軽減）。
    - factor_summary: count/mean/std/min/max/median を計算する集約ユーティリティ。
  - 研究用ユーティリティ zscore_normalize を kabusys.data.stats から再エクスポート（kabusys.research.__init__）。
  - pandas 等外部依存を避け、標準ライブラリ + DuckDB SQL で完結する設計。
- AI（kabusys.ai）
  - ニュースセンチメント（kabusys.ai.news_nlp）
    - score_news: raw_news と news_symbols を用い、銘柄ごとにニュースを集約して OpenAI（gpt-4o-mini）でスコア付与し ai_scores テーブルへ保存する処理を実装。
    - calc_news_window: JST ベースのニュース収集ウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST を UTC 区間に変換）。
    - バッチ処理（最大 20 銘柄/コール）、1 銘柄あたり記事数・文字数のトリム実装（_MAX_ARTICLES_PER_STOCK / _MAX_CHARS_PER_STOCK）。
    - JSON Mode を利用しレスポンスのバリデーションを厳格に行う（results list、code/score 等）。
    - リトライ（429/ネットワーク/タイムアウト/5xx）を指数バックオフで実装し、失敗時はフェイルセーフで該当チャンクをスキップ。
    - DB 書き込みは部分的置換（DELETE → INSERT）で冪等性と部分失敗耐性を確保。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - score_regime: ETF 1321（日経225 連動型）の 200 日移動平均乖離（重み 70%）と、マクロニュースの LLM センチメント（重み 30%）を統合して市場レジーム（bull/neutral/bear）を判定して market_regime テーブルへ書き込む。
    - prices_daily から ma200_ratio を計算するロジック、raw_news からマクロキーワード抽出、OpenAI 呼び出し・再試行・フェイルセーフ処理を実装。
    - LLM 呼び出しは専用の _call_openai_api を用意し、テスト時に差し替え可能。
  - ai パッケージは score_news を公開（kabusys.ai.__init__）。
- テスト性・安全性の考慮
  - 全体を通し「ルックアヘッドバイアス防止」の設計方針（datetime.today()/date.today() を処理内部で参照しない）を採用。
  - DB 書き込みはトランザクション（BEGIN/COMMIT/ROLLBACK）で行い、ROLLBACK 失敗時に警告ログを出す。
  - OpenAI 呼び出し周りはエラー種類ごとに挙動を分け、致命的でない場合はフォールバック値（0.0 など）を返すことで処理継続性を高める。
  - DuckDB 0.10 の制約（executemany の空リスト不可など）を考慮した実装。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Deprecated
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Security
- OpenAI API キー等の扱いについては、環境変数参照を基本とし、直接の埋め込みを避ける設計。KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード制御も提供。

Notes / 備考
- 必須環境変数（実行に必須・未設定時に ValueError を送出）:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
- OpenAI API を利用する関数（score_news, score_regime）は api_key を引数で注入可能。引数未指定時には環境変数 OPENAI_API_KEY を参照します。
- DuckDB の利用を前提とした実装になっています（prices_daily, raw_news, news_symbols, ai_scores, market_regime, market_calendar, raw_financials 等のスキーマが必要）。
- まだ未実装の機能（例: PBR や配当利回り等の一部バリューファクター）はコード内コメントで示されています。

今後の推奨:
- デプロイ前に .env.example を基に .env を作成し、必要な環境変数を設定してください。
- OpenAI 利用時はレート制限やコストに配慮して実行頻度を調整してください。