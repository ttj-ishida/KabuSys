CHANGELOG
=========

すべての注目すべき変更をここに記録します。  
このファイルは「Keep a Changelog」フォーマットに準拠しています。  

[Unreleased]
-------------

- （なし）

[0.1.0] - 2026-03-28
--------------------

Added
- 初回公開リリース。日本株自動売買プラットフォームのコア機能群を追加。
  - パッケージのメタ情報
    - kabusys.__version__ = "0.1.0"
    - パッケージ公開 API: data, strategy, execution, monitoring を __all__ に定義。
  - 設定 / 環境変数管理（kabusys.config）
    - .env ファイルと OS 環境変数を統合して読み込む自動ローダーを実装。
    - プロジェクトルート探索: .git または pyproject.toml を基準に検索（CWD 非依存）。
    - .env パーサーの実装（export 形式、クォート／エスケープ、インラインコメント対応）。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化。
    - Settings クラスでアプリ設定をラップ（必須キー検証、デフォルト値、型変換）。
    - バリデーション済み値: KABUSYS_ENV（development/paper_trading/live を許容）、LOG_LEVEL（標準ログレベル）。
    - 必須環境変数一覧（明示的に参照されるもの）:
      JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
      （データベースパス等はデフォルトで設定可能: DUCKDB_PATH, SQLITE_PATH）。
  - データ層（kabusys.data）
    - ETL パイプライン基盤（kabusys.data.pipeline）
      - 差分取得、バックフィル、品質チェック、DuckDB への冪等保存を想定した ETLResult データクラスを提供。
      - テーブル最終日付取得ユーティリティ、テーブル存在チェック等を実装。
      - エラー／品質問題の集約と to_dict 変換をサポート。
    - ETL の公開型再エクスポート (kabusys.data.etl → ETLResult)。
    - マーケットカレンダー管理（kabusys.data.calendar_management）
      - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day 等の営業日ロジックを実装。
      - market_calendar テーブルがない場合の曜日ベースフォールバック実装（週末を非営業日扱い）。
      - calendar_update_job: J-Quants API から差分取得して market_calendar を更新する夜間ジョブ（バックフィル、健全性チェック含む）。
      - DuckDB からの日付変換ユーティリティや最大探索日数の上限設定で安全性を確保。
  - 研究（Research）モジュール（kabusys.research）
    - factor_research
      - calc_momentum: 1M/3M/6M リターン、200日MA乖離を計算（データ不足時の扱いを明確化）。
      - calc_volatility: 20日 ATR、相対 ATR、20日平均売買代金、出来高比率を計算。
      - calc_value: EPS/ROE を用いた PER/ROE 計算（raw_financials から最新レコードを参照）。
      - DuckDB を使った SQL + Python 実装、外部 API 不使用を明記。
    - feature_exploration
      - calc_forward_returns: 将来リターン（複数ホライズン）を一括で取得する効率的な実装。
      - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を計算するユーティリティ。
      - rank: 同順位は平均ランクを割り当てるランク化ロジック（浮動小数丸めに配慮）。
      - factor_summary: 各ファクター列の基本統計量（count, mean, std, min, max, median）を標準ライブラリのみで計算。
    - 研究モジュールは pandas 等の外部依存を避ける設計。
  - AI / NLP（kabusys.ai）
    - news_nlp
      - calc_news_window: スコアリング対象のニュース時刻ウィンドウ（JST基準→UTC naive datetime）を計算。
      - score_news: raw_news と news_symbols を基に銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini）へバッチ送信してセンチメント（ai_scores）を書き込む処理を実装。
      - バッチング（最大20銘柄）、1銘柄あたりの記事トリム（記事数・文字数上限）でトークン肥大を抑制。
      - API リトライ（429/ネットワーク断/タイムアウト/5xx）を指数バックオフで実装。失敗はスキップし全体処理継続（フェイルセーフ）。
      - レスポンス検証（JSON パース回復ロジック、results の存在と型検査、未知コードの無視、数値変換とクリップ）。
      - DuckDB 書き込みは部分失敗に備え、対象コードのみ DELETE → INSERT（冪等性と部分保護）。
      - テスト容易性のため _call_openai_api をモック差替えできる設計。
    - regime_detector
      - ETF 1321 の 200 日 MA 乖離（重み 70%）とニュース由来のマクロセンチメント（重み 30%）を合成し、日次で market_regime テーブルへ書き込み。
      - マクロ記事抽出はキーワード（日本およびグローバル）ベース。LLM には gpt-4o-mini を利用し JSON 出力を想定。
      - API リトライ、失敗時のフォールバック（macro_sentiment=0.0）、スコアのクリッピング、レジーム判定閾値（bull/neutral/bear）を実装。
      - DB 書き込みは BEGIN/DELETE/INSERT/COMMIT の冪等処理、失敗時は ROLLBACK とログ出力。
      - lookahead バイアス対策として target_date 未満のデータのみ使用し、datetime.today()/date.today() に依存しない。
  - 共通実装上の配慮
    - DuckDB を前提にした SQL 実装で互換性配慮（executemany の空リスト回避等）。
    - API キーが未設定の場合は ValueError を発生させて早期に検出（OpenAI 関連処理）。
    - ロギングによる詳細情報出力（info/debug/warning/exception）。
    - 多くの箇所で「フェイルセーフ」設計を採用（API失敗→中立値/スキップ等）し、本番トレード系コードの安全マージンを確保。
    - テスト容易性を考慮したフック（プライベート _call_openai_api のモック差替え等）。

Changed
- 初回リリースにつき該当なし。

Fixed
- 初回リリースにつき該当なし。

Security
- OpenAI や J-Quants 等の外部 API キーは環境変数で管理。設定未実装時は明示的な例外を出すことで誤動作を防止。

Notes / Migration
- 必要な環境変数:
  - OPENAI_API_KEY（AI スコアリング／レジーム判定）
  - JQUANTS_REFRESH_TOKEN（J-Quants API）
  - KABU_API_PASSWORD, KABU_API_BASE_URL（kabuステーション API）
  - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID（通知）
  - DUCKDB_PATH, SQLITE_PATH（データベースファイルパス）
  - KABUSYS_ENV（development / paper_trading / live）
  - LOG_LEVEL（DEBUG/INFO/...）
- .env 自動読み込みはプロジェクトルート検出が成功した場合のみ有効。CI/テストでは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して無効化可能。
- DuckDB への書き込みロジックはバージョン依存の挙動（executemany の空リスト受け入れ可否）に配慮しているため、DuckDB のバージョンが古い/新しい環境では振る舞いが異なる可能性がある。問題がある場合はログとエラートレースを確認してください。

Acknowledgements
- OpenAI（gpt-4o-mini）を利用する設計を採用。API レスポンスの堅牢な処理・リトライ・バリデーションを重視。
- J-Quants との連携を前提としたデータ収集・カレンダー更新ロジックを実装。

--- 

今後の予定（例）
- strategy / execution / monitoring モジュールの実装拡張（注文管理、発注ロジック、監視アラート）。
- モデル評価パイプラインやバックテスト機能の追加。
- セキュリティ監査・より詳細な型ヒント・docstring の拡充。