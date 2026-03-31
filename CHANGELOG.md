# Changelog

すべての注目すべき変更をこのファイルに記録します。
このプロジェクトは Keep a Changelog の規約に準拠します。
SemVer を採用しています。

## [Unreleased]

## [0.1.0] - 2026-03-31
初回リリース。日本株自動売買システム「KabuSys」のコア機能を実装しました。主な追加点・設計上の注意点は以下の通りです。

### 追加 (Added)
- パッケージ基盤
  - パッケージメタ情報（kabusys.__init__）を追加。公開サブパッケージ: data, strategy, execution, monitoring。
  - バージョン: 0.1.0。

- 設定管理
  - 環境変数/.env 管理モジュール（kabusys.config）を追加。
    - プロジェクトルート検出（.git / pyproject.toml に基づく）。
    - .env / .env.local の自動読み込み（OS環境変数優先、.env.local は上書き）。
    - export KEY=val 形式やクォート・エスケープ・インラインコメントに対応したパーサ実装。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動読み込みを無効化可能。
    - 必須環境変数を取得する _require ヘルパーと Settings クラス（J-Quants, kabu API, Slack, DB パス, 環境判定, ログレベル等）。
    - デフォルト値や入力検証（KABUSYS_ENV / LOG_LEVEL の妥当性チェック）。

- AI（自然言語処理）機能
  - ニュース NLP スコアリング（kabusys.ai.news_nlp）
    - raw_news / news_symbols を集約して銘柄ごとの記事を作成。
    - OpenAI (gpt-4o-mini) を用いたバッチセンチメント解析（JSON Mode）。
    - リトライ戦略（429, ネットワーク断, タイムアウト, 5xx）を実装（指数バックオフ）。
    - レスポンスの厳密なバリデーションとスコアクリップ（±1.0）。
    - スコアを書き込む際は部分失敗が他銘柄データを壊さないよう、取得済みコードのみ DELETE → INSERT（冪等性確保）。
    - テスト容易性を考慮し OpenAI 呼び出し箇所を差し替え可能（内部 _call_openai_api を patch 可能）。
    - calc_news_window ユーティリティを提供（JST の時間ウィンドウを UTC naive datetime で返す）。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（Nikkei225 連動）の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次の市場レジームを判定（bull/neutral/bear）。
    - マクロ記事はキーワードベースで抽出。LLM 評価は gpt-4o-mini を使用。
    - API エラー時は macro_sentiment=0.0 にフォールバック（フェイルセーフ）。
    - DB への書き込みは冪等に BEGIN/DELETE/INSERT/COMMIT を使用。
    - テスト向けに _call_openai_api を差し替え可能。

- Data（データ管理・ETL）
  - マーケットカレンダー管理（kabusys.data.calendar_management）
    - market_calendar テーブルの管理と営業日判定ユーティリティ（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - DB にデータがない場合は曜日ベース（土日除外）でフォールバック。
    - JPX カレンダーの差分取得を行う夜間バッチ（calendar_update_job）を実装。バックフィル・健全性チェックあり。
  - ETL パイプライン（kabusys.data.pipeline / etl）
    - ETL の結果を表す ETLResult データクラスを公開（kabusys.data.etl で再エクスポート）。
    - 差分取得、保存（jquants_client 経由で冪等保存）、品質チェックフレームワークを想定した設計。
    - _get_max_date / _table_exists 等のヘルパーを実装。

- Research（リサーチ用ユーティリティ）
  - ファクター計算（kabusys.research.factor_research）
    - Momentum（1M/3M/6M リターン、ma200 乖離）、Volatility（20日 ATR 等）、Value（PER, ROE）を計算する関数を実装。DuckDB の SQL + Python 組み合わせで計算。
    - 欠損・データ不足は None を返すよう扱い、production データアクセスは行わない設計。
  - 特徴量解析（kabusys.research.feature_exploration）
    - 将来リターン計算（calc_forward_returns）、IC（calc_ic）計算、rank、factor_summary 等の統計関数を提供。
    - pandas 等に依存しない標準ライブラリ実装。

### 変更 (Changed)
- （初回リリースのため、変更履歴はありません）

### 修正 (Fixed)
- （初回リリースのため、修正履歴はありません）

### 注意点 / 既知の制約 (Notes / Known limitations)
- OpenAI API
  - news_nlp / regime_detector は OpenAI の API キー（api_key 引数または環境変数 OPENAI_API_KEY）を必須とします。未設定時は ValueError を送出します。
  - レスポンスは JSON mode を利用する前提だが、余計な前後テキストが混入するケースを想定して冗長なパースロジックを備えています。
  - テスト時の差し替えポイント（_call_openai_api）を用意しています。

- DuckDB スキーマ依存
  - 多くの関数は DuckDB の特定テーブル（prices_daily, raw_news, news_symbols, ai_scores, market_regime, market_calendar, raw_financials など）を前提としています。スキーマが揃っていないと動作しません。

- 自動 .env 読み込み
  - パッケージはインポート時にプロジェクトルートを探索して .env / .env.local を自動読み込みします。CI やテストでこれを抑制したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

- フォールバック方針
  - データ不足や API エラー時は可能な限り処理を続行し、フェイルセーフ（デフォルト値やスキップ）で挙動を安定化させる設計です。ただし、必須設定が欠けている場合は例外を投げます。

### セキュリティ (Security)
- 本リリースに関するセキュリティ修正の報告はありませんが、運用においては API キーやパスワード等の取り扱いに注意してください（.env ファイルの適切な管理、OS 環境変数の使用推奨）。

---

将来的な改善案（未実装）
- PBR や配当利回り等のバリューファクター拡張。
- AI プロンプトの継続的チューニングおよびモデル選択の抽象化。
- ETL の並列化・パフォーマンス最適化、より詳細な品質チェックルール。
- 単体テスト・統合テストの追加（現状は差し替えポイントはあるが完全網羅は未実装）。

※ 問題やバグを見つけた場合は issue として報告してください。