# CHANGELOG

すべての変更は Keep a Changelog の形式に従って記載します。  
このファイルはリポジトリ内のコードから推測して作成した初期の変更履歴です。

注: バージョン番号はパッケージ定義 (src/kabusys/__init__.py の __version__) に合わせています。

## [0.1.0] - 2026-03-29

### Added
- 初期リリース: KabuSys — 日本株自動売買／リサーチ基盤の最初の実装。
- パッケージ公開インターフェース
  - src/kabusys/__init__.py によるモジュール公開（data, strategy, execution, monitoring）。
- 設定・環境変数管理 (kabusys.config)
  - .env ファイル自動読み込み（プロジェクトルートを .git / pyproject.toml で探索）。
  - .env パーサ実装（コメント、export プレフィックス、シングル/ダブルクォート、エスケープ処理対応）。
  - 自動ロード無効化フラグ（KABUSYS_DISABLE_AUTO_ENV_LOAD）。
  - Settings クラスによる型付きプロパティ、必須キーに対する検証（例: JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN 等）。
  - 環境値検証（KABUSYS_ENV, LOG_LEVEL の許容値チェック）。
- AI モジュール (kabusys.ai)
  - ニュースNLP（kabusys.ai.news_nlp）
    - raw_news / news_symbols を集約して銘柄ごとにニュースを結合し、OpenAI（gpt-4o-mini）でセンチメントを取得。
    - バッチ処理（最大 20 銘柄/リクエスト）、1銘柄あたりの記事数・文字数上限設定。
    - JSON Mode レスポンス検証・復元ロジック（余分な前後テキストの復元、結果バリデーション）。
    - 429/ネットワーク断/タイムアウト/5xx を対象とした指数バックオフでのリトライ。
    - DuckDB へ冪等書き込み（DELETE → INSERT、部分失敗時に他銘柄の既存スコアを保護）。
    - テスト用に OpenAI 呼び出しを差し替え可能（_call_openai_api を patch で置換）。
    - calc_news_window による JST ベースのニュース収集ウィンドウ算出（ルックアヘッド回避）。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）と、マクロニュースの LLM センチメント（重み 30%）を合成して日次でレジーム判定（bull/neutral/bear）。
    - MA 計算は target_date 未満のデータのみ使用（ルックアヘッド防止）。
    - マクロ記事抽出（マクロキーワードによるフィルタ）、OpenAI 呼び出し、リトライ/フォールバック（API 失敗時 macro_sentiment=0.0）。
    - DuckDB への冪等書き込み（BEGIN/DELETE/INSERT/COMMIT と ROLLBACK の保護）。
- データプラットフォーム (kabusys.data)
  - マーケットカレンダー管理（kabusys.data.calendar_management）
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day 等の営業日判定ユーティリティ。
    - market_calendar がない場合の曜日ベースフォールバック実装（週末除外）。
    - calendar_update_job による J-Quants からの差分取得 → 保存の夜間バッチロジック、バックフィル・健全性チェックを含む。
    - DuckDB 互換の型変換ヘルパやテーブル存在チェックなどの内部ユーティリティを提供。
  - ETL・パイプライン（kabusys.data.pipeline, kabusys.data.etl）
    - ETLResult データクラス（ETL 実行結果の構造化、品質問題・エラー集約）。
    - 差分更新、backfill、品質チェック方針の骨子を実装。
    - jquants_client 経由での取得・保存を想定した設計（idempotent 保存、品質チェック集約）。
    - etl モジュールから ETLResult を再エクスポート。
- リサーチ機能 (kabusys.research)
  - factor_research
    - モメンタム（1M/3M/6M リターン）、200 日 MA 乖離、ATR、出来高・売買代金系の算出ロジック（DuckDB SQL を主体に実装）。
    - calc_momentum, calc_volatility, calc_value の実装（prices_daily / raw_financials を参照）。
    - データ不足時の挙動（不足なら None、ログ出力で通知）。
  - feature_exploration
    - 将来リターン計算（calc_forward_returns）：任意ホライズンに対する fwd_xd の計算（LEAD を用いた SQL 実装）。
    - IC（Information Coefficient）計算（calc_ic）：スピアマンのランク相関を実装、必要最小レコード数チェック。
    - ランク変換ユーティリティ（rank）：同順位は平均ランクで処理。
    - 統計サマリー（factor_summary）：count/mean/std/min/max/median を計算（None 除外）。
- DB・トランザクション制御
  - DuckDB 向けクエリと接続引数受け渡しでの設計。
  - 書込み時の BEGIN/COMMIT/ROLLBACK 保護とエラーハンドリング（ログ出力含む）。
- 実装方針・安全策
  - ルックアヘッドバイアス回避: date.today()/datetime.today() を判定ロジックに直接使わない設計（target_date を明示）。
  - フェイルセーフ: 外部 API 失敗時は無害な中立値へフォールバックして処理継続。
  - テストしやすさを考慮したポイント（OpenAI 呼び出しの差し替え等）。

### Changed
- （初期リリースのため該当なし）

### Fixed
- （初期リリースのため該当なし）

### Security
- 外部 API キーは引数経由または環境変数 OPENAI_API_KEY により解決する仕様。未設定時に明示的にエラーを上げることで誤動作を防止。

### Notes / Known limitations
- OpenAI API への呼び出しは gpt-4o-mini を想定しているため、API レスポンス仕様の変更や利用制限に注意が必要。
- DuckDB のバージョン差異に起因するバインド挙動（list 型バインド等）を回避する実装が含まれるが、実行環境の DuckDB バージョンによっては挙動確認が必要。
- ETL / calendar_update_job 等は jquants_client に依存するため、実行には適切な API クレデンシャルと環境整備が必要。
- news_nlp と regime_detector は JSON レスポンスのパースを厳密化しているが、LLM の出力変化には注意（ロバストネスはあるが万全ではない）。
- 一部ファイル/関数は設計方針の注釈が残っており、今後の拡張（例: PBR・配当利回りの実装、strategy / execution の実装細部）が想定される。

---

この CHANGELOG はコードから推測して作成しています。実際のコミット履歴やリリースノートがある場合はそちらを優先してください。