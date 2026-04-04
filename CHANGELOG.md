CHANGELOG
=========

すべての重要な変更は Keep a Changelog の形式に従って記載しています。  
このファイルはコードベースの内容から推測して作成した初回リリース向けの変更履歴です。

フォーマット:
- 変更はセクションごとに分類（Added / Changed / Fixed / Removed / Security）
- バージョンは src/kabusys/__init__.py の __version__ = "0.1.0" に合わせています

[Unreleased]
------------

- なし

[0.1.0] - 2026-04-04
--------------------

Added
- パッケージ初期リリース: kabusys 0.1.0
  - 日本株自動売買システムのコアモジュール群を追加。
  - パッケージ公開用の __version__ と __all__ の定義を追加。

- 環境設定 / 設定管理
  - 環境変数および .env ファイルの自動読み込み機能を追加（src/kabusys/config.py）。
    - プロジェクトルートを .git または pyproject.toml から探索して .env / .env.local を読み込む仕組み。
    - export KEY=val 形式・クォート・インラインコメントに対応したパーサ実装。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化オプション。
    - 必須変数取得用の _require と Settings クラスを提供（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD 等）。
    - 各種デフォルト設定（KABU_API_BASE_URL、データベースパス、監視閾値、ログレベル等）と値検証（KABUSYS_ENV, LOG_LEVEL）。
    - パスは Path オブジェクトで返却し expanduser を適用。

- AI（自然言語処理）
  - ニュースセンチメントスコアリング（src/kabusys/ai/news_nlp.py）
    - raw_news / news_symbols テーブルを読み、銘柄ごとにニュースを集約して OpenAI（gpt-4o-mini）へバッチ送信。
    - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）計算ユーティリティ calc_news_window を提供。
    - バッチサイズ、記事・文字数上限、APIリトライ（指数バックオフ）などを備えた堅牢な呼び出し処理。
    - JSON Mode レスポンスのバリデーションとスコア ±1.0 のクリップ処理。
    - ai_scores テーブルへ冪等（DELETE → INSERT）での書き込み。部分失敗時に既存データを保護する実装。
    - 公開 API: score_news(conn, target_date, api_key=None)
  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み70%）とマクロセンチメント（重み30%）を合成して日次の市場レジーム（bull/neutral/bear）を算出。
    - マクロセンチメントはニュースタイトルを抽出し OpenAI（gpt-4o-mini）でスコア化（JSON レスポンス）して使用。
    - ルックアヘッドバイアス対策（target_date 未満のみ参照）を徹底。
    - API エラー時は macro_sentiment=0.0 のフェイルセーフ。API呼び出しは独立実装でモジュール結合を避ける。
    - market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）。
    - 公開 API: score_regime(conn, target_date, api_key=None)

- データプラットフォーム / ETL
  - ETL 結果型の公開（src/kabusys/data/etl.py / pipeline.py）
    - ETLResult dataclass を追加（取得件数・保存件数・品質問題・エラー一覧等を含む）。to_dict により品質問題を辞書化可能。
  - ETL パイプライン基盤（src/kabusys/data/pipeline.py）
    - 差分取得、バックフィル、品質チェックを想定したパイプライン設計。
    - J-Quants クライアント呼び出しと idempotent な保存（jquants_client の save_* を利用）を前提。
    - バックフィルデフォルトや品質チェックの重大度管理を実装。
  - マーケットカレンダー管理（src/kabusys/data/calendar_management.py）
    - market_calendar テーブルの CRUD・夜間更新ジョブ（calendar_update_job）を実装。
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day の営業日判定ユーティリティを提供。
    - DB 登録値優先、未登録日は曜日ベースのフォールバックという一貫したポリシー。
    - 最大探索日数やバックフィル、健全性チェックを導入して無限ループや誤データを回避。
    - J-Quants からのフェッチと保存は jquants_client を経由。

- リサーチ（因子・特徴量探索）
  - ファクター計算モジュール（src/kabusys/research/factor_research.py）
    - Momentum（1M/3M/6M リターン、200 日 MA 乖離）、Volatility（20 日 ATR、相対 ATR）、Value（PER/ROE）等の計算を追加。
    - DuckDB 上の SQL とウィンドウ関数を利用した実装。欠損・データ不足時の None 戻しを設計。
    - 公開 API: calc_momentum, calc_volatility, calc_value
  - 特徴量探索モジュール（src/kabusys/research/feature_exploration.py）
    - 将来リターン計算（calc_forward_returns）、IC（Spearman）計算（calc_ic）、ランク変換（rank）、統計サマリー（factor_summary）を追加。
    - 外部依存なしで標準ライブラリと DuckDB を使用する実装。
    - calc_forward_returns は horizons の検証（整数かつ 1..252）やスキャン範囲のバッファ処理を実装。

- モジュール公開整理
  - 各サブパッケージの __init__.py で主要 API をエクスポート（例: kabusys.ai.score_news / score_regime、kabusys.research の各関数など）。

Changed
- （初版のため履歴なし）

Fixed
- （初版のため履歴なし）

Removed
- （初版のため履歴なし）

Security
- OpenAI API キーは引数経由か環境変数 OPENAI_API_KEY を使用。未設定時は ValueError を発生させ明示的に失敗する仕様。

Notes / 実装上の設計方針（ドキュメント的メモ）
- ルックアヘッドバイアス対策: datetime.today()/date.today() を直接参照せず、すべての関数は target_date を引数で受け取る設計。
- DB 書き込みは可能な限り冪等に（DELETE→INSERT、ON CONFLICT 等）し、部分失敗時に既存データを保護する方針。
- OpenAI 呼び出しは JSON Mode を利用し、429 / タイムアウト / ネットワーク断 / 5xx をリトライ（指数バックオフ）。解析エラー時はスキップして処理継続するフェイルセーフ。
- DuckDB（ローカル分析 DB）を想定した実装。デフォルトデータベースパスは data/kabusys.duckdb、監視用 sqlite は data/monitoring.db。
- ロギングレベルや閾値、パス等は環境変数でオーバーライド可能。LOG_LEVEL・KABUSYS_ENV の値検証を実装。

既知の省略 / 想定
- 実際の jquants_client 実装や保存関数、監視/実行（execution）モジュールの実装詳細はこのコードスニペットでは示されていないため、CHANGELOG にはそれらの具体的変更点は含めていません。
- release の日付は本CHANGELOG作成日（2026-04-04）を使用しています。

参考: 主要公開 API（抜粋）
- kabusys.config.settings から各種設定にアクセス
- kabusys.ai.score_news(conn, target_date, api_key=None)
- kabusys.ai.score_regime(conn, target_date, api_key=None)
- kabusys.ai.calc_news_window(target_date)
- kabusys.research.calc_momentum / calc_volatility / calc_value
- kabusys.research.calc_forward_returns / calc_ic / factor_summary / rank
- kabusys.data.calendar_management.is_trading_day / next_trading_day / prev_trading_day / get_trading_days / calendar_update_job
- kabusys.data.ETLResult（pipeline.ETLResult の再エクスポート）

ライセンスや配布、次回予定
- 次回リリースでは監視・実行（execution）や jquants_client の具体的実装連携、テストケース、ドキュメント強化（API 使用例、マイグレーション手順）を追加予定。

--- 
この CHANGELOG はソースコードから推測して作成しています。必要に応じて日付・詳細・カテゴリを調整してください。