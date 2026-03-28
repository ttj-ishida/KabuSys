CHANGELOG
=========

すべての注目すべき変更点はこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠し、セマンティックバージョニングを使用します。

0.1.0 - 2026-03-28
-----------------

初回公開リリース。

Added
- パッケージ初期化:
  - kabusys パッケージの __version__ を "0.1.0" に設定。
  - パッケージレベルで data/strategy/execution/monitoring を公開（__all__）。

- 設定管理:
  - 環境変数管理モジュールを追加（kabusys.config）。
  - .env / .env.local ファイルの自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml を探索して決定）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化サポート。
  - .env パーサは export プレフィックス、シングル/ダブルクォート内のエスケープ、行末コメントルール等に対応。
  - Settings クラスを提供し、J-Quants、kabuステーション、Slack、データベースパス、実行環境（development/paper_trading/live）やログレベルの解決ロジックを実装。未設定の必須変数は明確な ValueError を投げる。

- AI / ニュース NLP:
  - kabusys.ai.news_nlp モジュールを追加。
    - raw_news / news_symbols を参照して銘柄ごとの記事を集約し、OpenAI（gpt-4o-mini）のJSONモードで銘柄別センチメント（-1.0〜1.0）を取得。
    - バッチサイズ、記事数・文字数トリム、JSONレスポンスのバリデーション、スコアのクリップ等を実装。
    - 429, ネットワーク断・タイムアウト・5xx に対する指数バックオフリトライ。
    - DuckDB 互換性のため executemany に空リストを与えない保護処理を実装。
    - テスト用に内部の API 呼び出し関数を patch しやすい設計（_call_openai_api を差し替え可能）。
  - kabusys.ai.regime_detector モジュールを追加。
    - ETF(1321) の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定。
    - マクロ記事の抽出キーワード、OpenAI 呼び出し、リトライ/フェイルセーフ（API 失敗時は macro_sentiment=0.0）を実装。
    - DB 書込みは冪等に BEGIN / DELETE / INSERT / COMMIT の順で行う。失敗時は ROLLBACK を試みる。
  - kabusys.ai.__init__ で score_news を公開。

- データ関連:
  - kabusys.data.pipeline / etl / calendar_management など ETL / カレンダー管理の基礎を実装。
    - ETLResult データクラス（ETL の取得数 / 保存数 / 品質問題 / エラー等を格納）を公開。
    - pipeline: 差分更新、バックフィル、品質チェック（quality モジュールを想定）など設計方針の基礎実装。
    - calendar_management:
      - market_calendar を使った営業日判定ロジック（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）。
      - カレンダー未取得時は曜日ベース（土日）でフォールバックする一貫した振る舞い。
      - calendar_update_job により J-Quants API から差分取得 → 保存（バックフィル、健全性チェックを含む）を実装。
    - jquants_client 経由での保存処理呼び出しを前提とした設計。

- リサーチ / ファクター:
  - kabusys.research パッケージを追加。以下を実装・公開:
    - factor_research.calc_momentum: 1M/3M/6M リターン、MA200 乖離（ma200_dev）。
    - factor_research.calc_volatility: 20日 ATR、相対ATR、平均売買代金、出来高比率等。
    - factor_research.calc_value: PER, ROE（raw_financials から最新の財務データを取得）等。
    - feature_exploration.calc_forward_returns: 将来リターン（任意ホライズン）を一括取得する汎用実装。
    - feature_exploration.calc_ic: スピアマンランク相関（IC）計算。
    - feature_exploration.rank: 同順位は平均ランクで扱うランク変換ユーティリティ（丸め対策あり）。
    - feature_exploration.factor_summary: カラムごとの基本統計量（count/mean/std/min/max/median）を計算。
  - 研究用 API は DuckDB 接続を受け取り prices_daily / raw_financials などの DB テーブルのみを参照する設計（実際の発注等にはアクセスしない）。

Changed
- （初リリースのため該当なし）

Fixed
- （初リリースのため該当なし）

Deprecated
- （初リリースのため該当なし）

Removed
- （初リリースのため該当なし）

Security
- OpenAI API キーは引数で注入可能（テスト容易性）かつ環境変数 OPENAI_API_KEY もサポート。未設定時は ValueError を発生させ明示的に扱う。

注記（実装上の重要点 / 設計意図）
- ルックアヘッドバイアス回避:
  - AI モジュール（news_nlp, regime_detector）およびリサーチモジュールは datetime.today()/date.today() を内部参照しない設計。すべて明示的な target_date を引数で受ける。
- フェイルセーフ:
  - LLM の呼び出し失敗時は例外を上位に投げずフォールバック値（例: macro_sentiment=0.0、スコア未取得のスキップ）で継続する箇所がある。DB 書き込み失敗時は適切に ROLLBACK を試みる。
- DuckDB 互換性:
  - DuckDB の executemany に空リストを渡すとエラーとなる点に対応するガードあり。
- テスト支援:
  - AI 呼び出し箇所は内部関数（_call_openai_api）を patch して差し替えやすい実装になっている。

今後の予定（例）
- strategy / execution / monitoring の実装拡張（本リポジトリ内で参照のみのコンポーネントあり）。
- 追加の品質チェックルールと監視パイプラインの強化。
- OpenAI 呼び出しのロギングやメトリクス計測の拡充。

--- 

（注）本 CHANGELOG は提供されたソースコードからの推測に基づいて作成しています。実際のリリースノートや運用ルールに合わせて修正してください。