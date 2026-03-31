# Keep a Changelog

すべての変更は https://keepachangelog.com/ja/ に準拠して記載します。

## [Unreleased]

- （なし）

## [0.1.0] - 2026-03-31

初回リリース。日本株自動売買システム「KabuSys」のコアライブラリを公開します。主要な機能群、設計方針、公開APIを下記にまとめます。

### Added

- パッケージ基礎
  - src/kabusys/__init__.py: バージョン（0.1.0）および公開サブパッケージの定義。

- 設定 / 環境変数管理
  - src/kabusys/config.py
    - .env ファイル（.env / .env.local）および OS 環境変数から設定を自動読込する仕組みを実装。
    - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能（テスト用）。
    - プロジェクトルート検出は __file__ から親ディレクトリを走査し、.git または pyproject.toml を基準に決定。
    - .env パーサは export プレフィックス、クォート／エスケープ、インラインコメント処理に対応。
    - Settings クラスを提供（J-Quants / kabuAPI / Slack / DB パス / 環境モード / ログレベル等）。
    - 必須設定は _require() で検査し未設定時に ValueError を送出。
    - KABUSYS_ENV・LOG_LEVEL は許容値チェックを実施。

- AI（自然言語処理）モジュール
  - src/kabusys/ai/news_nlp.py
    - raw_news / news_symbols からニュースを銘柄別に集約し、OpenAI（gpt-4o-mini）の JSON Mode を使って銘柄ごとのセンチメント（-1.0〜1.0）を算出。
    - タイムウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST（UTC 換算済み）を対象。
    - バッチ処理: 最大 _BATCH_SIZE=20 銘柄でまとめて API コール。
    - 1銘柄あたりの記事数・文字数上限（_MAX_ARTICLES_PER_STOCK / _MAX_CHARS_PER_STOCK）によるトリム実装。
    - 再試行（429 / ネットワーク断 / タイムアウト / 5xx）に対する指数バックオフを実装。
    - レスポンスのバリデーション（JSON 抽出、results の構造、コードの整合性、数値チェック）を行い、スコアを ±1.0 にクリップ。
    - DuckDB へは idempotent に DELETE → INSERT を行う（部分失敗時に他銘柄データを保護）。
    - API キーは引数 api_key で注入可能。未指定時は環境変数 OPENAI_API_KEY を参照。
    - テスト容易性: _call_openai_api を unittest.mock.patch で差し替え可能。
    - エントリポイント: score_news(conn, target_date, api_key=None)

  - src/kabusys/ai/regime_detector.py
    - ETF 1321（Nikkei 225 連動）の 200 日移動平均乖離（重み 70%）と、マクロ経済ニュースの LLM センチメント（重み 30%）を合成して市場レジーム（bull/neutral/bear）を日次判定。
    - マクロ記事抽出のためのキーワード群を定義（日本・米国・グローバル指標等）。
    - OpenAI（gpt-4o-mini）呼び出し（JSON Mode）で macro_sentiment を取得。API エラー時はフェイルセーフで 0.0 を採用。
    - レジーム合成スコアは clip(0.7*(ma200_ratio-1)*10 + 0.3*macro_sentiment, -1, 1)。
    - 結果は market_regime テーブルへ冪等（BEGIN / DELETE / INSERT / COMMIT）で保存。
    - API キーは引数 api_key で注入可能。未指定時は環境変数 OPENAI_API_KEY を参照。
    - エントリポイント: score_regime(conn, target_date, api_key=None)

- データプラットフォーム関連
  - src/kabusys/data/calendar_management.py
    - JPX カレンダー（market_calendar）を扱う夜間バッチ（calendar_update_job）と営業日判定ユーティリティを提供。
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を実装。
    - DB 登録値優先、未登録日は曜日ベースでフォールバック。最大探索日数を設定して無限ループを防止。
    - J-Quants クライアントを通した差分取得・保存（バックフィル、健全性チェック付き）。
  - src/kabusys/data/pipeline.py
    - ETL パイプラインのインターフェースおよび補助関数を実装。
    - ETLResult dataclass を導入（target_date / fetched/saved counts / quality_issues / errors 等を保持）。has_errors / has_quality_errors / to_dict を提供。
    - テーブル最終日取得やテーブル存在チェック等のユーティリティを実装。
    - 市場カレンダーやバックフィル等の ETL 設計方針を反映。
  - src/kabusys/data/etl.py
    - pipeline.ETLResult を再エクスポート。

  - src/kabusys/data/__init__.py
    - パッケージ初期化（クライアント等の公開は別モジュールで実装予定）。

- 研究（Research）モジュール
  - src/kabusys/research/factor_research.py
    - モメンタム（1M/3M/6M）、200日移動平均乖離、ATR などのファクター計算関数を実装（prices_daily / raw_financials を使用）。
    - calc_momentum, calc_volatility, calc_value を提供。結果は (date, code) をキーとする dict リストで返却。
    - 設計上、外部API呼び出しは行わず DuckDB 内で SQL + Python による計算を行う。
  - src/kabusys/research/feature_exploration.py
    - 将来リターン計算（calc_forward_returns）、IC（calc_ic）、ランク変換（rank）、ファクター統計サマリー（factor_summary）を実装。
    - pandas 等に依存せず標準ライブラリのみで実装。rank は同順位を平均ランクとする実装。

- テスト性 / 安全性 / 実運用配慮
  - ルックアヘッドバイアス防止: 各種処理で datetime.today()/date.today() を直接参照しない設計（target_date を明示的に渡す）。
  - DB 書き込みは冪等化（DELETE→INSERT、ON CONFLICT 方針）を心がけ、部分失敗時のデータ保護を実装。
  - OpenAI など外部 API 呼び出しはパッチ可能なポイントを用意しユニットテストを容易化。
  - リトライ・バックオフ戦略（指数バックオフ、最大リトライ回数）を導入し一時的な障害耐性を強化。
  - ログ出力（logger）を各モジュールに配置し、処理状況や警告を明示。

### Changed

- （初版のため該当なし）

### Fixed

- （初版のため該当なし）

### Security

- 外部 API キー（OpenAI 等）は環境変数による注入を想定。必須キー未設定時は明示的に ValueError を返すことで誤った実行を防止。

### Notes / 既知の設計上のポイント

- データベースは DuckDB を想定し、日付値は date オブジェクトで取り扱う。
- DuckDB の executemany の挙動（空リスト不可など）に配慮した実装が施されているため、互換性のために個別 DELETE→INSERT を使用する箇所がある。
- LLM へは gpt-4o-mini の JSON Mode を利用する想定で実装しているため、将来 SDK/モデル仕様変更があった場合は _call_openai_api の差し替えが必要になる可能性がある。
- config の .env 自動読込みはプロジェクトルート判定に依存するため、配布環境やテストで挙動をコントロールするには KABUSYS_DISABLE_AUTO_ENV_LOAD を利用してください。

## 開発者向けアップグレードガイド

- 0.1.0 は初期 API を公開するバージョンです。将来のリリースで public API（関数名、戻り値構造、DB スキーマ）を変更する可能性があるため、外部から呼び出す際は target_date を必ず明示して呼ぶことを推奨します。
- OpenAI 呼び出しをモックするには各モジュールの _call_openai_api をパッチしてください（unittest.mock.patch を想定）。

## 謝辞

- このリリースはデータ取得（J-Quants）、DuckDB を前提にした研究および AI 支援の自動売買支援基盤の初期実装です。今後フィードバックを元に改善していきます。

---