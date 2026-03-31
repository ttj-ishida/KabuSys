# CHANGELOG

すべての公開変更は Keep a Changelog 準拠で記載しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

なお本 CHANGELOG はリポジトリ内のソースコード（src/kabusys 以下）から機能・設計意図・挙動を推測して作成しています。

## [Unreleased]

- ドキュメントやテストを追加予定
- マイナー改善（プロンプト調整・ログ出力改善など）
- OpenAI モデルやリトライ挙動のチューニング検討

## [0.1.0] - 2026-03-31

初回リリース。日本株自動売買システムのコアライブラリを追加しました。主な機能、設計方針、既知の挙動を以下にまとめます。

### Added
- パッケージ基盤
  - kabusys パッケージの初期実装を追加（__version__ = 0.1.0）。
  - パッケージ公開 API を __all__ で定義（data, strategy, execution, monitoring を想定）。

- 環境設定管理 (kabusys.config)
  - .env / .env.local の自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml で探索）。
  - .env パーサ実装:
    - export プレフィックス対応、クォート/エスケープの処理、インラインコメント処理等を考慮した堅牢なパーサ。
    - override／protected 機能で OS 環境変数の保護が可能。
  - Settings クラスを追加し、API トークンやDBパス、環境種類（development/paper_trading/live）、ログレベル等をプロパティ経由で取得。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化対応（テスト用）。

- AI 関連 (kabusys.ai)
  - ニュース NLP スコアリング (kabusys.ai.news_nlp)
    - raw_news と news_symbols を集約して銘柄ごとに OpenAI（gpt-4o-mini）でセンチメントを算出し ai_scores に書き込む。
    - バッチ処理（1 API 呼び出しあたり最大 20 銘柄）、1 銘柄あたり最大記事数・最大文字数制限によるトークン制御。
    - JSON Mode を用いた厳密な JSON 応答期待と、レスポンスの堅牢なバリデーション実装。
    - レート制限 / ネットワークエラー / タイムアウト / 5xx に対する指数バックオフリトライ。
    - API 呼び出し箇所はテスト用に差し替え可能（_call_openai_api を patch しやすい形で実装）。
    - DuckDB の executemany の仕様（空リスト不可）への対応を実装し、部分失敗時に既存スコアを保護するための差し替えロジック（DELETE → INSERT）。
    - ニュースウィンドウ（JST基準: 前日15:00 ～ 当日08:30）を計算する util を提供（calc_news_window）。
  - 市場レジーム判定 (kabusys.ai.regime_detector)
    - ETF 1321（日経225連動型）の 200 日移動平均乖離 (重み 70%) とマクロニュースの LLM センチメント (重み 30%) を合成して日次レジーム（bull/neutral/bear）を判定し market_regime テーブルへ冪等書き込み。
    - LLM 呼び出しは独立実装（news_nlp とは共有しない）でモジュール結合を抑制。
    - API エラー時は macro_sentiment = 0.0 とするフェイルセーフ。
    - リトライ戦略、JSON パース例外処理を備える。

- データプラットフォーム関連 (kabusys.data)
  - カレンダー管理 (kabusys.data.calendar_management)
    - JPX カレンダーの夜間差分取得ジョブ（calendar_update_job）実装。J-Quants クライアント経由で差分を取得し冪等保存。
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day 等の営業日判定ユーティリティを提供。
    - market_calendar 未取得時の曜日ベースフォールバックや、データ不整合（NULL）時のログ出力とフォールバックを実装。
    - 無限ループ回避用の最大探索日数制限を導入。
  - ETL パイプライン (kabusys.data.pipeline, kabusys.data.etl)
    - ETLResult データクラスで ETL 実行結果を集約（取得件数、保存件数、品質問題、エラー等）。
    - 差分更新、バックフィル、品質チェックの設計方針を実装（quality モジュールとの連携想定）。
    - jquants_client 経由での保存処理（idempotent 保存想定）を前提にした実装。
    - _get_max_date / _table_exists 等のユーティリティを追加。
  - jquants_client（参照箇所は存在、実際のクライアントは別モジュール想定）

- リサーチ・解析 (kabusys.research)
  - ファクター計算 (kabusys.research.factor_research)
    - Momentum: 1M/3M/6M リターン、ma200 乖離の算出（営業日ベースのラグを利用）。
    - Volatility / Liquidity: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率等の算出。
    - Value: raw_financials から EPS/ROE を取得し PER/ROE を算出（PBR・配当利回りは未実装）。
    - DuckDB を利用した SQL 主導の実装。
  - 特徴量探索 (kabusys.research.feature_exploration)
    - 将来リターン calc_forward_returns（任意ホライズン、最大 252 営業日の検証あり）。
    - IC（Spearman のランク相関）計算 calc_ic、rank ユーティリティ、factor_summary（count/mean/std/min/max/median）を実装。
    - pandas 等に依存せず標準ライブラリと DuckDB で実装。

### Changed
- N/A（初回リリース）

### Fixed
- N/A（初回リリース）

### Deprecated
- N/A（初回リリース）

### Removed
- N/A（初回リリース）

### Security
- 環境変数による機密情報管理:
  - OpenAI API キー (OPENAI_API_KEY)、J-Quants / kabu API トークン等は環境変数から取得する設計。Settings クラスは必須キー未設定時に ValueError を投げる。
  - .env/.env.local 自動ロード時に OS 環境変数を protected として上書きを防ぐための保護機構を実装。

### Notes / Known limitations
- Look-ahead バイアス対策:
  - 多くのモジュールで datetime.today() / date.today() を直接参照しない方針を採用（外部から target_date を注入する設計）。
- OpenAI 関連:
  - gpt-4o-mini を想定して JSON Mode（response_format={"type": "json_object"}）を利用する実装。実運用では API 応答のばらつきに注意が必要。
  - レスポンスパースや LLM の出力不正（余計な前後テキスト等）に対する復元ロジックを備えるが、完全な堅牢性は保証しない。
- データ前提:
  - raw_news.datetime は UTC で保存されている前提（news ウィンドウは UTC naive datetime を使用）。
  - DuckDB バージョン依存の挙動（executemany の空リスト処理等）を考慮したワークアラウンドを含む。
- 未実装 / TODO:
  - ファクター: PBR、配当利回り等は未実装。
  - 外部クライアント（jquants_client）の具体実装や quality モジュールの詳細は別実装を想定。
  - tests / CI / ドキュメントの追加（Unreleased に計画）。

---

著者注: この CHANGELOG はソースコードの静的解析から推測して作成しています。実際のリリースノートはバージョン管理履歴（コミットログ）やリリースノート作成方針に基づいて調整してください。必要であれば、特定モジュールごとの詳細な変更点（関数シグネチャ、戻り値の仕様、例外挙動など）をさらに展開して記載します。