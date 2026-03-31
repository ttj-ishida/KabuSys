CHANGELOG
=========
すべての重要な変更はこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠しています。
リリース日はリポジトリ内のコードから推測した日付を使用しています。

[Unreleased]
------------

- なし

[0.1.0] - 2026-03-31
-------------------

Added
- パッケージ初期公開: kabusys v0.1.0
  - パッケージメタ:
    - __version__ = "0.1.0"
    - パッケージの公開インターフェースに data, strategy, execution, monitoring を定義

- 環境設定管理 (kabusys.config)
  - .env / .env.local ファイルおよび環境変数から設定を自動で読み込む仕組みを実装
    - プロジェクトルートは .git または pyproject.toml を基準に探索（CWD 非依存）
    - 読み込み優先順位: OS 環境変数 > .env.local > .env
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能
    - .env パースは export 形式、クォート／エスケープ、インラインコメント等に対応
    - OS 環境変数の上書きを防ぐ「protected」機構を導入
  - Settings クラスによりアプリケーション設定をプロパティで提供
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, OPENAI_API_KEY（AI系関数で使用）などを参照
    - データベースパスの既定値: DUCKDB_PATH="data/kabusys.duckdb", SQLITE_PATH="data/monitoring.db"
    - KABUSYS_ENV の検証（development / paper_trading / live）
    - LOG_LEVEL の検証（DEBUG/INFO/WARNING/ERROR/CRITICAL）
    - is_live / is_paper / is_dev のユーティリティプロパティ

- AI モジュール (kabusys.ai)
  - ニュース NLP スコアリング (kabusys.ai.news_nlp)
    - raw_news / news_symbols を元に銘柄ごとにニュースを集約し、OpenAI (gpt-4o-mini) の JSON mode でセンチメントを取得
    - バッチ処理: 1 API コールあたり最大 20 銘柄
    - 1銘柄あたりの記事数・文字数上限でトリム（_MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK）
    - レート制限・ネットワーク断・タイムアウト・5xx に対する指数バックオフリトライ
    - レスポンスの堅牢なバリデーション（JSON 抽出・results 配列・code/score 検証・数値クリップ）
    - スコアは ±1.0 にクリップして ai_scores テーブルへ冪等的に書き込み（DELETE → INSERT）
    - テスト容易性のため _call_openai_api を patch 可能
    - calc_news_window など日時ウィンドウ計算ユーティリティを提供
  - 市場レジーム判定 (kabusys.ai.regime_detector)
    - ETF 1321 の 200日移動平均乖離（重み70%）とマクロニュースの LLM センチメント（重み30%）を合成して日次の market_regime を算出
    - マクロニュースは news_nlp の calc_news_window と raw_news から抽出（マクロ系キーワードでフィルタ）
    - OpenAI 呼び出しは専用実装（news_nlp とは独立）
    - API エラー時は macro_sentiment=0.0 のフェイルセーフ挙動
    - DuckDB への冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）とロールバック処理
    - 設定可能な閾値（bull/bear/neutral）やリトライ戦略を実装

- リサーチモジュール (kabusys.research)
  - ファクター計算 (kabusys.research.factor_research)
    - Momentum: 約1M/3M/6M リターン、ma200 乖離 (ma200_dev)
    - Volatility: 20日 ATR、相対 ATR、20日平均売買代金、出来高比率
    - Value: PER（EPS が無効な場合は None）、ROE（raw_financials から取得）
    - DuckDB を用いた SQL + Python 実装、結果は (date, code) をキーとする dict リストで返却
    - データ不足時の None ハンドリングとログ出力
  - 特徴量探索 (kabusys.research.feature_exploration)
    - 将来リターン計算（calc_forward_returns）: 任意ホライズン（デフォルト [1,5,21]）
    - IC 計算（calc_ic）: スピアマンランク相関（ランクは同順位を平均ランク化）
    - 統計サマリー（factor_summary）: count/mean/std/min/max/median
    - 外部ライブラリに依存せず標準ライブラリのみで実装

- データプラットフォーム (kabusys.data)
  - カレンダー管理 (kabusys.data.calendar_management)
    - JPX カレンダーの夜間バッチ更新（calendar_update_job）を J-Quants クライアント経由で実装
    - market_calendar に基づく is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を提供
    - market_calendar が不十分な場合の曜日ベースのフォールバックを実装
    - 最大探索範囲やバックフィル、健全性チェックを実装して異常値を回避
  - ETL パイプライン (kabusys.data.pipeline)
    - ETLResult データクラスを提供（取得/保存件数、品質問題、エラーの収集）
    - 差分更新、バックフィル、品質チェックの設計方針を反映
    - 内部ユーティリティ: テーブル存在確認、最大日付取得など
  - etl モジュールで ETLResult を公開再エクスポート

- インポート/公開整理
  - k abu sys.ai.__init__ で score_news を公開
  - kabusys.research.__init__ で主要関数を再エクスポート
  - パッケージ構成によりモジュールの責務を明確化

Security
- なし（特記事項なし）

Changed
- 初回リリースのため該当なし

Fixed
- 初回リリースのため該当なし

Notes / 重要な運用注意事項
- AI 系関数（score_news, score_regime）は OpenAI API キー（OPENAI_API_KEY）を必要とします。api_key を関数引数で明示的に渡すことも可能です。
- .env 自動読み込みはプロジェクトルートの検出に依存します。パッケージ配布先で自動ロードを無効にしたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。
- DB 書き込みは基本的に冪等化（DELETE → INSERT）・トランザクションで行われますが、部分失敗時に既存データを保護するためにコード単位で絞り込んで更新します。
- ルックアヘッドバイアス回避のため、日付判定ロジックは datetime.today() / date.today() を直接参照しない設計です（関数に target_date を渡して利用）。
- DuckDB のバージョン差異（executemany の空リスト扱い等）を考慮した実装上の注意があります。

既知の制限
- ai モジュールは外部 OpenAI API に依存するため、API 料金・レート制限・レスポンス仕様変更に影響されます。レスポンスフォーマットの破壊的変更には追加対応が必要です。
- 一部の SQL 実装は DuckDB の挙動に依存しており、異なる SQL エンジンでは動作しない可能性があります。

今後の予定（案）
- strategy / execution / monitoring の具現化（現時点でパッケージ名として公開済み）
- より詳細な品質チェックルールの拡張
- AI モデルの切り替え・ローカル推論対応オプションの追加

以上。