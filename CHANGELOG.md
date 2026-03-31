Keep a Changelog
=================
すべての重要な変更はこのファイルに記録します。

フォーマットは Keep a Changelog に準拠しています。
<https://keepachangelog.com/ja/1.0.0/>

Unreleased
----------

（なし）

[0.1.0] - 2026-03-31
--------------------

Added
- パッケージ初版を公開
  - パッケージ名: kabusys
  - バージョン: 0.1.0

- 基本構成・設定管理
  - kabusys.config
    - .env ファイルおよび環境変数の自動ロード機能を実装
      - 読み込み優先順位: OS 環境変数 > .env.local > .env
      - 自動ロードを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数に対応
      - プロジェクトルートは .git または pyproject.toml を探索して特定（cwd 非依存）
    - .env パーサを実装（export プレフィクス、シングル／ダブルクォート、エスケープ、インラインコメント処理に対応）
    - 環境変数保護（既存の OS 環境変数を保護する protected オプション）をサポート
    - Settings クラスで主要設定をプロパティとして公開
      - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID などの必須キー取得
      - DUCKDB_PATH / SQLITE_PATH のデフォルトパス
      - KABUSYS_ENV のバリデーション（development / paper_trading / live）
      - LOG_LEVEL のバリデーション

- AI（自然言語）関連
  - kabusys.ai.news_nlp
    - ニュース記事の銘柄別センチメント解析機能 score_news を実装
      - ニュース収集ウィンドウ計算（JSTベース -> UTC変換）を calc_news_window に実装
      - raw_news / news_symbols を集約し、銘柄ごとに最大記事数・最大文字数でトリムしてバッチ送信
      - OpenAI（gpt-4o-mini）の JSON mode を利用して出力を厳密な JSON として期待
      - バッチサイズ、トリム、JSON バリデーション、スコアの ±1.0 クリップを実装
      - リトライ（429・ネットワーク断・タイムアウト・5xx）を指数バックオフで実装
      - レスポンスパースやバリデーション失敗時は個別チャンクをスキップするフェイルセーフ設計
      - DuckDB に対する書き込みは部分更新（該当コードのみ DELETE → INSERT）で冪等性を確保
    - テスト用に _call_openai_api をパッチ可能に実装

  - kabusys.ai.regime_detector
    - 市場レジーム判定 score_regime を実装
      - ETF 1321 の 200 日移動平均乖離（重み 70%）とニュース由来のマクロセンチメント（重み 30%）を合成
      - マクロニュースのフィルタリング（キーワードリスト）と LLM による -1.0〜1.0 のスコア化
      - OpenAI 呼び出しに対するリトライ／バックオフ、API 失敗時は macro_sentiment=0.0 で継続
      - DuckDB へ冪等的に（BEGIN / DELETE / INSERT / COMMIT）書き込む
    - テスト用に _call_openai_api をパッチ可能に実装
    - ルックアヘッドバイアス防止（target_date 未満のみ参照）を明確に設計

- データプラットフォーム（DuckDB ベース）
  - kabusys.data.pipeline / etl
    - ETLResult データクラスを公開（ETL 実行の集計・監査用）
    - テーブル存在チェック・最大日付取得などのユーティリティ実装
    - 差分更新・backfill 等の設計方針を反映
  - kabusys.data.calendar_management
    - JPX カレンダー管理（market_calendar）と営業日判定ユーティリティを実装
      - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days 実装
      - market_calendar が未取得の場合は曜日ベースのフォールバック（土日除外）
      - calendar_update_job による J-Quants からの差分取得と冪等保存のワークフロー実装
      - バックフィル、先読み、健全性チェック（過剰に未来日付を検出した場合のスキップ）を実装
    - DuckDB からの date 型取り扱い補助を提供

- リサーチ（ファクター計算・特徴量解析）
  - kabusys.research.factor_research
    - モメンタム（1M/3M/6M、ma200 乖離）、ボラティリティ（20日 ATR）、流動性（平均売買代金、出来高比）、バリュー（PER, ROE）などのファクター計算関数を実装
    - DuckDB の SQL とウィンドウ関数を活用した高速集計を行い、(date, code) ごとの dict リストを返すインターフェース
    - データ不足時の None ハンドリングとログ出力
  - kabusys.research.feature_exploration
    - 将来リターン calc_forward_returns（任意ホライズン対応）
    - IC 計算（スピアマンランク相関）calc_ic
    - 値をランクに変換する rank 実装（同順位は平均ランク）
    - factor_summary で基本統計量（count/mean/std/min/max/median）を標準ライブラリのみで実装
    - pandas 等に依存しない設計

- パッケージ公開設定
  - src パッケージ配下にモジュール群を整備し __all__ を設定
  - __version__ = "0.1.0" を設定

Changed
- 設計ポリシー全体
  - ルックアヘッドバイアス防止を徹底（datetime.today()/date.today() を内部ロジックで直接参照しない設計を各モジュールで採用）
  - DuckDB との互換性考慮（executemany の空リスト問題等に対応）
  - 外部 API 呼び出し（OpenAI, J-Quants）失敗時はフェイルセーフ（処理継続、適切なデフォルト値）を採用

Fixed
- 環境変数パースの堅牢化
  - export キーワード、クォート内のバックスラッシュエスケープ、コメントの取り扱い等の処理を改善
- OpenAI 呼び出しの堅牢化
  - JSON レスポンスのパース耐性（前後余分なテキストが混入するケースの回復処理）
  - 5xx / ネットワークエラー / レート制限に対する再試行ロジックを実装
  - 非 5xx の APIError はリトライせずに警告を出してスキップする挙動を採用

Security
- 現時点で機密情報（API キー等）は Settings 経由で環境変数から取得する設計を採用
- .env 自動ロード時に OS 環境変数を保護する仕組み（protected set）を導入

Notes / Known issues
- OpenAI クライアントには gpt-4o-mini を想定しており、将来的な SDK 変更（例: 例外クラスや属性名の変更）に対しては部分的な互換性処理を含むが、完全互換性は保証しない
- DuckDB のバージョン差異（特にリスト型バインディングや executemany の挙動）に注意
- 一部機能は J-Quants クライアント（kabusys.data.jquants_client）に依存（実装側の API 呼び出し成功が必要）
- ETL / calendar_update_job は外部 API の利用とネットワーク環境に依存するため、API エラー時は 0 を返す等の安全策を取る

Authors
- kabusys 開発チーム

（以降の変更はこのファイルに記録してください）