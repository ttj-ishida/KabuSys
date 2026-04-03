# Changelog

すべての変更は「Keep a Changelog」仕様に準拠しています。日付はリリース日を示します。

## [0.1.0] - 2026-04-03

初回公開リリース。日本株自動売買システムのコア機能（データETL、マーケットカレンダー、ファクター計算、ニュースNLP/レジーム判定、設定管理など）を実装しました。

### 追加
- パッケージ基盤
  - kabusys パッケージの初期公開（バージョン 0.1.0）。
  - __all__ に data / strategy / execution / monitoring を公開（将来的な拡張箇所の用意）。

- 設定・環境変数管理（kabusys.config）
  - .env ファイルまたは環境変数から設定を読み込む Settings クラスを提供。
  - 自動 .env ロード機能（プロジェクトルートの検出: .git / pyproject.toml を基準）。
  - .env 解析の強化:
    - export KEY=val 形式に対応。
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理。
    - クォートなしの場合はインラインコメントの扱いを改善。
  - 自動ロードの無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - 必須環境変数取得用の _require による明確なエラー通知。
  - 多数の設定プロパティを提供（J-Quants トークン、kabu API、LINE トークン、DB パス、監視設定、閾値、実行環境判定等）。

- ニュースNLP（kabusys.ai.news_nlp）
  - raw_news / news_symbols を集計して OpenAI（gpt-4o-mini）で銘柄ごとのセンチメントを算出し ai_scores テーブルへ書き込む score_news を実装。
  - タイムウィンドウ計算（calc_news_window）：前日 15:00 JST 〜 当日 08:30 JST を UTC に変換して扱う。
  - 銘柄ごとに記事を集約し、文字数・記事数上限でトリム（_MAX_ARTICLES_PER_STOCK / _MAX_CHARS_PER_STOCK）。
  - バッチ処理（最大 20 銘柄／回）と JSON Mode を用いた OpenAI 呼び出し。
  - リトライ（429／ネットワーク断／タイムアウト／5xx に対する指数バックオフ）。
  - レスポンスのバリデーションと数値クリッピング（±1.0）。
  - DuckDB 用の安全な置換ロジック（部分失敗時に他コードの既存スコアを保護する DELETE → INSERT の実装）。
  - テスト容易性: OpenAI 呼び出しを簡単にモックできる設計（内部 _call_openai_api を patch 可能）。

- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF 1321（日経225連動型）200日移動平均乖離とマクロニュースの LLM センチメントを重み合成（70% / 30%）して日次で市場レジーム（bull / neutral / bear）を判定する score_regime を実装。
  - MA200 乖離計算（ルックアヘッドを防ぐため target_date 未満のデータのみ使用）。
  - マクロキーワードで raw_news をフィルタして LLM に渡すロジック。
  - OpenAI 呼び出しのリトライ・フォールバック（失敗時は macro_sentiment = 0.0）。
  - レジームスコアの閾値判定と冪等な DB 書き込み（BEGIN / DELETE / INSERT / COMMIT）。
  - テスト容易性・モジュール分離（news_nlp の内部呼び出し関数と独立した実装）。

- 研究用ファンクション（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）:
    - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev を計算。
    - calc_volatility: 20日 ATR、相対ATR、20日平均売買代金、出来高比率などを計算。
    - calc_value: EPS/ROE から PER, ROE を計算（raw_financials と価格を結合）。
    - DuckDB 内で SQL とウィンドウ関数を用いた実装。
  - 特徴量探索（kabusys.research.feature_exploration）:
    - calc_forward_returns: 将来リターン (horizons: default [1,5,21]) を計算。
    - calc_ic: スピアマンランク相関（Information Coefficient）を計算。
    - factor_summary: 各ファクターの基本統計量（count/mean/std/min/max/median）。
    - rank: 同順位は平均ランクを返すランク関数。
  - zscore_normalize をデータユーティリティから再エクスポート。
  - 実装方針: pandas 等に依存せず標準ライブラリと DuckDB のみで実装。

- データプラットフォーム（kabusys.data）
  - カレンダー管理（kabusys.data.calendar_management）:
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days を提供。
    - market_calendar がない場合は曜日ベースのフォールバック（週末は非営業日）。
    - calendar_update_job: J-Quants API から差分取得して market_calendar を冪等保存、バックフィルと健全性チェックを実装。
  - ETL パイプライン（kabusys.data.pipeline）:
    - ETLResult dataclass による実行結果集約（取得数・保存数・品質問題・エラー等）。
    - 差分取得・backfill・品質チェックを行う設計方針を反映した骨組み（jquants_client / quality モジュールとの連携想定）。
    - DuckDB の互換性・安全性を考慮したユーティリティ関数（テーブル存在チェック、最大日付取得等）。
  - etl モジュールで ETLResult を公開（kabusys.data.etl）。

### 変更（設計上の重要点）
- 全体に共通する設計方針を明文化:
  - ルックアヘッドバイアスを避けるため、datetime.today() や date.today() をスコア計算等の内部判定に直接参照しない実装。
  - OpenAI 等の外部APIはフェイルセーフに設計（API失敗時はスコア0.0やスキップで継続）。
  - DB 書き込みは冪等性を重視（DELETE → INSERT、ON CONFLICT などを想定）。
  - DuckDB のバージョン差異を考慮した実装（executemany の空リスト回避等）。
  - 本リポジトリ内の研究・データ処理コードは本番発注ロジックから分離（安全措置）。

### 既知の注意点 / 制約
- OpenAI を利用する機能（score_news / score_regime）は OPENAI_API_KEY の設定が必要（api_key 引数でも指定可能）。未設定時は ValueError を送出します。
- DuckDB に想定テーブル（prices_daily, raw_news, raw_financials, news_symbols, ai_scores, market_regime, market_calendar 等）が存在することが前提です。スキーマ準備は別途必要です。
- jquants_client（J-Quants API 連携）や quality モジュールは本コードから呼び出されますが、実際の実装・設定は外部依存です。
- __all__ に含まれる monitoring / strategy / execution モジュールの実装はこのリリースでは含まれていないか、別モジュールで提供される想定です。

### 修正
- なし（初版）。

### セキュリティ
- なし（初版）。ただし API キーやパスワードは環境変数で管理する設計。

---

今後のリリースで予定している改善例:
- strategy / execution / monitoring の具象実装（発注ロジック・監視プロセス）。
- テストカバレッジの拡充（ユニットテスト・統合テスト）。
- J-Quants / kabu API のクライアント実装の追加・強化。
- スキーマ定義・マイグレーション管理機能の提供。

（注）本 CHANGELOG は手元のコード内容から機能・設計を推測して作成しています。実際のリリースノートとして公開する際は、コミット履歴や差分に基づいて調整してください。