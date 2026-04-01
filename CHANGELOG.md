# CHANGELOG

このプロジェクトでは Keep a Changelog の形式に準拠して変更履歴を管理します。  
日付は本コードベースのスナップショット（src/ 以下の実装）に基づき推測しています。

すべての重要な変更は semver に従ってバージョン付けされます。

なお、本CHANGELOGはコード内容から推測して作成しています。実際のリリースノート作成時はコミットログやリリース手順に合わせて調整してください。

## [Unreleased]
- 当面のリリース予定なし（初期公開：0.1.0）。

## [0.1.0] - 2026-04-01
初回リリース。以下の主要機能と実装方針を含みます。

### Added
- パッケージ基盤
  - kabusys パッケージ（__version__ = 0.1.0）。公開モジュール: data, strategy, execution, monitoring。

- 環境設定管理 (kabusys.config)
  - .env/.env.local ファイルと OS 環境変数を統合して設定をロードする自動読み込み機能を実装。
  - 自動ロードを無効化するフラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - .env パーサ (_parse_env_line) は export プレフィックス、クォート、エスケープ、インラインコメント等に対応。
  - .env と .env.local の優先度: OS 環境変数 > .env.local > .env（.env.local は上書き許可）。
  - protected（OS 環境変数）キーを考慮した上書き制御。
  - Settings クラスを提供し、J-Quants / kabuステーション / Slack / DB パス / 監視閾値 / ログレベル等のプロパティを取得:
    - 必須項目のチェック（例：JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, KABU_API_PASSWORD）。
    - KABUSYS_ENV と LOG_LEVEL の検証（許容値チェック）。
    - Path 型の返却（duckdb/sqlite/pid ファイル等）および閾値値の型変換。

- AI モジュール (kabusys.ai)
  - ニュース NLP スコアリング (news_nlp.score_news)
    - raw_news / news_symbols を集約し、銘柄ごとにニュースを結合して OpenAI (gpt-4o-mini) に送信してセンチメントを算出。
    - JSON Mode を利用した堅牢なパースとバリデーション実装。
    - バッチ処理（最大 20 銘柄/リクエスト）、1 銘柄あたり記事数・文字数のトリム上限を設定。
    - リトライ戦略（429、ネットワーク断、タイムアウト、5xx に対して指数バックオフ）を実装。
    - レスポンス妥当性チェック（results 配列、code/score の型チェック、スコアのクリッピング ±1.0）。
    - API 未設定時は ValueError を返す。API 失敗時は個別チャンクをスキップして処理継続するフェイルセーフ設計。
    - 時間ウィンドウ計算（JST 前日 15:00 ～ 当日 08:30 相当）calc_news_window を提供。
    - 書き込みは部分成功を考慮し、取得済みコードのみ DELETE → INSERT で置換（冪等性と部分失敗時の保護）。

  - 市場レジーム判定 (regime_detector.score_regime)
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロセンチメント（重み 30%）を合成して market_regime テーブルへ日次判定結果を書き込み。
    - マクロセンチメントは別途抽出したマクロ関連ニュースタイトル群を LLM（gpt-4o-mini）へ渡して JSON レスポンスを期待。
    - LLM 呼び出しはリトライ（指数バックオフ）や 5xx 処理を備え、最終的に失敗した場合は macro_sentiment=0.0 にフォールバック（例外を上げず継続）。
    - ma200_ratio の算出は target_date 未満のデータのみ使用し、データ不足時は中立（1.0）にフォールバック。ルックアヘッドバイアス回避の方針を明示。
    - market_regime テーブルへの書き込みはトランザクションで冪等（DELETE / INSERT）にしている。

- データ基盤 (kabusys.data)
  - calendar_management
    - JPX カレンダー管理（market_calendar）: is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を提供。
    - DB 登録値優先、未登録日は曜日ベースのフォールバック（週末除外）で一貫した振る舞い。
    - calendar_update_job：J-Quants API から差分取得して market_calendar を冪等更新。バックフィルと健全性チェック（未来日付上限）を実装。
  - pipeline / etl
    - ETLResult データクラスを公開（ETL の取得数・保存数・品質問題・エラー一覧などを保持）。
    - ETL の設計方針として差分更新、backfill、品質チェックの集約（Fail-Fast ではなく全件収集）を採用。
    - 内部ユーティリティ：テーブル存在チェック、最大日付の取得など。

- 研究用モジュール (kabusys.research)
  - factor_research
    - モメンタム（1M/3M/6M）、200日MA乖離、ATR（20日）、出来高・売買代金指標、PER/ROE（raw_financials から）等を DuckDB 上で計算する関数を提供：
      - calc_momentum, calc_volatility, calc_value
    - データ不足時の None 扱い、DuckDB のウィンドウ関数を活用した実装。
    - すべての計算は prices_daily / raw_financials のみ参照し、本番取引 API へ触れない設計。
  - feature_exploration
    - 将来リターン計算（calc_forward_returns）: 任意ホライズンの fwd_* を一度のクエリで取得。
    - IC（calc_ic）: スピアマンランク相関の計算（ties を平均ランクで扱う）。
    - ランク関数（rank）とファクター統計サマリー（factor_summary）を実装。
    - pandas 等の外部ライブラリに依存しない純標準ライブラリ実装。

- 実装上の共通設計・品質ポイント
  - ルックアヘッドバイアス対策: date.today()/datetime.today() を直接参照しない関数設計（ターゲット日を引数で与える）。
  - IDempotent な DB 書き込み（DELETE → INSERT や ON CONFLICT 想定）を優先。
  - OpenAI 呼び出しのパスはテスト容易性を考慮し差し替え可能（モジュール内の _call_openai_api を patch 対象に想定）。
  - DuckDB を主要な分析 DB として使用。DuckDB バージョン相違（executemany の空リスト 等）に配慮した保護コードを含む。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- OpenAI API キーは引数で注入可能かつ環境変数 OPENAI_API_KEY を参照する方式。未設定時は ValueError を発生させることで誤使用を防止。

## 将来の検討事項（コードから推測）
- AI モジュールのモデル切替設定を外部化（設定でモデル指定可能にする）
- ai_scores / market_regime 等の書き込みに対するトランザクション監査ログ追加
- エラー集計・アラート（Slack 通知など）を監視モジュールと連携
- テストカバレッジ拡充：OpenAI 呼び出しのモックや DuckDB を使った統合テスト

---

参考: 本CHANGELOGは src/ 以下の実装内容をもとに推測して作成しています。実際の変更履歴として公開する際は、コミット履歴・差分・リリースノート原本を元に調整してください。