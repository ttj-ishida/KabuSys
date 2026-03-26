CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠して記載しています。

Unreleased
----------

（なし）

[0.1.0] - 2026-03-26
--------------------

Added
- パッケージ初期リリースを追加。
  - パッケージバージョン: 0.1.0

- 基本パッケージ構成
  - モジュール公開: kabusys.data, kabusys.strategy, kabusys.execution, kabusys.monitoring を __all__ に定義。

- 設定・環境変数管理（kabusys.config）
  - .env ファイルまたは環境変数から設定を自動読み込み（プロジェクトルートは .git または pyproject.toml を基準に探索）。
  - 自動ロードを無効化するフラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - .env のパース機能を実装:
    - コメント行、export KEY=val 形式、シングル／ダブルクォート、バックスラッシュエスケープ、行内コメントの取り扱いに対応。
  - .env.local を .env の上から上書き（既存の OS 環境変数は保護）。
  - Settings クラスを提供し、必須設定値をプロパティ経由で取得:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID は必須（未設定時は ValueError）。
    - KABU_API_BASE_URL、DUCKDB_PATH、SQLITE_PATH はデフォルト値あり。
    - KABUSYS_ENV（development / paper_trading / live）と LOG_LEVEL の検証を実装。
    - is_live / is_paper / is_dev のユーティリティプロパティを提供。

- ニュースNLP（kabusys.ai.news_nlp）
  - raw_news / news_symbols を用いた銘柄別ニュース集約と OpenAI によるセンチメントスコア付与機能を実装（score_news）。
  - タイムウィンドウ: JST 基準 前日15:00 ～ 当日08:30（内部は UTC naive で計算）。calc_news_window を提供。
  - 1銘柄あたりの記事数・文字数のトリム制限（_MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK）。
  - バッチ送信（1 API コールあたり最大 20 銘柄）とレスポンスのバリデーション（JSON mode を期待、results 配列の検証）。
  - API エラー（429 / ネットワーク断 / タイムアウト / 5xx）に対するエクスポネンシャルバックオフ・リトライ実装。
  - レスポンスのパース失敗や不正データはスキップして処理継続（フェイルセーフ）。
  - 取得スコアは ±1.0 にクリップ。書き込みは冪等（DELETE → INSERT）で部分失敗時に他コードの既存データを保護。
  - テスト用の差し替えポイント: _call_openai_api をモック可能。

- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF 1321（日経225連動）の 200 日移動平均乖離（重み 70%）と、マクロニュースの LLM センチメント（重み 30%）を合成して日次レジーム判定（score_regime）。
  - マクロ記事抽出はキーワード列（日本語・米国系）に基づき raw_news から取得。
  - OpenAI モデル gpt-4o-mini を使用し、JSON 形式で macro_sentiment を取得。API失敗時は macro_sentiment = 0.0 として継続。
  - レジームスコア合成 → ラベル化（bull / neutral / bear）。
  - DB への書き込みは冪等（BEGIN / DELETE / INSERT / COMMIT）で実施。
  - テスト用モックポイント: _call_openai_api。

- データ基盤ユーティリティ（kabusys.data）
  - マーケットカレンダー管理（calendar_management）:
    - is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days を提供。
    - market_calendar が未取得の場合は土日ベースのフォールバックを使用。
    - calendar_update_job: J-Quants API から差分取得して market_calendar を冪等に更新。バックフィル（直近 _BACKFILL_DAYS）と健全性チェック（未来日付の上限）を実装。
  - ETL パイプライン（pipeline）:
    - ETLResult データクラスを導入し、ETL の取得/保存件数、品質問題リスト、エラー概要を集約。to_dict() で辞書化可能。
    - テーブル最大日付取得・存在チェック等のユーティリティ関数を提供。
  - ETL 公開インターフェース（etl）:
    - pipeline.ETLResult を再エクスポート。

- リサーチ機能（kabusys.research）
  - ファクター計算（factor_research）:
    - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev を prices_daily から計算（データ不足時は None）。
    - calc_volatility: 20日 ATR、ATR 比率、20日平均売買代金、出来高比率を計算（データ不足時は None）。
    - calc_value: raw_financials と prices_daily を組み合わせて PER, ROE を算出（EPS が 0 または欠損の場合は None）。
    - 全関数は DuckDB 接続を受け取り、外部 API 呼び出しは行わない設計。
  - 特徴量探索（feature_exploration）:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを計算（horizons の検証あり）。
    - calc_ic: factor と forward returns を code で突合し、Spearman（ランク）相関（IC）を計算。十分なサンプルがない場合は None を返す。
    - rank: 同順位は平均ランクに変換（浮動誤差対策に round を使用）。
    - factor_summary: 基本統計量（count, mean, std, min, max, median）を計算。
  - research パッケージの __all__ で主要関数を公開。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Notes / 設計上の重要点
- ルックアヘッドバイアス対策:
  - 各種処理（news, regime, research 等）は内部で datetime.today()/date.today() を使わず、呼び出し側から target_date を受け取る設計。
  - DB クエリは target_date 未満／以前の条件を厳格に指定して将来データの参照を防止。
- フェイルセーフ方針:
  - 外部 API（OpenAI, J-Quants）呼び出し失敗時は基本的に処理を中断せず、該当部分は既定値（例: 0.0）またはスキップして継続する。
- テストしやすさ:
  - OpenAI 呼び出し箇所は内部関数でラップしており、unittest.mock.patch による差し替えが可能。
- 依存・運用:
  - データ処理は DuckDB を前提に実装。
  - OpenAI は gpt-4o-mini を利用する想定（JSON Mode を期待）。

Security
- API キー等の必須値は Settings 経由で管理し、.env / 環境変数で注入する設計。必須未設定時は ValueError を投げることで誤動作を防止。

今後の予定（例）
- ai_scores の保存におけるメタデータ拡充（スコア由来の詳細など）
- pipeline における品質チェック結果の自動アクション（アラート／再実行）
- strategy / execution / monitoring の具体実装（現状はパッケージ公開名のみ）