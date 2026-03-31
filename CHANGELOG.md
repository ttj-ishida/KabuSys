# CHANGELOG

すべての重要な変更は Keep a Changelog の形式に従って記載します。日時はコードベースの最終更新推定日を使用しています。

注: 本 CHANGELOG は提供されたソースコードから推測して作成しています。実際のコミット履歴やリリースノートが存在する場合は、そちらを優先してください。

## [Unreleased]

（なし）

## [0.1.0] - 2026-03-31

追加（Added）
- 基本パッケージ初期化
  - kabusys パッケージを公開（__version__ = "0.1.0"）。主要サブパッケージを __all__ で公開：data, strategy, execution, monitoring。

- 設定 / 環境変数管理（kabusys.config）
  - .env ファイルまたは OS 環境変数から設定値を自動読み込みする機能を実装。
    - プロジェクトルート検出: .git または pyproject.toml を基準に探索（CWD に依存しない）。
    - 読み込み優先順位: OS環境変数 > .env.local > .env。
    - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - .env パーサ実装（export 句対応、シングル/ダブルクォートとバックスラッシュエスケープ、インラインコメント処理）。
  - 保護キー（protected）を使った上書き制御（既存 OS 環境変数を保護）。
  - Settings クラスを提供し、アプリケーション設定をプロパティ経由で取得可能：
    - J-Quants / kabuステーション / Slack / DB パス / 監視しきい値 / 環境モード（development, paper_trading, live）等のプロパティを定義。
    - 必須環境変数が未設定の場合は ValueError を送出する _require() を採用。
    - LOG_LEVEL / KABUSYS_ENV のバリデーションを実装。

- AI（自然言語処理）機能（kabusys.ai）
  - ニュースセンチメントスコアリング（kabusys.ai.news_nlp）
    - raw_news と news_symbols を集約し、銘柄ごとのニュースを OpenAI（gpt-4o-mini）へ送信してセンチメントを算出。
    - バッチ処理（最大 20 銘柄/チャンク）、1銘柄あたり記事数・文字数制限（記事数最大 10 件、文字数最大 3000 文字）を実装してトークン肥大化に対処。
    - JSON Mode を利用したレスポンス処理と厳格なバリデーション（results 配列、code/score チェック、スコア数値化、±1.0 にクリップ）。
    - リトライ戦略: 429（レート制限）・ネットワーク断・タイムアウト・5xx に対して指数バックオフで再試行。その他エラーはスキップしてフェイルセーフ。
    - タイムウィンドウ: target_date に対する JST ベースのウィンドウ計算（前日15:00 JST ～ 当日08:30 JST）を calc_news_window で提供。
    - DB 書き込みは部分失敗耐性を考慮し、スコア取得済み銘柄のみ DELETE → INSERT（トランザクション）で置換。
    - テスト容易性のため、OpenAI 呼び出し箇所は patch で差し替え可能（_call_openai_api を参照）。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して市場レジーム（bull/neutral/bear）を算出。
    - MA 計算は target_date 未満のデータのみを使用してルックアヘッドバイアスを防止。
    - マクロニュース抽出はキーワードベースで raw_news からタイトルを抽出し、OpenAI へ投げて macro_sentiment を取得（記事なし時は LLM 呼び出しを行わない）。
    - OpenAI 呼び出しは冗長なエラー処理（リトライや 5xx 判定）を実装し、失敗時は macro_sentiment=0.0 にフォールバックして処理を継続。
    - 結果は idempotent に market_regime テーブルへ書き込み（BEGIN/DELETE/INSERT/COMMIT）。DB エラー時は ROLLBACK を試行して上位へ例外を伝播。

