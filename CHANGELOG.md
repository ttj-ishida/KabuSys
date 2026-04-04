# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠しています。  
このプロジェクトはセマンティックバージョニングを使用します。

## [Unreleased]

（現時点では未リリースの変更はありません）

## [0.1.0] - 2026-04-04

初回公開リリース。

### Added
- パッケージ基盤
  - パッケージメタ情報を追加（kabusys.__version__ = 0.1.0）。
  - パッケージ公開モジュール: data, strategy, execution, monitoring（__all__）。

- 環境設定 / ロード
  - 環境変数管理モジュールを追加（kabusys.config）。
    - プロジェクトルート（.git または pyproject.toml）を基に .env/.env.local を自動読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
    - .env の行解析はコメント、export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント等に対応。
    - .env と .env.local の読み込み優先度を実装（OS 環境変数を保護する protected 機構あり）。
    - Settings クラスを提供し、J-Quants / kabu API / LINE / DB パス / 監視設定 / システム設定などの取得（必須変数未設定時は ValueError）。
    - KABUSYS_ENV の値検証（development/paper_trading/live）と LOG_LEVEL の検証。

- データプラットフォーム
  - ETL パイプラインの結果モデル ETLResult を追加（kabusys.data.pipeline, kabusys.data.etl で公開）。
    - ETL 実行結果の集約、品質チェック結果保持、エラー判定プロパティ、辞書化メソッドを実装。
  - 市場カレンダー管理モジュールを追加（kabusys.data.calendar_management）。
    - is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days を実装。
    - market_calendar テーブルの存在/欠落時の曜日ベースフォールバック、最大探索範囲制限、SQL↔Python の日付ハンドリングを実装。
    - calendar_update_job: J-Quants からの差分取得、バックフィル（直近 _BACKFILL_DAYS 日）、健全性チェック（将来日付の異常検出）、冪等保存フローを実装。
  - DuckDB を想定した DB 操作ユーティリティ群を実装（テーブル存在チェック等）。

- 研究（Research）モジュール
  - ファクター計算モジュールを追加（kabusys.research.factor_research）。
    - calc_momentum: 1M/3M/6M リターン、200日 MA 乖離（ma200_dev）を計算。データ不足時は None を返す。
    - calc_volatility: 20日 ATR、相対ATR（atr_pct）、20日平均売買代金、出来高比率を計算。必要行数不足時は None を返す。
    - calc_value: raw_financials と prices_daily を結合し PER / ROE を取得（EPS=0/欠損時は None）。
    - 設計上、DuckDB + SQL ウィンドウ関数で実装し、外部 API にはアクセスしない。
  - 特徴量探索モジュールを追加（kabusys.research.feature_exploration）。
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターン取得（データ欠損は None）。
    - calc_ic: Spearman ランク相関（IC）計算。サンプル数不足（<3）時は None。
    - rank: 同順位は平均ランクとなるランク計算（丸めで ties を安定化）。
    - factor_summary: count/mean/std/min/max/median を計算する統計サマリー。
  - 研究用ユーティリティ zscore_normalize を kabusys.data.stats から再エクスポート（kabusys.research.__init__ にて公開）。

- AI（自然言語 / LLM）モジュール
  - ニュース NLP スコアリング（kabusys.ai.news_nlp）
    - score_news(conn, target_date, api_key=None) を実装。
    - 前日15:00 JST〜当日08:30 JST のウィンドウ計算（calc_news_window）を実装（UTC naive datetime を返す）。
    - raw_news + news_symbols から銘柄ごとに記事を集約し、銘柄単位に最大記事数・文字数でトリムして LLM にバッチ送信（チャンクサイズ: 20）。
    - OpenAI（gpt-4o-mini） JSON mode を使用。429/ネットワーク/タイムアウト/5xx は指数バックオフでリトライ。その他エラーはスキップして継続するフェイルセーフ設計。
    - レスポンスは厳密 JSON を想定するが、前後ノイズがあれば最外側の {} を抽出して復元を試みるなど堅牢にパース。結果検証（results 配列 / code が要求された銘柄に含まれること / score が数値で有限であること）を行い、スコアは ±1.0 にクリップ。
    - 成功した銘柄のみ ai_scores テーブルへ置換（DELETE → INSERT）して部分失敗時の既存データ保護を実現。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - score_regime(conn, target_date, api_key=None) を実装。
    - ETF 1321 の 200 日 MA 乖離（重み 70%）と、マクロニュースの LLM センチメント（重み 30%）を合成して regime_score（-1〜1）を算出し、regime_label を bull/neutral/bear と判定。
    - マクロニュース抽出はニュース NLP のウィンドウ計算を利用し、マクロキーワードでタイトルをフィルタ（最大 20 件）。
    - OpenAI 呼び出しは専用の呼び出し実装を持ち、API のリトライ/フェイルセーフ（失敗時 macro_sentiment=0.0）を行う。
    - 計算結果は market_regime テーブルへ冪等的に書き込み（BEGIN/DELETE/INSERT/COMMIT、失敗時 ROLLBACK）。

### Changed
- （初回リリースのため変更履歴はありません）

### Fixed
- （初回リリースのため修正履歴はありません）

### Security
- OpenAI API キーは関数引数で注入可能（テスト容易性）かつ、引数未指定時は環境変数 OPENAI_API_KEY を参照。未設定時は ValueError を発生させて明示。

### Notes / 設計上の重要ポイント
- ルックアヘッドバイアス回避: 全ての解析関数（score_news、score_regime、各種ファクター計算等）は内部で datetime.today() / date.today() を参照せず、外部から与えられた target_date 周りの過去データのみを使用する設計。
- DB 書き込みは冪等性を意識しており、部分失敗時に既存データを保護する（書き換え対象のコードを絞る等）。
- API 呼び出しはエラー耐性を重視（リトライ、バックオフ、フェイルセーフなデフォルト値）しており、外部サービス障害時もシステム全体が停止しないように設計。
- DuckDB を主なストレージとして想定。コード中で DuckDB のバージョン差分（executemany の空リスト取り扱いなど）に配慮した実装が入っている。

---

開発・利用上の問い合わせや、より詳細な仕様（データモデル、DB テーブル定義、API クライアントの実装詳細など）が必要な場合はお知らせください。