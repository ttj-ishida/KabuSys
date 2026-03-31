KEEP A CHANGELOG
すべての重要な変更はこのファイルに記録します。
このプロジェクトは Semantic Versioning を採用しています。

フォーマットは Keep a Changelog に準拠しています。
https://keepachangelog.com/ja/1.0.0/

## [0.1.0] - 2026-03-31
初回リリース

### 追加
- パッケージ基本
  - パッケージ名: kabusys、バージョン 0.1.0 を公開（src/kabusys/__init__.py）。
  - パッケージ公開 API: data, strategy, execution, monitoring を __all__ でエクスポート。

- 設定 / 環境変数管理 (kabusys.config)
  - .env ファイルおよび環境変数から設定をロードする仕組みを実装。
  - プロジェクトルート検出: .git または pyproject.toml を基準に自動探索（cwd 非依存）。
  - .env パーサ実装: export プレフィックス、クォート内エスケープ、行末コメント処理などに対応。
  - 自動ロードの優先順位: OS 環境変数 > .env.local > .env。
  - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD を追加（テスト用途）。
  - Settings クラスを実装し、アプリケーション設定をプロパティで提供（J-Quants/株API/Slack/DBパス/環境種別/ログレベル等）。
  - 必須環境変数未設定時は ValueError を送出する _require を実装。
  - 環境値のバリデーション（KABUSYS_ENV, LOG_LEVEL の許容値チェック）。

- AI 関連 (kabusys.ai)
  - ニュースセンチメントスコアリング (kabusys.ai.news_nlp)
    - raw_news と news_symbols から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini）の JSON mode で一括スコアリング。
    - バッチ処理、チャンクサイズ制限（最大 20 銘柄／APIコール）、1 銘柄あたりの記事数・文字数上限（トリム）を実装。
    - レスポンスの厳格バリデーション（JSON 抽出、results 配列、code/score 検証、スコアの有限性チェック）。
    - リトライ戦略: レート制限・ネットワーク断・タイムアウト・5xx に対して指数バックオフでリトライ。
    - DuckDB への冪等的な書き込み（DELETE→INSERT）とトランザクション制御（BEGIN/COMMIT/ROLLBACK）。
    - ロックや部分失敗を考慮し、成功した銘柄のみを差し替える実装。
    - 公開関数: score_news(conn, target_date, api_key=None) → 書き込み銘柄数を返す。
    - タイムウィンドウ計算 util: calc_news_window(target_date)（JST基準の前日15:00〜当日08:30 を UTC naive datetime に変換）。
  - 市場レジーム判定 (kabusys.ai.regime_detector)
    - ETF 1321（日経225連動）の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次レジームを判定（'bull' / 'neutral' / 'bear'）。
    - ニュースのフィルタに使用するマクロキーワード群を定義（国内・米国・グローバル指標等）。
    - OpenAI 呼び出しの専用ラッパ、再試行/バックオフ、API 失敗時のフェイルセーフ（macro_sentiment=0.0）を実装。
    - DuckDB の prices_daily/raw_news/market_regime を参照・更新する score_regime(conn, target_date, api_key=None) を提供。
    - レジーム計算はルックアヘッドバイアス回避の設計（target_date 未満のデータのみ参照、datetime.today() を参照しない）。

- Data / ETL / カレンダー (kabusys.data)
  - カレンダー管理 (kabusys.data.calendar_management)
    - JPX カレンダーの夜間差分更新ジョブ calendar_update_job を実装（J-Quants API から差分取得して market_calendar に保存）。
    - 営業日判定ユーティリティを提供: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day。
    - DB 不完全時は曜日ベースのフォールバック（週末を非営業日）を採用し、DB 登録ありの場合は DB 値を優先する一貫したロジック。
    - 最大探索日数上限を設け無限ループを回避（_MAX_SEARCH_DAYS）。
    - バックフィル・健全性チェックを実装（_BACKFILL_DAYS, _SANITY_MAX_FUTURE_DAYS）。
  - ETL パイプライン (kabusys.data.pipeline / etl)
    - ETLResult データクラスを実装して ETL 実行結果を集約（取得件数、保存件数、品質問題、エラー等）。
    - 差分ロジック / 最終日チェック / backfill の方針を明文化。
    - 内部ユーティリティ: テーブル存在チェック、最大日付取得など。
    - ETLResult.to_dict() で品質問題をシリアライズ可能に。

