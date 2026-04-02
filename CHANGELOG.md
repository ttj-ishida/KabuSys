# Changelog

すべての注目すべき変更履歴をここに記載します。本ファイルは Keep a Changelog の形式に準拠します。  

リリースポリシーやバージョニングは Semantic Versioning に準拠します。

## [Unreleased]
（なし）

## [0.1.0] - 2026-04-02
初期リリース。日本株自動売買システム「KabuSys」のコア機能群を実装しました。

### 追加 (Added)
- パッケージ初期化
  - パッケージメタ情報として version=0.1.0 を追加（src/kabusys/__init__.py）。
  - パッケージ構成要素のエクスポート（data, strategy, execution, monitoring）を宣言。

- 設定管理 (src/kabusys/config.py)
  - .env / .env.local ファイルおよび環境変数から設定を自動ロードする機能を実装。
    - プロジェクトルート検出（.git または pyproject.toml を基準）によりカレントディレクトリに依存せず動作。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能。
    - .env のパースは export 付きの行、クォート内のエスケープ、インラインコメントの取り扱いに対応。
    - override / protected オプションにより OS 環境変数の上書きを保護。
  - Settings クラスを実装し、主要設定値をプロパティで提供：
    - J-Quants / kabuステーション / Slack / DB パス / 監視閾値 / ログレベル / 環境（development, paper_trading, live）など。
  - 必須環境変数未設定時は ValueError を送出する _require ヘルパーを追加。

- AI（自然言語処理） (src/kabusys/ai/)
  - ニュースセンチメント分析（score_news）
    - raw_news と news_symbols を集約して銘柄ごとに記事をまとめ、OpenAI（gpt-4o-mini, JSON Mode）へバッチ送信してスコアを算出。
    - チャンク処理（最大 20 銘柄 / コール）、1 銘柄あたりの記事数・最大文字数制限（トリム）を実装。
    - リトライ（429 / ネットワーク / タイムアウト / 5xx）を指数バックオフで実施。失敗はスキップして継続（フェイルセーフ）。
    - レスポンス検証機構（JSON パース、results 配列、各要素 code/score の検証、数値チェック、±1.0 クリップ）を実装。
    - DuckDB への書き込みは部分失敗に備え、取得済みコードのみ DELETE→INSERT による置換を行い既存データを保護。
    - タイムウィンドウ計算（JST 前日 15:00 ～ 当日 08:30 を UTC に変換）を提供する calc_news_window 実装。
    - テスト容易性のため OpenAI 呼び出し部を差し替え可能（ユニットテスト用の patch 対応）。
  - 市場レジーム判定（score_regime）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成し、日次でレジーム（bull/neutral/bear）を決定。
    - prices_daily から MA200 比率を計算（ルックアヘッドバイアス防止のため target_date 未満データのみ使用）。
    - raw_news をマクロキーワードでフィルタしてタイトルを抽出し、OpenAI により macro_sentiment を算出（記事なし時・API 失敗時は 0.0 にフォールバック）。
    - レジーム結果を market_regime テーブルへ冪等的に書き込み（BEGIN/DELETE/INSERT/COMMIT を使用）。
    - API 呼び出し回りにリトライ・5xx 判定等の堅牢化を実装。
  - AI モジュールは news_nlp.score_news と regime_detector.score_regime を公開。

- データ基盤 (src/kabusys/data/)
  - ETL パイプライン
    - ETLResult データクラスを実装し、ETL 実行結果（取得数・保存数・品質問題・エラー）を構造化して返却・監査可能に。
    - ETL 設計に関する方針（差分更新・backfill 再取得・品質チェックは継続収集方針・id_token 注入可能）を実装方針として反映。
  - マーケットカレンダー管理（calendar_management）
    - market_calendar テーブルを参照して営業日判定ロジックを提供：
      - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day。
    - DB 登録値を優先し、未登録日は曜日ベース（土日非営業）でフォールバックする一貫した判定ロジック。
    - next/prev の探索は最大探索範囲（_MAX_SEARCH_DAYS）でガード。
    - calendar_update_job を実装し、J-Quants API から差分取得→冪等保存（save_market_calendar 呼び出し）を行う。バックフィル・健全性チェックを実装。
  - 内部ユーティリティ（テーブル存在チェック、日付変換など）を追加。

- リサーチ分析 (src/kabusys/research/)
  - ファクター計算（factor_research）
    - calc_momentum: mom_1m/mom_3m/mom_6m、ma200_dev（200日移動平均乖離）を実装。データ不足時は None を返却。
    - calc_volatility: 20日 ATR、相対 ATR（atr_pct）、20日平均売買代金、出来高比率を実装。TR は high/low/prev_close が存在しない場合は NULL 扱いして正確な集計を行う。
    - calc_value: raw_financials から最新財務を取得して PER（EPS が 0/NULL の場合は None）・ROE を計算。
    - 設計方針として DuckDB 接続のみを参照し、取引系・外部 API にはアクセスしないよう分離。
  - 特徴量探索（feature_exploration）
    - calc_forward_returns: 指定 horizon（デフォルト [1,5,21]）に対する将来リターンを計算。ホライズン検証（正の整数・252 以下）を実装。
    - calc_ic: スピアマンのランク相関（IC）を実装。データ不足（有効レコード <3）や分散 0 の場合は None を返す。
    - rank: 同順位は平均ランクとするランク付けユーティリティ（丸め処理により ties 判定を安定化）。
    - factor_summary: 各カラムの count/mean/std/min/max/median を算出する統計サマリー機能。
    - いずれも prices_daily / raw_financials のみ参照し、本番口座へ影響しない設計。

### 変更 (Changed)
- （初回リリースのため該当なし）

### 修正 (Fixed)
- （初回リリースのため該当なし）

### 注意事項 / 実装上の重要点
- ルックアヘッドバイアス回避
  - AI モジュールおよびリサーチ関数はいずれも datetime.today() や date.today() に依存せず、target_date 引数で日付を受け取る設計です。
- DB 書き込みの冪等性
  - market_regime / ai_scores / market_calendar 等への書き込みは既存データ保護（DELETE→INSERT や ON CONFLICT ベース）を意識して実装されています。
- OpenAI 呼び出しの堅牢化
  - JSON Mode を利用しつつ、実際の SDK レスポンスの揺らぎに備えた復元ロジック（最外側の {} を抽出してパース）や、リトライ/バックオフ/5xx 判定を実装。
- テスト支援
  - OpenAI 呼び出し部分はモジュール内部で分離されており、ユニットテストのためにパッチ差し替えが想定されています。
- 環境変数の必須項目（例）
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, OPENAI_API_KEY 等は Settings 経由で参照され、未設定時は明示的なエラーが発生します。

---

（今後のリリースでは、各機能の改良・バグ修正・API 変更・互換性に関する情報をここに追記します）