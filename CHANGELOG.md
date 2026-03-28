# Changelog

すべての重要な変更をここに記録します。  
このファイルは Keep a Changelog の形式に準拠します。  

- リリースノートの順序は最新が上です。
- 不具合修正や設計上の重要な挙動も記載しています。

## [Unreleased]

## [0.1.0] - 2026-03-28
初回リリース。

### Added
- パッケージの初期構成
  - パッケージ名: kabusys
  - バージョン: 0.1.0
  - 公開モジュール: data, strategy, execution, monitoring（kabusys.__init__）

- 環境設定 / 設定管理 (kabusys.config)
  - .env ファイル（.env, .env.local）および OS 環境変数からの自動読み込み機能を実装。
    - プロジェクトルート判定は __file__ を起点に `.git` または `pyproject.toml` を探索（CWD 非依存）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD を設定することで自動ロードを無効化可能。
  - .env パーサ実装（コメント・export キーワード・クォート内のエスケープ処理などに対応）。
  - .env 読み込み時の上書き制御（override）および OS 環境変数保護（protected set）。
  - Settings クラスを提供し、以下の設定プロパティを用意：
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）, SQLITE_PATH（デフォルト: data/monitoring.db）
    - KABUSYS_ENV（development / paper_trading / live の検証）および LOG_LEVEL（DEBUG/INFO/... の検証）
    - is_live / is_paper / is_dev の簡易判定プロパティ

- AI モジュール (kabusys.ai)
  - news_nlp.score_news
    - raw_news / news_symbols テーブルを集約し、銘柄ごとにニュースを結合して OpenAI（gpt-4o-mini）へ送信しセンチメントを算出。
    - バッチ処理（1 API 呼び出しあたり最大 20 銘柄）、記事数・文字数トリム制御（最大記事数・最大文字数）。
    - 再試行戦略（429 / ネットワーク / タイムアウト / 5xx に対する指数バックオフ）。
    - レスポンスの堅牢なバリデーション（JSON 抽出、results 配列チェック、コード照合、スコア数値チェック）。
    - スコアは ±1.0 にクリップ。AI スコアを ai_scores テーブルへ冪等的に書き込み（DELETE→INSERT）。
    - ルックアヘッドバイアス防止のため、内部で datetime.today() を参照せず、target_date ベースでウィンドウを計算。
    - API キー注入可能（api_key 引数または環境変数 OPENAI_API_KEY）。
  - regime_detector.score_regime
    - ETF 1321（日経225連動ETF）の 200 日移動平均乖離（重み 70%）と、マクロ経済ニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull / neutral / bear）を判定。
    - マクロ記事抽出はキーワードベース（日本語・英語キーワード群）。
    - OpenAI 呼び出し（gpt-4o-mini, JSON mode）への再試行＆フォールバック（全失敗時 macro_sentiment=0.0）。
    - スコア合成・クリップ・ラベル判定。market_regime テーブルへ冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）。
    - API キー注入可能（api_key 引数または環境変数 OPENAI_API_KEY）。
    - テストのため _call_openai_api をモック可能に設計（関数分離）。

- Data モジュール (kabusys.data)
  - calendar_management
    - JPX カレンダー管理（market_calendar テーブル）：営業日判定、次/前営業日取得、期間内営業日一覧取得、SQ 日判定。
    - DB にカレンダーがない場合は曜日ベース（土日非営業日）でフォールバック。DB 登録がある日を優先。
    - calendar_update_job: J-Quants API からの差分取得と market_calendar への冪等保存（fetch/save は jquants_client を利用）。
    - バックフィル・健全性チェック（将来日が過度に遠い場合はスキップ）を実装。
  - pipeline / ETL
    - ETLResult データクラスを公開（etl パッケージから再エクスポート）。
    - ETL の差分取得方針、backfill、品質チェック（quality モジュール）との連携設計を含むユーティリティ関数群。
    - DuckDB の最大日付取得・テーブル存在チェック等のユーティリティを実装。

- Research モジュール (kabusys.research)
  - factor_research
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離率（ma200_dev）等のモメンタム指標を計算。
    - calc_volatility: 20 日 ATR（単純平均）、ATR 比率、20 日平均売買代金、出来高比率などボラティリティ／流動性指標を計算。
    - calc_value: raw_financials から最新財務を取得して PER / ROE を計算（EPS=0/欠損時は None）。
    - 設計：DuckDB SQL を主体に実装、データ不足時は None を返す、外部 API にはアクセスしない。
  - feature_exploration
    - calc_forward_returns: 指定日から将来ホライズン（デフォルト [1,5,21]）までのリターンを一括クエリで取得。
    - calc_ic: Spearman ランク相関（Information Coefficient）を計算。十分なデータがない場合は None。
    - rank: 同順位は平均ランクで扱う実装（丸め処理により ties の漏れを防止）。
    - factor_summary: 各ファクター列の count/mean/std/min/max/median を算出。
  - research パッケージは主要関数を __all__ でエクスポート（zscore_normalize は kabusys.data.stats から利用）。

- その他の実装上の設計方針（全体）
  - ルックアヘッドバイアス防止のため、内部処理はすべて target_date ベースで完結し datetime.today()/date.today() の直接参照を避ける設計。
  - DuckDB をデータ層の主要ストレージとして想定。
  - OpenAI 呼び出しは JSON Mode を利用しレスポンスの構造化を試みる。レスポンスパースの堅牢性（前後余計テキストの抽出等）を確保。
  - API 呼び出し失敗時はフェイルセーフ（例: macro_sentiment=0.0、スコア取得失敗はスキップ）で継続性を重視。
  - DB 書き込みは可能な限り冪等性を確保（DELETE→INSERT、ON CONFLICT 想定など）。
  - テスト容易性を考慮して OpenAI 呼び出し部分を差し替え可能に設計。

### Fixed
- 初回リリースにつき該当なし

### Changed
- 初回リリースにつき該当なし

### Deprecated
- 初回リリースにつき該当なし

### Removed
- 初回リリースにつき該当なし

### Security
- 初回リリースにつき該当なし

---

開発・運用上の注記
- OpenAI API キーは api_key 引数で注入可能（テストや CI で便利）。未設定時は OPENAI_API_KEY 環境変数を参照します。
- .env の自動読み込みはプロジェクトルート検出に依存します。配布後の挙動を考慮して自動ロードを無効化するフラグを用意しています。
- DuckDB の executemany 等、バージョン依存の挙動に対する互換性考慮（空リストを渡さない等）を実装で扱っています。