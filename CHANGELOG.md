Keep a Changelog に準拠した CHANGELOG.md（日本語）
すべての注目すべき変更を記録します。バージョン番号はパッケージ内の __version__（0.1.0）に合わせています。

Unreleased
----------
（なし）

0.1.0 - 2026-03-29
-----------------
初回リリース。日本株自動売買・データ基盤・リサーチ・AI ユーティリティ群を含む基本機能を実装しました。

Added
- パッケージ基礎
  - パッケージ初期化: kabusys.__init__ にてバージョン "0.1.0" と主要サブパッケージ（data, research, ai, ...）を公開。
- 環境設定管理
  - Settings クラスを実装（kabusys.config）。
    - 環境変数から J-Quants / kabuステーション / Slack / DB パス / ログ等を取得するプロパティを提供。
    - env 値・LOG_LEVEL の妥当性検証を実装（許容値セットのチェック）。
    - 必須変数未設定時には明示的な ValueError を送出する _require を提供。
  - .env 自動ロード機能を実装（プロジェクトルートを .git / pyproject.toml から探索）。
    - 読み込み順序: OS 環境 > .env.local（override）> .env（未上書き）。
    - .env の行パーサ（クォート、export プレフィクス、インラインコメント、エスケープ処理をサポート）。
    - 自動ロードを無効化する環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD を用意（テストでの利用想定）。
    - OS 環境変数を保護する protected キーセットを考慮した上書き処理。
- AI（自然言語 / レジーム判定）
  - ニュースNLP スコアリング（kabusys.ai.news_nlp）
    - raw_news / news_symbols から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini）にバッチ（最大20銘柄/チャンク）で投げてセンチメントを取得。
    - 入力トークン肥大化対策（1銘柄あたり最大記事数・文字数のトリム）。
    - エラー耐性: 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフリトライ実装。
    - JSON 解析のロバスト化（前後に余計なテキストが混ざる場合に {} を抽出して復元）。
    - レスポンス検証ロジック（results リスト、code の照合、スコアの数値チェック、±1.0 クリップ）。
    - 成果は ai_scores テーブルへ冪等的に書き込む（該当コードのみ DELETE → INSERT）。
    - テスト容易性: _call_openai_api を patch で差し替え可能に設計。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（Nikkei 225 連動）の 200日移動平均乖離（重み 70%）と、マクロニュースの LLM センチメント（重み 30%）を合成して日次レジーム判定（bull/neutral/bear）。
    - prices_daily / raw_news からデータ取得、OpenAI 呼び出し（JSON mode）とスコア合成、market_regime へ冪等書き込み。
    - LLM 呼び出し失敗時は macro_sentiment = 0.0 にフォールバック（フェイルセーフ）。
    - API 呼び出しでの 5xx / レートリミット / 接続エラーに対するリトライとログ出力。
    - ルックアヘッドバイアス対策: datetime.today()/date.today() を参照せず、prices_daily クエリは target_date 未満のデータのみを使用。
- Data（ETL / カレンダー / パイプライン）
  - ETL パイプラインの結果型 ETLResult を実装（kabusys.data.pipeline / kabusys.data.etl で再エクスポート）。
    - 取得・保存件数、品質チェック結果、エラー一覧などをまとめて返す構造体。
    - has_errors / has_quality_errors / to_dict を提供。
  - 市場カレンダー管理（kabusys.data.calendar_management）
    - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day を実装。
    - market_calendar が未取得の場合は曜日ベース（土日除く）でフォールバックする一貫した挙動。
    - カレンダー夜間バッチ（calendar_update_job）を実装：J-Quants から差分取得 → 冪等保存、バックフィル、健全性チェック（将来日付制限）。
    - 最大探索範囲制限や NULL 値の検出時のログ出力など堅牢性を確保。
  - ETL パイプラインユーティリティ（kabusys.data.pipeline）
    - 差分更新・バックフィル・品質チェック連携を行うための基盤ロジック（関数群の一部を実装、ETLResult を提供）。
    - DuckDB の最大日付取得やテーブル存在チェックなどの汎用ユーティリティを実装。
