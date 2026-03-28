# Changelog

すべての重要な変更はこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠します。

## [Unreleased]

## [0.1.0] - 2026-03-28
初回リリース。日本株自動売買プラットフォームのコアライブラリを実装しました。主な追加点は以下の通りです。

### Added
- パッケージ基盤
  - パッケージのバージョンを設定（kabusys.__version__ = "0.1.0"）し、主要サブパッケージを公開（__all__: data, strategy, execution, monitoring）。
- 環境設定 / 設定管理（kabusys.config）
  - .env/.env.local からの自動ロード機能を実装（プロジェクトルート判定は .git または pyproject.toml を探索）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート。
  - .env パーサーを実装：export プレフィックス対応、シングル/ダブルクォートやエスケープ処理、インラインコメント処理等に対応。
  - 環境変数読み取り用 Settings クラスを提供。J-Quants / kabuステーション / Slack / DB パス / 環境（development/paper_trading/live）/ログレベル等のプロパティとバリデーションを実装。
  - 必須環境変数未設定時は ValueError を投げる _require ユーティリティを追加。
- AI 関連（kabusys.ai）
  - news_nlp モジュール（kabusys.ai.news_nlp）
    - raw_news / news_symbols を集約して銘柄ごとにニュースをまとめ、OpenAI（gpt-4o-mini）を用いたセンチメント評価を行う score_news を実装。
    - 前日15:00 JST〜当日08:30 JST の時間ウィンドウ計算（calc_news_window）。
    - バッチ処理（最大 20 銘柄/コール）、銘柄ごとのテキストトリム（記事数上限・文字数上限）。
    - JSON Mode を用いたレスポンス検証と復元ロジック（余分テキストが混ざる場合の {} 抽出）。
    - リトライ（429/ネットワーク/タイムアウト/5xx）と指数バックオフ、失敗時は該当チャンクをスキップして継続するフェイルセーフ設計。
    - API キー注入（api_key 引数または環境変数 OPENAI_API_KEY）。
    - テスト容易性のため _call_openai_api を差し替え可能に実装。
    - ai_scores テーブルへの冪等的書き込み（DELETE → INSERT、部分失敗時も既存スコア保護）。
  - regime_detector モジュール（kabusys.ai.regime_detector）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とニュース由来の LLM マクロセンチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定する score_regime を実装。
    - ma200_ratio 計算（ルックアヘッドを防ぐため target_date 未満のデータのみ使用、データ不足時は中立扱い）。
    - マクロ記事抽出（マクロキーワードリスト）、LLM による JSON 出力期待、レスポンスパース失敗や API エラーは macro_sentiment=0.0 にフォールバック。
    - OpenAI 呼び出しの冪等性と再試行ロジック、DB への冪等書き込み（BEGIN/DELETE/INSERT/COMMIT、失敗時は ROLLBACK）。
    - news_nlp と実装を分離しモジュール結合を避ける設計。
- Research（kabusys.research）
  - factor_research モジュール
    - モメンタム（1M/3M/6M リターン、200 日 MA 乖離）、ボラティリティ（20 日 ATR）、流動性（20 日平均売買代金・出来高比）、バリューファクター（PER/ROE）を計算する関数を実装（calc_momentum, calc_volatility, calc_value）。
    - DuckDB の SQL と窓関数を活用した実装。データ不足時は None を返す挙動。
  - feature_exploration モジュール
    - 将来リターン計算（calc_forward_returns、任意ホライズン対応）、IC（スピアマン順位相関）計算（calc_ic）、ランク化ユーティリティ（rank）、およびファクター統計サマリー（factor_summary）を実装。
    - pandas 等に依存せず標準ライブラリのみで実装。
  - パッケージ公開（kabusys.research.__init__）で主要関数を再エクスポート。
- Data プラットフォーム（kabusys.data）
  - calendar_management モジュール
    - market_calendar を用いた営業日判定（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）を実装。DB 登録値優先、未登録日は曜日ベースでフォールバック。
    - calendar_update_job による J-Quants からの差分取得と冪等保存、バックフィル・健全性チェックを実装。
  - ETL パイプライン（kabusys.data.pipeline）
    - 差分取得・保存・品質チェックフロー設計に基づく ETL 用ユーティリティを実装。
    - ETLResult データクラスを実装（取得数/保存数/品質問題/エラーなどを格納）。
  - etl モジュール（kabusys.data.etl）で ETLResult を再エクスポート。
  - jquants_client 経由での API 連携を想定する設計（fetch/save 関数を利用）。
- DuckDB を中心とした DB 環境を前提に全体設計。
- 多くのユーティリティにログ出力を追加（info/debug/warning/exception）。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- ルックアヘッドバイアス防止のため、すべてのスコア算出/ウィンドウ計算で datetime.today()/date.today() を直接参照しない設計を採用。
- 環境変数読み込み時に OS 環境変数を保護する protected セットを導入（.env.local による上書き制御含む）。

### Notes / Implementation details
- OpenAI モデルはデフォルトで "gpt-4o-mini" を使用。JSON Mode 応答を期待するプロンプト設計。
- API キーは関数引数で注入可能（テスト容易性、明示的なキー運用を想定）。
- テスト容易性のため、OpenAI 呼び出しを行う内部関数（_call_openai_api）をパッチで差し替え可能。
- DuckDB の executemany に関する互換性問題（空リスト不可など）に配慮した実装を行っている。
- 各モジュール内に設計方針や挙動を明記した docstring を多数含むため、挙動の追跡・テストが容易。

---

今後の予定（例）
- strategy / execution / monitoring の実装拡充（現在はパッケージ公開のみ）。
- 追加のファクター・リスク管理指標の導入。
- E2E テストと CI での OpenAI 呼び出しのモック整備。

README や API ドキュメントは別途追加予定。