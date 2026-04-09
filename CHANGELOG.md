# Changelog

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) の形式に従います。  
このファイルはコードベースから推測して作成した初期リリース向けの変更履歴です。

## [Unreleased]

## [0.1.0] - 2026-04-09
Initial release — 日本株自動売買／データ基盤のコアライブラリを追加。

### Added
- パッケージ初期化
  - kabusys パッケージのバージョンを `0.1.0` として公開。主要サブパッケージを __all__ で公開（data, research, ai, execution, monitoring, strategy などを想定）。

- 環境設定管理（kabusys.config）
  - .env と .env.local の自動ロード機能を実装（読み込み優先順位: OS 環境変数 > .env.local > .env）。
  - プロジェクトルート探索（.git または pyproject.toml を基準）により CWD に依存しない自動読み込み。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応（テスト用途）。
  - .env パーサーを実装（export 形式、シングル/ダブルクォート内のエスケープ、インラインコメントの扱いなどに対応）。
  - 環境変数の必須チェック用 _require() と Settings クラスを提供。
  - 主な設定項目（例）:
    - JQUANTS_REFRESH_TOKEN（必須）
    - KABU_API_PASSWORD（必須）
    - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
    - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（通知用）
    - DUCKDB_PATH / SQLITE_PATH（データベースパス、デフォルト値あり）
    - PAPER_FILL_MODE（paper trading のモックフィルモード。許容値: instant, partial, never, reject）
    - PAPER_TRADING_SQLITE_PATH（paper trading 用 DB）
    - 監視関連設定（PID / kill flag / リソース閾値）
    - KABUSYS_ENV（development / paper_trading / live の検証）
    - LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL の検証）
  - 設定アクセスはプロパティを介して行い、無効値検出時は ValueError を送出。

- ニュース NLP（kabusys.ai.news_nlp）
  - raw_news と news_symbols を用いて銘柄ごとのニュースを集約し、OpenAI（gpt-4o-mini）の JSON mode を使ってセンチメント（ai_score）を取得。
  - タイムウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST に対応する UTC 範囲）を提供（calc_news_window）。
  - バッチ処理（1APIコールあたり最大 20 銘柄）、記事・文字数のトリム（最大記事数・最大文字数）を実装。
  - 再試行ポリシー（429 / ネットワーク断 / タイムアウト / 5xx を対象に指数バックオフでリトライ）。
  - レスポンスの厳格バリデーション、JSON パース時の前後余分テキスト復元ロジック。
  - DuckDB へ冪等的に書き込むロジック（部分失敗時に既存スコアを保持する方針: 対象コードのみ DELETE → INSERT）。
  - フェイルセーフ: API 未設定や致命的失敗時は例外またはスキップする挙動（呼び出し側で制御可能）。

- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とマクロニュース由来の LLM センチメント（重み 30%）を合成して日次レジーム（bull / neutral / bear）を判定。
  - OpenAI 呼び出しは独立実装でモジュール結合を避ける設計。
  - リトライ / フェイルセーフ（API 失敗時 macro_sentiment=0.0 をフォールバック）。
  - DuckDB へ冪等的に書き込むトランザクション処理（BEGIN / DELETE / INSERT / COMMIT、失敗時は ROLLBACK）。
  - ルックアヘッドバイアス回避のため、target_date 未満のデータのみを利用し、datetime.today() を参照しない設計。

- データモジュール（kabusys.data）
  - calendar_management:
    - market_calendar を用いた営業日判定ユーティリティ（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）。
    - DB にデータがない場合は曜日ベース（平日は営業日）でのフォールバック。
    - 夜間バッチ更新ジョブ calendar_update_job: J-Quants API から差分取得・バックフィル・健全性チェックを行い market_calendar を更新。
  - pipeline / etl:
    - ETLResult データクラスを公開（ETL 実行の集計情報・品質問題・エラー一覧を保持）。
    - ETL パイプラインの方針（差分更新・バックフィル・品質チェック・idempotent 保存）を反映した設計。

- Research モジュール（kabusys.research）
  - factor_research:
    - モメンタム（1M/3M/6M リターン）、200 日 MA 乖離、ATR（20 日）、20 日平均売買代金・出来高比率などのファクター計算関数（calc_momentum / calc_volatility / calc_value）。
    - prices_daily / raw_financials のみを参照する、外部 API に依存しない実装。
    - データ不足時は None を返す仕様。
  - feature_exploration:
    - 将来リターン計算（calc_forward_returns）。horizons のバリデーション（正の整数かつ <= 252）。
    - IC（Information Coefficient）計算（calc_ic）: スピアマンのランク相関（最小有効サンプル数チェック）。
    - ランク付けユーティリティ（rank）: 同順位は平均ランク、数値丸めで ties 対応。
    - 統計サマリー（factor_summary）: count/mean/std/min/max/median を算出。

- モジュール公開の整理
  - ai.__init__ で score_news を公開。
  - research.__init__ で主要なリサーチ関数と zscore_normalize（data.stats から）を再エクスポート。
  - data.etl で ETLResult を再エクスポート。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Security
- API キーの取り扱い:
  - OpenAI API キーは関数引数で注入可能（テスト容易性）。引数未指定時は環境変数 OPENAI_API_KEY を参照。
  - 環境変数自動ロード時、OS 環境変数は保護され .env/.env.local による上書きを防止。

---

注意事項 / マイグレーションメモ
- OpenAI 関連機能を利用するには環境変数 OPENAI_API_KEY を設定するか、score_news / score_regime の api_key 引数でキーを渡してください。未設定時は ValueError を送出します。
- .env 自動ロードはプロジェクトルート（.git または pyproject.toml）を基準に行います。パッケージ配布先での挙動に注意してください。自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB の executemany は空リストを受け付けないバージョン差異に配慮した実装（空リストチェックあり）。
- 時刻や日付の扱いはルックアヘッドバイアス回避のため、内部で datetime.today()/date.today() を参照しない設計を徹底しています（target_date を明示的に渡す形を採用）。

既知の設計的配慮（今後の改善候補）
- OpenAI 呼び出しはモデル名やタイムアウト等ハードコードされている箇所があるため、将来的に設定化すると利便性が向上します。
- ai_score のスコアリングで使用するプロンプトやトークン上限のハンドリングは運用に合わせてチューニングが必要です。

---

作成元: ソースコード（src/ 以下）の解析に基づき推測・要約して作成しました。必要があれば各機能項目を詳述したリリースノートを生成します。