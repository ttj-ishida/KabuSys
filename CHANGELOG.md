# Changelog

すべての注記は Keep a Changelog の形式に準拠しています。  
このファイルはリポジトリ内のコードから機能・振る舞いを推測して記載した初回リリースの変更履歴です。

なお、本リリースでは DuckDB を主要な永続化層として使用し、外部 API（J-Quants / OpenAI / kabuステーション 等）と連携する各種モジュールを実装しています。

## [Unreleased]

## [0.1.0] - 2026-04-03

### Added
- パッケージ基盤
  - 初期パッケージ `kabusys` を追加。__version__ = "0.1.0"。
  - サブパッケージ公開: data, research, ai, execution, strategy, monitoring（__all__ に登録）。

- 環境設定・ロード機能（kabusys.config）
  - .env/.env.local ファイルと OS 環境変数の統合読み込みを実装（自動ロード機能）。
  - プロジェクトルートの探索は __file__ を起点に .git または pyproject.toml を探すため、CWD に依存しない。
  - .env パーサを実装。以下をサポート／考慮:
    - 空行・コメント行（#）の無視
    - export KEY=val 形式対応
    - シングル／ダブルクォート、バックスラッシュエスケープ対応
    - クォートなしの場合はインラインコメントの取り扱い（直前がスペース/タブのみ）
  - .env 読み込み時のオーバーライド制御（.env と .env.local の優先度）と protected（既存 OS 環境変数保護）機能を実装。
  - 自動ロードの無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD を追加（テスト用など）。
  - Settings クラスを追加し、各種設定をプロパティ経由で取得:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等の必須チェック（未設定時は ValueError を送出）
    - KABU_API_BASE_URL, LINE_* トークン、データベースパス（DUCKDB_PATH / SQLITE_PATH）等の既定値
    - 監視関連のファイルパス／閾値（PID ファイル、kill flag、CPU/MEM/DISK 閾値）
    - 環境（KABUSYS_ENV）とログレベル（LOG_LEVEL）のバリデーション（許容値チェック）
    - 便宜的な bool 判定プロパティ（is_live / is_paper / is_dev）

- AI モジュール（kabusys.ai）
  - ニュース NLP（kabusys.ai.news_nlp）
    - raw_news と news_symbols を対象に、銘柄ごとに記事を集約して OpenAI（gpt-4o-mini）へ送信しセンチメントを算出。
    - タイムウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST（内部は UTC naive datetime で扱う）。
    - チャンク処理（最大 20 銘柄 / コール）、1 銘柄あたり最大 10 記事かつ 3000 文字でトリム。
    - JSON Mode を使用し、レスポンスの堅牢なバリデーションとスコア ±1.0 のクリップ実装。
    - RateLimit / ネットワーク / タイムアウト / 5xx サーバーエラーに対する指数バックオフ・リトライ。
    - 部分成功時の DB 書き換えは対象コードのみを DELETE → INSERT することで既存データの保護（冪等性）。
    - テスト容易性を考慮して OpenAI API 呼び出し部分（_call_openai_api）を差し替え可能に実装。
    - 公開関数: score_news(conn, target_date, api_key=None) — 書き込み銘柄数を返す。api_key 未指定時は環境変数 OPENAI_API_KEY を参照。未設定時は ValueError。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（日経225連動型）200日移動平均乖離（重み70%）とマクロニュースの LLM センチメント（重み30%）を合成して市場レジームを判定（'bull' / 'neutral' / 'bear'）。
    - ルックアヘッドバイアス対策: target_date 未満のデータのみ使用し、datetime.today() などの直接参照を避ける。
    - マクロニュース抽出は news_nlp.calc_news_window に準拠したウィンドウを使用し、マクロキーワードによるフィルタを実施。
    - OpenAI 呼び出しは gpt-4o-mini（JSON mode）を使用、リトライ・バックオフ・フェイルセーフ（API 失敗時は macro_sentiment=0.0）を実装。
    - 結果は market_regime テーブルへトランザクション（BEGIN/DELETE/INSERT/COMMIT）で冪等に保存。
    - 公開関数: score_regime(conn, target_date, api_key=None) — 成功時に 1 を返す。api_key 未指定時は環境変数 OPENAI_API_KEY を参照。未設定時は ValueError。

