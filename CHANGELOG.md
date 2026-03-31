CHANGELOG
=========
All notable changes to this project will be documented in this file.

フォーマットは Keep a Changelog に準拠しています。  
リリース日 YYYY-MM-DD の形式で日付を記載しています。

[Unreleased]
------------

- （現在未リリースの変更はありません）

[0.1.0] - 2026-03-31
-------------------

Added
- 初版リリースを公開。
- パッケージのエントリポイントを追加:
  - kabusys.__version__ = "0.1.0"
  - __all__ に data, strategy, execution, monitoring を公開。
- 設定 / 環境変数管理:
  - kabusys.config モジュールを追加。
  - .env ファイルおよび環境変数の自動ロード機能を実装（プロジェクトルートを .git / pyproject.toml で検出）。
  - .env パーサは export 形式、シングル/ダブルクォート、エスケープ、コメント処理に対応。
  - 環境変数の自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - Settings クラスを提供し、JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、SLACK_BOT_TOKEN、SLACK_CHANNEL_ID、DUCKDB_PATH、SQLITE_PATH、KABUSYS_ENV、LOG_LEVEL などの取得ロジックを内包。
  - env 値の検証（KABUSYS_ENV / LOG_LEVEL の許容値チェック）を実装。
- AI 関連:
  - kabusys.ai.news_nlp: ニュース記事を OpenAI（gpt-4o-mini）でバッチ解析し、銘柄ごとのセンチメント（ai_scores）を計算・保存する機能を実装。
    - 前日15:00 JST ～ 当日08:30 JST のウィンドウ計算（UTC 変換）を提供。
    - バッチサイズ、記事数・文字数上限、JSON mode の応答バリデーション、傾向スコアの ±1.0 クリップ、再試行（429/ネットワーク/タイムアウト/5xx）を実装。
    - 部分失敗に対しては既存スコアを保護するため、書き込み時に対象コードのみ DELETE → INSERT を行う。
  - kabusys.ai.regime_detector: ETF 1321 の 200 日移動平均乖離（重み70%）とニュース由来のマクロセンチメント（重み30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定・保存する機能を実装。
    - OpenAI 呼び出し、リトライ、フェイルセーフ（API失敗時は macro_sentiment=0.0）を備える。
    - DuckDB 上の prices_daily / raw_news / market_regime を参照・更新（冪等書き込み）。
  - AI モジュールは共通ユーティリティをモジュール間で直接共有せず、各モジュールで独立して OpenAI 呼び出しラッパーを持つ設計。
- Data / ETL / カレンダー / 解析:
  - kabusys.data.pipeline: ETL パイプライン用の ETLResult データクラスを実装（取得件数・保存件数・品質問題・エラー概要を保持）。
  - kabusys.data.etl で ETLResult を再エクスポート。
  - kabusys.data.calendar_management: JPX カレンダー管理、営業日判定、next/prev_trading_day、get_trading_days、is_sq_day、calendar_update_job（J-Quants からの差分取得と冪等保存）を実装。
    - market_calendar が未取得の場合は曜日ベース（土日除外）でフォールバックする一貫した戦略を採用。
    - calendar_update_job はバックフィル、健全性チェック、J-Quants クライアント呼び出しの例外ハンドリングを実装。
  - kabusys.research:
    - factor_research: momentum/volatility/value 等のファクター計算（mom_1m/3m/6m、ma200乖離、ATR20、avg_turnover 等）を実装。DuckDB 上の prices_daily / raw_financials を利用。
    - feature_exploration: 将来リターン計算（calc_forward_returns）、IC（calc_ic）、ランク変換、統計サマリー（factor_summary）を実装。外部ライブラリに依存せず標準ライブラリのみで実装。
    - kabusys.research.__init__ で主要関数を公開（zscore_normalize は kabusys.data.stats から再利用）。
- DuckDB を主要な内部データストアとして利用する SQL 実装を多数追加。SQL と Python を組み合わせた設計で、高速な集計処理を想定。
- ロギングを多用し、情報・警告・例外状況を明示的にログ出力するように実装。

Changed
- （初版のため該当なし）

Fixed
- API 呼び出し失敗時にサービス全体が停止しないよう、ニューススコア／レジーム判定でフェイルセーフ（0.0 やスキップ）にフォールバックする堅牢性を実装。
- DuckDB の executemany に空リストを渡せない問題に対応するため、params が空でない場合のみ executemany を実行する対策を追加。

Security
- （今リリースで特記すべきセキュリティ修正はありません）

Notes / Migration
- 必須の環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID は Settings 経由で必須チェックされます。未設定時は ValueError を発生します。
  - OpenAI API を利用する関数（score_news, score_regime）は api_key 引数または環境変数 OPENAI_API_KEY の設定が必要です。未設定時は ValueError を発生します。
- 環境変数自動読み込み:
  - プロジェクトルート検出 (.git または pyproject.toml) に基づき .env → .env.local の順でロード（.env.local は上書き）。OS 環境変数は保護されます。
  - テスト時に自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- AI 関連:
  - デフォルトモデルは gpt-4o-mini。JSON mode を利用した厳密な JSON 応答を期待するプロンプト設計になっています。
  - バッチサイズ・タイムアウト・リトライ回数等は定数で定義されており、必要に応じて調整可能です。
- DuckDB 互換性:
  - 一部の操作（executemany の空パラメータ等）は DuckDB バージョン依存の挙動に対応するため保護処理を追加しています。
- ルックアヘッドバイアス防止:
  - 多くの分析関数（score_news, score_regime, factor 計算等）は内部で datetime.today()/date.today() を参照せず、target_date を明示的に渡す設計になっています（calendar_update_job のみバッチ実行時に date.today() を使用）。

今後の予定（例）
- strategy / execution / monitoring モジュールの実装・公開（現在はパッケージエントリに名前のみ登録）。
- テストカバレッジ拡充、外部 API 呼び出しのモック化を想定したユニットテスト整備。
- パフォーマンス最適化、追加の品質チェックルール導入。

---

既知の制約
- OpenAI の JSON mode を利用するため、LLM の出力が期待通りでない場合にスコアが取得できないケースがあり、その際はスコアスキップ（空辞書）となります。
- calendar_update_job は J-Quants クライアント実装（jquants_client.fetch_market_calendar / save_market_calendar）に依存します。クライアント実装が必要です。