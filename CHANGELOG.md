# CHANGELOG

すべての変更は Keep a Changelog の形式に従って記載しています。  
このプロジェクトはセマンティックバージョニングを採用しています。

## [Unreleased]
- （現在なし）

## [0.1.0] - 2026-03-27
初回リリース。

### 追加 (Added)
- パッケージ基盤
  - kabusys パッケージの初期実装を追加（バージョン: 0.1.0）。
  - パッケージトップで公開するサブモジュール: data, research, ai, （将来的に）execution, monitoring 等の構成を想定。

- 設定 / 環境変数管理
  - 環境変数読み込みモジュールを実装（kabusys.config）。
  - プロジェクトルート（.git または pyproject.toml）を基準に .env / .env.local の自動読み込みを行う機能を追加。OS 環境変数は上書き保護。
  - .env パーサを実装し、export KEY=val 形式、クォートやエスケープ、インラインコメントの取り扱いに対応。
  - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - Settings クラスを提供し、J-Quants / kabuステーション / Slack / DB パス等の設定アクセスとバリデーション（KABUSYS_ENV, LOG_LEVEL 等）を実装。

- データプラットフォーム（Data）
  - ETL パイプライン用インターフェースと ETLResult データクラスを実装（kabusys.data.pipeline / kabusys.data.etl）。
  - 市場カレンダー管理モジュールを実装（kabusys.data.calendar_management）。
    - market_calendar を用いた営業日判定・前後営業日取得・期間の営業日リスト取得機能を提供。
    - J-Quants からの差分取得を行う夜間バッチジョブ calendar_update_job を実装（バックフィル、健全性チェック、冪等保存）。
    - market_calendar がない場合は曜日ベースでのフォールバック（週末＝休場）をサポート。

- 研究用機能（Research）
  - ファクター計算（kabusys.research.factor_research）
    - モメンタム（1M/3M/6M リターン、200日移動平均乖離）
    - ボラティリティ / 流動性（20日 ATR、ATR 比、20日平均売買代金、出来高比率）
    - バリュー（PER、ROE。raw_financials からの最新財務データ結合）
    - DuckDB を用いた SQL + Python 実装、結果は (date, code) をキーとする辞書のリストで返す
  - 特徴量探索ユーティリティ（kabusys.research.feature_exploration）
    - 将来リターン計算（複数ホライズン対応: デフォルト [1,5,21]）
    - IC（Information Coefficient）計算（スピアマンのランク相関）
    - 基本統計サマリー（count/mean/std/min/max/median）
    - ランク変換ユーティリティ（同順位は平均ランクを返す）

- AI / NLP 機能（AI）
  - ニュースセンチメントスコアリング（kabusys.ai.news_nlp）
    - raw_news / news_symbols を集約して銘柄別にニューステキストを生成し、OpenAI（gpt-4o-mini / JSON Mode）へバッチ送信して銘柄ごとのセンチメントを算出。
    - バッチサイズ、記事数・文字数上限、リトライ（429/ネットワーク/5xx）・指数バックオフを実装。
    - レスポンスの堅牢なバリデーション（JSON モードの前後余計テキストの復元処理、results 配列の検証、未知コードの無視、数値チェック）を実装。
    - スコアは ±1.0 にクリップ。部分失敗に備え、書き込みは対象コードのみを DELETE → INSERT で置換（冪等性保護）。
    - テスト容易性のため _call_openai_api をモック差し替え可能に設計。

  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321 の 200 日 MA 乖離（重み70%）とマクロニュースの LLM センチメント（重み30%）を合成して日次で 'bull' / 'neutral' / 'bear' を判定。
    - prices_daily / raw_news を参照して ma200_ratio とマクロ記事を取得、OpenAI（gpt-4o-mini）へ問い合わせて macro_sentiment を算出。
    - レジームスコア合成と market_regime テーブルへの冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）。
    - API 障害時は macro_sentiment=0.0 としてフェイルセーフにフォールバック。OpenAI 呼び出しのリトライ/バックオフを実装。
    - lookahead バイアス防止のため、内部で datetime.today() を参照せず target_date 未満のデータのみを使用。

- 外部依存・統合
  - OpenAI API（OpenAI Python SDK）を利用した JSON Mode 呼び出しのインターフェースを実装（モデル: gpt-4o-mini）。
  - DuckDB を前提としたデータ操作。
  - J-Quants クライアント（kabusys.data.jquants_client を想定）および kabu ステーション API の設定（KABU_API_PASSWORD 等）を考慮した設計。
  - Slack 用トークン取得プロパティを用意（SLACK_BOT_TOKEN, SLACK_CHANNEL_ID）。

### 変更 (Changed)
- 初版のため過去バージョンからの変更はなし。

### 修正 (Fixed)
- 初版のため過去バージョンからの修正はなし。

### セキュリティ (Security)
- 必須環境変数（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, OPENAI_API_KEY 等）を Settings で取得し、未設定時は ValueError を発生させる仕様。
- .env 自動読み込み時に OS 環境変数を保護（上書き防止）。自動ロードを明示的に無効化するオプションあり。

### 設計上の注記 / 運用上の注意 (Notes)
- ルックアヘッドバイアス対策: AI モジュール・研究モジュールともに内部で date / target_date を明示的に受け取り、datetime.today() / date.today() を直接参照しない実装方針を採用。
- DB 書き込みは冪等性を意識（DELETE→INSERT、ON CONFLICT を使う jquants_client 側の保存等）。
- OpenAI 呼び出しはレスポンスの安全性確保のため複数回リトライと JSON バリデーションを行い、致命的エラー時もシステム全体は継続する（フェイルセーフ設計）。
- DuckDB のバージョン互換性: executemany に空リストを渡せない等の挙動を考慮した実装がある（空リスト時はスキップ）。
- news_nlp と regime_detector は内部で _call_openai_api を持ち、テスト時に個別にモック差し替え可能（モジュール結合を避けるため関数共有をしない設計）。
- news_nlp のニュース時間ウィンドウは JST ベースで定義されており、DB 比較時は UTC naive datetime に変換して使用する（前日 15:00 JST ～ 当日 08:30 JST）。

### 既知の制限 (Known limitations)
- PBR や配当利回りなど一部バリューファクターは未実装（将来拡張予定）。
- monitoring / execution 等のモジュールはパッケージレベルで参照されているが、今回のコードベースに具体実装が含まれていない箇所がある（今後実装予定）。
- OpenAI への問い合わせは JSON Mode（response_format）を利用しているが、稀に前後テキストが混入するため復元処理を実装している。完全に保証はできないため運用監視が推奨。

### アップグレード / 移行手順 (Upgrade / Migration)
- 初回導入時は必要な環境変数（JQUANTS_REFRESH_TOKEN, OPENAI_API_KEY, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等）を .env に設定してください。
- 自動 .env ロードを無効にしたい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。
- DuckDB スキーマ（prices_daily, raw_news, news_symbols, ai_scores, market_regime, market_calendar 等）が事前に準備されていることを前提としています。ETL パイプラインを実行して初期データをロードしてください。

---

参考: 本 CHANGELOG はコード中のドキュメントストリングやモジュール構成から推測して作成しています。実際のリリースノートとして使用する際は、実装者による確認・追記を推奨します。