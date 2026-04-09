# Changelog

すべての重要な変更は Keep a Changelog の慣例に従って記載しています。  
この CHANGELOG はソースコードから推測して作成したもので、実装の主要機能・設計上の注意点・公開 API を中心にまとめています。

フォーマット: https://keepachangelog.com/ja/1.0.0/

現在のバージョン: 0.1.0

## [Unreleased]

（今後の変更をここに記載してください）

---

## [0.1.0] - 2026-04-09

初回リリース。日本株自動売買システムのコア機能群を実装・公開。

### Added
- パッケージ基盤
  - kabusys パッケージ初期実装を追加。
  - バージョン情報: `__version__ = "0.1.0"`。
  - パッケージ公開 API：data, strategy, execution, monitoring（monitoring は __all__ に含まれるが本稿では実装未確認）。

- 設定管理（kabusys.config）
  - .env ファイルまたは環境変数から設定を読み込む自動ロード機構を実装。
  - プロジェクトルート検出ロジック（.git / pyproject.toml を親ディレクトリから探索）を実装し、CWD に依存しない読み込みを実現。
  - .env パーサを実装（export 構文、シングル/ダブルクォート、バックスラッシュエスケープ、行内コメントの扱いに対応）。
  - 自動ロードの優先順位：OS 環境変数 > .env.local > .env。
  - 自動ロードの無効化フラグ `KABUSYS_DISABLE_AUTO_ENV_LOAD` をサポート。
  - Settings クラスを実装し、アプリケーション設定をプロパティ経由で取得可能に：
    - J-Quants / kabuステーション / LINE / DB パス等の設定（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH 等）。
    - PID・kill flag・リソース閾値（CPU/メモリ/ディスク）などの監視設定。
    - PAPER_FILL_MODE の検証（"instant" | "partial" | "never" | "reject"）。
    - KABUSYS_ENV（development / paper_trading / live）と LOG_LEVEL の検証。
    - is_live / is_paper / is_dev の便利プロパティ。

- AI（kabusys.ai）
  - ニュース NLP（kabusys.ai.news_nlp）
    - raw_news と news_symbols を集約し、銘柄ごとに OpenAI（gpt-4o-mini）でセンチメントを評価する `score_news(conn, target_date, api_key=None)` を実装。
    - 評価対象ウィンドウ（JST 前日 15:00 〜 当日 08:30）を UTC 変換して扱う `calc_news_window` を提供。
    - バッチ処理（最大 20 銘柄 / チャンク）、1銘柄あたり記事数上限（10 件）および文字数上限（3000 文字）でトリムする実装。
    - OpenAI 呼び出しはリトライ（429/ネットワーク/タイムアウト/5xx に対する指数バックオフ）およびレスポンス検証（JSON パース、想定キー・型、スコア数値化、±1.0 でクリップ）を行う。
    - 書き込みは冪等化（対象 code を絞って DELETE → INSERT）して部分失敗時の既存データ保護を行う。
    - テスト容易性のため OpenAI 呼び出し部分をパッチ可能に（内部 `_call_openai_api` を差し替え可）。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次レジーム（bull/neutral/bear）を判定する `score_regime(conn, target_date, api_key=None)` を実装。
    - ma200 計算ではルックアヘッドを防ぐため target_date 未満のデータのみ使用し、データ不足時は中立（1.0）を採用するフェイルセーフ。
    - マクロニュース抽出（キーワードベース、最大 20 記事）→ OpenAI によるセンチメント評価（JSON 応答期待）→ リトライ & フェイルセーフ（API 失敗時は macro_sentiment=0.0）。
    - 結果を market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）する実装。
    - OpenAI SDK の例外種別（RateLimitError, APIConnectionError, APITimeoutError, APIError）に応じた扱いを実装。

- データプラットフォーム（kabusys.data）
  - カレンダー管理（kabusys.data.calendar_management）
    - JPX カレンダー管理ロジックを実装：is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day を提供。
    - market_calendar が未取得の場合は曜日ベースでフォールバック（土日を非営業日と扱う）。
    - calendar_update_job を実装し、J-Quants クライアントからカレンダーを差分取得して market_calendar に保存（バックフィル・健全性チェック内蔵）。
    - 探索上限（最大探索日数）やバックフィル日数などの安全ガードを導入。
  - ETL パイプライン（kabusys.data.pipeline / etl）
    - ETL の概念設計に基づく差分取得・保存・品質チェックの仕組みを整理。
    - ETLResult dataclass を実装（target_date、取得・保存件数、品質問題リスト、エラーリスト等を含む）。
    - `kabusys.data.etl` で ETLResult を公開再エクスポート。
    - デフォルトのバックフィル日数、最小開始日などの定数を定義。
    - 品質チェックを外部 quality モジュールと連携し、重大度フラグを扱う設計。

- リサーチ（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）
    - モメンタム（1M/3M/6M リターン、MA200 乖離）、ボラティリティ（20日 ATR）、流動性（20日平均売買代金・出来高比率）、バリュー（PER/ROE）を計算する関数を実装：
      - calc_momentum(conn, target_date)
      - calc_volatility(conn, target_date)
      - calc_value(conn, target_date)
    - DuckDB の SQL ウィンドウ関数を活用して効率的に集約。
    - データ不足時は None を返す等の堅牢な挙動。
  - 特徴量探索・統計（kabusys.research.feature_exploration）
    - 将来リターン計算（calc_forward_returns）、IC（Spearman ランク相関）計算（calc_ic）、ランク変換（rank）、ファクター統計サマリー（factor_summary）を実装。
    - Pandas 等の外部依存を持たず標準ライブラリ + DuckDB で実装。
  - research パッケージの公開 API を整備（主要関数を __all__ でエクスポート）。

### Changed
- N/A（初回リリースにつき該当なし。ただし実装上の設計判断・安全機構を多数盛り込んでいる点を記載）

### Fixed
- N/A（初回リリース）

### Security
- OpenAI API キーは関数引数で注入可能（api_key）か環境変数 OPENAI_API_KEY を参照。
- 環境変数ロード時に OS 環境変数を保護する仕組み（.env 読み込み時に protected set を使用）を実装。

### Notes / Implementation details（補足）
- すべての時刻/日付処理で「ルックアヘッドバイアス防止」を設計方針として採用。関数は内部で datetime.today()/date.today() を参照しない（外部から target_date を受け取る）。
- DuckDB を主要なデータストアとして想定（DuckDB 接続を引数に受け取る関数が多数）。
- OpenAI とのやり取りは gpt-4o-mini を推奨し、JSON Mode（response_format）を利用して厳密な JSON 応答を期待する実装。
- API 呼び出しには堅牢なリトライとフェイルセーフ（失敗時にスコアを 0.0 にフォールバック、例外を上位に投げない等）を導入。
- DB 書き込みは可能な限り冪等化（DELETE → INSERT、ON CONFLICT 想定）している。
- テスト容易性の配慮：内部 API 呼び出し部分をモック可能にしている（例: _call_openai_api の差し替え）。

---

配布後や運用時に追加・修正があれば Unreleased セクションに記載してください。必要であれば各関数の公開 API 仕様や使用例（例: score_news / score_regime / calc_momentum の使い方）を CHANGELOG に追記することも可能です。