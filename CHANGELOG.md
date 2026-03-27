# Changelog

すべての変更は Keep a Changelog の形式に従います。  
次のバージョンはセマンティックバージョニングを採用しています。

## [Unreleased]
(なし)

## [0.1.0] - 2026-03-27
初回公開リリース。本リリースでは日本株自動売買システム「KabuSys」のコア機能を実装しています。主な追加点は以下のとおりです。

### Added
- パッケージ基盤
  - パッケージメタ情報: kabusys v0.1.0 を追加。公開 API として data, strategy, execution, monitoring モジュールを __all__ で公開。

- 環境設定 / config
  - .env ファイルおよび環境変数から設定を読み込む自動ロード機能を実装（プロジェクトルート検出: .git または pyproject.toml を基準）。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。
  - 自動ロードを無効化するためのフラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - .env パーサ実装: `export KEY=val` 形式、シングル/ダブルクォート（エスケープ処理対応）、インラインコメント処理（クォートあり/なしの振る舞い差分）に対応。
  - Settings クラスを提供し、以下の設定プロパティを透過的に取得:
    - JQUANTS_REFRESH_TOKEN（必須）
    - KABU_API_PASSWORD（必須）
    - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
    - SLACK_BOT_TOKEN（必須）
    - SLACK_CHANNEL_ID（必須）
    - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
    - SQLITE_PATH（デフォルト: data/monitoring.db）
    - KABUSYS_ENV（有効値: development, paper_trading, live; デフォルト development）
    - LOG_LEVEL（有効値: DEBUG, INFO, WARNING, ERROR, CRITICAL; デフォルト INFO）
  - 必須環境変数が未設定の場合は明示的に ValueError を送出する設計。

- データプラットフォーム系（data）
  - market_calendar を用いたマーケットカレンダー管理モジュールを追加:
    - is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days の判定ユーティリティを実装。
    - DB にカレンダー情報がない場合は曜日（土日）ベースのフォールバックを使用。
    - next/prev_trading_day は探索上限を `_MAX_SEARCH_DAYS`（60日）で制限し、見つからない場合は ValueError を送出。
    - calendar_update_job を実装し、J-Quants API（jquants_client 経由）から差分フェッチして market_calendar を冪等に更新。バックフィルや健全性チェック（最大未来日数）を組み込み。
  - ETL パイプライン基盤:
    - ETLResult dataclass を公開（kabusys.data.ETLResult 経由で利用可能）。
    - 差分取得・保存・品質チェックの概念を組み込み（jquants_client と quality モジュール連携想定）。
    - internal ユーティリティ: テーブル存在チェック、最大日付取得など。

- AI 関連（kabusys.ai）
  - ニュース NLP スコアリング（news_nlp.score_news）を追加:
    - 対象ウィンドウ: target_date の前日 15:00 JST 〜 当日 08:30 JST（内部は UTC naive で比較）。
    - raw_news と news_symbols から銘柄ごとに記事を集約し、1 銘柄につき最新 10 件 / 最大 3000 文字にトリム。
    - 銘柄を最大 20 件ずつ（_BATCH_SIZE=20）バッチで OpenAI（gpt-4o-mini、JSON Mode）へ送信。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対して指数バックオフでリトライ（最大試行回数の制御）。
    - レスポンスの厳密なバリデーション実装（JSON 抽出、"results" 配列チェック、code と score チェック、数値型・有限チェック）。スコアは ±1.0 にクリップ。
    - 成功した銘柄に対し、ai_scores テーブルへ安全に置換（DELETE（個別）→ INSERT）を実行し、部分失敗時に既存データを保護する設計。
    - API 呼び出しの内部関数はテスト用にパッチ可能（unittest.mock.patch 対応）。

  - 市場レジーム判定（regime_detector.score_regime）を追加:
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（_MA_WINDOW=200）とマクロニュースの LLM センチメントを合成して日次で市場レジームを判定（'bull' / 'neutral' / 'bear'）。
    - 合成ロジック: MA 重み 70%（MA を (ratio - 1.0) * scale でスケーリング、_MA_SCALE=10.0）、マクロ重み 30%。
    - レジーム閾値: bull >= 0.2、bear <= -0.2。
    - マクロキーワードを用いて raw_news からタイトルを抽出（最大 20 件）。
    - OpenAI（gpt-4o-mini）でマクロセンチメントを JSON で取得。API 失敗時は macro_sentiment=0.0 にフォールバックし処理を継続（フェイルセーフ）。
    - market_regime テーブルへの書き込みは冪等（BEGIN / DELETE / INSERT / COMMIT）で実行。DB 書き込み失敗時は ROLLBACK の試行と例外伝播を行う。
    - OpenAI API キーは引数で注入可能（None の場合は OPENAI_API_KEY 環境変数を参照）。未設定時は ValueError を送出。

- リサーチ（kabusys.research）
  - ファクター計算モジュールを実装:
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）を計算。データ不足は None を返す。
    - calc_volatility: 20 日 ATR（atr_20）、相対 ATR（atr_pct）、20 日平均売買代金（avg_turnover）、出来高比（volume_ratio）を計算。必要行数未満は None を返す。
    - calc_value: raw_financials から target_date 以前の最新財務データを取得して PER（EPS が 0 または欠損の場合は None）と ROE を計算。
  - 特徴量探索（feature_exploration）を実装:
    - calc_forward_returns: デフォルト horizons=[1,5,21]、引数検証（正の整数かつ <= 252）。複数ホライズンをまとめて取得し将来リターンを算出。
    - calc_ic: Spearman ランク相関（Information Coefficient）を計算。レコード有効数が 3 未満の場合は None。
    - rank: 同順位は平均ランクを返す実装（丸めによる ties 対策: round(v, 12) を使用）。
    - factor_summary: count/mean/std/min/max/median を計算する統計サマリ。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- （現時点で特記すべきセキュリティ修正はなし）

### Notes / Implementation Details / テストへ向けた配慮
- OpenAI への API 呼び出しは各モジュール内で専用のラッパ関数を用意しており、ユニットテスト時は patch により差し替え可能（テスト容易性を確保）。
- DuckDB を前提とした SQL 実装であり、空の executemany など DuckDB のバージョン依存挙動（0.10 等）を考慮したガードを実装している。
- 時刻/日付処理はルックアヘッドバイアスを避けるため datetime.today() / date.today() を直接参照しない設計（関数引数で target_date を明示的に与える方式）。
- DB 書き込みは可能な限り冪等化（DELETE → INSERT、ON CONFLICT 想定）しており、部分失敗時に既存データを保護するロジックを備えている。

---

この CHANGELOG はソースコードからの推測に基づいて作成しています。実際の利用シナリオや外部依存（J-Quants / Slack / kabu API / OpenAI）の設定・権限などは別途ドキュメントを参照してください。