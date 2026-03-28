# Changelog

すべての注記は Keep a Changelog のフォーマットに準拠しています。  
この CHANGELOG はソースコード（src/ 以下）の実装内容から推測して作成しています。

## [Unreleased]

（現時点で未リリースの変更はありません）

## [0.1.0] - 2026-03-28

### Added
- パッケージ初期リリース: kabusys (バージョン 0.1.0)
  - パッケージメタ情報: __version__ = "0.1.0"、公開モジュール: data, strategy, execution, monitoring を __all__ に設定。

- 環境設定・ロード機能（kabusys.config）
  - .env ファイルおよび OS 環境変数から設定を読み込む自動ロード機能を実装。プロジェクトルートは .git または pyproject.toml を基準に探索して決定。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能（テスト用途）。
  - .env パーサーは以下に対応:
    - コメント行・空行を無視
    - export KEY=val 形式を許容
    - シングル/ダブルクォートとバックスラッシュエスケープを考慮した値抽出
    - クォートなしでも '#' 直前が空白/タブの場合はインラインコメント扱い
  - .env の読み込みは override フラグおよび protected キー（既存 OS 環境変数保護）に対応。
  - Settings クラスを提供し、アプリで使う個別設定をプロパティとして公開:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID を必須としてチェック（未設定時は ValueError を送出）。
    - KABU_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH のデフォルト値を提供。
    - KABUSYS_ENV（development / paper_trading / live）の検証、LOG_LEVEL（DEBUG/INFO/...）の検証、便利な is_live / is_paper / is_dev プロパティ。

- AI 関連機能（kabusys.ai）
  - news_nlp モジュール:
    - raw_news と news_symbols を使って銘柄ごとにニュースを集約し、OpenAI（gpt-4o-mini, JSON Mode）でセンチメントを取得して ai_scores テーブルへ保存する機能を実装。
    - タイムウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST 相当の UTC 範囲）を calc_news_window で提供。
    - 1チャンクあたり最大 20 銘柄（_BATCH_SIZE）でバッチ送信。1銘柄あたりの最大記事数と最大文字数でトリムしてトークン肥大を抑制。
    - OpenAI API 呼び出しはリトライ（429/接続断/タイムアウト/5xx を指数バックオフで再試行）し、失敗時はスキップして処理継続する設計（フェイルセーフ）。
    - レスポンスの厳密なバリデーション（JSON パース、"results" 配列、code と score の検証、数値・有限値チェック）を実装。スコアは ±1 にクリップ。
    - DuckDB への置換保存処理は部分失敗に備え、影響範囲を限定するため score を取得した code のみ DELETE → INSERT で置換する。
    - テスト容易性のため _call_openai_api をパッチ可能にしている。

  - regime_detector モジュール:
    - 日次で市場レジーム（bull / neutral / bear）を判定する機能を実装。
    - 判定ロジックは ETF 1321 の 200 日移動平均乖離（重み 70%）とニュース由来の LLM マクロセンチメント（重み 30%）を合成してスコアを算出。
    - LLM 呼び出しは gpt-4o-mini（JSON mode）を使用し、API エラー時は macro_sentiment = 0.0 として継続（フェイルセーフ）。リトライロジック、5xx の扱いを実装。
    - レジームスコアはクリップして閾値に基づきラベル付与。market_regime テーブルへの書き込みは冪等性を考慮したトランザクション（BEGIN / DELETE / INSERT / COMMIT）で行う。
    - datetime.today()/date.today() を参照せず、target_date を明示的に与える設計でルックアヘッドバイアスを回避。

- Research（kabusys.research）
  - factor_research モジュール:
    - Momentum（1M/3M/6M リターン、200日 MA 乖離）、Volatility（20日 ATR、相対 ATR、20日平均売買代金、出来高比率）、Value（PER、ROE）を DuckDB の SQL + Python で計算する関数を提供（calc_momentum, calc_volatility, calc_value）。
    - データ不足時の扱いやウィンドウ設定（スキャンバッファ等）を明確化。
  - feature_exploration モジュール:
    - 将来リターン計算（calc_forward_returns）: 複数ホライズン（デフォルト [1,5,21]）に対応し、LEAD を用いた単一クエリで取得。
    - IC（Information Coefficient）計算（calc_ic）: スピアマンランク相関を実装（結合・欠損除外・最小データ数チェック）。
    - ランク変換ユーティリティ（rank）やファクター統計サマリー（factor_summary）を提供。
  - research パッケージは zscore_normalize（kabusys.data.stats から）等を再エクスポート。

- Data（kabusys.data）
  - calendar_management モジュール:
    - market_calendar テーブルを基に営業日判定ロジック（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）を実装。
    - DB にカレンダー情報がない場合は曜日ベースのフォールバック（土日除外）を使用する一貫した設計。
    - calendar_update_job を提供し、J-Quants API から差分取得 → 保存（バックフィル・健全性チェック含む）する夜間ジョブを実装。
    - 最大探索範囲または健全性チェックで無限ループや極端な将来日付の取り込みを防止。
  - ETL / pipeline（kabusys.data.pipeline）:
    - ETLResult データクラスを導入し、ETL 実行結果（取得/保存レコード数、品質問題、エラー）を構造化して返却可能に。
    - テーブル存在確認や最大日付取得などのユーティリティを実装。
    - 差分更新・backfill・品質チェックを行う ETL の設計方針を実装（実運用の J-Quants クライアントとの連携想定）。
  - etl.py は ETLResult を再エクスポート。

- その他
  - DuckDB を主要なオンディスク分析 DB として利用する設計（多くのモジュールで DuckDBPyConnection を受け取る）。
  - OpenAI API クライアントの注入（api_key 引数 or 環境変数 OPENAI_API_KEY）によりテスト・運用の柔軟性を確保。
  - ロギングが各モジュールで適切に配置されており、警告・情報出力を通じて失敗時のフォールバックが追跡可能。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Known issues / Notes
- OpenAI 呼び出しは外部 API に依存するため、API キー未設定時は明示的に ValueError を送出する実装となっている（運用前に環境変数の設定が必須）。
- DuckDB の executemany に関する互換性考慮や空パラメータ回避のコードがあるため、古い/新しい DuckDB バージョンでの挙動確認が必要な場合がある。
- .env 自動ロードはプロジェクトルート検出に依存するため、パッケージ配布後やプロジェクト構成によって想定通りに動作しない場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を使って明示的に管理すること。

---

（本 CHANGELOG はコードからの推測に基づくため、実際のコミット履歴や意図と異なる可能性があります。必要であれば、コミットメッセージやリリースノートに合わせて調整してください。）