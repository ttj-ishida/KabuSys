Keep a Changelog
=================

すべての重要な変更を、このファイルで管理します。  
このプロジェクトは Keep a Changelog のフォーマットに従います。

[0.1.0] - 2026-04-01
--------------------

Added
- 基本パッケージ初期実装を追加
  - パッケージバージョン: 0.1.0（src/kabusys/__init__.py）
  - パブリックモジュール: data, strategy, execution, monitoring を __all__ で公開

- 環境変数 / 設定管理（src/kabusys/config.py）
  - .env / .env.local をプロジェクトルート（.git または pyproject.toml を探索）から自動読み込み
  - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動読み込みを無効化可能
  - .env パースの堅牢化（export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント扱い等）
  - 環境変数上書き制御（override / protected）を実装し OS 環境変数保護
  - Settings クラスを提供（J-Quants / kabuステーション / Slack / DB / 監視閾値 / システム設定）
  - 必須項目取得時の検証（_require）および KABUSYS_ENV / LOG_LEVEL の許容値検証
  - デフォルトパス/閾値を明示（例: DUCKDB_PATH="data/kabusys.duckdb" 等）

- AI モジュール（src/kabusys/ai）
  - ニュース NLP（src/kabusys/ai/news_nlp.py）
    - 指定タイムウィンドウ（前日 15:00 JST 〜 当日 08:30 JST）に基づき raw_news と news_symbols を集約
    - 銘柄ごとに記事を結合しトリム（最大記事数・最大文字数）して OpenAI（gpt-4o-mini）にバッチ送信
    - JSON Mode のレスポンス検証・パース、スコアクリッピング（±1.0）
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフリトライ
    - 部分成功を想定した idempotent な DB 書き換えロジック（DELETE → INSERT、書き込み対象コードを限定）
    - テスト容易性: _call_openai_api を patch して差し替え可能
  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次でレジーム判定
    - マクロキーワードで raw_news をフィルタし、OpenAI へ送信（gpt-4o-mini、JSON mode）
    - API レスポンスパース失敗や API エラー時は macro_sentiment=0.0 にフォールバック（フェイルセーフ）
    - レジームスコア合成後、market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）
    - API 呼び出しに対するリトライ制御と詳細なログ出力
    - テスト用に _call_openai_api を差し替え可能

- データプラットフォーム関連（src/kabusys/data）
  - カレンダー管理（src/kabusys/data/calendar_management.py）
    - market_calendar を元に営業日判定ユーティリティを提供: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day
    - calendar_update_job: J-Quants API から差分取得して market_calendar を冪等保存。バックフィル、健全性チェック実装
    - DB 未取得時の曜日ベースのフォールバックや、部分的な DB 登録（NULL 値含む）への対処を設計
  - ETL パイプライン（src/kabusys/data/pipeline.py, src/kabusys/data/etl.py）
    - ETLResult データクラスを導入（取得件数・保存件数・品質問題・エラー一覧を保持）
    - 差分更新・バックフィル・品質チェックの設計方針を実装。J-Quants クライアント経由で保存（idempotent）
    - etl モジュールは pipeline.ETLResult を再エクスポート
    - DuckDB に対するテーブル存在チェック等のユーティリティを実装
  - jquants_client / quality 等のクライアントを想定した抽象化（モジュール間の分離）

- リサーチ / ファクター（src/kabusys/research）
  - factor_research.py
    - Momentum（1M/3M/6M リターン、200日 MA 乖離）、Volatility（20日 ATR 等）、Value（PER, ROE）の計算を DuckDB SQL ベースで実装
    - 欠損時は None を返し、営業日/窓幅のバッファを設けた安定的なスキャンを実施
  - feature_exploration.py
    - 将来リターン calc_forward_returns（任意ホライズン対応）、IC（Spearman ランク相関）計算、rank、factor_summary（count/mean/std/min/max/median）を提供
    - pandas 等非依存の純 Python 実装
  - research パッケージの __all__ で主要関数を再公開

- データユーティリティ
  - zscore_normalize を data.stats 経由で利用可能（research/__init__.py から再エクスポート想定）

Changed
- （初期リリースのため該当なし）

Fixed
- （初期リリースのため該当なし）

Security
- OpenAI API キーは引数で注入可能（api_key 引数）または環境変数 OPENAI_API_KEY を使用。未設定時は ValueError を発生させ処理を中止（安全性のため明示的なエラー扱い）

Notes / 実装上の重要点（ユーザ向け）
- 必須環境変数（本実装で参照・必須となる可能性のあるもの）
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, OPENAI_API_KEY
- .env 自動読み込みの優先順位: OS 環境 > .env > .env.local（.env.local は override=True で上書き）
- AI モジュールは gpt-4o-mini の JSON Mode を前提にしており、API レスポンスの不備に対してフォールバックを行います（0.0 の中立値など）。
- ニュース集計ウィンドウ（score_news）:
  - JST ベース: 前日 15:00 ～ 当日 08:30 → UTC に変換して DB と比較（前日 06:00 ～ 23:30 UTC）
- テスト容易性:
  - OpenAI 呼び出しを行う内部関数（各モジュールの _call_openai_api）を unittest.mock.patch で差し替えてテスト可能
- DuckDB の executemany に関する互換性考慮（空リストを渡さないチェック）を実装

Known Issues / TODO
- src/kabusys/data/pipeline.py の末尾にコード断片（return date.fro）が存在するように見え、ファイル末尾が切れている可能性があります。実際のブランチでは pipeline の残り実装（最大日付取得など）の完成・整合性確認が必要です。
- 実際の production 接続（J-Quants クライアント、kabu API、Slack 連携等）の統合テストは別途必要。AI 呼び出しは課金やレート制限があるため、CI ではモック化推奨。

クレジット
- 初期設計では「ルックアヘッドバイアス防止」「DB への冪等保存」「フェイルセーフでの継続」「テスト可能な構造」を重点に実装されています。

---