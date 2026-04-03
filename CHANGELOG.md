# Changelog

すべての変更は Keep a Changelog の方針に従って記載しています。  
このプロジェクトはセマンティックバージョニングに従います。

現在のバージョン: 0.1.0 — 2026-04-03

## [Unreleased]
- なし

## [0.1.0] - 2026-04-03
最初の公開リリース。日本株自動売買プラットフォームのコアライブラリを実装しました。主な追加点、設計方針、注意点を以下にまとめます。

### 追加（Added）
- パッケージ基盤
  - kabusys パッケージの初期公開（__version__ = 0.1.0）。
  - モジュール公開: data, research, ai, config, などの主要サブパッケージ。

- 環境設定 / ロード（kabusys.config）
  - .env ファイルおよび環境変数の読み込み機能を実装（プロジェクトルート検出: .git または pyproject.toml を起点）。
  - .env / .env.local の読み込み順を実装（OS環境 > .env.local > .env）。.env.local は上書き優先。
  - 自動読み込みを無効化するフラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - 柔軟な .env パーサー実装（export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメント処理等を考慮）。
  - Settings クラスを提供し、J-Quants、kabu API、LINE、DB パス、監視閾値、環境・ログレベル判定（development/paper_trading/live）等のプロパティを公開。

- AI（kabusys.ai）
  - ニュース NLP（kabusys.ai.news_nlp）
    - raw_news と news_symbols を利用し、ターゲット時間窓のニュースを銘柄別に集約。
    - OpenAI（gpt-4o-mini）の JSON Mode を用いたバッチセンチメント評価（最大バッチサイズ＝20銘柄）。
    - レスポンスのバリデーション、スコアの ±1.0 クリップ、パース耐性（前後余計なテキストの復元）を実装。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフによるリトライ実装。
    - ai_scores テーブルへの冪等（DELETE → INSERT）書き込み。部分失敗時に他銘柄を保護するロジック。
    - 単体テスト容易性のため _call_openai_api を差し替え可能（モック可能）。
    - 公開関数: score_news(conn, target_date, api_key=None)、calc_news_window(target_date)。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を算出。
    - マクロキーワードに基づく raw_news フィルタリング、OpenAI 呼び出し（gpt-4o-mini）で macro_sentiment を取得。
    - API 障害に対するフェイルセーフ（失敗時 macro_sentiment=0.0）。
    - レジーム結果を market_regime テーブルへ冪等書き込み。
    - 公開関数: score_regime(conn, target_date, api_key=None)。

- データプラットフォーム（kabusys.data）
  - カレンダー管理（kabusys.data.calendar_management）
    - market_calendar を用いた営業日判定（is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days）。
    - DBデータを優先しつつ、未登録日は曜日ベース（平日のみ営業日）でフォールバックする一貫した挙動。
    - 夜間バッチで J-Quants から差分取得して market_calendar を更新する calendar_update_job を実装。バックフィルと健全性チェックあり。
  - ETL パイプライン（kabusys.data.pipeline）
    - 差分取得、保存（jquants_client の save_* による冪等保存）、品質チェック（kabusys.data.quality と連携）の枠組みを実装。
    - ETLResult データクラスを定義して取得/保存件数、品質問題、エラーを集約（kabusys.data.etl で再エクスポート）。
    - 初回ロード用の最小日付、バックフィル・カレンダー先読み等の既定値を提供。

- リサーチ（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）
    - Momentum: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）。
    - Volatility: 20 日 ATR（atr_20, atr_pct）、20 日平均売買代金、出来高比率。
    - Value: PER, ROE（raw_financials から最新レコードを取得）。
    - 各関数は prices_daily / raw_financials のみ参照し副作用なしで結果を dict リストで返す。
  - 特徴量探索（kabusys.research.feature_exploration）
    - 将来リターン計算（calc_forward_returns：任意ホライズンのリターン取得、horizons バリデーションあり）。
    - IC（Information Coefficient）計算（calc_ic：スピアマンのランク相関）、rank ユーティリティ、factor_summary（基礎統計量）を実装。
    - pandas 等に依存せず標準ライブラリ + DuckDB SQL で実装。

### 変更（Changed）
- 初回リリースのため変更履歴はなし。

### 修正（Fixed）
- 初回リリースのため修正履歴はなし。

### セキュリティ（Security）
- 環境変数の取り扱い注意:
  - OpenAI の API キーは score_news / score_regime の api_key 引数または環境変数 OPENAI_API_KEY を利用。キー未設定時は ValueError を送出。
  - 自動 .env 読み込みを無効化するために KABUSYS_DISABLE_AUTO_ENV_LOAD を設定可能（CI/テストで便利）。
- ログや設定で秘密情報が直接出力されないよう注意すること（本実装は設定プロパティをそのまま参照するため、運用での管理に依存）。

### 既知の注意点 / 設計上の決定
- ルックアヘッドバイアス対策:
  - 日付判定やウィンドウ計算で datetime.today() / date.today() を参照しない関数設計（すべて target_date を引数に受ける）。
  - DB クエリでは target_date 未満 / 排他条件を使用してルックアヘッドを回避。
- OpenAI 呼び出し:
  - gpt-4o-mini を既定モデルとして使用、JSON Mode で厳密な JSON 出力を期待する。ただしレスポンスが不正な場合の復元ロジックを実装。
  - リトライ方針: 429・ネットワーク・タイムアウト・5xx に対して指数バックオフでリトライ。その他は失敗をスキップして継続するフェイルセーフ設計。
  - テスト容易性のため _call_openai_api の差し替えが可能。
- DB 書き込み:
  - ai_scores / market_regime / その他の書き込みは冪等性（DELETE→INSERT や ON CONFLICT を想定）を考慮して実装。
  - DuckDB の executemany が空リストを受け付けない点を考慮して空チェックを行っている。
- タイムゾーン:
  - raw_news.datetime は UTC 保存を前提に、ニュースの時間窓は JST ベースで計算し UTC に変換した naive datetime を用いる（calc_news_window）。
- 依存:
  - DuckDB（duckdb パッケージ）および OpenAI SDK（openai パッケージ）への依存がある。
- 期待される DB テーブル（実行前に用意が必要）
  - prices_daily, raw_news, news_symbols, ai_scores, market_regime, raw_financials, market_calendar など。

### マイグレーション / 使用上のメモ
- 必須環境変数（例）
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD（kabu API 用）、OPENAI_API_KEY（AI 呼び出し）、KABUSYS_ENV（development/paper_trading/live）等。
- .env の自動読み込みが有効な場合、プロジェクトルートを .git または pyproject.toml から探索するため、配布後に CWD に依存せず動作します。必要に応じて KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を利用してください。
- テスト時は OpenAI 呼び出しをモックすることで外部 API 依存を排除できます（_call_openai_api をパッチ）。

---

今後の予定（例）
- model の切替 / 複数モデル対応、追加のファクター拡張、ETL のスケジューリングサポート、監視/アラート周りの強化などを検討しています。

もし CHANGELOG に追加してほしい点（実装の細部や日付の修正、セクションの細分化など）があれば教えてください。