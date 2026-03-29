# Changelog

すべての注記は Keep a Changelog の形式に準拠しています。  
レンジ: 初期リリース v0.1.0（パッケージ内の __version__ を基に作成）。

※日付は本生成時点（2026-03-29）をリリース日として記載しています。

## [Unreleased]

なし

## [0.1.0] - 2026-03-29

### Added
- パッケージ基本情報
  - kabusys パッケージ初期バージョン（__version__ = "0.1.0"）。
  - パッケージ公開 API として data / strategy / execution / monitoring を __all__ に定義。

- 環境設定・自動読み込み機能（kabusys.config）
  - .env / .env.local ファイルおよび環境変数を解釈・読み込みする自動ローダーを実装。
    - プロジェクトルートは __file__ を基点に .git または pyproject.toml を探索して検出（CWD に依存しない）。
    - 読み込み順序: OS 環境変数 > .env.local > .env。既存の OS 環境変数は保護される。
    - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能（テスト用途向け）。
  - .env パーサの拡張:
    - export KEY=val 形式に対応。
    - シングル/ダブルクォート中のエスケープ処理、インラインコメントの取り扱い、空行・コメント行の無視などに対応。
  - Settings クラスを提供（settings インスタンスをエクスポート）。
    - J-Quants / kabuステーション / Slack / DB パス / 実行環境（KABUSYS_ENV） / LOG_LEVEL 等のプロパティを定義。
    - 必須環境変数が欠けている場合は _require() により ValueError を送出。
    - 環境値の検証（KABUSYS_ENV, LOG_LEVEL の許容値チェック、Path の展開など）。

- AI ニュース NLP（kabusys.ai.news_nlp）
  - score_news(conn, target_date, api_key=None) を実装:
    - 対象ウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST（UTC 変換済み）を収集（calc_news_window）。
    - raw_news と news_symbols を結合して銘柄ごとに記事を集約（最大記事数・最大文字数でトリム）。
    - 最大 _BATCH_SIZE（20）銘柄ずつ OpenAI (gpt-4o-mini) に JSON mode で問い合わせてスコアを取得。
    - レスポンスの厳密なバリデーション（JSON 抽出、results 配列、code/score の存在、数値チェック、既知コードのみ採用）。
    - スコアを ±1.0 にクリップして ai_scores テーブルへ冪等的に保存（DELETE → INSERT、トランザクション管理）。
    - API の一時エラー（429 / ネットワーク断 / タイムアウト / 5xx）に対して指数バックオフでリトライ。
    - API キー未設定時は ValueError を送出。全体失敗時も部分成功のスコアは保持（フェイルセーフ設計）。
    - テスト用に _call_openai_api を差し替え可能。

  - calc_news_window(target_date) を実装: ウィンドウの UTC naive datetime を返すユーティリティ。

- AI 市場レジーム判定（kabusys.ai.regime_detector）
  - score_regime(conn, target_date, api_key=None) を実装:
    - ETF 1321（Nikkei225 連動）の直近200日移動平均乖離（ma200_ratio）を計算（_calc_ma200_ratio）。
      - target_date 未満のデータのみを使用し、データ不足時は中立値（1.0）を採用して警告ログ出力。
    - マクロキーワードでフィルタしたニュースタイトルを取得（_fetch_macro_news）。
    - OpenAI によるマクロセンチメント評価（_score_macro）。記事が無ければ呼び出さず 0.0 を返す。
    - 重み付け合成: ma (70%) と macro (30%) を組み合わせ、閾値により 'bull' / 'neutral' / 'bear' を判定。
    - market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）とトランザクションロールバック処理。
    - API キー未設定時は ValueError を送出。API 失敗時は macro_sentiment=0.0（フェイルセーフ）。
    - OpenAI 呼び出しはニュース NLP 実装と意図的に分離（モジュール結合を低くする設計）。

