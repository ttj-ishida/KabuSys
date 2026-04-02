# Changelog

すべての注目すべき変更はこのファイルに記録します。  
このファイルは Keep a Changelog の形式に準拠しています。<https://keepachangelog.com/ja/1.0.0/>

## [Unreleased]
- （現時点で未リリースの変更はありません）

## [0.1.0] - 2026-04-02
初回リリース（コードベースの現状に基づく機能群と設計方針をまとめています）。

### Added
- パッケージ基盤
  - kabusys パッケージを追加。公開 API として data, strategy, execution, monitoring をエクスポート。
  - パッケージバージョンを `__version__ = "0.1.0"` に設定。

- 設定 / 環境変数管理
  - `kabusys.config.Settings` を実装。J-Quants / kabu ステーション / Slack / データベースパス / 監視閾値 等の設定プロパティを提供。
  - .env 自動ロード機能を追加（プロジェクトルートの判定は .git または pyproject.toml を基準に実施）。
  - .env ファイルパーサーを実装（export プレフィックス対応、シングル/ダブルクォートのエスケープ、コメントの扱い等）。
  - OS 環境変数を保護するため、.env 上書き時に既存の OS 環境変数を保護する仕組みを導入。
  - 自動ロード抑止用の環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD` を追加（テスト用等）。

- データプラットフォーム関連
  - `kabusys.data.pipeline.ETLResult` を公開（ETL 実行結果の構造化）。
  - ETL パイプライン骨格を実装（差分取得、保存、品質チェックを想定）。
  - DuckDB を前提としたデータ操作ユーティリティを多数実装。

- カレンダー管理
  - `kabusys.data.calendar_management` を追加。
  - market_calendar テーブルを用いた営業日判定と補助関数を実装：
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day
  - JPX カレンダーの夜間差分取得ジョブ `calendar_update_job` を追加（J-Quants クライアント経由、バックフィル・健全性チェック付き）。

- 研究（Research）モジュール
  - `kabusys.research` 名前空間とファクター計算を提供。
  - `factor_research`:
    - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離の計算。
    - calc_volatility: 20日 ATR、相対 ATR、20日平均売買代金、出来高比率等を計算。
    - calc_value: raw_financials から PER / ROE を算出。
  - `feature_exploration`:
    - calc_forward_returns: 将来リターンの一括計算（複数ホライズン対応）。
    - calc_ic: ファクター値と将来リターンの Spearman ランク相関（IC）を計算。
    - factor_summary / rank: 統計要約・ランク変換ユーティリティ。
  - 研究用ユーティリティとして `kabusys.data.stats.zscore_normalize` を再エクスポート。

- AI / NLP 機能
  - `kabusys.ai.news_nlp.score_news` を実装：
    - raw_news と news_symbols を元に銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini）の JSON Mode でバッチ評価して `ai_scores` テーブルへ書き込む。
    - バッチ処理（最大 20 銘柄/チャンク）、記事トリム（最大記事数・最大文字数）をサポート。
    - API 呼び出しに対してエクスポネンシャルバックオフのリトライ処理を実装。
    - レスポンスのバリデーション処理（JSON 抽出、results 配列チェック、コード正規化、スコア数値化、±1.0 クリップ）を実装。
    - 部分成功を考慮して ai_scores の置換は該当コードのみ DELETE → INSERT する設計（部分失敗で既存スコアを保護）。
    - テスト容易性のため OpenAI 呼び出し部分は差し替え可能（内部関数に対して patch 可能）。

  - `kabusys.ai.regime_detector.score_regime` を実装：
    - ETF 1321 の 200 日移動平均乖離（70%）とマクロニュースセンチメント（30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定し `market_regime` テーブルへ冪等書き込み。
    - マクロニュースは `news_nlp.calc_news_window` を用いてフィルタし、OpenAI（gpt-4o-mini）により -1.0〜1.0 を返す想定（JSON のみ）。
    - API 失敗時はフェイルセーフとして macro_sentiment=0.0 を採用。
    - レトライ・エラーハンドリング、JSON パースの耐性強化を実施。

### Changed / Design decisions
- ルックアヘッドバイアス回避
  - いずれの処理（news スコア、レジーム判定、ファクター計算、将来リターン計算）でも内部で datetime.today() / date.today() を直接参照せず、必ず明示的な target_date を受け取る設計。
  - DB クエリは target_date 未満 / 限定レンジで取得することでルックアヘッドを防止。

- DB 操作の安全性
  - DuckDB の仕様差（executemany に空リストを渡せない等）を考慮して、INSERT/DELETE の前にパラメータリストの空チェックを行う。
  - トランザクション処理時に例外が発生した場合は ROLLBACK を試行し、ROLLBACK に失敗した場合は警告ログを出す。

- OpenAI / 外部 API
  - OpenAI 呼出はモデル `gpt-4o-mini` を使用する想定。
  - レート制限・ネットワーク断・タイムアウト・5xx に対してリトライ（指数バックオフ）を実装。非 5xx の APIError やレスポンスパースエラーはフォールバック動作（例: スコア 0.0、該当チャンクスキップ）とすることで処理継続を優先。

### Fixed / Robustness improvements
- 環境変数パーサーの堅牢化
  - export キーワード、クォート内のバックスラッシュエスケープ、行内コメントの扱い等に対応。
  - キーが空の場合の無視、無効行のスキップ実装。

- LLM レスポンスの耐性向上
  - JSON Mode でも前後に余計なテキストが混入するケースに備え、最外の波括弧 {} を抽出して JSON を復元する処理を追加。
  - LLM が整数形式でコードを返す場合を想定してコードを文字列化して照合。

- データ不足時の安全なフォールバック
  - 1321 のデータが不足する場合、MA200 比率は中立（1.0）を返す。
  - ニュース記事がない場合は LLM 呼び出しを行わず、macro_sentiment=0.0 を用いる。

- ロギング
  - 主要な分岐やエラー時に適切な情報ログ／警告ログ／例外ログを出力するよう整備（tracing に有用）。

### Known limitations / Notes
- 外部依存:
  - J-Quants API や OpenAI API の利用に際しては、環境変数（例: OPENAI_API_KEY, JQUANTS_REFRESH_TOKEN）や適切な認証情報が必要。
- 実装上の想定:
  - DuckDB に特化した SQL を利用しているため、他の DB での互換性は保証していません。
- セキュリティ:
  - .env 自動ロードはデフォルトで有効。CI/テストで不要な場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

もしリリース日や追加のリリースノート（個別のコミットに対応した変更点）を指定いただければ、それに合わせて CHANGELOG を調整します。