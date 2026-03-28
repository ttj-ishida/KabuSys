# Changelog

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠し、セマンティックバージョニングを使用します。

## [Unreleased]
（なし）

## [0.1.0] - 2026-03-28
初期リリース

### Added
- パッケージ基盤
  - パッケージ名: kabusys、バージョン 0.1.0 を導入。
  - パッケージ公開 API の初期エントリポイントを定義（src/kabusys/__init__.py）。デフォルトの __all__ に ["data", "strategy", "execution", "monitoring"] を設定。

- 設定 / 環境変数管理
  - settings クラスを提供し、環境変数から各種設定を取得可能に（src/kabusys/config.py）。
  - .env ファイルの自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml で検出）。
  - 読み込み順序: OS 環境 > .env.local（上書き） > .env（未設定時のみ）。自動ロード無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - .env のパーサを実装（コメント、export プレフィックス、クォート・エスケープ対応、行内コメント処理等）。
  - 必須環境変数チェックを実装:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
  - デフォルト値/検証:
    - KABUSYS_ENV: development / paper_trading / live の検証
    - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL の検証
    - DB パスのデフォルト（DUCKDB_PATH, SQLITE_PATH）

- AI（自然言語処理）モジュール
  - ニュースセンチメントスコアリング（news_nlp）
    - raw_news と news_symbols を集約して OpenAI（gpt-4o-mini）に送信し、銘柄ごとの ai_score を ai_scores テーブルへ書き込むワークフローを追加。
    - バッチ送信（デフォルト最大 20 銘柄/回）、1 銘柄あたり最大記事数・文字数制限（トークン爆発対策）。
    - レスポンス JSON の堅牢なバリデーションとスコアの ±1.0 クリッピング。
    - リトライ戦略: 429 / ネットワーク断 / タイムアウト / 5xx に対して指数バックオフでリトライ。その他のエラーはスキップしてフェイルセーフで継続。
    - タイムウィンドウ: 前日 15:00 JST 〜 当日 08:30 JST（UTC で前日 06:00 ～ 23:30）を対象にする calc_news_window 実装。
    - API キーは引数または環境変数 OPENAI_API_KEY を使用。未設定時は ValueError を送出。
  - 市場レジーム判定（regime_detector）
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を組み合わせ、日次で市場レジーム（bull / neutral / bear）を算出して market_regime テーブルへ書き込む。
    - マクロニュース抽出用にキーワードリストを持つフィルタ実装。
    - OpenAI 呼び出しの独立実装、API エラー時は macro_sentiment = 0.0 でフォールバック（フェイルセーフ）。
    - LLM 呼び出しに対するリトライ（最大 3 回）および 5xx 特別扱いを実装。
    - レジームスコア合成後、冪等な DB 書き込み（BEGIN / DELETE / INSERT / COMMIT）を行う。
    - ルックアヘッドバイアス防止のため、datetime.today() / date.today() を直接参照しない設計。prices_daily クエリも排他条件（date < target_date）を使用。

- データプラットフォーム（Data）
  - ETL パイプラインおよび結果型を提供（data.pipeline.ETLResult を data.etl で再エクスポート）。
  - calendar_management
    - JPX マーケットカレンダー管理（market_calendar テーブルの読み書き、営業日判定、next/prev/get_trading_days、is_sq_day）。
    - DB 登録が無い日については曜日ベースのフォールバック（土日非営業日扱い）。
    - calendar_update_job: J-Quants API から差分取得して冪等保存。バックフィル、健全性チェックを実装。
  - ETL パイプライン（data.pipeline）
    - 差分更新、バックフィル、品質チェック（quality モジュール連携）等の骨子を実装。
    - ETLResult dataclass による実行結果集約。品質問題やエラーの列挙をサポート。
    - DuckDB を用いた最大日付取得/テーブル存在チェック等のユーティリティを提供。

- リサーチ / ファクター計算（research）
  - factor_research: モメンタム / ボラティリティ / バリュー等のファクター計算関数を実装。
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離（データ不足時の None ハンドリング）。
    - calc_volatility: 20 日 ATR、相対 ATR、平均売買代金、出来高比率 等。
    - calc_value: PER（EPS が 0/欠損時は None）、ROE（raw_financials から最新値）。
    - すべて DuckDB の SQL + 最小限の Python ロジックで実装。外部 API を呼ばない安全設計。
  - feature_exploration: 将来リターン計算、IC（Spearman ρ）計算、統計サマリー、ランク付けユーティリティを実装。
    - calc_forward_returns: 任意ホライズンの将来リターンを一括で取得（horizons のバリデーションあり）。
    - calc_ic: factor と forward return を code によって結合し、スピアマンのランク相関を計算（有効レコード数が 3 未満の場合は None）。
    - factor_summary: count/mean/std/min/max/median を計算。
    - rank: 同順位は平均ランクで処理（浮動小数丸めによる ties 対応）。

- 基本設計思想（ドキュメント内注記）
  - ルックアヘッドバイアス防止のため日付取得を外部から受ける、または厳密な比較条件を使用。
  - API 失敗時はフェイルセーフ（例: macro_sentiment=0.0、スコア取得失敗はスキップ）で継続。
  - DB 書き込みは可能な限り冪等（DELETE → INSERT、ON CONFLICT 処理を想定）。
  - DuckDB の特性（executemany と空リストの扱い等）に配慮した実装。
  - OpenAI 呼び出しはテスト容易性のため内部で差し替え可能（ユニットテスト向けの patch ポイントを用意）。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Deprecated
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Security
- 外部 API キーと機密情報は環境変数経由で管理する設計。デフォルトで .env 自動読み込みを行うが、テスト時に KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能。

---

注: 本 CHANGELOG は現行ソースコードから推測して作成しています。将来の変更では API（関数シグネチャや環境変数名など）や内部実装が変わる可能性があります。