# Changelog

すべての重要な変更はこのファイルに記録します。  
形式は「Keep a Changelog」に準拠しています。

## [Unreleased]

## [0.1.0] - 2026-03-29
### Added
- 初期リリース。以下の主要機能を追加。
- パッケージメタ情報
  - パッケージ名: kabusys、バージョン: 0.1.0。
  - パッケージの公開 API として data, strategy, execution, monitoring を __all__ に定義。

- 設定 / 環境変数管理（kabusys.config）
  - .env / .env.local をプロジェクトルート（.git または pyproject.toml を探索）から自動ロードする機能を実装（自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
  - .env ファイルのパース機能を実装（コメント、export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの扱いに対応）。
  - 環境変数必須チェック用の _require() と Settings クラスを提供。J-Quants / kabuAPI / Slack / DB パス等の設定プロパティを含む。
  - KABUSYS_ENV と LOG_LEVEL のバリデーション（許容値チェック）を実装。
  - デフォルトの DB パス（duckdb / sqlite）および API base URL の既定値を設定。

- AI 系モジュール（kabusys.ai）
  - ニュース NLP（kabusys.ai.news_nlp）
    - raw_news と news_symbols から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini）の JSON モードで一括センチメント評価を行い ai_scores テーブルへ書き込む処理を実装。
    - チャンク処理（デフォルト _BATCH_SIZE=20）と1銘柄あたりの文字数/記事数制限（トークン肥大対策）を実装。
    - API 呼び出しに対して 429 / ネットワーク断 / タイムアウト / 5xx を対象とした指数バックオフリトライ処理を実装。リトライ上限や待機時間を定義。
    - レスポンスの厳密なバリデーションとスコアの ±1.0 クリッピング。部分成功時の DB 書き換え保護（対象コードのみ DELETE → INSERT）をサポート。
    - テスト用に _call_openai_api を patch できる設計（ユニットテスト容易化）。
    - ニュース収集ウィンドウ計算（JST ベース → UTC naive datetime 変換）を提供（前日 15:00 JST 〜 当日 08:30 JST）。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（日経225 連動 ETF）の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull / neutral / bear）を判定。
    - マクロニュース抽出、OpenAI 呼び出し（gpt-4o-mini）、リトライ／フォールバック（API 失敗時 macro_sentiment=0.0）を実装。
    - レジーム合成ロジック、閾値（_BULL_THRESHOLD/_BEAR_THRESHOLD）および DuckDB への冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）を実装。
    - lookahead バイアス防止のため、datetime.today() 等を参照しない設計。

- Data / ETL（kabusys.data）
  - カレンダー管理（kabusys.data.calendar_management）
    - JPX カレンダーを管理する market_calendar テーブル周りのユーティリティ（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）を実装。
    - DB 登録がない日については曜日ベースのフォールバック（週末除外）。DB データが混在する場合でも一貫した判定が行える実装。
    - 夜間バッチ calendar_update_job を実装（J-Quants から差分取得→保存、バックフィル、健全性チェック）。
  - ETL パイプライン（kabusys.data.pipeline / kabusys.data.etl）
    - ETL 実行結果を表す ETLResult データクラスを提供（取得件数、保存件数、品質チェック結果、エラー一覧など）。
    - 差分更新、バックフィル、品質チェック（quality モジュール呼び出し）および id_token 注入によるテスト容易性を考慮した設計。
    - DuckDB 上のテーブル存在チェックや最大日付取得ユーティリティを提供。

- Research（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）
    - Momentum（1M/3M/6M リターン、200 日 MA 乖離）、Value（PER、ROE）、Volatility（20 日 ATR）、Liquidity（20 日平均売買代金、出来高比率）を DuckDB で計算する関数を実装（calc_momentum, calc_value, calc_volatility）。
    - 返却は (date, code) をキーとした辞書リスト。データ不足時の扱い（None）を明確に実装。
  - 特徴量探索（kabusys.research.feature_exploration）
    - 将来リターン計算（calc_forward_returns）: 指定ホライズン後のリターンを計算（複数ホライズンを1クエリで処理）。
    - IC（Information Coefficient）計算（calc_ic）: スピアマン順位相関によりファクター効果を評価。データが不足する場合は None を返す。
    - ランク関数（rank）: 同順位の平均ランク処理を含む実装。
    - 統計サマリー（factor_summary）: count/mean/std/min/max/median を計算。
  - 研究用ユーティリティとしてデータ統計の zscore_normalize を data.stats から再エクスポート。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- OpenAI API キーや各種シークレットは Settings 経由で必須チェックし、未設定時は ValueError を送出して明示的に失敗するように実装。
- .env 自動読み込みは明示的に無効化可能（KABUSYS_DISABLE_AUTO_ENV_LOAD）でテスト/CI 環境での誤読を防止。

### Notes / Design highlights
- ルックアヘッドバイアス対策: ニュース・レジーム・研究モジュールは内部で datetime.today()/date.today() を直接参照せず、呼び出し側から target_date を渡す設計。
- API 呼び出しの堅牢性: OpenAI 等外部 API の失敗は多くの箇所でフォールバック（0.0 やスキップ）して処理継続するようになっており、運用時の耐障害性を重視。
- DB 書き込みは冪等性を考慮（DELETE → INSERT、ON CONFLICT 設計に準拠する保存関数の想定）し、トランザクション（BEGIN/COMMIT/ROLLBACK）で整合性を確保。
- テスト容易性: OpenAI 呼び出しエントリポイント（_call_openai_api）を patch してモック化できるよう設計。

### Breaking Changes
- （初回リリースのため該当なし） 

---

今後のリリースでは、strategy / execution / monitoring モジュールの実装状況に応じて運用周り（実注入・ポジション管理・アラート）や監視機能の変更履歴を追記します。