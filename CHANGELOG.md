CHANGELOG
=========

すべての重要な変更はこのファイルに記録します。フォーマットは "Keep a Changelog" に準拠しています。

[0.1.0] - 2026-04-04
--------------------

Added
- 初回リリース: KabuSys 日本株自動売買システムの基本コンポーネントを追加。
  - パッケージ公開情報
    - バージョン: 0.1.0
    - パッケージ初期エントリ: kabusys.__init__（__all__ に data, strategy, execution, monitoring を公開）
  - 設定管理（kabusys.config）
    - .env / .env.local の自動読み込み（プロジェクトルートを .git または pyproject.toml で検出）
    - .env パース機能（コメント、export プレフィックス、シングル/ダブルクォート、エスケープ対応）
    - 自動ロードを無効化する環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD
    - OS 環境変数を保護する読み込み挙動（.env.local が .env を上書きする）
    - 必須値チェック用の _require と Settings クラス（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等のプロパティを提供）
    - 各種デフォルト設定（KABU_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH 等）と監視閾値（CPU/MEM/DISK）およびログ/環境設定検証
  - AI モジュール（kabusys.ai）
    - ニュース NLP（kabusys.ai.news_nlp）
      - raw_news / news_symbols を集約し、OpenAI（gpt-4o-mini）を使って銘柄ごとのセンチメント ai_score を計算
      - 時間ウィンドウ計算（前日15:00 JST ～ 当日08:30 JST）、バッチ処理（最大20銘柄/チャンク）、トークン制御（記事数・文字数制限）
      - JSON Mode レスポンス検証、部分失敗を許容する設計（失敗時はスキップして継続）
      - 429/ネットワーク/タイムアウト/5xx に対する指数バックオフ・リトライ処理
      - ai_scores テーブルへの冪等書き込み（DELETE → INSERT、部分失敗時の既存データ保護）
      - 公開関数: score_news(conn, target_date, api_key=None)
    - 市場レジーム判定（kabusys.ai.regime_detector）
      - ETF 1321（日経225連動）200日MA乖離（重み70%）とマクロニュースのLLMセンチメント（重み30%）を合成して日次レジーム判定
      - マクロキーワードによる raw_news フィルタ、OpenAI 呼び出し（gpt-4o-mini）、フェイルセーフ（API失敗時 macro_sentiment=0.0）
      - レジームスコアを market_regime テーブルへ冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）
      - 公開関数: score_regime(conn, target_date, api_key=None)
  - Data モジュール（kabusys.data）
    - カレンダー管理（kabusys.data.calendar_management）
      - JPX カレンダー取得のバッチ更新ジョブ（calendar_update_job）
      - 営業日判定・前後営業日取得・期間内営業日列挙（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）
      - market_calendar が存在しない場合の曜日ベースのフォールバック設計、最大探索日数制限、バックフィルと健全性チェック
    - ETL パイプライン（kabusys.data.pipeline）
      - 差分更新・バックフィル、jquants_client による冪等保存、品質チェック収集方針を実装
      - ETL 実行結果を表す ETLResult データクラスを提供（to_dict, has_errors, has_quality_errors 等）
    - ETL 公開インターフェース（kabusys.data.etl）
      - pipeline.ETLResult の再エクスポート
  - Research モジュール（kabusys.research）
    - ファクター計算（kabusys.research.factor_research）
      - Momentum（1M/3M/6M リターン、200日MA乖離）、Value（PER, ROE）、Volatility（20日ATR, 相対ATR, 出来高/売買代金指標）
      - DuckDB 上で SQL とウィンドウ関数を用いて効率的に計算。データ不足時は None を返す等の耐障害性
      - 公開関数: calc_momentum, calc_value, calc_volatility
    - 特徴量探索（kabusys.research.feature_exploration）
      - 将来リターン計算（calc_forward_returns）、IC（calc_ic）、ランク関数（rank）、統計サマリー（factor_summary）
      - pandas 等外部依存なしで実装、Spearman（ランク相関）を自前で計算
    - 研究向けユーティリティを __all__ で公開（zscore_normalize を含む）
  - 共通設計上の注意点（ライブラリ全体）
    - ルックアヘッドバイアス防止: datetime.today() / date.today() を内部処理で不用意に参照しない設計（target_date ベースで全て計算）
    - DB 書き込みは冪等性を重視（DELETE→INSERT、ON CONFLICT など）
    - 外部 API 呼び出しは耐障害性重視（リトライ、バックオフ、失敗時の安全なフォールバック）
    - OpenAI 呼び出し箇所は各モジュール内で独立実装（テスト時にモック差替え可能）
    - DuckDB を主要な分析/保管エンジンとして想定

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。

Security
- 初回リリースのため該当なし。
  - 注意: OpenAI API キーや J-Quants トークン、Kabu API パスワードなどの機密情報は環境変数で管理すること（Settings で参照）。.env を配布しないよう注意。

使用上の注意（短記）
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
  - OPENAI_API_KEY（score_news / score_regime 呼び出し時に必要）
- .env 自動読み込みはプロジェクトルート検出に依存（.git または pyproject.toml）。テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により無効化可。
- DuckDB を利用するため、実行環境に duckdb パッケージが必要。
- ai モジュールは外部 API（OpenAI）に依存するため、API レート制限や課金に注意。

今後の予定（例）
- strategy / execution / monitoring パッケージの実装拡充（本リリースでは公開名のみ設定）
- 追加の品質チェック・ETL テスト・CI の整備
- 研究向け可視化ユーティリティやモデル学習パイプラインの追加

---