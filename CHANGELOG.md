# Changelog

すべての注目すべき変更履歴をここに記録します。  
フォーマットは「Keep a Changelog」に準拠し、セマンティックバージョニングを採用します。

なお、このファイルはコードベースから推測して作成した初期リリースの変更履歴です。

## [Unreleased]

- なし

## [0.1.0] - 2026-03-28

初回公開リリース。

### Added
- パッケージ基盤
  - kabusys パッケージ初期化（バージョン 0.1.0）。__all__ に data, strategy, execution, monitoring を公開。
- 設定管理
  - 環境変数・設定管理モジュールを追加（kabusys.config）。
    - .env / .env.local をプロジェクトルート（.git または pyproject.toml を探索）から自動ロードする機能。
    - 自動ロードを無効化する環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD。
    - .env と .env.local の読み込み優先順位（OS環境変数 > .env.local > .env）。.env.local は上書き（override=True）。
    - .env 解析は export 形式、クォート、インラインコメント等に対応。
    - Settings クラスを提供し、アプリケーション設定（J-Quants / kabuステーション / Slack / DB パス / 環境・ログレベル判定等）をプロパティとして取得可能。
    - 必須環境変数未設定時は ValueError を投げる _require() を使用。
    - デフォルト DB パス: DUCKDB_PATH="data/kabusys.duckdb", SQLITE_PATH="data/monitoring.db"。
    - 有効な KABUSYS_ENV 値: development / paper_trading / live。LOG_LEVEL の検証も実施。
- AI（自然言語処理）
  - kabusys.ai パッケージ
    - news_nlp.score_news: ニュース記事を OpenAI（gpt-4o-mini）でセンチメント解析し、ai_scores テーブルへ書き込むバッチ処理を提供。
      - 対象ウィンドウ: target_date の前日 15:00 JST 〜 当日 08:30 JST（内部は UTC naive datetime）。calc_news_window ユーティリティを提供。
      - 銘柄毎に記事を集約し、最大 _BATCH_SIZE (20) 銘柄ずつバッチ送信。1銘柄あたり記事数・文字数上限を適用（_MAX_ARTICLES_PER_STOCK/_MAX_CHARS_PER_STOCK）。
      - API エラー（429/ネットワーク/タイムアウト/5xx）は指数バックオフでリトライ。その他エラーは該当チャンクをスキップして継続（フェイルセーフ）。
      - レスポンスのバリデーションを実施し、スコアを ±1.0 にクリップ。部分成功時は成功銘柄のみ ai_scores を更新（DELETE → INSERT の冪等処理）。
      - テスト容易性のため OpenAI 呼び出し箇所を patch 可能（kabusys.ai.news_nlp._call_openai_api）。
    - regime_detector.score_regime: ETF（1321）の 200 日移動平均乖離とニュース由来のマクロセンチメントを重み合成し、市場レジーム（bull/neutral/bear）を判定して market_regime テーブルへ書き込む。
      - MA 要素（重み 70%）と LLM によるマクロセンチメント（重み 30%）を統合。
      - マクロ記事の抽出はマクロキーワード一覧でフィルタ。記事が無い場合は LLM コールをスキップ（macro_sentiment=0.0）。
      - OpenAI API 呼び出しのリトライ・フェイルセーフ・JSON パース失敗時のフォールバックを実装。
      - DB 書き込みは冪等（BEGIN / DELETE / INSERT / COMMIT）。失敗時は ROLLBACK を行い上位へ例外を伝播。
      - テスト容易性のため OpenAI 呼び出し箇所を差し替え可能（kabusys.ai.regime_detector._call_openai_api）。
- 研究（Research）モジュール
  - kabusys.research パッケージを追加。research 内で利用可能な関数を再エクスポート。
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離（ma200_dev）を計算。データ不足時は None を返す。
    - calc_volatility: 20日 ATR、相対 ATR（atr_pct）、20日平均売買代金（avg_turnover）、出来高比率を計算。必要行数不足時は None。
    - calc_value: raw_financials から直近財務を取得し PER / ROE を計算（EPS が 0 または欠損時は None）。
  - feature_exploration:
    - calc_forward_returns: 複数ホライズンの将来リターンを一括取得（デフォルト [1,5,21]）。horizons の検証あり。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を計算。有効レコード数が 3 未満なら None。
    - rank: 同順位は平均ランクで扱うランク付けユーティリティ（丸めで ties の検出漏れを防止）。
    - factor_summary: count/mean/std/min/max/median を計算する統計サマリ機能。
  - zscore_normalize を含むデータ統計ユーティリティへの参照を再エクスポート。
- データプラットフォーム（Data）
  - kabusys.data パッケージ
    - calendar_management: JPX カレンダー管理と営業日判定機能を提供。
      - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を実装。
      - market_calendar がない場合は曜日ベース（土日非営業）でフォールバックする一貫したロジック。
      - calendar_update_job: J-Quants API から差分取得して market_calendar を冪等に更新。バックフィル・健全性チェックを実装。
    - pipeline, etl:
      - ETLResult データクラスを定義し、ETL の実行結果と品質問題（quality モジュール）を集約可能に。
      - ETL に関するユーティリティ（差分取得、backfill、品質チェック方針）を定義（実装は pipeline 内）。
    - jquants_client / quality 等は参照している前提（実装は別モジュールで提供）。
- テスト・デバッグ補助
  - OpenAI 呼び出し箇所に対してユニットテストで差し替え可能な設計（関数抽出）を採用。
- エラーハンドリングとフェイルセーフ
  - AI API 呼び出しに対するリトライ（指数バックオフ）・フェイルセーフロジックを複数箇所に実装。
  - DuckDB 書き込みはトランザクション（BEGIN/COMMIT/ROLLBACK）で保護し、ROLLBACK の失敗ログを捕捉。

### Changed
- 初回リリースのため該当なし。

### Fixed
- 初回リリースのため該当なし。

### Deprecated
- 初回リリースのため該当なし。

### Removed
- 初回リリースのため該当なし。

### Security
- 本パッケージは複数の機密情報（OPENAI_API_KEY、JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、SLACK_BOT_TOKEN 等）を環境変数で参照します。  
  - .env を利用する場合は .env.example を参照し、機密情報はリポジトリにコミットしないでください。
  - 自動 .env 読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

### Notes / Known limitations
- OpenAI 連携は gpt-4o-mini を前提としており、API レスポンスは JSON モードを想定しています。必ずレスポンスのバリデーションを行う設計です。
- ETL / J-Quants 連携部分（jquants_client, quality など）は本リリースの他モジュール実装に依存します。実運用前に API クレデンシャルと DB 初期化を行ってください。
- strategy / execution / monitoring などの上位モジュール（__all__ に列挙）は公開インターフェースとして存在しますが、個別機能の実装状況によっては追加ドキュメント・安定化が必要です。
- duckdb バージョン依存の挙動（executemany に空リスト不可等）に配慮した実装になっていますが、動作確認は環境ごとに行ってください。

---

今後のリリース予定:
- 監視（monitoring）・注文実行（execution）・戦略（strategy）周りの具体的実装とエンドツーエンドの統合テストの追加。
- ドキュメント（Usage / Deployment / Examples）の整備。