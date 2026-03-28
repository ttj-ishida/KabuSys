# Changelog

すべての注目すべき変更はこのファイルに記録します。  
このプロジェクトは Keep a Changelog の慣習に従って管理されています。  

## [0.1.0] - 2026-03-28

### Added
- 初回リリース。日本株自動売買システム "KabuSys" の基本モジュール群を追加。
  - パッケージ情報
    - バージョン: 0.1.0
    - パッケージ公開: `kabusys`（トップレベルで data, strategy, execution, monitoring を公開）
  - 設定/環境管理（kabusys.config）
    - .env ファイルおよび環境変数からの設定読み込み機能を提供。
    - プロジェクトルート検出: .git または pyproject.toml を基準に探索（CWD 非依存）。
    - 自動ロードの優先順位: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロードを無効化可能（テスト用）。
    - .env パーサは export 前置、クォート（'"/エスケープ）、インラインコメントに対応。
    - Settings クラスを公開（例: settings.jquants_refresh_token, settings.kabu_api_password, settings.is_live 等）。
    - 環境値検証: KABUSYS_ENV（development/paper_trading/live）と LOG_LEVEL の値チェック。
    - デフォルトパス設定: DUCKDB_PATH / SQLITE_PATH。
  - AI / ニュース NLP（kabusys.ai.news_nlp）
    - raw_news および news_symbols を元に銘柄ごとのニュースセンチメントを算出して ai_scores テーブルへ書き込む。
    - OpenAI（gpt-4o-mini, JSON mode）を用いたバッチ評価（1回最大 20 銘柄）。
    - タイムウィンドウ（JST 基準）: 前日 15:00 ～ 当日 08:30（UTC に変換して DB 比較）。
    - 入力テキストの制限: 1銘柄あたり最大 10 件、最大 3000 文字へトリム。
    - リトライ/バックオフ: 429・ネットワーク断・タイムアウト・5xx に対して指数バックオフで再試行。
    - レスポンスバリデーション: JSON パース、results リスト、code/score の検証、スコアを ±1.0 にクリップ。
    - API 呼び出しはテスト差し替え可能（_call_openai_api を patch 可能）。
    - score_news(conn, target_date, api_key=None) を公開（戻り値: 書き込んだ銘柄数）。
  - AI / 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（日経225連動型）200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次レジーム（bull/neutral/bear）を算出。
    - 設計値: MA スケール 10、閾値 bull >= 0.2 / bear <= -0.2、最大記事数 20、モデル gpt-4o-mini、リトライ最大 3 回。
    - LLM 呼び出し失敗時は macro_sentiment = 0.0 でフェイルセーフ継続。
    - market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）。
    - score_regime(conn, target_date, api_key=None) を公開（戻り値: 1=成功）。
  - Research（kabusys.research）
    - factor_research: calc_momentum / calc_value / calc_volatility を実装。
      - Momentum: mom_1m/mom_3m/mom_6m、ma200_dev（ma200 データ不足時は None）。
      - Volatility: 20 日 ATR（atr_20/atr_pct）、20 日平均売買代金、出来高比率。
      - Value: PER（EPS が 0 または欠損の場合は None）、ROE（raw_financials から取得）。
      - DuckDB 上の SQL と Python による実装（prices_daily/raw_financials を参照）。
    - feature_exploration: calc_forward_returns（デフォルト horizons=[1,5,21]）、calc_ic（Spearman のランク相関）、factor_summary、rank（タイ付き平均ランク処理）。
    - 設計方針として本番 API にアクセスしない、安全に再現可能な分析ユーティリティを提供。
  - Data（kabusys.data）
    - calendar_management: JPX カレンダー管理、is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day 等のユーティリティを提供。
      - market_calendar がない場合は曜日ベースのフォールバック（土日非営業日）。
      - calendar_update_job(conn, lookahead_days=90): J-Quants API から差分取得して market_calendar を更新。バックフィル 7 日、先読み 90 日、健全性チェック（未来日チェック 365 日）。
    - pipeline / etl:
      - pipeline.ETLResult を提供（ETL 実行結果の dataclass、品質問題やエラーの集約）。
      - ETL 設計: 差分更新、バックフィル（デフォルト 3 日）、品質チェックの実行だが致命的エラーでも全問題を収集して呼び出し元に委ねる。
      - 内部ユーティリティ: テーブル存在チェック、最大日付取得など。
    - etl モジュールは pipeline.ETLResult を再エクスポート。
  - その他ユーティリティ
    - DuckDB を利用した SQL 実装に合わせた互換性対策（例: executemany に空リストを渡さない等の注記）。
    - 各モジュールで「ルックアヘッドバイアス回避」のため datetime.today()/date.today() を直接参照しない設計。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Deprecated
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Security
- OpenAI API キー・各種トークンは環境変数で管理（コード中ハードコーディングなし）。
- 必須環境変数未設定時は明確なエラーメッセージを送出（ValueError）。

### Notes / Known limitations / Migration notes
- OpenAI 利用
  - API クライアントに OpenAI の公式 SDK（OpenAI クラス）を使用。実行には OPENAI_API_KEY の設定が必須（関数引数で上書き可能）。
  - News / Regime モジュールは gpt-4o-mini の JSON mode を想定したレスポンスを期待します。LLM 出力の不正や API エラーはログに記録してフォールバック（スコア 0.0 や該当銘柄スキップ）します。
  - テスト用に _call_openai_api を patch して外部 API 呼び出しを差し替え可能。
- データベース
  - DuckDB を前提に SQL を記述。DuckDB のバージョン差異に備えた互換性注記あり（例: executemany 空リストの扱い）。
  - ai_scores/market_regime 等への書き込みは冪等になるよう設計（対象日の DELETE → INSERT）。
- 未実装 / TODO
  - calc_value 内での PBR や配当利回りは現バージョンでは未実装。
- 設定ロード
  - .env パーサは多くのケースに対応するが、極端に複雑な構文（多重改行を含むクォート等）は想定外の挙動となる可能性あり。
- テスト性
  - 主要な外部依存（OpenAI、J-Quants クライアント呼び出し）は差し替え・モックしやすい設計を意識。

---

今後のリリースでは以下の点を予定しています（計画）:
- 追加ファクター（PBR、配当利回り）、およびファクター統合ロジックの強化。
- strategy / execution モジュール（発注ロジック）と監視（monitoring）の実装拡充。
- より詳細な品質チェックとアラート機構の実装。

もし上記の変更点について補足や修正が必要であればお知らせください。