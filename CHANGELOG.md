# Changelog

すべての重要な変更は Keep a Changelog の形式に準拠して記載しています。  
このファイルはコードベースから推測して作成した初期リリースの変更履歴です。

全般的な方針:
- DuckDB をデータストアとして利用（テーブル読み書きは DuckDB 接続を受け取る設計）。
- OpenAI（gpt-4o-mini）を JSON Mode で呼び出して NLP 処理を行う。
- ルックアヘッドバイアス防止のため、date/timestamp の取扱いに注意（datetime.today()/date.today() を直接参照しない等）。
- フェイルセーフ設計：外部 API エラー時は例外で即停止させず、デフォルト値で継続する箇所がある。
- DuckDB の互換性（executemany の空リスト回避等）を考慮した実装。

## [0.1.0] - 2026-04-03

### Added
- パッケージ基本情報
  - パッケージ名: kabusys、バージョン 0.1.0 を追加（src/kabusys/__init__.py）。
  - パッケージ公開 API として data / strategy / execution / monitoring を __all__ に定義。

- 環境設定管理
  - .env ファイルまたは環境変数から設定を読み込む Settings 実装を追加（src/kabusys/config.py）。
    - 自動ロード: プロジェクトルート（.git または pyproject.toml）を基準に .env を自動読み込み。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能（テスト用途）。
    - export KEY=val, クォート・エスケープ・インラインコメント処理を考慮した .env パーサを実装。
    - 必須環境変数未設定時に ValueError を投げる _require() を提供。
    - 各種設定プロパティを提供（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL, LINE 関連, DB パス, 監視用 PID/KILL フラグ, CPU/MEM/DISK 閾値, KABUSYS_ENV / LOG_LEVEL 判定ヘルパ等）。

- AI（NLP）機能
  - ニュースセンチメントスコアリング（銘柄別）
    - src/kabusys/ai/news_nlp.py を提供。
    - raw_news + news_symbols からタイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）内のニュースを集約し、銘柄ごとに gpt-4o-mini にバッチ送信してスコアを算出。
    - バッチ処理（最大 20 銘柄/コール）、1 銘柄あたり記事数・文字数上限（トリム）を実装。
    - JSON レスポンスのバリデーションとスコアクリップ（±1.0）。
    - リトライ戦略: RateLimit / ネットワーク断 / タイムアウト / 5xx を対象に指数バックオフで再試行。
    - 書き込みは idempotent を意識（該当日のコード群のみ DELETE → INSERT）し、DuckDB の executemany の空パラメータ問題に対応。
    - 公開関数: score_news(conn, target_date, api_key=None) → 書き込んだ銘柄数を返す。
    - calc_news_window(target_date) を公開（UTC naive datetime を返す）。

  - 市場レジーム判定
    - src/kabusys/ai/regime_detector.py を提供。
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニューズの LLM センチメント（重み 30%）を合成して日次の市場レジームを判定（'bull'/'neutral'/'bear'）。
    - prices_daily から ma200_ratio を算出（target_date 未満のデータのみ参照してルックアヘッド防止）。
    - raw_news のマクロキーワード抽出（タイトル）を用いて LLM に渡す。記事がない場合は LLM 呼び出しをスキップ（macro_sentiment=0.0）。
    - OpenAI 呼び出しは独自関数化し、リトライや 5xx の扱いを明確化。
    - 計算結果は market_regime テーブルへ冪等に書き込み（BEGIN/DELETE/INSERT/COMMIT）。DB エラー時は ROLLBACK を試み上位へ例外伝搬。
    - 公開関数: score_regime(conn, target_date, api_key=None) → 1（成功）を返す。

