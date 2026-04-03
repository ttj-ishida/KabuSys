# CHANGELOG

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。

全般
- リリース方針: このプロジェクトは semver を想定しており、本ドキュメントはリリースごとに更新します。

## [0.1.0] - 2026-04-03

初回公開リリース。日本株自動売買システム「KabuSys」のコア機能群を実装・公開しました。主な内容は以下の通りです。

### 追加 (Added)
- パッケージ基盤
  - パッケージルートとバージョン情報を追加 (kabusys.__version__ = 0.1.0)。
  - モジュール公開インターフェースの整理 (__all__ に data, strategy, execution, monitoring を追加)。

- 設定・環境変数管理 (kabusys.config)
  - .env / .env.local の自動ロード機能を実装（プロジェクトルートは .git または pyproject.toml を基準に探索）。
  - export 付き行やクォート・エスケープ、インラインコメントを考慮した .env のパーサーを実装。
  - OS 環境変数を保護する protected キーの概念を導入し、.env.local で上書き可能に。
  - 自動ロードを無効化する環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - Settings クラスを導入し、J-Quants / kabuステーション / LINE / DB パス / 監視パラメータ / ログレベル / 環境種別等をプロパティとして提供。未設定の必須変数に対しては明確な例外を発生。
  - 環境値の妥当性チェック（KABUSYS_ENV, LOG_LEVEL の許容値検査）を実装。

- AI（自然言語処理）関連 (kabusys.ai)
  - ニュース NLP スコアリング (kabusys.ai.news_nlp)
    - raw_news と news_symbols を元に銘柄ごとのニュースを集約し、OpenAI（gpt-4o-mini）を用いて銘柄ごとのセンチメント（-1.0〜1.0）を算出。
    - バッチ処理（最大20銘柄/チャンク）、トークン肥大化対策（記事数上限・文字数トリム）を実装。
    - JSON Mode のレスポンス検証と頑健なパースロジック（前後余分なテキストを含む場合の復元）を実装。
    - 429/ネットワーク断/タイムアウト/5xx に対する指数バックオフリトライ対応。失敗時はスキップして継続（フェイルセーフ）。
    - DuckDB への書き込みは部分失敗に備え、対象コードのみ DELETE → INSERT の冪等置換を行う（executemany の空リスト制約に考慮）。
    - 公開 API: score_news(conn, target_date, api_key=None) → 書き込み銘柄数を返す。

  - 市場レジーム判定 (kabusys.ai.regime_detector)
    - ETF 1321 の 200 日移動平均乖離（重み70%）と、マクロ経済ニュースの LLM センチメント（重み30%）を合成して、市場レジーム（bull/neutral/bear）を日次判定。
    - prices_daily / raw_news / market_regime を参照し、duckdb に対して冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）を行う。
    - ルックアヘッドバイアス防止のため date の扱いを厳格にし、target_date 未満のデータのみを使用する設計。
    - OpenAI 呼び出しは独立実装でモジュール結合を避け、API エラー時は macro_sentiment=0.0 として継続（フェイルセーフ）。
    - 公開 API: score_regime(conn, target_date, api_key=None) → 成功時 1 を返す。

- データ基盤 (kabusys.data)
  - カレンダー管理 (kabusys.data.calendar_management)
    - JPX カレンダーの夜間バッチ更新ジョブ calendar_update_job を実装（J-Quants API から差分取得・冪等保存）。
    - 営業日判定・前後営業日取得・期間内営業日取得・SQ判定などのユーティリティ（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）を実装。DB が未取得の場合は曜日ベースのフォールバックを使用。
    - 最大探索日数やバックフィル・健全性チェックを導入し無限ループや異常値へ対処。

  - ETL パイプライン (kabusys.data.pipeline, kabusys.data.etl)
    - ETLResult データクラスを実装し、ETL実行結果（取得数・保存数・品質問題・エラー等）を構造化して返却可能に。
    - 差分更新・バックフィル・品質チェックの方針に基づく設計を実装（jquants_client と quality モジュールを利用する想定）。
    - data.etl モジュールで ETLResult を再エクスポート。

- リサーチ / ファクター (kabusys.research)
  - ファクター計算 (kabusys.research.factor_research)
    - Momentum, Volatility, Value, Liquidity などの定量ファクターを実装:
      - calc_momentum(conn, target_date): mom_1m/mom_3m/mom_6m / ma200_dev（データ不足時は None）
      - calc_volatility(conn, target_date): atr_20, atr_pct, avg_turnover, volume_ratio（データ不足時は None）
      - calc_value(conn, target_date): per, roe（最新の raw_financials を用いる。EPS欠損時は None）
    - DuckDB 内の SQL とウィンドウ関数を多用し、外部 API に依存しない実装。
  - 特徴量探索 (kabusys.research.feature_exploration)
    - calc_forward_returns(conn, target_date, horizons=None): 各ホライズンの将来リターンを一括クエリで取得。
    - calc_ic(factor_records, forward_records, factor_col, return_col): スピアマンのランク相関（IC）を実装（有効レコード 3 未満は None）。
    - factor_summary(records, columns): count/mean/std/min/max/median を計算。
    - rank(values): 同順位は平均ランクとする安定的なランク関数実装。
  - research パッケージの __all__ を通じて主要関数群を公開（zscore_normalize は data.stats から再利用）。

### 変更 (Changed)
- （初回リリースのため該当なし）

### 修正 (Fixed)
- （初回リリースのため該当なし）

### 注意事項 / 既知の制約 (Notes / Known limitations)
- OpenAI API
  - score_news / score_regime は OpenAI API キー（api_key 引数または環境変数 OPENAI_API_KEY）が必須。未設定時は ValueError を送出。
  - LLM 呼び出しは外部ネットワークに依存し、ネットワーク障害時は対象データをスキップして継続する設計（安全に中立扱いを採用）。
  - JSON レスポンスのパースは冗長テキストを復元する処理を行うが、完全に保証はできないためパース失敗時はそのチャンクをスキップする。
- DB（DuckDB）関連
  - executemany に空リストを渡せない環境（DuckDB 0.10 等）を考慮した実装になっているため、空リスト処理に注意。
  - ETL / AI 書き込みは部分失敗に備え、対象コードのみを削除してから挿入することで既存データの保護を行う。
- 一部指標未実装
  - calc_value では現フェーズで PBR・配当利回りなどは未実装（注記あり）。
- ルックアヘッドバイアス対策
  - AI / リサーチモジュールは内部で datetime.today() / date.today() をそのまま参照しないよう設計。すべて target_date に依存するため再現性が高い。
- テスト容易性
  - OpenAI 呼び出し用の内部関数（_call_openai_api 等）は unittest.mock.patch による差し替えを想定している。

### セキュリティ (Security)
- .env 読み込み時に OS 環境変数を保護する仕組みを導入（既存の OS 環境変数は .env により上書きされないよう保護）。.env.local は override=True により上書き可能で、テスト時に明示的に自動ロードを無効化できるフラグを提供。

---

今後の予定（例）
- strategy / execution / monitoring モジュールの実装・公開（現時点ではパッケージエントリは存在するが具象実装は差分で追加予定）。
- J-Quants クライアント周りの統合テストと運用観点のログ強化。
- AI プロンプト改善・モデル選定の見直し（コスト/精度のトレードオフ）。

変更や問題点の報告、改善提案は Pull Request / Issue で歓迎します。