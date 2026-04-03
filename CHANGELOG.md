# CHANGELOG

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠します。  

## [Unreleased]

## [0.1.0] - 2026-04-03
初回リリース。日本株自動売買システム「KabuSys」の基礎機能群を実装・公開します。以下はコードベースから推測してまとめた実装内容と注意点です。

### Added
- パッケージ基盤
  - kabusys パッケージ初期化（__version__ = 0.1.0、公開サブパッケージ指定）
  - 公開モジュール群: data, research, ai, など（strategy / execution / monitoring などは名前空間に含むが個別実装は一部のみ提供）

- 設定・環境変数管理（kabusys.config）
  - .env または .env.local をプロジェクトルート（.git / pyproject.toml 基準）から自動読み込みする機能を実装
  - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードの無効化が可能
  - export KEY=val 形式やクォート・エスケープ、インラインコメント処理に対応する .env パーサー実装
  - Settings クラスを提供し、J-Quants / kabu ステーション / LINE / DB パス / 監視閾値 / システムモード等の取得を統一
  - 必須キー未設定時は ValueError を送出する _require 実装
  - KABUSYS_ENV と LOG_LEVEL のバリデーション（許容値チェック）

- データ基盤（kabusys.data）
  - calendar_management
    - market_calendar を用いた営業日判定ロジックを実装: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day
    - DB データがない/未登録日の場合は曜日ベース（土日非営業）のフォールバックを採用
    - calendar_update_job: J-Quants からの差分取得と冪等保存（バックフィル、健全性チェック含む）
    - 最大探索日数やバックフィル、先読み日数などの安全装置を実装
  - pipeline / ETL
    - ETLResult データクラスを追加（ETL 実行結果 / 品質問題 / エラー情報を集約）
    - ETL の差分更新・バックフィル・品質チェックを想定した設計（jquants_client と quality モジュールを利用）
  - etl モジュール: pipeline.ETLResult の再エクスポート

- 研究・リサーチ（kabusys.research）
  - factor_research
    - モメンタム: calc_momentum（1M/3M/6M リターン、200日 MA 乖離）
    - ボラティリティ/流動性: calc_volatility（20日 ATR、相対 ATR、平均売買代金、出来高比率）
    - バリュー: calc_value（PER、ROE を raw_financials と prices_daily から算出）
    - DuckDB を利用した SQL ベース実装。十分な過去データがない場合は None を返す設計
  - feature_exploration
    - 将来リターン: calc_forward_returns（任意ホライズンに対応、入力検証あり）
    - IC 計算: calc_ic（スピアマンランク相関）
    - ランク変換: rank（同順位は平均ランク）
    - 統計サマリー: factor_summary（count/mean/std/min/max/median）
  - research パッケージのエクスポート整備（主要関数を __all__ で公開）
  - zscore_normalize を data.stats から再エクスポート（ユーティリティ連携）

- AI / ニュース系（kabusys.ai）
  - news_nlp
    - score_news API を提供：raw_news / news_symbols を集約して銘柄ごとにニュースを結合し、OpenAI（gpt-4o-mini, JSON Mode）へバッチ送信してセンチメントスコアを ai_scores テーブルへ書き込む
    - タイムウィンドウ（前日15:00 JST ～ 当日08:30 JST）を calc_news_window で算出（UTC に変換して DB と比較）
    - バッチサイズ、記事数上限、文字数トリムなどのトークン肥大化対策を導入（_BATCH_SIZE, _MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK 等）
    - 429・ネットワーク断・タイムアウト・5xx を対象に指数バックオフでリトライ。レスポンスの厳密な JSON バリデーション実装
    - 部分成功を許容する安全な DB 書き込み（対象コードのみ DELETE→INSERT）により既存データの保護
  - regime_detector
    - ETF 1321（日経225連動）200日 MA 乖離（重み70%）とマクロニュースの LLM センチメント（重み30%）を合成して日次の市場レジーム（bull/neutral/bear）を算出し market_regime テーブルへ冪等書き込み
    - マクロニュース抽出（キーワードベース）と OpenAI 呼び出しを行い、API 失敗時は macro_sentiment = 0.0 でフォールバック
    - 明示的にルックアヘッドバイアス回避の設計（datetime.today() を参照しない等）
    - OpenAI 呼び出しは専用関数を用意しテストで差し替え可能（patch可能）
  - ai.__init__ にて score_news を公開

- OpenAI 統合の共通点
  - gpt-4o-mini を想定した Chat Completions＋JSON Mode を使用
  - レスポンスは JSON のみ期待し、パース失敗は安全にフォールバックして処理継続
  - API キーは api_key 引数または環境変数 OPENAI_API_KEY から解決し、未設定時は ValueError を送出

- 共通設計方針（全体）
  - DuckDB を主要なローカル DB として利用（関数は DuckDB 接続を引数に受ける）
  - ルックアヘッドバイアス回避: datetime.today()/date.today() を直接参照しないことを徹底
  - DB 書き込みは冪等性を意識（DELETE→INSERT / ON CONFLICT を想定）
  - フェイルセーフ設計: 外部 API 失敗時はスキップ・デフォルト値で継続し、例外は必要箇所でのみ伝播

### Changed
- 初回リリースのため該当なし

### Fixed
- 初回リリースのため該当なし

### Security / Ops 注意点
- OpenAI API キー（OPENAI_API_KEY）、J-Quants トークン（JQUANTS_REFRESH_TOKEN）、Kabu API パスワード（KABU_API_PASSWORD）は機密情報です。環境変数または安全なシークレット管理で運用してください。
- .env 自動読み込みはプロジェクトルート検出に依存します。パッケージ配布後やテスト時に挙動を無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- settings.env / log_level の値が不正な場合は ValueError が発生します。運用設定を事前に検証してください。

### Known limitations / TODO（コードから推測）
- 一部の名前空間（strategy, execution, monitoring）は __all__ に含まれるが、今回提供された snippet には実装が限定的／未提供の可能性があるため、実運用前に該当モジュールの存在と API を確認してください。
- News / Regime の LLM 評価は gpt-4o-mini の JSON モードに依存し、将来の OpenAI SDK 変更により status_code 等の取り扱いが変わる可能性があるため、SDK バージョンの追従が必要です。
- DuckDB の executemany に空リストを渡せない点（0.10 系）を考慮した実装が行われているが、DuckDB のバージョン違いによる挙動差異に注意してください。

---

今後のリリースでは、戦略（strategy）と実行（execution）周りの発注ロジック、監視（monitoring）サービス、より詳細な品質チェックや CI テストカバレッジの拡張などが想定されます。