- データ（Data Platform）機能
  - カレンダー管理
    - src/kabusys/data/calendar_management.py を提供。
    - market_calendar を利用して営業日判定／次営業日／前営業日／期間内営業日リスト／SQ判定を行う関数を実装（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）。
    - market_calendar 未取得時は曜日ベース（週末除外）でフォールバック。
    - 夜間バッチ更新 job: calendar_update_job(conn, lookahead_days=90) を実装。J-Quants API クライアント（jquants_client）を用いた差分取得・保存・バックフィル・健全性チェックを実装。

  - ETL パイプライン
    - src/kabusys/data/pipeline.py を実装。
    - ETLResult dataclass による実行結果の構造化（取得数／保存数／品質問題／エラー等）。
    - 差分更新・バックフィル・品質チェック（quality モジュール）連携の設計を明記。
    - 内部ユーティリティ: テーブル存在チェック、最大日付取得等を実装。

  - ETL インターフェース再公開
    - src/kabusys/data/etl.py で ETLResult を公開。

  - jquants_client への参照を行う実装（fetch/save を想定）を各所で使用（calendar_management, pipeline）。

- リサーチ機能
  - src/kabusys/research 以下を実装・公開（研究用ユーティリティ）。
    - factor_research.py: calc_momentum / calc_volatility / calc_value を実装（prices_daily / raw_financials を参照）。
      - Momentum: mom_1m / mom_3m / mom_6m / ma200_dev（データ不足時は None）。
      - Volatility: 20 日 ATR（atr_20）, atr_pct, avg_turnover, volume_ratio（ウィンドウ不足時は None）。
      - Value: PER / ROE（raw_financials の最新レコードを利用）。
    - feature_exploration.py:
      - calc_forward_returns(conn, target_date, horizons=None): 将来リターン（LEAD を使用）を一クエリで取得。
      - calc_ic(factor_records, forward_records, factor_col, return_col): スピアマンのランク相関（IC）を実装。データ不足時は None。
      - rank(values): ランク付け（同順位は平均ランク）。
      - factor_summary(records, columns): count/mean/std/min/max/median の統計サマリー。
    - research パッケージ __init__ で zscore_normalize（kabusys.data.stats から）および上記関数を公開。

- 実装上の細かな考慮点（横断的）
  - DuckDB 操作での冪等性と互換性を重視（BEGIN/COMMIT/ROLLBACK、executemany の空リスト回避）。
  - API 呼び出し（OpenAI / J-Quants 等）でのリトライ・バックオフ戦略を実装して堅牢化。
  - タイムゾーンの混入を避けるため UTC naive datetime や date オブジェクトを明示して扱う箇所を設計書に沿って実装。
  - OpenAI レスポンスのパースで JSON の周囲に余計なテキストが混ざるケースを想定した復元処理を実装。
  - テスト容易性を配慮して OpenAI 呼び出し部分は内部で独立した関数として切り出し、モック差し替えを想定。

### Security
- 環境変数の自動ロードは既存の OS 環境変数を保護する仕組み（protected set）を導入。
- KABUSYS_DISABLE_AUTO_ENV_LOAD により CI/テストで .env 自動読み込みを無効化できる。

### Notes / Usage
- OpenAI API キーは score_news / score_regime の api_key 引数で注入可能。省略時は環境変数 OPENAI_API_KEY を参照する。未設定時は ValueError を送出。
- J-Quants 関連の動作は JQUANTS_REFRESH_TOKEN 等の環境変数に依存。
- DuckDB 接続に対して想定されるテーブル（prices_daily, raw_news, news_symbols, ai_scores, market_regime, market_calendar, raw_financials など）が存在することが前提。
- 本リリースでは本番発注 API に接続するコードは含まれておらず、Research / Data / AI 処理に注力した初期実装。

### Breaking Changes
- 初期リリースのため破壊的変更はなし。

---

今後の想定追加事項（参考）
- strategy / execution / monitoring の実装拡充（現在はパッケージ公開のみ）。
- より詳細な品質チェックルール（quality モジュールの実装強化）。
- テストカバレッジと CI ワークフロー、実行環境での安全なデプロイ手順の整備。