- Research（ファクター計算・特徴量探索）
  - ファクター計算（kabusys.research.factor_research）
    - calc_momentum: 1M/3M/6M リターン、200日 MA 乖離（ma200_dev）を計算（prices_daily 参照）。データ不足時は None を返す。
    - calc_volatility: 20日 ATR、相対 ATR（atr_pct）、20日平均売買代金、出来高比率を計算。true_range の NULL 伝播制御あり。
    - calc_value: raw_financials から最新財務を取得して PER / ROE を計算。EPS が 0/欠損時は None。
    - 設計方針として DB（prices_daily, raw_financials）参照のみで外部 API や発注ロジックに依存しない。
  - 特徴量探索（kabusys.research.feature_exploration）
    - calc_forward_returns: 指定ホライズン（デフォルト 1,5,21 営業日）に対する将来リターンを一括 SQL で取得。
    - calc_ic: ファクター値と将来リターンのスピアマンランク相関（IC）を実装。3 銘柄未満で計算不能なら None。
    - rank: 同順位は平均ランクにするランク化実装（丸め処理で浮動小数の ties を適切に扱う）。
    - factor_summary: count/mean/std/min/max/median の統計サマリーを提供。
  - research パッケージのエクスポートを整備（calc_momentum, calc_value, calc_volatility, zscore_normalize の再エクスポートなど）。
- その他
  - 各所に詳細な docstring と設計上の注意（ルックアヘッド回避、DuckDB 互換性、テスト容易性のための差し替えポイント等）を追加。
  - OpenAI クライアント呼び出し周りはモジュール毎に独立実装（モジュール結合を避けるため）。

Changed
- 初回リリースのため変更履歴はなし（新規追加のみ）。

Fixed
- 初回リリースのため修正履歴はなし。

Security
- OpenAI API キーは引数で注入可能（api_key）か環境変数 OPENAI_API_KEY を参照する方式を採用。未設定時は明示的にエラーを出すことで秘密鍵漏洩に対する扱いを明確化。

Notes / 実装上の重要ポイント
- ルックアヘッドバイアス防止: AI / ファクター / ETL など時間ベースの処理で datetime.today()/date.today() を直接参照しない設計（すべて target_date を明示指定）。
- DB 書き込みは可能な限り冪等（DELETE → INSERT、ON CONFLICT を使用する保存関数想定）に設計し、部分失敗時に既存データを不必要に消さないよう配慮。
- OpenAI 呼び出しは堅牢に（JSON パース耐性、指数バックオフ、最大リトライ、非致命的フォールバック）。
- DuckDB 互換性に配慮（executemany に空リストを与えない、日時型変換ユーティリティ等）。
- テストしやすさ: OpenAI 呼び出し部分は patch で差し替え可能にしてユニットテストが行えるよう配慮。

今後の予定（例）
- jquants_client / kabusys.data.jquants_client の実装・テストカバレッジ強化
- ai モジュールの評価ループ（ローカル評価用モック）やスループット改善
- ETL のスケジューリング・監視（monitoring サブパッケージ）との統合
- ドキュメント（StrategyModel.md, DataPlatform.md 等）の補完

索引（主な公開 API）
- kabusys.settings (Settings のインスタンス)
- kabusys.ai.score_news(conn, target_date, api_key=None)
- kabusys.ai.score_regime(conn, target_date, api_key=None)
- kabusys.data.calendar_management: is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day / calendar_update_job
- kabusys.data.etl.ETLResult
- kabusys.research: calc_momentum, calc_value, calc_volatility, calc_forward_returns, calc_ic, factor_summary, rank, zscore_normalize

---  
この CHANGELOG はコードの実装内容から推測して作成しています。追加の変更点やリリースノートの追記があれば反映してください。