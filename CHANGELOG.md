# Changelog

すべての重要な変更をこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠しています。  
公開リリース毎にセクションを追加してください。

## [Unreleased]
- (なし)

## [0.1.0] - 2026-03-28
初回リリース。日本株自動売買システムのコア機能群を実装しました。主な追加点をカテゴリ別にまとめます。

### Added
- パッケージ基盤
  - kabusys パッケージの公開インターフェースを追加（__version__ = 0.1.0）。
  - サブモジュール群をエクスポート: data, research, ai, execution, strategy, monitoring（__all__）。

- 設定・環境変数管理（kabusys.config）
  - .env / .env.local 自動読み込み機能を実装。読み込み優先順位は OS 環境変数 > .env.local > .env。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
  - .env パーサーを実装（コメント、export プレフィックス、クォート内のエスケープ、インラインコメントの扱い等に対応）。
  - 既存 OS 環境変数を保護する protected 機構を実装（.env の上書きを防止）。
  - Settings クラスを追加し、以下のプロパティを提供:
    - jquants_refresh_token, kabu_api_password, kabu_api_base_url（デフォルト: http://localhost:18080/kabusapi）
    - slack_bot_token, slack_channel_id
    - duckdb_path（デフォルト data/kabusys.duckdb）, sqlite_path（デフォルト data/monitoring.db）
    - env（development / paper_trading / live の検証）, log_level（DEBUG/INFO/WARNING/ERROR/CRITICAL の検証）
    - is_live / is_paper / is_dev のヘルパー

- データ基盤（kabusys.data）
  - market_calendar を扱う calendar_management モジュール追加
    - 営業日判定: is_trading_day, is_sq_day
    - 翌営業日／前営業日検索: next_trading_day, prev_trading_day（探索上限 _MAX_SEARCH_DAYS を設け安全化）
    - 期間内の営業日列挙: get_trading_days
    - JPX カレンダーを J-Quants から差分取得して保存する夜間ジョブ: calendar_update_job（バックフィル・健全性チェックを含む）
    - market_calendar 未取得時は曜日ベースでフォールバック（週末を休場とみなす）
  - ETL パイプライン基盤（kabusys.data.pipeline）
    - ETLResult データクラスを実装（取得件数、保存件数、品質問題、エラー集約、ヘルパー to_dict 等）
    - 差分取得／バックフィル／品質チェック設計に関するユーティリティ（テーブル存在確認、最大日付取得 など）
  - data.etl で ETLResult を再エクスポート

- AI（kabusys.ai）
  - ニュース NLP（kabusys.ai.news_nlp）
    - raw_news / news_symbols を集約して銘柄ごとのニュースを OpenAI（gpt-4o-mini）でスコアリングし ai_scores へ書き込み
    - スコアリング対象ウィンドウは JST 前日 15:00 ～ 当日 08:30（UTC に変換して DB クエリを実施）
    - チャンク処理（最大 _BATCH_SIZE: 20 銘柄/コール）、1銘柄あたりの記事数上限・文字数トリム対策
    - JSON Mode 出力のバリデーションと堅牢なパース（余分な前後テキストの復元処理含む）
    - エラー（429・ネットワーク断・タイムアウト・5xx）に対する指数バックオフリトライ、失敗時は部分的スキップで継続（フェイルセーフ）
    - DuckDB の executemany 空リスト制約への対応（空パラメータでの INSERT/DELETE を回避）
    - score_news API: スコアを書き込んだ銘柄数を返す。API キーは引数 or 環境変数 OPENAI_API_KEY から解決
    - テストしやすさのため _call_openai_api の差し替えを想定（unittest.mock.patch を利用可能）
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（日経225連動）の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次で market_regime に書き込み
    - マクロニュースは news_nlp の calc_news_window と raw_news からフィルタ取得（マクロキーワード群を用いる）
    - OpenAI 呼び出しのリトライ・フェイルセーフ（失敗時 macro_sentiment=0.0）
    - レジームスコア合成とラベル付与（bull / neutral / bear）
    - DB 書き込みは冪等（BEGIN / DELETE / INSERT / COMMIT）、失敗時は ROLLBACK を実行
    - テスト用に _call_openai_api を差し替え可能

- リサーチ（kabusys.research）
  - factor_research: ファクター計算群を実装
    - calc_momentum: 1M/3M/6M リターン、200日 MA 乖離（データ不足時は None）
    - calc_volatility: 20日 ATR、ATR 比率、20日平均売買代金、出来高比率
    - calc_value: raw_financials から最新財務情報を取得し PER/ROE を計算
    - すべて DuckDB (prices_daily / raw_financials) のみを参照し外部 API にはアクセスしない
  - feature_exploration: 特徴量評価ユーティリティを実装
    - calc_forward_returns: 指定ホライズンの将来リターンを LEAD を用いて一括取得（horizons の検証あり）
    - calc_ic: ランク相関（Spearman ρ）を実装（欠損・同順位処理を含む）
    - rank: 同順位は平均ランクを返す実装（丸めで ties を安定化）
    - factor_summary: count/mean/std/min/max/median を計算

### Changed
- （初版リリースにつき過去の変更なし）  
- モジュール設計上の一貫性改善:
  - AI モジュールはテスト容易性のため内部の OpenAI 呼び出しを置換可能に設計
  - ルックアヘッドバイアス対策として datetime.today()/date.today() を分析ロジックの内部参照に使用しない設計を徹底

### Fixed
- （初版リリースにつき過去の修正なし）  
- 実運用を想定した堅牢化:
  - JSON パースや API エラー時にプロセス全体が停止しないようフォールバック値を用意
  - DuckDB のバージョン差分（executemany の空リスト等）に対応する安全策を導入

### Security
- OpenAI と各 API へのキーは環境変数で管理（OPENAI_API_KEY, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN 等）。キー未設定時は明示的に ValueError を発生させ処理側に通知します。
- .env 自動読み込みはデフォルトで有効。CI / テスト環境等で無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

### Notes / Migration / Usage Tips
- デフォルトの DuckDB パスは data/kabusys.duckdb、SQLite（監視用）は data/monitoring.db。必要に応じて環境変数 DUCKDB_PATH / SQLITE_PATH で変更可能。
- OpenAI モデルは現時点で gpt-4o-mini を使用。大量コール時は料金・レート制限に注意してください。
- news_nlp のバッチサイズ・トリム設定 (_BATCH_SIZE, _MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK) は実運用に合わせて調整可能です。
- ETLResult と各関数は DuckDB 接続を受け取り DB に対して副作用を持ちます。テスト時はモック DB や patch を活用してください。
- 研究系関数群は外部ネットワークアクセスを行いません。リサーチ環境で安全に利用可能です。

---

今後の予定（例）
- apis/clients の抽象化によるモック容易化・DI サポート強化
- 知見に基づくファクター追加・チューニング
- monitoring / execution モジュールの実装充実（現在はエクスポート名のみ用意）

README や各モジュールのドキュメントを参照して導入・設定を行ってください。