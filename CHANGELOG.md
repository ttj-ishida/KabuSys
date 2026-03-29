# CHANGELOG

すべての変更は Keep a Changelog の形式に従って記載します。バージョン番号はパッケージ内の __version__ を参照しています。

フォーマット:  
- 変更は「Added / Changed / Fixed / Deprecated / Removed / Security」のカテゴリで整理しています。  
- 日付は YYYY-MM-DD 形式です。

## [0.1.0] - 2026-03-29

### Added
- 初回リリース。パッケージ名: kabusys、バージョン 0.1.0。
- パッケージの公開インターフェースを設定（src/kabusys/__init__.py）。
  - __all__ に data, strategy, execution, monitoring を定義（将来的なモジュール構造を示す）。
- 環境変数・設定管理モジュール（src/kabusys/config.py）を追加。
  - プロジェクトルートを .git または pyproject.toml から探索して .env/.env.local を自動ロードする機能を実装。
  - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env パーサを実装（export プレフィックス対応、クォート内のエスケープ処理、インラインコメントの取り扱いなど）。
  - .env の読み込み時に OS 環境変数を保護する protected セットをサポート（.env.local は override=True で上書き）。
  - 必須環境変数を要求する _require 関数と、Settings クラスを提供。
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等を取得するプロパティを持つ。
    - duckdb/sqlite のデフォルトパス、KABUSYS_ENV 検証（development/paper_trading/live）、LOG_LEVEL 検証を実装。
    - is_live/is_paper/is_dev ヘルパーを提供。
- AI モジュール（src/kabusys/ai）を追加。
  - ai/__init__.py で score_news を公開。
  - news_nlp モジュール（src/kabusys/ai/news_nlp.py）
    - raw_news + news_symbols を集約し、OpenAI（gpt-4o-mini）を用いて銘柄ごとのセンチメント（ai_score）を計算して ai_scores テーブルへ書き込む処理を実装。
    - タイムウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST）を calc_news_window で提供。
    - API 呼び出しは JSON Mode を想定、レスポンス検証ロジック（results 配列、code/score のバリデーション、スコアのクリップ）を実装。
    - バッチ処理（最大 20 銘柄/チャンク）、1 銘柄あたりの最大記事数・文字数制限、エクスポネンシャルバックオフによるリトライを実装。
    - テスト容易性のため _call_openai_api を patch して差し替え可能に設計。
  - regime_detector モジュール（src/kabusys/ai/regime_detector.py）
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定し market_regime テーブルへ書き込む処理を実装。
    - マクロキーワードで raw_news をフィルタし、OpenAI へ送信して macro_sentiment を取得。API エラー時はフォールバック値 0.0 を使用（フェイルセーフ）。
    - DuckDB を用いたルックアヘッドバイアス防止（date 比較は target_date 未満、datetime.today() を参照しない設計）。
    - 冪等な DB 書き込み（BEGIN / DELETE / INSERT / COMMIT）を実装。
    - API 呼び出しは独立実装で、テスト時に差し替え可能。
- Research モジュール（src/kabusys/research）を追加。
  - research/__init__.py で主要関数を公開（calc_momentum, calc_value, calc_volatility, zscore_normalize の再エクスポート、calc_forward_returns, calc_ic, factor_summary, rank）。
  - factor_research（src/kabusys/research/factor_research.py）
    - Momentum ファクター: mom_1m, mom_3m, mom_6m, ma200_dev（200 日 MA 乖離）を計算する calc_momentum を実装。データ不足時の None 帰却を明示。
    - Volatility / Liquidity ファクター: 20 日 ATR（atr_20）、相対 ATR（atr_pct）、20 日平均売買代金（avg_turnover）、出来高比率（volume_ratio）を計算する calc_volatility を実装。NULL/データ不足の扱いに注意。
    - Value ファクター: raw_financials から最新財務を取得し PER / ROE を算出する calc_value を実装。EPS が 0 または欠損時は per を None とする。
    - DuckDB ベースの SQL 実装で、価格・財務テーブルのみ参照する安全設計（発注 API 等にはアクセスしない）。
  - feature_exploration（src/kabusys/research/feature_exploration.py）
    - 将来リターン計算（calc_forward_returns）: 指定 horizon（営業日ベース）に対する将来リターンを一括取得する汎用クエリを実装。horizons の検証（1..252）あり。
    - IC（Information Coefficient）計算（calc_ic）: スピアマンのランク相関を計算。有効レコード数が 3 未満の場合は None を返す。
    - ランク変換ユーティリティ（rank）: 同順位は平均ランクで扱う。丸めによる ties を防ぐ工夫あり。
    - 統計サマリー（factor_summary）: count/mean/std/min/max/median を算出するユーティリティ。
    - pandas 等の外部依存を避け、標準ライブラリ + DuckDB で実装。
