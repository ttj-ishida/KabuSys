# CHANGELOG

すべての注目すべき変更点を記録します。フォーマットは「Keep a Changelog」に準拠しています。  
各リリースはセマンティックバージョニングに従います。

## [Unreleased]
- （なし）

## [0.1.0] - 2026-03-29
初回公開リリース。日本株自動売買システムのコア機能群を実装しました。

### 追加（Added）
- パッケージ基盤
  - パッケージ初期化 (kabusys.__init__) とバージョン設定を追加（バージョン 0.1.0）。
  - パブリックサブパッケージとして data, strategy, execution, monitoring をエクスポート。

- 環境設定 / 設定管理（kabusys.config）
  - .env / .env.local 自動読み込み機能を実装（プロジェクトルート検出: .git または pyproject.toml）。
  - .env パース実装: export プレフィックス、シングル/ダブルクォート内のエスケープ処理、行内コメント処理に対応。
  - 自動ロードの無効化フラグ（KABUSYS_DISABLE_AUTO_ENV_LOAD）をサポート。
  - Settings クラスを提供し、J-Quants / kabuステーション / Slack / DB パス /実行環境などの設定プロパティを公開（必須値は未設定時に ValueError を送出）。
  - 環境名（KABUSYS_ENV）とログレベル（LOG_LEVEL）のバリデーションを実装。

- AI ニュース分析（kabusys.ai.news_nlp）
  - raw_news と news_symbols を集約して OpenAI（gpt-4o-mini）で銘柄ごとのニュースセンチメントを算出する score_news 関数を実装。
  - ニュースの時間ウィンドウ計算（JST基準 → DB上は UTC naive の datetime）を実装（calc_news_window）。
  - バッチ処理（最大 20 銘柄）での API 呼び出し、トークン肥大対策（記事数・文字数トリム）を導入。
  - レスポンスバリデーションとスコアクリッピング（±1.0）。
  - 冗長性対策: 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフリトライを実装。
  - DB 書き込みは冪等性を考慮（対象コードのみ DELETE → INSERT）。DuckDB の executemany の空リスト制約への対応あり。
  - テスト容易性: OpenAI 呼び出し部分を patch して差し替え可能（内部 _call_openai_api）。

- AI 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF 1321（日経225連動）200日移動平均乖離とマクロセンチメント（LLM）を重み合成して日次の market_regime を算出する score_regime を実装。
  - マクロキーワードによる raw_news フィルタリング、LLM（gpt-4o-mini）での JSON 出力想定、フェイルセーフ（API 失敗時は macro_sentiment=0.0）を導入。
  - ルックアヘッドバイアス防止のため target_date 未満のデータのみ使用、datetime.today() 等を参照しない設計。
  - DB 書き込みはトランザクション（BEGIN / DELETE / INSERT / COMMIT）で冪等化し、失敗時には ROLLBACK。

- リサーチ / ファクター計算（kabusys.research）
  - ファクター計算: calc_momentum, calc_value, calc_volatility を実装（prices_daily / raw_financials を参照）。
    - Momentum: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）。
    - Value: PER（EPS が 0 または NULL の場合は None）、ROE。
    - Volatility/Liquidity: 20 日 ATR、相対ATR、20 日平均売買代金、出来高比率。
  - 特徴量探索: calc_forward_returns（任意ホライズンの将来リターン取得）、calc_ic（Spearman のランク相関（IC）計算）、rank（平均ランク処理）、factor_summary（統計サマリー）を実装。
  - Z スコア正規化ユーティリティは kabusys.data.stats から再エクスポート。
  - 実装方針として DuckDB に対する SQL と Python の組合せを採用、外部依存（pandas 等）なし。

- データプラットフォーム（kabusys.data）
  - マーケットカレンダー管理（calendar_management）を実装:
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day 等の営業日関連ユーティリティ。
    - DB に market_calendar がある場合は DB 優先、未登録日は曜日ベースのフォールバックを一貫して適用。
    - calendar_update_job により J-Quants から差分取得→保存（バックフィル、健全性チェックあり）。
  - ETL 基盤:
    - ETLResult データクラス（kabusys.data.pipeline）を公開して ETL の結果を集約。
    - 差分取得、保存（idempotent な save_* の利用想定）、品質チェックフレームワークとの連携方針を実装（quality モジュールへの参照）。
    - 内部ユーティリティ: テーブル存在チェック、最大日付取得、トレーディングデイ調整ロジック等。

- テスト/運用を考慮した設計上の特徴
  - ルックアヘッドバイアス対策: date.today() / datetime.today() を直接参照しない設計が多くのモジュールで採用されている（外部から target_date を注入するスタイル）。
  - OpenAI 呼び出し部分は内部関数をモジュール単位で独立実装し、テスト時に差し替え可能。
  - API リトライ・フェイルセーフの一貫した取り扱いにより、API 障害時もシステム継続を優先。

### 変更（Changed）
- 初回リリースのため該当なし。

### 修正（Fixed）
- 初回リリースのため該当なし。

### 削除（Removed）
- 初回リリースのため該当なし。

### 既知の注意点（Notes）
- 環境変数の必須項目（例）:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, OPENAI_API_KEY（score_news / score_regime 実行時に必要）
- DuckDB を利用する前提の SQL 実装が多数あるため、互換性のある DuckDB バージョンでの動作を想定しています（executemany の空リスト制約等を考慮した実装あり）。
- OpenAI API は JSON Mode を期待するプロンプト・レスポンス設計になっています。モデルや SDK の将来的な変更によりパース処理の調整が必要になる可能性があります。

---

(この CHANGELOG はコードベースの現在実装内容から推測して作成しています。実際のリリースノートとして公開する際は、テスト結果や運用上の変更を反映してください。)