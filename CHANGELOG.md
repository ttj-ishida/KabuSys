# CHANGELOG

すべての重要な変更を記録します。本ファイルは Keep a Changelog の形式に従っています。  
初期リリースと主要な機能・設計上の注意点をコードベースから推測してまとめています。

全般方針:
- 重大なバグ修正・破壊的変更は Breaking changes として明示します（現状なし）。
- 日付は本ソーススナップショット作成日（2026-03-31）を使用しています。

## [0.1.0] - 2026-03-31
初回公開リリース。

### 追加
- パッケージ全体
  - 基本パッケージエントリポイントを追加（kabusys.__init__）。
  - バージョンは 0.1.0。

- 設定・環境変数管理（kabusys.config）
  - .env ファイルおよび環境変数の自動読み込み機能を実装。
    - プロジェクトルートは .git または pyproject.toml を基準に探索（CWD 非依存）。
    - 読み込み優先順位: OS環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
  - .env のパースは以下に対応:
    - 空行、コメント行（#）の無視。
    - export KEY=val 形式のサポート。
    - シングル/ダブルクォート内でのバックスラッシュエスケープ対応。
    - クォートなしの行では '#' が直前に空白/タブある場合のみコメントとして扱う。
  - 必須環境変数取得ユーティリティ (_require) を提供。
  - アプリケーション設定ラッパー Settings を提供。取得可能な設定例:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH（デフォルト data/kabusys.duckdb）
    - SQLITE_PATH（デフォルト data/monitoring.db）
    - KABUSYS_ENV（validation: development / paper_trading / live）
    - LOG_LEVEL（validation: DEBUG/INFO/WARNING/ERROR/CRITICAL）
    - is_live / is_paper / is_dev の便宜プロパティ

- AI 関連（kabusys.ai）
  - news_nlp モジュール
    - raw_news と news_symbols を集約し、OpenAI（gpt-4o-mini）を使って銘柄ごとにニュースセンチメント（ai_score）を算出し ai_scores テーブルへ保存する処理を実装。
    - タイムウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST（UTC に変換して DB 比較）。
    - チャンク処理: 最大 20 銘柄／コール、1 銘柄あたり最大 10 記事、3000 文字でトリム。
    - JSON Mode を期待したレスポンス検証を実装（厳密な JSON を想定しつつ前後余計なテキストを復元する処理あり）。
    - 再試行ロジック: 429・接続断・タイムアウト・5xx は指数バックオフでリトライ（デフォルト上限）。
    - レスポンス検証で未知コードや数値以外は無視し、スコアは ±1.0 にクリップ。
    - 部分失敗を考慮して、ai_scores の置換は対象コードの DELETE → INSERT を行い既存データの保護を実現。
    - 公開関数: score_news(conn, target_date, api_key=None) → 書き込んだ銘柄数を返す。

  - regime_detector モジュール
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（70%）と、news_nlp 経由のマクロセンチメント（30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定し market_regime テーブルへ冪等書き込みを行う。
    - MA 計算は target_date 未満のデータのみを使用しルックアヘッドを防止。
    - マクロニュースは _MACRO_KEYWORDS に基づき raw_news から抽出、最大 20 記事を LLM に投げる。
    - OpenAI 呼び出しは独立実装、API 再試行・フェイルセーフ（失敗時は macro_sentiment=0.0）を備える。
    - 公開関数: score_regime(conn, target_date, api_key=None) → 成功時 1 を返す。

- データ・ETL（kabusys.data）
  - calendar_management
    - JPX マーケットカレンダー用ユーティリティを実装（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）。
    - market_calendar が未取得の場合は曜日ベース（土日）でフォールバック。
    - 夜間バッチ calendar_update_job(conn, lookahead_days) で J-Quants API から差分取得 → 保存（バックフィル・健全性チェックあり）。
  - pipeline / etl
    - ETLResult データクラスを公開（ETL 実行メタ情報、品質チェック結果、エラー一覧等を格納）。
    - ETL パイプライン設計に基づく差分取得・保存・品質チェックの骨組みを実装。
    - 内部ユーティリティ: テーブル存在チェック、最大日付取得など。
  - jquants_client など外部クライアントは別モジュールに委譲（モックや差し替えが容易）。

- リサーチ（kabusys.research）
  - factor_research
    - モメンタム（1m/3m/6m リターン、ma200 乖離）、ボラティリティ（20日 ATR、相対 ATR）、流動性指標（20日平均売買代金、出来高比率）、バリュー（PER, ROE）を計算する関数を実装。
    - すべて DuckDB の prices_daily / raw_financials を参照し外部 API に依存しない。
    - 公開関数: calc_momentum, calc_volatility, calc_value（各日付ごとに (date, code) をキーとした dict list を返す）。
  - feature_exploration
    - 将来リターン計算 (calc_forward_returns)、IC（calc_ic）計算、ファクター統計サマリー (factor_summary)、およびランク変換ユーティリティ (rank) を実装。
    - pandas 等には依存せず標準ライブラリ + DuckDB で実装。
    - calc_forward_returns は horizons のバリデーションと一括クエリ実行で効率化。

### 変更
- 初回リリースのため過去バージョンからの変更点はありません（新規実装）。

### 修正 / 考慮済みの堅牢化
- AI 呼び出し部分での堅牢性向上:
  - OpenAI API の 429 / 接続断 / タイムアウト / 5xx を対象とした再試行（指数バックオフ）。
  - JSON パース失敗時のフォールバック（文字列から最外の {} を抽出して復元）。
  - レスポンス検証を厳格化し、不正なスコアや未知コードを無害化。
- DB 書き込みは冪等性を意識して実装（DELETE → INSERT、トランザクション管理、例外時の ROLLBACK）。
- ルックアヘッドバイアス回避設計:
  - datetime.today()/date.today() を直接参照しないコード設計（関数引数で target_date を受ける）。
  - prices_daily クエリで target_date 未満・BETWEEN 範囲などを適切に指定。

### 注意事項（互換性・運用）
- OpenAI API
  - gpt-4o-mini を前提とした JSON Mode を使用。API キーは引数で注入可能（テスト時に差し替えやモックが可能）。
  - api_key 未提供かつ環境変数 OPENAI_API_KEY 未設定の場合、score_news / score_regime は ValueError を送出する。
- 環境変数の必須項目（例: JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, KABU_API_PASSWORD）を設定しておく必要あり。
- DuckDB を前提とした SQL 実装のため、DuckDB バージョン差異（例: executemany の空リスト挙動や配列バインド）に留意。
- calendar_update_job 等の外部 API 呼び出し部は jquants_client 依存。実行環境で該当クライアントが利用可能であること。

### 既知の制約 / 今後の改善候補（コードから推測）
- ai_scores / market_regime 等のスキーマ依存: スキーマ変更時は ETL/pipeline 側も修正が必要。
- news_nlp のレスポンスサイズやトークン超過対策は基本的対処（トリム）に留まるため、長文対策やプロンプト最適化の余地あり。
- エラーハンドリングはフェイルセーフ（失敗時はスキップ）を優先しているため、運用側での監視・アラートが重要。

---

今後のリリースでは、「小さな機能追加」「バグ修正」「破壊的変更（Breaking changes）」をセクション別に分けて追記してください。