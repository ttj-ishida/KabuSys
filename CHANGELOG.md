# CHANGELOG

すべての注目すべき変更点を記録します。  
このファイルは Keep a Changelog の慣習に従っており、安定したリリースや将来の変更の参照に利用してください。

注: 日付はリリース作成日です。

## [Unreleased]

## [0.1.0] - 2026-04-04

初回リリース。日本株自動売買プラットフォームのコアライブラリを提供します。主な機能は以下の通りです。

### 追加 (Added)
- パッケージ初期化
  - pakage: kabusys
  - __version__ = "0.1.0"
  - パブリックサブパッケージ: data, strategy, execution, monitoring を __all__ で公開。

- 設定・環境変数管理 (kabusys.config)
  - .env / .env.local をプロジェクトルート（.git または pyproject.toml 基準）から自動読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化対応）。
  - export KEY=val や引用符付き値、インラインコメント等に対応した独自の .env パーサ実装。
  - override / protected オプションによる上書き制御（OS 環境変数保護）。
  - Settings クラスにより各種設定をプロパティとして提供（J-Quants トークン、kabu API、LINE、DB パス、監視閾値、環境/ログレベル判定など）。
  - 設定値のバリデーション（KABUSYS_ENV, LOG_LEVEL 等）。

- ニュース NLP（kabusys.ai.news_nlp）
  - raw_news + news_symbols を用いて銘柄別にニュースを集約し、OpenAI（gpt-4o-mini）の JSON mode でセンチメントを評価して ai_scores テーブルへ書き込み。
  - JST 時間ウィンドウ（前日 15:00 ～ 当日 08:30）に対応する calc_news_window 実装。
  - バッチ処理（最大 20 銘柄）・トークン過大対策（記事数/文字数制限）・バリデーション（results キー・型チェック）を実装。
  - リトライ戦略（429／ネットワーク断／タイムアウト／5xx を指数バックオフでリトライ）を実装。
  - API キー注入（引数優先、なければ OPENAI_API_KEY 環境変数）と未設定時の ValueError。
  - DuckDB への冪等的な書き込み（対象コードのみ DELETE→INSERT）で部分失敗に対する保護。

- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull / neutral / bear）を判定。
  - OpenAI 呼び出し・JSON パースの堅牢化（再試行、エラーハンドリング、フォールバック macro_sentiment=0.0）。
  - DuckDB から価格・ニュースを参照し、market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）。
  - ルックアヘッドバイアス対策（内部で datetime.today() を参照しない、date 未満のデータのみを使用）。

- 研究用モジュール（kabusys.research）
  - factor_research: モメンタム、ボラティリティ、バリュー系ファクター計算を提供。
    - calc_momentum: 1M/3M/6M リターン、ma200_dev（データ不足時は None, ログ出力）。
    - calc_volatility: 20日 ATR、ATR 比、20日平均売買代金、出来高比率。
    - calc_value: raw_financials から EPS/ROE を取得し PER/ROE を計算（EPS が 0/欠損時は None）。
  - feature_exploration: 将来リターン計算、IC（Spearman ランク相関）、統計サマリー、ランク関数等を実装。
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21] 営業日）に対するリターンを一括取得。
    - calc_ic: factor と forward return を code で結合して Spearman ρ を算出。サンプル不足（<3）で None を返す。
    - factor_summary: count/mean/std/min/max/median の計算。
  - zscore_normalize は kabusys.data.stats から再エクスポート。

- データプラットフォーム（kabusys.data）
  - calendar_management:
    - JPX カレンダーの夜間差分更新ジョブ (calendar_update_job) を提供（J-Quants から取得して market_calendar に保存）。
    - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day 等の営業日判定ユーティリティ。
    - DB 登録がない部分は曜日ベースのフォールバック。最大探索日数の上限を設けて無限ループを防止。
    - バックフィル・健全性チェック（将来日付が異常に遠い場合はスキップ）。
  - pipeline / etl:
    - ETLResult データクラスを公開（kabusys.data.etl で再エクスポート）。
    - pipeline モジュール（ETL の差分取得、保存、品質チェックのための基盤）を実装。
    - 差分更新、バックフィル、品質チェック（重大度管理）などの設計方針に準拠。

- DuckDB を主要なストレージ層として採用
  - 各種モジュールで DuckDB 接続を受け取り SQL + Python ハイブリッドで処理を実施。

- OpenAI 統合
  - gpt-4o-mini を利用した JSON mode の呼び出しラッパーを各モジュールで実装。
  - テスト容易性を考慮し、内部の API 呼び出し関数は patch 可能な形で分離。

### 変更 (Changed)
- 初回リリースのため該当なし。

### 修正 (Fixed)
- 初回リリースのため該当なし。

### 既知の設計上の注意点・挙動
- ルックアヘッドバイアス防止のため、全ての日付判定・集計は target_date 引数に基づき、内部で datetime.today()/date.today() を参照しない設計が徹底されています（ただしカレンダー更新ジョブは内部で date.today() を参照）。
- OpenAI API 呼び出し失敗時はフォールバック動作（スコア 0.0 や処理スキップ）を行い、例外を上位へ投げない設計の箇所があります（運用時にはログで失敗を確認してください）。
- DuckDB のバージョン差分（executemany の空リスト等）に配慮した実装がなされています。
- .env 自動ロードはプロジェクトルートの特定に .git または pyproject.toml を使用します。パッケージ配布後に自動ロードを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。

### セキュリティ (Security)
- 初回リリースのため該当なし。

---

将来的なリリースでは、API の追加・既存関数の改善・型注釈の強化・テストカバレッジの向上などを予定しています。質問や改善提案があれば issue を立ててください。