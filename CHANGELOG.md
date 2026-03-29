# Changelog

すべての変更は Keep a Changelog のガイドラインに従って記載しています。  
フォーマット: https://keepachangelog.com/ja/

## [Unreleased]

（なし）

## [0.1.0] - 2026-03-29

初回公開リリース。本リポジトリは日本株のデータ取得・ETL、因子探索、ニュースAI解析、マーケットレジーム判定などを統合した研究／運用補助ライブラリです。主な追加点・設計方針は以下の通りです。

### Added
- パッケージ基本情報
  - パッケージ初期化: kabusys.__init__ にてバージョン "0.1.0" を定義し、主要サブパッケージを __all__ で公開（data, strategy, execution, monitoring）。

- 環境設定管理（kabusys.config）
  - .env ファイルの自動ロード機能を実装（プロジェクトルート判定: .git または pyproject.toml を探索）。
  - 読み込み順序: OS環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロード無効化可能。
  - .env の行解析を堅牢化:
    - コメント行と export プレフィックス対応。
    - シングル／ダブルクォート内のエスケープ処理をサポート。
    - クォートなし時のインラインコメント判定ルールを実装。
  - _require() による必須環境変数取得で未設定時に明確な ValueError を送出。
  - Settings クラスで各種設定をプロパティとして公開:
    - J-Quants / kabu / Slack / DB パスなどのキーを提供（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID）。
    - env / log_level の入力検証（許容値チェック）。
    - is_live / is_paper / is_dev の便宜プロパティ。

- AI ニュース解析（kabusys.ai.news_nlp）
  - raw_news + news_symbols を集約して銘柄別にニュースを結合し、OpenAI（gpt-4o-mini）へバッチ送信してセンチメント評価を取得する機能を実装。
  - 時間ウィンドウ: 前日15:00 JST ～ 当日08:30 JST を対象とする計算（UTC への変換を内部で行う calc_news_window を提供）。
  - バッチ処理とスコアリング:
    - 銘柄毎の最大記事数・最大文字数制限（_MAX_ARTICLES_PER_STOCK / _MAX_CHARS_PER_STOCK）。
    - 1 API コールあたり最大銘柄数 _BATCH_SIZE（デフォルト20）。
    - OpenAI JSON Mode を利用し、厳密な JSON レスポンスを期待（"results" 配列の形式）。
    - レスポンスのバリデーションとスコアクリップ（±1.0）。
  - エラー耐性設計:
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフでのリトライ。
    - API 呼び出しやパース失敗は個別チャンクをスキップして処理継続（フェイルセーフ）。最終的に取得できた銘柄のみ ai_scores に置換（DELETE → INSERT）して部分失敗時の既存データ保護。
  - テスト容易性: OpenAI 呼び出しを行う内部関数 _call_openai_api を差し替え可能（unittest.mock.patch を想定）。

- マクロレジーム判定（kabusys.ai.regime_detector）
  - ETF 1321（225連動）の200日移動平均乖離（重み70%）とマクロニュースのLLMセンチメント（重み30%）を合成して日次の市場レジーム（bull / neutral / bear）を判定する機能を追加。
  - 具体的処理:
    - prices_daily から ma200_ratio を計算（target_date 未満のデータを使用してルックアヘッドを防止）。
    - raw_news からマクロ関連キーワードでフィルタしたタイトルを抽出し、OpenAI（gpt-4o-mini）で macro_sentiment を算出。
    - スコア合成: clip(0.7*(ma200_ratio-1)*10 + 0.3*macro_sentiment, -1, 1) の方式を採用。閾値でラベル化。
    - DB への冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）を実装。
  - エラー耐性:
    - API 失敗やパース失敗時は macro_sentiment=0.0 として継続。
    - OpenAI クライアントは呼び出し時に api_key を受け取れるようにしている。

