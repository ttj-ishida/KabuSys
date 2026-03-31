# Changelog

すべての重要な変更は "Keep a Changelog" の形式に従って記録します。  
このファイルはコードベース（初期リリース想定）の現状から推測して作成しています。

フォーマット:
- 変更はセクション別（Added, Changed, Fixed, Deprecated, Removed, Security）で記載しています。
- バージョンはパッケージ内の __version__（0.1.0）に合わせています。

## [0.1.0] - 2026-03-31

### Added
- パッケージの初期実装を追加（KabuSys: 日本株自動売買システムの骨格）。
  - パッケージバージョン: 0.1.0
  - パブリックAPIのエントリポイントに data, strategy, execution, monitoring を公開。

- 環境設定管理 (kabusys.config)
  - プロジェクトルートを .git または pyproject.toml から自動検出し、.env / .env.local をロードする自動ローダーを実装。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応。
  - .env パーサーは export プレフィックス、シングル/ダブルクォート内のバックスラッシュエスケープ、行内コメントの取り扱いに対応。
  - OS 環境変数を保護する protected 機構（.env.local が OS 環境変数を上書きしない等）を実装。
  - Settings クラスで主要設定をプロパティとして提供（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, DUCKDB_PATH, SQLITE_PATH, PID_FILE_PATH, CPU/MEMORY/DISK 閾値, KABUSYS_ENV, LOG_LEVEL など）。
  - KABUSYS_ENV と LOG_LEVEL の値検証を実装し、不正な値は ValueError を送出。

- データモジュール (kabusys.data)
  - ETL・パイプライン基盤（kabusys.data.pipeline）を実装。ETL 実行結果を表す ETLResult データクラスを公開。
  - calendar_management: JPX カレンダー管理（market_calendar テーブル）を提供。営業日判定、前後営業日の取得、期間内営業日列挙、SQ 判定、夜間バッチ更新ジョブ（calendar_update_job）を実装。
    - DB に calendar 情報がない場合は曜日ベース（土日除外）でフォールバック。
    - 夜間ジョブはバックフィルや健全性チェックを行い、J-Quants クライアント経由で差分取得・冪等保存を行う。
  - ETL 用のユーティリティと設計（差分取得、backfill 処理、品質チェックとの連携）を用意。
  - jquants_client と quality モジュールを呼び出す想定のインターフェースを整備。

- 研究（Research）モジュール (kabusys.research)
  - factor_research: モメンタム、ボラティリティ、バリュー等のファクター計算関数を実装。
    - calc_momentum: 1M/3M/6M リターン、200 日移動平均乖離（ma200_dev）を計算。
    - calc_volatility: 20 日 ATR、相対 ATR（atr_pct）、20 日平均売買代金、出来高比率を計算。
    - calc_value: PER（EPS が 0/欠損時は None）、ROE を raw_financials と prices_daily から計算。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一括取得。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を計算。
    - rank: 値をランクへ変換（同順位は平均ランク）。
    - factor_summary: カラムごとの count/mean/std/min/max/median の統計サマリーを算出。
  - すべての関数は DuckDB 接続を受け取り、prices_daily / raw_financials 等の DB テーブルのみ参照する設計（実運用口座・発注 API には触れない）。

- AI モジュール (kabusys.ai)
  - news_nlp.score_news:
    - raw_news / news_symbols を集約して銘柄ごとに記事をまとめ、OpenAI（gpt-4o-mini / JSON mode）へバッチ送信してセンチメントを算出。
    - チャンク処理（最大 _BATCH_SIZE=20 銘柄）、1 銘柄当たりの記事数・文字数上限（_MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK）を実装。
    - レスポンスのバリデーション（JSON 抽出、results 配列、code/score 検証）とスコアの ±1.0 クリップを実装。
    - API の 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフリトライ。失敗時は部分的にスキップして他コードを保護する（DELETE→INSERT の idempotent 書き込み）。
    - テスト用に _call_openai_api を patch して差し替え可能。
  - regime_detector.score_regime:
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とニュース由来のマクロセンチメント（重み 30%）を合成して market_regime テーブルを日次で書き込み。
    - マクロニュースは news_nlp.calc_news_window によるウィンドウからフィルタ（マクロキーワード一覧）して取得、LLM に送信。
    - LLM 呼び出しは gpt-4o-mini、JSON mode。API 失敗時は macro_sentiment=0.0 でフォールバック（フェイルセーフ）。
    - スコア合成後、market_regime テーブルへの冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）を実装。

- その他ユーティリティ
  - DuckDB との互換性や実行時の健全性を考慮した各種防御実装を追加（例: DuckDB executemany の空リスト回避、date の変換ユーティリティなど）。
  - ロギングを豊富に追加して処理の追跡性を確保。

### Changed
- （初期リリースのため該当なし）設計方針や安全対策については多くのモジュール内に明確に注記済み：
  - ルックアヘッドバイアス回避のため datetime.today()/date.today() を直接参照しない実装方針。
  - DB クエリは target_date より前・後の境界を明確に扱う実装。
  - 外部 API 失敗時のフェイルセーフ（例: マクロセンチメント 0.0、スコア未取得銘柄の保護）を採用。

### Fixed
- DuckDB の実装差分に起因する実行時問題を回避するための対応を実装。
  - executemany に空リストを渡せないバージョン対策として事前チェックを追加。
  - market_calendar / ai_scores 等の置換処理で部分失敗時に他データを消さないよう DELETE → INSERT の戦略を採用。

### Deprecated
- （初期リリースのため該当なし）

### Removed
- （初期リリースのため該当なし）

### Security
- OpenAI API キーや各種秘密情報は Settings 経由で環境変数から取得する設計。キーが未設定の場合は ValueError を発生させ明示的に扱う。
- .env の自動ロードは環境変数から無効化可能（KABUSYS_DISABLE_AUTO_ENV_LOAD）でテスト環境へ配慮。

---

注記（実装上の重要ポイント、README 等へ記載推奨）
- OpenAI API 呼び出しは JSON mode を想定しており、LLM の返却が仕様どおりでない場合はパースロジックが余裕を持って復元を試みる（最外の {} を抽出する等）。
- テスト容易性のため、AI モジュールの内部 API 呼び出し関数（_kabusys.ai.news_nlp._call_openai_api や kabusys.ai.regime_detector._call_openai_api）は unittest.mock.patch で差し替え可能に設計されている。
- settings が必須とする環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID（未設定でアクセスすると ValueError）
  - OPENAI_API_KEY は AI 関数呼び出し時に引数で渡すことも可能（引数優先）。未指定なら環境変数を参照。
- DuckDB スキーマ（prices_daily, raw_news, raw_financials, ai_scores, market_calendar など）に依存するため、初期データロード/スキーマ作成手順のドキュメント化を推奨。

もし詳細なリリースノートや各関数の API ドキュメント（使用例・期待される DB スキーマ・サンプルデータ）を別途作成したい場合は、優先順位に応じてセクションを分けて作成します。必要であればテンプレートや README も作成します。