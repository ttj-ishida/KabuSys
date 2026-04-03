CHANGELOG
=========

すべての重要な変更点をこのファイルで記録します。
このプロジェクトは Keep a Changelog の慣習に従います。
リリースノートは後方互換性や設計上の重要な挙動も含めて記載しています。

Unreleased
----------

（なし）

0.1.0 - 2026-04-03
------------------

Added
- パッケージ初期リリース: kabusys (バージョン 0.1.0)
  - src/kabusys/__init__.py にてパッケージを公開。

- 環境設定 / ローディング機能（kabusys.config）
  - .env ファイルまたは環境変数から設定を読み込む自動ローダーを実装。
    - プロジェクトルートは __file__ を基準に上位ディレクトリから .git または pyproject.toml を探索して特定。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能（テスト用）。
    - .env のパースは export 形式、シングル/ダブルクォート、エスケープ、行末コメント処理に対応。
    - .env 読み込み時のファイルアクセス失敗は警告として扱う。
    - 上書き時に OS 環境変数を保護するため protected キーを使用。
  - Settings クラスを提供（settings インスタンスで利用可能）。
    - J-Quants / kabu ステーション / LINE / データベース / 監視閾値 / システム設定等のプロパティを定義。
    - 必須環境変数未設定時は明示的な ValueError を送出。
    - KABUSYS_ENV と LOG_LEVEL の値検証を実施（有効値の列挙とエラー報告）。
    - デフォルトの DB パス、PID/kill flag パス、リソース閾値等のデフォルト値を提供。

- ニュース NLP（kabusys.ai.news_nlp）
  - score_news(conn, target_date, api_key=None)
    - raw_news と news_symbols を集計して銘柄ごとのニュースをまとめ、OpenAI（gpt-4o-mini）でセンチメントを評価。
    - JST 時間窓（前日 15:00 ～ 当日 08:30）を UTC に変換してクエリ。
    - 1 銘柄あたりの最大記事数・最大文字数でトリム（トークン肥大対策）。
    - 最大 _BATCH_SIZE（20）銘柄ごとにバッチ送信。
    - RateLimit(429), ネットワーク断, タイムアウト, 5xx エラーは指数バックオフでリトライ。
    - JSON Mode 出力のパースとバリデーション（results 配列 / code, score の検査）。
    - スコアは ±1.0 にクリップ。部分失敗が発生しても他銘柄の既存スコアを保護するため、書き込みは取得できたコードのみ置換（DELETE→INSERT）。
    - DuckDB の executemany に関する互換性（空リスト回避）に配慮。
    - テストのため OpenAI 呼び出し関数を差し替え可能（unittest.mock.patch 対応）。

- 市場レジーム判定（kabusys.ai.regime_detector）
  - score_regime(conn, target_date, api_key=None)
    - ETF 1321（日経225連動型）の直近 200 日 MA 乖離（重み 70%）と
      マクロニュースの LLM センチメント（重み 30%）を合成して市場レジーム（bull/neutral/bear）を判定。
    - macro_sentiment の取得は OpenAI（gpt-4o-mini）を使用、API 失敗時は macro_sentiment=0.0 にフォールバック（フェイルセーフ）。
    - レジームスコアのクリップ、閾値判定、market_regime テーブルへの冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）を実装。
    - LLM 呼び出しは news_nlp と独立した実装にしてモジュール結合を避けた設計。
    - API 呼び出しはリトライ処理と 5xx 判定に対応。

- Research（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）
    - calc_momentum(conn, target_date): mom_1m/mom_3m/mom_6m, ma200_dev（データ不足時は None）。
    - calc_volatility(conn, target_date): atr_20, atr_pct, avg_turnover, volume_ratio（ウィンドウ内データ不足時は None）。
    - calc_value(conn, target_date): PER（EPS が 0/欠損時は None）、ROE（raw_financials の最新値を使用）。
    - DuckDB 上で SQL とウィンドウ関数を用いて効率的に計算。外部 API や発注処理にはアクセスしない設計。
  - 特徴量探索（kabusys.research.feature_exploration）
    - calc_forward_returns(conn, target_date, horizons=None): 指定ホライズンの将来リターン（horizons の検証あり）。
    - calc_ic(factor_records, forward_records, factor_col, return_col): スピアマン（ランク）相関（IC）を計算。データ不足時は None。
    - rank(values): 同順位は平均ランクを付与するランクトランスフォーム。
    - factor_summary(records, columns): count/mean/std/min/max/median を計算する統計サマリー。
  - zscore_normalize を data.stats から再エクスポート。

- Data モジュール（kabusys.data）
  - calendar_management
    - JPX マーケットカレンダーを扱うユーティリティ群:
      - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day
    - market_calendar が未取得の場合は曜日ベースのフォールバック（週末を非営業日扱い）。
    - next/prev/get_trading_days は DB 登録を優先し、未登録日は曜日フォールバックで一貫性を保つ。
    - calendar_update_job(conn, lookahead_days=90): J-Quants API（jquants_client）から差分取得して market_calendar を冪等的に更新。
      - バックフィルや健全性チェック（未来日付異常検知）に対応。
  - pipeline
    - ETLResult データクラスを実装（ETL 実行結果・品質チェック・エラー一覧を保持）。
    - ETL パイプライン設計方針に基づくユーティリティ（差分取得・保存・品質チェックのための下地）。
  - etl は pipeline.ETLResult を再エクスポート。

- 共通設計上の注意点（ドキュメント化）
  - ルックアヘッドバイアス回避: datetime.today()/date.today() を直接参照しない関数設計（target_date を明示的に渡す）。
  - テスト容易性: OpenAI 呼び出し等を差し替え可能に実装。
  - DB 書き込みはトランザクションで保護し、失敗時は ROLLBACK を試行しログ出力。
  - DuckDB の実装差異（executemany の空リスト不可等）を考慮した実装。

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし（しかし各モジュールでパース例外や API エラーをログに落としつつフェイルセーフ化している点を反映）。

Removed
- 初回リリースのため該当なし。

Security
- 初回リリースのため該当なし。
  - 注意: OpenAI API キーや他の機密情報は環境変数経由で渡し、.env の自動ロード挙動は環境変数で無効化可能（KABUSYS_DISABLE_AUTO_ENV_LOAD）。

備考（実装上の重要ポイント）
- デフォルトの DuckDB / SQLite パスや監視ファイルの場所は Settings 経由で変更可能。
- OpenAI 呼び出しは gpt-4o-mini を想定した JSON Mode を利用し、レスポンスの堅牢なパースと検証を行う設計。
- news_nlp と regime_detector は両方とも OpenAI を使用するが、内部の API 呼び出し実装はモジュール間で共有せず独立させている（疎結合）。
- ETL・データ処理系は DuckDB を前提に記述されており、直接実際の売買・発注 API へアクセスするコードは含まれていない（研究・スコアリング専用）。

--- 

（この CHANGELOG はコードベースの内容から推測して作成しています。実際のリリース日や追加予定の変更はリポジトリ管理者の公式リリースノートを参照してください。）