- Research（因子・特徴量解析） (kabusys.research)
  - factor_research
    - モメンタム: 1M/3M/6M リターン、200日 MA 乖離（ma200_dev）を計算する calc_momentum(conn, target_date) を実装。
    - ボラティリティ・流動性: 20日 ATR、相対ATR、20日平均売買代金、出来高比率を計算する calc_volatility(conn, target_date) を実装。
    - バリュー: raw_financials から EPS/ROE を取得して PER/ROE を算出する calc_value(conn, target_date) を実装。
    - DuckDB SQL を多用した実装で、外部APIや発注処理には依存しない。
  - feature_exploration
    - 将来リターンの計算 calc_forward_returns(conn, target_date, horizons) を実装（horizons のバリデーションあり）。
    - IC（スピアマン順位相関）計算 calc_ic(factor_records, forward_records, factor_col, return_col) を実装。データ不足時は None を返す。
    - ランク変換ユーティリティ rank(values)（同順位は平均ランク）。
    - ファクター統計サマリ factor_summary(records, columns)（count/mean/std/min/max/median）。

- データアクセス依存と注意点
  - 全モジュールで DuckDB を前提に設計（型は DuckDB のネイティブ型を想定）。
  - 必要なテーブル例: prices_daily, raw_news, news_symbols, ai_scores, raw_financials, market_calendar など。
  - OpenAI クライアント（openai.OpenAI）を利用。API キーは api_key 引数または環境変数 OPENAI_API_KEY で指定する必要がある。

### 変更 / 挙動
- 全体設計上のポリシー明示
  - ルックアヘッドバイアス回避のため datetime.today()/date.today() を直接参照しない設計（target_date を明示的に渡す）。
  - DB 書き込みは冪等性を考慮（DELETE→INSERT, ON CONFLICT 相当, トランザクション制御）。
  - 外部 API 呼び出し失敗時はフェイルセーフ動作（例: マクロセンチメントやチャンク失敗はスキップして処理続行）。
  - テスト容易性のため、OpenAI 呼び出し点を単純に差し替えられる設計（内部 _call_openai_api の patch を想定）。

### 既知の制約 / 注意点
- OpenAI API のレスポンスは JSON mode を期待するが、実運用では余剰テキストが混入する場合があるため復元ロジックを実装している。とはいえレスポンス形式の不一致はスコア取得失敗の原因となりうる。
- DuckDB の executemany に対する互換性問題に配慮（空リストを渡さない等のワークアラウンドを適用）。
- news_nlp / regime_detector の OpenAI 呼び出しはそれぞれ独立実装（モジュール間でプライベート関数を共有しない設計）。
- 環境自動読み込みはプロジェクトルートの検出に依存するため、配布環境やインストール配置によっては .env 自動ロードがスキップされる場合がある。必要に応じて KABUSYS_DISABLE_AUTO_ENV_LOAD を用いるか明示的に環境を設定すること。

### セキュリティ
- 設定値（API トークン・パスワード等）は環境変数で扱う設計。.env ファイルは UTF-8 で読み込み、読み込み失敗時は警告を出す。

---

将来的には以下を検討:
- strategy / execution / monitoring モジュールの実装詳細（現状はトップレベルでエクスポートのみ）。
- テストカバレッジおよび CI 用のモック/フィクスチャ整備（DuckDB インメモリ、OpenAI API モック等）。
- パフォーマンス改善（大規模データ処理時の SQL チューニングや並列化）。