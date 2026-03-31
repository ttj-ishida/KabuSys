# Change Log

すべての重要な変更をこのファイルに記録します。  
このプロジェクトは Keep a Changelog の慣習に従い、セマンティック バージョニングを採用します。

なお以下はソースコード（src/）の実装内容から推測して作成した変更履歴です。

## [Unreleased]
- 今後のリリース向けの改善メモ（例）
  - OpenAI 呼び出しのモック用フック拡張やテストカバレッジの強化
  - ETL パイプラインの細粒度なメトリクス集計・可視化
  - jquants_client / kabu ステーション周りの接続リトライ・認証フロー強化

---

## [0.1.0] - 2026-03-31

### Added
- 初期リリース。パッケージ名: kabusys (バージョン 0.1.0)
  - パッケージ公開情報: src/kabusys/__init__.py に __version__ = "0.1.0" を設定。

- 設定管理
  - .env ファイルおよび環境変数の自動読み込み機能を実装（src/kabusys/config.py）。
    - プロジェクトルート検出は .git または pyproject.toml を探索して行うため、CWD に依存しない動作。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD で自動読み込み無効化が可能。
    - 高度な .env パーサを実装（export 構文、シングル/ダブルクォート、エスケープ、インラインコメント扱いなど）。
    - Settings クラスを提供し、必須環境変数取得（_require）や各種設定プロパティを公開:
      - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等の必須チェック
      - データベースパス（DUCKDB_PATH, SQLITE_PATH）、監視設定（PID_FILE_PATH, CPU/MEM/MEM閾値）等のデフォルト値
      - KABUSYS_ENV（development / paper_trading / live）と LOG_LEVEL の検証ユーティリティ

- AI モジュール（OpenAI 統合）
  - ニュース NLP（src/kabusys/ai/news_nlp.py）
    - raw_news と news_symbols を集約して銘柄ごとにニュースをまとめ、OpenAI（gpt-4o-mini）の JSON Mode を用いてセンチメントスコアを算出。
    - タイムウィンドウ計算（JST 基準 → UTC 変換）を提供する calc_news_window を実装。
    - バッチ処理（最大 20 銘柄 / リクエスト）、入力トリム（記事数・文字数制限）を実装。
    - エラーハンドリング: レート制限 / ネットワーク断 / タイムアウト / サーバー 5xx に対する指数バックオフのリトライ、レスポンスパース失敗時のフォールバック（スキップ）。
    - レスポンスバリデーション（JSON 抽出、results の整合性チェック、未知コードの無視、スコアの数値化とクリップ）。
    - 成果は ai_scores テーブルへ冪等的に保存（DELETE → INSERT、DuckDB executemany の空リスト回避）。
    - テスト容易性のため _call_openai_api を切り替え可能に実装。
  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321（日経225 連動型）の 200 日移動平均乖離（重み 70%）とマクロセンチメント（重み 30%）を合成して日次レジーム（bull / neutral / bear）を算出。
    - マクロ記事のフィルタリング（マクロキーワード一覧） → LLM による macro_sentiment の評価（gpt-4o-mini、JSON Mode）。
    - API 呼び出しに対するリトライ/フォールバックロジック（失敗時 macro_sentiment=0.0）を実装。
    - market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）を実装。
    - ルックアヘッドバイアス回避の設計（date 引数ベース、DB クエリに date < target_date の排他条件等）。

- Data モジュール（DuckDB ベース）
  - カレンダー管理（src/kabusys/data/calendar_management.py）
    - market_calendar テーブルを利用した営業日判定 API を提供:
      - is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days
    - DB 未取得時は曜日ベースのフォールバック（週末除外）を採用。
    - calendar_update_job: J-Quants API から差分取得して market_calendar を冪等保存。バックフィルや健全性チェック（将来日付の異常検出）を実装。
    - 最大探索日数上限（_MAX_SEARCH_DAYS）で無限ループを防止。
  - ETL / パイプライン（src/kabusys/data/pipeline.py, src/kabusys/data/etl.py）
    - ETLResult データクラスを実装（取得/保存件数、品質問題、エラー一覧などを格納）。
    - 差分更新、バックフィル、品質チェック（quality モジュールとの連携）を行うETLの設計方針を実装。
    - jquants_client の save_* 関数を用いた冪等保存を想定。
    - src/kabusys/data/etl.py で ETLResult を公開（再エクスポート）。

- Research モジュール（ファクター計算・特徴量探索）
  - ファクター計算（src/kabusys/research/factor_research.py）
    - モメンタム（1M/3M/6M リターン、ma200_dev）、ボラティリティ（20 日 ATR、atr_pct）、流動性（平均売買代金、volume_ratio）、
      バリュー（PER、ROE）を DuckDB クエリで計算する関数群: calc_momentum, calc_volatility, calc_value。
    - 必要データ不足時は None を返す方針（安全設計）。
    - DuckDB のウィンドウ関数を活用し、営業日ベースのラグ計算を実装。
  - 特徴量探索（src/kabusys/research/feature_exploration.py）
    - 将来リターン計算（calc_forward_returns）: LEAD を使い複数ホライズンを一度に算出、入力検証（horizons の範囲）。
    - IC（Information Coefficient）計算（calc_ic）: スピアマンランク相関を実装（ランクは平均ランクを採用、ties は round で安定化）。
    - ランク関数（rank）と統計サマリー（factor_summary）を実装（外部依存なし）。

### Changed
- （初期リリースのため該当なし）設計上の注意点を README/ドキュメントに反映推奨:
  - OpenAI API キーは api_key 引数または OPENAI_API_KEY 環境変数から解決（未設定時は ValueError）。
  - 日時処理はルックアヘッドバイアスを避けるため target_date ベースで実装されている点を明記。

### Fixed
- （初期リリース）内部実装での耐障害性・互換性考慮:
  - DuckDB executemany の空リスト制約を回避するためのガード実装。
  - OpenAI SDK バージョン差異（APIError に status_code がある場合の安全参照）への対応。

### Security
- 機密情報（API トークン等）は Settings クラス経由で環境変数から取り扱う設計。自動 .env ロードは環境変数上書き保護（protected set）を行うことで OS 環境変数の意図せぬ上書きを防止。

---

メンテナンス / 今後の改善提案（コードからの推測）
- OpenAI 呼び出しのレート制御・バッチ最適化の追加（コスト削減のため）。
- 詳細なロギングとメトリクス（各チャンク・API 呼び出しの成功率・遅延）を収集する仕組み。
- DB マイグレーションスキーマやスキーマ検証ツールの導入。
- 単体テスト・統合テストの追加（特に LLM レスポンスのパース・ETL のロバストネス）。

以上。必要であれば各変更項目を英語版に翻訳する、あるいは各関数ごとの変更差分（コミット単位想定）に合わせたより細かい CHANGELOG を作成します。どの形式がよいか指示してください。