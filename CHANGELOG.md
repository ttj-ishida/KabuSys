# CHANGELOG

すべての変更は Keep a Changelog 規約に準拠して記載します。  
このプロジェクトはセマンティックバージョニング (MAJOR.MINOR.PATCH) を採用しています。

## [0.1.0] - 2026-03-28
初回公開リリース。日本株自動売買システム「KabuSys」の基盤機能を提供します。主な追加点は以下の通りです。

### 追加 (Added)
- パッケージ基盤
  - パッケージ初期化 (kabusys.__init__) とバージョン定義 (`__version__ = "0.1.0"`) を追加。
  - 主要サブモジュール（data / research / ai / monitoring / execution / strategy）をエクスポート準備。

- 設定管理 (kabusys.config)
  - .env / .env.local ファイルおよび環境変数から設定を読み込む自動ローダーを実装。
  - プロジェクトルート検出（.git または pyproject.toml を基準）により CWD に依存しないロードを実現。
  - .env パーサー（クォート、エスケープ、コメント、export 形式に対応）を実装。
  - OS 環境変数保護（protected set）と override フラグをサポート。
  - 自動ロード無効化フラグ `KABUSYS_DISABLE_AUTO_ENV_LOAD` をサポート。
  - Settings クラスを提供し、J-Quants / kabu / Slack / DB パスや実行環境（development/paper_trading/live）・ログレベル検証などのプロパティを公開。

- ニュース NLP & LLM 統合 (kabusys.ai)
  - news_nlp モジュール
    - raw_news と news_symbols から銘柄別に記事を集約し、OpenAI（gpt-4o-mini、JSON Mode）で銘柄ごとのセンチメント（-1.0〜1.0）を算出。
    - バッチ処理（最大 20 銘柄 / API コール）、1銘柄あたり記事数・文字数上限（トリム）をサポート。
    - 429/ネットワーク断/タイムアウト/5xx に対する指数バックオフでのリトライロジックを実装。
    - レスポンスの堅牢なバリデーションと JSON 復元ロジック（前後ノイズの扱い含む）。
    - DuckDB への冪等書き込み（DELETE → INSERT、部分失敗時に他銘柄スコアを保護）。
  - regime_detector モジュール
    - ETF (1321) の 200 日移動平均乖離（70%）とマクロニュース LLM センチメント（30%）を合成して日次市場レジーム（bull/neutral/bear）を判定。
    - OpenAI 呼び出しのリトライ・フォールバック（失敗時 macro_sentiment=0.0）や API エラー分類（5xx の再試行等）を実装。
    - DB からのデータ取得はルックアヘッドバイアスを避けるため target_date 未満や calc_news_window を利用。
    - market_regime テーブルへの冪等書き込みを実装（BEGIN/DELETE/INSERT/COMMIT + ROLLBACK 保護）。

- データプラットフォーム (kabusys.data)
  - calendar_management
    - JPX カレンダー管理（market_calendar テーブルの参照／更新、is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day のユーティリティ）を実装。
    - カレンダーデータがない場合は曜日ベースでフォールバック。DB 登録ありでは DB 値を優先する一貫した判定ルールを採用。
    - 夜間バッチ更新ジョブ（calendar_update_job）で J-Quants API から差分取得と冪等保存をサポート、バックフィルと健全性チェックを実装。
  - pipeline / ETL
    - ETLResult データクラスを提供（取得件数 / 保存件数 / 品質問題 / エラー情報など）。
    - 差分更新、バックフィルロジック（既存最終取得日の数日前から再取得）、品質チェックフック（quality モジュール想定）など ETL 設計方針を実装。
    - jquants_client を用いたデータ取得・保存処理を想定したパイプライン設計。

- リサーチ / ファクター群 (kabusys.research)
  - factor_research モジュール
    - Momentum（1M/3M/6M リターン、200 日 MA 乖離）、Volatility（20 日 ATR、相対 ATR、平均売買代金、出来高比率）、Value（PER, ROE）を DuckDB の SQL と Python で計算する関数を実装。
    - データ不足時の None 処理やスキャン日数バッファを考慮。
  - feature_exploration モジュール
    - 将来リターン計算（calc_forward_returns）、IC（calc_ic）計算（Spearman の ρ）、rank、factor_summary（count/mean/std/min/max/median）を追加。
    - pandas 等に依存せずに標準ライブラリと DuckDB で動作する実装。
  - research パッケージ自動エクスポート（主要関数の __all__ 定義）。

### 変更 (Changed)
- 設計/実装ガイドラインの明文化（各モジュールの docstring にて）
  - ルックアヘッドバイアス回避のため datetime.today()/date.today() の非使用方針を徹底。
  - DuckDB の互換性（executemany の空リスト制約など）に配慮した実装。

### 修正 (Fixed)
- OpenAI レスポンスや API エラー処理におけるフォールバックを整備（LLM 呼出し失敗時に例外を上位に伝播させず安全に継続する挙動を採用）。
- .env パーサーの改善（export 形式、クォート内エスケープ、インラインコメントの扱い）により実際の .env フォーマットとの互換性を向上。

### 注意事項 (Notes)
- OpenAI API キーは関数引数で注入可能。引数が None の場合は環境変数 OPENAI_API_KEY を参照します。未設定時は ValueError を発生させます。
- 多くの処理は DuckDB のテーブル（prices_daily / raw_news / news_symbols / ai_scores / market_calendar / raw_financials / market_regime 等）を前提としており、スキーマ整備が必要です。
- ETL・カレンダー更新・LLM 呼び出しは外部 API（J-Quants, OpenAI, kabu station 等）に依存します。運用時は環境変数や認証情報 (.env) を適切に設定してください。
- 本リリースは初期機能セットの提供であり、監視、実行（発注）、戦略モジュールの詳細実装・安全対策（実取引時のガード等）は今後のリリースで追加予定です。

## 以前のバージョン
- なし（初回リリース）

以上。