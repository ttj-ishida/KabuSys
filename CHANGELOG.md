CHANGELOG
=========

すべての注目すべき変更を記録します。本ファイルは「Keep a Changelog」準拠の形式で記載しています。

フォーマット:
- バージョン見出しは YYYY-MM-DD 形式の日付を付与しています（リリース日）。
- セクション: Added / Changed / Fixed / Security 等を使用します。

Unreleased
----------

（現在のコードベースは初回リリース相当の内容のため、未リリースの作業は特にありません）

0.1.0 - 2026-04-09
------------------

Added
- 基本パッケージを追加しました（kabusys v0.1.0）。
  - パッケージエントリポイント: src/kabusys/__init__.py（__version__ = "0.1.0"）。
- 環境変数・設定管理（kabusys.config）
  - .env ファイルおよび環境変数の自動読み込みを実装（優先順: OS 環境変数 > .env.local > .env）。
  - 自動読み込みの無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - .env 行パーサーを実装（export プレフィクス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント処理をサポート）。
  - ファイル読み込み時の保護（protected keys）や読み込み失敗時の警告出力を実装。
  - Settings クラスを追加し、J-Quants / kabuステーション / LINE / DB パス / PaperTrading の設定や監視用閾値（CPU/MEM/DISK）、PID/KILL フラグ等を環境変数から取得するプロパティを提供。
  - 設定値の妥当性検査を実装（PAPER_FILL_MODE, KABUSYS_ENV, LOG_LEVEL など）。
- AI 関連（kabusys.ai）
  - ニュース NLP スコアリング（kabusys.ai.news_nlp）
    - raw_news / news_symbols を集約し、OpenAI（gpt-4o-mini）へ JSON Mode でバッチ送信して銘柄ごとのセンチメント ai_score を生成。
    - 時間ウィンドウ計算（前日 15:00 JST 〜 当日 08:30 JST を UTC に変換）機能を実装（calc_news_window）。
    - バッチ処理、トークン肥大化対策（_MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK）、最大バッチサイズ、レスポンス検証、スコアの ±1.0 クリップを実装。
    - API エラー（429/ネットワーク断/タイムアウト/5xx）に対する指数バックオフリトライとフェイルセーフ（失敗時はスキップして継続）。
    - レスポンスの堅牢な JSON 復元ロジックとスコア検証実装（未要求コードは無視）。
    - テスト容易性のために OpenAI 呼び出しを置換可能に（内部 _call_openai_api をモック可）。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成し、日次で市場レジーム（bull/neutral/bear）を判定して market_regime テーブルへ冪等保存。
    - マクロキーワードによる記事フィルタリング、OpenAI 呼び出し、リトライ/バックオフ、レスポンスパースのフォールバック（失敗時 macro_sentiment=0.0）を実装。
    - ルックアヘッドバイアス防止の設計（target_date 未満データのみ使用）を採用。
- データプラットフォーム（kabusys.data）
  - カレンダー管理（kabusys.data.calendar_management）
    - JPX カレンダー管理用ユーティリティを実装。
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を提供。
    - market_calendar の存在有無に応じた DB優先 / 曜日フォールバックの挙動、最大探索日数による安全策、lookahead/backfill/健全性チェックを実装。
    - calendar_update_job により J-Quants から差分取得して保存（fetch/save の例外処理とログ出力を実装）。
  - ETL パイプライン（kabusys.data.pipeline + data.etl）
    - ETL の結果表現 ETLResult を導入（target_date, fetched/ saved カウント, quality_issues, errors 等を保持）。
    - 差分更新・バックフィル・品質チェック・idempotent 保存（ON CONFLICT 形式）を想定した設計。
    - data.etl で ETLResult を再エクスポート。
- リサーチ / ファクター計算（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）
    - モメンタム（1M/3M/6M）、200 日 MA 乖離、ATR（20 日）、流動性（20 日平均売買代金/出来高変化率）等を DuckDB 上で SQL によって計算する関数を実装（calc_momentum / calc_volatility / calc_value）。
    - 欠損データやデータ不足時の None 取り扱い、結果は (date, code) を含む辞書リストで返却。
  - 特徴量探索（kabusys.research.feature_exploration）
    - 将来リターン計算（calc_forward_returns: 任意ホライズンの fwd_nd を一括取得）、IC（Spearman 相関）計算（calc_ic）、統計サマリ（factor_summary）、ランク変換ユーティリティ（rank）を実装。
    - pandas 等外部依存を用いずに標準ライブラリと DuckDB SQL で実装。
  - research パッケージの __init__ で主要関数をエクスポート（zscore_normalize は kabusys.data.stats から再エクスポート）。
- ロギング・トランザクション・耐障害性
  - 各種 DB 書き込みは BEGIN / DELETE / INSERT / COMMIT の冪等パターンを採用し、例外時は ROLLBACK を試行してログ出力。
  - OpenAI 呼び出し箇所における 5xx を考慮したリトライ方針と、非致命的失敗時のフォールバック（スコア 0.0 やスキップ）を実装。
- テスト支援
  - OpenAI 呼び出しを抽象化した内部関数を用意し、unittest.mock.patch による差し替えでテストが容易になるよう設計。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Security
- （特記なし。環境変数・APIキーは Settings 経由で取得する設計。自動 .env ロードを無効にするオプションあり）

Notes / 設計方針（ドキュメント化された重要点）
- ルックアヘッドバイアス防止: AI / リサーチ系関数は内部で datetime.today()/date.today() を直接参照せず、外部から target_date を受け取る設計。
- 部分失敗耐性: 複数銘柄のバッチ処理では、取得できた銘柄のみを DB に書き込む（部分失敗時も既存データを保護）。
- DuckDB の互換性考慮: executemany に空リストを渡さない等の実装上の注意を反映。
- 外部 API 呼び出しに対する堅牢化: リトライ・バックオフ・最大試行回数・サーバーエラー判定（status_code）などを実装。

今後の計画（補足、推測）
- monitoring / execution 等の実行周りのモジュールは __all__ に含まれており、今後のリリースで発注/監視機能の実装が想定される。
- テスト用モックや CI 用のユーティリティ（KABUSYS_DISABLE_AUTO_ENV_LOAD など）は既に考慮済みで、単体テスト・統合テストの整備がしやすい設計。

ライセンスや著作権情報はソースリポジトリの該当ファイルを参照してください。