- Data モジュール（kabusys.data）
  - カレンダー管理（calendar_management）:
    - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day といったマーケットカレンダー問い合わせ API を実装。
    - market_calendar テーブルが存在しない場合や欠損値は曜日ベースのフォールバック（週末除外）で一貫した挙動を返す。
    - 最大探索日数に上限を設けて無限ループを防止（_MAX_SEARCH_DAYS）。
    - calendar_update_job(conn, lookahead_days=90) を実装。J-Quants クライアントから差分取得して market_calendar を冪等保存。バックフィルや健全性チェックを実装。
    - 内部ユーティリティ（_table_exists, _has_calendar_data, _fetch_is_trading など）を実装。

  - ETL パイプライン（pipeline）
    - ETLResult dataclass を追加: ETL の各種カウント、品質チェック結果、エラー情報を保持。to_dict でシリアライズ可能。
    - パイプライン内ユーティリティ（_table_exists, _get_max_date, _adjust_to_trading_day など）を実装。
    - kabusys.data.etl が pipeline.ETLResult を再エクスポート。

- Research モジュール（kabusys.research）
  - ファクター計算と特徴量探索を実装・公開:
    - calc_momentum(conn, target_date): mom_1m / mom_3m / mom_6m / ma200_dev を DuckDB SQL ベースで算出。
    - calc_volatility(conn, target_date): 20日 ATR（atr_20）、相対ATR（atr_pct）、avg_turnover、volume_ratio を算出。
    - calc_value(conn, target_date): raw_financials から最新財務データを取得し PER, ROE を算出（EPS が無効な場合は None）。
    - calc_forward_returns(conn, target_date, horizons=None): 指定ホライズンの将来リターンを一括 SQL で取得。
    - calc_ic(factor_records, forward_records, factor_col, return_col): スピアマンランク相関（IC）を実装（有効レコード <3 の場合は None）。
    - rank(values): 同順位は平均ランクにするランク計算ユーティリティ（丸めで ties 検出を安定化）。
    - factor_summary(records, columns): count/mean/std/min/max/median を算出する統計サマリー。
  - 研究用関数は外部 API に依存せず DuckDB 及び標準ライブラリのみで実装（本番発注系とは分離）。

### Changed
- （初期リリースにつき該当なし）

### Fixed
- （初期リリースにつき該当なし）

### Removed
- （初期リリースにつき該当なし）

---

## 互換性・注意事項 / マイグレーションノート
- 依存:
  - DuckDB を利用するため、環境に duckdb が必要です。
  - OpenAI SDK（OpenAI クライアント）を使用するため OpenAI の Python ライブラリが必要です。OpenAI のレスポンス仕様（JSON mode 等）に依存しています。
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等は Settings のプロパティで必須とされており、未設定時は ValueError を発生します（利用 API による）。
  - AI 機能（score_news, score_regime）を使用するには OPENAI_API_KEY を渡すか環境変数で設定してください。未設定時は ValueError。
- .env の自動読み込み:
  - パッケージ初期化時にプロジェクトルートが検出される場合は .env / .env.local を自動で読み込む挙動があります。テスト時に自動ロードを抑制したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- データベース操作:
  - ai_scores / market_regime 等のテーブル操作は冪等性を意識した DELETE→INSERT・トランザクション管理を行いますが、DuckDB バージョンによる executemany の制約（空リスト不可等）を考慮した実装になっています。
- フェイルセーフ設計:
  - 外部 API（OpenAI や J-Quants）失敗時はスコアリングをスキップまたは中立値で継続し、全体の停止を避ける設計です。ただし、API キー未設定は直ちに例外となります。
- 時刻処理とルックアヘッド:
  - AI スコアリング・レジーム判定等の関数は内部で datetime.today()/date.today() を参照しない設計（target_date 引数を明示）で、ルックアヘッドバイアスを防止しています。

---

もし CHANGELOG に追記したい追加情報（例: リリース日を別にしたい、特定の変更点を詳述したい、あるいは今後のリリースで出す予定の機能など）があれば指定してください。