- データプラットフォーム（kabusys.data）
  - カレンダー管理（data.calendar_management）:
    - market_calendar テーブルを使った営業日判定ロジックを提供（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）。
    - DB 登録が無い場合は曜日ベース（土日休）でフォールバックする実装。
    - next/prev/get_trading_days は最大探索日数制限（_MAX_SEARCH_DAYS）を導入して無限ループ回避。
    - 夜間バッチ calendar_update_job を実装し、J-Quants API（jquants_client 経由）から差分取得して保存するロジック（バックフィル・健全性チェック含む）。
  - ETL パイプライン（data.pipeline / data.etl）:
    - ETLResult dataclass を定義し、ETL 実行結果（取得数・保存数・品質問題・エラー一覧）を構造化して返却。
    - 差分取得、バックフィル、品質チェック（quality モジュールを想定）を行う設計方針を明記。
    - DuckDB を用いた最大日付取得やテーブル存在チェック等のユーティリティを提供。
    - ETL は idempotent に保存することを目標とし、部分失敗時に既存データを保護する実装（書込前の個別 DELETE、empty executemany 回避）。

- Research（kabusys.research）
  - ファクター計算（research.factor_research）:
    - Momentum: 1M/3M/6M リターン、200日 MA 乖離（ma200_dev）を計算する calc_momentum。
    - Volatility & Liquidity: 20日 ATR、ATR比率、20日平均売買代金、出来高比率を計算する calc_volatility。
    - Value: raw_financials から直近の財務データを取得して PER / ROE を計算する calc_value。
    - いずれの関数も DuckDB の SQL ウィンドウ関数を活用して効率的に計算。データ不足時は None を返す仕様。
  - 特徴量探索（research.feature_exploration）:
    - 将来リターン計算 calc_forward_returns（任意ホライズンをサポート、引数 validation を実施）。
    - IC（Information Coefficient）計算 calc_ic（スピアマンのρ相当をランクで算出、データ不足時は None）。
    - ランキングユーティリティ rank（同順位は平均ランク、浮動小数の丸めで ties 対策）。
    - factor_summary による基本統計量集計（count/mean/std/min/max/median）。
  - すべての Research 関数は DB の prices_daily / raw_financials 等のみを参照し、実際の発注や外部サービスへはアクセスしない設計。

### Changed
- 設計・運用上の注意点（初版として明示）
  - ルックアヘッドバイアス対策: 日付の計算で datetime.today()/date.today() を直接参照しない設計。target_date を呼び出し元が明示的に渡す前提。
  - DuckDB に対する互換性考慮（executemany の空リスト回避、list バインドの回避など）を各所で対応。
  - OpenAI 呼び出しは各モジュールで独自にラップしており、モジュール間で内部関数を共有しないことで結合度を下げている（テスト時の差し替えを容易に）。

### Fixed
- 初期リリースにつき既知の「バグ修正」はなし。ただし以下の堅牢化を実施:
  - .env パーサーでのクォート内エスケープ処理とインラインコメントの曖昧さを解消。
  - OpenAI レスポンスパース失敗時に非致命的にフォールバックするロジックを全 AI 関連処理で統一。
  - DuckDB 書き込み時のトランザクション/ROLLBACK の失敗を WARN ログに記録する保護処理を追加。

### Security
- 外部への API キーは明示的に引数で渡すか環境変数 OPENAI_API_KEY 等を使用する設計（環境変数未設定時は ValueError を送出）。自動でキーを取得する等の暗黙的挙動は行わない。

### Internal / Developer
- テスト容易性:
  - OpenAI 呼び出し部分は内部関数をモック可能にしており、ユニットテストで外部通信を差し替えられる。
  - config モジュールは KABUSYS_DISABLE_AUTO_ENV_LOAD により自動 .env 読み込みを抑止できるため、テスト環境での環境制御が可能。
- ロギング:
  - 各モジュールで詳細な INFO/DEBUG/WARNING ログを出力するよう実装。失敗時は logger.exception / logger.warning による情報出力を行う。

---

以上がコードベースから推測して作成した初期リリース（0.1.0）の CHANGELOG です。必要であれば、リリースノートの記載粒度（より技術的な差分や API 使用例の追加など）を調整して更新します。