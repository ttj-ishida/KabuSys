# Changelog

すべての変更は "Keep a Changelog" 準拠で記載しています。  
既存バージョンはセマンティックバージョニングに従います。

## [0.1.0] - 2026-03-29

初回リリース。日本株自動売買プラットフォームのコアライブラリを実装しました。主な追加点は以下の通りです。

### Added
- パッケージ基盤
  - パッケージルート (kabusys) とバージョン番号を導入（__version__ = "0.1.0"）。
  - メインサブパッケージのエクスポートを定義（data, strategy, execution, monitoring）。

- 設定管理（kabusys.config）
  - .env ファイルまたは環境変数から設定値を読み込む自動ローダーを実装。
    - プロジェクトルート検出は __file__ を起点に .git または pyproject.toml を探索（CWD 非依存）。
    - 読み込み優先度: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能。
  - .env パーサを独自実装（コメント、export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ対応）。
  - 保護された OS 環境変数（protected set）を上書きから保護する仕組みを導入。
  - Settings クラスを提供し、J-Quants / kabu API / Slack / DB パス / 環境種別 / ログレベル等のプロパティで安全にアクセス可能。
    - 環境値検証（KABUSYS_ENV, LOG_LEVEL の許容値チェック）。
    - duckdb/sqlite パスは Path 型で取得。

- AI ニュース解析（kabusys.ai.news_nlp）
  - raw_news と news_symbols を入力に銘柄ごとのニュースセンチメントを算出し ai_scores テーブルへ書き込むスコアリングパイプラインを実装。
  - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）計算ユーティリティを提供（calc_news_window）。
  - OpenAI（gpt-4o-mini）を用いたバッチスコアリング:
    - 1 API コールあたり最大 20 銘柄のチャンク処理。
    - 1 銘柄あたり最新 N 件・最大文字数でトリム（トークン肥大対策）。
    - JSON Mode を用いた厳密なレスポンス期待と、レスポンスの堅牢なバリデーション（JSON 抽出・型検証・未知コード無視・スコアの数値/有限性チェック）。
  - ネットワーク障害/429/タイムアウト/5xx に対する指数バックオフリトライ。
  - フェイルセーフ設計: API 失敗時は該当チャンクをスキップして他銘柄の処理を継続。部分成功時は該当コードのみを DELETE→INSERT で置換して既存スコアを保護。
  - テスト容易性のために OpenAI 呼び出しを差し替え可能に実装（内部 _call_openai_api を patch 可能）。

- AI 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF 1321（日経225連動）の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定する機能を実装。
  - prices_daily / raw_news から必要データを取得し、計算結果を market_regime テーブルへ冪等（BEGIN / DELETE / INSERT / COMMIT）で保存。
  - OpenAI 呼び出しは gpt-4o-mini と JSON Mode を使用。API エラー時は macro_sentiment=0.0 でフォールバック。
  - レジーム合成ロジック、閾値、リトライ戦略を実装。
  - ルックアヘッドバイアス対策（date 比較で排他条件使用、datetime.today() 不使用）。

- データ/カレンダー（kabusys.data.calendar_management）
  - market_calendar を元に営業日判定ロジックを提供:
    - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day。
  - DB にカレンダーがない場合は曜日ベース（土日休）でフォールバック。
  - next/prev_trading_day は最大探索日数制限 (_MAX_SEARCH_DAYS) を設け ValueError を投げる安全策。
  - JPX カレンダー差分取得と market_calendar 更新を行う夜間バッチジョブ calendar_update_job を実装（J-Quants クライアントを利用）。
  - バックフィル・健全性チェック（未来日が異常に遠い場合スキップ）等の運用考慮。

- ETL パイプライン（kabusys.data.pipeline / etl）
  - ETLResult dataclass を導入（取得件数、保存件数、品質チェック結果、エラー一覧等を保持）。
  - 差分更新／バックフィル方針の設計（最小データ日、カレンダー先読み、デフォルトバックフィル日数等）。
  - DB 存在チェック・最大日付取得ユーティリティを実装。
  - エラー／品質チェックの扱い方針（Fail-Fast ではなく全件収集して呼び出し元に委ねる設計）。
  - etl モジュールで ETLResult を再エクスポート。

- リサーチ機能（kabusys.research）
  - ファクター計算（factor_research）:
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）を計算。
    - calc_volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials から EPS/ROE を取得して PER/ROE を計算（EPS が 0/NULL の場合は None）。
    - DuckDB を用いたウィンドウ関数ベースの実装（営業日ベースの窓・データ不足時は None）。
  - 特徴量探索（feature_exploration）:
    - calc_forward_returns: 指定ホライズン先の将来リターン（LEAD を利用）を計算。horizons の検証あり。
    - calc_ic: スピアマンランク相関（Information Coefficient）を計算。少数データや分散ゼロの扱いは保護。
    - rank: 同順位は平均ランクにするランク化ユーティリティ（丸めによる ties 対策あり）。
    - factor_summary: 各カラムの count/mean/std/min/max/median を標準ライブラリのみで計算。
  - research パッケージの __all__ を通じて主要関数を公開。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- 環境変数ロード時に OS 環境（既存の os.environ）を保護する仕組みを導入。.env による上書きは保護されたキーを除外。
- OpenAI API キー未設定時は明示的に ValueError を発生させ、誤った無言失敗を防止。

### Notes / Limitations
- OpenAI API（gpt-4o-mini）を利用する機能は API キー（OPENAI_API_KEY）が必要です。api_key 引数からの注入も可能。
- J-Quants 関連クライアント（jquants_client）や kabu ステーション API クライアントは参照されますが、本リリースではクライアント実装の詳細は別モジュール/パッケージに依存します。
- DuckDB のバージョン依存（executemany の空配列扱い等）に関する互換性対策を含めています。
- 本ライブラリはルックアヘッドバイアス回避の設計原則に基づき実装されています（date 比較やウィンドウ境界の排他扱い等）。
- 単体テスト用に OpenAI 呼び出しをモックできるよう内部関数を公開している箇所があります。

---

今後のリリースでは、strategy / execution / monitoring の具体的な注文発注フロー、Webhook や Slack 連携、より詳細な品質チェックルールの追加、及び外部クライアントの統合実装を予定しています。