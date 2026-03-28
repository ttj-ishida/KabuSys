# Changelog

すべての注目すべき変更をここに記録します。  
フォーマットは「Keep a Changelog」に準拠し、セマンティック バージョニングを使用します。

## [Unreleased]

## [0.1.0] - 2026-03-28
初回リリース — 日本株自動売買 / 研究・データ基盤の初期実装を追加。

### 追加 (Added)
- パッケージ初期化
  - kabusys パッケージの __version__ を 0.1.0 に設定。主要サブパッケージを __all__ に公開（data, strategy, execution, monitoring）。

- 設定 / 環境変数管理 (src/kabusys/config.py)
  - .env/.env.local をプロジェクトルート (.git または pyproject.toml 基準) から自動読み込みする仕組みを実装。
  - .env ファイルパーサ実装（コメント、export プレフィックス、シングル/ダブルクォート、エスケープ対応）。
  - 自動ロード無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - 環境変数保護機能（OS 環境変数を protected set として上書きから防止）。
  - Settings クラスを提供し、J-Quants / kabu API / Slack / DB パスなど主要設定（取得とバリデーション）をプロパティで公開。
  - KABUSYS_ENV と LOG_LEVEL の許容値チェック、is_live / is_paper / is_dev ヘルパーを追加。

- AI モジュール (src/kabusys/ai)
  - news_nlp（src/kabusys/ai/news_nlp.py）
    - raw_news / news_symbols を集約して銘柄ごとのニュースを作成し、OpenAI（gpt-4o-mini）の JSON mode を使ってセンチメント評価を行い ai_scores に書き込む処理を実装。
    - バッチ処理（1 API 呼び出しあたり最大 20 銘柄）、記事数・文字数トリム（最大記事数/文字数）を実装。
    - リトライロジック（429/ネットワーク断/タイムアウト/5xx に対する指数バックオフ）を導入。
    - レスポンスバリデーション（JSON 抽出・results 配列・code/score 検証）とスコアの ±1.0 クリップ。
    - ルックアヘッドバイアス回避（target_date を引数に取り datetime.today() を参照しない）。
    - テスト容易性のため OpenAI 呼び出し関数を差し替え可能に設計（unit test 用のパッチポイントを用意）。

  - regime_detector（src/kabusys/ai/regime_detector.py）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次市場レジーム（bull/neutral/bear）を算出・market_regime テーブルへ冪等書き込み。
    - マクロニュース抽出（キーワードベース）、OpenAI 呼び出し（gpt-4o-mini）、API リトライ・フェイルセーフ（失敗時 macro_sentiment=0.0）。
    - レジーム合成・閾値、ログ出力を実装。
    - テスト用に OpenAI 呼び出しを差し替え可能。

  - ai.__init__ で score_news をエクスポート。

- リサーチ（因子・特徴量）モジュール (src/kabusys/research)
  - factor_research（src/kabusys/research/factor_research.py）
    - モメンタム（1M/3M/6M）、200 日 MA 乖離、ATR（20日）、出来高・売買代金系指標、PER/ROE（raw_financials から）などの定量ファクター計算を実装。
    - DuckDB を用いた SQL ベースの計算で、prices_daily / raw_financials のみ参照（実取引 API は参照しない）。
    - データ不足時の None 処理、ログ出力あり。
  - feature_exploration（src/kabusys/research/feature_exploration.py）
    - 将来リターン計算（horizons: デフォルト [1,5,21]、任意指定、最大 252 日制約）、IC（Spearman ランク相関）計算、rank 関数（同順位の平均ランク処理）、ファクター統計サマリー関数を実装。
    - pandas 等に依存しない純標準ライブラリ実装。
  - research.__init__ で主要関数を再エクスポート（calc_momentum, calc_value, calc_volatility, zscore_normalize, calc_forward_returns, calc_ic, factor_summary, rank）。

- データ基盤モジュール (src/kabusys/data)
  - calendar_management（src/kabusys/data/calendar_management.py）
    - market_calendar を用いた営業日判定ユーティリティ（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）を実装。DB にデータがない場合は曜日ベースでフォールバック。
    - calendar_update_job を実装：J-Quants（jquants_client）からカレンダー差分取得 → 冪等保存（ON CONFLICT 相当）・バックフィル・健全性チェックを実装。
  - pipeline / ETL（src/kabusys/data/pipeline.py, src/kabusys/data/etl.py）
    - ETLResult dataclass（ETL 実行結果の構造化、品質チェック問題やエラー一覧の保持、シリアライズ用 to_dict）を実装し etl.py で公開。
    - ETL 補助ユーティリティ（テーブル存在チェック、最大日付取得）を実装。
    - ETL 設計方針に沿った差分取得・バックフィル・品質チェック連携のための基盤を準備。
  - data.__init__ を追加（空の公開ポイントとして準備）。

### 変更 (Changed)
- 実装方針・設計上の注意点をコード中に明記（主にドキュメント文字列）。
  - 全ての日付処理でルックアヘッドバイアスを避けるため datetime.today()/date.today() を参照しない設計が採用されている箇所を明示。
  - DuckDB の executemany に関する互換性考慮（空リストは不可）に基づく保護ロジックを実装。

### 修正 (Fixed)
- N/A（初回リリースのため過去のバグ修正履歴はなし）。

### セキュリティ (Security)
- API キーの取り扱いは引数注入または環境変数参照とし、未設定時は ValueError を投げる明示的なチェックを実装（OpenAI/Slack/J-Quants 等の必須キー）。

### その他 / 実装上の注記
- OpenAI 呼び出しは JSON Mode を使用し、レスポンスの堅牢な解析とフォールバックを重視（JSON 前後ノイズの抽出など）。
- 多くの外部 API 呼び出し周りに対して再試行戦略（指数バックオフ）を実装し、最終的な失敗はスキップしてフェイルセーフ（例: macro_sentiment=0.0、該当チャンクスキップ）を適用。
- DuckDB をメイン DB として使用する前提の SQL 実装。日付型の扱いに注意している（to_date ユーティリティ等）。
- テストしやすさを考え、内部の OpenAI 呼び出し関数はモジュール単位で差し替え可能に設計（unittest.mock.patch による置換を想定）。

--- 

今後のリリースでは、機能拡張（発注ロジック、モニタリング・実行層）、テストカバレッジ強化、パフォーマンス最適化、ドキュメント・使用例の追加を予定しています。