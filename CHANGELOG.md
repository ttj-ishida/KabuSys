Keep a Changelog
----------------

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。

[Unreleased]
------------

- 今のところなし。

[0.1.0] - 2026-04-01
-------------------

Added
- 初回リリース: KabuSys 日本株自動売買システムのコアライブラリを追加。
  - パッケージバージョン: 0.1.0（src/kabusys/__init__.py）
- 環境設定
  - .env/.env.local 自動ロード機能を実装（プロジェクトルートは .git または pyproject.toml で探索）。自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。（src/kabusys/config.py）
  - .env パーサーの実装: export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメントの扱いなどを考慮した堅牢なパース処理を提供。
  - Settings クラスを公開し、J-Quants / kabuステーション / Slack / DB パス / 監視閾値 / 環境・ログレベルの検証済みプロパティを提供（必須環境変数は未設定時に ValueError を発生）。
- AI（自然言語処理）機能
  - ニュースセンチメントスコアリング（score_news）
    - raw_news と news_symbols を集約して銘柄ごとにニュースを結合し、OpenAI（gpt-4o-mini）へバッチ送信して銘柄ごとのセンチメント（-1.0〜1.0）を生成・ai_scores テーブルへ書き込み。（src/kabusys/ai/news_nlp.py）
    - チャンクサイズ、1銘柄あたりの最大記事数／文字数制限、JSON Mode を前提としたレスポンスバリデーション、スコアのクリップ処理を実装。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフリトライを実装。API 失敗時はフェイルセーフ（該当チャンクをスキップ）で継続。
    - ニュース集計ウィンドウは JST ベースで「前日 15:00 JST ～ 当日 08:30 JST」（UTC に変換して DB クエリ）を計算する calc_news_window を提供。
    - テスト容易性のため、OpenAI 呼び出しはモジュール内の _call_openai_api をパッチ可能に設計。
  - 市場レジーム判定（score_regime）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とニュース由来のマクロセンチメント（重み 30%）を合成して日次でレジーム（bull/neutral/bear）を判定・market_regime テーブルへ冪等的に書き込み。（src/kabusys/ai/regime_detector.py）
    - マクロセンチメントはマクロキーワードでフィルタしたニュースタイトル群を LLM（gpt-4o-mini）へ投げ、JSON レスポンスから抽出。API 失敗時は macro_sentiment=0.0 で継続するフェイルセーフを実装。
    - LLM 呼び出しは内部で再試行・エラーハンドリングを実装し、重大な障害時のロギングを強化。
- Research（因子計算・特徴量探索）
  - ファクター計算: モメンタム（1M/3M/6M、ma200 乖離）、ボラティリティ（20日 ATR 等）、バリュー（PER, ROE）を計算する関数を実装。すべて DuckDB の prices_daily / raw_financials を用いた SQL ベースの実装で外部 API には依存しない。（src/kabusys/research/factor_research.py）
  - 特徴量探索: 将来リターン計算（calc_forward_returns）、IC（calc_ic）、ランク変換（rank）、ファクター統計サマリー（factor_summary）を実装。外部ライブラリに依存せず純粋 Python/SQL で実装。（src/kabusys/research/feature_exploration.py）
  - zscore_normalize を data.stats から再エクスポートする細かな API 統合。（src/kabusys/research/__init__.py）
- Data（ETL / カレンダー / パイプライン）
  - 市場カレンダー管理（calendar_management）
    - market_calendar テーブルを基に営業日判定、次/前営業日取得、期間内営業日列挙、SQ 日判定を実装。DB にデータがない場合は曜日ベースのフォールバックを行う設計。（src/kabusys/data/calendar_management.py）
    - JPX カレンダー差分フェッチの夜間ジョブ calendar_update_job を実装（J-Quants クライアント経由で差分取得・バックフィル・健全性チェック・冪等保存）。
  - ETL パイプライン（pipeline）
    - ETL 実行結果を表す ETLResult dataclass を追加。フェッチ/保存件数、品質チェック結果、エラー概要などを含む。品質チェック結果は辞書化して出力可能。（src/kabusys/data/pipeline.py）
    - 差分更新・バックフィル・品質チェックの設計方針をコメントで明記（実装は pipeline モジュールに準備）。
  - ETL 公開インターフェースとして ETLResult を再エクスポート（src/kabusys/data/etl.py）。
- 互換性・運用上の注意
  - DuckDB の executemany に空リストを渡せない問題を考慮した実装（空チェックを入れてから executemany 実行）。
  - 各種操作で冪等（BEGIN / DELETE / INSERT / COMMIT など）を意識した DB 操作を採用。
  - ルックアヘッドバイアス回避のため、内部実装で datetime.today()/date.today() を直接参照しない設計を明記（target_date を明示的に受け取る仕様）。
  - OpenAI 呼び出しや外部 API 呼び出しは失敗時にフォールバックするフェイルセーフを複数箇所で実装。

Changed
- （初版のため該当なし）

Fixed
- （初版のため該当なし）

Security
- 環境変数の読み込み・上書きに際して OS 環境変数を保護するための protected set を使用（config._load_env_file）。機密情報の誤上書きを回避。

Notes / Known limitations
- OpenAI API 呼び出しは gpt-4o-mini / JSON Mode を前提としており、API の仕様変更やレスポンスの変動に伴う微調整が必要になる可能性があります。
- ETL パイプラインの高レベル設計は整備済みだが、外部 J-Quants クライアント実装（jquants_client）や quality モジュールに依存するため、本パッケージ単体では外部実装の存在が必要です（参照: src/kabusys/data/jquants_client を想定）。
- docs やユーザー向けの CLI / サービス起動スクリプトは本バージョンに含まれていません。運用周りは別途整備が必要です。

Authors
- KabuSys 開発チーム（ソースコード内の設計コメントに基づく初期実装）

Acknowledgments
- DuckDB、OpenAI API（および gpt-4o-mini）に依存。

----