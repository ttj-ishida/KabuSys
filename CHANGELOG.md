# CHANGELOG

すべての変更は Keep a Changelog の形式に従い、重要度別に記載しています。

現在のバージョン: 0.1.0

## [Unreleased]

- なし（初期リリースのため未リリース項目はありません）

## [0.1.0] - 2026-04-04

初回公開リリース。以下の主要機能・モジュールを実装・公開しました。

### Added
- パッケージ基盤
  - kabusys パッケージ初期化（バージョン 0.1.0）。
  - __all__ に data, strategy, execution, monitoring を公開。

- 環境変数 / 設定管理（kabusys.config）
  - .env / .env.local を自動的にプロジェクトルートから読み込む機能を実装（CWD に依存しない）。
  - .env パーサーは export 句、シングル/ダブルクォート、エスケープ、インラインコメント処理をサポート。
  - 読み込み順序: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
  - Settings クラスを提供し、主要設定をプロパティ経由で取得:
    - J-Quants / kabu API / LINE / DB パス（duckdb/sqlite）/監視設定（PID ファイル/kill flag）/閾値（CPU/MEM/DISK）等。
  - 環境変数検証:
    - KABUSYS_ENV は `development`, `paper_trading`, `live` のいずれかのみ許容。
    - LOG_LEVEL は標準ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）を検証。
  - 必須設定未設定時には ValueError を発生させる _require() を実装。

- AI モジュール（kabusys.ai）
  - ニュース NLP（kabusys.ai.news_nlp）
    - raw_news / news_symbols を基に銘柄単位でニュースを集約し、OpenAI（gpt-4o-mini, JSON Mode）でセンチメントを評価して ai_scores テーブルへ書き込み。
    - タイムウィンドウ: 前日15:00 JST〜当日08:30 JST（UTC に変換して DB 検索）。
    - バッチ処理: 最大 20 銘柄ずつ API コール、1 銘柄あたり最大 10 記事・3000 文字でトリム。
    - 再試行: 429 / ネットワーク断 / タイムアウト / 5xx に対して指数バックオフでリトライ。
    - レスポンス検証: JSON 抽出・results キー検査・code/score 検証・数値性・±1.0 クリップ。
    - 部分成功対策: 書き込みは該当コードのみ DELETE → INSERT（部分失敗時に既存スコアを保護）。
    - フェイルセーフ: API エラー等でスコア取得できない場合はその銘柄をスキップし、全体処理を継続。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull / neutral / bear）を算出。
    - マクロニュース抽出はマクロキーワードでフィルタ。LLM 評価は gpt-4o-mini を JSON 出力で呼び出し。
    - LLM 呼び出しは最大リトライ・エラー時は macro_sentiment=0.0 のフェイルセーフ。
    - レジームスコアはクリップして判定し、market_regime テーブルへ冪等的に書き込み（BEGIN / DELETE / INSERT / COMMIT）。トランザクション失敗時は ROLLBACK を試行して例外を伝播。

  - ai パブリック API:
    - score_news(conn, target_date, api_key=None) → ai_scores へ書込んだ銘柄数を返す。
    - score_regime(conn, target_date, api_key=None) → market_regime へ書込んで 1 を返す。

  - セキュリティ / 利便性:
    - API キーは引数で注入可能（テスト容易性）。未設定の場合は環境変数 OPENAI_API_KEY を参照し、未設定だと ValueError。

- Data モジュール（kabusys.data）
  - マーケットカレンダー管理（kabusys.data.calendar_management）
    - market_calendar を利用した営業日判定ロジックを提供:
      - is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days。
    - DB 登録値優先、未登録日は曜日（平日）ベースのフォールバック。
    - 最大探索日数制限（_MAX_SEARCH_DAYS）で無限ループを防止。
    - calendar_update_job(conn, lookahead_days) により J-Quants から差分取得 → 保存（バックフィル / 健全性チェック実装）。
  - ETL パイプライン（kabusys.data.pipeline, kabusys.data.etl）
    - ETLResult データクラスを導入（ターゲット日・取得/保存件数・品質問題・エラー一覧等を保持）。
    - 差分フェッチ/保存/品質チェックの設計方針を実装（バックフィル日数・品質問題は収集して処理継続）。
    - _table_exists / _get_max_date 等のユーティリティを提供。
  - jquants_client へのインターフェース利用を想定（fetch/save 関連の呼出し箇所あり）。

- Research モジュール（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）
    - calc_momentum(conn, target_date): mom_1m, mom_3m, mom_6m, ma200_dev（データ不足時は None）。
    - calc_volatility(conn, target_date): atr_20, atr_pct, avg_turnover, volume_ratio（欠損制御を考慮）。
    - calc_value(conn, target_date): per（EPS が 0/欠損なら None）, roe（raw_financials から最新値）。
    - 設計方針: DuckDB の SQL 窓関数を活用し、prices_daily / raw_financials のみ参照・外部 API 非依存。
  - 特徴量探索（kabusys.research.feature_exploration）
    - calc_forward_returns(conn, target_date, horizons): 複数ホライズンの将来リターンを一度のクエリで計算（入力検証あり）。
    - calc_ic(factor_records, forward_records, factor_col, return_col): スピアマン順位相関（ランク）で IC を算出。サンプル不足（<3）時は None。
    - rank(values): 同順位は平均ランクで扱うユーティリティ（丸め処理で ties の問題を低減）。
    - factor_summary(records, columns): count / mean / std / min / max / median を算出。

### Changed
- 設計上の注意点を明文化（コード内ドキュメント）:
  - すべてのスコアリング/判定処理は datetime.today()/date.today() に依存しない設計（ルックアヘッドバイアス回避）。
  - DuckDB 実行前に空パラメータの executemany を回避する実装（DuckDB 互換性対応）。

### Fixed
- 初期リリースでは特定のバグ修正履歴なし（新規実装）。

### Security
- OpenAI API キーは外部に漏れないよう設計（環境変数か引数での注入のみ）。
- .env 自動ロード時に OS 環境変数を保護するため既存キーは上書きしない実装（ただし .env.local で上書きを許可するオプションあり）。

### Notes / Known limitations
- AI 機能は OpenAI のサービス（gpt-4o-mini）に依存。API キー未設定時は該当関数は ValueError を返す。
- ETL / calendar_update_job は jquants_client（別モジュール）に依存しており、実行には外部 API アクセスが必要。
- DuckDB のバージョン差異（配列バインドの互換性など）に配慮した実装が含まれるため、環境によっては細かな挙動差異が生じる可能性がある。
- 一部の算出結果（MA200 等）はデータ不足時に中立値（例: ma200_ratio=1.0）や None を返す設計（安全側のフォールバック）。

---

今後の予定（想定）
- strategy / execution / monitoring の具体的な取引ロジック・発注実装の追加。
- テストカバレッジ（ユニット/統合）と CI パイプラインの整備。
- ドキュメント（Usage、API リファレンス、データモデル）の拡充。

もし CHANGELOG に特定の変更点（実際のコミットや issue 番号）を追記したい場合は、該当情報を提供してください。