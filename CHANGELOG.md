CHANGELOG
=========

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。

Unreleased
----------

- 現在未リリースの変更はありません。

[0.1.0] - 2026-03-31
-------------------

Added
- パッケージ初期リリース: kabusys 0.1.0
  - エントリポイントを定義（src/kabusys/__init__.py）。公開モジュール: data, strategy, execution, monitoring。
- 環境設定管理（src/kabusys/config.py）
  - .env/.env.local の自動読み込みをサポート（OS 環境変数優先、.env.local は上書き）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化を実装。
  - .env 行パーサの強化: export プレフィックス対応、シングル/ダブルクォート内のエスケープ処理、インラインコメントの扱いを考慮。
  - OS 環境変数を保護する protected パラメータを導入。
  - Settings クラスを提供し、J-Quants / kabu / Slack / データベース / システム設定をプロパティ経由で取得。未設定時は明示的なエラーを送出するユーティリティを実装。
  - KABUSYS_ENV と LOG_LEVEL の値検証（有効値セットを定義）。
- ニュース NLP（src/kabusys/ai/news_nlp.py）
  - raw_news と news_symbols を基に銘柄ごとのニュース集約を行い、OpenAI（gpt-4o-mini）でセンチメントを評価して ai_scores テーブルへ書き込む機能を実装（score_news）。
  - 時間ウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST）と UTC 変換ロジックを実装。
  - バッチ送信（最大 20 銘柄／チャンク）、記事トリム（記事数・文字数制限）を実装。
  - OpenAI 呼び出しに対する再試行（429/ネットワーク断/タイムアウト/5xx の指数バックオフ）とフォールバック戦略を実装。
  - レスポンス検証ロジックを実装（JSON パースの復元ロジック、results 配列検査、コード整合性、スコアの数値性・有限性、±1.0 クリップ）。
  - DuckDB の executemany の空リスト制約を考慮した安全な置換（DELETE → INSERT）処理を実装。
  - テスト容易性のため OpenAI 呼び出し箇所を patch 可能に設計（_call_openai_api を独立実装）。
- レジーム検出（src/kabusys/ai/regime_detector.py）
  - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次市場レジーム（bull / neutral / bear）を判定し market_regime テーブルへ書き込む機能を実装（score_regime）。
  - prices_daily からの MA 計算（ルックアヘッド防止のため target_date 未満を使用）を実装。データ不足時は中立（1.0）でフォールバック。
  - マクロニュース取得（マクロキーワードでフィルタ）と LLM 呼び出し（gpt-4o-mini）を実装。API 失敗時は macro_sentiment = 0.0 にフォールバック。
  - レジームスコア合成、閾値判定、冪等な DB 書き込み（BEGIN / DELETE / INSERT / COMMIT）を実装。
  - OpenAI 呼び出しも news_nlp とは独立した実装にし、モジュール間の結合を低減。
- 研究（research）モジュール（src/kabusys/research/）
  - factor_research: calc_momentum, calc_volatility, calc_value を実装。
    - Momentum: 1/3/6 ヶ月リターン、200 日 MA 乖離（データ不足時は None）。
    - Volatility: 20 日 ATR、相対 ATR、平均売買代金、出来高比率を計算。
    - Value: raw_financials から最新財務データを取り込み PER・ROE を算出。
    - DuckDB 上で SQL と window 関数を活用する実装（外部 API 不使用）。
  - feature_exploration: calc_forward_returns（複数ホライズンで将来リターン）、calc_ic（Spearman ランク相関による IC）、rank（平均ランク実装）、factor_summary（count/mean/std/min/max/median）を実装。
  - 設計方針として外部ライブラリに依存せず標準ライブラリで実装、ルックアヘッドバイアス回避を明示。
- データ（data）モジュール（src/kabusys/data/）
  - calendar_management:
    - market_calendar ベースの営業日判定ユーティリティを実装（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）。
    - DB 未取得時の曜日ベースフォールバック、DB 値優先の一貫した振る舞いを実装。
    - calendar_update_job を実装（J-Quants API から差分取得、バックフィル、健全性チェック、冪等保存）。
  - ETL / pipeline:
    - ETLResult データクラスを公開して ETL 実行結果の集約を提供（src/kabusys/data/pipeline.py / etl.py）。
    - 差分更新・バックフィル・品質チェック設計の骨子を実装。DuckDB のテーブル存在チェック・最大日付取得等のユーティリティを提供。
  - jquants_client との連携ポイントを用意（fetch/save を呼ぶ設計。実装は外部モジュールに委譲）。
- 操作性・堅牢性の向上
  - DuckDB に対する互換性配慮（executemany の空リスト回避、日付型の安全な変換）。
  - 例外・ログの扱いを統一（失敗時に WARNING/INFO/EXCEPTION を出力し、致命的なケースのみ例外を送出）。
  - ルックアヘッドバイアス防止のため datetime.today() / date.today() の不用意な参照を避ける設計を明記（target_date を明示的引数に取る設計）。

Changed
- N/A（初回リリースのため変更履歴なし）

Fixed
- N/A（初回リリースのため修正履歴なし）

Notes
- OpenAI API（gpt-4o-mini）を利用する機能は API キーが必要です。score_news / score_regime の呼び出し時は api_key 引数または環境変数 OPENAI_API_KEY を設定してください。
- DuckDB スキーマ（prices_daily, raw_news, news_symbols, ai_scores, market_regime, market_calendar, raw_financials 等）を前提としています。データベース初期化・スキーマ定義は別途用意してください。