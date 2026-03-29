# Changelog

すべての変更は「Keep a Changelog」慣習に準拠して記載しています。  
フォーマット: https://keepachangelog.com/ja/ に準拠しています。

注: このCHANGELOGはコードベースの実装内容から推測して作成しています。実際のリリース履歴や日付は推定です。

## [Unreleased]

### Added
- パッケージ初期構成の公開 API を追加
  - kabusys パッケージのトップレベルでの __version__ (0.1.0 相当) と __all__ を定義。
  - サブパッケージ: data, research, ai, monitoring, execution, strategy（実装済み・公開予定のモジュールを想定）。

- 環境変数/設定管理 (kabusys.config)
  - .env ファイルの自動読み込み機能を実装（プロジェクトルートを .git / pyproject.toml で検出）。
  - 読み込み順序: OS 環境変数 > .env.local > .env。.env.local は上書き（override）を許可。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化サポート（テスト用途）。
  - .env パーサの強化:
    - export KEY=val 形式をサポート。
    - シングル/ダブルクォートとバックスラッシュエスケープ対応。
    - クォートなし値のインラインコメント処理（直前がスペース/タブの場合のみ）。
  - 環境変数未設定時に例外を投げる _require() と、各種必須設定（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、SLACK_BOT_TOKEN、SLACK_CHANNEL_ID など）のプロパティを追加。
  - 設定の検証: KABUSYS_ENV の有効値チェック（development / paper_trading / live）、LOG_LEVEL の有効値チェック。
  - デフォルト DB パス（duckdb / sqlite）の設定プロパティを提供。

- AI（自然言語処理）モジュール (kabusys.ai)
  - ニュースセンチメントスコアリング (news_nlp.score_news)
    - 指定ターゲット日の「前日15:00 JST ～ 当日08:30 JST」ウィンドウに基づく記事集約ロジックを実装（UTC 変換を内部で処理）。
    - 銘柄ごとに最新記事を集約してトリム（最大記事数、最大文字数制限）。
    - OpenAI（gpt-4o-mini）へのバッチ送信（1コールあたり最大20銘柄）と JSON Mode 応答パース。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフリトライとフェイルセーフ（失敗時はスキップして継続）。
    - レスポンスバリデーション（results フィールド・型・スコア数値性・既知コードのみ採用）、±1.0 にクリップして ai_scores テーブルへ冪等的に書き込み。
    - テスト容易性のため OpenAI 呼び出し箇所をモジュール内でラップしてモック差替え可能に実装。
    - 処理中のログ出力（対象記事数、チャンク数、書込み結果等）。

  - 市場レジーム判定 (regime_detector.score_regime)
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（ma200_ratio）と、マクロ経済ニュースの LLM センチメントを合成して日次の市場レジーム（bull/neutral/bear）を判定。
    - マクロニュース抽出はキーワードベース（デフォルト複数キーワードを定義）で記事タイトルを取得。
    - LLM（gpt-4o-mini）呼び出しは専用ラッパーで実行、API エラー時はマクロスコアを 0.0 とするフォールバック実装。
    - レジームスコア合成ルール（MA 重み 70%、マクロ重み 30%、スケーリング、閾値判定）を実装。
    - market_regime テーブルへの冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）を実装。
    - ルックアヘッドバイアス防止: datetime.today() を参照しない、DB クエリにおいて target_date 未満のデータのみを使用。

### Changed
- DuckDB を中心としたデータ参照設計を採用
  - 各種リサーチ・ETL・データ管理関数は DuckDB 接続を受け取り SQL を利用して処理。
  - 外部の実トレード発注やネットワーク呼び出し（kabu ステーション等）は直接行わない設計を明確化（安全性・テスト容易性のため）。

- Research（kabusys.research）
  - ファクター計算群を追加:
    - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離を算出（データ不足時は None）  
    - calc_volatility: 20日 ATR、相対ATR、20日平均売買代金、出来高比率を算出（データ不足時は None）  
    - calc_value: raw_financials から最新財務を取得して PER / ROE を算出（EPS 0/欠損時は None）
  - 特徴量探索ツール:
    - calc_forward_returns: 指定ホライズンの将来リターンを一括で取得（horizons 引数の妥当性チェックあり）
    - calc_ic: Spearman（ランク相関）による IC 計算（結合・欠損排除・最小有効サンプルチェック）
    - rank: 同順位は平均ランクにするランク化関数（浮動小数点の丸め対策あり）
    - factor_summary: 各カラムの count/mean/std/min/max/median を計算するユーティリティ
  - いずれも外部ライブラリ（pandas 等）に依存せず標準ライブラリ + DuckDB で実装。

- Data（kabusys.data）
  - マーケットカレンダー管理 (calendar_management)
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day 等の API を提供。
    - market_calendar テーブルがない場合の曜日ベースフォールバック（主に土日除外）を実装。
    - calendar_update_job: J-Quants API から差分取得して market_calendar を冪等更新、バックフィルと健全性チェック（未来日付過多時はスキップ）を実装。
  - ETL パイプライン (pipeline.ETLResult)
    - ETL 実行結果を集約する dataclass を公開（取得件数、保存件数、品質問題、エラー等を保持）。
    - ETL の差分更新・バックフィル方針・品質チェック方針を定義（実装の意図を明記）。

### Fixed
- ロバスト性と安全性の改善
  - OpenAI 呼び出しで発生しうる各種エラー（RateLimit、接続、タイムアウト、APIError(5xx)）に対してリトライ戦略とフェイルセーフ（macro_sentiment=0.0 やスキップ）を整備。
  - DuckDB の executemany に対する互換性（空リスト不可）に配慮した処理（書込み前に params の有無をチェック）を実装。
  - DB 書込み失敗時のトランザクション回復処理（ROLLBACK の例外も捕捉して警告ログ出力）を実装。

### Security
- 設定管理で OS 環境変数を保護（.env の上書き時に保護セットを考慮）する仕組みを導入。

---

## [0.1.0] - 2026-03-29

初回リリース相当（コードベースの現状を反映）。主な機能は上記 Unreleased にまとめています。実運用を想定した以下の機能を含みます。

### Added
- パッケージ基本構造とバージョン情報を追加。
- 環境設定読み込み・検証機能。
- DuckDB ベースのデータ操作ユーティリティと ETL 結果オブジェクト。
- ニュース NLP スコアリング（OpenAI）と市場レジーム判定ロジック。
- ファクター計算（モメンタム、ボラティリティ、バリュー）および特徴量探索ユーティリティ。
- マーケットカレンダー管理と夜間更新ジョブ。

### Changed
- —（初回リリースのため該当なし）

### Fixed
- —（初回リリースのため該当なし）

### Notes
- 実行に必要な環境変数（例）
  - OPENAI_API_KEY（OpenAI 呼び出し）
  - JQUANTS_REFRESH_TOKEN（J-Quants API）
  - KABU_API_PASSWORD / KABU_API_BASE_URL（kabu API）
  - SLACK_BOT_TOKEN / SLACK_CHANNEL_ID（通知用）
- デフォルトで DuckDB・SQLite のファイルパスは設定値が用意されていますが、本番環境では明示的に環境変数で上書きすることを推奨します。
- OpenAI 呼び出し部分はテスト時に差し替え可能な実装になっています（ユニットテストでのモックが可能）。

---

変更履歴やリリースノートに不明点や補足が必要でしたら、具体的にどのモジュール／機能について詳細を出力するか教えてください。必要に応じてタグ付けや日付の調整、既存のリリース分割（複数バージョンへの分割）も可能です。