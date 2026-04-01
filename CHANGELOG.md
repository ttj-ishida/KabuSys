Keep a Changelog
=================

すべての重要な変更点をこのファイルに記録します。  
このプロジェクトは Keep a Changelog の形式に準拠します。

[Unreleased]
------------

- （なし）

[0.1.0] - 2026-04-01
--------------------

Added
- パッケージ初期リリース: kabusys v0.1.0
  - パッケージメタ情報: __version__ = "0.1.0"
  - 公開サブパッケージ/モジュール:
    - kabusys.config: 環境変数・設定管理（Settings クラスを公開）
    - kabusys.ai: ニュースNLP と市場レジーム判定
    - kabusys.data: データ ETL / カレンダー管理 / pipeline 再エクスポート
    - kabusys.research: ファクター計算・特徴量探索ユーティリティ
    - （監視・実行・戦略等の名前空間は __all__ に含むが本差分での主な実装は上記）
- 環境設定機能
  - .env / .env.local 自動読み込み機能（プロジェクトルートは .git または pyproject.toml で検出）
  - 読み込み優先順位: OS 環境変数 > .env.local > .env
  - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD
  - .env パースの堅牢化: export プレフィックス対応、クォート内のエスケープ処理、インラインコメント取り扱い
  - 必須環境変数取得ヘルパー _require と Settings プロパティ群
    - 必須環境変数（例）: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DB パスデフォルト: DUCKDB_PATH="data/kabusys.duckdb", SQLITE_PATH="data/monitoring.db"
    - 監視設定（PID ファイル、閾値）やログレベル / 環境モード（development/paper_trading/live）検証

- AI モジュール（OpenAI 統合）
  - kabusys.ai.news_nlp
    - raw_news と news_symbols を集約して銘柄ごとのニュースを作成
    - gpt-4o-mini（JSON Mode）を用いたバッチセンチメント評価
    - バッチサイズ、記事数・文字数トリム、再試行（429/ネットワーク/タイムアウト/5xx の指数バックオフ）を実装
    - レスポンス検証（JSON 抽出、results 配列、コード/スコア整合性、スコアの ±1.0 クリップ）
    - ai_scores テーブルへの冪等書き込み（該当 code の DELETE → INSERT）
    - 外部化されたテストフック: _call_openai_api を patch 可能
    - 公開関数: score_news(conn, target_date, api_key=None)
    - タイムウィンドウ計算ユーティリティ: calc_news_window(target_date)
    - 設計原則: datetime.today() を参照しない（ルックアヘッドバイアス回避）
  - kabusys.ai.regime_detector
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を組み合わせた日次市場レジーム判定
    - OpenAI 呼び出しは独立実装（news_nlp と共有せずモジュール結合を低減）
    - マクロキーワードで raw_news をフィルタし、最大 20 件を LLM に送信
    - 再試行/フォールバック: API 失敗時は macro_sentiment = 0.0、ログ出力、リトライ実装
    - market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）
    - 公開関数: score_regime(conn, target_date, api_key=None)

- データプラットフォーム関連
  - kabusys.data.pipeline
    - ETLResult dataclass を導入（取得数／保存数／品質問題／エラー一覧等を集計）
    - 差分取得・バックフィル設計のための定数とユーティリティ実装（最小データ日付、backfill_days 等）
  - kabusys.data.etl
    - pipeline.ETLResult を再エクスポート（外部 API 用の安定インターフェース）
  - kabusys.data.calendar_management
    - JPX カレンダー管理: market_calendar テーブル参照・更新用ユーティリティ
    - 営業日判定関数群:
      - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day
    - カレンダーが未取得の場合は曜日ベースのフォールバック（週末除外）
    - calendar_update_job: J-Quants から差分取得して冪等保存（バックフィル、健全性チェックを実装）
    - 最大探索範囲制限により無限ループを防止（_MAX_SEARCH_DAYS など）
    - jquants_client との連携を想定（fetch_market_calendar, save_market_calendar 呼び出し）

- 研究（Research）ユーティリティ
  - kabusys.research.factor_research
    - モメンタム: mom_1m/mom_3m/mom_6m、ma200_dev（200日移動平均乖離）
    - ボラティリティ／流動性: 20日 ATR（atr_20, atr_pct）、20日平均売買代金、出来高比率
    - バリュー: per（EPS が 0 または欠損時は None）、roe（raw_financials から最新値）
    - DuckDB SQL を利用した効率的な窓関数実装
    - 設計原則: 本番発注 API にアクセスしない（読み取り専用）
  - kabusys.research.feature_exploration
    - 将来リターン計算: calc_forward_returns（任意ホライズン、入力検証あり）
    - IC（Information Coefficient）計算: calc_ic（Spearman ランク相関）
    - ランク変換ユーティリティ: rank（同順位は平均ランク）
    - 統計サマリー: factor_summary（count/mean/std/min/max/median）
    - 外部ライブラリに依存せず標準ライブラリのみで実装

Changed
- n/a （初回リリースのため変更履歴はなし）

Fixed
- n/a （初回リリースのため修正履歴はなし）

Notes / 設計上の重要ポイント
- ルックアヘッドバイアス対策:
  - 各 AI / 研究処理は target_date 引数を必須にし、datetime.today() や date.today() を内部で参照しない方針
  - prices_daily 等のクエリは target_date 未満／以前の排他条件を明示
- フェイルセーフ:
  - OpenAI API 呼び出し失敗時は処理を継続する（デフォルトのフォールバック値を使用し例外送出を回避）
  - DB 書き込みはトランザクションで行い、例外時は ROLLBACK を試みる
- テスト容易性:
  - OpenAI 呼び出し用の内部関数（_call_openai_api）を patch 可能にしてユニットテストを容易化
- DuckDB 互換性:
  - executemany に空パラメータを渡さない等、DuckDB のバージョン差異に配慮した実装
- ロギング:
  - 各処理は詳細な info/debug/warning ログを出力するよう実装

必要な環境変数（例）
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- SLACK_BOT_TOKEN（必須）
- SLACK_CHANNEL_ID（必須）
- OPENAI_API_KEY（score_news / score_regime 実行時に必要、引数で上書き可能）
- DUCKDB_PATH / SQLITE_PATH / PID_FILE_PATH / CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT / KABUSYS_ENV / LOG_LEVEL

既知の制限・今後の改善候補
- ai_score と sentiment_score は現フェーズで同値として保存しているが、将来的に別計算に分離可能
- 一部の機能（例: 市場注文実行、監視モジュールなど）は外部に依存するか、今回の差分では実装のカバー範囲外
- エラー分類・品質チェックの運用ポリシーは ETL の呼び出し側で柔軟に扱う想定（Fail-Fast ではなく収集型）

----

この CHANGELOG はコードベースの実装内容から推測して作成しています。実際の利用やデプロイにあたっては README 等のドキュメントやテストで挙動を確認してください。