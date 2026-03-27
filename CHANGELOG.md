# Changelog

すべての注目すべき変更点をこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠し、セマンティックバージョニングを使用します。

## [Unreleased]

## [0.1.0] - 2026-03-27
初回リリース。日本株自動売買システムのコア機能を実装・公開。

### 追加
- パッケージ基盤
  - kabusys パッケージの初期公開（__version__ = 0.1.0）。
  - パッケージ公開 API の __all__ に data, strategy, execution, monitoring を設定。

- 設定・環境変数管理（kabusys.config）
  - .env ファイルおよび環境変数から設定を読み込む自動ローダーを実装。
    - プロジェクトルートを .git または pyproject.toml で探索して .env/.env.local を優先順で読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
    - OS 環境変数を保護（.env.local は上書き可能だが既存 OS 環境変数は保護）。
  - .env パーサーは export プレフィックス、シングル／ダブルクォート、エスケープ、インラインコメント処理に対応。
  - Settings クラスを提供：
    - J-Quants、kabuステーション、Slack、DB パス等のプロパティ経由でアクセス可能。
    - 必須設定は未設定時に明示的なエラーを発生させる（_require）。
    - KABUSYS_ENV と LOG_LEVEL の値検証（許容値チェック）と利便性プロパティ（is_live / is_paper / is_dev）。

- ニュース NLP（kabusys.ai.news_nlp）
  - raw_news と news_symbols を使った銘柄単位ニュース集約（前日 15:00 JST ～ 当日 08:30 JST のウィンドウ）。
  - OpenAI（gpt-4o-mini）を用いたバッチセンチメントスコアリング（JSON Mode を使用）。
  - バッチサイズ、記事数・文字数トリム、リトライ（指数バックオフ）や 5xx/429/タイムアウト等の耐障害性を実装。
  - レスポンス検証ロジック（JSON 部分抽出・results 構造検査・スコア数値検証）とスコアの ±1.0 クリップ。
  - DuckDB への冪等書き込み（存在する code のみ DELETE → INSERT）で部分失敗時の既存データ保護。
  - テスト容易化のため OpenAI 呼び出しを差し替え可能（内部の _call_openai_api をモック可能）。

- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF 1321（日経225連動）200日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）の合成で日次レジーム判定（bull / neutral / bear）。
  - prices_daily と raw_news を参照して ma200_ratio とマクロタイトルを取得。
  - OpenAI（gpt-4o-mini）を使ったマクロセンチメント評価にリトライ・フェイルセーフ（失敗時 macro_sentiment=0.0）。
  - 計算結果を market_regime テーブルへ冪等的に書き込み（BEGIN / DELETE / INSERT / COMMIT）。
  - ルックアヘッドバイアス対策（date 引数を明示的に受け、datetime.today() を参照しないクリーン設計）。

- データプラットフォーム（kabusys.data）
  - カレンダー管理（calendar_management）
    - JPX カレンダーの夜間バッチ更新ジョブ（calendar_update_job）を実装。J-Quants クライアント経由で差分取得 → 保存（ON CONFLICT DO UPDATE）。
    - market_calendar が未取得の際は曜日ベースのフォールバック（週末を非営業日扱い）。
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day の一貫した営業日判定 API を提供。
    - 探索の上限日数やバックフィル、健全性チェックを実装して無限ループ・異常データを回避。
  - ETL パイプライン（pipeline）
    - 差分取得・保存・品質チェックのフローを実装。
    - ETLResult データクラスを提供（取得数・保存数・品質問題・エラー概要を格納、辞書変換可能）。
    - デフォルトのバックフィル日数やカレンダー先読みの設定を実装。
    - テーブル存在チェックや最大日付取得などのユーティリティを含む。
  - etl モジュールで ETLResult を再エクスポート（kabusys.data.etl）。

- リサーチ／ファクター（kabusys.research）
  - factor_research:
    - モメンタム（1M/3M/6M リターン、200日 MA 乖離）、ボラティリティ（20日 ATR）、流動性（20日平均売買代金、出来高比）、バリュー（PER, ROE）計算を SQL + DuckDB で実装。
    - データ不足時の None 処理やログ出力を考慮。
  - feature_exploration:
    - 将来リターン計算（任意ホライズン、デフォルト [1,5,21]）、IC（Spearman の ρ）計算、ファクター統計サマリー、ランク変換ユーティリティを提供。
    - pandas 等に依存せず標準ライブラリと DuckDB のみで実装。
  - 研究用ユーティリティの公開（zscore_normalize 再利用、主要関数の __all__ へ登録）。

### 安全策・設計方針（注記）
- ルックアヘッドバイアス回避
  - AI スコア生成やファクター計算は全て target_date を明示的に受け取り、datetime.today()/date.today() を直接参照しない設計。
- フェイルセーフ
  - OpenAI など外部 API の失敗時は例外を投げるのではなく安全なデフォルト（0.0）やスキップで継続し、ログに失敗を残す。
- 冪等性
  - DB 書き込みは基本的に冪等（DELETE → INSERT / ON CONFLICT）で設計され、部分失敗による既存データの破壊を防ぐ。
- テスト容易性
  - OpenAI 呼び出しポイントは内部関数を経由しており、ユニットテストでのモック差し替えを想定。

### 既知の制限・注意点
- OpenAI API キー（OPENAI_API_KEY）が必須な処理がある（score_news / score_regime はキー未設定で ValueError を発生）。
- 本バージョンは DuckDB をデータストアとして利用する設計。SQL の互換性や executemany の空リスト制約（DuckDB 0.10）を考慮した実装が含まれる。
- 一部の外部連携（J-Quants クライアント、kabuステーション API、Slack 投稿等）はモジュール化されているが、ランタイム環境での接続設定が必要。

### 修正
- （初回リリースのため該当なし）

### 非推奨
- （初回リリースのため該当なし）

### セキュリティ
- （初回リリースのため該当なし）