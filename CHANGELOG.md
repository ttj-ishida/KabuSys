# Changelog

すべての注目すべき変更点をこのファイルに記録します。  
フォーマットは「Keep a Changelog」の仕様に準拠しています。  

## [Unreleased]

開発中の変更や今後のマイルストーンはここに記載してください。

---

## [0.1.0] - 2026-03-29

初期リリース。日本株自動売買システム「KabuSys」のコア機能を提供します。

### 追加 (Added)
- パッケージ初期化
  - kabusys パッケージのバージョンを 0.1.0 として公開。
  - __all__ に data / strategy / execution / monitoring を公開。

- 環境設定管理 (kabusys.config)
  - .env ファイルおよび環境変数から設定を読み込む自動ロード機能を実装。
    - 読み込み順序: OS 環境変数 > .env.local > .env
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
    - プロジェクトルートは .git または pyproject.toml を基準に探索（__file__ 起点）。
  - .env パーサーは export 形式・クォート・エスケープ・インラインコメントに対応。
  - Settings クラスを提供し、主要設定をプロパティ経由で取得:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH, SQLITE_PATH
    - KABUSYS_ENV（development/paper_trading/live）、LOG_LEVEL（DEBUG/INFO/...）
    - is_live / is_paper / is_dev のヘルパー

- AI モジュール (kabusys.ai)
  - news_nlp.score_news
    - raw_news と news_symbols から銘柄ごとのニュースを集約し、OpenAI（gpt-4o-mini）の JSON モードでセンチメント評価。
    - バッチ処理（最大 20 銘柄/コール）、トークン肥大化対策（記事数・文字数制限）。
    - リトライ（429 / ネットワーク / タイムアウト / 5xx）を指数バックオフで実装。
    - レスポンス検証、スコアの ±1.0 クリップ、ai_scores への冪等書き込み（DELETE → INSERT）。
    - テストフックとして _call_openai_api をモック差替え可能。
  - regime_detector.score_regime
    - ETF 1321（日経225連動）200日移動平均乖離（70%）とマクロニュース LLM センチメント（30%）を合成して市場レジーム（bull/neutral/bear）を判定し、market_regime テーブルへ冪等書き込み。
    - prices_daily からのルックアヘッド回避、API レスポンスパース失敗時のフェイルセーフ（macro_sentiment = 0.0）。
    - OpenAI クライアント生成・リトライロジックを内包。

- データモジュール (kabusys.data)
  - calendar_management
    - JPX カレンダー用ユーティリティ（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）。
    - market_calendar が存在しない場合は曜日ベース（平日）でフォールバック。
    - 夜間バッチ calendar_update_job: J-Quants から差分取得し market_calendar を更新、バックフィル・健全性チェックを実装。
  - pipeline / etl / ETLResult
    - ETLResult データクラスで ETL 実行結果を表現（フェッチ数・保存数・品質問題・エラー等）。
    - 差分更新・バックフィル・品質チェックの方針に基づく ETL パイプライン基盤（jquants_client 連携を想定）。
    - data.etl は pipeline.ETLResult を再エクスポート。

- リサーチモジュール (kabusys.research)
  - factor_research
    - モメンタム: 1M/3M/6M リターン、200日 MA 乖離（ma200_dev）
    - ボラティリティ/流動性: 20日 ATR、相対 ATR、20日平均売買代金、出来高比
    - バリュー: PER（EPS が 0/欠損なら None）、ROE（raw_financials から取得）
    - DuckDB + SQL を主体に計算し、(date, code) をキーとする辞書リストを返す設計
  - feature_exploration
    - 将来リターン計算 (calc_forward_returns): 任意ホライズン（デフォルト [1,5,21]）の計算、入力検証
    - IC（Information Coefficient）計算（スピアマンランク相関 calc_ic）
    - ランク変換ユーティリティ rank（同順位は平均ランク）
    - 統計サマリー factor_summary（count/mean/std/min/max/median）

- その他
  - テスト容易性のため複数の内部関数（OpenAI 呼び出し等）を差し替え可能に実装。
  - DuckDB を前提としたクエリ実装と、DuckDB の実装差異（executemany の空リスト等）への対応。

### 変更 (Changed)
- （初期リリースのため過去からの変更はありません）

### 修正 (Fixed)
- （初期リリースのため過去の不具合修正はありません）

### 注意事項 / 既知の制約 (Known limitations)
- OpenAI（gpt-4o-mini）および openai SDK に依存。API キーは OPENAI_API_KEY 環境変数か関数引数で供給する必要あり。
- DuckDB 接続を多用する設計のため、DuckDB が動作する環境が必要。
- .env 自動ロードはプロジェクトルート探索に依存するため、配布後の利用時は環境変数の事前設定を推奨（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
- ai モジュールは外部 API の失敗時に「スコア 0.0」や「スキップ」でフォールバックする設計。外部 API の可用性により結果が変動する可能性がある。
- 一部 DuckDB バージョンや SQL 機能差分に対して互換性処理を実装しているが、ランタイム環境での検証が必要。

### セキュリティ (Security)
- なし（初期リリース時点で特記事項なし）。

---

作成者: KabuSys 開発チーム  
（この CHANGELOG はコードベースから推測して作成しました。実際のリリースノートはリリース管理ポリシーに合わせて調整してください。）