# Changelog

すべての注目すべき変更を記録します。これは Keep a Changelog のフォーマットに準拠しています。  

現在のバージョン: 0.1.0（初回リリース）

## [Unreleased]
- なし

## [0.1.0] - 2026-04-03
初回リリース。主にデータ取得/ETL、マーケットカレンダー管理、ファクター計算、ニュース／市場レジームのAIスコアリング、環境設定ユーティリティなどを実装しました。

### 追加 (Added)
- パッケージ基盤
  - パッケージメタ情報: kabusys.__version__ = "0.1.0" を追加。
  - パッケージ公開 API: data, strategy, execution, monitoring を __all__ としてエクスポート。

- 設定・環境変数管理 (kabusys.config)
  - .env ファイル自動ロード機能を実装（プロジェクトルートの検出: .git または pyproject.toml を基準）。
  - ロード順序: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロード無効化。
  - .env パーサ実装: export 形式、クォート内エスケープ、インラインコメントの取り扱い等に対応。
  - Settings クラスを提供し、アプリ固有設定をプロパティ経由で取得（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、KABU_API_BASE_URL、LINE 関連、データベースパス、監視関連パス、閾値、環境/ログレベル検証など）。
  - 環境値バリデーション: KABUSYS_ENV（development/paper_trading/live）、LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL）の検証。

- AI モジュール (kabusys.ai)
  - ニュースNLPスコアリング (kabusys.ai.news_nlp)
    - raw_news + news_symbols を集約し、OpenAI（gpt-4o-mini）へバッチ送信して銘柄ごとのセンチメント (ai_score) を計算。
    - タイムウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST（UTC 換算）を採用。calc_news_window 関数でウィンドウを正確に算出。
    - トークン肥大化対策: 銘柄当たり最大記事数・最大文字数でトリム（_MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK）。
    - バッチ処理: 1回のAPIコールで最大 20 銘柄 (_BATCH_SIZE)。
    - レスポンス検証と堅牢化: JSON 抽出・バリデーション、スコア ±1.0 にクリップ、部分失敗時の DB 保護（対象コードのみ DELETE → INSERT）。
    - 再試行ロジック: 429・ネットワーク断・タイムアウト・5xx に対する指数バックオフリトライ実装。
    - テスト容易性: _call_openai_api を patch で差し替え可能。
    - API キー注入: api_key 引数 or 環境変数 OPENAI_API_KEY を使用。

  - 市場レジーム判定 (kabusys.ai.regime_detector)
    - ETF 1321（NIKKEI 連動 ETF）の 200 日移動平均乖離（重み 70%）とマクロ経済ニュースの LLM センチメント（重み 30%）を合成して日次で regime（'bull' / 'neutral' / 'bear'）を判定。
    - マクロキーワードフィルタで raw_news を抽出、OpenAI（gpt-4o-mini）で macro_sentiment を算出（記事が無ければ LLM 呼び出し無し、API失敗時は 0.0 にフォールバック）。
    - レジームスコア合成式と閾値定義（_MA_WEIGHT, _MACRO_WEIGHT, _BULL_THRESHOLD, _BEAR_THRESHOLD）を実装。
    - 結果を書き込む際は冪等（BEGIN / DELETE / INSERT / COMMIT）で market_regime テーブルを更新。
    - API 呼び出しの再試行・5xx 判定・JSON パース失敗時の安全なフォールバック実装。

- データモジュール (kabusys.data)
  - マーケットカレンダー管理 (kabusys.data.calendar_management)
    - market_calendar を参照して営業日判定・前後営業日の取得・期間内営業日リスト取得・SQ日判定を実装（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - DB が未取得または未登録日の扱いは曜日ベースのフォールバック（主に土日判定）。
    - 最大探索日数や先読み日数、バックフィル、健全性チェックなどの保護ロジックを実装。
    - 夜間バッチ更新ジョブ calendar_update_job を実装（J-Quants クライアント経由で差分取得 → 保存。バックフィルや健全性チェックを含む）。
    - DuckDB 結合に伴う date 型変換ユーティリティ等を提供。

  - ETL パイプライン (kabusys.data.pipeline / kabusys.data.etl)
    - ETLResult データクラスを実装（取得数・保存数・品質チェック結果・エラー一覧などを保持）。
    - 差分取得ロジック、バックフィル、品質チェック統合を想定した設計（jquants_client, quality モジュールとの連携を前提）。
    - kabusys.data.etl から ETLResult を再エクスポート。

  - DuckDB 互換性を考慮した実装（executemany 空リスト回避などの互換性処理を盛り込む）。

- 研究／リサーチモジュール (kabusys.research)
  - ファクター計算 (kabusys.research.factor_research)
    - モメンタム（1M/3M/6M リターン、200日 MA 乖離）、ボラティリティ（20日 ATR 等）、バリュー（PER, ROE）を計算する関数を提供: calc_momentum, calc_volatility, calc_value。
    - DuckDB SQL を多用して高効率に集計し、データ不足時の None 処理やログ出力を実装。
  - 特徴量探索 (kabusys.research.feature_exploration)
    - 将来リターンの計算 calc_forward_returns（任意ホライズン対応、入力バリデーションあり）。
    - IC（Information Coefficient）計算（Spearman ランク相関） calc_ic、ランク変換ユーティリティ rank。
    - ファクターの統計サマリー factor_summary（count, mean, std, min, max, median）。
  - 研究ユーティリティの公開: kabusys.research.__init__ で主要関数をまとめてエクスポート。

### 変更 (Changed)
- 初回リリースのためなし（今後のバージョンで追記予定）。

### 修正 (Fixed)
- 初回リリースのためなし（今後のバージョンで追記予定）。

### 削除 (Removed)
- 該当なし。

### セキュリティ (Security)
- OpenAI API キーや J-Quants トークン等は環境変数経由で取得。設定がない場合は明示的に例外を投げる箇所を用意（誤操作でのキー暴露を防止する実装方針）。

### 実装上の設計方針（重要な注意点）
- ルックアヘッドバイアス防止: 各種処理で datetime.today() / date.today() を直接参照せず、target_date を明示的に受け取る設計。
- データベース操作の冪等性確保: ON CONFLICT/DELETE→INSERT/トランザクションを活用して再実行可能な設計。
- フェイルセーフ: AI/API の失敗は例外で停止させず、スコアを 0.0 にフォールバックするなどしてパイプライン継続を優先。
- DuckDB のバージョン差異（executemany の空リストなど）への互換性対策を実施。
- OpenAI 呼び出しは JSON Mode を利用、レスポンスの堅牢なパースと検証を行う。

---

注: 上記はソースコードの内容および docstring から推測して作成した初回リリースの CHANGELOG です。実際のリリース日やリリースノートのカテゴリ分類はプロジェクト実情に合わせて調整してください。