- Data モジュール（src/kabusys/data）を追加。
  - data/etl.py で pipeline.ETLResult を再エクスポート。
  - pipeline（src/kabusys/data/pipeline.py）
    - ETLResult データクラスを実装（取得件数、保存件数、品質問題、エラーの集約）。to_dict でシリアライズ可能。
    - 差分更新・バックフィル・品質チェックの設計に準拠したユーティリティを実装（DuckDB を前提）。
    - テーブル存在チェック、最大日付取得ユーティリティを提供。
  - calendar_management（src/kabusys/data/calendar_management.py）
    - market_calendar テーブルを使った営業日判定ロジック（is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days）を実装。DB が未取得のときは曜日ベースのフォールバックを行う。
    - calendar_update_job を実装し、J-Quants API から差分取得して market_calendar を冪等更新（バックフィル・健全性チェックあり）。
    - 最大探索日数、先読み日数、バックフィル日数、健全性の閾値を定義して無限ループ・異常値を防止。
  - jquants_client を想定した fetch/save の呼び出しに対応（実装箇所との連携を想定）。
- テストしやすさに配慮
  - OpenAI 呼び出し点（news_nlp._call_openai_api / regime_detector._call_openai_api）を patch できるようにしてユニットテストでの外部依存除去を容易にした。

### Changed
- （該当なし）初回リリースのため変更履歴はありません。

### Fixed
- （該当なし）初回リリースのため修正履歴はありません。

### Deprecated
- （該当なし）

### Removed
- （該当なし）

### Security
- 環境変数を通じた API キーおよびパスワード取得の仕組みを提供。機密情報の扱いには .env/.env.local の運用上の注意が必要（.env.local が優先で上書きされることに留意）。

---

注意事項・設計上の重要点（要約）
- ルックアヘッドバイアス回避: AI スコアリング・レジーム判定・ファクター計算などの関数は datetime.today() / date.today() を内部で参照せず、必ず target_date 引数に依存します。これによりバックテストでの正確性を担保します。
- フェイルセーフ設計: OpenAI 呼び出しや外部 API の一部失敗はサービス全体を停止させず、フォールバック値やスキップとして継続する設計です（例: macro_sentiment=0.0、空のスコアチャンクのスキップ等）。
- DuckDB 前提: データ操作は DuckDB 接続を受け取り SQL で完結するよう設計されており、executemany の空リスト制約や日付型の扱いなど DuckDB の挙動に依存した実装上の配慮があります。
- 環境設定: Settings クラスで必須キーが未設定のときは明示的に ValueError を発生させます。KABUSYS_ENV / LOG_LEVEL には明確な許容値検証を行います。

今後の予定（例）
- strategy / execution / monitoring モジュールの実装（__all__ に含まれているため、次版で公開予定）。
- より細かい品質チェックモジュール（data.quality）の実装と ETL パイプラインの統合テスト強化。
- OpenAI API 抽象化レイヤの整備（ローカルテスト・モックの利便性向上）。

もし CHANGELOG に追記したい差分（追加した機能の強調、既知の制限、互換性注意点など）があれば教えてください。必要に応じて Unreleased セクションを作成して今後の変更を記録できます。