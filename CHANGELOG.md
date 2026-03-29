# Changelog

すべての注目すべき変更点をここに記録します。
このファイルは Keep a Changelog の形式に準拠しています。
リリース日はタグ付けやパッケージのバージョンに基づいて記載しています。

注意:
- 本リリースはパッケージの初期公開に相当する内容をコードベースから推測してまとめたものです。
- 実際の変更履歴やリリースノートはプロジェクトの履歴（コミット・タグ）に基づいて確認してください。

## [Unreleased]

## [0.1.0] - 2026-03-29
Added
- パッケージ初期リリース: kabusys 0.1.0
  - 目的: 日本株自動売買システムおよび研究プラットフォームの基盤機能群を提供。

- 環境設定 / 設定管理 (kabusys.config)
  - .env ファイルおよび環境変数から設定を自動読み込みする機能を実装。
    - プロジェクトルートの検出: .git または pyproject.toml を基準に探索（CWD に依存しない）。
    - 読み込み順序: OS 環境変数 > .env.local > .env。
    - OS 側の環境変数は保護（protected set）され、.env の上書きを制御。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能（テスト用途向け）。
  - .env のパース仕様:
    - export KEY=val 形式やシングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント（条件付き）に対応。
  - Settings クラスを提供し、アプリ設定をプロパティで取得可能:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID は必須として取得時に例外を送出。
    - KABUSYS_ENV (development / paper_trading / live) と LOG_LEVEL のバリデーション。
    - DUCKDB_PATH / SQLITE_PATH のデフォルトパスを提供。

- AI（自然言語処理）機能 (kabusys.ai)
  - ニュースセンチメント解析 (kabusys.ai.news_nlp)
    - raw_news と news_symbols を元に、銘柄ごとのニュースを集約して OpenAI（gpt-4o-mini）へバッチ送信し ai_scores テーブルへ記録する機能を実装。
    - タイムウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST を対象（UTC に変換して DB 比較）。
    - チャンク処理: 最大 _BATCH_SIZE（デフォルト20）銘柄ずつ API へ投げる。
    - トークン肥大化対策: 1 銘柄あたり最大記事数・最大文字数でトリム。
    - 再試行/バックオフ: 429・ネットワーク断・タイムアウト・5xx に対する指数バックオフ実装。
    - レスポンス検証: JSON 解析、"results" フォーマット検証、未知コードの除外、スコアの数値チェック、±1.0 にクリップ。
    - DB 書き込みは冪等性を保つ: 成功したコードのみ DELETE → INSERT（部分失敗時に既存スコアを保護）。
    - テストフック: OpenAI 呼び出し箇所（_call_openai_api）を unittest.mock.patch で差し替え可能。
  - 市場レジーム判定 (kabusys.ai.regime_detector)
    - ETF 1321（Nikkei 225 連動型）の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定。
    - ma200_ratio の計算は target_date 未満のデータのみを使用してルックアヘッドバイアスを回避。
    - マクロキーワードで raw_news をフィルタし、最大記事数を上限に LLM で macro_sentiment を取得。API 失敗時は macro_sentiment=0.0 でフォールバック。
    - レジームスコア合成と閾値判定（BULL/BEAR）を行い、market_regime テーブルへトランザクション単位で冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）。
    - OpenAI 呼び出しに対してもリトライ・例外ハンドリングを実装。

- Research（因子計算・特徴量探索） (kabusys.research)
  - factor_research:
    - calc_momentum: 約1M/3M/6M リターン、200日 MA 乖離率を計算。
    - calc_value: raw_financials を用いて PER（EPS が無い/0 の場合は None）や ROE を計算。
    - calc_volatility: 20 日 ATR、相対 ATR、20日平均売買代金、出来高比（volume_ratio）を計算。
    - 実装は DuckDB の SQL ウィンドウ関数を利用し、prices_daily / raw_financials のみ参照（取引・実行 API にアクセスしない）。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターン計算。horizons の入力検証あり。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を計算。有効レコードが 3 未満なら None を返す。
    - factor_summary: 基本統計量（count, mean, std, min, max, median）を計算。
    - rank: タイを平均ランクで扱うランク変換ユーティリティ。
  - kabusys.research.__init__ で主要関数を再エクスポート。

- Data（データ基盤） (kabusys.data)
  - calendar_management:
    - JPX カレンダー管理: market_calendar を元に is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を提供。
    - market_calendar が未取得の場合は曜日（平日）ベースのフォールバックを使用。
    - next/prev_trading_day は DB 登録値を優先し、未登録日は曜日フォールバックで一貫した結果を返す。
    - calendar_update_job: J-Quants API から差分取得して market_calendar を冪等に更新。バックフィル・健全性チェックを実装。
  - pipeline / etl:
    - ETLResult データクラスを公開（kabusys.data.etl で再エクスポート）。
    - ETLResult は取得/保存件数、品質チェック結果、エラー一覧を保持。has_errors / has_quality_errors / to_dict を提供。
    - ETL パイプライン方針: 差分取得、バックフィル、生データ保存は idempotent（ON CONFLICT DO UPDATE 想定）、品質チェックは問題を収集して呼び出し元へ報告する設計。
  - DB ユーティリティ:
    - テーブル存在チェック / 最大日付取得などのユーティリティを提供し、DuckDB バージョンの制約（executemany の空リスト不可など）に配慮。

- 共通設計・品質方針（全体）
  - ルックアヘッドバイアス対策:
    - 多くの関数は datetime.today() / date.today() に依存せず、引数で指定された target_date のみで計算する設計。
    - DB クエリは target_date 未満（排他）などの条件で将来データの参照を防止。
  - フェイルセーフ/堅牢性:
    - 外部 API（OpenAI / J-Quants）失敗時は可能な限りフェイルセーフにフォールバック（例: macro_sentiment=0、部分的スキップ）し、致命的な例外は上位へ伝播する。
    - DB 書き込みはトランザクション管理（BEGIN/COMMIT/ROLLBACK）を行い、ROLLBACK 失敗時は警告ログを出す。
  - テスト容易性:
    - OpenAI 呼び出し箇所などは private 関数を patch できるように実装（unittest.mock.patch を想定）。
  - ロギング:
    - 詳細な debug/info/warning ログを多数出力して運用上の可観測性を確保。

Changed
- 初期リリースのため該当なし。

Fixed
- 初期リリースのため該当なし。

Security
- 初期リリースのため該当なし。

Notes / Known limitations
- OpenAI クライアント（OpenAI(api_key=...)）および duckdb の実行環境が別途必要。
- ai モジュールは OpenAI API のレスポンス形式に依存しており、API の仕様変更やモデル出力の変動によるパース失敗が起き得るため、ログとフォールバック処理を備えています。
- DuckDB のバージョン差異（例: list 型バインドの挙動）に配慮して実装している箇所がある（executemany を利用する等）。
- calendar_update_job / ETL は外部 J-Quants クライアント実装 (kabusys.data.jquants_client) に依存。

参考（実装上の主な公開 API）
- kabusys.config.settings (Settings)
- kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)
- kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
- kabusys.research.calc_momentum / calc_value / calc_volatility
- kabusys.research.calc_forward_returns / calc_ic / factor_summary
- kabusys.data.calendar_management.is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day / calendar_update_job
- kabusys.data.ETLResult

--- 

（補足）実際の運用・リリースノート作成時はコミットログやタグ、CHANGELOG の手動記録に基づき各項目を厳密に更新してください。