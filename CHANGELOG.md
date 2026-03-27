# CHANGELOG

すべての注目すべき変更を記録します。フォーマットは "Keep a Changelog" に準拠し、セマンティックバージョニングを使用します。

## [Unreleased]
- （現状のコードベースは初期リリース相当です。今後の変更はここに記載します。）

## [0.1.0] - 2026-03-27
初回リリース（コードベースのスナップショットに基づき推測）。

### Added
- パッケージ初期構成
  - kabusys パッケージの公開 API を定義（kabusys.__init__）。
  - バージョン: 0.1.0

- 環境設定管理（kabusys.config）
  - .env ファイルと OS 環境変数の自動読み込み機能を実装。
  - プロジェクトルートの検出（.git または pyproject.toml）に基づく .env / .env.local の優先読み込み。
  - export KEY=val 形式、シングル/ダブルクォートとバックスラッシュエスケープ、コメント処理に対応した .env パーサー実装。
  - 自動ロード無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - Settings クラスを提供し、主要設定項目をプロパティ経由で取得可能:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH, SQLITE_PATH
    - KABUSYS_ENV（development / paper_trading / live）と LOG_LEVEL の検証
    - is_live / is_paper / is_dev ヘルパー

- AI モジュール（kabusys.ai）
  - ニュース NLP（kabusys.ai.news_nlp）
    - raw_news と news_symbols を元に銘柄毎のニュースを集約し、OpenAI（gpt-4o-mini）の JSON Mode を用いて銘柄別センチメント（-1.0〜1.0）を算出。
    - バッチ処理（最大 20 銘柄）、1 銘柄あたりの最大記事数・最大文字数トリム、レスポンス検証、スコアクリップ、部分書き換え（DELETE → INSERT）による冪等保存を実装。
    - リトライ戦略（429/ネットワーク断/タイムアウト/5xx）とエラーフェイルセーフ（失敗時はスキップ・ログ記録）。
    - テスト容易性のため _call_openai_api をパッチ差し替え可能に実装。

  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成し、日次で 'bull' / 'neutral' / 'bear' を判定して market_regime テーブルへ冪等書き込み。
    - prices_daily を target_date 未満のデータのみで集計し、ルックアヘッドバイアスを回避。
    - マクロニュースはマクロキーワードでフィルタし、LLM（gpt-4o-mini）に JSON 応答を要求してスコアを取得。API 失敗時は macro_sentiment=0.0 で継続。
    - リトライ（指数バックオフ）、API エラー分類（5xx リトライ等）に対応。
    - _call_openai_api は news_nlp と意図的に分離（モジュール結合を低減）。

- Data モジュール（kabusys.data）
  - マーケットカレンダー管理（calendar_management）
    - market_calendar テーブルの使用を前提とした営業日判定ユーティリティを提供:
      - is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days
    - DB 登録値優先、未登録日は曜日ベースでフォールバックする一貫したロジック。
    - calendar_update_job による J-Quants からの差分取得と冪等保存（バックフィル・健全性チェック付き）。
  - ETL パイプライン（pipeline）
    - ETLResult データクラスを実装し、ETL 実行結果の集約（取得数・保存数・品質問題・エラー等）を提供。
    - 差分更新・バックフィル・品質チェック方針を実装するためのユーティリティを提供（テーブル存在チェックや最大日付取得など）。
  - etl モジュールは pipeline.ETLResult を再エクスポート。

- Research モジュール（kabusys.research）
  - factor_research:
    - Momentum（1M/3M/6M リターン・200 日 MA 乖離）、Volatility（20 日 ATR・相対 ATR）、Value（PER・ROE）などのファクター計算を実装。
    - DuckDB を用いた SQL ベースの高速計算（prices_daily / raw_financials を参照）。
    - データ不足時の None ハンドリング、結果を (date, code) ベースの dict リストで返す設計。
  - feature_exploration:
    - 将来リターン計算（calc_forward_returns）、IC（calc_ic）、rank、factor_summary など統計解析用ユーティリティを実装。
    - pandas 等に依存せず標準ライブラリのみで実装。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- API キー（OpenAI）や各サービスのトークンは Settings 経由で必須化。自動読み込み動作を無効化する環境変数を用意（テスト時の安全対策）。

### Notes / Implementation details（設計上の重要点）
- ルックアヘッドバイアス回避:
  - AI スコア計算・レジーム判定・ファクター計算などは内部で datetime.today()/date.today() を参照せず、呼び出し側が target_date を明示的に渡す設計。
  - DB クエリも target_date 未満／等の条件を明確に使用。

- 冪等性と部分書き換え:
  - データ書込み（ai_scores, market_regime, market_calendar 等）は既存レコードを削除してから挿入するなど、再実行に耐える実装を志向。

- エラーハンドリング:
  - OpenAI 呼び出しは 429/ネットワーク/タイムアウト/5xx をリトライ、その他はスキップしてフェイルセーフ（ログ記録）で継続。
  - DB 書き込みはトランザクション（BEGIN/COMMIT/ROLLBACK）で保護し、ROLLBACK 失敗時は警告ログを出力。

- テスト容易性:
  - OpenAI API 呼び出しを内部関数でラップし、unittest.mock.patch で差し替え可能にしている。

### Known limitations / Work in progress
- スニペットの末尾（kabusys.data.pipeline._adjust_to_trading_day の途中）が切れており、その関数の完全実装はコード抜粋に含まれていません。実運用前に当該部分の完成・レビューが必要です。
- data パッケージの __init__.py は空（公開 API の整理が今後必要）。
- 外部モジュール依存:
  - 実行には duckdb と openai (OpenAI SDK) が必要。その他 J-Quants / kabu ステーション / Slack 等の API クライアント（jquants_client 等）の実装や設定が前提。

### Breaking Changes
- なし（初回リリース）

---

開発チーム向けメモ:
- 環境変数キー一覧（Settings で参照）:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, DUCKDB_PATH, SQLITE_PATH, KABUSYS_ENV, LOG_LEVEL, OPENAI_API_KEY
- DB テーブル期待一覧（コード中で参照）:
  - prices_daily, raw_news, news_symbols, ai_scores, market_regime, raw_financials, market_calendar, など

今後のタスク候補:
- pipeline._adjust_to_trading_day の完実装と単体テスト追加。
- data パッケージの公開 API を整理しドキュメント化。
- CI における環境依存設定（API キー等）の扱い整備（自動ロード時の安全性確認）。
- テスト用モック（OpenAI, J-Quants, kabu API）を整備してテストカバレッジを向上。