Keep a Changelog 準拠の CHANGELOG.md（日本語）を以下に作成しました。プロジェクトの現在のバージョン __version__ = 0.1.0 に対応する初回リリースの変更点を、コードから推測して記載しています。

CHANGELOG.md
-------------

すべての重要な変更はこのファイルに記録します。  
フォーマットは Keep a Changelog (https://keepachangelog.com/ja/) に準拠します。  

Unreleased
----------

（なし）

0.1.0 - 2026-03-28
------------------

Added
- パッケージ基盤
  - パッケージ名 kabusys、バージョン 0.1.0 を追加。パッケージ初期化で公開モジュールを定義（data, strategy, execution, monitoring）。
- 環境設定管理 (kabusys.config)
  - .env および .env.local をプロジェクトルート（.git / pyproject.toml 基準）から自動ロードする仕組みを追加。
  - .env パースの強化：先頭の export キーワード、シングル/ダブルクォート内のエスケープ処理、インラインコメント判定（クォート無し時の # 扱い）に対応。
  - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - Settings クラスを追加し、J-Quants / kabuステーション / Slack / DB パス / 実行環境 (development/paper_trading/live) / ログレベルの取得・検証を提供。必須変数未設定時は ValueError を送出。
  - デフォルト DuckDB/SQLite パス（data/kabusys.duckdb, data/monitoring.db）を提供。
- AI モジュール (kabusys.ai)
  - ニュースNLP スコアリング (news_nlp.score_news)
    - raw_news / news_symbols を集約し、銘柄ごとに最大記事数・文字数でトリムして OpenAI（gpt-4o-mini）の JSON モードで一括スコアリング。
    - バッチ処理（最大 20 銘柄/チャンク）、リトライ（429/ネットワーク/タイムアウト/5xx を指数バックオフでリトライ）、レスポンスバリデーション、±1.0 クリップ、DuckDB への冪等的書き込み（DELETE→INSERT）を実装。
    - テスト容易性のため OpenAI 呼び出し関数をパッチ可能に実装（kabusys.ai.news_nlp._call_openai_api をモック可能）。
    - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）計算ユーティリティ（calc_news_window）を提供。
  - レジーム判定 (regime_detector.score_regime)
    - ETF 1321 の 200 日移動平均乖離（重み 70%）と、マクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定・保存。
    - raw_news からマクロキーワードでフィルタし、OpenAI（gpt-4o-mini）により JSON 出力でマクロセンチメントを取得。API 失敗時はフェイルセーフで macro_sentiment=0.0 を採用。
    - DuckDB を用いた冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）と例外時の ROLLBACK ロギングを実装。
    - OpenAI 呼び出しは news_nlp と独立した実装で、モジュール結合を避ける設計。テスト用に差し替え可能。
- Data モジュール (kabusys.data)
  - カレンダー管理 (calendar_management)
    - market_calendar を参照して営業日判定・前後営業日の計算・期間内営業日取得・SQ 日判定を提供。
    - DB 未取得時は曜日ベース（土日非営業日）でフォールバック。DB 登録あり → DB 優先、未登録日は曜日で補完する一貫した挙動を実装。
    - カレンダー夜間更新ジョブ（calendar_update_job）を実装。J-Quants API から差分取得し冪等保存、バックフィル・健全性チェックを実装。
  - ETL パイプライン (pipeline.ETLResult / etl)
    - ETL 実行結果を表す ETLResult データクラスを追加（取得件数・保存件数・品質問題・エラー等）。
    - 差分更新、バックフィル、品質チェックを想定した設計（jq クライアント・quality モジュールとの連携想定）。
    - _get_max_date 等の DB ユーティリティを追加。
  - jquants_client の公開APIを想定した save / fetch 呼び出しに耐える設計。
- Research モジュール (kabusys.research)
  - factor_research: モメンタム / ボラティリティ / バリューなどの定量ファクター計算を追加。
    - calc_momentum: mom_1m/mom_3m/mom_6m, ma200_dev（200 日 MA 乖離）を計算。データ不足時は None を返す。
    - calc_volatility: 20 日 ATR, ATR 比率, 20 日平均売買代金, 出来高比率などを計算。
    - calc_value: raw_financials から EPS/ROE を取得して PER/ROE を計算（EPS=0 または欠損で None）。
    - 計算は DuckDB SQL ウィンドウ関数中心で実装、外部 API にはアクセスしない設計。
  - feature_exploration: 将来リターン計算 / IC（Spearman ρ） / 統計サマリー / ランキングユーティリティを追加。
    - calc_forward_returns: 複数ホライズンの将来リターンを一度のクエリで取得可能。
    - calc_ic: factor と将来リターンのランク相関（Spearman）を算出。有効レコード < 3 の場合は None。
    - factor_summary: count/mean/std/min/max/median を算出。
    - rank: 同順位は平均ランクを返す安定的ランクラッパー。丸めによる ties 考慮あり。
- 実装上の堅牢化・設計方針（横断）
  - ルックアヘッドバイアス防止: score_news / score_regime 等は datetime.today()/date.today() を内部参照せず、target_date 引数で動作するよう設計。
  - OpenAI 呼び出しは JSON モードを利用し、レスポンスの前後余計なテキストを復元してパースするロバストな実装。
  - API の一時的失敗 (429/ネットワーク/タイムアウト/5xx) に対して指数バックオフでリトライし、最終的にフェイルセーフなデフォルト（例: 0.0）で継続する方針。
  - DuckDB の制約（executemany に空リストを渡せない）に対するガードロジックを追加して互換性を確保。
  - 主要操作は全てログを出力（info/debug/warning/exception）し、エラー時は部分的に保護する（部分失敗時に他コードの既存スコアを保護する等）。

Security
- 環境変数に依存する秘密情報（OpenAI API キー等）については、関数引数で注入可能（api_key 引数）でテストやキー管理に柔軟性を確保。必須が未設定の際は ValueError を送出して失敗させるため、誤動作を未然に防止。

Notes / Usage
- OpenAI API キーは関数引数 api_key を優先して使用し、None の場合は環境変数 OPENAI_API_KEY を参照します。
- 環境変数の主なキー:
  - JQUANTS_REFRESH_TOKEN（必須）
  - KABU_API_PASSWORD（必須）
  - KABU_API_BASE_URL（省略時 http://localhost:18080/kabusapi）
  - SLACK_BOT_TOKEN（必須）
  - SLACK_CHANNEL_ID（必須）
  - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH（デフォルト: data/monitoring.db）
  - KABUSYS_ENV（allowed: development, paper_trading, live。デフォルト: development）
  - LOG_LEVEL（allowed: DEBUG, INFO, WARNING, ERROR, CRITICAL。デフォルト: INFO）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD（=1 で .env 自動ロードを無効化）
- テストの容易性
  - news_nlp/_call_openai_api や regime_detector/_call_openai_api 等はパッチ可能に実装されており、ユニットテストで外部 API 呼び出しをモックできます。

Breaking Changes
- なし（初回リリース）

Acknowledgements
- このリリースは内部仕様コメント（Design/Docs の記述）とコード実装に基づいて構成されています。今後、API やデータモデル変更に伴い項目を更新します。

--- 
注: 日付は現在日（2026-03-28）を使用して記載しています。必要に応じてリリース日や項目を調整してください。