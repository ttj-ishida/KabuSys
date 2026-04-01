# Changelog

すべての注記は Keep a Changelog の形式に準拠し、慣例的にセマンティック バージョニングを使用しています。

## [0.1.0] - 2026-04-01
初回リリース（ベース実装）。

### Added
- パッケージ基盤
  - kabusys パッケージを追加。__version__ = 0.1.0、公開モジュール: data, research, ai, その他所定のサブパッケージを提供。

- 設定/環境変数管理 (kabusys.config)
  - .env ファイルまたは環境変数からの設定読み込みを自動化（プロジェクトルート検出に .git / pyproject.toml を利用）。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロード無効化可能。
  - .env パーサ: コメント、export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ等に対応する堅牢なパーサを実装。
  - 環境変数の上書き時に OS 環境変数を保護する protected 機構を実装。
  - Settings クラスを導入し、J-Quants / kabu ステーション / Slack / DB パス / 監視閾値 / システム環境（KABUSYS_ENV）等の取得をプロパティで提供。KABUSYS_ENV と LOG_LEVEL の値検証を実施。
  - 必須値未設定時は ValueError を送出する _require ユーティリティを実装。

- AI モジュール (kabusys.ai)
  - news_nlp.score_news:
    - raw_news と news_symbols を集約し、銘柄ごとにニュースを結合して OpenAI（gpt-4o-mini、JSON mode）へバッチ送信しセンチメント（-1.0〜1.0）を取得して ai_scores テーブルへ書き込み。
    - チャンク処理（デフォルト _BATCH_SIZE=20）、1 銘柄あたりの記事数・文字数上限のトリム、JSON レスポンスの堅牢な検証と数値クリップをサポート。
    - リトライ／指数バックオフを実装（429・ネットワーク断・タイムアウト・5xx を対象）。API 失敗時は該当チャンクをスキップし処理継続するフェイルセーフ設計。
    - テスト容易性のため _call_openai_api を差し替え可能（unittest.mock.patch を想定）。
    - calc_news_window を公開し、JST 基準のニュース収集ウィンドウ計算を提供（ルックアヘッドバイアス防止のため target_date ベース）。

  - regime_detector.score_regime:
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull / neutral / bear）を判定して market_regime テーブルへ冪等的に保存。
    - _calc_ma200_ratio によるデータ不足ハンドリング（200 日未満で中立扱い）。
    - マクロニュースは news_nlp.calc_news_window と raw_news を用いて抽出、OpenAI 呼び出しは独自実装で結合度を低く保つ。
    - OpenAI API 呼び出しでのリトライ、例外処理および失敗時の macro_sentiment=0.0 フォールバックを実装。

- データプラットフォーム (kabusys.data)
  - calendar_management:
    - market_calendar テーブルを基にした営業日判定ユーティリティ群を提供: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day。
    - DB 登録値優先・未登録日は曜日ベースのフォールバックを採用。最大探索日数制限（_MAX_SEARCH_DAYS）で無限ループ防止。
    - calendar_update_job を実装し、J-Quants からの差分取得・バックフィル（直近 _BACKFILL_DAYS）・健全性チェックを行い、冪等的に market_calendar を更新。

  - pipeline / ETL:
    - ETLResult dataclass を実装し、ETL 実行結果（取得件数・保存件数・品質チェック・エラー等）を構造化して返却、to_dict によるシリアライズを提供。
    - _table_exists / _get_max_date 等のユーティリティを含む（差分取得ロジックの基盤）。
    - data.etl で ETLResult を再エクスポート。

- research モジュール (kabusys.research)
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）を計算。データ不足銘柄は None を返す設計。
    - calc_volatility: 20 日 ATR、相対 ATR（atr_pct）、20 日平均売買代金、出来高比率を計算。NULL 値取り扱いを明示。
    - calc_value: raw_financials から最近の財務を取得し PER / ROE を計算（EPS=0 や欠損時は None）。
  - feature_exploration:
    - calc_forward_returns: 任意ホライズン（デフォルト [1,5,21]）の将来リターンを一括取得する高速 SQL 実装（ホライズン最大値の 2 倍日数でスキャン範囲限定）。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を計算。十分な有効サンプルがない場合は None。
    - rank: 同順位は平均ランクとするランク化ユーティリティ（丸めによる ties 対策あり）。
    - factor_summary: count/mean/std/min/max/median を標準ライブラリのみで計算。
  - research パッケージ __init__ で主要関数を再エクスポート。

### Changed
- なし（初回リリース）

### Fixed
- なし（初回リリース）

### Security
- 環境変数の自動読み込みで OS 環境変数を保護する protected 機構を実装（.env による上書きから保護）。
- OpenAI / Slack / Kabu API 等の必須トークンは Settings 経由で明示的に必須化され、未設定時は明確なエラーを返す。

### Notes / Design decisions
- ルックアヘッドバイアス防止:
  - AI スコア / レジーム判定 / ファクター計算の全関数は内部で datetime.today() / date.today() を参照せず、必ず呼び出し元から target_date を与える設計。
  - DB クエリは target_date 未満 / 以前 のデータのみを使用するよう注意している。
- フェイルセーフ:
  - OpenAI 等の外部 API が失敗した場合、致命的停止を避け可能な限り処理を継続（部分スコアのスキップ、macro_sentiment=0.0 フォールバック等）。
- テスト容易性:
  - OpenAI 呼び出しを行う内部関数（_kabusys.ai.*._call_openai_api）をモック差し替えできる設計。
- DuckDB 互換性:
  - executemany の空リストバインド制約（DuckDB 0.10 相当）を回避するための条件付き実行を行っている部分がある。
- レスポンスパース:
  - OpenAI の JSON Mode を利用するが、前後に余計なテキストが混入するケースを想定して最外郭の JSON を抽出する耐性を有する。

### Known limitations
- OpenAI 依存部はモデル/API の挙動（出力フォーマットの逸脱等）に対して最善のガードを実装しているが、完全に防げないケースがあるため運用時の監視が推奨される。
- 一部処理は J-Quants / kabu API のクライアント実装（kabusys.data.jquants_client 等）に依存しており、外部 API のレスポンス仕様変更があると調整が必要。

---

今後のリリース案内や修正点は CHANGELOG に追記予定です。必要であれば、特定モジュールや関数に関する詳細な変更ログ（例: API シグネチャ、内部アルゴリズム）を追加で作成します。