# Changelog

すべての変更は Keep a Changelog のガイドラインに従って記載しています。  
現在のバージョンはパッケージの src/kabusys/__init__.py に定義された __version__ に基づき 0.1.0 です。

## [Unreleased]
（なし）

## [0.1.0] - 2026-03-27
初回リリース。日本株自動売買プラットフォームのコアライブラリを実装。

### 追加 (Added)
- パッケージ基盤
  - kabusys パッケージの初期エクスポートを実装（data, strategy, execution, monitoring）。
  - バージョン情報を src/kabusys/__init__.py に定義（0.1.0）。

- 設定管理 (kabusys.config)
  - .env ファイルおよび環境変数から設定を読み込む Settings クラスを実装。
  - 自動 .env ロード機能（プロジェクトルート検出: .git または pyproject.toml に基づく）。
  - .env, .env.local の優先順とオーバーライドルール、OS 環境変数保護機能を実装。
  - 複雑な .env 行パースに対応（export プレフィックス、クォート・エスケープ、インラインコメント扱いなど）。
  - 必須環境変数チェック (_require) と既定値（KABU_API_BASE_URL、データベースパスなど）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応。
  - 環境値検証（KABUSYS_ENV の有効値検査、LOG_LEVEL 検査）および環境判定ユーティリティ（is_live/is_paper/is_dev）。

- データ処理・ETL (kabusys.data)
  - ETL パイプラインのインターフェース ETLResult を公開（kabusys.data.pipeline.ETLResult）。
  - pipeline モジュール:
    - 差分更新・バックフィルの方針、品質チェック統合、DuckDB を用いた最大日付取得等のユーティリティを実装。
    - ETLResult データクラス（品質問題・エラー集約・シリアライズ to_dict）。
  - calendar_management モジュール:
    - JPX カレンダー管理、営業日判定関数群を実装。
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days。
    - market_calendar が未取得の場合は曜日ベースでフォールバックする堅牢な挙動。
    - calendar_update_job: J-Quants API からの差分取得と冪等保存ロジック（バックフィル・健全性チェック含む）。
  - DuckDB と連携する実装方針を採用（date の扱いや NULL 扱いに配慮）。

- 研究ツール (kabusys.research)
  - factor_research:
    - モメンタム（1M/3M/6M リターン、200日移動平均乖離）、ボラティリティ（20日 ATR）、流動性（20日平均出来高・売買代金）、
      バリュー（PER, ROE）を DuckDB の prices_daily / raw_financials から計算する関数群（calc_momentum, calc_volatility, calc_value）。
    - データ不足時の None 戻しやログ出力等、実運用を意識した設計。
  - feature_exploration:
    - 将来リターン計算 calc_forward_returns（任意ホライズン対応、入力検証）。
    - IC（Information Coefficient）計算 calc_ic（スピアマンの順位相関）。
    - ランク関数 rank（平均ランク処理、丸め処理による ties 対応）。
    - 統計サマリー factor_summary（count/mean/std/min/max/median）。
  - これらは本番口座や発注 API にアクセスしない純粋な解析ユーティリティとして実装。

- AI / NLP (kabusys.ai)
  - news_nlp モジュール:
    - raw_news と news_symbols から銘柄ごとに記事を集約し、OpenAI (gpt-4o-mini, JSON Mode) によるセンチメントスコアを ai_scores テーブルへ書き込む。
    - UTC/JST のニュース・ウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST に対応する UTC 範囲）を実装（calc_news_window）。
    - バッチ処理（最大 _BATCH_SIZE=20 銘柄/リクエスト）、1 銘柄当たりの最大記事数・文字数トリム、レスポンスの厳密バリデーションを実装。
    - エラー・429・ネットワーク切断・タイムアウト・5xx に対する指数バックオフのリトライ戦略を実装。
    - API 呼び出し箇所はテスト置換可能（_call_openai_api をパッチ可能に設計）。
    - レスポンスの JSON 抽出・堅牢なパース処理（前後テキストの切り出し等）。
    - スコアは ±1.0 にクリップ。部分失敗時に他銘柄スコアを保護するための部分置換（DELETE → INSERT）での DB 更新。
  - regime_detector モジュール:
    - ETF 1321（日経225連動型）200 日移動平均乖離（重み 70%）と、news_nlp ベースのマクロセンチメント（重み 30%）を合成して市場レジーム（bull / neutral / bear）を日次判定。
    - LLM 呼び出しは独立実装でモジュール結合を避ける設計（news_nlp と直接共有しない）。
    - DuckDB からのデータ取得はルックアヘッドバイアスを防ぐクエリ（date < target_date 等）。
    - OpenAI API の各種例外（RateLimit, Connection, Timeout, APIError）に対するリトライ／フォールバック（macro_sentiment=0.0）を実装。
    - market_regime テーブルへの冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）を実装。

### 変更 (Changed)
- （初期リリースのため該当なし）

### 修正 (Fixed)
- （初期リリースのため該当なし）

### セキュリティ (Security)
- OpenAI API キーは引数経由または環境変数 OPENAI_API_KEY を使用し、未設定時は明示的に ValueError を送出して誤動作を防止。
- .env 読み込み時にファイル読み込み失敗は警告を出すが致命的にはしない（安全なフェールオーバー）。

### 設計上の重要な注意点
- ルックアヘッドバイアス防止のため、datetime.today() / date.today() を直接スコープ内部で参照しない設計を徹底（外部から target_date を注入するスタイル）。
- DuckDB を主要な永続化層として利用。クエリは NULL ハンドリングや行数チェックを行い、データ不足時には安全に処理を継続する。
- 外部 API 呼び出し（OpenAI / J-Quants）は堅牢なリトライとフォールバックを備え、部分失敗時に既存データを不必要に削除しない更新方式を採用。
- テスト容易性のため、OpenAI 呼び出し箇所をモック可能に実装。

---

今後の予定（例）
- strategy / execution / monitoring の具象実装（現状はパッケージ名でのエクスポートのみ）。
- ai モデルやプロンプト改善、より詳細な品質チェックの拡充。
- CI テスト・型チェック・ドキュメント整備の強化。

もし CHANGELOG に追記したい変更点（例えば日付の修正や省略している実装の詳細）があれば教えてください。