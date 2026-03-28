# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠して記載しています。  
バージョン番号はパッケージの __version__ (src/kabusys/__init__.py) に合わせています。

## [0.1.0] - 2026-03-28

### Added
- 初期公開: KabuSys 日本株自動売買システムのコアモジュール群を追加。
  - パッケージ構成: data, research, ai, monitoring, strategy, execution などの名前空間を公開。

- 環境設定管理 (kabusys.config)
  - .env / .env.local 自動ロード機能を実装（プロジェクトルートの検出: .git または pyproject.toml 基準）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化サポート（テスト向け）。
  - .env パーサ実装:
    - export KEY=val 形式対応、シングル/ダブルクォート内のバックスラッシュエスケープ処理、インラインコメント処理などを考慮。
  - _load_env_file による override / protected キー（OS 環境変数保護）制御。
  - Settings クラスを提供し、必要な環境変数をプロパティ経由で取得:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等の必須チェック。
    - DUCKDB_PATH / SQLITE_PATH の既定値と Path 変換。
    - KABUSYS_ENV / LOG_LEVEL の検証（許容値チェック）。
    - is_live / is_paper / is_dev ヘルパープロパティ。

- AI モジュール (kabusys.ai)
  - news_nlp:
    - raw_news テーブルからニュースを収集し、OpenAI（gpt-4o-mini）で銘柄別センチメントを算出して ai_scores テーブルへ書き込むフローを実装。
    - 時間ウィンドウ（前日15:00 JST ～ 当日08:30 JST）計算用の calc_news_window を提供。
    - バッチ処理 (最大 20 銘柄/コール)、1銘柄あたりの記事トリム（最大記事数・最大文字数）によるトークン肥大化対策。
    - 再試行（429、ネットワーク断、タイムアウト、5xx）と指数バックオフの実装。
    - レスポンスの堅牢なバリデーション（JSON抽出、results 型チェック、コード照合、数値検査）、スコアの ±1.0 クリップ。
    - DuckDB へは冪等的に部分置換（DELETE → INSERT）で書き込む実装（部分失敗時の既存スコア保護）。
    - テスト用フック: _call_openai_api を patch で差し替え可能。
  - regime_detector:
    - ETF 1321 の 200 日移動平均乖離（重み70%）とマクロニュースの LLM センチメント（重み30%）を合成して日次の市場レジーム（bull/neutral/bear）を算出。
    - ma200_ratio 計算は target_date 未満のデータのみ使用（ルックアヘッド防止）。
    - マクロニュース抽出（マクロキーワード）、OpenAI 呼び出し（gpt-4o-mini）による macro_sentiment 評価、API 再試行/フォールバック（失敗時は 0.0）。
    - 合成スコアの閾値によるラベル付け、market_regime テーブルへの冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）。
    - テスト用に _call_openai_api 実装を独立させモジュール結合を低減。

- Research モジュール (kabusys.research)
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、ma200 乖離などのモメンタム指標を計算。
    - calc_volatility: 20日 ATR、相対 ATR、20日平均売買代金、出来高比率を算出。
    - calc_value: raw_financials から EPS/ROE を取得して PER/ROE を計算（EPS 0 や欠損時は None）。
    - いずれも DuckDB の prices_daily / raw_financials のみを参照し、結果を (date, code) ベースの dict リストで返す。
  - feature_exploration:
    - calc_forward_returns: 指定 horizon の将来リターンを一度のクエリで取得（複数ホライズン対応、入力検証あり）。
    - calc_ic: ファクター値と将来リターンのスピアマンランク相関（IC）を計算（データ不足時は None）。
    - rank: 同順位は平均ランクにするランク化ユーティリティ（浮動小数の丸めで ties 対策）。
    - factor_summary: 各ファクター列の count/mean/std/min/max/median を算出。
  - research パッケージは zscore_normalize（kabusys.data.stats から）と主要関数を公開。

- Data モジュール (kabusys.data)
  - calendar_management:
    - market_calendar に基づく営業日ロジック（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）を実装。
    - DB 登録がない日/NULL 値は曜日ベースのフォールバック（週末除外）で一貫した挙動。
    - calendar_update_job: J-Quants からの差分取得・バックフィル・健全性チェック・保存の夜間バッチを実装（J-Quants クライアント経由）。
  - pipeline / etl:
    - ETLResult dataclass を実装し、ETL 実行結果（フェッチ数、保存数、品質問題、エラー等）を一元化。
    - 内部ユーティリティ: テーブル存在チェック、最大日付取得、トレーディング日補正など。
    - デフォルトバックフィルや calendar lookahead のポリシーを実装。
  - data パッケージは ETLResult を再エクスポート。

- 共通設計上の方針（各モジュール）
  - ルックアヘッドバイアス防止: score_news / score_regime 等で datetime.today() / date.today() を直接参照しない設計。
  - フェイルセーフ: 外部 API 失敗時は処理を停止せず、デフォルト値（例: macro_sentiment=0.0）で継続する実装。
  - DuckDB 互換性を考慮した実装（executemany の空引数回避、date 型変換ユーティリティ等）。
  - ロギング、警告、ROLLBACK の robust な扱い（書き込み失敗時は ROLLBACK を試行し、失敗ログを出力）。

### Changed
- （初版リリースのため該当なし）

### Fixed
- （初版リリースのため該当なし）

### Deprecated
- （初版リリースのため該当なし）

### Removed
- （初版リリースのため該当なし）

### Security
- 環境変数ロードにおいて OS 環境変数を protected として上書きを防止する仕組みを導入。
- 必須環境変数が未設定の場合は明確な例外メッセージを出力して失敗させる（誤動作防止）。

### Notes / Known limitations
- news_nlp のプロンプト設計では結果を厳密な JSON として期待しているが、LLM の出力によっては前後に余分なテキストが混入することがあるため復元ロジックを実装している（それでも不完全なケースはスキップされる）。
- calc_value では PBR や 配当利回りは未実装（将来拡張予定）。
- OpenAI API 呼び出しは gpt-4o-mini を想定。SDK や API の将来的な変更により例外型やフィールド名が変わった場合に対応が必要。
- calendar_update_job / pipeline の J-Quants クライアントは外部モジュールに依存しており、実行には適切な API キーやネットワークアクセスが必要。

--- 

今後のリリースではテストカバレッジの拡充、PBR/配当利回りなどバリューファクターの追加、発注・実行パス（execution / strategy）および監視（monitoring）機能の実装・強化を予定しています。