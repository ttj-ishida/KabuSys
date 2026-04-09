# Changelog

すべての重要な変更点をここに記録します。  
フォーマットは「Keep a Changelog」準拠です。

なお本CHANGELOGは、提供されたコードベースの内容から仕様・実装を推測して作成しています。

## [Unreleased]

## [0.1.0] - 2026-04-09

### Added
- 初回リリース: KabuSys — 日本株自動売買 / データ解析プラットフォームの基礎機能を実装。
- パッケージ公開情報
  - パッケージバージョンを `kabusys.__version__ = "0.1.0"` として追加。
  - パッケージトップで主要サブパッケージを公開: data, strategy, execution, monitoring（__all__）。

- 環境設定 / 設定管理（kabusys.config）
  - .env ファイルまたは環境変数から設定を自動読み込み（プロジェクトルートの .git または pyproject.toml を基準に探索）。
  - 自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
  - .env パーサ実装（export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメント処理に対応）。
  - 読み込み優先度: OS 環境変数 > .env.local > .env。OS 環境変数のキーは保護（上書き防止）。
  - Settings クラスを提供し、主要設定をプロパティとして公開:
    - J-Quants / kabuステーション / LINE / DB パス（duckdb, sqlite, paper_trading）等の設定取得。
    - PAPER_FILL_MODE の検証（"instant" | "partial" | "never" | "reject"）。
    - KABUSYS_ENV（development / paper_trading / live）および LOG_LEVEL の検証。
    - 監視用設定（PID ファイル、kill フラグ、CPU/メモリ/ディスクしきい値）など。

- AI（自然言語処理）モジュール（kabusys.ai）
  - news_nlp.score_news
    - raw_news / news_symbols から指定ウィンドウ（前日15:00 JST〜当日08:30 JST相当）の記事を集約し、銘柄ごとに OpenAI（gpt-4o-mini）の JSON モードでセンチメントを評価。
    - バッチ処理（最大 20 銘柄/回）、1 銘柄あたり記事数上限・文字数トリムによるトークン肥大対策。
    - API の 429/ネットワーク断/タイムアウト/5xx に対する指数バックオフリトライ。応答のバリデーションとスコアの ±1.0 クリップ。
    - 成功したスコアのみ ai_scores テーブルへ冪等的に置換（DELETE → INSERT）。部分失敗時に既存スコアを保護する設計。
    - テスト容易性: OpenAI 呼び出し部は patch 可能（_call_openai_api）。
    - スコア生成件数を返却。API キー未設定時は ValueError。

  - regime_detector.score_regime
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）と、マクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull / neutral / bear）を判定。
    - prices_daily から target_date 未満のデータのみ参照して look-ahead バイアスを回避。
    - raw_news からマクロキーワードで記事を抽出し、OpenAI（gpt-4o-mini）で macro_sentiment を取得（記事なし時は LLM 呼び出しをスキップして 0.0）。
    - API エラー時のリトライ/フォールバック（macro_sentiment=0.0）、および DB へ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）。API キー未設定時は ValueError。

  - ai パッケージは `score_news` を公開 API としてエクスポート。

- データプラットフォーム（kabusys.data）
  - カレンダー管理（calendar_management）
    - market_calendar テーブルを利用した営業日判定ロジックを提供:
      - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day
    - market_calendar がない場合は土日フォールバック（DB 登録がある場合は DB 値を優先）。
    - next/prev_trading_day は探索範囲制限（最大 _MAX_SEARCH_DAYS）で無限ループを防止。
    - calendar_update_job: J-Quants クライアント（jquants_client.fetch_market_calendar / save_market_calendar）を使って差分取得・バックフィル（直近 N 日再取得）・保存。健全性チェック（過度に将来日付がある場合はスキップ）。
  - ETL / パイプライン（pipeline, etl）
    - ETLResult データクラスを公開（etl モジュールから再エクスポート）。ETL 結果、品質問題、エラー一覧などを保持。
    - pipeline 設計方針: 差分更新、idempotent 保存（ON CONFLICT 互換）、品質チェックを行い、致命的エラーがあっても呼び出し元で判定できるように情報を返す。
    - J-Quants クライアントと品質検査モジュール（quality）を連携する設計。

- リサーチ / ファクター（kabusys.research）
  - factor_research:
    - calc_momentum: mom_1m / mom_3m / mom_6m と ma200_dev（200日 MA 乖離率）を計算。データ不足は None。
    - calc_volatility: 20日 ATR（atr_20）、相対ATR（atr_pct）、20日平均売買代金（avg_turnover）、出来高比（volume_ratio）を計算。
    - calc_value: raw_financials から最新財務を取得し PER / ROE を計算（EPS が 0/欠損時は None）。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一括取得。horizons の妥当性検証。
    - calc_ic: factor_records と forward_records を code で結合し、Spearman のランク相関（IC）を計算。十分なサンプルがない場合は None を返す。
    - factor_summary: 各ファクター列の count/mean/std/min/max/median を計算。
    - rank: 同順位に平均ランクを割り当てるランク計算（float の丸め対策）。
  - research パッケージは上記関数群と data.stats.zscore_normalize を公開。

- 共通実装・設計上の注意点
  - DuckDB を DB 層に使用（各モジュールは DuckDB の接続オブジェクトを受け取る）。
  - ルックアヘッドバイアス回避のため、各スコアリング/集計関数は明示的な target_date を受け取り、date.today()/datetime.today() を参照しない設計。
  - OpenAI 呼び出しはモデル "gpt-4o-mini" を想定し、JSON Mode（response_format）での応答パースを前提として実装。
  - API 呼び出しの堅牢化: RateLimit/接続/タイムアウト/5xx を考慮したリトライ（指数バックオフ）と、パース失敗時の安全なフォールバック（0.0 やスキップ）。
  - DB 書き込みは冪等性を意識して DELETE→INSERT、トランザクション（BEGIN/COMMIT/ROLLBACK）で実装。ROLLBACK 失敗時は警告ログを出す。
  - テスト容易性を考慮し、OpenAI 呼び出しを差し替え可能にしてある（unittest.mock.patch を想定）。
  - DuckDB バージョン依存の挙動に配慮（executemany に空リストを渡さない等の対処）。

### Fixed
- （初回リリースのため該当なし）

### Changed
- （初回リリースのため該当なし）

### Deprecated
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Security
- .env 自動読み込みはデフォルトで OS 環境変数を上書きしない（保護済みキー）。自動読み込みを無効化する手段を提供（KABUSYS_DISABLE_AUTO_ENV_LOAD）。
- OpenAI / 各種 API キーは明示的に設定が必要（未設定時は ValueError を送出して誤動作を防止）。

---

注意:
- 本CHANGELOGはコード上の実装とドキュメンテーション文字列に基づく推測を含みます。外部モジュール（例: data.jquants_client, quality 等）の実装は本コードセットに含まれていないため、動作はそれらの実装に依存します。
- 実際のリリース日やリリースノートの文言はリリース時の方針に合わせて調整してください。