# Changelog

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。  

## [Unreleased]

## [0.1.0] - 2026-03-28
初回リリース（ベースライン実装）。

### Added
- パッケージ初期化
  - kabusys パッケージを公開。バージョンは 0.1.0。
  - __all__ に data, strategy, execution, monitoring を登録。

- 環境設定管理 (kabusys.config)
  - .env ファイルおよび環境変数から設定を読み込む自動ロード実装。
    - 読み込み優先度: OS 環境変数 > .env.local > .env
    - プロジェクトルート判定は __file__ を起点に .git または pyproject.toml を探索（CWD に依存しない挙動）。
    - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env パーサ実装（export KEY=val、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの扱いに対応）。
  - Settings クラスでアプリケーション設定をプロパティとして提供:
    - J-Quants / kabuステーション / Slack / DB パス等の設定を取得（必須項目は _require() で ValueError を発生）。
    - env（development / paper_trading / live）と log_level のバリデーション。
    - duckdb / sqlite のデフォルトパスを提供。

- AI モジュール (kabusys.ai)
  - ニュース NLP（kabusys.ai.news_nlp）
    - raw_news と news_symbols を集約して銘柄ごとにニュースをまとめ、OpenAI（gpt-4o-mini）に JSON モードでバッチ送信してセンチメントを算出。
    - タイムウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST（UTC に変換して DB クエリ実行）。
    - バッチ処理: 最大 20 銘柄 / リクエスト、1 銘柄当たり最大 10 記事・3000 文字でトリム。
    - リトライ戦略: 429 / ネットワーク断 / タイムアウト / 5xx を対象に指数バックオフでリトライ。
    - レスポンス検証: JSON 抽出・results 配列・code/score 検証・スコアは ±1.0 にクリップ。
    - 書き込み: 取得できた銘柄のみ ai_scores テーブルを DELETE → INSERT の冪等操作で置換（部分失敗時に既存スコアを保護）。
    - テスト容易性: _call_openai_api はパッチ可能に実装。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（Nikkei 225 連動型）の 200 日移動平均乖離（重み 70%）と、マクロニュースの LLM センチメント（重み 30%）を組み合わせて日次でレジーム（bull / neutral / bear）を判定。
    - MA 計算は target_date 未満のデータのみを使用しルックアヘッドを防止。
    - マクロニュースは news_nlp の calc_news_window を使ってウィンドウ抽出、最大 20 件を LLM に渡す。
    - OpenAI 呼び出しは独立実装。API エラー時は macro_sentiment=0.0 にフォールバックして処理継続。
    - 結果は market_regime テーブルへ冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）。DB 書き込み失敗時は ROLLBACK。

- データプラットフォーム (kabusys.data)
  - カレンダー管理（kabusys.data.calendar_management）
    - JPX カレンダー（market_calendar）を用いた営業日判定ユーティリティを提供:
      - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day
    - DB にデータがない場合は曜日（平日）ベースのフォールバック実装。
    - next/prev の探索は最大探索日数上限を設け無限ループを回避。
    - calendar_update_job: J-Quants クライアント経由で差分取得・バックフィル・保存を行う処理を実装し、健全性チェック（過剰な未来日付はスキップ）を搭載。
    - jquants_client を介した取得・保存処理を想定（外部クライアントモジュールに委譲）。
  - ETL パイプライン（kabusys.data.pipeline / etl）
    - ETLResult データクラスを公開（ETL 実行結果の集約・品質問題・エラー情報を保持）。
    - 差分更新・バックフィル・品質チェック・保存（idempotent）を行う ETL 設計に準拠するための下地実装。
    - 内部ユーティリティ: テーブル存在チェック、最大日付取得、トレーディングデー調整ユーティリティ等。
    - DataPlatform ドキュメントに合わせた設計方針（差分単位、部分失敗の保護、テスト容易性）。

- リサーチ（kabusys.research）
  - factor_research
    - モメンタム（1M/3M/6M リターン、ma200 乖離）、ボラティリティ（20日 ATR、相対 ATR）、流動性（20日平均売買代金・出来高比率）、バリュー（PER, ROE）の計算関数を提供。
    - DuckDB SQL をベースにしており、prices_daily / raw_financials テーブルのみ参照。
    - 不足データの扱い（必要行数未満で None を返す）や結果フォーマットは (date, code) をキーとした dict リスト。
  - feature_exploration
    - 将来リターン計算（任意ホライズン、デフォルト [1,5,21]）、IC（Spearman の ρ）計算、ランク付け、統計サマリー（count/mean/std/min/max/median）を実装。
    - 外部ライブラリに依存せず標準ライブラリと DuckDB のみで実装。
    - rank() は同順位の平均ランクを採る実装（浮動小数丸めで ties を安定化）。

### Changed
- なし（初回リリース）

### Fixed
- なし（初回リリース）

### Security
- なし（初回リリース）

### Notes / 注意事項
- OpenAI / J-Quants / Slack / kabu ステーション 等の外部 API キーやパスワードは環境変数で供給する必要があります。主な必須環境変数:
  - OPENAI_API_KEY（score_news / score_regime の呼び出しに必要）
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
  - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
- 自動 .env 読み込みはプロジェクトルートが検出できない場合はスキップされます（パッケージ配布後の安全性を考慮）。
- DuckDB を前提とした SQL 実装であり、テーブルスキーマ（prices_daily, raw_news, news_symbols, ai_scores, market_calendar, raw_financials, market_regime など）が期待されます。初期化スクリプトは含まれていません。
- AI 呼び出しは JSON Mode を使用した厳密な出力フォーマットを期待しますが、実運用では応答のばらつきに対する耐性（パース失敗時のフォールバック）を盛り込んでいます。
- 実際の発注・実行ロジック（execution モジュール等）は本リリースの範囲外（公開 API の設計は示唆されているが実装は別途）です。

### Migration / 移行
- 既存データベース／カレンダーデータが未設定の場合、関数は曜日ベースでのフォールバックを行います。将来的に市場カレンダーを導入する場合は market_calendar テーブルを用意してください。
- AI スコア周りを利用するには OPENAI_API_KEY を設定してください。テスト時は各モジュールの _call_openai_api をモックしてください（実装でパッチ可能になっています）。

---
このリリースはコードベース（src/kabusys 以下）から抽出した機能と設計意図に基づき作成しています。追加のリリースや修正がある場合は本 CHANGELOG を更新してください。