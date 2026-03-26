# CHANGELOG

すべての重要な変更はこのファイルに記載します。  
このプロジェクトは Keep a Changelog の方針に準拠しています。  

※ 日付はこのリリースが作成された日付を記載しています。

## [Unreleased]

## [0.1.0] - 2026-03-26
初回リリース（ベース機能実装）

### Added
- パッケージの基本構成を追加
  - パッケージ名: kabusys
  - バージョン: 0.1.0

- 環境設定管理
  - .env ファイルまたは環境変数から設定値を読み込む `kabusys.config` を実装
  - 自動 .env ロード機能（プロジェクトルート検出: .git または pyproject.toml 基準）
  - `.env` / `.env.local` の読み込み順制御（OS 環境変数は保護）
  - 複雑な .env パース処理を実装（export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメント処理）
  - 自動ロード無効フラグ `KABUSYS_DISABLE_AUTO_ENV_LOAD` をサポート
  - 型/値検証付き Settings クラスを提供（必須キー取得、env 値検証、デフォルト値）
  - 必須環境変数（例: JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD / SLACK_BOT_TOKEN / SLACK_CHANNEL_ID）を明示

- AI（自然言語処理）モジュール
  - ニュースセンチメント解析: `kabusys.ai.news_nlp.score_news`
    - ニュースのタイムウィンドウ定義（JST ベース → UTC 変換）
    - 銘柄ごとにニュース記事を集約して OpenAI（gpt-4o-mini）へバッチ送信
    - バッチサイズ・文字数上限・記事数上限の制御
    - JSON Mode を利用した厳密なレスポンスパースとバリデーション
    - レスポンス検証 (results 配列、code/score 検査)、スコアの ±1.0 クリップ
    - レート制限やネットワーク障害、5xx に対する指数バックオフリトライ
    - 部分成功時に既存スコアを保護するための差分 DELETE → INSERT の冪等保存
    - テスト容易性のため OpenAI 呼び出し（内部関数）を patch 可能に実装
  - 市場レジーム判定: `kabusys.ai.regime_detector.score_regime`
    - ETF 1321 の 200 日移動平均乖離（重み 70%）と、マクロニュースの LLM センチメント（重み 30%）を合成して日次でレジーム判定（bull/neutral/bear）
    - マクロキーワードフィルタ、最大記事数、OpenAI 呼び出し、リトライ・フェイルセーフの実装
    - レジームスコアのクリップ・閾値判定・market_regime テーブルへの冪等書き込み
    - API キー注入可能（api_key 引数 or OPENAI_API_KEY 環境変数）

- データ関連モジュール
  - マーケットカレンダー管理: `kabusys.data.calendar_management`
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day 等の営業日判定ユーティリティ
    - market_calendar が未取得の場合の曜日ベースフォールバック（週末除外）
    - JPX カレンダーを J-Quants から差分取得して更新するバッチジョブ `calendar_update_job`
    - バックフィル、先読み、最大探索範囲、健全性チェックなど実運用向け考慮
  - ETL / パイプライン基盤: `kabusys.data.pipeline` / `kabusys.data.etl`
    - ETL 実行結果を表す `ETLResult` データクラスを実装・公開
    - 差分取得・保存（idempotent 保存）、品質チェックフローを想定した設計
    - DuckDB を前提とした実装（最大日付取得、テーブル存在チェック等）
  - jquants_client と quality モジュールへの統合ポイント（外部クライアント呼び出しを想定）

- リサーチ（ファクター）モジュール
  - `kabusys.research.factor_research`
    - Momentum（1M/3M/6M リターン、200 日 MA 乖離）
    - Volatility（20 日 ATR、ATR 比率、20 日平均売買代金、出来高比率）
    - Value（PER、ROE を raw_financials から取得）
    - DuckDB SQL を使った高性能な集計実装、データ不足時は None を返す堅牢設計
  - `kabusys.research.feature_exploration`
    - 将来リターン計算（任意ホライズン、デフォルト [1,5,21]）
    - IC（Spearman の ρ）計算（ランク化、ties の平均ランク対応）
    - ファクター統計サマリー（count/mean/std/min/max/median）
    - pandas 等に依存せず標準ライブラリで実装

- 共通設計・品質上の配慮
  - ルックアヘッドバイアス防止のため、内部実装で datetime.today()/date.today() を直接用いない設計（target_date を明示的に受け取る）
  - DuckDB をデータ層に採用し、SQL + Python の組合せで計算処理を実装
  - DB 書き込みは明示的なトランザクション（BEGIN / DELETE / INSERT / COMMIT）と ROLLBACK ハンドリングで冪等性・障害回復性を確保
  - OpenAI 呼び出しに対し厳格なエラーハンドリングとリトライ戦略を実装（RateLimit / ネットワーク / Timeout / 5xx）
  - テスト容易化のため外部 API 呼び出し関数を patch できるように内部実装を分離

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- OpenAI API キーは引数で注入可能かつ環境変数（OPENAI_API_KEY）から取得する設計。必須チェックを行い、未設定時は明示的に ValueError を送出。

---

開発者向けメモ（実装上の注意）
- AI 機能を利用する際は OPENAI_API_KEY を設定してください。テストでは関数内部の _call_openai_api をモックすると API 呼び出しを避けられます。
- .env 読み込みはプロジェクトルートの検出に依存します。パッケージ配布後やテスト時に自動読み込みを抑止したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB の executemany に対して空リストを渡すとエラーになるバージョンがあるため、実装側で空チェックを行っています。
- ニュースのタイムウィンドウやマーケットカレンダーの判定は UTC naive な date/datetime を使用しているため、扱う側で timezone に注意してください。

（以降のリリースでは、各モジュールのユニットテスト、OpenAI 使用量最適化、ETL の監査ログ強化、外部 API クライアントの抽象化などを予定しています。）