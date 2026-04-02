# CHANGELOG

すべての変更は「Keep a Changelog」準拠で記載しています。  
このファイルはコードベースの現状から機能・設計・注意点を推測してまとめた初版のリリースノートです。

## [0.1.0] - 2026-04-02

### 追加 (Added)
- 基本パッケージ構成を追加
  - パッケージ: kabusys（__version__ = 0.1.0）
  - サブモジュール: data, research, ai, monitoring, execution, strategy（公開APIとして __all__ を定義）

- 環境設定・自動.envロード機能（kabusys.config）
  - プロジェクトルートの自動検出（.git または pyproject.toml を基準）による .env / .env.local の自動読み込み
  - export KEY=val 形式、シングル/ダブルクォート、エスケープ、行コメントなどに対応したパーサを実装
  - OS 環境変数保護（既存値を挟んで上書きを制御）や自動ロード無効化フラグ（KABUSYS_DISABLE_AUTO_ENV_LOAD）を提供
  - Settings クラスでアプリ設定をプロパティとして提供（J-Quants / kabu API / Slack / DB パス / 監視閾値 / 環境フラグ等）
  - 必須環境変数取得時は未設定なら ValueError を送出する `_require` を提供

- ニュースNLP（kabusys.ai.news_nlp）
  - raw_news と news_symbols を用いた銘柄ごとのニュース集約機能
  - OpenAI (gpt-4o-mini) を用いた銘柄単位センチメントスコアリング（JSON Mode 出力想定）
  - バッチ処理（最大 _BATCH_SIZE=20 銘柄）・1銘柄あたりの記事数および文字数トリム（_MAX_ARTICLES_PER_STOCK / _MAX_CHARS_PER_STOCK）
  - 再試行（429・ネットワーク断・タイムアウト・5xx）を指数バックオフで実施
  - レスポンス検証ロジック（JSON 抽出、results 配列・code/score 検証、±1.0 でクリップ）
  - DuckDB 互換性考慮（executemany に対する空パラメータ防止）と DB の冪等更新（DELETE → INSERT）

- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）で日次レジーム判定
  - マクロキーワードによる raw_news フィルタリング、OpenAI 呼び出し（gpt-4o-mini）での macro_sentiment 評価
  - API リトライ/バックオフ、エラー時のフォールバック macro_sentiment=0.0、計算結果のクリップとラベル付与（bull/neutral/bear）
  - 結果を market_regime テーブルへ冪等（BEGIN / DELETE / INSERT / COMMIT）で書き込み

- データプラットフォーム機能（kabusys.data）
  - マーケットカレンダー管理（calendar_management）
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を提供
    - market_calendar が未取得時の曜日フォールバック、DB 登録優先の一貫した判定ロジック
    - calendar_update_job: J-Quants API からの差分取得・バックフィル・健全性チェック・冪等保存を実装
  - ETL パイプライン（pipeline）
    - 差分取得、保存（jquants_client の save_* 呼び出しを前提）、品質チェック統合のための ETLResult データクラスを追加
    - ETLResult に処理結果要約・品質情報（quality_issues）・エラーメッセージを保持し to_dict で出力可能
  - ETL の補助: jquants_client 経由でのデータ取得/保存想定、backfill デザイン、品質チェックは非 Fail-Fast 設計

- リサーチ分析（kabusys.research）
  - factor_research: momentum, volatility, value, liquidity 等のファクター計算を実装
    - calc_momentum: mom_1m/3m/6m、ma200_dev（データ不足時は None）
    - calc_volatility: 20日 ATR、相対ATR、20日平均売買代金、出来高比率
    - calc_value: raw_financials から最新財務を結合して PER / ROE を算出（EPS=0/欠損は None）
  - feature_exploration: 将来リターン計算 / IC（Spearman） / 統計サマリー・ランク処理を実装
    - calc_forward_returns: 複数ホライズンに対応（デフォルト [1,5,21]）、horizons のバリデーション
    - calc_ic: factor と forward を code で結合しスピアマン ρ を計算（有効レコード < 3 は None）
    - factor_summary: count/mean/std/min/max/median を標準ライブラリのみで算出
    - zscore_normalize は data.stats から再エクスポート

### 変更 (Changed)
- （初期リリースにつき主要な「追加」が中心。コード中に多数の互換性配慮・安全対策を組み込み）
  - DuckDB の挙動差異（executemany の空リスト不可等）に合わせたガード処理を追加
  - LLM 呼び出しとレスポンス処理は JSON Mode を前提にしつつ、前後余計なテキスト混入時の復元ロジックを実装

### 修正 (Fixed)
- OpenAI / ネットワークエラー時のフォールバックを徹底
  - news_nlp と regime_detector ともに 429 / ネット切断 / タイムアウト / 5xx をリトライ対象とし、最終的に失敗した場合はスキップまたは安全値（0.0）を使用してシステム全体の頑健性を確保

### 注意点 (Notable behavior / Known issues)
- OpenAI API キーは必須
  - score_news/score_regime の api_key 引数が None の場合は環境変数 OPENAI_API_KEY を参照。未設定時は ValueError を送出する
- DB スキーマ依存
  - 多くの関数は prices_daily, raw_news, news_symbols, raw_financials, ai_scores, market_regime, market_calendar 等のテーブルを前提としている。これらが存在しない・期待列が欠落している場合は例外または 0 / 空の結果を返す
- LLM レスポンスの厳格な JSON 出力を前提としているが、実環境では余計な文字列が混入する可能性があるため復元処理を入れている（それでもパースに失敗すると該当チャンクはスキップされる）
- 一部未実装/将来対応事項
  - calc_value: PBR・配当利回りは未実装（注記あり）
  - news/LLM 周りはプロンプトやモデル変更により結果が変化するため運用での監視が必要

### セキュリティ (Security)
- 環境変数の扱いにおいて OS 側の既存環境変数を保護する仕組みを導入（.env 上書き制御）
- 機密情報（API キー等）は Settings 経由で要求され、未設定時に明示的な例外を出す設計

---

注: 本 CHANGELOG は配布されているソースコードの内容から機能・設計意図を推測して作成したものです。実際のリリース履歴や運用上の変更履歴とは差異があり得ます。追加のリリース履歴（パッチやマイナーバージョン）は今後のコード変更に応じて追記してください。