Keep a Changelog
=================

すべての重要な変更はこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠します。

なお、このCHANGELOGはコードベースから実装内容を推測して作成した初回リリース向けの要約です。

0.1.0 - 2026-04-09
------------------

Added
- パッケージ初回公開。
  - パッケージ名: kabusys
  - バージョン: 0.1.0

- 環境設定管理（kabusys.config）
  - .env/.env.local の自動読み込みを実装（プロジェクトルートは .git または pyproject.toml を起点に探索、CWD 非依存）。
  - 読み込み順序: OS 環境変数 > .env.local > .env。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 による自動ロード無効化に対応（テスト用途）。
  - .env パーサーの強化:
    - export KEY=val 形式対応。
    - シングル/ダブルクォート内のバックスラッシュエスケープ対応。
    - クォートなし行のインラインコメント解析（'#' の取り扱い）。
  - .env 上書き制御（override）と OS 環境変数保護（protected set）を実装。
  - Settings クラスを提供し、J-Quants / kabuステーション API / LINE / DB パス / Paper Trading / 監視閾値 / システム設定等の環境変数アクセスをプロパティとして提供。
  - 設定の入力検証:
    - KABUSYS_ENV は development/paper_trading/live に制限。
    - LOG_LEVEL は DEBUG/INFO/WARNING/ERROR/CRITICAL に制限。
    - PAPER_FILL_MODE は instant/partial/never/reject のいずれかに検証。
  - path系設定は Path オブジェクトで返却（expanduser 対応）。

- ニュースNLP（kabusys.ai.news_nlp）
  - raw_news と news_symbols を元に銘柄ごとのニュースを集約し、OpenAI(gpt-4o-mini) の JSON モードでセンチメントを解析して ai_scores テーブルへ書き込む処理を実装。
  - 対象ウィンドウは JST 基準で「前日 15:00 ～ 当日 08:30」（UTC に変換して DB 比較）。
  - 1 銘柄あたり最大記事数と最大文字数のトリム機能を実装（_MAX_ARTICLES_PER_STOCK / _MAX_CHARS_PER_STOCK）。
  - 最大バッチサイズ 20 銘柄でのバッチ処理。
  - 再試行ポリシー（429/ネットワーク断/タイムアウト/5xx）を指数バックオフで実装（_MAX_RETRIES / _RETRY_BASE_SECONDS）。
  - レスポンスバリデーション:
    - JSON パースの堅牢化（前後余計テキストの {} 抽出含む）。
    - "results" リスト形式検証、各要素の code/score 検証、未知コードは無視。
    - スコアを ±1.0 にクリップ。
  - 書き込みは冪等性を考慮（該当 date/code を先に DELETE してから INSERT、部分失敗時に他コードの既存データを保護）。
  - 処理はルックアヘッドバイアスを避ける設計（date.today() を参照しない）。
  - API 呼び出し箇所を関数化してテスト差し替えを容易に（unittest.mock.patch 用の設計）。

- レジーム判定（kabusys.ai.regime_detector）
  - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定。
  - LLM 評価は gpt-4o-mini を使用。LLM 呼び出しは JSON モード想定でパース。
  - マクロキーワードによる raw_news タイトル抽出（最大 20 件）。
  - OpenAI API のリトライ / エラー処理（RateLimit/接続/タイムアウト/5xx）、API 失敗時は macro_sentiment=0.0 にフォールバック。
  - レジームスコア合成と閾値判定（_MA_WEIGHT/_MACRO_WEIGHT、クリッピング、閾値に基づくラベリング）。
  - market_regime テーブルへの冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）を実装。
  - ルックアヘッドバイアス防止のため target_date 未満のデータのみ使用。

- データプラットフォーム（kabusys.data）
  - ETL パイプラインの骨子（kabusys.data.pipeline）を実装。
    - 差分更新、バックフィル、品質チェックの設計を反映。
    - ETLResult データクラスを導入（取得/保存数、品質問題、エラー集約、has_errors/has_quality_errors プロパティ、辞書化メソッド）。
  - ETLResult を kabusys.data.etl で再エクスポート。
  - マーケットカレンダー管理（kabusys.data.calendar_management）
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day 等の営業日判定ユーティリティを実装。
    - market_calendar が未取得の場合の曜日ベースフォールバック（週末除外）。
    - DB 登録日を優先し、未登録日は曜日ベースで一貫した補完を行う設計。
    - calendar_update_job を実装（J-Quants API から差分取得、バックフィル、健全性チェック、冪等保存）。
    - 最大探索日数・ルックアヘッド・バックフィル・健全性（未来日異常検出）といった安全機構を実装。
  - jquants_client を利用した fetch/save のフックを想定（実装は外部モジュールとして分離）。

- リサーチ（kabusys.research）
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離を計算（データ不足時は None）。
    - calc_volatility: 20 日 ATR、ATR 比率、20 日平均売買代金、出来高比率等を算出。
    - calc_value: raw_financials の最新財務情報を使った PER/ROE の計算（report_date <= target_date の最新）。
    - いずれも DuckDB 内の SQL とウィンドウ関数を組み合わせて実装。
  - feature_exploration:
    - calc_forward_returns: 複数ホライズン（デフォルト [1,5,21]）の将来リターンを一括取得する汎用実装（horizons の検証あり）。
    - calc_ic: ファクター値と将来リターンのスピアマンランク相関（IC）を実装（有効レコード 3 未満で None）。
    - rank / factor_summary: ランク化（同順位は平均ランク）と基本統計量（count/mean/std/min/max/median）計算を提供。
  - 全リサーチ機能は外部 API を呼ばず DuckDB のみを参照する設計。

- パッケージエクスポート整理
  - kabusys.__init__ に主要サブパッケージ（data, strategy, execution, monitoring）を __all__ で公開。
  - ai / research パッケージで必要関数を明示的にエクスポート（例: score_news, score_regime, zscore_normalize, 各ファクター計算関数 等）。

Changed
- 初回リリースのため目立った変更はなし（初期実装）。

Fixed
- 初回リリースのため既知のバグ修正はなし（実装済みの堅牢化・フェイルセーフ処理を実装）。

Security
- OpenAI API キーは引数で注入可能（テスト容易化）かつ環境変数 OPENAI_API_KEY から取得する仕様。API キー未設定時は明示的な ValueError を発生させ安全性を確保。
- 環境変数の自動読み込みはデフォルトで有効だが、KABUSYS_DISABLE_AUTO_ENV_LOAD により明示的に無効化可能。

Notes / Limitations
- DuckDB を前提とした実装であり、SQL 方言・バインドの互換性のため executemany を使う等の実装上の配慮あり（例: DuckDB 0.10 の制約に対処）。
- OpenAI 呼び出しは外部サービスへの依存があるため、ランタイムでは API キーとネットワークが必要。API エラーは基本的にフェイルセーフ（0.0 フォールバックやスキップ）で継続する設計。
- 実際の jquants_client / kabu ステーション API 連携部分は別モジュール（kabusys.data.jquants_client 等）に分離して利用する想定。

今後の予定（例）
- strategy / execution / monitoring サブパッケージの詳細実装と統合テストの追加。
- ドキュメント（Usage / Deployment / API キー管理 / テストガイド）の整備。
- エンドツーエンドの CI 環境での ETL / AI スコアリングの検証と運用監視の強化。

---
このCHANGELOGはリポジトリ内のコードから推測して作成しています。実際のリリースノートや運用ドキュメントが必要な場合は、追加情報（目的のバージョン、リリース日、変更履歴の正確な一覧）を提供してください。