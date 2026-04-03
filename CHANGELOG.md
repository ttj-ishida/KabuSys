Keep a Changelog
=================

すべての注目すべき変更点をこのファイルで管理します。  
フォーマットは "Keep a Changelog" に準拠します。

[Unreleased]
-----------

（現時点で未リリースの変更はありません）

[0.1.0] - 2026-04-03
-------------------

Added
- 基本パッケージ初期版を追加（バージョン 0.1.0）。
- パッケージ構成:
  - kabusys: core パッケージエントリ（__version__ = 0.1.0）。
  - サブパッケージ: data, research, ai, （execution, monitoring はパッケージ公開側に含める設計）。
- 環境設定管理（kabusys.config）
  - .env ファイルと OS 環境変数の自動読み込みを実装（プロジェクトルートは .git または pyproject.toml を探索）。
  - .env のパース実装: export 形式、シングル/ダブルクォート、バックスラッシュエスケープ、行内コメント（クォートの有無に応じた挙動）に対応。
  - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - Settings クラスを提供し、J-Quants / kabuステーション / LINE / DB /監視/システム設定等のプロパティを環境変数から取得。
  - 必須環境変数未設定時には ValueError を発生させる _require を実装。
  - 環境値のバリデーション（KABUSYS_ENV, LOG_LEVEL の許容値チェック）。
- AI モジュール（kabusys.ai）
  - ニュースセンチメントバッチ処理: score_news(conn, target_date, api_key=None)
    - raw_news と news_symbols から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini、JSON mode）へ最大 20 銘柄／チャンクで送信してスコアを取得。
    - タイムウィンドウ計算（JST 前日 15:00 〜 当日 08:30、内部は UTC naive datetime で扱う calc_news_window）。
    - API の 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフリトライ実装。
    - レスポンスの堅牢なバリデーション（JSON 抽出、results 配列・code と score の検証、スコアの ±1.0 クリップ）。
    - DuckDB 互換性のための executemany 空リスト回避などの DB 書き込み保護（部分失敗時に既存スコアを消さない挙動）。
  - 市場レジーム判定: score_regime(conn, target_date, api_key=None)
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次で regime_score と regime_label（bull/neutral/bear）を計算して market_regime に冪等書き込み。
    - マクロニュース抽出（キーワードリスト）→ LLM 評価（gpt-4o-mini、JSON mode）→ 合成スコア → DB 書き込みのフローを実装。
    - LLM 呼び出し失敗時はフェイルセーフとして macro_sentiment = 0.0 を使用。
    - モデル呼び出し用の内部 _call_openai_api を含む（テストで差し替え可能）。
- Data モジュール（kabusys.data）
  - マーケットカレンダー管理（calendar_management）
    - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day を実装。
    - market_calendar が未取得のときは曜日ベースのフォールバック（平日が営業日）を行う実装。
    - DB 登録値優先、未登録日は曜日フォールバックの一貫した挙動。検索上限日数を設定して無限ループを防止。
    - calendar_update_job による J-Quants からの差分取得と冪等保存（バックフィル、健全性チェックを含む）。
  - ETL パイプライン（pipeline）
    - ETL のための ETLResult dataclass を実装（取得数・保存数・品質問題・エラー等を集約）。
    - 差分更新、backfill、品質チェック（quality モジュールを想定）に基づく設計方針を反映。
    - _table_exists / _get_max_date 等の内部ユーティリティを実装（DuckDB 前提）。
  - data.etl で ETLResult を公開（再エクスポート）。
- Research モジュール（kabusys.research）
  - ファクター計算（factor_research）
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）を計算。データ不足は None を返す。
    - calc_volatility: 20 日 ATR（atr_20）, atr_pct, avg_turnover, volume_ratio を計算。欠損/不足時は None。
    - calc_value: raw_financials の最新財務を用いて PER, ROE を計算（EPS が 0/欠損時は PER=None）。
  - 特徴量探索（feature_exploration）
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを計算（LEAD を利用）。
    - calc_ic: factor_records と forward_records を code で結合して Spearman ランク相関（IC）を算出。十分な有効データがなければ None を返す。
    - rank: 同順位は平均ランクにするランク変換実装（丸めで ties 検出の安定化）。
    - factor_summary: count/mean/std/min/max/median を計算する統計サマリー実装。
  - research パッケージの __init__ で主要関数群を公開（zscore_normalize は data.stats から再利用）。
- テストしやすさ・設計上の配慮
  - OpenAI API 呼び出しをモジュール内でラップし、unittest.mock.patch で差し替え可能にしている（テスト容易性）。
  - DB 書き込みは冪等性を保つ（DELETE → INSERT の形式、トランザクション制御 BEGIN/COMMIT/ROLLBACK）。
  - ルックアヘッドバイアス防止設計: date.today()/datetime.today() を主要処理で直接参照しない（target_date を明示的に与える）。

Changed
- 新規リリースのための初期実装。設計ドキュメントの方針（DataPlatform.md / StrategyModel.md に基づく）をコードに反映。

Fixed
- N/A（初回リリースのため既知のバグ修正はなし。ただし各モジュールにフォールバック・例外処理・ログ出力を充実させ堅牢性を高めている）。

Security
- 環境変数の扱い:
  - OS 環境変数は保護（.env 読み込み時に既存の OS 環境変数を保護する仕組み）。
  - API キーは引数経由でも渡せるが、省略時は OPENAI_API_KEY 等の環境変数を参照。未設定時は明示的にエラーを出す。

Notes / Migration
- 初回リリースのため破壊的変更はなし。
- 将来的に OpenAI SDK のバージョン変更や DuckDB のバインド挙動変更に伴う互換性注意あり（既にいくつか互換性ワークアラウンドを実装）。
- 自動 .env 読み込みはプロジェクトルート検出に依存するため、パッケージ配布後の実行環境では KABUSYS_DISABLE_AUTO_ENV_LOAD を使って制御してください。

Acknowledgements
- 本リリースはローカル DB（DuckDB）を中心に設計され、外部発注/実行ロジックとは分離された構成になっています。AI 呼び出し周り・ETL/カレンダー処理はプロダクション運用を想定した堅牢性（リトライ・フェイルセーフ・冪等性）を重視して実装されています。