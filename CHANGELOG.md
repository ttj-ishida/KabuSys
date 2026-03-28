Keep a Changelog
=================

すべての重要な変更をこのファイルで記録します。  
フォーマットは "Keep a Changelog" に準拠します。

Unreleased
----------

- （なし）

0.1.0 - 2026-03-28
------------------

初回リリース。日本株自動売買システムのコアライブラリを公開します。主な追加点・挙動は以下の通りです。

Added
- パッケージ基礎
  - kabusys パッケージを追加。バージョンは 0.1.0。
  - パッケージ公開 API: kabusys/__init__.py で submodule（data, strategy, execution, monitoring）を公開。

- 設定・環境変数管理 (kabusys.config)
  - .env / .env.local の自動読み込み機能を追加（プロジェクトルートは .git または pyproject.toml から探索）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート（テスト用）。
  - .env 解析器は export KEY=val 形式、シングル/ダブルクォート、エスケープ、行末コメントを適切に処理。
  - .env.local は .env を上書き（OS 環境変数は保護される）。
  - Settings クラスを実装し、使用可能な設定プロパティを提供:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH, SQLITE_PATH
    - KABUSYS_ENV（development/paper_trading/live の検証）および LOG_LEVEL の検証
    - is_live / is_paper / is_dev のユーティリティプロパティ
  - 必須環境変数未設定時は ValueError を送出する明示的な検証を追加。

- AI モジュール (kabusys.ai)
  - news_nlp モジュール:
    - raw_news と news_symbols を集約して銘柄ごとにテキストを準備し、OpenAI（gpt-4o-mini）を用いて銘柄単位のセンチメント ai_score を生成。
    - バッチ処理（最大 20 銘柄/リクエスト）、トークン肥大化対策（記事数・文字数のトリム）、JSON Mode を利用した堅牢なレスポンス処理。
    - 再試行（429/ネットワーク断/タイムアウト/5xx）を指数バックオフで実装。失敗時は該当チャンクをスキップして続行。
    - レスポンスのバリデーション（JSON 抽出、results 配列、code/score の検査、スコアのクリップ）を実装。
    - ai_scores テーブルへの置換的書き込み（BEGIN / DELETE (個別 executemany) / INSERT / COMMIT）により冪等性を確保。部分失敗時に既存データを不要に削除しない設計。
    - calc_news_window ユーティリティ（JST ベースの時間ウィンドウ -> UTC naive datetime）を提供。
    - score_news(conn, target_date, api_key=None) を実装（書き込んだ銘柄数を返す。APIキー未設定時は ValueError）。
  - regime_detector モジュール:
    - ETF 1321 の 200 日移動平均乖離（70%）とマクロニュース LLM センチメント（30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定する機能を追加。
    - マクロ記事はキーワードベースで抽出（最大 20 件）。LLM 呼び出しは JSON Mode で macro_sentiment を取得。
    - API エラー時のフェイルセーフ（macro_sentiment=0.0）、冪等な DB 書き込み（DELETE/INSERT/COMMIT）を採用。
    - score_regime(conn, target_date, api_key=None) を実装（成功時に 1 を返す）。APIキー未設定時は ValueError。

- データ（Data Platform）モジュール (kabusys.data)
  - calendar_management:
    - market_calendar を用いた営業日判定・検索ユーティリティを実装。
      - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days を提供。
    - DB にカレンダーが無い場合は曜日ベース（土日を非営業日）でフォールバック。
    - next/prev/get の探索は最大 _MAX_SEARCH_DAYS の上限を設けて無限ループを防止。
    - calendar_update_job により J-Quants API から差分取得し market_calendar を冪等保存。バックフィル・健全性チェックを実装。
  - pipeline / etl:
    - ETLResult データクラスを実装（取得件数・保存件数・品質問題・エラー一覧などを保持）。
    - データ差分取得・保存・品質チェックのための基盤を追加（jquants_client / quality と連携する想定）。
    - kabusys.data.etl で ETLResult を再エクスポート。

- リサーチ（kabusys.research）
  - factor_research:
    - calc_momentum / calc_volatility / calc_value を実装。prices_daily / raw_financials を参照し、各銘柄のファクターを計算して (date, code) キーの dict リストを返す。
    - 設計上、データ不足時は None を返すなど堅牢な振る舞い。
  - feature_exploration:
    - calc_forward_returns（任意ホライズンに対する将来リターン）、calc_ic（Spearman のランク相関による IC）、rank、factor_summary（各列の基本統計量）を実装。
    - pandas など外部依存を使わずに標準ライブラリ／DuckDB SQL で実装。
  - research パッケージの __all__ で主要関数を再エクスポート。

Changed
- 初版リリースのため、マイグレーションや後方互換性の変更はなし。

Fixed
- 初版リリースのため、バグ修正履歴はなし。

Security
- OpenAI / 外部 API 利用：
  - OpenAI API キーが未設定の場合、score_news / score_regime は ValueError を送出して明示的に失敗するようにしている（安全性を重視）。
  - 必須の外部トークン（JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN, KABU_API_PASSWORD 等）は Settings で必須化している。
- .env 読み込み時に OS 環境変数を保護（.env ファイルで既存の OS 環境変数を上書きしない等）する仕組みを導入。

Notes / Implementation details
- 全モジュールでルックアヘッドバイアスを避ける設計を採用（datetime.today() / date.today() を直接参照しない、ターゲット日ベースでウィンドウを計算）。
- DuckDB を主要なローカル DB として利用する想定（関数は duckdb.DuckDBPyConnection を受け取る）。
- OpenAI とのやり取りは JSON Mode を利用し、レスポンスに対する堅牢なパース・バリデーションを行う。
- AI 呼び出し部分はテスト容易性のため _call_openai_api のオーバーライド（patch）を想定した設計。
- DB 書き込みは可能な限り冪等性を確保（DELETE→INSERT、ON CONFLICT、BEGIN/COMMIT/ROLLBACK）。

今後の予定（例）
- strategy / execution / monitoring の具体実装と統合テスト。
- jquants_client や Slack 通知の具体実装とエンドツーエンド確認。
- パフォーマンス向上のための並列化やバッチ最適化。

--- 

変更や誤りの報告、改善提案は Issue や Pull Request にて歓迎します。