- データプラットフォーム関連（kabusys.data）
  - カレンダー管理（kabusys.data.calendar_management）
    - JPX マーケットカレンダーを扱うユーティリティ群を提供（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - market_calendar が存在しない場合は曜日ベースのフォールバック（週末を非営業日）を採用。
    - calendar_update_job を実装: J-Quants API から差分取得し market_calendar を冪等的に更新（バックフィル・健全性チェック付き）。
    - 最大探索日数やルックアヘッド、バックフィル日数等の安全機構を実装。
  - ETL / パイプライン（kabusys.data.pipeline, kabusys.data.etl）
    - ETLResult データクラスを公開（ETL の実行結果や品質チェック結果、エラーを集約）。
    - 差分更新、バックフィル、品質チェックの方針をコードで表現（jquants_client 経由の取得 → save_* による冪等保存 → quality チェック）。
    - 内部ユーティリティ: テーブル存在チェック、最大日付取得等を実装。
    - etl モジュールは pipeline.ETLResult を再エクスポート。

- リサーチ / ファクター（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）
    - Momentum: 1M/3M/6M リターン、200日移動平均乖離（ma200_dev）。
    - Volatility / Liquidity: 20日 ATR、相対 ATR、20日平均売買代金、出来高比率。
    - Value: PER（price / EPS、EPS=0 または欠損時は None）、ROE（raw_financials から取得）。
    - DuckDB SQL を用いた実装で prices_daily / raw_financials のみ参照。外部 API や実口座アクセスは行わない。
    - データ不足時の扱い（必要行数未達時は None）やログ出力。
  - 特徴量探索（kabusys.research.feature_exploration）
    - 将来リターン計算: calc_forward_returns（複数ホライズン対応、ホライズン検証、1クエリ設計）。
    - IC（Information Coefficient）計算: calc_ic（Spearman の ρ、コード結合、最小サンプルチェック）。
    - ランキングユーティリティ: rank（同順位は平均ランク、丸めによる ties 対応）。
    - 統計サマリー: factor_summary（count/mean/std/min/max/median を計算、None は除外）。
  - 研究ユーティリティの公開（kabusys.research.__init__）として zscore_normalize を data.stats から再利用可能にした上で複数関数を __all__ で公開。

- その他ユーティリティ
  - 各モジュールでログ出力（logger）を適切に行うように実装。
  - DuckDB をデータストアとして利用することを前提とした SQL 実装とトランザクション処理を多数実装。

変更（Changed）
- 初期リリースのため、後方互換性や既存機能からの変更はなし（新規追加）。

修正（Fixed）
- 初期リリースのため、バグ修正履歴はなし（コード内にエラー処理・フェイルセーフの実装あり）。

注意事項 / ユーザー向け情報
- OpenAI API
  - 各 AI 機能は OpenAI API（gpt-4o-mini）を利用する設計。api_key は関数引数で注入可能（テスト時に差し替えやすい）。引数未指定時は環境変数 OPENAI_API_KEY を参照し、未設定であれば ValueError を投げる。
- 環境変数
  - 必須の環境変数（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等）は Settings のプロパティ経由で取得する際に未設定だと例外が発生するため、実行前に .env を作成するか OS 環境変数を設定してください。
- DB スキーマ依存
  - 多くの関数は DuckDB の特定テーブル（prices_daily, raw_news, news_symbols, ai_scores, market_regime, raw_financials, market_calendar など）を前提とする。実行前にスキーマ・データの準備が必要です。
- テスト容易性
  - OpenAI 呼び出しや一部内部関数は unittest.mock.patch により置き換え可能に実装してあり、ユニットテストの容易化に配慮しています。

将来のリリース候補（推測）
- strategy / execution / monitoring の実装（現在 __all__ に含まれるが、提供コードには未含）。実注文・バックテスト・監視エージェントの追加が想定されます。
- ai モデルやプロンプトの改善、レスポンスフォーマットの堅牢化、J-Quants クライアントの機能拡張。

---

参考:
- 本 CHANGELOG はソースコードの実装内容から推測して作成しています。実際のコミット単位や詳細なマイグレーション情報は含まれていません。必要に応じてリリースノートをコミット履歴やタグと照合してください。