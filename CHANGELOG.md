# CHANGELOG

すべての変更は Keep a Changelog 準拠で記載します。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

現在のパッケージバージョンは src/kabusys/__init__.py の __version__ に準拠しています。

## [Unreleased]

（現時点では未リリースの変更はありません）

---

## [0.1.0] - 2026-03-29

初回公開リリース。日本株自動売買システムのコア機能群を実装しました。主に以下のサブパッケージ／機能を含みます。

### 追加（Added）
- パッケージ基盤
  - kabusys パッケージ初版を追加（__version__ = 0.1.0）。
  - パッケージのエクスポート: data, strategy, execution, monitoring。

- 環境設定 & ロード（kabusys.config）
  - .env および .env.local をプロジェクトルート（.git または pyproject.toml）から自動読み込みする仕組みを実装。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応（テスト用）。
  - export KEY=val 形式やクォート / エスケープ、インラインコメントの取り扱いを考慮した .env パーサー実装。
  - 必須環境変数取得ヘルパー `_require` と Settings クラスを提供。
  - Settings により J-Quants / kabuステーション / Slack / DB パス / 実行環境（development/paper_trading/live）などの設定を取得可能。

- AI（kabusys.ai）
  - ニュース NLP（kabusys.ai.news_nlp）
    - raw_news と news_symbols を集約し、OpenAI（gpt-4o-mini, JSON mode）で銘柄ごとのセンチメント（-1.0〜1.0）を評価し ai_scores テーブルへ保存する score_news を実装。
    - 時間ウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）計算の calc_news_window を提供。
    - バッチ（最大 20 銘柄）での API 呼び出し、トークン肥大化対策（記事数・文字数制限）、応答バリデーション、スコアクリップを実装。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフリトライを実装。API失敗時は該当チャンクをスキップして継続するフェイルセーフ設計。
    - 単体テスト用に OpenAI 呼び出しを差し替え可能（内部の _call_openai_api を patch 可能）。

  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（日経225連動型）200日移動平均乖離（重み70%）とマクロニュースの LLM センチメント（重み30%）を合成し、日次で市場レジーム（bull/neutral/bear）を判定する score_regime を実装。
    - prices_daily と raw_news を参照し、ma200_ratio の算出、マクロニュース抽出、OpenAI による macro_sentiment の評価を行う。
    - API 呼び出し時のリトライ（429/ネットワーク断/タイムアウト/5xx）、フォールバック（API失敗時 macro_sentiment=0.0）実装。
    - DB 書き込みは冪等性を考慮した BEGIN / DELETE / INSERT / COMMIT を採用。失敗時に ROLLBACK を試行。
    - ルックアヘッドバイアス防止に注力（target_date 未満のみ参照、datetime.today() を参照しない）。

- データプラットフォーム（kabusys.data）
  - カレンダー管理（kabusys.data.calendar_management）
    - market_calendar を利用した営業日判定ロジック（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）を実装。
    - DB にカレンダーが存在しない場合は曜日ベースでフォールバック（週末 = 非営業日）。
    - カレンダーの夜間バッチ更新 job（calendar_update_job）を実装（J-Quants クライアントから差分取得 → 保存 → バックフィル / 健全性チェック）。
  - ETL パイプライン（kabusys.data.pipeline, etl）
    - ETL の結果を表す ETLResult データクラスを追加（品質チェック結果やエラー集約を含む）。
    - 差分取得／バックフィル／保存（jquants_client の save_* を利用）／品質チェックのワークフロー設計を反映。
    - DuckDB の可搬性を考慮したテーブル存在チェックや最大日付取得等のユーティリティを実装。
  - jquants_client, quality 等のクライアントやユーティリティは別モジュール（data.jquants_client など）を想定して連携。

- リサーチ（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）
    - Momentum（1M/3M/6M リターン、ma200 乖離）、Volatility（20日 ATR、相対 ATR、出来高関連）、Value（PER、ROE）等を DuckDB の prices_daily / raw_financials から計算する calc_momentum / calc_volatility / calc_value を実装。
    - データ不足時の扱い（必要行数未満 → None）やログ出力を実装。
  - 特徴量探索（kabusys.research.feature_exploration）
    - 将来リターン計算（calc_forward_returns）、IC（Spearman ランク相関）計算（calc_ic）、ランク変換ユーティリティ（rank）、ファクター統計サマリー（factor_summary）を実装。
    - pandas 等の外部依存を避け、標準ライブラリと DuckDB の SQL で完結する設計。

### 変更（Changed）
- 初版リリースのため「変更」は特になし（全て新規追加）。

### 修正（Fixed）
- 初版リリースのため「修正」は特になし。実装にはフェイルセーフ・リトライ・入力バリデーション等の堅牢性強化を組み込んでいます。

### 破壊的変更（Breaking Changes）
- 初回リリースのため既存互換性問題はなし。ただし今後の API 変更に備えて OpenAI 呼び出しや DB スキーマを安定化する予定。

### セキュリティ（Security）
- OpenAI の API キーや各種トークンは Settings 経由で環境変数から取得する設計。必須環境変数が未設定の場合は明確な ValueError を発生させるようにしています。
- .env 自動ロードはデフォルトで有効だが、テストや CI 用に KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。

---

## 既知の注意点 / マイグレーションノート
- 必須環境変数（例）
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID は Settings により必須扱い。OPENAI_API_KEY は score_news / score_regime 呼び出し時に必要（api_key 引数で上書き可能）。
- DuckDB スキーマ
  - 本コードは prices_daily, raw_news, raw_financials, news_symbols, ai_scores, market_regime, market_calendar などのテーブルが存在することを前提としています。初期導入時はスキーマの作成と初回 ingest が必要です。
- テスト時の差し替え
  - OpenAI への実ネットワーク呼び出しはモジュール内の _call_openai_api を patch することでモック可能です（unittest.mock.patch を想定）。
- レスポンスパースの堅牢性
  - LLM の応答は JSON mode を利用しますが、まれに前後に余計なテキストが混入することを想定して復元処理を行います。それでも想定外の形式はスキップされます。

---

貢献者: 初期実装チーム（コードベース注釈に基づく推定実装者情報は省略）。  
質問や改善提案があれば CHANGELOG の更新とあわせて issue を作成してください。