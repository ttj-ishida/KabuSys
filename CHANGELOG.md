# CHANGELOG

すべての変更は Keep a Changelog 準拠で記載しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

なお、本CHANGELOGはリポジトリ内のコード構成・実装から推測して作成した初期リリース向けの変更履歴です。

## [Unreleased]
- （現時点で未リリースの変更はありません）

## [0.1.0] - 2026-03-29
初回リリース。日本株自動売買システム "KabuSys" のコアライブラリを提供します。主な機能は以下のとおりです。

### Added
- パッケージ基礎
  - パッケージ初期化 (src/kabusys/__init__.py) とバージョン定義 (0.1.0)。
  - パブリックサブパッケージ: data, strategy, execution, monitoring を __all__ で公開。

- 設定管理
  - 環境変数/設定管理モジュールを追加 (src/kabusys/config.py)。
    - .env と .env.local の自動読み込み（プロジェクトルートを .git または pyproject.toml から検出）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能。
    - .env パーサ実装（コメント、export 形式、シングル／ダブルクォート、エスケープに対応）。
    - 環境変数必須チェック用 _require と Settings クラスを提供。
    - デフォルト値やバリデーションを含む設定プロパティ:
      - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID の必須取得
      - KABU_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH のデフォルト値
      - KABUSYS_ENV（development|paper_trading|live）および LOG_LEVEL の検証
      - is_live / is_paper / is_dev のユーティリティプロパティ

- AI（自然言語処理）モジュール
  - ニュースセンチメントスコアリング (src/kabusys/ai/news_nlp.py)
    - raw_news と news_symbols を集約して銘柄単位で LLM に投げ、ai_scores テーブルへ書き込むフローを実装。
    - タイムウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST（UTC に変換して DB クエリに使用）。calc_news_window 関数を提供。
    - バッチ処理: 1 API 呼び出しで最大 20 銘柄を処理（_BATCH_SIZE）。
    - トークン肥大化対策: 1銘柄当たり最大記事数・文字数でトリム（_MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK）。
    - JSON Mode（厳密 JSON）でのレスポンス処理・検証ロジック（_validate_and_extract）。
    - レート制限/ネットワーク断/サーバーエラー(5xx) に対する指数バックオフリトライの実装。
    - スコアは ±1.0 にクリップして保存。
    - DuckDB の executemany の互換性を考慮した部分置換（DELETE→INSERT）で冪等性を確保。
    - テスト容易性: OpenAI 呼び出し層（_call_openai_api）をモック差し替え可能に設計。
    - 公開 API: score_news(conn, target_date, api_key=None)

  - 市場レジーム判定 (src/kabusys/ai/regime_detector.py)
    - ETF 1321（日経225連動）200日移動平均乖離（重み70%）とマクロニュースのLLMセンチメント（重み30%）を合成して市場レジームを判定（bull/neutral/bear）。
    - マクロキーワードによる raw_news フィルタリングと最大 20 件までのタイトル抽出。
    - OpenAI（gpt-4o-mini）を用いたマクロセンチメント評価（JSON 出力を期待）。
    - API リトライ/バックオフ、5xx 判定や JSON パース失敗時のフェイルセーフ（macro_sentiment=0.0）。
    - レジームスコア合成と -1..1 のクリップ、しきい値に基づくラベル付け。
    - market_regime テーブルへ冪等的（BEGIN/DELETE/INSERT/COMMIT）に書き込み。
    - テスト用に _call_openai_api を差し替え可能。

  - ai パッケージ初期化で score_news を公開 (src/kabusys/ai/__init__.py)。

- Research（リサーチ）モジュール
  - ファクター計算および特徴量解析用関数群を追加 (src/kabusys/research/*)。
  - factor_research.py:
    - calc_momentum: 1M/3M/6M リターン、200日MA乖離を計算（prices_daily に依存）。
    - calc_volatility: 20日 ATR、相対ATR、20日平均売買代金、出来高比率などを計算。
    - calc_value: raw_financials と prices_daily を用いて PER / ROE を算出（最終財務レコードの参照）。
    - 計算は DuckDB SQL を多用し、外部 API にアクセスしない設計。
  - feature_exploration.py:
    - calc_forward_returns: 複数ホライズン（デフォルト [1,5,21]）の将来リターンを一括で取得。
    - calc_ic: スピアマンのランク相関（Information Coefficient）を実装。
    - rank: 同順位は平均ランクで扱うランク変換。
    - factor_summary: count/mean/std/min/max/median の統計サマリーを返す。
    - 実装は標準ライブラリのみで依存を抑制（pandas 等に依存しない）。
  - research パッケージ初期化で主要関数群を再エクスポート。

- Data（データ）モジュール
  - ETL パイプライン基盤 (src/kabusys/data/pipeline.py, src/kabusys/data/etl.py)
    - ETLResult データクラスを導入（ETL の取得数/保存数、品質チェック、エラー管理を保持）。
    - 差分取得、バックフィル、品質チェックの設計方針を反映。
    - pipeline 内で DuckDB テーブル存在チェックや最大日付取得ユーティリティを実装。
    - etl パッケージから ETLResult を再エクスポート。
  - カレンダー管理 (src/kabusys/data/calendar_management.py)
    - JPX カレンダー取得ジョブ calendar_update_job を実装（J-Quants クライアント経由で差分取得→save）。
    - 営業日判定ユーティリティ:
      - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day を提供。
    - DB にカレンダーがない場合は曜日ベース（土日休）でフォールバック。
    - 最大探索日数や先読み、バックフィル、健全性チェックを実装して無限ループ/誤データを防止。
    - jquants_client（外部）との疎結合で fetch/save を呼び出す設計。
  - jquants_client 連携を想定した ETL ワークフロー設計を反映（差分取得・冪等保存・品質チェック）。

### Changed
- N/A（初回リリースのため既存変更はなし）

### Fixed
- N/A（初回リリースのため修正履歴はなし）

### Security
- 外部 API キー（OpenAI 等）は引数で注入可能か環境変数で参照する設計。必須チェックで未設定時は ValueError を明示的に送出。

### Notes / 設計上の重要ポイント
- ルックアヘッドバイアス防止:
  - AI / リサーチ関連関数は datetime.today() / date.today() を直接参照せず、呼び出し元から target_date を受け取る設計。
  - DB クエリの境界条件は target_date 未満/排他などで将来データを参照しないよう配慮。
- フェイルセーフ:
  - OpenAI 呼び出し失敗やパースエラー時は例外で全面停止させず、ログを残してフォールバック（例: macro_sentiment=0.0）やスキップする動作を多用。
- テスト容易性:
  - OpenAI 呼び出し箇所（_call_openai_api 等）をモック差し替え可能にし、ユニットテストでの再現を容易にしている。
- DuckDB 互換性:
  - executemany に空リストを渡せない等の DuckDB 特有の挙動に注意した実装（空チェックを明示的に行う）。

---

この CHANGELOG はコードベースの内容をもとに推測して作成した初期リリース向けの記述です。差分や追加のリリースが発生した場合は、Unreleased セクションに変更点を追記し、適切にバージョンと日付を付与してください。