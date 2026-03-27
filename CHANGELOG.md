# Changelog

すべての永続的な変更はこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠します。  

※初版リリース（v0.1.0）はリポジトリ内の実装から推測して作成しています。

## [Unreleased]
- 次回リリースに向けた変更履歴をここに記載します。

## [0.1.0] - 2026-03-27
Initial release — 日本株自動売買／リサーチ基盤の初期実装。

### 追加 (Added)
- パッケージ基盤
  - kabusys パッケージの公開 API を定義（__version__ = 0.1.0）。__all__ に data/strategy/execution/monitoring を設定。
- 環境設定管理 (kabusys.config)
  - .env ファイルおよび環境変数から設定を読み込む自動ローダーを実装。
    - プロジェクトルート検出: .git または pyproject.toml を探索して自動的に .env/.env.local を読み込む。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動読み込みを無効化可能。
    - .env.local は .env をオーバーライド（ただし既存 OS 環境変数は保護）。
  - .env パーサーの強化:
    - export KEY=val 形式に対応。
    - シングル／ダブルクォート内のバックスラッシュエスケープを考慮。
    - インラインコメントの扱い（クォート有無で異なる挙動）。
  - Settings クラスを提供（J-Quants / kabuステーション / Slack / DB パス / 環境種別 / ログレベル等）。
    - 必須環境変数未設定時は明示的な ValueError を送出。
    - 環境（development/paper_trading/live）とログレベルのバリデーションを実装。
- AI モジュール (kabusys.ai)
  - ニュースNLP（kabusys.ai.news_nlp）
    - raw_news / news_symbols を集約して銘柄ごとのセンチメント（ai_score）を算出し ai_scores に書き込む機能を実装。
    - OpenAI（gpt-4o-mini）を用いた JSON Mode 呼び出し、バッチ（最大20銘柄）処理、トークン肥大化対策（記事数・文字数のトリム）。
    - 再試行（429・ネットワーク・タイムアウト・5xx）と指数バックオフを実装。
    - レスポンスの厳格バリデーションと ±1.0 クリップ。
    - calc_news_window(target_date) ユーティリティ（JSTウィンドウ → UTC naive datetime 返却）。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（日経225連動）の 200 日移動平均乖離（重み70%）とマクロセンチメント（重み30%）を合成して日次レジーム判定を行う機能を実装。
    - マクロ記事フィルタ（キーワード群）＋ OpenAI を用いたマクロセンチメント算出。
    - API 呼び出し失敗時は macro_sentiment=0.0 とするフェイルセーフ、リトライ／バックオフを実装。
    - 計算結果を market_regime テーブルに冪等的に書き込む（BEGIN/DELETE/INSERT/COMMIT、失敗時は ROLLBACK）。
    - 外部モジュールへの過度な結合を避ける設計（_call_openai_api 等はモジュールごとに独立）。
- データプラットフォーム (kabusys.data)
  - ETL パイプライン（kabusys.data.pipeline）
    - 差分更新、保存（jquants_client の save_* を想定）、品質チェックの枠組みを提供。
    - ETLResult データクラスを公開（取得件数・保存件数・品質問題・エラー等を集約、to_dict を提供）。
    - 最小データ日やバックフィル・カレンダー先読みなどの設定を含む。
  - ETL 公開エントリ（kabusys.data.etl）で ETLResult を再エクスポート。
  - マーケットカレンダー管理（kabusys.data.calendar_management）
    - market_calendar テーブルを元に営業日判定/is_sq_day/next/prev/get_trading_days を提供。
    - DB 未取得時は曜日ベースでフォールバック（週末を非営業日扱い）。
    - calendar_update_job: J-Quants から差分取得して market_calendar を冪等更新するバッチジョブ。
    - 健全性チェック、バックフィル、最大探索日数制限を実装。
- リサーチモジュール (kabusys.research)
  - factor_research
    - モメンタム (1M/3M/6M)、ma200 乖離、ATR(20)、流動性（20日平均売買代金・出来高比）等を DuckDB と SQL で計算する関数を提供。
    - calc_momentum, calc_volatility, calc_value を実装。raw_financials / prices_daily を参照。
  - feature_exploration
    - 将来リターン計算（calc_forward_returns、任意ホライズン対応）、IC（calc_ic）計算、ランク変換ユーティリティ（rank）、統計サマリー（factor_summary）を実装。
    - pandas 等には依存せず純標準ライブラリ＋DuckDB で実装。
  - research パッケージ __all__ に主要関数を公開（zscore_normalize 等を再利用）。
- DuckDB を前提とした各種 SQL 実装
  - 全モジュールは DuckDBPyConnection を受け取り、prices_daily / raw_news / ai_scores / market_regime / raw_financials / market_calendar 等のテーブルと連携する設計。

### 変更 (Changed)
- （初版のため該当なし）: 将来のリリースでインターフェース改善や追加機能を予定。

### 修正 (Fixed)
- （初版のため該当なし）

### 注意事項 / 実装上の設計・挙動
- ルックアヘッドバイアス回避:
  - datetime.today() / date.today() を内部ロジック（AI スコア算出等）で参照しない方針。target_date を明示的に渡す設計。
  - DB クエリは target_date 未満／指定範囲で排他条件を用いるなど、未来データを参照しないよう配慮。
- フェイルセーフ:
  - OpenAI API 呼び出しに失敗した場合は例外を投げずに 0.0 やスキップで継続する箇所がある（ニュース・レジーム判定等）。呼び出し元は戻り値で失敗を判定可能。
  - DB 書き込み（複数行）は明示的なトランザクション制御（BEGIN/COMMIT/ROLLBACK）で保護。
- API キー取り扱い:
  - OpenAI API キーは関数引数で注入可能（テスト容易化）。引数未指定時は環境変数 OPENAI_API_KEY を参照し、未設定時は ValueError。
- DuckDB 互換性注意:
  - executemany に空リストを与えると失敗するバージョンを想定し、空リストチェックを行っている箇所あり。
- .env パーサーは実運用の様々な書式に対応するよう実装されているが、極端なケース（複雑なエスケープや多行値等）は未対応の可能性あり。
- OpenAI SDK 依存:
  - 実装は openai.OpenAI クライアントとエラー型（APIConnectionError, APIError, RateLimitError 等）に依存。SDK の将来的な API 変更に備えた安全策（getattr で status_code を取得等）を取り入れている。

### 既知の制約 / 今後の改善候補
- ニュース処理・LLM 呼び出しはコストとレイテンシを伴うため、バッチ化戦略やキャッシュ（過去スコア再利用）の追加を検討。
- raw_financials に基づく PBR・配当利回りなどのバリューファクターは未実装（calc_value の拡張余地あり）。
- テスト用のインターフェース（モック差し替え）については一部関数で意図的に patch しやすい実装があるが、全体でのテストカバレッジ向上が望まれる。

---

（参考）
- 主要公開関数: kabusys.config.settings、kabusys.ai.news_nlp.score_news、kabusys.ai.regime_detector.score_regime、kabusys.data.pipeline.ETLResult、kabusys.data.calendar_management の is_trading_day/next_trading_day/prev_trading_day/get_trading_days/calendar_update_job、kabusys.research の各ファクター関数 等。