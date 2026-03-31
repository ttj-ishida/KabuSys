CHANGELOG
=========
すべての注目すべき変更はこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠し、セマンティックバージョニングを採用します。  
https://keepachangelog.com/ja/ と https://semver.org/lang/ja/ を参照してください。

[0.1.0] - 2026-03-31
-------------------

Added
- 初回公開: kabusys パッケージを追加。
  - パッケージ構成（主要モジュール）
    - kabusys.config: 環境変数／設定管理
    - kabusys.ai: ニュース NLP と市場レジーム判定 (news_nlp, regime_detector)
    - kabusys.data: データ ETL／カレンダー管理／パイプライン
    - kabusys.research: ファクター計算・特徴量探索
    - kabusys.research.*: momentum/value/volatility 等の計算関数群
    - kabusys.data.pipeline: ETLResult dataclass（型付き結果の集約）
    - kabusys.data.etl: ETLResult の再エクスポート

- 環境設定 (kabusys.config)
  - .env ファイルおよび OS 環境変数から設定を自動読み込み（プロジェクトルートを .git または pyproject.toml から検出）。
  - 読み込み順序: OS 環境 > .env.local（上書き可）> .env（上書き不可）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能。
  - .env のパース機能を実装（export プレフィックス、シングル／ダブルクォート、エスケープ、インラインコメント処理に対応）。
  - Settings クラスを提供し、以下のキーをプロパティ経由で取得:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH（デフォルト data/kabusys.duckdb）、SQLITE_PATH（デフォルト data/monitoring.db）
    - KABUSYS_ENV（development/paper_trading/live の検証）、LOG_LEVEL（DEBUG/INFO/... の検証）
    - is_live / is_paper / is_dev のブール判定

- ニュース NLP / AI スコアリング (kabusys.ai.news_nlp)
  - score_news(conn, target_date, api_key=None):
    - 対象ウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST（UTC に変換して DB を検索）
    - raw_news と news_symbols を結合し、銘柄ごとに記事を集約（1 銘柄あたり最大記事数・文字数でトリム）
    - OpenAI (gpt-4o-mini) に JSON mode でバッチ送信（最大 20 銘柄／バッチ）
    - レート制限・タイムアウト・5xx 等に対して指数バックオフでリトライ
    - レスポンスのバリデーションとスコア ±1.0 クリップ
    - 成功した銘柄のみ ai_scores テーブルへ置換的に書き込み（DELETE → INSERT、部分失敗でも既存スコアを保護）
  - 補助:
    - calc_news_window(target_date) によりウィンドウを計算
    - テスト容易性のため _call_openai_api をパッチ差し替え可能
    - DuckDB 0.10 の executemany の制約（空リスト不可）に配慮した実装

- 市場レジーム判定 (kabusys.ai.regime_detector)
  - score_regime(conn, target_date, api_key=None):
    - ETF 1321 の直近 200 日の終値から MA200 乖離を計算（look-ahead バイアス防止のため target_date 未満のデータのみ使用）
    - マクロ経済ニュース（タイトル）を抽出（マクロキーワードでフィルタ、最大 20 件）
    - OpenAI によりマクロセンチメントを -1.0～1.0 でスコア化（API失敗時は 0.0 にフォールバック）
    - MA（70%）とマクロセンチメント（30%）を合成して regime_score（クリップ）を算出し、閾値で bull/neutral/bear を判定
    - market_regime テーブルへ冪等的に書き込み（BEGIN / DELETE / INSERT / COMMIT）
  - 冗長な失敗時に例外を投げず継続するフェイルセーフ設計（ただし DB 書き込み失敗は上位へ伝播）

- データカレンダー / 管理 (kabusys.data.calendar_management)
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を提供
  - market_calendar テーブルが無い場合は曜日ベース（土日休）でフォールバック
  - DB 登録値があれば優先、未登録日は曜日フォールバックで一貫した結果を返す設計
  - calendar_update_job(conn, lookahead_days=90):
    - J-Quants API から差分取得して market_calendar を冪等保存
    - バックフィル（直近 _BACKFILL_DAYS）は必ず再フェッチ
    - 健全性チェック（極端な future 値の検出）を実装
    - jquants_client.fetch_market_calendar / save_market_calendar を利用（外部クライアント）

- ETL / パイプライン (kabusys.data.pipeline)
  - ETLResult dataclass を導入（取得件数、保存件数、品質問題、エラー一覧等を集約）
  - _get_max_date / _table_exists 等のユーティリティを実装
  - 差分更新・バックフィル・品質チェックの方針を実装に反映（jquants_client / quality モジュールと連携想定）

- リサーチ（因子計算） (kabusys.research)
  - calc_momentum(conn, target_date): mom_1m/mom_3m/mom_6m / ma200_dev を計算
  - calc_volatility(conn, target_date): atr_20 / atr_pct / avg_turnover / volume_ratio を計算
  - calc_value(conn, target_date): per / roe（raw_financials から latest を取得）
  - feature_exploration:
    - calc_forward_returns(conn, target_date, horizons=[1,5,21] デフォルト)
    - calc_ic(factor_records, forward_records, factor_col, return_col): スピアマン順位相関（IC）を計算
    - rank(values): 同順位は平均ランクを割り当てる実装
    - factor_summary(records, columns): count/mean/std/min/max/median を計算
  - いずれの関数も look-ahead バイアス回避、DuckDB SQL を主体とした設計

Internal / Implementation notes
- OpenAI 呼び出しは chat.completions.create を利用し、response_format={"type": "json_object"} を指定（JSON mode）。
- API 呼び出し失敗時のリトライ戦略、5xx と 4xx の扱いを明確化。
- JSON レスポンスの柔軟なパース（前後に余計なテキストが混入するケースへの復元ロジック）。
- DuckDB に対する互換性考慮（executemany の空引数回避、日付型変換ユーティリティ等）。
- テスト容易性のため _call_openai_api のパッチ差し替えを想定。

Known limitations / 注意事項
- OpenAI API キー（OPENAI_API_KEY）は必須（各 API 呼び出しで引数注入可能）。
- AI スコアリングは外部 API に依存するため、API の利用制限やコストに影響を受ける。
- 一部の DB 書き込みは冪等化されているが、例外発生時は呼び出し元でのリトライ管理が必要。
- .env パーサは一般的な形式に対応するが、極端に非標準なフォーマットはサポート外。
- 現バージョンでは PBR・配当利回りなど一部ファクターは未実装（calc_value 参照）。
- calendar_update_job / ETL の一部機能は jquants_client / quality の実装依存。

セマンティックバージョニングと今後の方針
- 今後の追加機能（発注／実行モジュール、監視／Slack 通知、さらに細かい品質チェック等）はマイナー／パッチの規則に従ってバージョン管理します。
- 破壊的変更はメジャーを上げて明示します。

（以上）