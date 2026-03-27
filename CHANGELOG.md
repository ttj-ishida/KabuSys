# Changelog

すべての変更は Keep a Changelog の形式に従い、セマンティック バージョニングを使用します。
このファイルは推定に基づき、コードベースの実装内容から作成しています。

## [0.1.0] - 2026-03-27

### Added
- 初回リリース。日本株自動売買システム「KabuSys」のコア機能を追加。
- パッケージ公開インターフェース
  - kabusys.__init__ による主要サブパッケージのエクスポート: data, strategy, execution, monitoring。
- 環境設定 / ロード
  - kabusys.config: .env ファイルおよび環境変数からの設定読み込み機能を実装。
  - プロジェクトルート検出（.git または pyproject.toml を起点）により CWD に依存しない自動 .env ロードを実現。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート（テスト等で使用）。
  - .env パーサーは export KEY=val、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント処理などに対応。
  - Settings クラスを提供し、必須環境変数（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID など）を検証・取得する API を追加。
  - KABUSYS_ENV（development/paper_trading/live）と LOG_LEVEL の検証を実装。
  - デフォルトの DB パス（duckdb/sqlite）を設定するプロパティを追加。

- ニュース NLP / 市場レジーム判定（AI）
  - kabusys.ai.news_nlp:
    - raw_news と news_symbols に基づき、銘柄毎にニュースを集約して OpenAI（gpt-4o-mini）へ送信しセンチメントスコアを算出する score_news を実装。
    - JST ベースのニュース収集ウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）の計算（calc_news_window）。
    - バッチ処理（1APIコールあたり最大 20 銘柄）、記事数・文字数トリム、JSON Mode 応答のバリデーションとスコアクリッピング（±1.0）。
    - 再試行ロジック（429/ネットワーク/タイムアウト/5xx に対する指数バックオフ）とフェイルセーフ（API 失敗時は該当チャンクをスキップ）。
    - DuckDB への冪等書き込み（DELETE → INSERT を個別 executemany で実行し部分失敗に耐性）。
  - kabusys.ai.regime_detector:
    - ETF 1321（Nikkei 225 連動 ETF）の 200 日移動平均乖離（重み 70%）とニュースベースのマクロセンチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定する score_regime を実装。
    - raw_news からマクロキーワードで記事を抽出し LLM（gpt-4o-mini）でマクロセンチメントを評価。API エラー時は macro_sentiment=0.0 として継続。
    - MA 計算・スコア合成・クリッピング・閾値判定の各処理と、market_regime テーブルへの冪等書き込みを実装。
    - OpenAI 呼び出しは専用の内部関数で分離し、テスト時に差し替え可能（unittest.mock.patch を想定）。

- データプラットフォーム（Data）
  - kabusys.data.calendar_management:
    - JPX カレンダー管理（market_calendar テーブル）を実装し、営業日判定・前後営業日取得・期間内営業日リスト取得・SQ 日判定等のユーティリティを追加。
    - DB にカレンダーが存在しない場合は曜日（平日）ベースのフォールバックを利用する堅牢な挙動を実装。
    - calendar_update_job による J-Quants API からの差分取得・バックフィル（直近 N 日再取得）・健全性チェック（将来日付異常検出）を実装（jquants_client を利用）。
  - kabusys.data.pipeline:
    - ETL パイプラインの基本構成を実装（差分取得、保存、品質チェックの呼び出し）。
    - ETLResult データクラスを追加し、取得件数・保存件数・品質問題・エラーを集約、辞書変換メソッドを提供。
    - 差分取得ロジック（最小データ日、デフォルトの backfill、calendar lookahead 等）と品質チェックの扱い方針（エラーは収集して呼び出し元へ伝搬）を実装。
  - kabusys.data.etl:
    - pipeline.ETLResult を再エクスポート。

- リサーチ / ファクター計算
  - kabusys.research.factor_research:
    - モメンタム（1M/3M/6M、ma200乖離）、ボラティリティ（20日 ATR、相対 ATR）、流動性（20日平均売買代金、出来高比率）、バリュー（PER、ROE）などの計算関数を実装:
      - calc_momentum, calc_volatility, calc_value
    - DuckDB 上の SQL を主体にして高速かつ外部 API に依存しない設計。データ不足時は None を返す設計。
  - kabusys.research.feature_exploration:
    - 将来リターン計算（calc_forward_returns）、IC（Information Coefficient）計算（calc_ic）、ランク変換（rank）、ファクター統計サマリー（factor_summary）を実装。
    - pandas 等に依存せず標準ライブラリのみで実装し、スピアマン相関（ランク相関）や統計量（mean/std/median 等）を提供。
  - kabusys.research.__init__ で上記ユーティリティを公開（zscore_normalize は kabusys.data.stats から参照）。

### Changed
- 設計方針の明確化（コード内ドキュメンテーションに反映）
  - 全てのモジュールで datetime.today()/date.today() を直接参照しない方針を採用（ルックアヘッドバイアス対策）。関数は target_date を受け取る API を主体に実装。
  - DuckDB に対する操作は冪等性（DELETE→INSERT、ON CONFLICT 想定）と部分失敗への耐性を重視して実装。

### Fixed / Robustness improvements
- .env 読み込みの堅牢化
  - 読み込み失敗時に警告を出して継続（テスト環境等での強制停止を防止）。
  - OS 環境変数を保護するため読み込み時の protected キーセット機能を追加（.env.local は上書き可だが OS 環境変数は保護）。
- AI 呼び出し周りのフェイルセーフとリトライ
  - JSON パース失敗、API レスポンスの不正時に WARN を出してフェイルセーフ値（0.0 など）へフォールバック。
  - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフのリトライ実装。
  - レート制限やサーバーエラー時のログ強化。
- DuckDB 互換性考慮
  - executemany に空リストを渡さないチェック（DuckDB 0.10 の制約への対応）。
  - 日付値の型変換ユーティリティ（_to_date）を追加して DuckDB の返却型差異に対応。

### Removed
- 該当なし（初回リリース）。

### Security
- OpenAI API キーは引数で注入可能（api_key）か環境変数 OPENAI_API_KEY を使用。未設定時は ValueError を投げることでキー漏洩や未設定状態を明示。

---

注: 上記はコードベースの実装内容から推測して作成した CHANGELOG です。リリースに含める文章や日付、カテゴリの割当はプロジェクトの正式なリリース方針に合わせて調整してください。