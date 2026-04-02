# Changelog

すべての注目すべき変更をこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠し、セマンティックバージョニングを使用します。  

## Unreleased

（なし）

## [0.1.0] - 2026-04-02

### Added
- 基本パッケージ基盤
  - パッケージ初期バージョンを追加（kabusys.__version__ = 0.1.0）。
  - パッケージ公開インターフェースを __all__ で定義（data, research, ai, ...）。

- 環境設定 / ロード機能（kabusys.config）
  - .env ファイルおよび環境変数から設定を読み込む自動ローダーを実装。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能（テスト用途）。
    - プロジェクトルートは .git または pyproject.toml を基準に探索（CWD に依存しない）。
  - .env のパースは以下に対応:
    - コメント、空行、export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント（クォートなしの # の扱い）等。
  - 環境変数保護:
    - OS 環境変数を protected として .env による上書きを防止。
    - .env.local は override=True として .env の値を上書き可能。
  - Settings クラスを提供:
    - J-Quants / kabuAPI / Slack / DB パス / 監視閾値 / システム設定（KABUSYS_ENV, LOG_LEVEL）等のプロパティを公開。
    - 必須項目 (例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID) は未設定時に ValueError を発生させる。
    - KABUSYS_ENV と LOG_LEVEL の検証（許容値チェック）を実施。

- AI モジュール（kabusys.ai）
  - ニュース NLP スコアリング（kabusys.ai.news_nlp）
    - raw_news / news_symbols テーブルから対象記事を集約し、OpenAI（gpt-4o-mini）の JSON Mode を用いて銘柄ごとのセンチメント（-1.0〜1.0）を算出して ai_scores テーブルへ保存する。
    - バッチ処理: 1 API コールで最大 _BATCH_SIZE（デフォルト20）銘柄を一度に評価。
    - API レート制限・ネットワーク断・タイムアウト・5xx は指数バックオフでリトライ。リトライ上限を超えた場合は当該チャンクをスキップ（フェイルセーフ）。
    - レスポンス検証: JSON 抽出、results リスト・各要素の code/score 検証、未知コードは無視、スコアは ±1.0 にクリップ。
    - DuckDB 保存は部分的な失敗に備えて、スコア取得済みコードのみ DELETE → INSERT で置換（idempotent）。
    - 時間ウィンドウ計算（calc_news_window）を提供（前日15:00 JST ～ 当日08:30 JST に相当する UTC 時刻範囲）。
    - テスト容易性のため OpenAI 呼び出し箇所を差し替え可能（関数単位で patch しやすい設計）。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（日経225連動）について直近200日移動平均乖離（重み70%）とマクロセンチメント（重み30%）を合成し、日次で市場レジーム（bull/neutral/bear）を判定して market_regime テーブルへ保存する。
    - マクロセンチメントはニュースタイトルをマクロキーワードで抽出し、OpenAI により -1.0〜1.0 に評価。
    - API 呼び出しはリトライ/バックオフを実装し、失敗時は macro_sentiment=0.0 のフェイルセーフで継続。
    - DB 書き込みは BEGIN / DELETE / INSERT / COMMIT を行い冪等性を確保。障害発生時は ROLLBACK を試みる。

- データプラットフォーム（kabusys.data）
  - カレンダー管理（kabusys.data.calendar_management）
    - market_calendar を前提とした営業日判定 API を実装:
      - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day
    - DB にカレンダーがない場合は曜日ベース（土日を非営業日）でフォールバック。
    - calendar_update_job を実装し J-Quants API から差分取得して market_calendar を更新（バックフィル・健全性チェックを含む）。
  - ETL / パイプライン（kabusys.data.pipeline, kabusys.data.etl）
    - ETLResult データクラスを公開（取得件数・保存件数・品質問題・エラーを格納）。
    - 差分更新・バックフィル・品質チェックの設計方針を反映した ETL ベースラインを実装（jquants_client と quality モジュールと連携する想定）。
    - kabusys.data.etl で ETLResult を再エクスポート。

- リサーチ / ファクター（kabusys.research）
  - factor_research:
    - calc_momentum: mom_1m/mom_3m/mom_6m, ma200_deviation（データ不足時は None を返す）を計算。
    - calc_volatility: ATR(20), 相対 ATR, 20日平均売買代金, 出来高比率等を計算。
    - calc_value: raw_financials から最新財務を参照して PER, ROE を計算（EPS が 0/欠損の場合は None）。
    - 全て DuckDB の SQL を活用して高効率に計算。
  - feature_exploration:
    - calc_forward_returns: 指定 horizon(s) における将来リターンを取得（デフォルト: [1,5,21]）。
    - calc_ic: ファクター値と将来リターンの Spearman ランク相関（IC）を計算（有効レコード不足時は None）。
    - factor_summary: カラムごとの count/mean/std/min/max/median を計算。
    - rank: 平均順位付けを行うランク変換ユーティリティ（同順位は平均ランク）。
  - 実装方針:
    - 全関数は prices_daily / raw_financials 等の DB テーブルのみ参照し、本番発注系へのアクセスは行わない。
    - datetime.today()/date.today() を直接参照せず、必ず target_date を外部から受け取ることでルックアヘッドバイアスを排除。

- 汎用・堅牢性向上
  - OpenAI 呼び出し箇所は例外ハンドリングとリトライを備え、5xx/タイムアウト/レート制限などに対してバックオフ戦略を実装。
  - DB 書き込み時のトランザクションと ROLLBACK の取り扱いを明示。
  - DuckDB の executemany に対する空リスト回避のガードを追加。
  - ロギングを各モジュールに組み込み（情報・警告・例外の可視化を重視）。

### Changed
- 初回リリースのため該当なし。

### Fixed
- 初回リリースのため該当なし。

### Security
- OpenAI API キー・各種トークンは環境変数で管理することを想定。Settings で必須チェックを行うため、CI/デプロイ時に機密情報の管理を徹底してください。
- .env の自動ロードはテスト環境などで無効化可能（KABUSYS_DISABLE_AUTO_ENV_LOAD）。

### Notes / Developers
- 必要な主な環境変数:
  - OPENAI_API_KEY（AI モジュールを利用する際必須）
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
  - DUCKDB_PATH, SQLITE_PATH（デフォルトは data/ 配下）
- 設計方針の要点:
  - ルックアヘッドバイアス防止のため、時間基準は必ず外部から受け取る target_date を用いる。
  - 外部 API 呼び出し失敗時はフェイルセーフ（スキップまたは中立スコア）で継続する設計。
  - DB 操作は可能な限り冪等（idempotent）に設計。
  - DuckDB 接続を関数引数として受け取ることでテスト容易性を確保。

もし詳細な変更差分（コミット毎の記録）やリリースノートの拡張（既知の制限・互換性情報・移行手順など）を希望される場合は、追加情報（Git コミットログやリリースターゲット）を提供してください。