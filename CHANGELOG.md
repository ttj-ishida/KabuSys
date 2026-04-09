# Changelog

すべての注目に値する変更点を記録します。  
このファイルは「Keep a Changelog」に準拠しています。  

## [0.1.0] - 2026-04-09

### 追加 (Added)
- 基本パッケージ構成を追加
  - パッケージエントリポイント: kabusys.__init__ を導入（version = 0.1.0、公開モジュール: data, strategy, execution, monitoring）。
- 環境設定・読み込み機能を実装 (kabusys.config)
  - .env ファイルまたは環境変数から設定を読み込む自動ロード機能を実装（読み込み優先度: OS 環境変数 > .env.local > .env）。
  - プロジェクトルート特定ロジックを導入（.git または pyproject.toml を起点に探索）。プロジェクトルート未特定時は自動ロードをスキップ。
  - .env パーサーの強化:
    - `export KEY=val` 形式に対応。
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理をサポート。
    - クォートなしの行でのインラインコメント処理（直前が空白/タブ時のみコメント認識）。
  - 読み込み時の上書き/保護ロジック（override, protected）を実装し、OS 環境変数の保護をサポート。
  - 設定取得ラッパー Settings を実装。主なプロパティ:
    - J-Quants / kabu ステーション / LINE Messaging / DB パス（duckdb, sqlite） / paper trading 設定（PAPER_FILL_MODE, PAPER_TRADING_SQLITE_PATH） / 監視用ファイルパス（PID, kill flag） / システム env, log_level 判定・検証メソッド等。
    - 設定値のバリデーションを実装（例: KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE の有効値チェック）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化を実装（テストで利用可能）。
- AI モジュール (kabusys.ai)
  - ニュース NLP スコアリング (kabusys.ai.news_nlp)
    - raw_news と news_symbols を集約して銘柄ごとのニュースを作成し、OpenAI（gpt-4o-mini）へバッチ送信してセンチメントを算出。
    - タイムウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST（UTC に変換して DB クエリ実行）。calc_news_window を提供。
    - バッチ処理（1 API コールあたり最大 20 銘柄）、1 銘柄あたり記事数/文字数上限（_MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK）を導入しトークン肥大化を抑制。
    - JSON Mode を使用したレスポンスパースと厳密なバリデーションを実装（results リスト・code/score の検証、スコアの ±1.0 クリップ）。
    - リトライ戦略: 429・ネットワーク断・タイムアウト・5xx を指数バックオフで再試行。その他エラーはスキップして継続するフェイルセーフ設計。
    - DuckDB への書き込みは部分置換方式（DELETE → INSERT、空リスト取り扱いに配慮）で冪等化。
    - OpenAI 呼び出しはテスト差し替えしやすいように内部関数化（_call_openai_api）。
  - 市場レジーム判定 (kabusys.ai.regime_detector)
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロ経済ニュースの LLM センチメント（重み 30%）を合成して日次のレジーム判定（'bull' / 'neutral' / 'bear'）を実装。
    - ma200_ratio 計算 (_calc_ma200_ratio) は target_date 未満のデータのみを使用しルックアヘッドバイアスを防止。不足時は中立値 (1.0) を使用。
    - マクロニュース抽出（_fetch_macro_news）と LLM スコアリング（_score_macro）を実装。API エラー時は macro_sentiment=0.0 フォールバック。
    - OpenAI 呼び出しはリトライ・5xx 判定・バックオフを行い、最終結果を market_regime テーブルへトランザクション（BEGIN/DELETE/INSERT/COMMIT）で冪等保存。
    - 設計上、datetime.today()/date.today() を直接参照しない実装でルックアヘッド回避。
- リサーチ／因子計算モジュール (kabusys.research)
  - factor_research: Momentum / Value / Volatility / Liquidity 等の定量ファクター計算を実装。
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）を DuckDB SQL で高速に算出。データ不足時は None を返す仕様。
    - calc_volatility: 20 日 ATR（単純平均）、相対 ATR（atr_pct）、20 日平均売買代金・出来高比率などを計算。
    - calc_value: raw_financials からの最新財務データと当日の株価を組み合わせ PER / ROE を算出。
  - feature_exploration: 将来リターン、IC（Information Coefficient）、統計サマリー等を実装。
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンをまとめて取得。horizons のバリデーションを実施。
    - calc_ic: factor_records と forward_records を code で結合し、Spearman のランク相関（IC）を計算。有効レコードが 3 未満の場合は None。
    - rank: 同順位は平均ランクで処理（丸めによる ties 対応）。
    - factor_summary: count/mean/std/min/max/median を計算する統計サマリー。
  - research パッケージの public exports を整理（zscore_normalize をデータ層から再利用するなど）。
- データ層 (kabusys.data)
  - calendar_management: JPX カレンダー管理と営業日判定ロジックを実装。
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days を提供。
    - DB（market_calendar）にデータがある場合は DB 値優先、未登録日は曜日ベースでフォールバックする一貫した挙動。
    - calendar_update_job: J-Quants API から差分取得して market_calendar を冪等に更新。バックフィル・先読み・健全性チェック（将来日付が大きすぎる場合のスキップ）を実装。
  - ETL パイプライン基盤 (kabusys.data.pipeline / etl)
    - ETLResult dataclass を導入し、取得件数・保存件数・品質問題リスト・エラーリスト等を格納。to_dict による辞書化をサポート。
    - pipeline モジュールは差分取得・保存（jquants_client 経由）・品質チェック（quality モジュール）という設計方針を実装。
    - kabusys.data.etl で ETLResult を再エクスポート。

### 変更 (Changed)
- なし（初期リリース）

### 修正 (Fixed)
- なし（初期リリース）

### セキュリティ (Security)
- なし

---

注記:
- 全体的に「ルックアヘッドバイアス防止」を意識した設計が適用されています（datetime.today()/date.today() を直接参照しない、DB クエリで排他条件を指定する等）。
- OpenAI 絡みの処理は外部 API の不安定性を考慮し、リトライ・フォールバック（0.0 のスコア）・部分失敗時の DB 保護（書き込み対象のコードを絞る）などフェイルセーフ設計になっています。
- DuckDB を主要なデータベースとして利用する前提の SQL 実装と、DuckDB の特性（executemany の空リスト不可等）への対応が含まれます。

（初版 v0.1.0: 基本機能群の実装）