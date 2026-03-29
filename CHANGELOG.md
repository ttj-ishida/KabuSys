# Changelog

すべての注目すべき変更点はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠しています。

最新リリース
- リリース日は YYYY-MM-DD（ここではコードベースの現状を 0.1.0 として記載しています）

なお、この CHANGELOG はコード内容から推測して作成しています（実際のコミット履歴ではありません）。

Unreleased
---------
- （現在未リリースの変更はありません）

[0.1.0] - 2026-03-29
-------------------
Added
- 基本パッケージ初期実装を追加
  - パッケージルート: kabusys/__init__.py にバージョン情報 __version__ = "0.1.0" を追加。

- 環境設定・自動 .env ロード機能（kabusys.config）
  - Settings クラスを追加し、アプリ設定を環境変数から取得するプロパティを提供。
    - jquants_refresh_token, kabu_api_password, kabu_api_base_url, slack_bot_token,
      slack_channel_id, duckdb_path, sqlite_path, env, log_level, is_live/is_paper/is_dev など。
  - 自動 .env ロード:
    - プロジェクトルート（.git または pyproject.toml を基準）を検出して .env/.env.local を読み込み。
    - 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
    - .env パーサは export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント処理に対応。
    - .env.local は .env の上から上書き（ただし OS 環境変数は保護）する動作を実装。
  - 入力検証:
    - KABUSYS_ENV（development/paper_trading/live）と LOG_LEVEL（DEBUG/INFO/...）の値検証を実装。
  - 必須項目未設定時は明示的な ValueError を投げる（ユーザに .env.example の作成を促す）。

- AI 関連: ニュースNLP と レジーム判定（kabusys.ai）
  - news_nlp.score_news:
    - raw_news と news_symbols を集約し、銘柄ごとに OpenAI（gpt-4o-mini）へバッチ送信してセンチメント（ai_score）を算出。
    - JST 時間ウィンドウの計算（前日 15:00 JST ～ 当日 08:30 JST を UTC に変換）を calc_news_window で提供。
    - バッチ処理（最大 20 銘柄／コール）、各銘柄は最大記事数・最大文字数でトリム。
    - 429/ネットワーク断/タイムアウト/5xx に対して指数バックオフでリトライし、API 応答は JSON mode を想定してパース・検証。
    - レスポンス検証: results 配列・code/score の存在確認、未知コードは無視、スコアは ±1 にクリップ。
    - DuckDB への書き込みは部分的に冪等（該当コードのみ DELETE → INSERT）で実施し、失敗時はトランザクションを ROLLBACK。
    - テスト用に _call_openai_api をパッチできる設計。
  - regime_detector.score_regime:
    - ETF 1321（日経225連動）200日移動平均乖離（重み 70%）と、マクロニュースの LLM センチメント（重み 30%）を合成して
      市場レジーム（bull/neutral/bear）を判定し market_regime テーブルへ書き込み。
    - マクロニュースは kabusys.ai.news_nlp.calc_news_window と raw_news からマクロキーワードで抽出。
    - OpenAI 呼び出しは独立実装で、リトライ・5xx 判定・JSON パース失敗時は macro_sentiment=0.0 としてフェイルセーフ継続。
    - レジームスコア合成・閾値判定・トランザクション（BEGIN/DELETE/INSERT/COMMIT）を実装。

- 研究（Research）モジュール（kabusys.research）
  - factor_research:
    - calc_momentum: 1M/3M/6M リターンと 200 日 MA 乖離（ma200_dev）を計算。
    - calc_volatility: ATR（20日）、相対 ATR、20日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials から直近財務を取り出し PER/ROE を計算。
    - いずれも DuckDB の prices_daily / raw_financials テーブルのみ参照し、データ不足時は None を返す設計。
  - feature_exploration:
    - calc_forward_returns: 任意ホライズンの将来リターン（デフォルト [1,5,21]）を計算。ホライズンは検証済み（1〜252）。
    - calc_ic: スピアマンランク相関（IC）を計算。データ不足（有効レコード < 3）の場合は None。
    - rank / factor_summary: ランク変換（同順位は平均ランク）および基本統計量（count/mean/std/min/max/median）を計算。
  - kabusys.research.__init__ で主要関数を再エクスポート（便利な API）。

- データ基盤（kabusys.data）
  - calendar_management:
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を実装。
    - market_calendar テーブルの有無に応じて DB 値優先、未登録日は曜日ベースのフォールバックを行う設計。
    - next/prev_trading_day は検索上限（_MAX_SEARCH_DAYS）を設けて無限ループを防止。
    - calendar_update_job: J-Quants API（jquants_client）からカレンダー差分を取得し、バックフィル（直近 _BACKFILL_DAYS 日）・健全性チェックを行った上で保存するバッチ処理を実装。
  - pipeline / etl:
    - ETLResult データクラスを追加し、ETL 結果（取得件数・保存件数・品質チェック結果・エラー等）を構造化して返却可能に。
    - data.etl で ETLResult を公開再エクスポート。
  - 各所で DuckDB 用の互換性配慮（executemany の空リスト回避等）を実装。

- 内部設計上の安全機構・テスト支援
  - ルックアヘッドバイアス防止: datetime.today()/date.today() を直接参照しない設計（全関数は target_date で動作）。
  - API 呼び出し失敗時はフェイルセーフ（スコア 0.0 または処理スキップ）で続行する方針。
  - テスト容易性のため、OpenAI 呼び出しを行う内部関数（_call_openai_api）を unittest.mock.patch で差し替え可能にしている箇所あり。
  - 各種トランザクションは冪等性を保つ実装（DELETE→INSERT、ON CONFLICT 等を利用する前提）。

Changed
- なし（初回リリース想定）

Fixed
- なし（初回リリース想定）

Security
- 環境変数の取り扱いに注意:
  - 自動 .env ロードは OS 環境変数を保護（.env/.env.local が OS 環境変数を上書きしない）する実装。
  - OpenAI API キーや各種トークンは Settings の必須プロパティとして扱い、未設定時は明示的なエラーを出す。

Notes / Known limitations
- 一部モジュールは外部依存（DuckDB、OpenAI SDK、jquants_client 等）を前提としており、
  実行には適切な環境（テーブルスキーマ、API キー、ネットワーク）が必要です。
- news_nlp / regime_detector の OpenAI 呼び出しは JSON mode を利用する想定だが、
  実際のモデル挙動により余計なテキストが混入する場合があるため、パース復元ロジックを追加。
- ETL・calendar の細かい動作（jquants_client の実装依存部、保存方法の詳細）は jquants_client 側の挙動に依存します。
- この CHANGELOG はコードの状態から推測して作成したため、実際のリポジトリのコミットメッセージとは差異がある可能性があります。

--- 

参考: 主な公開関数 / クラス
- kabusys.config.Settings (settings)
- kabusys.ai.news_nlp.score_news, calc_news_window
- kabusys.ai.regime_detector.score_regime
- kabusys.research.calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary, rank
- kabusys.data.calendar_management.is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day / calendar_update_job
- kabusys.data.pipeline.ETLResult
- kabusys.data.etl.ETLResult（再エクスポート）

今後の案（作業候補）
- strategy / execution / monitoring の具体的実装を追加して取引フローを完結させる。
- 単体テスト・統合テストの追加（OpenAI 呼び出しのモック化、DuckDB テスト用フィクスチャなど）。
- ドキュメント（API 使用例、DB スキーマ定義、運用手順）の整備。