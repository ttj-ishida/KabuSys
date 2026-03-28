# Changelog

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠しています。

※ このリリースノートは提示されたコードベースから推測して作成しています。

## [Unreleased]

## [0.1.0] - 2026-03-28
初回リリース

### Added
- パッケージ基盤
  - パッケージ名: kabusys、バージョン: 0.1.0（src/kabusys/__init__.py）。
  - top-level エクスポート: data, strategy, execution, monitoring。

- 設定 / 環境変数管理 (src/kabusys/config.py)
  - .env ファイルおよび環境変数から設定を自動ロードするユーティリティを実装。
    - プロジェクトルート判定: .git または pyproject.toml を起点に探索（CWD に依存しない）。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1。
    - .env パーサは export KEY=val、クォート・エスケープ、インラインコメントなどに対応。
  - Settings クラスを提供し、環境変数をプロパティ経由で参照可能:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH（デフォルト data/kabusys.duckdb）
    - SQLITE_PATH（デフォルト data/monitoring.db）
    - KABUSYS_ENV（development, paper_trading, live の検証）
    - LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL の検証）
    - ヘルパー: is_live / is_paper / is_dev
  - 未設定の必須環境変数に対しては ValueError を発生させる _require を実装。

- データプラットフォーム機能 (src/kabusys/data/...)
  - calendar_management
    - JPX マーケットカレンダー管理機能（market_calendar テーブルを前提）。
    - 営業日判定 API: is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days。
    - 夜間バッチ更新ジョブ: calendar_update_job（J-Quants から差分取得・保存、バックフィル、健全性チェック）。
    - DB 登録が不十分な場合は曜日ベースのフォールバック（週末除外）を使用。
    - 探索上限 (_MAX_SEARCH_DAYS) を設け無限ループを防止。
  - ETL / pipeline
    - ETLResult データクラスを公開（kabusys.data.etl に再エクスポート）。
    - 市場データの差分更新・保存・品質チェックを想定した設計（backfill・品質問題の集約など）。
    - DuckDB を想定したヘルパー関数（テーブル存在チェック、最大日付取得など）。
  - jquants_client と quality モジュール連携を想定（実装は参照箇所のみ）。

- AI（自然言語処理）機能 (src/kabusys/ai/...)
  - ニュース NLP（src/kabusys/ai/news_nlp.py）
    - raw_news / news_symbols テーブルから記事を集約し、銘柄ごとに OpenAI（gpt-4o-mini）へバッチ送信してセンチメントを算出。
    - タイムウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST（UTC に変換して処理）。
    - バッチサイズ、1 銘柄あたりの最大記事数・文字数トリム、JSON Mode を使った堅牢なレスポンス処理。
    - 再試行ポリシー: 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフ。
    - レスポンス検証: JSON 抽出、"results" の存在確認、code の正規化、スコアの数値化と有限性チェック、±1.0 でクリップ。
    - DB 書き込みは部分的な失敗に備え、対象コードのみを DELETE → INSERT で置換（冪等性と既存データ保護）。
    - テストフック: OpenAI 呼び出し部分はモジュール内関数をパッチして差し替え可能。
    - 公開 API: score_news(conn, target_date, api_key=None) を提供。ai モジュールの __all__ に score_news をエクスポート。
  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次レジーム（bull/neutral/bear）を判定。
    - マクロニュース抽出は news_nlp.calc_news_window を使用し、マクロキーワードでフィルタ。
    - OpenAI 呼び出し（gpt-4o-mini）と再試行・エラーハンドリングを実装。API 失敗時は macro_sentiment=0.0（フェイルセーフ）。
    - レジームスコアはクリップされ、market_regime テーブルへ冪等的に書き込み（BEGIN / DELETE / INSERT / COMMIT）。
    - 公開 API: score_regime(conn, target_date, api_key=None)。

- Research（因子・特徴量探索）機能 (src/kabusys/research/...)
  - factor_research
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離などのモメンタム系ファクターを計算。
    - calc_volatility: 20 日 ATR、相対 ATR、平均売買代金、出来高比率などボラティリティ/流動性系を計算。
    - calc_value: raw_financials と prices_daily を組み合わせて PER, ROE を計算（EPS が 0/欠損なら None）。
    - 実装は DuckDB SQL を中心に行い、lookup 範囲や滑らかな欠損処理を考慮。
  - feature_exploration
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを計算。horizons のバリデーションあり。
    - calc_ic: スピアマンランク相関（IC）を計算。サンプル数不足時は None を返す。
    - rank: 同順位は平均ランクにするランク化ユーティリティ（浮動小数の丸め対策あり）。
    - factor_summary: count/mean/std/min/max/median を算出する統計サマリー。
  - research パッケージは主要関数を __all__ で再エクスポート。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Notes / 実装上の重要ポイント（運用時注意）
- 全ての日付計算で datetime.today() / date.today() を直接参照しない設計（ルックアヘッドバイアス回避）。関数呼び出し側が target_date を渡す必要がある。
- OpenAI 連携部分は gpt-4o-mini を利用し、JSON Mode を前提とした厳密なパースとバリデーションを実装。
- API キーは関数引数で注入可能（api_key=None の場合は環境変数 OPENAI_API_KEY を使用）。未設定の場合は ValueError を送出。
- DuckDB に対する executemany の制約（空リスト不可）を考慮した実装（空チェックを行う）。
- DB 書き込みは冪等性を意識（既存行の DELETE → INSERT、トランザクションで囲む）。書き込み失敗時は ROLLBACK を試み、ROLLBACK 失敗はログ出力。
- テスト容易性のため、OpenAI 呼び出し箇所はモジュール内プライベート関数をパッチして差し替え可能。

### Required / 推奨環境変数
- 実行に必須（使用する機能により必須となる）
  - JQUANTS_REFRESH_TOKEN (データ取得)
  - KABU_API_PASSWORD (kabu API)
  - SLACK_BOT_TOKEN / SLACK_CHANNEL_ID (通知)
  - OPENAI_API_KEY (AI 機能を利用する場合)
- 任意
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1（自動 .env ロードを無効化）
  - KABUSYS_ENV（development / paper_trading / live）
  - LOG_LEVEL（ログレベル）
  - DUCKDB_PATH / SQLITE_PATH（DB パスのオーバーライド）

### Breaking Changes
- 初回リリースのため該当なし。

### Security
- OpenAI API キー等の機密情報は環境変数で管理する設計。.env 自動ロードの制御フラグを用意。

---

フィードバックや追加の実装情報があれば、それを元にリリースノートを拡張します。