# Changelog

すべての注目すべき変更点はこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠しています。  

注意: 以下の履歴は提供されたソースコードの内容から推測して作成したものであり、実際のコミット履歴ではありません。

## [0.1.0] - 2026-04-03

### Added
- パッケージ初期リリース: kabusys (バージョン 0.1.0)
  - パッケージメタ情報: src/kabusys/__init__.py に __version__ と __all__ を追加。

- 環境設定管理 (src/kabusys/config.py)
  - .env（.env.local）および OS 環境変数からの自動読み込み機能を実装。
    - プロジェクトルートを .git / pyproject.toml から探索して自動読み込み（CWD に依存しない）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
  - .env のパースを強化:
    - export プレフィックス対応、シングル/ダブルクォート内でのバックスラッシュエスケープ処理、インラインコメントの扱い。
  - override / protected オプションで既存 OS 環境変数を保護して上書き制御。
  - Settings クラスを提供し、アプリケーションで利用する設定プロパティを列挙（J-Quants / kabuAPI / LINE / DB パス / 監視設定 / システム設定 等）。
    - 必須値取得時の _require による明示的なエラー報告。
    - KABUSYS_ENV / LOG_LEVEL の値検証とユーティリティプロパティ (is_live / is_paper / is_dev) を実装。
    - デフォルト値・型変換・閾値（CPU/MEM/ディスク）などを設定。

- AI ニュース解析 & 市場レジーム判定 (src/kabusys/ai)
  - news_nlp モジュール (src/kabusys/ai/news_nlp.py)
    - raw_news / news_symbols を元に銘柄ごとのニュースを集約し、OpenAI（gpt-4o-mini）の JSON Mode を用いて銘柄別センチメント（ai_score）を算出。
    - タイムウィンドウの計算（前日 15:00 JST 〜 当日 08:30 JST 相当の UTC 範囲）を calc_news_window で提供。
    - バッチ処理（最大 20 銘柄/リクエスト）、1銘柄あたりの記事トリム（最大記事数・文字数）によるトークン肥大化対策。
    - レート制限・ネットワーク断・タイムアウト・5xx に対する指数バックオフ・リトライ実装。
    - レスポンスの厳密なバリデーション（JSON 抽出、キー/型検査、未知コード無視、スコア ±1.0 クリップ）。
    - DuckDB への冪等的書き込み（DELETE→INSERT を executemany で実行、空リスト回避）およびトランザクション処理（BEGIN/COMMIT/ROLLBACK）。
    - テスト容易性のため _call_openai_api を差し替え可能（unittest.mock.patch を想定）。
  - regime_detector モジュール (src/kabusys/ai/regime_detector.py)
    - ETF 1321 の 200 日移動平均乖離 (重み 70%) とマクロニュースの LLM センチメント (重み 30%) を合成して日次の市場レジーム (bull/neutral/bear) を判定。
    - prices_daily と raw_news を参照し、ma200_ratio 計算、マクロキーワードでの記事抽出、OpenAI 呼び出し、スコア合成、market_regime テーブルへの冪等書き込みを実施。
    - API 障害時は macro_sentiment=0.0 にフォールバックするフェイルセーフ設計。
    - リトライ・バックオフ、OpenAI API エラー処理（5xx 再試行等）を実装。
    - ルックアヘッドバイアスを避けるため datetime.today() 等を参照しない設計。

- データプラットフォーム (src/kabusys/data)
  - calendar_management (src/kabusys/data/calendar_management.py)
    - market_calendar テーブルに基づく営業日判断ユーティリティを提供（is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days）。
    - DB が未取得の範囲は曜日（平日）ベースでフォールバック。
    - JPX カレンダーの夜間差分更新ジョブ calendar_update_job を実装（J-Quants クライアント経由で差分取得、バックフィル、整合性チェック）。
    - 最大探索日数や健全性チェック、バックフィル日数などの安全策を導入。
  - ETL パイプライン (src/kabusys/data/pipeline.py)
    - 差分取得・保存・品質チェックを組み合わせた ETLResult データクラスを実装。
    - ETL の設計方針: 差分更新（営業日単位）、バックフィル、品質チェックはエラーを収集して呼び出し元に報告（Fail-Fast ではない）。
    - jquants_client と quality モジュールを組み合わせて利用することを想定。
  - etl モジュールは ETLResult を再エクスポート (src/kabusys/data/etl.py)。

- リサーチ / ファクター分析 (src/kabusys/research)
  - factor_research (src/kabusys/research/factor_research.py)
    - Momentum ファクター（1M/3M/6M リターン、200 日 MA 乖離）、Volatility（20 日 ATR 等）、Value（PER, ROE）等を DuckDB 上で計算する関数を提供（calc_momentum / calc_volatility / calc_value）。
    - 計算は prices_daily / raw_financials のみ参照し、本番発注 API には影響しない設計。
    - データ不足時に None を返すなどの堅牢な扱い。
  - feature_exploration (src/kabusys/research/feature_exploration.py)
    - 将来リターン 계산 (calc_forward_returns)、IC（情報係数）計算 (calc_ic)、ランキング変換 (rank)、ファクター統計サマリー (factor_summary) を実装。
    - 外部ライブラリに依存せず標準ライブラリと DuckDB で実行可能な実装。

- パッケージ内部公開整理
  - ai/__init__.py, research/__init__.py で主要 API を再エクスポート（score_news, score_regime, calc_* 等）。
  - data/__init__.py はモジュール群のルートとして整備。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Internal / Implementation notes
- ルックアヘッドバイアス対策として多くの関数が datetime.today() / date.today() を参照せず、呼び出し元から target_date を受け取る設計を採用。
- DuckDB の仕様（executemany に空リスト渡せない等）を考慮した実装を行い、部分失敗時に既存データを保護するために対象コードを絞って DELETE → INSERT を行うパターンを採用。
- OpenAI 呼び出しに関しては JSON Mode を利用し、レスポンス整形・堅牢性強化（余計な前後テキストの除去等）を実装。
- テストフレンドリーなフック（_call_openai_api の差し替え等）を複数箇所に提供。

## 未記載項目
- 実際のリリース日や細かなバグ修正・マイナー変更は本 CHANGELOG の想定外です。実際のコミット履歴に基づく正確な履歴は Git の履歴を参照してください。