- データプラットフォーム（kabusys.data）
  - マーケットカレンダー管理（kabusys.data.calendar_management）
    - market_calendar テーブルの存在有無に基づく営業日判定（is_trading_day、is_sq_day、next_trading_day、prev_trading_day、get_trading_days）を実装。
    - DB 登録がない日については曜日ベース（平日）をフォールバックとして扱う（DB とフォールバックで一貫した判定を返す設計）。
    - calendar_update_job(conn, lookahead_days=90) を実装。J-Quants クライアント（jquants_client.fetch_market_calendar / save_market_calendar）を用いた差分取得と冪等保存、バックフィル、健全性チェックを実施。
  - ETL パイプライン（kabusys.data.pipeline / kabusys.data.etl）
    - ETLResult データクラスを定義し、ETL 実行結果（取得件数・保存件数・品質チェック結果・エラー）を一元化。
    - 差分取得・バックフィル・品質チェック（kabusys.data.quality へ委譲）の設計方針を実装。J-Quants クライアント経由での保存は冪等（ON CONFLICT DO UPDATE）を想定。
    - ETLResult.to_dict() で品質問題を辞書化して監査ログ等に利用可能。

- リサーチ・ファクター群（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）
    - Momentum（1M/3M/6M リターン、ma200_dev）、Volatility（20日 ATR、ATR 比率、20日平均売買代金、出来高比率）、Value（PER / ROE）を DuckDB の prices_daily / raw_financials を参照して計算する関数を実装。
    - 欠損データやデータ不足時の取り扱い（必要行数未満は None）を明示。
    - 結果は (date, code) を含む dict のリストで返却。
  - 特徴量探索（kabusys.research.feature_exploration）
    - 将来リターン計算: calc_forward_returns(conn, target_date, horizons=None)（デフォルト [1,5,21]）。
    - IC（Information Coefficient）計算: calc_ic(factor_records, forward_records, factor_col, return_col) — スピアマンのランク相関を実装。十分なサンプルがない場合は None。
    - ランキング変換ユーティリティ rank(values)（同順位は平均ランク）。
    - factor_summary(records, columns) による基本統計量（count/mean/std/min/max/median）計算。外部ライブラリに依存しない純 Python 実装。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- OpenAI API キーや各種シークレットは Settings 経由で管理し、必須変数が未設定の場合に早期にエラーとなる設計になっている。自動 env 読み込みはオプトアウト可能（KABUSYS_DISABLE_AUTO_ENV_LOAD）でテストや CI の明示的制御を想定。

### Notes / Known limitations
- DuckDB を前提としており、想定するテーブルスキーマ（prices_daily, raw_news, news_symbols, ai_scores, market_regime, market_calendar, raw_financials など）が存在することが前提です。スキーマの定義・マイグレーションは別途提供される想定です。
- OpenAI 呼び出しは gpt-4o-mini（JSON mode）で行うため、レスポンス仕様変更や API の挙動変化に依存します。テストは _call_openai_api を差し替えることにより実行可能です。
- 時刻ウィンドウ（ニュース収集等）は JST を基準に内部で UTC naive datetime を構築して DB と比較します。タイムゾーン混在に注意してください。
- ai モジュールは API エラー時にフェイルセーフでスコア 0.0 を用いるなど保守性を重視しているため、一部失敗は無視して継続する設計です（呼び出し元で結果を監視することを推奨）。

もし CHANGELOG に追加したい具体的なリリース日や著者、あるいはリリース範囲（例えば beta/alpha、互換性ポリシーなど）があれば教えてください。それに合わせて修正します。