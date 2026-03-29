Keep a Changelog — kabusys

すべての重要な変更はこのファイルに記録します。  
このプロジェクトはセマンティックバージョニングに従います（https://semver.org/）。

## [0.1.0] - 2026-03-29
初回公開リリース。日本株のデータ取得・前処理・リサーチ・AI スコアリング・市場レジーム判定を行うモジュール群を追加。

### 追加
- 基本パッケージ構成
  - パッケージ名: kabusys、バージョン 0.1.0。
  - __all__ で data, strategy, execution, monitoring を公開。

- 設定管理（kabusys.config）
  - .env ファイルおよび環境変数から設定を自動読み込み（プロジェクトルートは .git または pyproject.toml から探索）。
  - 読み込み優先度: OS 環境 > .env.local > .env。
  - 自動ロードを無効化するフラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - .env 解析の堅牢化（export 対応、クォート内のエスケープ処理、インラインコメント処理）。
  - 必須設定取得ユーティリティ _require と Settings クラスを提供。
  - 主な環境変数:
    - JQUANTS_REFRESH_TOKEN（必須）
    - KABU_API_PASSWORD（必須）
    - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
    - SLACK_BOT_TOKEN（必須）
    - SLACK_CHANNEL_ID（必須）
    - DUCKDB_PATH / SQLITE_PATH（デフォルトパスを提供）
    - KABUSYS_ENV（development / paper_trading / live の検証）
    - LOG_LEVEL（ログレベルの検証）

- AI 関連（kabusys.ai）
  - news_nlp.score_news(conn, target_date, api_key=None)
    - raw_news と news_symbols を集約し、OpenAI（gpt-4o-mini）へバッチ送信して銘柄別センチメントを算出し ai_scores テーブルへ保存。
    - バッチ処理、最大バッチサイズ 20、1 銘柄当たり記事上限と文字数トリム、レスポンスの厳密な JSON 検証。
    - ネットワーク/429/タイムアウト/5xx に対する指数的バックオフとリトライを実装。失敗時は該当チャンクをスキップして継続（フェイルセーフ）。
    - 取得スコアは ±1.0 にクリップ。DuckDB の executemany の仕様差異を吸収する保護処理あり。

  - regime_detector.score_regime(conn, target_date, api_key=None)
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とニュース（news_nlp のウィンドウ抽出によるマクロ記事、LLM によるセンチメント、重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定し market_regime テーブルへ冪等書き込み。
    - LLM 呼び出しのリトライ、API 失敗時は macro_sentiment=0.0 にフォールバック。
    - ルックアヘッドバイアス対策（datetime.today() を直接参照しない、DB クエリに date < target_date の排他条件など）。

- データ（kabusys.data）
  - calendar_management
    - JPX カレンダー管理、market_calendar をベースに is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を提供。
    - market_calendar 未取得時は曜日ベースのフォールバック（週末を休日扱い）。
    - calendar_update_job による J-Quants からの差分取得と冪等保存（バックフィルと健全性チェックを含む）。
  - pipeline / etl
    - ETLResult データクラス（ETL の収集・保存・品質チェック結果を格納）を公開。
    - jquants_client と quality モジュールを組み合わせた差分更新・保存・品質チェック方針を反映。
    - 差分更新ロジック、バックフィル日数、最小データ日などの定数を導入。

- リサーチ（kabusys.research）
  - factor_research
    - calc_momentum(conn, target_date)：1M/3M/6M リターン、ma200_dev を計算。
    - calc_volatility(conn, target_date)：20 日 ATR（atr_20、atr_pct）、平均売買代金、出来高比を計算。
    - calc_value(conn, target_date)：raw_financials からの EPS / ROE を使って PER と ROE を計算。
    - 設計では DB（prices_daily / raw_financials）のみ参照、本番注文 API 等にはアクセスしない。
  - feature_exploration
    - calc_forward_returns(conn, target_date, horizons=None)：指定ホライズンの将来リターンを計算。
    - calc_ic(factor_records, forward_records, factor_col, return_col)：スピアマンランク相関（IC）を計算。
    - rank(values)：同順位を平均ランクにするランク化ユーティリティ。
    - factor_summary(records, columns)：count/mean/std/min/max/median を計算。
  - data.stats の zscore_normalize を再公開（research パッケージ経由で利用可能）。

### 変更（設計上の決定・方針）
- ルックアヘッドバイアス防止を全ての分析/スコア処理で明示的に考慮（datetime.today()/date.today() 参照を抑制）。
- OpenAI 呼び出しは JSON mode（response_format={"type": "json_object"}）を利用し、レスポンスパースは厳密に行う実装に統一。
- モジュール間でプライベート関数を共有しない設計（_call_openai_api などを各モジュールで独自実装）により結合度を低減。
- DuckDB の実装差異（executemany の空リストなど）に対応する処理を追加。

### 修正（バグ修正的な注意点）
- API エラーやレスポンスパース失敗時に例外を投げずフォールバックすることで ETL やスコアリングの一部失敗がシステム全体を止めないようにしている（ログ出力で検知可能）。

### 既知の制約 / 注意点
- OpenAI API キー（OPENAI_API_KEY）は各 AI 関数で必須。未設定時は ValueError を送出。
- news_nlp は各チャンクで最大 20 銘柄を処理し、1 銘柄あたり記事数・文字数上限を持つ（トークン肥大化対策）。
- DuckDB を前提としたテーブル構造（prices_daily, raw_news, news_symbols, ai_scores, raw_financials, market_regime, market_calendar など）が必要。
- calendar_update_job は J-Quants クライアント（kabusys.data.jquants_client）に依存する。外部 API 呼び出しの失敗時は 0 を返して安全に終了する。
- JSON レスポンスの前後ノイズに対しては最外の {} を抽出して復元する試みをするが、完全な保証はない。
- 一部設計は将来的な拡張（PBR・配当利回り等）を考慮しているが現バージョンでは未実装。

### セキュリティ
- 環境変数による機密情報管理を想定。.env 自動ロード機能はテストや CI で無効化可能（KABUSYS_DISABLE_AUTO_ENV_LOAD）。

---

今後のリリースでは、以下を検討しています（例示）:
- strategy / execution の具体的なトレード実行モジュールの追加およびテスト整備。
- OpenAI 呼び出しの抽象化レイヤーとロギング／メトリクスの強化。
- テストカバレッジの拡充（特に外部 API との統合テスト）。
- パフォーマンス改善（大量データ処理時の最適化、並列処理など）。

もし特定ファイルや挙動についてさらに詳細な changelog 欄（例えばコミット単位の記載）が必要であれば、追加情報を指定してください。