# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠し、セマンティックバージョニングに従います。  
（このCHANGELOGはソースコードから推測して自動生成されています。実際のコミット履歴と差異がある場合があります）

ドキュメント日: 2026-04-02

## [Unreleased]
（現時点で未リリースの変更はありません）

## [0.1.0] - 2026-04-02
初回公開リリース。日本株自動売買プラットフォームのコアライブラリを提供します。主な追加点は以下の通りです。

Added
- パッケージ初期化
  - kabusys パッケージの初期バージョンを追加。バージョンは 0.1.0。
  - __all__ に data, strategy, execution, monitoring を宣言。

- 設定 / 環境変数管理（kabusys.config）
  - .env/.env.local 自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml を基準に検索）。
  - .env パーサ実装: export prefix、シングル/ダブルクォート、エスケープ、インラインコメントの扱いに対応。
  - 読み込み優先順位: OS環境 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロード無効化可能。
  - 必須環境変数を取得する _require 関数と Settings クラスを提供:
    - JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、SLACK_BOT_TOKEN、SLACK_CHANNEL_ID 等のプロパティを提供
    - デフォルトの API ベース URL、DB パス（DuckDB/SQLite）、監視パラメータ、ログレベル、環境（development/paper_trading/live）等を取得可能
  - 値検証: KABUSYS_ENV / LOG_LEVEL の許容値チェック、各閾値の型変換（float）等を備える。

- AI モジュール（kabusys.ai）
  - news_nlp モジュールを追加（score_news）：raw_news と news_symbols を読み、OpenAI（gpt-4o-mini）を用いて銘柄別センチメント（ai_score）を計算し ai_scores テーブルへ書き込む。
    - タイムウィンドウ計算（前日15:00 JST ～ 当日08:30 JST を UTC ベースで扱う）。
    - バッチ処理（最大 20 銘柄 / チャンク）、1 銘柄あたり記事数・文字数トリム、JSON Mode レスポンスのバリデーション。
    - リトライ（429・ネットワーク・タイムアウト・5xx）に対する指数バックオフとフェイルセーフ（失敗時はスキップし処理継続）。
    - レスポンス検証: results キー・型チェック・コード照合・スコア数値化・±1.0 クリップ。
    - DuckDB への書き込みは冪等（DELETE → INSERT）で部分失敗時に既存データを保護。
  - regime_detector モジュールを追加（score_regime）：ETF 1321（日経225連動型）の 200 日移動平均乖離（重み70%）とニュース由来のマクロセンチメント（重み30%）を合成し、市場レジーム（bull/neutral/bear）を判定して market_regime テーブルへ保存。
    - ma200_ratio 計算（target_date 未満のデータのみ使用、データ不足時は中立値 1.0 を採用）。
    - マクロ記事抽出（タイトルフィルタリング／最大 20 記事）。
    - OpenAI 呼び出しでのリトライとフォールバック（API 失敗時は macro_sentiment=0.0）。
    - 最終的にスコアをクリップし閾値で label を決定、DB 書き込みは BEGIN/DELETE/INSERT/COMMIT の冪等処理とロールバック保護。

- データ基盤・ETL（kabusys.data）
  - ETL 結果データクラス ETLResult を公開（kabusys.data.etl に再エクスポート）。
    - ETL の取得件数、保存件数、品質問題、エラーの集約と to_dict シリアライズを提供。
  - pipeline モジュール（ETL の設計方針、ヘルパー）を追加（未完成の一部実装あり）。
    - テーブル存在チェック、最大日付取得などのユーティリティを実装（DuckDB 前提）。
  - market calendar 管理（calendar_management）
    - market_calendar テーブルを用いた営業日判定ユーティリティ群を提供（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - DB 登録値を優先し、未登録日は曜日ベースのフォールバック（週末除外）。
    - calendar_update_job: J-Quants API から差分取得して冪等的に保存（lookahead/backfill/sanity チェックを実装）。
    - 最大探索日数制限（_MAX_SEARCH_DAYS）やバックフィル、健全性チェックを備える。

- 研究（research）モジュール（kabusys.research）
  - factor_research：
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離を計算（不足時は None）。
    - calc_volatility: 20 日 ATR、ATR 比率、20 日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials と prices_daily を組み合わせて PER / ROE を計算。
    - DuckDB SQL ベースでの実装、外部 API にはアクセスしない。
  - feature_exploration：
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一度のクエリで取得。
    - calc_ic: スピアマンのランク相関（IC）を計算（有効レコードが 3 未満なら None）。
    - rank: 同順位は平均ランクへ（丸めによる ties 対応）。
    - factor_summary: カラムごとの count/mean/std/min/max/median を計算。
  - research.__init__ で主要関数を公開・再エクスポート。

- モジュールのエラーハンドリングとフェイルセーフ方針
  - OpenAI/API 周りは 5xx・ネットワーク断・タイムアウト・429 を再試行対象にして指数バックオフを行う。
  - JSON のパース失敗や不正レスポンスは WARN ログを出してスキップ（例外を投げず処理継続）。
  - DB 書き込みはトランザクション（BEGIN/COMMIT/ROLLBACK）で保護し、ROLLBACK 失敗は WARN ログで通知。

Changed
- （初回リリースにつき該当なし）

Fixed
- （初回リリースにつき該当なし）

Security
- （特記事項なし）

Notes / マイグレーション
- OpenAI 利用には OPENAI_API_KEY が必要。score_news / score_regime ともに引数でキー注入可能（テスト容易性）。
- 自動 .env ロードはデフォルトで有効。CI/テスト環境等で無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。
- DuckDB を前提に設計されており、executemany に対する空引数の扱いなど DuckDB バージョン依存の注意点がコード内に記載されています。
- calendar_update_job、ETL パイプライン等は外部 J-Quants クライアント（kabusys.data.jquants_client）を利用する想定。実運用時は該当クライアントの実装と API キーの準備が必要です。

既知の制約 / TODO（ソースから推測）
- 一部 pipeline の実装が未完（ファイル末尾に未完のコード片が含まれている可能性あり）。
- strategy / execution / monitoring パッケージは __all__ に宣言されているが、この差分では実装の有無が限定的（個別実装・統合テストが必要）。
- OpenAI のレスポンスは厳密 JSON を期待するが、実際の運用では追加の堅牢化（プロンプトやパーシングの保護）が推奨される。

以上。必要であれば各モジュールごとの詳細な変更点（関数一覧、パラメータ、返り値の詳細、ログメッセージ例、エラーケース）を追記して CHANGELOG を拡張します。どの粒度で出力するか指定してください。