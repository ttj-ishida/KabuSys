# CHANGELOG

すべての注目すべき変更点はこのファイルに記載します。  
フォーマットは「Keep a Changelog」に準拠します。

なお、本リポジトリはバージョン 0.1.0 を持つ初期公開リリースです。

## [Unreleased]
（なし）

## [0.1.0] - 2026-03-31
初回リリース

### 追加 (Added)
- 基本パッケージ骨格
  - パッケージ名: kabusys
  - バージョン: 0.1.0
  - 公開されるサブパッケージ: data, research, ai, monitoring, strategy, execution（__all__ にて一括公開）

- 環境設定管理 (kabusys.config)
  - .env ファイルおよび環境変数から設定を読み込む自動ローダーを実装
    - プロジェクトルートの検出: .git または pyproject.toml を基準に探索
    - 自動読み込み優先順位: OS 環境変数 > .env.local > .env
    - 自動ロードを無効にするための環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
    - .env ロード時のオーバーライド制御（protected による OS 環境変数保護）
  - .env 行パーサーを実装（コメント、export プレフィックス、クォート・エスケープ対応）
  - 必須設定の取得ユーティリティ _require
  - Settings クラスを提供。以下のプロパティを環境変数から取得（不足時は例外）
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - KABU_API_BASE_URL（デフォルト http://localhost:18080/kabusapi）
    - DUCKDB_PATH（デフォルト data/kabusys.duckdb）
    - SQLITE_PATH（デフォルト data/monitoring.db）
    - KABUSYS_ENV のバリデーション（development / paper_trading / live）
    - LOG_LEVEL のバリデーション（DEBUG/INFO/WARNING/ERROR/CRITICAL）
    - is_live / is_paper / is_dev のショートカットプロパティ

- ニュース NLP（kabusys.ai.news_nlp）
  - raw_news / news_symbols テーブルからニュースを集約し、OpenAI（gpt-4o-mini JSON mode）により
    銘柄ごとのセンチメント ai_score を計算して ai_scores テーブルへ書き込む処理を実装
  - 処理の主な特徴:
    - タイムウィンドウ計算（JST基準: 前日15:00〜当日08:30）
    - 1銘柄あたり最大記事数・文字数でトリム（トークン肥大抑制）
    - チャンク（最大20銘柄）単位でバッチAPI送信
    - 再試行ロジック（429 / ネットワーク切断 / タイムアウト / 5xx を対象に指数バックオフ）
    - レスポンスの厳密バリデーション（JSON抽出、results 配列、コード照合、数値検査）
    - スコアは ±1.0 にクリップ
    - 書き込みは部分失敗時に既存スコアを保護するためコード絞り込みで DELETE → INSERT（冪等）
  - テスト容易性のため、OpenAI 呼び出し部分は _call_openai_api を patch 可能に設計

- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF 1321（日経225連動）の 200 日移動平均乖離（70%）とマクロニュースの LLM センチメント（30%）を合成して
    日次で市場レジーム（bull / neutral / bear）を判定して market_regime テーブルへ書き込む機能を実装
  - 特徴:
    - ma200_ratio 計算（target_date 未満のデータのみ使用しルックアヘッドバイアスを排除）
    - マクロニュースはキーワードでフィルタ（デフォルトリストあり）し上位記事を LLM へ送る
    - OpenAI（gpt-4o-mini）へ JSON モードで問い合わせ
    - API 失敗・パース失敗時は macro_sentiment=0.0 にフェイルセーフ
    - 冪等な DB 書き込み（BEGIN / DELETE / INSERT / COMMIT）を実装
    - テスト用に _call_openai_api を差し替え可能

- データ処理 / ETL（kabusys.data.pipeline / kabusys.data.etl）
  - ETLResult データクラスを追加（ETL の取得件数・保存件数・品質問題・エラーを集約）
  - ETL パイプラインの設計方針とユーティリティ関数を実装
    - 差分取得、バックフィル、品質チェックの概念設計を反映
    - DuckDB のテーブル存在チェック、最大日付取得ユーティリティを提供

- マーケットカレンダー管理（kabusys.data.calendar_management）
  - market_calendar テーブルを用いた営業日判定ロジックを実装
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days を提供
    - DB登録値を優先し、未登録日は曜日ベースのフォールバック（週末を非営業日扱い）
    - 最大探索日数による無限ループ防止
  - calendar_update_job を実装（J-Quants からカレンダーを差分取得して保存）
    - バックフィル、健全性チェック（極端に未来の日付は警告してスキップ）

- リサーチ機能（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）を追加
    - モメンタム: 1M/3M/6M リターン、ma200 乖離
    - ボラティリティ: 20日 ATR、相対ATR、平均売買代金、出来高比
    - バリュー: PER, ROE（raw_financials からの照合）
    - DuckDB 上の SQL を活用した一貫実装。結果は (date, code) 単位の dict リストで返却
  - 特徴量解析ユーティリティ（kabusys.research.feature_exploration）
    - 将来リターン計算（calc_forward_returns）
    - スピアマンランク相関（IC）計算（calc_ic）
    - ランキング補助（rank）
    - ファクター統計要約（factor_summary）
    - 外部ライブラリに依存せず標準ライブラリと DuckDB のみで実装

### 変更 (Changed)
- 初期実装のため該当なし（新規機能群の追加が中心）

### 修正 (Fixed)
- 初期実装のため該当なし

### 削除 (Removed)
- 初回リリースのため該当なし

### 警告 / 重要な注意点 (Notes)
- OpenAI API キー
  - news_nlp.score_news と regime_detector.score_regime は引数 api_key を受け取る（None の場合は環境変数 OPENAI_API_KEY を使用）。未設定の場合は ValueError を送出する。
- フェイルセーフ挙動
  - LLM 呼び出しの失敗やパースエラーは基本的に例外を投げずフォールバック値（macro_sentiment=0.0 やスコアスキップ）で継続する設計。ただし DB 書き込み時の例外はロールバック後に上位へ伝播する。
- テスト容易性
  - OpenAI 呼び出し箇所（_call_openai_api）はユニットテストで patch しやすいように設計されている。
- DB 書き込みの互換性
  - DuckDB の executemany に関する互換性（空リスト不可等）を考慮して実装している。
- 時刻・タイムゾーン
  - 日付/時刻処理はルックアヘッドバイアスを避けるために引数で与えた target_date を基準に計算し、datetime.today() / date.today() を極力使用しない設計とする関数が多い（例: news window, regime scoring）。calendar_update_job は内部で date.today() を使用するため注意。

### 既知の制約 (Known limitations)
- 一部の機能は外部 API（J-Quants, OpenAI）に依存するため、動作には各種トークンと接続が必要。
- PBR・配当利回り等いくつかのバリューメトリクスは現バージョンでは未実装。
- calendar_update_job / ETL 周りは J-Quants クライアント（kabusys.data.jquants_client）へ委譲しており、クライアント実装の変更に影響を受ける。

---

リリースや API の変更点は今後のバージョンでこの CHANGELOG に追記します。要望やバグ報告は issue を立ててください。