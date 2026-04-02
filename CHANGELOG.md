# Changelog

すべての注目すべき変更点を記録します。フォーマットは「Keep a Changelog」準拠です。

- リリースポリシー: 互換性のある変更は MAJOR.MINOR.PATCH に基づいて管理します。
- 日付はリリース日を示します（このファイルはコードベースの内容から推測して作成しています）。
- 以降の記載はコードの docstring / 実装から推測した機能・設計意図をまとめたものです。

## [Unreleased]

## [0.1.0] - 2026-04-02

### Added
- パッケージ基盤
  - kabusys パッケージの初期公開（__version__ = 0.1.0）。主要サブパッケージとして data, research, ai, monitoring, execution, strategy を想定するエクスポートを準備。
- 環境設定管理 (kabusys.config)
  - .env ファイルと環境変数を優先順に読み込む自動ローダーを実装。
    - 読み込み順: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能（テスト向け）。
    - プロジェクトルートは .git または pyproject.toml を基準に探索（CWD 非依存）。
    - .env パーサは export プレフィックス、クォート中のエスケープ、インラインコメントの扱いに対応。
    - 読み込み失敗時は警告を出力してフォールバック。
  - Settings クラスを提供し、アプリケーションで使用する主要な環境変数をプロパティとして公開。
    - J-Quants / kabu API / Slack / DB パス / 監視閾値 / システム環境 (KABUSYS_ENV, LOG_LEVEL) 等を取得。
    - 必須変数未設定時は ValueError を送出する厳格な require ロジックを持つ。
    - 環境値のバリデーション（KABUSYS_ENV, LOG_LEVEL の許容値チェック）を実装。
- AI モジュール (kabusys.ai)
  - ニュースセンチメントスコアリング (kabusys.ai.news_nlp)
    - raw_news と news_symbols を集約し、銘柄ごとにニューステキストを結合して OpenAI（gpt-4o-mini）へバッチ送信し ai_scores テーブルへ書き込む機能を実装。
    - タイムウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST（UTC 変換された半開区間）を対象にする calc_news_window を提供。
    - バッチサイズ、1銘柄あたり最大記事数／文字数の制限を実装しトークン肥大化を防止。
    - JSON Mode を利用した厳格なレスポンス検証とスコア ±1.0 でのクリッピングを実装。
    - 429 / ネットワーク断 / タイムアウト / サーバー5xx に対する指数バックオフリトライを実装。
    - API 呼び出し部分はテスト容易性のため差し替えポイント（_call_openai_api）を用意。
    - DuckDB の executemany 空リスト制約に対応し、部分失敗時に既存スコアを保護する idempotent な DELETE→INSERT ロジックを採用。
  - 市場レジーム判定 (kabusys.ai.regime_detector)
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）と、ニュース由来の LLM マクロセンチメント（重み 30%）を合成して日次で市場レジーム（bull / neutral / bear）を判定し market_regime テーブルへ書き込む機能を実装。
    - prices_daily からの ma200_ratio 計算はルックアヘッドを防ぐため target_date 未満のデータのみを使用。
    - マクロニュースは raw_news からキーワードフィルタで抽出（最大件数制限あり）。
    - OpenAI 呼び出しは独立実装（news_nlp と内部関数を共有しない）で、API エラー時は macro_sentiment=0.0 にフォールバックするフェイルセーフを実装。
    - 書き込みはトランザクション（BEGIN / DELETE / INSERT / COMMIT）で冪等性を確保。失敗時は ROLLBACK を試行して例外を上位に伝播。
    - リトライや 5xx の扱い、JSON パースの例外処理など堅牢な実装。
- Research モジュール (kabusys.research)
  - factor_research モジュール:
    - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev（200日 MA 乖離率）を prices_daily から計算。
    - calc_volatility: 20日 ATR（平均 true range）／atr_pct／avg_turnover／volume_ratio を計算。
    - calc_value: raw_financials から最新財務を取得し PER, ROE を計算（EPS が 0/欠損時は None）。
    - 実装は DuckDB のウィンドウ関数・SQL を活用し、外部 API へ依存しない。
  - feature_exploration モジュール:
    - calc_forward_returns: 指定のホライズン（デフォルト [1,5,21] 営業日）に対する将来リターンを計算。
    - calc_ic: スピアマンのランク相関（IC）を計算するユーティリティを実装（必要レコード数チェックあり）。
    - rank / factor_summary: ランク化と統計サマリー（count/mean/std/min/max/median）を提供。
    - 実装は標準ライブラリ + DuckDB のみで依存軽量。
- Data モジュール (kabusys.data)
  - calendar_management:
    - JPX マーケットカレンダー管理：is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を実装。
    - market_calendar が未登録の場合は曜日ベース（土日非営業）でフォールバックする一貫したロジックを提供。
    - calendar_update_job で J-Quants（jquants_client 経由）から差分取得して market_calendar を冪等更新。バックフィル・健全性チェックを備える。
  - pipeline / ETL:
    - ETLResult dataclass を定義し、ETL 実行結果（取得件数・保存件数・品質問題・エラー）を表現。
    - pipeline モジュールは差分更新、保存（jquants_client の save_* を利用して idempotent 保存）、品質チェックを想定したインターフェースを実装（コード中の設計方針に準拠）。
    - kabusys.data.etl で ETLResult を再エクスポート。
  - DuckDB 互換性のための実装上の注意点（executemany の空リスト回避など）を反映。
- ロギング/設計方針
  - ほとんどの処理でルックアヘッドバイアスを防ぐため datetime.today() / date.today() を直接参照しない設計（target_date を引数に受ける）。
  - DB 書き込みは可能な限り冪等性・トランザクションで保護し、失敗時に ROLLBACK を試行。
  - OpenAI 呼び出し周りはリトライ戦略（指数バックオフ）、5xx とそれ以外の扱いを区別した堅牢なエラーハンドリングを実装。
  - テスト容易性のため、API 呼び出し部分に差し替えポイント（モック可能）を用意。

### Changed
- 初期リリースのため該当なし。

### Fixed
- 初期リリースのため該当なし。

### Security
- 環境変数を必要とする API キー類（OPENAI_API_KEY 等）は Settings で必須チェックを行い、未設定時に例外を投げることで誤動作を防止。
- .env 自動ロードは OS 環境変数を保護する仕組み（protected set）を備える。

## Notes / Known limitations
- 外部依存:
  - OpenAI: OpenAI SDK（client.chat.completions.create を利用）を想定。実行には OPENAI_API_KEY が必要。
  - J-Quants: jquants_client の存在を前提としており、実際の API クライアントは別モジュール（kabusys.data.jquants_client）で提供される想定。
  - DuckDB を利用した DB スキーマが前提（prices_daily / raw_news / news_symbols / ai_scores / market_calendar / raw_financials / market_regime 等のテーブル）。
- 実装上、LLM の応答パース失敗や API エラー時は「スコアを 0.0 にフォールバック」や「該当チャンクをスキップ」するなどフェイルセーフを優先する設計のため、外部 API の安定性に依存するワークフローでは部分的にスコア欠損が発生する可能性があります。
- 一部 DuckDB バージョンに依存するバインド挙動回避のため、実装で若干の冗長性（個別 DELETE の executemany 等）を採用しています。

---

（以降のバージョンでは機能追加・バグ修正をカテゴリ分けして追記してください。）