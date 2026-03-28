CHANGELOG
=========

すべての重要な変更点をこのファイルに記録します。  
このプロジェクトは Keep a Changelog の形式に準拠しています。  

[0.1.0] - 2026-03-28
--------------------

Added
- 初回リリース。
- パッケージメタ情報
  - バージョン: `kabusys.__version__ = "0.1.0"`
  - パッケージの公開 API: `__all__ = ["data", "strategy", "execution", "monitoring"]`（将来的なモジュール構成を示唆）

- 環境設定 / ロード
  - `kabusys.config` を追加。
  - .env ファイルまたは環境変数から設定を読み込む自動ローダーを実装（プロジェクトルートの検出は `.git` または `pyproject.toml` を基準に行う）。
  - 高度な .env パーサー実装（export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの扱いなどをサポート）。
  - 自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
  - `Settings` クラスを提供（必須環境変数取得 `_require()`、J-Quants / kabu / Slack / DB パス等のプロパティ、`KABUSYS_ENV` / `LOG_LEVEL` の検証ロジック、環境判定ユーティリティ `is_live` / `is_paper` / `is_dev`）。
  - デフォルトの DB パス: DuckDB `data/kabusys.duckdb`、SQLite `data/monitoring.db`。

- AI: ニュース NLP と市場レジーム判定
  - `kabusys.ai.news_nlp`
    - raw_news / news_symbols を集約して銘柄ごとのニューステキストを作成し、OpenAI (gpt-4o-mini) に JSON Mode で送信してセンチメント（ai_score）を算出。
    - バッチ処理（最大 20 銘柄／チャンク）、1銘柄あたり記事数・文字数トリム、スコアクリップ（±1.0）。
    - API 呼び出しで 429/ネットワークエラー/タイムアウト/5xx を対象とした指数バックオフ・リトライ実装。
    - レスポンスの堅牢なバリデーション（JSON パースの救済処理含む）。失敗時は空スコア（フェイルセーフ）で処理継続。
    - テスト容易性のため OpenAI 呼び出しを差し替え可能（`_call_openai_api` の patch を想定）。
    - 公開関数 `score_news(conn, target_date, api_key=None)` は書き込み（ai_scores テーブル）を冪等かつ部分失敗に強い方式（対象コードに限定して DELETE → INSERT）で行う。
    - `calc_news_window(target_date)` を提供（JST ベースの収集ウィンドウを UTC-naive datetime で返す）。

  - `kabusys.ai.regime_detector`
    - ETF 1321（日経225連動型）の 200日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次の市場レジーム（'bull' / 'neutral' / 'bear'）を判定。
    - マクロキーワードで raw_news をフィルタし、最大 20 件を LLM に渡して JSON で macro_sentiment を取得。
    - LLM 呼び出しはリトライと 5xx ハンドリングを実装、失敗時は macro_sentiment=0.0 で継続。
    - レジームスコアの合成と閾値判定、`market_regime` テーブルへの冪等な書き込みトランザクションを実装。
    - ルックアヘッドバイアス防止の設計（日時参照の禁止、DB クエリで date < target_date など）。

- Data / ETL / カレンダー
  - `kabusys.data.calendar_management`
    - JPX カレンダー（market_calendar）管理ユーティリティを実装。
    - 営業日判定 API：`is_trading_day`, `is_sq_day`, `next_trading_day`, `prev_trading_day`, `get_trading_days`。
    - DB 登録値優先、未登録日は曜日ベースでフォールバックする一貫したロジック。
    - 夜間バッチ更新ジョブ `calendar_update_job(conn, lookahead_days=90)`：J-Quants から差分取得して冪等に保存（バックフィル、健全性チェックを含む）。
    - 最大探索日数やサニティチェックなど無限ループ回避・安全性を考慮。

  - `kabusys.data.pipeline` / `kabusys.data.etl`
    - ETL パイプライン用の `ETLResult` データクラスを提供（フェッチ数／保存数／品質問題／エラーの集約）。
    - 差分更新、バックフィル、品質チェック（`kabusys.data.quality` と連携）を想定した設計。
    - `_get_max_date` / `_table_exists` 等のユーティリティ実装。
    - `etl` モジュールは `ETLResult` を再エクスポート（公開インターフェース）。

- Research
  - `kabusys.research.factor_research`
    - モメンタム（1M/3M/6M リターン、200日 MA 乖離）、ボラティリティ（20日 ATR）、流動性（20日平均売買代金・出来高比率）、バリュー（PER, ROE）を計算する関数を提供。
    - 全関数は DuckDB 接続を受け取り prices_daily / raw_financials のみを参照（サンドボックス的設計）。
    - 結果は (date, code) ベースの dict リストで返却。
    - 関数: `calc_momentum`, `calc_volatility`, `calc_value`。

  - `kabusys.research.feature_exploration`
    - 将来リターン計算 (`calc_forward_returns`)：任意ホライズン（デフォルト [1,5,21]）の fwd リターンを算出。
    - IC（Information Coefficient）計算 `calc_ic`（Spearman 的ランク相関）、ランク変換 `rank`。
    - 統計サマリー `factor_summary`（count/mean/std/min/max/median）。
    - 設計方針として標準ライブラリのみで実装し、DuckDB に依存する設計。
    - `research.__init__` で zscore 正規化ユーティリティを re-export。

- デザイン上の注目ポイント（フェイルセーフ / テスト性 / バイアス対策）
  - ルックアヘッドバイアス防止を徹底（datetime.today()/date.today() 参照禁止、クエリにおける排他条件）。
  - LLM 呼び出しは失敗時フォールバック（スコアを 0.0）でトレードオフし、例外を投げずに処理を継続する設計。
  - OpenAI 呼び出し部分はテスト時に差し替え可能（関数を分離）。
  - DB 書き込みは冪等性を考慮（DELETE→INSERT、ON CONFLICT 想定、部分失敗時に既存データを保護）。
  - リトライ/バックオフ、レスポンスバリデーション、スコアのクリップなど堅牢化。

Changed
- なし（初回リリース）

Fixed
- なし（初回リリース）

Deprecated
- なし（初回リリース）

Removed
- なし（初回リリース）

Security
- 環境変数に機密情報（例: OPENAI_API_KEY, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN）が必要。Settings で未設定の場合は ValueError を発生させる設計。

Notes / 今後の案内
- strategy / execution / monitoring モジュールは __all__ に含まれているが、このリリースに実体が含まれていないため、今後のリリースで追加される予定です。
- 今後のリリースでは API 仕様の微調整、追加の品質チェック、メトリクス・監視・運用用ツールの拡張を予定しています。