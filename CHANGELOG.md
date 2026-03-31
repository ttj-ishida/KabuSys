# Changelog

すべての重要な変更をこのファイルに記録します。  
このプロジェクトは Keep a Changelog に準拠しています。  
安定版リリースはセマンティックバージョニングを採用しています。

## [Unreleased]
(なし)

## [0.1.0] - 2026-03-31
初回リリース。日本株のデータ取得・前処理・リサーチ・AI スコアリング・カレンダー管理を中心としたライブラリを提供します。

### 追加 (Added)
- パッケージ全体
  - パッケージメタ情報: kabusys v0.1.0
  - モジュール構成の公開: data, strategy, execution, monitoring（__all__）

- 設定・環境変数管理 (kabusys.config)
  - .env ファイルまたは環境変数からの設定読み込みを自動で行うローダーを実装。
    - プロジェクトルートは .git または pyproject.toml を探索して特定。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env
    - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  - .env のパースロジックはコメント、export プレフィックス、クォート、エスケープ等に対応。
  - Settings クラスを導入し、以下のプロパティ経由で設定にアクセス可能:
    - JQUANTS_REFRESH_TOKEN (必須)
    - KABU_API_PASSWORD (必須)
    - KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
    - SLACK_BOT_TOKEN (必須)
    - SLACK_CHANNEL_ID (必須)
    - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
    - SQLITE_PATH (デフォルト: data/monitoring.db)
    - KABUSYS_ENV (development/paper_trading/live、デフォルト development)
    - LOG_LEVEL (DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト INFO)
  - 設定取得時のバリデーションと必須チェックを実装（未設定時は ValueError を発生）。

- AI 関連 (kabusys.ai)
  - ニュース NLP スコアリング (kabusys.ai.news_nlp)
    - raw_news と news_symbols を使って銘柄ごとのニュースを集約し、OpenAI（gpt-4o-mini）の JSON mode を用いて銘柄ごとのセンチメント（-1.0〜1.0）を算出。
    - タイムウィンドウ: 前日 15:00 JST 〜 当日 08:30 JST（UTC に変換して DB クエリ）。
    - バッチ処理: 最大 20 銘柄ずつ API 送信、1 銘柄あたり最大 10 記事・3000 文字でトリム。
    - 再試行・バックオフ: 429/ネットワーク/タイムアウト/5xx に対して指数バックオフでリトライ。
    - レスポンスの厳密な検証とスコアクリッピング（±1.0）。
    - 書き込み: ai_scores テーブルに対して、部分成功時に既存データを保護するため対象コードのみ DELETE → INSERT。
    - 公開 API: score_news(conn, target_date, api_key=None) → 書き込んだ銘柄数を返す。
    - テスト容易性: OpenAI 呼び出し箇所をモック可能（_call_openai_api を patch）。

  - 市場レジーム判定 (kabusys.ai.regime_detector)
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成し、日次で市場レジーム（bull/neutral/bear）を判定。
    - マクロ記事はマクロキーワードでフィルタ（複数キーワード定義済み）。
    - OpenAI（gpt-4o-mini）を用いたセンチメント評価。API 失敗時は macro_sentiment=0.0 で継続する安全化。
    - 冪等書き込み: market_regime テーブルへ BEGIN/DELETE/INSERT/COMMIT で保存。
    - 公開 API: score_regime(conn, target_date, api_key=None) → 1 を返す（成功）。

- データプラットフォーム (kabusys.data)
  - ETL パイプライン (kabusys.data.pipeline)
    - ETLResult データクラス導入: ETL 実行の取得/保存件数、品質問題、エラー一覧を保持。
    - 差分取得、バックフィル、カレンダー参照ロジックのためのユーティリティを実装。
  - ETL 公開インターフェース (kabusys.data.etl)
    - ETLResult を再エクスポート。
  - カレンダー管理 (kabusys.data.calendar_management)
    - JPX 市場カレンダーの夜間バッチ更新ジョブ calendar_update_job 実装（J-Quants クライアント経由で差分取得→保存）。
    - 営業日判定/次営業日/前営業日/期間内営業日取得/is_sq_day 等のユーティリティを実装。
    - DB にカレンダーがない場合は曜日ベース（土日除外）でフォールバック。
    - バックフィル期間や探索上限等の安全策を実装（_BACKFILL_DAYS, _MAX_SEARCH_DAYS, _SANITY_MAX_FUTURE_DAYS）。

- Research モジュール (kabusys.research)
  - ファクター計算 (kabusys.research.factor_research)
    - Momentum: 1M/3M/6M リターン、200 日 MA 乖離計算（データ不足時は None）。
    - Volatility: 20 日 ATR、ATR 比率、20 日平均売買代金、出来高比率。
    - Value: PER（EPS=0/欠損時は None）、ROE（raw_financials 参照）。
    - いずれも DuckDB の prices_daily / raw_financials を参照し、SQL で高効率に計算。
  - 特徴量探索 (kabusys.research.feature_exploration)
    - 将来リターン calc_forward_returns（任意ホライズン、デフォルト [1,5,21]）。
    - IC（Spearman のランク相関）calc_ic。
    - ランク変換ユーティリティ rank（同順位は平均ランク）。
    - ファクター統計 summary を算出する factor_summary（count/mean/std/min/max/median）。
  - 便利な再エクスポート: zscore_normalize を含む（kabusys.data.stats 参照）。

### 変更 (Changed)
- 初回公開のため変更履歴はなし。

### 修正 (Fixed)
- 初回公開のため修正履歴はなし。

### 既知の制約・注意点 (Notes / Known limitations)
- OpenAI API 呼び出しには gpt-4o-mini を想定している。API キーは api_key 引数または環境変数 OPENAI_API_KEY で供給する必要がある。未設定の場合は ValueError を発生。
- DuckDB を想定した SQL 実装のため、DuckDB バージョンに依存する挙動（リストバインドの扱い等）がある。コード内で互換性向上のための回避策を取っている（ex. executemany を利用した DELETE の繰り返し）。
- ai モジュールは LLM の出力形式に依存しているため、実運用ではレスポンス監視と適切なリトライ設定・監査が必要。
- 発注/実行ロジック（実際の売買）は本リリースでは含まれていない（strategy, execution パッケージは公開されているが、実トレード実装は別途必要）。

### テスト支援 / 開発者向け
- OpenAI 呼び出し箇所（news_nlp._call_openai_api, regime_detector._call_openai_api）はテストで差し替え（unittest.mock.patch）可能。これにより外部 API をモックしてユニットテストが行える。
- 自動 .env 読み込みを無効化する環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD が利用可能（ユニットテストや CI で便利）。

### セキュリティ (Security)
- API キーやパスワード等の機密値は環境変数を通して供給する設計。.env をリポジトリに含めないこと（.env.example を参照する旨のメッセージを出す）。
- auto env loader は既存の OS 環境変数を保護するため .env の上書きを制御する仕組みを持つ。

---

貢献・バグ報告・改善提案は Issue を通じてお願いします。